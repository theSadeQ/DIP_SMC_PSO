#==========================================================================================\\\
#======================= src/analysis/validation/benchmarking.py ========================\\\
#==========================================================================================\\\

"""Benchmarking and comparison tools for analysis validation.

This module provides comprehensive benchmarking capabilities for comparing
analysis methods, controllers, and algorithms in control engineering applications.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any, Union, Callable
import numpy as np
from scipy import stats
import warnings
from dataclasses import dataclass, field
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

from ..core.interfaces import StatisticalValidator, AnalysisResult, AnalysisStatus, DataProtocol
from ..core.data_structures import StatisticalTestResult, ComparisonResult


@dataclass
class BenchmarkConfig:
    """Configuration for benchmarking."""
    # Basic benchmark parameters
    n_trials: int = 30
    confidence_level: float = 0.95
    significance_level: float = 0.05
    random_seed: Optional[int] = None

    # Performance metrics
    metrics_to_compare: List[str] = field(default_factory=lambda: ["performance", "robustness", "efficiency"])
    primary_metric: str = "performance"

    # Statistical testing
    use_paired_tests: bool = True
    correction_method: str = "bonferroni"  # "bonferroni", "holm", "fdr_bh", "none"
    effect_size_measure: str = "cohen_d"  # "cohen_d", "glass_delta", "hedges_g"

    # Computational benchmarking
    measure_computation_time: bool = True
    measure_memory_usage: bool = False
    parallel_execution: bool = True
    max_workers: Optional[int] = None

    # Robustness testing
    noise_levels: List[float] = field(default_factory=lambda: [0.0, 0.01, 0.05, 0.1])
    parameter_perturbations: List[float] = field(default_factory=lambda: [0.9, 0.95, 1.05, 1.1])

    # Report generation
    generate_plots: bool = True
    save_raw_data: bool = False
    output_format: str = "dict"  # "dict", "json", "csv", "latex"


class BenchmarkSuite(StatisticalValidator):
    """Comprehensive benchmarking and comparison framework."""

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        """Initialize benchmark suite.

        Parameters
        ----------
        config : BenchmarkConfig, optional
            Configuration for benchmarking
        """
        self.config = config or BenchmarkConfig()
        if self.config.max_workers is None:
            self.config.max_workers = min(4, multiprocessing.cpu_count())

        if self.config.random_seed is not None:
            np.random.seed(self.config.random_seed)

    @property
    def validation_methods(self) -> List[str]:
        """List of validation methods supported."""
        return [
            "performance_comparison",
            "robustness_comparison",
            "efficiency_comparison",
            "statistical_significance_testing",
            "effect_size_analysis",
            "ranking_analysis"
        ]

    def validate(self, data: Union[List[Dict[str, float]], np.ndarray], **kwargs) -> AnalysisResult:
        """Perform comprehensive benchmarking analysis.

        Parameters
        ----------
        data : Union[List[Dict[str, float]], np.ndarray]
            Data for benchmarking (can be results from multiple methods)
        **kwargs
            Additional parameters:
            - methods: List of methods/algorithms to compare
            - simulation_function: Function to run simulations
            - test_cases: Different test scenarios
            - baseline_method: Reference method for comparison

        Returns
        -------
        AnalysisResult
            Comprehensive benchmarking results
        """
        try:
            results = {}

            # Get methods to compare
            methods = kwargs.get('methods', [])
            simulation_function = kwargs.get('simulation_function')
            test_cases = kwargs.get('test_cases', [{}])  # Default single test case

            if not methods and simulation_function is None:
                return AnalysisResult(
                    status=AnalysisStatus.ERROR,
                    message="No methods or simulation function provided for benchmarking",
                    data={}
                )

            # Run benchmarks
            if simulation_function is not None:
                benchmark_results = self._run_simulation_benchmarks(methods, simulation_function, test_cases, **kwargs)
                results['simulation_benchmarks'] = benchmark_results
            else:
                # Analyze provided data
                data_results = self._analyze_provided_data(data, **kwargs)
                results['data_analysis'] = data_results

            # Performance comparison
            if "performance_comparison" in self.validation_methods:
                performance_comparison = self._perform_performance_comparison(results, **kwargs)
                results['performance_comparison'] = performance_comparison

            # Robustness comparison
            if "robustness_comparison" in self.validation_methods:
                robustness_comparison = self._perform_robustness_comparison(results, **kwargs)
                results['robustness_comparison'] = robustness_comparison

            # Statistical significance testing
            if "statistical_significance_testing" in self.validation_methods:
                significance_testing = self._perform_significance_testing(results, **kwargs)
                results['statistical_significance_testing'] = significance_testing

            # Effect size analysis
            if "effect_size_analysis" in self.validation_methods:
                effect_size_analysis = self._perform_effect_size_analysis(results, **kwargs)
                results['effect_size_analysis'] = effect_size_analysis

            # Ranking analysis
            if "ranking_analysis" in self.validation_methods:
                ranking_analysis = self._perform_ranking_analysis(results, **kwargs)
                results['ranking_analysis'] = ranking_analysis

            # Overall benchmark summary
            benchmark_summary = self._generate_benchmark_summary(results)
            results['benchmark_summary'] = benchmark_summary

            return AnalysisResult(
                status=AnalysisStatus.SUCCESS,
                message="Benchmarking completed successfully",
                data=results,
                metadata={
                    'validator': 'BenchmarkSuite',
                    'config': self.config.__dict__,
                    'n_methods': len(methods),
                    'n_test_cases': len(test_cases)
                }
            )

        except Exception as e:
            return AnalysisResult(
                status=AnalysisStatus.ERROR,
                message=f"Benchmarking failed: {str(e)}",
                data={'error_details': str(e)}
            )

    def _run_simulation_benchmarks(self, methods: List[Any], simulation_function: Callable,
                                  test_cases: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Run simulation benchmarks for all methods and test cases."""
        benchmark_results = {}

        for case_idx, test_case in enumerate(test_cases):
            case_name = test_case.get('name', f'test_case_{case_idx}')
            case_results = {}

            for method_idx, method in enumerate(methods):
                method_name = getattr(method, '__name__', f'method_{method_idx}')

                # Run trials for this method and test case
                method_results = self._run_method_trials(method, simulation_function, test_case, **kwargs)
                case_results[method_name] = method_results

            benchmark_results[case_name] = case_results

        return benchmark_results

    def _run_method_trials(self, method: Any, simulation_function: Callable,
                          test_case: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Run multiple trials for a single method."""
        trial_results = []
        computation_times = []
        memory_usages = []

        for trial in range(self.config.n_trials):
            trial_start_time = time.time()

            try:
                # Run simulation
                if self.config.measure_memory_usage:
                    import psutil
                    process = psutil.Process()
                    mem_before = process.memory_info().rss

                result = simulation_function(method, test_case, trial=trial, **kwargs)

                if self.config.measure_memory_usage:
                    mem_after = process.memory_info().rss
                    memory_usages.append(mem_after - mem_before)

                trial_end_time = time.time()
                computation_times.append(trial_end_time - trial_start_time)

                # Store result
                trial_results.append(result)

            except Exception as e:
                warnings.warn(f"Trial {trial} failed for method {getattr(method, '__name__', 'unknown')}: {e}")
                trial_results.append(None)

        # Analyze trial results
        valid_results = [r for r in trial_results if r is not None]

        if not valid_results:
            return {'error': 'All trials failed'}

        # Extract metrics
        metrics_analysis = self._analyze_trial_metrics(valid_results)

        # Computational performance
        computational_analysis = {
            'mean_computation_time': float(np.mean(computation_times)),
            'std_computation_time': float(np.std(computation_times)),
            'median_computation_time': float(np.median(computation_times)),
            'total_computation_time': float(np.sum(computation_times))
        }

        if memory_usages:
            computational_analysis.update({
                'mean_memory_usage': float(np.mean(memory_usages)),
                'peak_memory_usage': float(np.max(memory_usages))
            })

        return {
            'trial_results': trial_results if self.config.save_raw_data else None,
            'n_successful_trials': len(valid_results),
            'n_failed_trials': len(trial_results) - len(valid_results),
            'success_rate': len(valid_results) / len(trial_results),
            'metrics_analysis': metrics_analysis,
            'computational_analysis': computational_analysis
        }

    def _analyze_trial_metrics(self, trial_results: List[Any]) -> Dict[str, Any]:
        """Analyze metrics from trial results."""
        if not trial_results:
            return {}

        # Handle different result formats
        if isinstance(trial_results[0], dict):
            # Results are dictionaries of metrics
            metric_names = set()
            for result in trial_results:
                metric_names.update(result.keys())

            metrics_analysis = {}
            for metric_name in metric_names:
                values = []
                for result in trial_results:
                    if metric_name in result and isinstance(result[metric_name], (int, float)):
                        if np.isfinite(result[metric_name]):
                            values.append(result[metric_name])

                if values:
                    metrics_analysis[metric_name] = self._compute_metric_statistics(values)

        elif isinstance(trial_results[0], (int, float)):
            # Results are scalar values
            values = [r for r in trial_results if np.isfinite(r)]
            metrics_analysis = {'primary_metric': self._compute_metric_statistics(values)}

        else:
            # Try to extract numeric values
            metrics_analysis = {'note': 'Could not analyze non-numeric results'}

        return metrics_analysis

    def _compute_metric_statistics(self, values: List[float]) -> Dict[str, float]:
        """Compute comprehensive statistics for a metric."""
        if not values:
            return {}

        values_array = np.array(values)

        # Basic statistics
        stats_dict = {
            'count': len(values),
            'mean': float(np.mean(values_array)),
            'std': float(np.std(values_array)),
            'median': float(np.median(values_array)),
            'min': float(np.min(values_array)),
            'max': float(np.max(values_array)),
            'q25': float(np.percentile(values_array, 25)),
            'q75': float(np.percentile(values_array, 75)),
            'iqr': float(np.percentile(values_array, 75) - np.percentile(values_array, 25))
        }

        # Confidence interval for mean
        if len(values) > 1:
            alpha = 1 - self.config.confidence_level
            t_value = stats.t.ppf(1 - alpha/2, len(values) - 1)
            margin_error = t_value * stats_dict['std'] / np.sqrt(len(values))

            stats_dict['confidence_interval'] = {
                'lower': stats_dict['mean'] - margin_error,
                'upper': stats_dict['mean'] + margin_error,
                'confidence_level': self.config.confidence_level
            }

        return stats_dict

    def _analyze_provided_data(self, data: Union[List[Dict[str, float]], np.ndarray], **kwargs) -> Dict[str, Any]:
        """Analyze provided benchmark data."""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            # Data is list of dictionaries
            method_data = {}

            # Group by method if method identifier is present
            method_key = kwargs.get('method_key', 'method')

            if method_key in data[0]:
                for record in data:
                    method_name = record[method_key]
                    if method_name not in method_data:
                        method_data[method_name] = []
                    method_data[method_name].append(record)
            else:
                # Assume all data is from one method
                method_data['method_0'] = data

            # Analyze each method's data
            analysis_results = {}
            for method_name, method_records in method_data.items():
                analysis_results[method_name] = self._analyze_trial_metrics(method_records)

            return analysis_results

        else:
            # Handle array data
            return {'method_0': self._compute_metric_statistics(data.flatten().tolist())}

    def _perform_performance_comparison(self, results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Perform performance comparison between methods."""
        comparison_results = {}

        # Extract performance data for each method
        method_performance = self._extract_method_performance(results)

        if len(method_performance) < 2:
            return {'error': 'Need at least 2 methods for comparison'}

        # Pairwise comparisons
        method_names = list(method_performance.keys())
        pairwise_comparisons = {}

        for i, method_a in enumerate(method_names):
            for j, method_b in enumerate(method_names):
                if i < j:  # Avoid duplicate comparisons
                    comparison_key = f"{method_a}_vs_{method_b}"

                    # Compare on primary metric
                    primary_metric = self.config.primary_metric
                    perf_a = method_performance[method_a].get(primary_metric, {})
                    perf_b = method_performance[method_b].get(primary_metric, {})

                    if 'mean' in perf_a and 'mean' in perf_b:
                        comparison = self._compare_two_methods(perf_a, perf_b, method_a, method_b)
                        pairwise_comparisons[comparison_key] = comparison

        # Overall ranking
        ranking = self._rank_methods_by_performance(method_performance)

        return {
            'pairwise_comparisons': pairwise_comparisons,
            'method_ranking': ranking,
            'performance_summary': method_performance
        }

    def _perform_robustness_comparison(self, results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Perform robustness comparison between methods."""
        # Extract standard deviation and range information
        robustness_metrics = {}

        method_performance = self._extract_method_performance(results)

        for method_name, method_data in method_performance.items():
            for metric_name, metric_data in method_data.items():
                if isinstance(metric_data, dict):
                    # Coefficient of variation as robustness measure
                    mean_val = metric_data.get('mean', 0)
                    std_val = metric_data.get('std', 0)

                    if mean_val != 0:
                        cv = std_val / abs(mean_val)
                    else:
                        cv = np.inf

                    # Range-based robustness
                    min_val = metric_data.get('min', 0)
                    max_val = metric_data.get('max', 0)
                    range_val = max_val - min_val

                    if method_name not in robustness_metrics:
                        robustness_metrics[method_name] = {}

                    robustness_metrics[method_name][metric_name] = {
                        'coefficient_of_variation': float(cv),
                        'range': float(range_val),
                        'std_normalized': float(std_val),
                        'robustness_score': float(1.0 / (1.0 + cv))  # Higher is more robust
                    }

        # Rank by robustness
        if robustness_metrics:
            # Use primary metric for ranking
            primary_metric = self.config.primary_metric
            robustness_ranking = []

            for method_name, method_robustness in robustness_metrics.items():
                if primary_metric in method_robustness:
                    robustness_score = method_robustness[primary_metric]['robustness_score']
                    robustness_ranking.append((method_name, robustness_score))

            robustness_ranking.sort(key=lambda x: x[1], reverse=True)

            return {
                'robustness_metrics': robustness_metrics,
                'robustness_ranking': robustness_ranking
            }
        else:
            return {'error': 'Could not compute robustness metrics'}

    def _perform_significance_testing(self, results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Perform statistical significance testing between methods."""
        # Extract raw performance data
        method_raw_data = self._extract_raw_performance_data(results)

        if len(method_raw_data) < 2:
            return {'error': 'Need at least 2 methods for significance testing'}

        # Pairwise statistical tests
        method_names = list(method_raw_data.keys())
        test_results = {}

        for i, method_a in enumerate(method_names):
            for j, method_b in enumerate(method_names):
                if i < j:
                    comparison_key = f"{method_a}_vs_{method_b}"

                    # Get data for primary metric
                    primary_metric = self.config.primary_metric
                    data_a = method_raw_data[method_a].get(primary_metric, [])
                    data_b = method_raw_data[method_b].get(primary_metric, [])

                    if len(data_a) > 0 and len(data_b) > 0:
                        test_result = self._perform_statistical_test(data_a, data_b, method_a, method_b)
                        test_results[comparison_key] = test_result

        # Multiple comparison correction
        if len(test_results) > 1:
            corrected_results = self._apply_multiple_comparison_correction(test_results)
        else:
            corrected_results = test_results

        return {
            'uncorrected_tests': test_results,
            'corrected_tests': corrected_results,
            'correction_method': self.config.correction_method
        }

    def _perform_effect_size_analysis(self, results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Perform effect size analysis between methods."""
        method_raw_data = self._extract_raw_performance_data(results)

        if len(method_raw_data) < 2:
            return {'error': 'Need at least 2 methods for effect size analysis'}

        method_names = list(method_raw_data.keys())
        effect_sizes = {}

        for i, method_a in enumerate(method_names):
            for j, method_b in enumerate(method_names):
                if i < j:
                    comparison_key = f"{method_a}_vs_{method_b}"

                    # Get data for primary metric
                    primary_metric = self.config.primary_metric
                    data_a = method_raw_data[method_a].get(primary_metric, [])
                    data_b = method_raw_data[method_b].get(primary_metric, [])

                    if len(data_a) > 0 and len(data_b) > 0:
                        effect_size = self._compute_effect_size(data_a, data_b)
                        effect_sizes[comparison_key] = effect_size

        return effect_sizes

    def _perform_ranking_analysis(self, results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Perform comprehensive ranking analysis."""
        # Multi-criteria ranking
        method_performance = self._extract_method_performance(results)

        if not method_performance:
            return {'error': 'No performance data available for ranking'}

        # Rank by each metric
        metric_rankings = {}
        all_metrics = set()

        for method_data in method_performance.values():
            all_metrics.update(method_data.keys())

        for metric_name in all_metrics:
            metric_values = []
            for method_name, method_data in method_performance.items():
                if metric_name in method_data and 'mean' in method_data[metric_name]:
                    metric_values.append((method_name, method_data[metric_name]['mean']))

            # Sort by metric value (assuming higher is better for now)
            metric_values.sort(key=lambda x: x[1], reverse=True)
            metric_rankings[metric_name] = metric_values

        # Aggregate ranking (Borda count)
        borda_scores = {}
        n_methods = len(method_performance)

        for method_name in method_performance.keys():
            borda_scores[method_name] = 0

        for metric_name, ranking in metric_rankings.items():
            for rank, (method_name, _) in enumerate(ranking):
                borda_scores[method_name] += (n_methods - rank - 1)

        # Final ranking
        final_ranking = sorted(borda_scores.items(), key=lambda x: x[1], reverse=True)

        return {
            'metric_rankings': metric_rankings,
            'borda_scores': borda_scores,
            'final_ranking': final_ranking,
            'ranking_method': 'borda_count'
        }

    def _extract_method_performance(self, results: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract method performance data from results."""
        method_performance = {}

        # Look for performance data in different result structures
        if 'simulation_benchmarks' in results:
            sim_results = results['simulation_benchmarks']
            for test_case, case_results in sim_results.items():
                for method_name, method_data in case_results.items():
                    if isinstance(method_data, dict) and 'metrics_analysis' in method_data:
                        method_performance[method_name] = method_data['metrics_analysis']

        elif 'data_analysis' in results:
            method_performance = results['data_analysis']

        return method_performance

    def _extract_raw_performance_data(self, results: Dict[str, Any]) -> Dict[str, Dict[str, List[float]]]:
        """Extract raw performance data for statistical testing."""
        # This would extract the actual trial values rather than summary statistics
        # Simplified implementation - would need access to raw trial data
        return {}

    def _compare_two_methods(self, perf_a: Dict[str, float], perf_b: Dict[str, float],
                           method_a: str, method_b: str) -> Dict[str, Any]:
        """Compare two methods on a single metric."""
        mean_a = perf_a['mean']
        mean_b = perf_b['mean']
        std_a = perf_a.get('std', 0)
        std_b = perf_b.get('std', 0)

        # Relative improvement
        if mean_b != 0:
            relative_improvement = (mean_a - mean_b) / abs(mean_b) * 100
        else:
            relative_improvement = 0

        # Confidence intervals overlap check
        ci_a = perf_a.get('confidence_interval', {})
        ci_b = perf_b.get('confidence_interval', {})

        overlap = False
        if 'lower' in ci_a and 'upper' in ci_a and 'lower' in ci_b and 'upper' in ci_b:
            overlap = not (ci_a['upper'] < ci_b['lower'] or ci_b['upper'] < ci_a['lower'])

        return {
            'method_a': method_a,
            'method_b': method_b,
            'mean_a': mean_a,
            'mean_b': mean_b,
            'difference': mean_a - mean_b,
            'relative_improvement_percent': relative_improvement,
            'better_method': method_a if mean_a > mean_b else method_b,
            'confidence_intervals_overlap': overlap
        }

    def _rank_methods_by_performance(self, method_performance: Dict[str, Dict[str, Any]]) -> List[Tuple[str, float]]:
        """Rank methods by performance on primary metric."""
        primary_metric = self.config.primary_metric
        method_scores = []

        for method_name, method_data in method_performance.items():
            if primary_metric in method_data and 'mean' in method_data[primary_metric]:
                score = method_data[primary_metric]['mean']
                method_scores.append((method_name, score))

        # Sort by score (assuming higher is better)
        method_scores.sort(key=lambda x: x[1], reverse=True)

        return method_scores

    def _perform_statistical_test(self, data_a: List[float], data_b: List[float],
                                 method_a: str, method_b: str) -> Dict[str, Any]:
        """Perform statistical test between two methods."""
        data_a = np.array(data_a)
        data_b = np.array(data_b)

        # Choose appropriate test
        if self.config.use_paired_tests and len(data_a) == len(data_b):
            # Paired t-test
            statistic, p_value = stats.ttest_rel(data_a, data_b)
            test_name = "Paired t-test"
        else:
            # Independent t-test (Welch's by default)
            statistic, p_value = stats.ttest_ind(data_a, data_b, equal_var=False)
            test_name = "Welch's t-test"

        # Mann-Whitney U test (non-parametric alternative)
        u_statistic, u_p_value = stats.mannwhitneyu(data_a, data_b, alternative='two-sided')

        return {
            'test_name': test_name,
            'statistic': float(statistic),
            'p_value': float(p_value),
            'significant': bool(p_value < self.config.significance_level),
            'mann_whitney_u': float(u_statistic),
            'mann_whitney_p': float(u_p_value),
            'mann_whitney_significant': bool(u_p_value < self.config.significance_level)
        }

    def _apply_multiple_comparison_correction(self, test_results: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Apply multiple comparison correction to p-values."""
        p_values = [result['p_value'] for result in test_results.values()]

        if self.config.correction_method == "bonferroni":
            corrected_p_values = [p * len(p_values) for p in p_values]
        elif self.config.correction_method == "holm":
            corrected_p_values = self._holm_correction(p_values)
        elif self.config.correction_method == "fdr_bh":
            corrected_p_values = self._benjamini_hochberg_correction(p_values)
        else:
            corrected_p_values = p_values

        # Update test results with corrected p-values
        corrected_results = {}
        for i, (comparison_key, result) in enumerate(test_results.items()):
            corrected_result = result.copy()
            corrected_result['corrected_p_value'] = float(min(1.0, corrected_p_values[i]))
            corrected_result['corrected_significant'] = bool(corrected_result['corrected_p_value'] < self.config.significance_level)
            corrected_results[comparison_key] = corrected_result

        return corrected_results

    def _holm_correction(self, p_values: List[float]) -> List[float]:
        """Apply Holm-Bonferroni correction."""
        sorted_indices = np.argsort(p_values)
        sorted_p_values = np.array(p_values)[sorted_indices]
        n = len(p_values)

        corrected = np.zeros(n)
        for i, p in enumerate(sorted_p_values):
            corrected[i] = min(1.0, p * (n - i))

        # Ensure monotonicity
        for i in range(1, n):
            corrected[i] = max(corrected[i], corrected[i-1])

        # Restore original order
        original_order_corrected = np.zeros(n)
        original_order_corrected[sorted_indices] = corrected

        return original_order_corrected.tolist()

    def _benjamini_hochberg_correction(self, p_values: List[float]) -> List[float]:
        """Apply Benjamini-Hochberg FDR correction."""
        sorted_indices = np.argsort(p_values)
        sorted_p_values = np.array(p_values)[sorted_indices]
        n = len(p_values)

        corrected = np.zeros(n)
        for i in range(n-1, -1, -1):
            corrected[i] = min(1.0, sorted_p_values[i] * n / (i + 1))
            if i < n - 1:
                corrected[i] = min(corrected[i], corrected[i + 1])

        # Restore original order
        original_order_corrected = np.zeros(n)
        original_order_corrected[sorted_indices] = corrected

        return original_order_corrected.tolist()

    def _compute_effect_size(self, data_a: List[float], data_b: List[float]) -> Dict[str, float]:
        """Compute effect size between two groups."""
        data_a = np.array(data_a)
        data_b = np.array(data_b)

        mean_a = np.mean(data_a)
        mean_b = np.mean(data_b)
        std_a = np.std(data_a, ddof=1)
        std_b = np.std(data_b, ddof=1)

        n_a = len(data_a)
        n_b = len(data_b)

        effect_sizes = {}

        # Cohen's d
        if self.config.effect_size_measure == "cohen_d":
            pooled_std = np.sqrt(((n_a - 1) * std_a**2 + (n_b - 1) * std_b**2) / (n_a + n_b - 2))
            cohens_d = (mean_a - mean_b) / pooled_std if pooled_std > 0 else 0
            effect_sizes['cohens_d'] = float(cohens_d)

        # Glass's Delta
        elif self.config.effect_size_measure == "glass_delta":
            glass_delta = (mean_a - mean_b) / std_b if std_b > 0 else 0
            effect_sizes['glass_delta'] = float(glass_delta)

        # Hedges' g
        elif self.config.effect_size_measure == "hedges_g":
            pooled_std = np.sqrt(((n_a - 1) * std_a**2 + (n_b - 1) * std_b**2) / (n_a + n_b - 2))
            if pooled_std > 0:
                cohens_d = (mean_a - mean_b) / pooled_std
                correction_factor = 1 - (3 / (4 * (n_a + n_b) - 9))
                hedges_g = cohens_d * correction_factor
            else:
                hedges_g = 0
            effect_sizes['hedges_g'] = float(hedges_g)

        # Interpretation
        primary_effect_size = list(effect_sizes.values())[0] if effect_sizes else 0
        effect_sizes['interpretation'] = self._interpret_effect_size(abs(primary_effect_size))

        return effect_sizes

    def _interpret_effect_size(self, effect_size: float) -> str:
        """Interpret effect size magnitude."""
        if effect_size < 0.2:
            return "negligible"
        elif effect_size < 0.5:
            return "small"
        elif effect_size < 0.8:
            return "medium"
        else:
            return "large"

    def _generate_benchmark_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall benchmark summary."""
        summary = {
            'benchmark_completed': True,
            'best_performing_method': None,
            'most_robust_method': None,
            'key_findings': [],
            'recommendations': []
        }

        # Find best performing method
        if 'performance_comparison' in results:
            perf_comparison = results['performance_comparison']
            if 'method_ranking' in perf_comparison and perf_comparison['method_ranking']:
                summary['best_performing_method'] = perf_comparison['method_ranking'][0][0]

        # Find most robust method
        if 'robustness_comparison' in results:
            robustness_comparison = results['robustness_comparison']
            if 'robustness_ranking' in robustness_comparison and robustness_comparison['robustness_ranking']:
                summary['most_robust_method'] = robustness_comparison['robustness_ranking'][0][0]

        # Generate key findings
        if 'statistical_significance_testing' in results:
            sig_testing = results['statistical_significance_testing']
            if 'corrected_tests' in sig_testing:
                significant_differences = []
                for comparison, test_result in sig_testing['corrected_tests'].items():
                    if test_result.get('corrected_significant', False):
                        significant_differences.append(comparison)

                if significant_differences:
                    summary['key_findings'].append(f"Significant differences found in {len(significant_differences)} comparisons")
                else:
                    summary['key_findings'].append("No significant differences found between methods")

        # Generate recommendations
        if summary['best_performing_method'] and summary['most_robust_method']:
            if summary['best_performing_method'] == summary['most_robust_method']:
                summary['recommendations'].append(f"Recommend {summary['best_performing_method']} for best performance and robustness")
            else:
                summary['recommendations'].append(f"Trade-off between performance ({summary['best_performing_method']}) and robustness ({summary['most_robust_method']})")

        return summary


def create_benchmark_suite(config: Optional[Dict[str, Any]] = None) -> BenchmarkSuite:
    """Factory function to create benchmark suite.

    Parameters
    ----------
    config : Dict[str, Any], optional
        Configuration parameters

    Returns
    -------
    BenchmarkSuite
        Configured benchmark suite
    """
    if config is not None:
        benchmark_config = BenchmarkConfig(**config)
    else:
        benchmark_config = BenchmarkConfig()

    return BenchmarkSuite(benchmark_config)