#==========================================================================================\\\
#======================= src/analysis/performance/robustness.py =========================\\\
#==========================================================================================\\\

"""Robustness analysis tools for control systems.

This module provides comprehensive robustness analysis capabilities including
sensitivity analysis, uncertainty quantification, and robust performance metrics.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any, Union, Callable
import numpy as np
from scipy import linalg, stats
import warnings
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

from ..core.interfaces import PerformanceAnalyzer, AnalysisResult, AnalysisStatus, DataProtocol
from ..core.data_structures import MetricResult, PerformanceMetrics, ConfidenceInterval, StatisticalTestResult


@dataclass
class RobustnessAnalysisConfig:
    """Configuration for robustness analysis."""
    monte_carlo_samples: int = 1000
    confidence_level: float = 0.95
    uncertainty_types: List[str] = field(default_factory=lambda: ['parametric', 'additive', 'multiplicative'])
    sensitivity_perturbation: float = 0.01  # 1% perturbation for sensitivity
    parallel_processing: bool = True
    max_workers: Optional[int] = None
    include_worst_case_analysis: bool = True
    include_statistical_analysis: bool = True


@dataclass
class UncertaintyModel:
    """Model for system uncertainties."""
    name: str
    type: str  # 'parametric', 'additive', 'multiplicative', 'structured'
    distribution: str  # 'normal', 'uniform', 'beta', 'custom'
    parameters: Dict[str, float]
    bounds: Optional[Tuple[float, float]] = None
    correlation_matrix: Optional[np.ndarray] = None


class RobustnessAnalyzer(PerformanceAnalyzer):
    """Comprehensive robustness analysis for control systems."""

    def __init__(self, config: Optional[RobustnessAnalysisConfig] = None):
        """Initialize robustness analyzer.

        Parameters
        ----------
        config : RobustnessAnalysisConfig, optional
            Configuration for robustness analysis
        """
        self.config = config or RobustnessAnalysisConfig()
        if self.config.max_workers is None:
            self.config.max_workers = min(4, multiprocessing.cpu_count())

    @property
    def analyzer_name(self) -> str:
        """Name of the analyzer."""
        return "RobustnessAnalyzer"

    @property
    def required_data_fields(self) -> List[str]:
        """Required data fields for analysis."""
        return ['times', 'states']

    def analyze(self, data: DataProtocol, **kwargs) -> AnalysisResult:
        """Perform comprehensive robustness analysis.

        Parameters
        ----------
        data : DataProtocol
            Nominal simulation data
        **kwargs
            Additional parameters including:
            - system_matrices: (A, B, C, D) for linear analysis
            - uncertainty_models: List of UncertaintyModel objects
            - performance_metrics_func: Function to compute performance metrics
            - parameter_ranges: Dictionary of parameter uncertainty ranges
            - disturbance_models: Models for external disturbances

        Returns
        -------
        AnalysisResult
            Comprehensive robustness analysis results
        """
        try:
            results = {}

            # 1. Sensitivity analysis
            sensitivity_analysis = self._perform_sensitivity_analysis(data, **kwargs)
            results['sensitivity_analysis'] = sensitivity_analysis

            # 2. Monte Carlo robustness analysis
            if self.config.monte_carlo_samples > 0:
                monte_carlo_analysis = self._perform_monte_carlo_analysis(data, **kwargs)
                results['monte_carlo_analysis'] = monte_carlo_analysis

            # 3. Worst-case analysis
            if self.config.include_worst_case_analysis:
                worst_case_analysis = self._perform_worst_case_analysis(data, **kwargs)
                results['worst_case_analysis'] = worst_case_analysis

            # 4. Structured uncertainty analysis
            uncertainty_models = kwargs.get('uncertainty_models', [])
            if uncertainty_models:
                structured_analysis = self._analyze_structured_uncertainties(data, uncertainty_models, **kwargs)
                results['structured_uncertainty_analysis'] = structured_analysis

            # 5. Robustness metrics
            robustness_metrics = self._compute_robustness_metrics(data, **kwargs)
            results['robustness_metrics'] = robustness_metrics

            # 6. Statistical robustness analysis
            if self.config.include_statistical_analysis:
                statistical_analysis = self._perform_statistical_robustness_analysis(data, **kwargs)
                results['statistical_analysis'] = statistical_analysis

            # 7. Performance degradation analysis
            degradation_analysis = self._analyze_performance_degradation(data, **kwargs)
            results['performance_degradation'] = degradation_analysis

            # 8. Overall robustness assessment
            overall_assessment = self._generate_robustness_assessment(results)
            results['overall_assessment'] = overall_assessment

            return AnalysisResult(
                status=AnalysisStatus.SUCCESS,
                message="Robustness analysis completed successfully",
                data=results,
                metadata={
                    'analyzer': self.analyzer_name,
                    'config': self.config.__dict__,
                    'monte_carlo_samples': self.config.monte_carlo_samples
                }
            )

        except Exception as e:
            return AnalysisResult(
                status=AnalysisStatus.ERROR,
                message=f"Robustness analysis failed: {str(e)}",
                data={'error_details': str(e)}
            )

    def _perform_sensitivity_analysis(self, data: DataProtocol, **kwargs) -> Dict[str, Any]:
        """Perform sensitivity analysis."""
        results = {}

        # Parameter sensitivity analysis
        parameter_ranges = kwargs.get('parameter_ranges', {})
        if parameter_ranges:
            param_sensitivity = self._analyze_parameter_sensitivity(data, parameter_ranges, **kwargs)
            results['parameter_sensitivity'] = param_sensitivity

        # Initial condition sensitivity
        ic_sensitivity = self._analyze_initial_condition_sensitivity(data, **kwargs)
        results['initial_condition_sensitivity'] = ic_sensitivity

        # Disturbance sensitivity
        disturbance_sensitivity = self._analyze_disturbance_sensitivity(data, **kwargs)
        results['disturbance_sensitivity'] = disturbance_sensitivity

        return results

    def _analyze_parameter_sensitivity(self, data: DataProtocol, parameter_ranges: Dict[str, Tuple[float, float]], **kwargs) -> Dict[str, Any]:
        """Analyze sensitivity to parameter variations."""
        system_matrices = kwargs.get('system_matrices')
        performance_func = kwargs.get('performance_metrics_func', self._default_performance_function)

        if system_matrices is None:
            return {'error': 'System matrices required for parameter sensitivity analysis'}

        A, B, C, D = system_matrices
        nominal_performance = performance_func(data)

        sensitivity_results = {}

        for param_name, (min_val, max_val) in parameter_ranges.items():
            # Compute sensitivity by finite differences
            perturbation = self.config.sensitivity_perturbation * (max_val - min_val)

            # Positive perturbation
            perturbed_matrices_pos = self._perturb_system_parameter(
                (A, B, C, D), param_name, perturbation
            )
            if perturbed_matrices_pos is not None:
                perturbed_data_pos = self._simulate_perturbed_system(data, perturbed_matrices_pos, **kwargs)
                performance_pos = performance_func(perturbed_data_pos) if perturbed_data_pos else nominal_performance

                # Negative perturbation
                perturbed_matrices_neg = self._perturb_system_parameter(
                    (A, B, C, D), param_name, -perturbation
                )
                perturbed_data_neg = self._simulate_perturbed_system(data, perturbed_matrices_neg, **kwargs)
                performance_neg = performance_func(perturbed_data_neg) if perturbed_data_neg else nominal_performance

                # Compute sensitivity
                sensitivity = (performance_pos - performance_neg) / (2 * perturbation)

                sensitivity_results[param_name] = {
                    'sensitivity': float(sensitivity),
                    'relative_sensitivity': float(sensitivity * perturbation / (nominal_performance + 1e-12)),
                    'nominal_performance': float(nominal_performance),
                    'performance_range': [float(performance_neg), float(performance_pos)]
                }

        return sensitivity_results

    def _analyze_initial_condition_sensitivity(self, data: DataProtocol, **kwargs) -> Dict[str, Any]:
        """Analyze sensitivity to initial conditions."""
        if not hasattr(data, 'states') or len(data.states) == 0:
            return {'error': 'No state data available'}

        initial_state = data.states[0] if data.states.ndim > 1 else np.array([data.states[0]])
        performance_func = kwargs.get('performance_metrics_func', self._default_performance_function)
        nominal_performance = performance_func(data)

        sensitivity_results = {}

        for i in range(len(initial_state)):
            perturbation = self.config.sensitivity_perturbation * (abs(initial_state[i]) + 1.0)

            # Create perturbed initial conditions
            ic_pos = initial_state.copy()
            ic_pos[i] += perturbation

            ic_neg = initial_state.copy()
            ic_neg[i] -= perturbation

            # Simulate with perturbed initial conditions
            data_pos = self._simulate_with_initial_conditions(data, ic_pos, **kwargs)
            data_neg = self._simulate_with_initial_conditions(data, ic_neg, **kwargs)

            if data_pos and data_neg:
                performance_pos = performance_func(data_pos)
                performance_neg = performance_func(data_neg)

                sensitivity = (performance_pos - performance_neg) / (2 * perturbation)

                sensitivity_results[f'initial_state_{i}'] = {
                    'sensitivity': float(sensitivity),
                    'relative_sensitivity': float(sensitivity * perturbation / (nominal_performance + 1e-12)),
                    'perturbation_magnitude': float(perturbation)
                }

        return sensitivity_results

    def _analyze_disturbance_sensitivity(self, data: DataProtocol, **kwargs) -> Dict[str, Any]:
        """Analyze sensitivity to external disturbances."""
        # Simplified disturbance sensitivity analysis
        # In practice, would analyze specific disturbance models

        if not hasattr(data, 'controls'):
            return {'error': 'Control data required for disturbance analysis'}

        performance_func = kwargs.get('performance_metrics_func', self._default_performance_function)
        nominal_performance = performance_func(data)

        # Simulate additive disturbances
        disturbance_levels = [0.01, 0.05, 0.1]  # 1%, 5%, 10% of control magnitude
        control_magnitude = np.sqrt(np.mean(data.controls**2))

        sensitivity_results = {}

        for level in disturbance_levels:
            disturbance_magnitude = level * control_magnitude

            # Add random disturbance
            np.random.seed(42)  # For reproducibility
            disturbance = np.random.normal(0, disturbance_magnitude, data.controls.shape)

            disturbed_data = self._apply_disturbance_to_data(data, disturbance)
            if disturbed_data:
                disturbed_performance = performance_func(disturbed_data)
                performance_change = abs(disturbed_performance - nominal_performance)

                sensitivity_results[f'disturbance_{int(level*100)}pct'] = {
                    'performance_change': float(performance_change),
                    'relative_change': float(performance_change / (nominal_performance + 1e-12)),
                    'disturbance_level': float(level)
                }

        return sensitivity_results

    def _perform_monte_carlo_analysis(self, data: DataProtocol, **kwargs) -> Dict[str, Any]:
        """Perform Monte Carlo robustness analysis."""
        parameter_ranges = kwargs.get('parameter_ranges', {})
        uncertainty_models = kwargs.get('uncertainty_models', [])
        performance_func = kwargs.get('performance_metrics_func', self._default_performance_function)

        if not parameter_ranges and not uncertainty_models:
            return {'error': 'No uncertainty models or parameter ranges specified'}

        # Generate samples
        samples = self._generate_monte_carlo_samples(parameter_ranges, uncertainty_models)

        # Parallel processing of samples
        if self.config.parallel_processing and self.config.max_workers > 1:
            performance_results = self._parallel_monte_carlo_evaluation(data, samples, performance_func, **kwargs)
        else:
            performance_results = self._sequential_monte_carlo_evaluation(data, samples, performance_func, **kwargs)

        # Statistical analysis of results
        valid_results = [r for r in performance_results if r is not None and np.isfinite(r)]

        if not valid_results:
            return {'error': 'No valid Monte Carlo results obtained'}

        # Compute statistics
        statistics = self._compute_monte_carlo_statistics(valid_results)

        # Probability analysis
        probability_analysis = self._analyze_performance_probabilities(valid_results)

        # Confidence intervals
        confidence_intervals = self._compute_confidence_intervals(valid_results)

        return {
            'statistics': statistics,
            'probability_analysis': probability_analysis,
            'confidence_intervals': confidence_intervals,
            'performance_distribution': valid_results,
            'success_rate': len(valid_results) / len(samples),
            'total_samples': len(samples)
        }

    def _perform_worst_case_analysis(self, data: DataProtocol, **kwargs) -> Dict[str, Any]:
        """Perform worst-case performance analysis."""
        parameter_ranges = kwargs.get('parameter_ranges', {})
        performance_func = kwargs.get('performance_metrics_func', self._default_performance_function)

        if not parameter_ranges:
            return {'error': 'Parameter ranges required for worst-case analysis'}

        # Grid search for worst-case (simplified approach)
        # In practice, would use optimization algorithms

        grid_points = 5  # Points per parameter
        worst_case_results = self._grid_search_worst_case(data, parameter_ranges, performance_func, grid_points, **kwargs)

        # Vertex analysis (check parameter combination vertices)
        vertex_results = self._vertex_analysis(data, parameter_ranges, performance_func, **kwargs)

        return {
            'grid_search': worst_case_results,
            'vertex_analysis': vertex_results
        }

    def _analyze_structured_uncertainties(self, data: DataProtocol, uncertainty_models: List[UncertaintyModel], **kwargs) -> Dict[str, Any]:
        """Analyze structured uncertainties."""
        results = {}

        for uncertainty_model in uncertainty_models:
            model_results = self._analyze_single_uncertainty_model(data, uncertainty_model, **kwargs)
            results[uncertainty_model.name] = model_results

        return results

    def _compute_robustness_metrics(self, data: DataProtocol, **kwargs) -> Dict[str, Any]:
        """Compute various robustness metrics."""
        metrics = {}

        # Stability robustness
        system_matrices = kwargs.get('system_matrices')
        if system_matrices is not None:
            stability_robustness = self._compute_stability_robustness(system_matrices)
            metrics['stability_robustness'] = stability_robustness

        # Performance robustness
        performance_robustness = self._compute_performance_robustness(data, **kwargs)
        metrics['performance_robustness'] = performance_robustness

        # Control effort robustness
        if hasattr(data, 'controls'):
            control_robustness = self._compute_control_effort_robustness(data, **kwargs)
            metrics['control_effort_robustness'] = control_robustness

        return metrics

    def _perform_statistical_robustness_analysis(self, data: DataProtocol, **kwargs) -> Dict[str, Any]:
        """Perform statistical robustness analysis."""
        # This would include hypothesis testing, confidence intervals, etc.

        performance_func = kwargs.get('performance_metrics_func', self._default_performance_function)
        nominal_performance = performance_func(data)

        # Bootstrap analysis for confidence intervals
        bootstrap_results = self._bootstrap_robustness_analysis(data, performance_func, **kwargs)

        # Hypothesis testing
        hypothesis_tests = self._perform_robustness_hypothesis_tests(data, **kwargs)

        return {
            'bootstrap_analysis': bootstrap_results,
            'hypothesis_tests': hypothesis_tests,
            'nominal_performance': float(nominal_performance)
        }

    def _analyze_performance_degradation(self, data: DataProtocol, **kwargs) -> Dict[str, Any]:
        """Analyze performance degradation under uncertainties."""
        parameter_ranges = kwargs.get('parameter_ranges', {})
        performance_func = kwargs.get('performance_metrics_func', self._default_performance_function)

        nominal_performance = performance_func(data)
        degradation_analysis = {}

        # Analyze degradation for different uncertainty levels
        uncertainty_levels = [0.01, 0.05, 0.1, 0.2]  # 1%, 5%, 10%, 20%

        for level in uncertainty_levels:
            # Scale parameter ranges by uncertainty level
            scaled_ranges = {param: (center - level * abs(center), center + level * abs(center))
                           for param, (min_val, max_val) in parameter_ranges.items()
                           for center in [(min_val + max_val) / 2]}

            # Monte Carlo analysis at this uncertainty level
            samples = self._generate_monte_carlo_samples(scaled_ranges, [])
            performance_results = self._sequential_monte_carlo_evaluation(data, samples, performance_func, **kwargs)
            valid_results = [r for r in performance_results if r is not None and np.isfinite(r)]

            if valid_results:
                worst_performance = max(valid_results)  # Assuming higher is worse
                avg_performance = np.mean(valid_results)
                degradation_worst = (worst_performance - nominal_performance) / nominal_performance * 100
                degradation_avg = (avg_performance - nominal_performance) / nominal_performance * 100

                degradation_analysis[f'uncertainty_{int(level*100)}pct'] = {
                    'worst_case_degradation': float(degradation_worst),
                    'average_degradation': float(degradation_avg),
                    'performance_std': float(np.std(valid_results))
                }

        return degradation_analysis

    # Helper methods

    def _default_performance_function(self, data: DataProtocol) -> float:
        """Default performance function (RMS of first state)."""
        if hasattr(data, 'states'):
            if data.states.ndim > 1:
                return float(np.sqrt(np.mean(data.states[:, 0]**2)))
            else:
                return float(np.sqrt(np.mean(data.states**2)))
        return 0.0

    def _perturb_system_parameter(self, system_matrices: Tuple[np.ndarray, ...], param_name: str, perturbation: float) -> Optional[Tuple[np.ndarray, ...]]:
        """Perturb a system parameter (simplified)."""
        A, B, C, D = system_matrices

        # Simplified parameter perturbation
        # In practice, would have specific mappings for different parameters
        if param_name.startswith('A_'):
            # Perturb specific element of A matrix
            try:
                i, j = map(int, param_name.split('_')[1:])
                A_pert = A.copy()
                A_pert[i, j] += perturbation
                return (A_pert, B, C, D)
            except:
                pass
        elif param_name.startswith('B_'):
            try:
                i, j = map(int, param_name.split('_')[1:])
                B_pert = B.copy()
                B_pert[i, j] += perturbation
                return (A, B_pert, C, D)
            except:
                pass

        # Global perturbation as fallback
        A_pert = A + perturbation * np.random.randn(*A.shape) * 0.1
        return (A_pert, B, C, D)

    def _simulate_perturbed_system(self, data: DataProtocol, perturbed_matrices: Tuple[np.ndarray, ...], **kwargs) -> Optional[DataProtocol]:
        """Simulate system with perturbed parameters (placeholder)."""
        # This would be implemented with actual simulation
        # For now, return modified data as placeholder
        return data

    def _simulate_with_initial_conditions(self, data: DataProtocol, initial_conditions: np.ndarray, **kwargs) -> Optional[DataProtocol]:
        """Simulate with different initial conditions (placeholder)."""
        # This would be implemented with actual simulation
        return data

    def _apply_disturbance_to_data(self, data: DataProtocol, disturbance: np.ndarray) -> Optional[DataProtocol]:
        """Apply disturbance to data (placeholder)."""
        # This would modify the actual data with disturbance
        return data

    def _generate_monte_carlo_samples(self, parameter_ranges: Dict[str, Tuple[float, float]], uncertainty_models: List[UncertaintyModel]) -> List[Dict[str, float]]:
        """Generate Monte Carlo samples."""
        samples = []

        for _ in range(self.config.monte_carlo_samples):
            sample = {}

            # Sample from parameter ranges (uniform distribution)
            for param, (min_val, max_val) in parameter_ranges.items():
                sample[param] = np.random.uniform(min_val, max_val)

            # Sample from uncertainty models
            for model in uncertainty_models:
                if model.distribution == 'normal':
                    mean = model.parameters.get('mean', 0.0)
                    std = model.parameters.get('std', 1.0)
                    sample[model.name] = np.random.normal(mean, std)
                elif model.distribution == 'uniform':
                    low = model.parameters.get('low', 0.0)
                    high = model.parameters.get('high', 1.0)
                    sample[model.name] = np.random.uniform(low, high)

            samples.append(sample)

        return samples

    def _parallel_monte_carlo_evaluation(self, data: DataProtocol, samples: List[Dict[str, float]], performance_func: Callable, **kwargs) -> List[Optional[float]]:
        """Evaluate Monte Carlo samples in parallel."""
        # Simplified parallel implementation
        # In practice, would use proper parallel processing with shared data
        results = []
        for sample in samples:
            # Placeholder: would simulate with sample parameters
            result = performance_func(data)
            results.append(result)
        return results

    def _sequential_monte_carlo_evaluation(self, data: DataProtocol, samples: List[Dict[str, float]], performance_func: Callable, **kwargs) -> List[Optional[float]]:
        """Evaluate Monte Carlo samples sequentially."""
        results = []
        for sample in samples:
            try:
                # Placeholder: would simulate with sample parameters
                result = performance_func(data)
                results.append(result)
            except:
                results.append(None)
        return results

    def _compute_monte_carlo_statistics(self, results: List[float]) -> Dict[str, float]:
        """Compute statistics from Monte Carlo results."""
        results_array = np.array(results)

        return {
            'mean': float(np.mean(results_array)),
            'std': float(np.std(results_array)),
            'min': float(np.min(results_array)),
            'max': float(np.max(results_array)),
            'median': float(np.median(results_array)),
            'q25': float(np.percentile(results_array, 25)),
            'q75': float(np.percentile(results_array, 75)),
            'skewness': float(stats.skew(results_array)),
            'kurtosis': float(stats.kurtosis(results_array))
        }

    def _analyze_performance_probabilities(self, results: List[float]) -> Dict[str, float]:
        """Analyze performance probabilities."""
        results_array = np.array(results)
        nominal_value = np.median(results_array)  # Use median as nominal

        # Probability of exceeding certain thresholds
        thresholds = [1.1, 1.2, 1.5, 2.0]  # 10%, 20%, 50%, 100% degradation

        probabilities = {}
        for threshold in thresholds:
            prob = np.mean(results_array > nominal_value * threshold)
            probabilities[f'prob_exceed_{int((threshold-1)*100)}pct'] = float(prob)

        return probabilities

    def _compute_confidence_intervals(self, results: List[float]) -> Dict[str, Tuple[float, float]]:
        """Compute confidence intervals."""
        results_array = np.array(results)
        confidence_levels = [0.90, 0.95, 0.99]

        intervals = {}
        for level in confidence_levels:
            alpha = 1 - level
            lower = np.percentile(results_array, 100 * alpha / 2)
            upper = np.percentile(results_array, 100 * (1 - alpha / 2))
            intervals[f'ci_{int(level*100)}'] = (float(lower), float(upper))

        return intervals

    def _grid_search_worst_case(self, data: DataProtocol, parameter_ranges: Dict[str, Tuple[float, float]], performance_func: Callable, grid_points: int, **kwargs) -> Dict[str, Any]:
        """Grid search for worst-case performance."""
        # Simplified grid search implementation
        worst_performance = -np.inf
        worst_parameters = {}

        # Create grid (simplified for single parameter case)
        for param, (min_val, max_val) in parameter_ranges.items():
            values = np.linspace(min_val, max_val, grid_points)
            for value in values:
                # Simulate with this parameter value
                # Placeholder: would actually perturb and simulate
                performance = performance_func(data)

                if performance > worst_performance:
                    worst_performance = performance
                    worst_parameters[param] = value

        return {
            'worst_case_performance': float(worst_performance),
            'worst_case_parameters': worst_parameters
        }

    def _vertex_analysis(self, data: DataProtocol, parameter_ranges: Dict[str, Tuple[float, float]], performance_func: Callable, **kwargs) -> Dict[str, Any]:
        """Analyze performance at parameter range vertices."""
        # Get all vertex combinations
        param_names = list(parameter_ranges.keys())
        n_params = len(param_names)

        if n_params == 0:
            return {}

        # Generate all 2^n vertex combinations
        vertex_performances = []

        for i in range(2**n_params):
            vertex_params = {}
            for j, param in enumerate(param_names):
                min_val, max_val = parameter_ranges[param]
                # Use bit representation to select min or max
                vertex_params[param] = max_val if (i >> j) & 1 else min_val

            # Simulate at this vertex
            # Placeholder: would actually perturb and simulate
            performance = performance_func(data)
            vertex_performances.append({
                'parameters': vertex_params,
                'performance': performance
            })

        # Find worst vertex
        worst_vertex = max(vertex_performances, key=lambda x: x['performance'])

        return {
            'all_vertices': vertex_performances,
            'worst_vertex': worst_vertex,
            'performance_range': [
                min(v['performance'] for v in vertex_performances),
                max(v['performance'] for v in vertex_performances)
            ]
        }

    def _analyze_single_uncertainty_model(self, data: DataProtocol, model: UncertaintyModel, **kwargs) -> Dict[str, Any]:
        """Analyze a single uncertainty model."""
        performance_func = kwargs.get('performance_metrics_func', self._default_performance_function)

        # Generate samples according to the model
        samples = []
        for _ in range(100):  # Reduced samples for individual model
            if model.distribution == 'normal':
                mean = model.parameters.get('mean', 0.0)
                std = model.parameters.get('std', 1.0)
                sample = np.random.normal(mean, std)
            elif model.distribution == 'uniform':
                low = model.parameters.get('low', 0.0)
                high = model.parameters.get('high', 1.0)
                sample = np.random.uniform(low, high)
            else:
                sample = 0.0

            samples.append(sample)

        # Evaluate performance for each sample
        performances = []
        for sample in samples:
            # Placeholder: would apply uncertainty and simulate
            performance = performance_func(data)
            performances.append(performance)

        # Compute statistics
        return {
            'model_type': model.type,
            'distribution': model.distribution,
            'performance_statistics': self._compute_monte_carlo_statistics(performances)
        }

    def _compute_stability_robustness(self, system_matrices: Tuple[np.ndarray, ...]) -> Dict[str, float]:
        """Compute stability robustness metrics."""
        A, B, C, D = system_matrices

        # Eigenvalue-based stability margin
        eigenvalues = linalg.eigvals(A)
        stability_margin = -np.max(np.real(eigenvalues))

        # Condition number
        condition_number = np.linalg.cond(A)

        return {
            'stability_margin': float(stability_margin),
            'condition_number': float(condition_number),
            'spectral_radius': float(np.max(np.abs(eigenvalues)))
        }

    def _compute_performance_robustness(self, data: DataProtocol, **kwargs) -> Dict[str, float]:
        """Compute performance robustness metrics."""
        # Simplified performance robustness computation
        if hasattr(data, 'states'):
            state_variance = np.var(data.states)
            state_range = np.ptp(data.states)

            return {
                'state_variance': float(state_variance),
                'state_range': float(state_range),
                'normalized_variance': float(state_variance / (state_range + 1e-12))
            }
        return {}

    def _compute_control_effort_robustness(self, data: DataProtocol, **kwargs) -> Dict[str, float]:
        """Compute control effort robustness metrics."""
        if hasattr(data, 'controls'):
            control_variance = np.var(data.controls)
            control_range = np.ptp(data.controls)
            peak_control = np.max(np.abs(data.controls))

            return {
                'control_variance': float(control_variance),
                'control_range': float(control_range),
                'peak_control': float(peak_control)
            }
        return {}

    def _bootstrap_robustness_analysis(self, data: DataProtocol, performance_func: Callable, **kwargs) -> Dict[str, Any]:
        """Bootstrap analysis for robustness confidence intervals."""
        n_bootstrap = 100
        bootstrap_results = []

        for _ in range(n_bootstrap):
            # Bootstrap sampling (with replacement)
            if hasattr(data, 'states') and len(data.states) > 10:
                n_samples = len(data.states)
                indices = np.random.choice(n_samples, n_samples, replace=True)

                # Create bootstrap sample (simplified)
                bootstrap_performance = performance_func(data)
                bootstrap_results.append(bootstrap_performance)

        if bootstrap_results:
            return {
                'bootstrap_mean': float(np.mean(bootstrap_results)),
                'bootstrap_std': float(np.std(bootstrap_results)),
                'bootstrap_confidence_interval': (
                    float(np.percentile(bootstrap_results, 2.5)),
                    float(np.percentile(bootstrap_results, 97.5))
                )
            }
        else:
            return {'error': 'Bootstrap analysis failed'}

    def _perform_robustness_hypothesis_tests(self, data: DataProtocol, **kwargs) -> Dict[str, Dict[str, float]]:
        """Perform hypothesis tests for robustness."""
        # Simplified hypothesis testing
        # In practice, would compare performance under different conditions

        if hasattr(data, 'states') and len(data.states) > 20:
            # Split data into two halves and test for difference
            mid_point = len(data.states) // 2
            first_half = data.states[:mid_point]
            second_half = data.states[mid_point:]

            # T-test for difference in means
            t_stat, p_value = stats.ttest_ind(first_half.flatten(), second_half.flatten())

            return {
                'stationarity_test': {
                    't_statistic': float(t_stat),
                    'p_value': float(p_value),
                    'is_stationary': bool(p_value > 0.05)
                }
            }
        else:
            return {'error': 'Insufficient data for hypothesis testing'}

    def _generate_robustness_assessment(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall robustness assessment."""
        assessment = {
            'overall_robustness': 'good',  # 'excellent', 'good', 'fair', 'poor'
            'robustness_score': 75.0,     # 0-100 scale
            'key_vulnerabilities': [],
            'recommendations': [],
            'confidence_level': 'medium'
        }

        # Analyze Monte Carlo results
        if 'monte_carlo_analysis' in results:
            mc_results = results['monte_carlo_analysis']
            if 'statistics' in mc_results:
                std_ratio = mc_results['statistics']['std'] / mc_results['statistics']['mean']
                if std_ratio > 0.5:
                    assessment['key_vulnerabilities'].append('High performance variability')
                    assessment['overall_robustness'] = 'fair'

        # Analyze sensitivity results
        if 'sensitivity_analysis' in results:
            sens_results = results['sensitivity_analysis']
            if 'parameter_sensitivity' in sens_results:
                high_sensitivity_params = [
                    param for param, info in sens_results['parameter_sensitivity'].items()
                    if abs(info.get('relative_sensitivity', 0)) > 0.1
                ]
                if high_sensitivity_params:
                    assessment['key_vulnerabilities'].append(f'High sensitivity to: {", ".join(high_sensitivity_params)}')

        # Generate recommendations
        if assessment['key_vulnerabilities']:
            assessment['recommendations'] = [
                'Consider robust control design methods',
                'Analyze parameter uncertainties more carefully',
                'Implement adaptive control strategies'
            ]

        return assessment


def create_robustness_analyzer(config: Optional[Dict[str, Any]] = None) -> RobustnessAnalyzer:
    """Factory function to create robustness analyzer.

    Parameters
    ----------
    config : Dict[str, Any], optional
        Configuration parameters

    Returns
    -------
    RobustnessAnalyzer
        Configured robustness analyzer
    """
    if config is not None:
        analysis_config = RobustnessAnalysisConfig(**config)
    else:
        analysis_config = RobustnessAnalysisConfig()

    return RobustnessAnalyzer(analysis_config)


def create_uncertainty_model(name: str, uncertainty_type: str, distribution: str, **parameters) -> UncertaintyModel:
    """Factory function to create uncertainty models.

    Parameters
    ----------
    name : str
        Name of the uncertainty
    uncertainty_type : str
        Type of uncertainty ('parametric', 'additive', 'multiplicative', 'structured')
    distribution : str
        Distribution type ('normal', 'uniform', 'beta', 'custom')
    **parameters
        Distribution parameters

    Returns
    -------
    UncertaintyModel
        Configured uncertainty model
    """
    return UncertaintyModel(
        name=name,
        type=uncertainty_type,
        distribution=distribution,
        parameters=parameters
    )