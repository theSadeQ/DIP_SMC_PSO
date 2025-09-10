# scripts/sensitivity_analysis.py ===============================================================================\\\
"""
Standalone script to perform sensitivity analysis on cost function weights.

"""
import argparse
import copy
import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
import yaml
import tempfile

sys.path.append(str(Path(__file__).parent.parent))

from src.optimizer.pso_optimizer import PSOTuner
from src.controllers.factory import create_controller
from src.config import load_config, ConfigSchema
from src.core.vector_sim import simulate_system_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class SensitivityAnalyzer:
    """
    Class for performing sensitivity analysis on cost function weights.
    
    """

    def __init__(self, config_path: str = "config.yaml", controller_type: str = "classical_smc"):
        """
        Initialize the sensitivity analyzer.

        Parameters
        ----------
        config_path : str, optional
            Path to the configuration YAML file, by default "config.yaml"
        controller_type : str, optional
            Type of controller to analyze, by default "classical_smc"
            
        """
        self.original_config: ConfigSchema = load_config(config_path)
        self.controller_type: str = controller_type
        self.results_dir: Path = Path("sensitivity_results") / datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(config_path, self.results_dir / "config.yaml")
        
    def _create_temp_config(self, weight_name: str, value: float) -> Tuple[str, tempfile.TemporaryDirectory]:
        """
        Create a temporary configuration file with a modified weight value.

        Parameters
        ----------
        weight_name : str
            Name of the weight to modify
        value : float
            New value for the weight

        Returns
        -------
        tuple[str, tempfile.TemporaryDirectory]
            Path to the temporary config file and the temporary directory object
            
        """
        temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(temp_dir.name) / "config.yaml"
        mod_config = copy.deepcopy(self.original_config)
        setattr(mod_config.cost_function.weights, weight_name, float(value))
        with open(temp_path, "w") as f:
            yaml.safe_dump(mod_config.model_dump(), f)
        return str(temp_path), temp_dir
        
    def _compute_metrics(self, best_gains: np.ndarray, config: ConfigSchema) -> Dict[str, float]:
        """
        Compute performance metrics using the optimized gains.

        Parameters
        ----------
        best_gains : np.ndarray
            Optimized controller gains
        config : ConfigSchema
            Configuration object

        Returns
        -------
        dict[str, float]
            Dictionary of computed metrics
            
        """
        def controller_factory(gains: np.ndarray):
            return create_controller(self.controller_type, gains)
        
        sim_time: float = config.simulation.duration
        particles: np.ndarray = np.array([best_gains])
        t, states, controls, sigma = simulate_system_batch(controller_factory, particles, sim_time)
        
        dt: float = np.diff(t)[0]
        n_steps: int = len(t)
        rms_state: float = np.sqrt(np.mean(np.sum(states[0, :, :3] ** 2, axis=1)))
        rms_control: float = np.sqrt(np.mean(controls[0] ** 2))
        du: np.ndarray = np.diff(controls[0], prepend=controls[0][0])
        rms_du: float = np.sqrt(np.mean(du ** 2))
        rms_sigma: float = np.sqrt(np.mean(sigma[0] ** 2))
        
        threshold: float = 0.01
        angles: np.ndarray = np.abs(states[0, :, 1:3])
        settled: np.ndarray = np.all(angles < threshold, axis=1)
        if np.all(settled[-int(n_steps / 10) :]):
            unsettle_idx: np.ndarray = np.where(~settled)[0]
            settling_time: float = t[unsettle_idx[-1] + 1] if len(unsettle_idx) > 0 else 0.0
        else:
            settling_time: float = sim_time
            
        return {
            "rms_state": rms_state,
            "rms_control": rms_control,
            "rms_du": rms_du,
            "rms_sigma": rms_sigma,
            "settling_time": settling_time,
        }
    
    def analyze(self) -> pd.DataFrame:
        """
        Perform the sensitivity analysis.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the analysis results
            
        """
        data = []
        weights_to_vary = ["state_error", "control_effort", "control_rate", "stability"]
        for weight_name in weights_to_vary:
            default_val = getattr(self.original_config.cost_function.weights, weight_name)
            if weight_name == "state_error":
                values = np.linspace(10, 100, 5)
            else:
                values = np.linspace(0.05, 0.5, 5)

            for val in values:
                logging.info(f"Analyzing {weight_name} = {val:.2f}")
                temp_config_path, temp_dir = self._create_temp_config(weight_name, val)
                
                def controller_factory(gains: np.ndarray):
                    return create_controller(self.controller_type, gains)
                
                tuner = PSOTuner(controller_factory, temp_config_path)
                bounds = tuner.cfg.pso.bounds
                x0 = tuple(np.mean([bounds.min, bounds.max], axis=0))
                
                start_time = time.time()
                result = tuner.optimise(x0=x0)
                elapsed_time = time.time() - start_time
                
                best_gains = result["best_pos"]
                best_cost = result["best_cost"]
                
                metrics = self._compute_metrics(best_gains, tuner.cfg)
                
                entry = { 
                    "weight_name": weight_name, 
                    "value": float(val), 
                    "best_gains": best_gains.tolist(), 
                    "best_cost": float(best_cost), 
                    "optimization_time": elapsed_time 
                }
                entry.update(metrics)
                data.append(entry)
                
                temp_dir.cleanup()
        
        df = pd.DataFrame(data)
        df.to_csv(self.results_dir / "sensitivity_data.csv", index=False)
        logging.info(f"Data saved to: {self.results_dir / 'sensitivity_data.csv'}")
        self._generate_plots(df)
        return df

    def _generate_plots(self, df: pd.DataFrame) -> None:
        """
        Generate trade-off plots from the analysis data.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame containing the analysis results
            
        """
        weights_to_vary = df["weight_name"].unique()
        for weight_name in weights_to_vary:
            sub_df = df[df["weight_name"] == weight_name].sort_values("value")
            plt.figure(figsize=(8, 6))
            plt.plot(sub_df["rms_state"], sub_df["rms_control"], "o-", label="Trade-off Curve")
            for i, val in enumerate(sub_df["value"]):
                plt.annotate(f"{val:.2f}", (sub_df["rms_state"].iloc[i], sub_df["rms_control"].iloc[i]))
            plt.xlabel("RMS State Error")
            plt.ylabel("RMS Control Effort")
            plt.title(f"Trade-off: RMS State Error vs. Control Effort\n(Varying {weight_name})")
            plt.legend()
            plt.grid(True)
            filename = self.results_dir / f"tradeoff_{weight_name}.png"
            plt.savefig(filename, dpi=150, bbox_inches="tight")
            plt.close()

def main() -> None:
    """Main entry point for the sensitivity analysis script."""
    parser = argparse.ArgumentParser(description="Sensitivity analysis on cost function weights.")
    parser.add_argument("--config", default="config.yaml", help="Path to configuration YAML file.")
    parser.add_argument("--controller_type", default="classical_smc", help="Controller type to analyze.")
    args = parser.parse_args()
    analyzer = SensitivityAnalyzer(config_path=args.config, controller_type=args.controller_type)
    analyzer.analyze()
    logging.info(f"\n{'='*60}\nSensitivity analysis complete!\nAll results saved in: {analyzer.results_dir}")

if __name__ == "__main__":
    main()
#===========================================================================================================\\\   