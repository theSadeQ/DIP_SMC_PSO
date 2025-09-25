#==========================================================================================\\\
#============================= automated_benchmark.py =============================\\\
#==========================================================================================\\\
"""
Automated benchmarking framework for SMC controllers comparison.

This module provides a comprehensive benchmarking system that automatically runs
all test scenarios across all four SMC controllers, collects performance data,
performs statistical analysis, and generates comparison reports.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import json
import pickle
from pathlib import Path
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import matplotlib.pyplot as plt
import seaborn as sns

from experimental_design import ExperimentalDesign, TestScenario, ControllerType, PerformanceMetrics, MetricsCalculator
from statistical_analysis import StatisticalAnalyzer, StatisticalResult


class BenchmarkRunner:
    """Automated benchmark execution and data collection system."""

    def __init__(self,
                 output_dir: str = "benchmark_results",
                 n_monte_carlo: int = 100,
                 parallel_jobs: int = 4,
                 random_seed: int = 42):
        """
        Initialize benchmark runner.

        Parameters
        ----------
        output_dir : str
            Directory to store benchmark results
        n_monte_carlo : int
            Number of Monte Carlo trials per scenario
        parallel_jobs : int
            Number of parallel jobs for computation
        random_seed : int
            Random seed for reproducibility
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.n_monte_carlo = n_monte_carlo
        self.parallel_jobs = parallel_jobs
        self.random_seed = random_seed

        # Initialize components
        self.experimental_design = ExperimentalDesign()
        self.metrics_calculator = MetricsCalculator()
        self.statistical_analyzer = StatisticalAnalyzer()

        # Set up logging
        self._setup_logging()

        # Initialize random state
        np.random.seed(random_seed)

    def _setup_logging(self):
        """Set up logging configuration."""
        log_file = self.output_dir / "benchmark.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger(__name__)

    def run_complete_benchmark(self) -> Dict[str, Any]:
        """
        Run complete benchmark suite across all controllers and scenarios.

        Returns
        -------
        Dict[str, Any]
            Complete benchmark results including raw data and statistical analysis
        """

        self.logger.info("Starting complete benchmark suite...")
        self.logger.info(f"Scenarios: {len(self.experimental_design.scenarios)}")
        self.logger.info(f"Controllers: {len(ControllerType)}")
        self.logger.info(f"Monte Carlo trials: {self.n_monte_carlo}")

        # Run all benchmarks
        all_results = {}

        for controller_type in ControllerType:
            self.logger.info(f"Benchmarking {controller_type.value}...")

            controller_results = self._run_controller_benchmark(controller_type)
            all_results[controller_type.value] = controller_results

        # Perform statistical analysis
        self.logger.info("Performing statistical analysis...")
        statistical_results = self._perform_statistical_analysis(all_results)

        # Generate comprehensive report
        self.logger.info("Generating reports...")
        report = self._generate_benchmark_report(all_results, statistical_results)

        # Save results
        self.logger.info("Saving results...")
        self._save_results(all_results, statistical_results, report)

        self.logger.info("Benchmark suite completed successfully!")

        return {
            'raw_results': all_results,
            'statistical_results': statistical_results,
            'report': report,
            'metadata': self._get_benchmark_metadata()
        }

    def _run_controller_benchmark(self, controller_type: ControllerType) -> Dict[str, List[PerformanceMetrics]]:
        """Run benchmark for a single controller across all scenarios."""

        controller_results = {}

        for scenario in self.experimental_design.scenarios:
            self.logger.info(f"  Running scenario: {scenario.name}")

            scenario_results = self._run_scenario_benchmark(controller_type, scenario)
            controller_results[scenario.name] = scenario_results

        return controller_results

    def _run_scenario_benchmark(self,
                               controller_type: ControllerType,
                               scenario: TestScenario) -> List[PerformanceMetrics]:
        """Run Monte Carlo trials for a single controller-scenario combination."""

        # Generate parameter variations for Monte Carlo
        parameter_sets = self.experimental_design.get_monte_carlo_parameters(scenario, self.n_monte_carlo)

        results = []

        if self.parallel_jobs > 1:
            # Parallel execution
            with ProcessPoolExecutor(max_workers=self.parallel_jobs) as executor:
                futures = []

                for i, params in enumerate(parameter_sets):
                    future = executor.submit(
                        self._run_single_simulation,
                        controller_type, scenario, params, i
                    )
                    futures.append(future)

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result is not None:
                            results.append(result)
                    except Exception as e:
                        self.logger.error(f"Simulation failed: {e}")
        else:
            # Sequential execution
            for i, params in enumerate(parameter_sets):
                try:
                    result = self._run_single_simulation(controller_type, scenario, params, i)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Simulation {i} failed: {e}")

        self.logger.info(f"    Completed {len(results)}/{self.n_monte_carlo} trials")

        return results

    def _run_single_simulation(self,
                              controller_type: ControllerType,
                              scenario: TestScenario,
                              parameters: Dict[str, float],
                              trial_id: int) -> Optional[PerformanceMetrics]:
        """
        Run a single simulation trial.

        This is a placeholder that should be replaced with actual controller/simulation code.
        """

        try:
            # TODO: Replace with actual simulation code
            # This would involve:
            # 1. Creating the controller instance
            # 2. Setting up the plant model with parameters
            # 3. Running the simulation with the scenario
            # 4. Calculating performance metrics

            # Placeholder: Generate mock realistic data for now
            metrics = self._generate_mock_metrics(controller_type, scenario, trial_id)

            return metrics

        except Exception as e:
            self.logger.error(f"Trial {trial_id} failed: {e}")
            return None

    def _generate_mock_metrics(self,
                              controller_type: ControllerType,
                              scenario: TestScenario,
                              trial_id: int) -> PerformanceMetrics:
        """Generate realistic mock performance metrics for testing."""

        # Set different baseline performance for each controller
        controller_baselines = {
            ControllerType.CLASSICAL_SMC: {
                'settling_time': 3.5, 'chattering_index': 0.15, 'control_energy': 125.0
            },
            ControllerType.ADAPTIVE_SMC: {
                'settling_time': 2.8, 'chattering_index': 0.12, 'control_energy': 110.0
            },
            ControllerType.STA_SMC: {
                'settling_time': 3.2, 'chattering_index': 0.06, 'control_energy': 95.0
            },
            ControllerType.HYBRID_ADAPTIVE_STA: {
                'settling_time': 2.5, 'chattering_index': 0.04, 'control_energy': 85.0
            }
        }

        baseline = controller_baselines[controller_type]

        # Add noise and scenario-specific variations
        noise_factor = 0.1 + 0.05 * np.random.randn()
        scenario_factor = 1.0

        if 'Disturbance' in scenario.name:
            scenario_factor = 1.2
        elif 'Uncertainty' in scenario.name:
            scenario_factor = 1.15
        elif 'Noise' in scenario.name:
            scenario_factor = 1.1

        return PerformanceMetrics(
            settling_time=baseline['settling_time'] * scenario_factor * (1 + noise_factor),
            rise_time=0.8 * baseline['settling_time'] * scenario_factor * (1 + 0.8 * noise_factor),
            overshoot=5.0 + 3.0 * np.random.rand() * scenario_factor,
            steady_state_error=0.01 + 0.005 * np.random.rand() * scenario_factor,
            chattering_index=baseline['chattering_index'] * scenario_factor * (1 + abs(noise_factor)),
            control_energy=baseline['control_energy'] * scenario_factor * (1 + abs(noise_factor)),
            rms_control_effort=np.sqrt(baseline['control_energy']) * scenario_factor * (1 + abs(noise_factor)),
            disturbance_rejection=0.85 + 0.1 * np.random.rand(),
            noise_sensitivity=0.75 + 0.15 * np.random.rand(),
            parameter_sensitivity=0.8 + 0.15 * np.random.rand()
        )

    def _perform_statistical_analysis(self,
                                    all_results: Dict[str, Dict[str, List[PerformanceMetrics]]]) -> Dict[str, Dict[str, StatisticalResult]]:
        """Perform statistical analysis across all scenarios and metrics."""

        statistical_results = {}

        # Get all performance metric names
        if all_results:
            sample_metrics = next(iter(next(iter(all_results.values())).values()))[0]
            metric_names = [field.name for field in sample_metrics.__dataclass_fields__]
        else:
            return statistical_results

        # Analyze each scenario
        for scenario_name in self.experimental_design.scenarios[0].name.__class__.__dict__:
            if not hasattr(self.experimental_design.scenarios[0], scenario_name):
                continue

        scenarios = [s.name for s in self.experimental_design.scenarios]

        for scenario_name in scenarios:
            scenario_results = {}

            # Collect results for this scenario across all controllers
            scenario_data = {}
            for controller_name, controller_results in all_results.items():
                if scenario_name in controller_results:
                    scenario_data[controller_name] = controller_results[scenario_name]

            if not scenario_data:
                continue

            # Analyze each metric for this scenario
            for metric_name in metric_names:
                try:
                    result = self.statistical_analyzer.analyze_metric_comparison(
                        scenario_data, metric_name
                    )
                    scenario_results[metric_name] = result
                except Exception as e:
                    self.logger.error(f"Statistical analysis failed for {scenario_name}/{metric_name}: {e}")

            statistical_results[scenario_name] = scenario_results

        return statistical_results

    def _generate_benchmark_report(self,
                                 all_results: Dict[str, Dict[str, List[PerformanceMetrics]]],
                                 statistical_results: Dict[str, Dict[str, StatisticalResult]]) -> str:
        """Generate comprehensive benchmark report."""

        report_lines = []
        report_lines.append("=" * 100)
        report_lines.append("SMC CONTROLLERS COMPREHENSIVE BENCHMARK REPORT")
        report_lines.append("=" * 100)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Monte Carlo trials: {self.n_monte_carlo}")
        report_lines.append(f"Random seed: {self.random_seed}")
        report_lines.append("")

        # Executive summary
        report_lines.append("EXECUTIVE SUMMARY")
        report_lines.append("-" * 20)
        report_lines.extend(self._generate_executive_summary(all_results, statistical_results))
        report_lines.append("")

        # Scenario-by-scenario analysis
        for scenario_name, scenario_stats in statistical_results.items():
            report_lines.append(f"SCENARIO: {scenario_name}")
            report_lines.append("-" * len(f"SCENARIO: {scenario_name}"))

            scenario_report = self.statistical_analyzer.generate_comparison_report(scenario_stats)
            report_lines.append(scenario_report)
            report_lines.append("")

        return "\n".join(report_lines)

    def _generate_executive_summary(self,
                                  all_results: Dict[str, Dict[str, List[PerformanceMetrics]]],
                                  statistical_results: Dict[str, Dict[str, StatisticalResult]]) -> List[str]:
        """Generate executive summary of benchmark results."""

        summary = []

        # Count significant differences
        total_comparisons = 0
        significant_comparisons = 0

        for scenario_stats in statistical_results.values():
            for stat_result in scenario_stats.values():
                total_comparisons += 1
                if stat_result.significant:
                    significant_comparisons += 1

        summary.append(f"Total statistical comparisons: {total_comparisons}")
        summary.append(f"Significant differences found: {significant_comparisons} ({100*significant_comparisons/total_comparisons:.1f}%)")
        summary.append("")

        # Overall best performer analysis
        controller_wins = {controller: 0 for controller in ControllerType}

        for scenario_stats in statistical_results.values():
            for metric_name, stat_result in scenario_stats.items():
                if stat_result.significant:
                    # Find best performer for this metric
                    means = {controller: stats['mean']
                            for controller, stats in stat_result.summary_statistics.items()}
                    best_controller = min(means.keys(), key=lambda k: means[k])

                    # Find corresponding ControllerType
                    for controller_type in ControllerType:
                        if controller_type.value == best_controller:
                            controller_wins[controller_type] += 1
                            break

        summary.append("Overall performance ranking:")
        sorted_controllers = sorted(controller_wins.items(), key=lambda x: x[1], reverse=True)
        for i, (controller, wins) in enumerate(sorted_controllers, 1):
            summary.append(f"{i}. {controller.value}: {wins} metric wins")

        return summary

    def _save_results(self,
                     all_results: Dict[str, Dict[str, List[PerformanceMetrics]]],
                     statistical_results: Dict[str, Dict[str, StatisticalResult]],
                     report: str):
        """Save all benchmark results to files."""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save raw results as pickle for Python analysis
        with open(self.output_dir / f"raw_results_{timestamp}.pkl", 'wb') as f:
            pickle.dump(all_results, f)

        # Save statistical results as JSON
        statistical_json = {}
        for scenario, scenario_stats in statistical_results.items():
            statistical_json[scenario] = {}
            for metric, stat_result in scenario_stats.items():
                statistical_json[scenario][metric] = asdict(stat_result)

        with open(self.output_dir / f"statistical_results_{timestamp}.json", 'w') as f:
            json.dump(statistical_json, f, indent=2, default=str)

        # Save report as text
        with open(self.output_dir / f"benchmark_report_{timestamp}.txt", 'w') as f:
            f.write(report)

        # Save summary CSV for easy analysis
        self._save_summary_csv(all_results, timestamp)

    def _save_summary_csv(self,
                         all_results: Dict[str, Dict[str, List[PerformanceMetrics]]],
                         timestamp: str):
        """Save summary statistics as CSV."""

        summary_data = []

        for controller_name, controller_results in all_results.items():
            for scenario_name, metrics_list in controller_results.items():

                # Calculate summary statistics for each metric
                if metrics_list:
                    sample_metrics = metrics_list[0]
                    metric_names = [field.name for field in sample_metrics.__dataclass_fields__]

                    for metric_name in metric_names:
                        values = [getattr(metric, metric_name) for metric in metrics_list]

                        summary_data.append({
                            'Controller': controller_name,
                            'Scenario': scenario_name,
                            'Metric': metric_name,
                            'Mean': np.mean(values),
                            'Std': np.std(values),
                            'Median': np.median(values),
                            'Min': np.min(values),
                            'Max': np.max(values),
                            'N': len(values)
                        })

        df = pd.DataFrame(summary_data)
        df.to_csv(self.output_dir / f"summary_statistics_{timestamp}.csv", index=False)

    def _get_benchmark_metadata(self) -> Dict[str, Any]:
        """Get benchmark metadata for reproducibility."""

        return {
            'timestamp': datetime.now().isoformat(),
            'n_monte_carlo': self.n_monte_carlo,
            'random_seed': self.random_seed,
            'parallel_jobs': self.parallel_jobs,
            'scenarios': [s.name for s in self.experimental_design.scenarios],
            'controllers': [c.value for c in ControllerType],
            'output_directory': str(self.output_dir)
        }

    def generate_visualization_plots(self,
                                   all_results: Dict[str, Dict[str, List[PerformanceMetrics]]]):
        """Generate visualization plots for benchmark results."""

        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")

        # Create plots directory
        plots_dir = self.output_dir / "plots"
        plots_dir.mkdir(exist_ok=True)

        # Generate plots for key metrics
        key_metrics = ['settling_time', 'chattering_index', 'control_energy']

        for metric_name in key_metrics:
            self._plot_metric_comparison(all_results, metric_name, plots_dir)

        # Generate overall performance heatmap
        self._plot_performance_heatmap(all_results, plots_dir)

    def _plot_metric_comparison(self,
                               all_results: Dict[str, Dict[str, List[PerformanceMetrics]]],
                               metric_name: str,
                               plots_dir: Path):
        """Plot comparison for a specific metric across scenarios."""

        # Prepare data for plotting
        plot_data = []

        for controller_name, controller_results in all_results.items():
            for scenario_name, metrics_list in controller_results.items():
                values = [getattr(metric, metric_name) for metric in metrics_list]

                for value in values:
                    plot_data.append({
                        'Controller': controller_name,
                        'Scenario': scenario_name,
                        'Value': value
                    })

        df = pd.DataFrame(plot_data)

        # Create box plot
        plt.figure(figsize=(15, 8))
        sns.boxplot(data=df, x='Scenario', y='Value', hue='Controller')
        plt.title(f'{metric_name.replace("_", " ").title()} Comparison Across Scenarios')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(plots_dir / f"{metric_name}_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_performance_heatmap(self,
                                 all_results: Dict[str, Dict[str, List[PerformanceMetrics]]],
                                 plots_dir: Path):
        """Plot performance heatmap showing relative rankings."""

        # Calculate mean performance for each controller-scenario combination
        performance_matrix = {}

        scenarios = list(next(iter(all_results.values())).keys())
        controllers = list(all_results.keys())

        key_metrics = ['settling_time', 'chattering_index', 'control_energy']

        for metric_name in key_metrics:
            matrix_data = []

            for controller in controllers:
                controller_row = []
                for scenario in scenarios:
                    if scenario in all_results[controller]:
                        values = [getattr(metric, metric_name)
                                for metric in all_results[controller][scenario]]
                        mean_value = np.mean(values)
                    else:
                        mean_value = np.nan
                    controller_row.append(mean_value)
                matrix_data.append(controller_row)

            # Create heatmap
            plt.figure(figsize=(12, 6))
            sns.heatmap(matrix_data,
                       xticklabels=scenarios,
                       yticklabels=controllers,
                       annot=True,
                       fmt='.3f',
                       cmap='RdYlBu_r')
            plt.title(f'{metric_name.replace("_", " ").title()} - Performance Heatmap')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(plots_dir / f"{metric_name}_heatmap.png", dpi=300, bbox_inches='tight')
            plt.close()


# Usage example
if __name__ == "__main__":
    # Create and run benchmark
    benchmark = BenchmarkRunner(
        output_dir="smc_benchmark_results",
        n_monte_carlo=50,  # Reduced for testing
        parallel_jobs=2,
        random_seed=42
    )

    # Run complete benchmark suite
    results = benchmark.run_complete_benchmark()

    # Generate visualizations
    benchmark.generate_visualization_plots(results['raw_results'])

    print("Benchmark completed! Check the output directory for results.")