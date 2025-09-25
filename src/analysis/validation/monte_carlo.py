#==========================================================================================\\\
#======================= src/analysis/validation/monte_carlo.py =========================\\\
#==========================================================================================\\\

"""Monte Carlo analysis tools for validation and uncertainty quantification.

This module provides comprehensive Monte Carlo simulation capabilities for
analyzing system behavior under uncertainty, validating controller performance,
and quantifying confidence in analysis results.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any, Union, Callable
import numpy as np
from scipy import stats
import warnings
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing
from functools import partial

from ..core.interfaces import StatisticalValidator, AnalysisResult, AnalysisStatus, DataProtocol
from ..core.data_structures import ConfidenceInterval, StatisticalTestResult


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo analysis."""
    # Basic simulation parameters
    n_samples: int = 1000
    confidence_level: float = 0.95
    random_seed: Optional[int] = None

    # Parallel processing
    parallel_processing: bool = True
    max_workers: Optional[int] = None
    chunk_size: Optional[int] = None

    # Sampling methods
    sampling_method: str = "random"  # "random", "latin_hypercube", "sobol", "halton"
    antithetic_variates: bool = False
    control_variates: bool = False

    # Convergence criteria
    convergence_tolerance: float = 0.01
    min_samples: int = 100
    max_samples: int = 10000
    convergence_window: int = 50

    # Bootstrap parameters
    bootstrap_samples: int = 1000
    bootstrap_confidence_level: float = 0.95

    # Sensitivity analysis
    sensitivity_analysis: bool = True
    sensitivity_method: str = "sobol"  # "sobol", "morris", "fast"

    # Output options
    save_all_samples: bool = False
    compute_percentiles: List[float] = field(default_factory=lambda: [5, 25, 50, 75, 95])


