# scripts/reoptimize_controllers.py ========================================================\\\
"""
Main script to perform systematic re-optimization of all controller types
using the consolidated PSO tuner.
"""
import argparse
import json
import logging
import matplotlib.pyplot as plt
import numpy as np
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Setup project path to import src files

sys.path.append(str(Path(__file__).parent.parent))

from src.optimizer.pso_optimizer import PSOTuner
from src.controllers.factory import create_controller
from src.config import load_config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ControllerReoptimizer:
    """Systematic re-optimization of all controller types."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize re-optimizer with configuration."""
        self.config = load_config(config_path)
        self.results_dir = Path("optimization_results") / datetime.now().strftime(
            "%Y-%m-%d_%H%M%S"
        )
        self.results_dir.mkdir(parents=True, exist_ok=True)
        # Save a copy of the config for reproducibility
        shutil.copy(config_path, self.results_dir / "config.yaml")

    def optimize_controller(self, controller_type: str, n_runs: int = 3) -> Dict:
        """
        Optimize a specific controller type multiple times for statistical confidence.
        """
        logging.info(
            "=" * 60 + f"\nOptimizing {controller_type} Controller\n" + "=" * 60
        )

        pso_section = self.config.pso

        # The new config schema nests the bounds
        bounds = pso_section.bounds

        def controller_factory(gains):
            return create_controller(controller_type, gains)

        all_costs, all_gains, all_results = [], [], []

        for run in range(n_runs):
            logging.info(f"--- Run {run + 1}/{n_runs} ---")
            np.random.seed(self.config.global_seed + run)

            tuner = PSOTuner(
                controller_factory, config_path=str(self.results_dir / "config.yaml")
            )

            # Initial guess is the mean of the bounds
            x0 = tuple(np.mean([bounds.min, bounds.max], axis=0))

            start_time = time.time()
            result = tuner.optimise(x0=x0, use_hyperopt=False)
            result["elapsed_time"] = time.time() - start_time

            all_results.append(result)
            all_gains.append(result["best_pos"])
            all_costs.append(result["best_cost"])

            logging.info(
                f"Best cost: {result['best_cost']:.6f} | Best gains: {result['best_pos']}"
            )

        best_idx = np.argmin(all_costs)
        stats = {
            "controller_type": controller_type,
            "best_gains": all_gains[best_idx].tolist(),
            "best_cost": float(all_costs[best_idx]),
            "mean_cost": float(np.mean(all_costs)),
            "std_cost": float(np.std(all_costs)),
            "convergence_history": all_results[best_idx]["history"],
        }

        self._save_results(controller_type, stats)
        self._plot_convergence(controller_type, all_results)
        return stats

    def _save_results(self, controller_type: str, results: Dict):
        """Save optimization results to a JSON file."""
        filename = self.results_dir / f"{controller_type}_results.json"
        with open(filename, "w") as f:
            json.dump(results, f, indent=2, sort_keys=True)
        logging.info(f"Results saved to: {filename}")

    def _plot_convergence(self, controller_type: str, all_results: list):
        """Plot and save the convergence history for all runs."""
        plt.figure(figsize=(10, 6))
        for i, result in enumerate(all_results):
            if "history" in result and result["history"]:
                plt.semilogy(result["history"], alpha=0.8, label=f"Run {i + 1}")
        plt.xlabel("Iteration")
        plt.ylabel("Cost (log scale)")
        plt.title(f"{controller_type} PSO Convergence History")
        plt.legend()
        plt.grid(True, which="both", ls="--", alpha=0.5)
        filename = self.results_dir / f"{controller_type}_convergence.png"
        plt.savefig(filename, dpi=150, bbox_inches="tight")
        plt.close()

    def optimize_all_controllers(self) -> Dict:
        """Optimize all controller types specified in the config."""
        all_controller_results = {}
        controller_types = list(self.config.controllers.keys())

        for ctrl_type in controller_types:
            results = self.optimize_controller(ctrl_type, n_runs=3)
            all_controller_results[ctrl_type] = results

        self._create_comparison_report(all_controller_results)
        return all_controller_results

    def _create_comparison_report(self, all_results: Dict):
        """Generate a markdown summary report of the optimization results."""
        report = [
            f"# Controller Optimization Report\n\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        ]
        report.append("## Summary of Best Results\n")
        report.append("| Controller | Best Cost | Mean Cost (Std) | Best Gains |")
        report.append("|------------|-----------|-----------------|------------|")

        for ctrl, res in all_results.items():
            gains_str = ", ".join([f"{g:.3f}" for g in res["best_gains"]])
            cost_str = f"{res['best_cost']:.6f}"
            mean_std_str = f"{res['mean_cost']:.4f} (±{res['std_cost']:.4f})"
            report.append(f"| {ctrl} | {cost_str} | {mean_std_str} | `{gains_str}` |")

        report_file = self.results_dir / "optimization_report.md"
        with open(report_file, "w") as f:
            f.write("\n".join(report))
        logging.info(f"\nReport saved to: {report_file}")


def main(argv: Optional[list[str]] = None):
    """Main entry point to run the re-optimization for all controllers."""
    parser = argparse.ArgumentParser(
        description="Systematic re-optimization of all controller types."
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to the configuration YAML file."
    )
    parser.add_argument("--iterations", type=int, help="Override PSO iterations.")
    parser.add_argument(
        "--save-json", type=str, help="Save final gains to a JSON file."
    )
    parser.add_argument(
        "--hyper-tune",
        action="store_true",
        help="Run Optuna hyperparameter search over PSO (w, c1, c2) instead of direct gain optimization.",
    )

    args = parser.parse_args(argv)

    optimizer = ControllerReoptimizer(config_path=args.config)

    if args.hyper_tune:
        # Hyperparameter search path: tune (w, c1, c2), compare to default, and log improvement
        final_results = {}
        controller_types = list(optimizer.config.controllers.keys())
        for ctrl in controller_types:
            logging.info("=" * 60 + f"\nHyper-tuning PSO for {ctrl}\n" + "=" * 60)
            bounds = optimizer.config.pso.bounds

            # Factory for this controller
            def controller_factory(gains):
                from src.controllers.factory import create_controller

                return create_controller(ctrl, gains)

            from src.optimizer.pso_optimizer import PSOTuner

            tuner = PSOTuner(
                controller_factory,
                config_path=str(optimizer.results_dir / "config.yaml"),
            )

            # Baseline using default PSO (as in config)
            baseline = tuner.optimise()
            logging.info(f"[{ctrl}] Default PSO cost: {baseline['best_cost']:.6f}")

            # Run Optuna study to find better (w, c1, c2)
            hyper = tuner.run_hyper_tuning()
            logging.info(f"[{ctrl}] Best PSO hyperparameters: {hyper['best_params']}")
            logging.info(
                f"[{ctrl}] Best cost found during study: {hyper['best_value']:.6f}"
            )

            # Re-run PSO once with the discovered hyperparameters for an apples-to-apples comparison
            tuned = tuner.optimise(options_override=hyper["best_params"])
            logging.info(
                f"[{ctrl}] Tuned PSO cost: {tuned['best_cost']:.6f} "
                f"(Δ = {baseline['best_cost'] - tuned['best_cost']:+.6f})"
            )

            # Persist per-controller hyper-tuning summary
            out = {
                "controller": ctrl,
                "default_cost": float(baseline["best_cost"]),
                "tuned_cost": float(tuned["best_cost"]),
                "improvement": float(baseline["best_cost"] - tuned["best_cost"]),
                "best_pso_hyperparams": hyper["best_params"],
                "study_best_value": float(hyper["best_value"]),
            }
            final_results[ctrl] = out
            with open(optimizer.results_dir / f"{ctrl}_hyper_tuning.json", "w") as f:
                json.dump(out, f, indent=2)
        # Optional combined save
        if args.save_json:
            with open(args.save_json, "w") as f:
                json.dump(final_results, f, indent=2)
        logging.info("\n" + "=" * 60)
        logging.info("Hyper-tuning complete!")
        logging.info(f"All results saved in: {optimizer.results_dir}")
        return

    # Default path (no flag): keep current behavior
    final_results = optimizer.optimize_all_controllers()

    if args.save_json:
        optimized_gains = {
            ctrl: data["best_gains"] for ctrl, data in final_results.items()
        }
        with open(args.save_json, "w") as f:
            json.dump(optimized_gains, f, indent=2)
        logging.info(f"Best overall gains saved to: {args.save_json}")

    logging.info("\n" + "=" * 60)
    logging.info("Re-optimization complete!")
    logging.info(f"All results saved in: {optimizer.results_dir}")


if __name__ == "__main__":
    main()
# scripts/reoptimize_controllers.py ========================================================\\\