class MonteCarloAnalyzer(StatisticalValidator):
    """Monte Carlo analyzer for uncertainty quantification and validation."""

    def __init__(self, config: Optional[MonteCarloConfig] = None):
        """Initialize Monte Carlo analyzer.

        Parameters
        ----------
        config : MonteCarloConfig, optional
            Configuration for Monte Carlo analysis
        """
        self.config = config or MonteCarloConfig()
        if self.config.max_workers is None:
            self.config.max_workers = min(4, multiprocessing.cpu_count())

        # Set random seed for reproducibility
        if self.config.random_seed is not None:
            np.random.seed(self.config.random_seed)

    @property
    def validation_methods(self) -> List[str]:
        """List of validation methods supported."""
        return [
            "uncertainty_propagation",
            "sensitivity_analysis",
            "robustness_analysis",
            "confidence_intervals",
            "distribution_fitting",
            "tail_risk_analysis"
        ]

    def validate(self, data: Union[List[Dict[str, float]], np.ndarray], **kwargs) -> AnalysisResult:
        """Perform Monte Carlo validation analysis.

        Parameters
        ----------
        data : Union[List[Dict[str, float]], np.ndarray]
            Data for Monte Carlo analysis
        **kwargs
            Additional parameters:
            - simulation_function: Function to simulate system behavior
            - parameter_distributions: Dictionary of parameter uncertainty distributions
            - target_metrics: List of metrics to analyze
            - validation_data: Reference data for validation

        Returns
        -------
        AnalysisResult
            Comprehensive Monte Carlo analysis results
        """
        try:
            results = {}

            # Check if this is a Monte Carlo simulation or analysis of existing data
            simulation_function = kwargs.get('simulation_function')
            parameter_distributions = kwargs.get('parameter_distributions', {})

            if simulation_function is not None:
                # Perform Monte Carlo simulation
                mc_results = self._perform_monte_carlo_simulation(
                    simulation_function, parameter_distributions, **kwargs
                )
                results['monte_carlo_simulation'] = mc_results
            else:
                # Analyze existing data with Monte Carlo methods
                data_analysis = self._analyze_data_with_monte_carlo(data, **kwargs)
                results['data_analysis'] = data_analysis

            # Bootstrap analysis
            bootstrap_results = self._perform_bootstrap_analysis(data, **kwargs)
            results['bootstrap_analysis'] = bootstrap_results

            # Sensitivity analysis (if enabled)
            if self.config.sensitivity_analysis and parameter_distributions:
                sensitivity_results = self._perform_sensitivity_analysis(
                    simulation_function, parameter_distributions, **kwargs
                )
                results['sensitivity_analysis'] = sensitivity_results

            # Distribution analysis
            distribution_results = self._analyze_distributions(data, **kwargs)
            results['distribution_analysis'] = distribution_results

            # Risk analysis
            risk_results = self._perform_risk_analysis(data, **kwargs)
            results['risk_analysis'] = risk_results

            # Validation summary
            validation_summary = self._generate_validation_summary(results)
            results['validation_summary'] = validation_summary

            return AnalysisResult(
                status=AnalysisStatus.SUCCESS,
                message="Monte Carlo validation completed successfully",
                data=results,
                metadata={
                    'analyzer': 'MonteCarloAnalyzer',
                    'config': self.config.__dict__,
                    'n_samples': self.config.n_samples
                }
            )

        except Exception as e:
            return AnalysisResult(
                status=AnalysisStatus.ERROR,
                message=f"Monte Carlo validation failed: {str(e)}",
                data={'error_details': str(e)}
            )

    def _perform_monte_carlo_simulation(self, simulation_function: Callable,
                                      parameter_distributions: Dict[str, Any],
                                      **kwargs) -> Dict[str, Any]:
        """Perform Monte Carlo simulation."""
        # Generate parameter samples
        parameter_samples = self._generate_parameter_samples(parameter_distributions)

        # Run simulations
        simulation_results = self._run_simulations(simulation_function, parameter_samples, **kwargs)

        # Analyze results
        analysis_results = self._analyze_simulation_results(simulation_results)

        # Convergence analysis
        convergence_results = self._analyze_convergence(simulation_results)

        return {
            'parameter_samples': parameter_samples if self.config.save_all_samples else None,
            'simulation_results': simulation_results if self.config.save_all_samples else None,
            'statistical_summary': analysis_results,
            'convergence_analysis': convergence_results,
            'n_successful_simulations': len([r for r in simulation_results if r is not None])
        }

    def _generate_parameter_samples(self, parameter_distributions: Dict[str, Any]) -> List[Dict[str, float]]:
        """Generate parameter samples according to specified distributions."""
        if self.config.sampling_method == "latin_hypercube":
            return self._latin_hypercube_sampling(parameter_distributions)
        elif self.config.sampling_method == "sobol":
            return self._sobol_sampling(parameter_distributions)
        elif self.config.sampling_method == "halton":
            return self._halton_sampling(parameter_distributions)
        else:
            return self._random_sampling(parameter_distributions)

    def _random_sampling(self, parameter_distributions: Dict[str, Any]) -> List[Dict[str, float]]:
        """Generate random samples."""
        samples = []

        for _ in range(self.config.n_samples):
            sample = {}
            for param_name, distribution_info in parameter_distributions.items():
                sample[param_name] = self._sample_from_distribution(distribution_info)
            samples.append(sample)

        # Apply antithetic variates if enabled
        if self.config.antithetic_variates:
            antithetic_samples = []
            for sample in samples[:len(samples)//2]:
                antithetic_sample = {}
                for param_name, value in sample.items():
                    dist_info = parameter_distributions[param_name]
                    # Generate antithetic variate
                    antithetic_sample[param_name] = self._generate_antithetic_variate(value, dist_info)
                antithetic_samples.append(antithetic_sample)
            samples.extend(antithetic_samples)

        return samples

    def _latin_hypercube_sampling(self, parameter_distributions: Dict[str, Any]) -> List[Dict[str, float]]:
        """Latin Hypercube Sampling for better space coverage."""
        n_params = len(parameter_distributions)
        param_names = list(parameter_distributions.keys())

        # Generate LHS matrix
        intervals = np.arange(0, self.config.n_samples + 1) / self.config.n_samples
        lhs_matrix = np.zeros((self.config.n_samples, n_params))

        for i in range(n_params):
            # Random permutation of intervals
            permuted_intervals = np.random.permutation(self.config.n_samples)
            # Random values within each interval
            random_values = np.random.uniform(0, 1, self.config.n_samples)
            lhs_matrix[:, i] = (permuted_intervals + random_values) / self.config.n_samples

        # Transform to parameter distributions
        samples = []
        for i in range(self.config.n_samples):
            sample = {}
            for j, param_name in enumerate(param_names):
                distribution_info = parameter_distributions[param_name]
                uniform_value = lhs_matrix[i, j]
                sample[param_name] = self._inverse_transform_sample(uniform_value, distribution_info)
            samples.append(sample)

        return samples

    def _sobol_sampling(self, parameter_distributions: Dict[str, Any]) -> List[Dict[str, float]]:
        """Sobol sequence sampling (simplified implementation)."""
        # Simplified Sobol - in practice would use scipy.stats.qmc
        param_names = list(parameter_distributions.keys())
        n_params = len(param_names)

        # Generate quasi-random sequences (simplified)
        samples = []
        for i in range(self.config.n_samples):
            sample = {}
            for j, param_name in enumerate(param_names):
                # Simple van der Corput sequence
                uniform_value = self._van_der_corput_sequence(i, 2 + j)
                distribution_info = parameter_distributions[param_name]
                sample[param_name] = self._inverse_transform_sample(uniform_value, distribution_info)
            samples.append(sample)

        return samples

    def _halton_sampling(self, parameter_distributions: Dict[str, Any]) -> List[Dict[str, float]]:
        """Halton sequence sampling."""
        param_names = list(parameter_distributions.keys())
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]  # First 10 primes

        samples = []
        for i in range(self.config.n_samples):
            sample = {}
            for j, param_name in enumerate(param_names):
                prime = primes[j % len(primes)]
                uniform_value = self._van_der_corput_sequence(i + 1, prime)
                distribution_info = parameter_distributions[param_name]
                sample[param_name] = self._inverse_transform_sample(uniform_value, distribution_info)
            samples.append(sample)

        return samples

    def _sample_from_distribution(self, distribution_info: Dict[str, Any]) -> float:
        """Sample from a distribution specification."""
        dist_type = distribution_info.get('type', 'normal')

        if dist_type == 'normal':
            mean = distribution_info.get('mean', 0.0)
            std = distribution_info.get('std', 1.0)
            return np.random.normal(mean, std)

        elif dist_type == 'uniform':
            low = distribution_info.get('low', 0.0)
            high = distribution_info.get('high', 1.0)
            return np.random.uniform(low, high)

        elif dist_type == 'beta':
            alpha = distribution_info.get('alpha', 2.0)
            beta = distribution_info.get('beta', 2.0)
            return np.random.beta(alpha, beta)

        elif dist_type == 'gamma':
            shape = distribution_info.get('shape', 2.0)
            scale = distribution_info.get('scale', 1.0)
            return np.random.gamma(shape, scale)

        elif dist_type == 'lognormal':
            mean = distribution_info.get('mean', 0.0)
            sigma = distribution_info.get('sigma', 1.0)
            return np.random.lognormal(mean, sigma)

        else:
            warnings.warn(f"Unknown distribution type: {dist_type}. Using normal(0,1).")
            return np.random.normal(0, 1)

    def _inverse_transform_sample(self, uniform_value: float, distribution_info: Dict[str, Any]) -> float:
        """Transform uniform sample to target distribution using inverse CDF."""
        dist_type = distribution_info.get('type', 'normal')

        if dist_type == 'normal':
            mean = distribution_info.get('mean', 0.0)
            std = distribution_info.get('std', 1.0)
            return stats.norm.ppf(uniform_value, mean, std)

        elif dist_type == 'uniform':
            low = distribution_info.get('low', 0.0)
            high = distribution_info.get('high', 1.0)
            return stats.uniform.ppf(uniform_value, low, high - low)

        elif dist_type == 'beta':
            alpha = distribution_info.get('alpha', 2.0)
            beta = distribution_info.get('beta', 2.0)
            return stats.beta.ppf(uniform_value, alpha, beta)

        elif dist_type == 'gamma':
            shape = distribution_info.get('shape', 2.0)
            scale = distribution_info.get('scale', 1.0)
            return stats.gamma.ppf(uniform_value, shape, scale=scale)

        elif dist_type == 'lognormal':
            mean = distribution_info.get('mean', 0.0)
            sigma = distribution_info.get('sigma', 1.0)
            return stats.lognorm.ppf(uniform_value, sigma, scale=np.exp(mean))

        else:
            return stats.norm.ppf(uniform_value, 0, 1)

    def _van_der_corput_sequence(self, n: int, base: int) -> float:
        """Generate van der Corput sequence value."""
        vdc = 0.0
        f = 1.0 / base
        i = n

        while i > 0:
            vdc += f * (i % base)
            i //= base
            f /= base

        return vdc

    def _generate_antithetic_variate(self, value: float, distribution_info: Dict[str, Any]) -> float:
        """Generate antithetic variate for variance reduction."""
        # Simplified antithetic variate generation
        dist_type = distribution_info.get('type', 'normal')

        if dist_type == 'normal':
            mean = distribution_info.get('mean', 0.0)
            return 2 * mean - value

        elif dist_type == 'uniform':
            low = distribution_info.get('low', 0.0)
            high = distribution_info.get('high', 1.0)
            return low + high - value

        else:
            # For other distributions, use reflection around median
            return -value

    def _run_simulations(self, simulation_function: Callable,
                        parameter_samples: List[Dict[str, float]],
                        **kwargs) -> List[Any]:
        """Run Monte Carlo simulations."""
        if self.config.parallel_processing and self.config.max_workers > 1:
            return self._run_simulations_parallel(simulation_function, parameter_samples, **kwargs)
        else:
            return self._run_simulations_sequential(simulation_function, parameter_samples, **kwargs)

    def _run_simulations_sequential(self, simulation_function: Callable,
                                   parameter_samples: List[Dict[str, float]],
                                   **kwargs) -> List[Any]:
        """Run simulations sequentially."""
        results = []

        for i, params in enumerate(parameter_samples):
            try:
                result = simulation_function(params, **kwargs)
                results.append(result)
            except Exception as e:
                warnings.warn(f"Simulation {i} failed: {e}")
                results.append(None)

        return results

    def _run_simulations_parallel(self, simulation_function: Callable,
                                 parameter_samples: List[Dict[str, float]],
                                 **kwargs) -> List[Any]:
        """Run simulations in parallel."""
        # Create partial function with fixed kwargs
        sim_func = partial(self._safe_simulation_wrapper, simulation_function, **kwargs)

        chunk_size = self.config.chunk_size or max(1, len(parameter_samples) // (self.config.max_workers * 4))

        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            results = list(executor.map(sim_func, parameter_samples, chunksize=chunk_size))

        return results

    def _safe_simulation_wrapper(self, simulation_function: Callable, params: Dict[str, float], **kwargs) -> Any:
        """Wrapper for safe simulation execution."""
        try:
            return simulation_function(params, **kwargs)
        except Exception as e:
            warnings.warn(f"Simulation failed with params {params}: {e}")
            return None

    def _analyze_simulation_results(self, results: List[Any]) -> Dict[str, Any]:
        """Analyze Monte Carlo simulation results."""
        valid_results = [r for r in results if r is not None]

        if not valid_results:
            return {'error': 'No valid simulation results'}

        # Extract numeric values
        if isinstance(valid_results[0], dict):
            # Results are dictionaries of metrics
            analysis = {}
            for key in valid_results[0].keys():
                values = [r[key] for r in valid_results if key in r and np.isfinite(r[key])]
                if values:
                    analysis[key] = self._compute_statistical_summary(values)
        else:
            # Results are scalar values
            values = [r for r in valid_results if np.isfinite(r)]
            analysis = self._compute_statistical_summary(values)

        return analysis

    def _compute_statistical_summary(self, values: List[float]) -> Dict[str, Any]:
        """Compute comprehensive statistical summary."""
        if not values:
            return {'error': 'No valid values'}

        values_array = np.array(values)

        # Basic statistics
        summary = {
            'count': len(values),
            'mean': float(np.mean(values_array)),
            'std': float(np.std(values_array)),
            'var': float(np.var(values_array)),
            'min': float(np.min(values_array)),
            'max': float(np.max(values_array)),
            'median': float(np.median(values_array)),
            'skewness': float(stats.skew(values_array)),
            'kurtosis': float(stats.kurtosis(values_array))
        }

        # Percentiles
        for p in self.config.compute_percentiles:
            summary[f'percentile_{p}'] = float(np.percentile(values_array, p))

        # Confidence intervals
        alpha = 1 - self.config.confidence_level
        try:
            # Bootstrap confidence interval for mean
            bootstrap_means = []
            for _ in range(1000):
                bootstrap_sample = np.random.choice(values_array, size=len(values_array), replace=True)
                bootstrap_means.append(np.mean(bootstrap_sample))

            ci_lower = np.percentile(bootstrap_means, 100 * alpha / 2)
            ci_upper = np.percentile(bootstrap_means, 100 * (1 - alpha / 2))

            summary['confidence_interval_mean'] = {
                'lower': float(ci_lower),
                'upper': float(ci_upper),
                'confidence_level': self.config.confidence_level
            }
        except Exception as e:
            summary['confidence_interval_mean'] = {'error': str(e)}

        return summary

    def _analyze_convergence(self, results: List[Any]) -> Dict[str, Any]:
        """Analyze Monte Carlo convergence."""
        valid_results = [r for r in results if r is not None]

        if len(valid_results) < self.config.min_samples:
            return {'error': 'Insufficient samples for convergence analysis'}

        # Extract scalar values for convergence analysis
        if isinstance(valid_results[0], dict):
            # Use first metric for convergence analysis
            metric_name = list(valid_results[0].keys())[0]
            values = [r[metric_name] for r in valid_results if metric_name in r and np.isfinite(r[metric_name])]
        else:
            values = [r for r in valid_results if np.isfinite(r)]

        if not values:
            return {'error': 'No valid values for convergence analysis'}

        # Compute running means
        running_means = []
        for i in range(1, len(values) + 1):
            running_means.append(np.mean(values[:i]))

        # Check convergence
        converged = False
        convergence_point = None

        if len(running_means) >= self.config.convergence_window:
            for i in range(self.config.convergence_window, len(running_means)):
                recent_window = running_means[i - self.config.convergence_window:i]
                relative_change = np.std(recent_window) / (np.mean(recent_window) + 1e-12)

                if relative_change < self.config.convergence_tolerance:
                    converged = True
                    convergence_point = i
                    break

        return {
            'converged': converged,
            'convergence_point': convergence_point,
            'final_mean': float(running_means[-1]),
            'running_means': running_means if self.config.save_all_samples else None,
            'convergence_tolerance': self.config.convergence_tolerance
        }

    def _analyze_data_with_monte_carlo(self, data: Union[List[Dict[str, float]], np.ndarray],
                                     **kwargs) -> Dict[str, Any]:
        """Analyze existing data using Monte Carlo methods."""
        # Convert data to array
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                # Extract first numeric metric
                for key, value in data[0].items():
                    if isinstance(value, (int, float)):
                        values = np.array([d.get(key, np.nan) for d in data])
                        break
            else:
                values = np.array(data)
        else:
            values = data.flatten()

        # Remove invalid values
        valid_values = values[np.isfinite(values)]

        if len(valid_values) == 0:
            return {'error': 'No valid data values'}

        # Bootstrap analysis
        bootstrap_results = self._bootstrap_analysis(valid_values)

        # Subsampling analysis
        subsampling_results = self._subsampling_analysis(valid_values)

        return {
            'bootstrap_analysis': bootstrap_results,
            'subsampling_analysis': subsampling_results,
            'original_statistics': self._compute_statistical_summary(valid_values.tolist())
        }

    def _perform_bootstrap_analysis(self, data: Union[List[Dict[str, float]], np.ndarray],
                                   **kwargs) -> Dict[str, Any]:
        """Perform bootstrap analysis."""
        # Extract values
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                values = []
                for d in data:
                    for key, value in d.items():
                        if isinstance(value, (int, float)) and np.isfinite(value):
                            values.append(value)
                            break
                values = np.array(values)
            else:
                values = np.array(data)
        else:
            values = data.flatten()

        valid_values = values[np.isfinite(values)]

        if len(valid_values) == 0:
            return {'error': 'No valid data for bootstrap analysis'}

        return self._bootstrap_analysis(valid_values)

    def _bootstrap_analysis(self, values: np.ndarray) -> Dict[str, Any]:
        """Perform bootstrap resampling analysis."""
        n_bootstrap = self.config.bootstrap_samples
        bootstrap_means = []
        bootstrap_stds = []
        bootstrap_medians = []

        for _ in range(n_bootstrap):
            bootstrap_sample = np.random.choice(values, size=len(values), replace=True)
            bootstrap_means.append(np.mean(bootstrap_sample))
            bootstrap_stds.append(np.std(bootstrap_sample))
            bootstrap_medians.append(np.median(bootstrap_sample))

        # Compute confidence intervals
        alpha = 1 - self.config.bootstrap_confidence_level

        mean_ci = [
            np.percentile(bootstrap_means, 100 * alpha / 2),
            np.percentile(bootstrap_means, 100 * (1 - alpha / 2))
        ]

        std_ci = [
            np.percentile(bootstrap_stds, 100 * alpha / 2),
            np.percentile(bootstrap_stds, 100 * (1 - alpha / 2))
        ]

        median_ci = [
            np.percentile(bootstrap_medians, 100 * alpha / 2),
            np.percentile(bootstrap_medians, 100 * (1 - alpha / 2))
        ]

        return {
            'mean_confidence_interval': {
                'lower': float(mean_ci[0]),
                'upper': float(mean_ci[1]),
                'confidence_level': self.config.bootstrap_confidence_level
            },
            'std_confidence_interval': {
                'lower': float(std_ci[0]),
                'upper': float(std_ci[1]),
                'confidence_level': self.config.bootstrap_confidence_level
            },
            'median_confidence_interval': {
                'lower': float(median_ci[0]),
                'upper': float(median_ci[1]),
                'confidence_level': self.config.bootstrap_confidence_level
            },
            'bootstrap_distribution_mean': {
                'mean': float(np.mean(bootstrap_means)),
                'std': float(np.std(bootstrap_means))
            },
            'n_bootstrap_samples': n_bootstrap
        }

    def _subsampling_analysis(self, values: np.ndarray) -> Dict[str, Any]:
        """Perform subsampling analysis."""
        n_original = len(values)
        subsample_sizes = [n_original // 4, n_original // 2, 3 * n_original // 4]

        results = {}

        for subsample_size in subsample_sizes:
            if subsample_size < 10:
                continue

            subsample_means = []
            n_subsamples = min(100, n_original // subsample_size)

            for _ in range(n_subsamples):
                subsample = np.random.choice(values, size=subsample_size, replace=False)
                subsample_means.append(np.mean(subsample))

            results[f'subsample_size_{subsample_size}'] = {
                'mean_of_means': float(np.mean(subsample_means)),
                'std_of_means': float(np.std(subsample_means)),
                'n_subsamples': n_subsamples
            }

        return results

    def _perform_sensitivity_analysis(self, simulation_function: Callable,
                                     parameter_distributions: Dict[str, Any],
                                     **kwargs) -> Dict[str, Any]:
        """Perform sensitivity analysis."""
        if self.config.sensitivity_method == "sobol":
            return self._sobol_sensitivity_analysis(simulation_function, parameter_distributions, **kwargs)
        elif self.config.sensitivity_method == "morris":
            return self._morris_sensitivity_analysis(simulation_function, parameter_distributions, **kwargs)
        else:
            return self._simple_sensitivity_analysis(simulation_function, parameter_distributions, **kwargs)

    def _simple_sensitivity_analysis(self, simulation_function: Callable,
                                    parameter_distributions: Dict[str, Any],
                                    **kwargs) -> Dict[str, Any]:
        """Simple one-at-a-time sensitivity analysis."""
        baseline_params = {}
        sensitivity_results = {}

        # Create baseline parameters (mean values)
        for param_name, dist_info in parameter_distributions.items():
            if dist_info.get('type', 'normal') == 'normal':
                baseline_params[param_name] = dist_info.get('mean', 0.0)
            elif dist_info.get('type') == 'uniform':
                low = dist_info.get('low', 0.0)
                high = dist_info.get('high', 1.0)
                baseline_params[param_name] = (low + high) / 2
            else:
                baseline_params[param_name] = 0.0

        # Baseline simulation
        try:
            baseline_result = simulation_function(baseline_params, **kwargs)
        except Exception as e:
            return {'error': f'Baseline simulation failed: {e}'}

        # Sensitivity analysis for each parameter
        for param_name, dist_info in parameter_distributions.items():
            param_sensitivities = []

            # Generate perturbations
            perturbation_factors = [-0.1, -0.05, 0.05, 0.1]  # ±10%, ±5%

            for factor in perturbation_factors:
                perturbed_params = baseline_params.copy()

                if dist_info.get('type', 'normal') == 'normal':
                    std = dist_info.get('std', 1.0)
                    perturbed_params[param_name] += factor * std
                else:
                    perturbed_params[param_name] *= (1 + factor)

                try:
                    perturbed_result = simulation_function(perturbed_params, **kwargs)

                    # Compute sensitivity
                    if isinstance(baseline_result, dict) and isinstance(perturbed_result, dict):
                        for metric_name in baseline_result.keys():
                            if metric_name in perturbed_result:
                                baseline_value = baseline_result[metric_name]
                                perturbed_value = perturbed_result[metric_name]
                                if baseline_value != 0:
                                    sensitivity = (perturbed_value - baseline_value) / (baseline_value * factor)
                                    param_sensitivities.append((metric_name, factor, sensitivity))
                    else:
                        # Scalar results
                        if baseline_result != 0:
                            sensitivity = (perturbed_result - baseline_result) / (baseline_result * factor)
                            param_sensitivities.append(('result', factor, sensitivity))

                except Exception as e:
                    warnings.warn(f"Sensitivity analysis failed for {param_name} with factor {factor}: {e}")

            sensitivity_results[param_name] = param_sensitivities

        return {
            'method': 'one_at_a_time',
            'baseline_parameters': baseline_params,
            'baseline_result': baseline_result,
            'parameter_sensitivities': sensitivity_results
        }

    def _sobol_sensitivity_analysis(self, simulation_function: Callable,
                                   parameter_distributions: Dict[str, Any],
                                   **kwargs) -> Dict[str, Any]:
        """Simplified Sobol sensitivity analysis."""
        # This is a simplified implementation
        # In practice, would use SALib or similar library
        return {'error': 'Sobol analysis not fully implemented in this simplified version'}

    def _morris_sensitivity_analysis(self, simulation_function: Callable,
                                    parameter_distributions: Dict[str, Any],
                                    **kwargs) -> Dict[str, Any]:
        """Simplified Morris sensitivity analysis."""
        # This is a simplified implementation
        return {'error': 'Morris analysis not fully implemented in this simplified version'}

    def _analyze_distributions(self, data: Union[List[Dict[str, float]], np.ndarray],
                              **kwargs) -> Dict[str, Any]:
        """Analyze and fit distributions to data."""
        # Extract values
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                values = []
                for d in data:
                    for key, value in d.items():
                        if isinstance(value, (int, float)) and np.isfinite(value):
                            values.append(value)
                            break
                values = np.array(values)
            else:
                values = np.array(data)
        else:
            values = data.flatten()

        valid_values = values[np.isfinite(values)]

        if len(valid_values) == 0:
            return {'error': 'No valid data for distribution analysis'}

        # Fit common distributions
        distributions_to_test = ['norm', 'lognorm', 'exponential', 'gamma', 'beta']
        distribution_fits = {}

        for dist_name in distributions_to_test:
            try:
                if dist_name == 'norm':
                    params = stats.norm.fit(valid_values)
                    ks_stat, p_value = stats.kstest(valid_values, lambda x: stats.norm.cdf(x, *params))
                elif dist_name == 'lognorm':
                    if np.all(valid_values > 0):
                        params = stats.lognorm.fit(valid_values)
                        ks_stat, p_value = stats.kstest(valid_values, lambda x: stats.lognorm.cdf(x, *params))
                    else:
                        continue
                elif dist_name == 'exponential':
                    if np.all(valid_values >= 0):
                        params = stats.expon.fit(valid_values)
                        ks_stat, p_value = stats.kstest(valid_values, lambda x: stats.expon.cdf(x, *params))
                    else:
                        continue
                elif dist_name == 'gamma':
                    if np.all(valid_values > 0):
                        params = stats.gamma.fit(valid_values)
                        ks_stat, p_value = stats.kstest(valid_values, lambda x: stats.gamma.cdf(x, *params))
                    else:
                        continue
                elif dist_name == 'beta':
                    if np.all(valid_values >= 0) and np.all(valid_values <= 1):
                        params = stats.beta.fit(valid_values)
                        ks_stat, p_value = stats.kstest(valid_values, lambda x: stats.beta.cdf(x, *params))
                    else:
                        continue

                distribution_fits[dist_name] = {
                    'parameters': params,
                    'ks_statistic': float(ks_stat),
                    'p_value': float(p_value),
                    'aic': 2 * len(params) - 2 * np.sum(getattr(stats, dist_name).logpdf(valid_values, *params))
                }

            except Exception as e:
                distribution_fits[dist_name] = {'error': str(e)}

        # Best fit (lowest AIC)
        valid_fits = {k: v for k, v in distribution_fits.items() if 'aic' in v}
        if valid_fits:
            best_fit = min(valid_fits.keys(), key=lambda k: valid_fits[k]['aic'])
        else:
            best_fit = None

        return {
            'distribution_fits': distribution_fits,
            'best_fit': best_fit,
            'sample_size': len(valid_values)
        }

    def _perform_risk_analysis(self, data: Union[List[Dict[str, float]], np.ndarray],
                              **kwargs) -> Dict[str, Any]:
        """Perform risk analysis including tail risk assessment."""
        # Extract values
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                values = []
                for d in data:
                    for key, value in d.items():
                        if isinstance(value, (int, float)) and np.isfinite(value):
                            values.append(value)
                            break
                values = np.array(values)
            else:
                values = np.array(data)
        else:
            values = data.flatten()

        valid_values = values[np.isfinite(values)]

        if len(valid_values) == 0:
            return {'error': 'No valid data for risk analysis'}

        # Value at Risk (VaR) and Conditional Value at Risk (CVaR)
        risk_levels = [0.01, 0.05, 0.1]  # 1%, 5%, 10%
        var_results = {}
        cvar_results = {}

        for alpha in risk_levels:
            var = np.percentile(valid_values, alpha * 100)
            # CVaR (Expected Shortfall)
            tail_values = valid_values[valid_values <= var]
            cvar = np.mean(tail_values) if len(tail_values) > 0 else var

            var_results[f'var_{int(alpha*100)}'] = float(var)
            cvar_results[f'cvar_{int(alpha*100)}'] = float(cvar)

        # Extreme value analysis
        extreme_analysis = self._extreme_value_analysis(valid_values)

        return {
            'value_at_risk': var_results,
            'conditional_value_at_risk': cvar_results,
            'extreme_value_analysis': extreme_analysis,
            'tail_statistics': {
                'left_tail_mean': float(np.mean(valid_values[valid_values <= np.percentile(valid_values, 5)])),
                'right_tail_mean': float(np.mean(valid_values[valid_values >= np.percentile(valid_values, 95)])),
                'tail_ratio': float(np.percentile(valid_values, 95) / np.percentile(valid_values, 5))
                if np.percentile(valid_values, 5) != 0 else np.inf
            }
        }

    def _extreme_value_analysis(self, values: np.ndarray) -> Dict[str, Any]:
        """Perform extreme value analysis."""
        try:
            # Block maxima method (simplified)
            block_size = max(10, len(values) // 20)
            n_blocks = len(values) // block_size

            block_maxima = []
            for i in range(n_blocks):
                block = values[i * block_size:(i + 1) * block_size]
                if len(block) > 0:
                    block_maxima.append(np.max(block))

            if len(block_maxima) < 5:
                return {'error': 'Insufficient data for extreme value analysis'}

            # Fit GEV distribution (simplified)
            gev_params = stats.genextreme.fit(block_maxima)

            return {
                'block_size': block_size,
                'n_blocks': n_blocks,
                'gev_parameters': gev_params,
                'return_levels': {
                    '10_year': float(stats.genextreme.ppf(1 - 1/10, *gev_params)),
                    '100_year': float(stats.genextreme.ppf(1 - 1/100, *gev_params))
                }
            }

        except Exception as e:
            return {'error': str(e)}

    def _generate_validation_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate validation summary."""
        summary = {
            'validation_successful': True,
            'key_findings': [],
            'recommendations': [],
            'confidence_assessment': 'medium'
        }

        # Check convergence
        if 'monte_carlo_simulation' in results:
            mc_results = results['monte_carlo_simulation']
            if 'convergence_analysis' in mc_results:
                convergence = mc_results['convergence_analysis']
                if not convergence.get('converged', False):
                    summary['key_findings'].append('Monte Carlo simulation may not have converged')
                    summary['recommendations'].append('Consider increasing sample size')
                    summary['confidence_assessment'] = 'low'

        # Check bootstrap results
        if 'bootstrap_analysis' in results:
            bootstrap = results['bootstrap_analysis']
            if 'mean_confidence_interval' in bootstrap:
                ci = bootstrap['mean_confidence_interval']
                ci_width = ci['upper'] - ci['lower']
                if ci_width > 0.1 * abs(ci['lower'] + ci['upper']) / 2:  # Wide CI
                    summary['key_findings'].append('Wide confidence intervals indicate high uncertainty')
                    summary['recommendations'].append('Consider collecting more data or reducing variability')

        # Check distribution fits
        if 'distribution_analysis' in results:
            dist_analysis = results['distribution_analysis']
            if dist_analysis.get('best_fit') is None:
                summary['key_findings'].append('No good distribution fit found')
                summary['recommendations'].append('Consider data transformation or alternative distributions')

        return summary


def create_monte_carlo_analyzer(config: Optional[Dict[str, Any]] = None) -> MonteCarloAnalyzer:
    """Factory function to create Monte Carlo analyzer.

    Parameters
    ----------
    config : Dict[str, Any], optional
        Configuration parameters

    Returns
    -------
    MonteCarloAnalyzer
        Configured Monte Carlo analyzer
    """
    if config is not None:
        mc_config = MonteCarloConfig(**config)
    else:
        mc_config = MonteCarloConfig()

    return MonteCarloAnalyzer(mc_config)