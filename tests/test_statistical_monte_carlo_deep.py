#==========================================================================================\\\
#============== tests/test_statistical_monte_carlo_deep.py ===============================\\\
#==========================================================================================\\\

"""
Deep Statistical Validation and Monte Carlo Analysis Tests.
COMPREHENSIVE JOB: Test statistical properties, Monte Carlo validation, and stochastic behavior.
"""

import pytest
import numpy as np
import scipy.stats as stats
from typing import Dict, List, Tuple, Callable, Optional, Any
from dataclasses import dataclass
import warnings
from collections import defaultdict


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo analysis."""
    samples: np.ndarray
    mean: float
    std: float
    confidence_interval_95: Tuple[float, float]
    confidence_interval_99: Tuple[float, float]
    distribution_test_p_value: float
    outlier_fraction: float
    convergence_analysis: Dict[str, Any]


@dataclass
class StatisticalTestResult:
    """Results from statistical hypothesis testing."""
    test_statistic: float
    p_value: float
    critical_value: float
    reject_null: bool
    effect_size: float
    power: float
    interpretation: str


class StatisticalAnalyzer:
    """Advanced statistical analysis tools."""

    @staticmethod
    def monte_carlo_analysis(
        sampling_function: Callable,
        n_samples: int = 1000,
        confidence_levels: List[float] = [0.95, 0.99]
    ) -> MonteCarloResult:
        """Perform comprehensive Monte Carlo analysis."""

        # Generate samples
        samples = []
        for _ in range(n_samples):
            try:
                sample = sampling_function()
                if np.isfinite(sample):
                    samples.append(sample)
            except Exception as e:
                warnings.warn(f"Sample generation failed: {e}")

        samples = np.array(samples)

        if len(samples) == 0:
            raise ValueError("No valid samples generated")

        # Basic statistics
        mean = np.mean(samples)
        std = np.std(samples, ddof=1)  # Sample standard deviation

        # Confidence intervals
        confidence_intervals = {}
        for level in confidence_levels:
            alpha = 1 - level
            df = len(samples) - 1
            t_critical = stats.t.ppf(1 - alpha/2, df)
            margin_of_error = t_critical * std / np.sqrt(len(samples))

            ci = (mean - margin_of_error, mean + margin_of_error)
            confidence_intervals[level] = ci

        # Distribution normality test (Shapiro-Wilk)
        if len(samples) >= 3:
            _, normality_p_value = stats.shapiro(samples)
        else:
            normality_p_value = 1.0

        # Outlier detection (using IQR method)
        q1, q3 = np.percentile(samples, [25, 75])
        iqr = q3 - q1
        outlier_bounds = (q1 - 1.5*iqr, q3 + 1.5*iqr)
        outliers = (samples < outlier_bounds[0]) | (samples > outlier_bounds[1])
        outlier_fraction = np.sum(outliers) / len(samples)

        # Convergence analysis
        convergence = StatisticalAnalyzer._analyze_convergence(samples)

        return MonteCarloResult(
            samples=samples,
            mean=mean,
            std=std,
            confidence_interval_95=confidence_intervals.get(0.95, (mean, mean)),
            confidence_interval_99=confidence_intervals.get(0.99, (mean, mean)),
            distribution_test_p_value=normality_p_value,
            outlier_fraction=outlier_fraction,
            convergence_analysis=convergence
        )

    @staticmethod
    def _analyze_convergence(samples: np.ndarray) -> Dict[str, Any]:
        """Analyze convergence of Monte Carlo samples."""
        n = len(samples)
        if n < 10:
            return {'insufficient_data': True}

        # Running mean convergence
        running_means = np.cumsum(samples) / np.arange(1, n + 1)
        final_mean = running_means[-1]

        # Check convergence using relative changes
        convergence_threshold = 0.01  # 1% threshold
        converged_indices = []

        for i in range(10, n):
            relative_change = abs(running_means[i] - running_means[i-10]) / (abs(running_means[i-10]) + 1e-10)
            if relative_change < convergence_threshold:
                converged_indices.append(i)

        # Monte Carlo standard error
        mc_std_error = np.std(samples, ddof=1) / np.sqrt(n)

        return {
            'running_means': running_means,
            'converged': len(converged_indices) > n // 4,  # At least 25% of later points converged
            'convergence_point': converged_indices[0] if converged_indices else None,
            'mc_standard_error': mc_std_error,
            'effective_sample_size': n,  # Simplified - could compute autocorrelation
            'final_mean': final_mean
        }

    @staticmethod
    def two_sample_test(
        sample1: np.ndarray,
        sample2: np.ndarray,
        test_type: str = 'welch'
    ) -> StatisticalTestResult:
        """Perform two-sample statistical test."""

        if test_type == 'welch':
            # Welch's t-test (unequal variances)
            t_stat, p_value = stats.ttest_ind(sample1, sample2, equal_var=False)

            # Degrees of freedom for Welch's test
            s1, s2 = np.var(sample1, ddof=1), np.var(sample2, ddof=1)
            n1, n2 = len(sample1), len(sample2)
            df = (s1/n1 + s2/n2)**2 / ((s1/n1)**2/(n1-1) + (s2/n2)**2/(n2-1))

            critical_value = stats.t.ppf(0.975, df)  # Two-tailed, alpha=0.05

        elif test_type == 'mann_whitney':
            # Mann-Whitney U test (non-parametric)
            u_stat, p_value = stats.mannwhitneyu(sample1, sample2, alternative='two-sided')
            t_stat = u_stat  # For consistency
            critical_value = stats.norm.ppf(0.975)  # Approximate

        else:
            raise ValueError(f"Unknown test type: {test_type}")

        # Effect size (Cohen's d)
        pooled_std = np.sqrt(((len(sample1)-1)*np.var(sample1, ddof=1) +
                             (len(sample2)-1)*np.var(sample2, ddof=1)) /
                            (len(sample1) + len(sample2) - 2))
        cohens_d = (np.mean(sample1) - np.mean(sample2)) / pooled_std

        # Power analysis (simplified)
        effect_size = abs(cohens_d)
        if effect_size < 0.2:
            power = 0.2  # Low power for small effects
        elif effect_size < 0.5:
            power = 0.5  # Medium power
        else:
            power = 0.8  # High power for large effects

        # Interpretation
        alpha = 0.05
        reject_null = p_value < alpha

        if reject_null:
            if abs(cohens_d) < 0.2:
                interpretation = "Statistically significant but small effect"
            elif abs(cohens_d) < 0.5:
                interpretation = "Statistically significant with medium effect"
            else:
                interpretation = "Statistically significant with large effect"
        else:
            interpretation = "No significant difference detected"

        return StatisticalTestResult(
            test_statistic=t_stat,
            p_value=p_value,
            critical_value=critical_value,
            reject_null=reject_null,
            effect_size=cohens_d,
            power=power,
            interpretation=interpretation
        )


class MockStochasticController:
    """Mock controller with stochastic behavior for Monte Carlo testing."""

    def __init__(self, gains, noise_level=0.01):
        self.gains = np.array(gains)
        self.noise_level = noise_level
        self.performance_history = []

    def simulate_control_performance(self, initial_state, n_steps=100):
        """Simulate control performance with noise."""
        np.random.seed()  # Fresh random seed

        state = np.array(initial_state)
        total_error = 0.0

        for step in range(n_steps):
            # Add measurement noise
            noisy_state = state + np.random.normal(0, self.noise_level, len(state))

            # Control computation
            control = -np.dot(self.gains, noisy_state)

            # Add control noise
            noisy_control = control + np.random.normal(0, self.noise_level * 0.5)

            # Simple dynamics with process noise
            state = state * 0.95 + noisy_control * 0.1 + np.random.normal(0, self.noise_level * 0.1, len(state))

            # Accumulate error
            total_error += np.linalg.norm(state) * 0.01

        return total_error

    def monte_carlo_performance_analysis(self, n_trials=1000):
        """Perform Monte Carlo analysis of controller performance."""

        def sample_performance():
            initial_state = np.random.normal(0, 0.1, 6)  # Random initial condition
            return self.simulate_control_performance(initial_state)

        return StatisticalAnalyzer.monte_carlo_analysis(sample_performance, n_trials)


@pytest.mark.statistical
class TestMonteCarloValidation:
    """Monte Carlo validation tests."""

    def test_controller_performance_monte_carlo(self):
        """Test controller performance using Monte Carlo analysis."""
        controller = MockStochasticController([2, 4, 3, 1, 2, 1], noise_level=0.02)

        # Monte Carlo analysis
        result = controller.monte_carlo_performance_analysis(n_trials=500)

        # Validation checks
        assert len(result.samples) >= 400, "Insufficient valid samples generated"
        assert result.mean > 0, "Performance metric should be positive"
        assert result.std > 0, "Should have variation in performance"

        # Statistical properties
        assert result.confidence_interval_95[0] < result.mean < result.confidence_interval_95[1]
        assert result.confidence_interval_99[0] <= result.confidence_interval_95[0]
        assert result.confidence_interval_95[1] <= result.confidence_interval_99[1]

        # Outlier analysis
        assert result.outlier_fraction < 0.2, "Too many outliers detected"

        # Convergence check
        if not result.convergence_analysis.get('insufficient_data', False):
            assert result.convergence_analysis['mc_standard_error'] > 0
            assert result.convergence_analysis['final_mean'] == result.mean

    def test_monte_carlo_robustness_analysis(self):
        """Test system robustness using Monte Carlo parameter variations."""

        def sample_robustness():
            # Random parameter variations
            base_gains = np.array([2, 4, 3, 1, 2, 1])
            gain_variations = np.random.normal(1.0, 0.1, 6)  # ±10% variation
            varied_gains = base_gains * gain_variations

            # Random noise level
            noise_level = np.random.uniform(0.001, 0.05)

            controller = MockStochasticController(varied_gains, noise_level)

            # Fixed initial condition for robustness test
            initial_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
            return controller.simulate_control_performance(initial_state, n_steps=50)

        result = StatisticalAnalyzer.monte_carlo_analysis(sample_robustness, n_samples=300)

        # Robustness validation
        assert result.mean < 10.0, "Poor average robustness"
        assert result.std < result.mean, "Excessive performance variation"

        # Distribution should be approximately normal for robust system
        if result.distribution_test_p_value < 0.01:
            warnings.warn("Performance distribution significantly non-normal")

    def test_monte_carlo_convergence_properties(self):
        """Test Monte Carlo convergence properties."""

        def deterministic_sample():
            return 5.0 + np.random.normal(0, 1.0)  # Known distribution: N(5, 1)

        # Test different sample sizes
        sample_sizes = [50, 100, 200, 500]
        results = []

        for n in sample_sizes:
            result = StatisticalAnalyzer.monte_carlo_analysis(deterministic_sample, n_samples=n)
            results.append(result)

        # Convergence checks
        means = [r.mean for r in results]
        std_errors = [r.convergence_analysis['mc_standard_error'] for r in results]

        # Mean should converge to true value (5.0)
        for mean in means:
            assert abs(mean - 5.0) < 0.5, f"Mean {mean} too far from expected value 5.0"

        # Standard error should decrease with sample size
        for i in range(1, len(std_errors)):
            ratio = std_errors[i] / std_errors[i-1]
            expected_ratio = np.sqrt(sample_sizes[i-1] / sample_sizes[i])
            assert abs(ratio - expected_ratio) < 0.3, "Standard error not decreasing correctly"

    def test_monte_carlo_distribution_validation(self):
        """Test distribution validation using Monte Carlo."""

        # Test different known distributions
        distributions = {
            'normal': lambda: np.random.normal(0, 1),
            'exponential': lambda: np.random.exponential(2.0),
            'uniform': lambda: np.random.uniform(-2, 2)
        }

        for dist_name, sampler in distributions.items():
            result = StatisticalAnalyzer.monte_carlo_analysis(sampler, n_samples=200)

            # All distributions should converge
            assert result.convergence_analysis.get('converged', False), f"{dist_name} failed to converge"

            # Outlier fraction should be reasonable
            assert result.outlier_fraction < 0.15, f"{dist_name} has excessive outliers"

            # Confidence intervals should be reasonable
            ci_width = result.confidence_interval_95[1] - result.confidence_interval_95[0]
            assert ci_width > 0, f"{dist_name} has invalid confidence interval"


@pytest.mark.statistical
class TestStatisticalComparison:
    """Statistical comparison and hypothesis testing."""

    def test_controller_comparison_statistical(self):
        """Statistical comparison of different controllers."""

        # Controller A: Conservative gains
        controller_a = MockStochasticController([1, 2, 1.5, 0.5, 1, 0.5], noise_level=0.01)

        # Controller B: Aggressive gains
        controller_b = MockStochasticController([4, 8, 6, 2, 4, 2], noise_level=0.01)

        # Generate performance samples
        n_trials = 150
        initial_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])

        samples_a = [controller_a.simulate_control_performance(initial_state, 50) for _ in range(n_trials)]
        samples_b = [controller_b.simulate_control_performance(initial_state, 50) for _ in range(n_trials)]

        # Statistical comparison
        test_result = StatisticalAnalyzer.two_sample_test(
            np.array(samples_a),
            np.array(samples_b),
            test_type='welch'
        )

        # Validation
        assert test_result.p_value >= 0, "p-value should be non-negative"
        assert test_result.p_value <= 1, "p-value should be at most 1"
        assert np.isfinite(test_result.effect_size), "Effect size should be finite"
        assert 0 <= test_result.power <= 1, "Power should be between 0 and 1"

        # Interpretation should be meaningful
        assert test_result.interpretation in [
            "Statistically significant but small effect",
            "Statistically significant with medium effect",
            "Statistically significant with large effect",
            "No significant difference detected"
        ]

    def test_noise_sensitivity_statistical_analysis(self):
        """Statistical analysis of noise sensitivity."""

        base_controller = MockStochasticController([2, 4, 3, 1, 2, 1])
        noise_levels = [0.001, 0.01, 0.05, 0.1]

        performance_by_noise = {}

        for noise_level in noise_levels:
            controller = MockStochasticController(base_controller.gains, noise_level)

            # Generate samples
            samples = []
            for _ in range(100):
                initial_state = np.random.normal(0, 0.05, 6)
                performance = controller.simulate_control_performance(initial_state, 30)
                samples.append(performance)

            performance_by_noise[noise_level] = np.array(samples)

        # Statistical analysis of noise effect
        low_noise = performance_by_noise[0.001]
        high_noise = performance_by_noise[0.1]

        noise_effect_test = StatisticalAnalyzer.two_sample_test(low_noise, high_noise)

        # High noise should generally increase performance metric (error)
        assert np.mean(high_noise) >= np.mean(low_noise), "High noise should increase error"

        # Should be statistically significant
        assert noise_effect_test.reject_null, "Noise effect should be significant"
        assert noise_effect_test.effect_size > 0, "Effect size should indicate degradation"

    def test_parameter_sensitivity_monte_carlo(self):
        """Monte Carlo analysis of parameter sensitivity."""

        def sample_parameter_sensitivity():
            # Base parameters
            base_gains = np.array([2, 4, 3, 1, 2, 1])

            # Random perturbations
            perturbation_std = 0.2  # 20% standard deviation
            gain_multipliers = np.random.lognormal(0, perturbation_std, 6)
            perturbed_gains = base_gains * gain_multipliers

            controller = MockStochasticController(perturbed_gains, noise_level=0.01)

            # Fixed test conditions
            initial_state = np.array([0.15, 0.1, 0.05, 0.0, 0.0, 0.0])
            return controller.simulate_control_performance(initial_state, 40)

        # Monte Carlo analysis
        result = StatisticalAnalyzer.monte_carlo_analysis(sample_parameter_sensitivity, n_samples=300)

        # Sensitivity analysis
        assert result.mean > 0, "Performance should be positive"

        # Coefficient of variation (relative standard deviation)
        cv = result.std / result.mean
        assert cv < 1.0, "Excessive parameter sensitivity"

        # Distribution should not be too skewed
        samples = result.samples
        skewness = stats.skew(samples)
        assert abs(skewness) < 2.0, "Highly skewed performance distribution"

    def test_statistical_power_analysis(self):
        """Test statistical power for detecting performance differences."""

        # Create controllers with known performance difference
        controller_good = MockStochasticController([3, 6, 4, 1.5, 3, 1.5], noise_level=0.01)
        controller_poor = MockStochasticController([1, 2, 1, 0.5, 1, 0.5], noise_level=0.01)

        sample_sizes = [20, 50, 100, 200]
        power_results = []

        for n in sample_sizes:
            # Generate samples
            good_samples = []
            poor_samples = []

            for _ in range(n):
                initial_state = np.random.normal(0, 0.1, 6)

                good_perf = controller_good.simulate_control_performance(initial_state, 30)
                poor_perf = controller_poor.simulate_control_performance(initial_state, 30)

                good_samples.append(good_perf)
                poor_samples.append(poor_perf)

            # Statistical test
            test_result = StatisticalAnalyzer.two_sample_test(
                np.array(good_samples),
                np.array(poor_samples)
            )

            power_results.append({
                'sample_size': n,
                'p_value': test_result.p_value,
                'effect_size': test_result.effect_size,
                'power': test_result.power,
                'significant': test_result.reject_null
            })

        # Power should generally increase with sample size
        p_values = [r['p_value'] for r in power_results]

        # Larger sample sizes should generally give smaller p-values (higher power)
        # At least the largest sample should detect the difference
        assert power_results[-1]['significant'], "Largest sample size should detect difference"


@pytest.mark.statistical
class TestStochasticValidation:
    """Validation of stochastic properties."""

    def test_random_walk_properties(self):
        """Test random walk properties in control systems."""

        def random_walk_controller_simulation():
            """Simulate controller with random walk disturbances."""
            n_steps = 100
            state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
            controller_gains = np.array([2, 4, 3, 1, 2, 1])

            cumulative_disturbance = 0.0
            total_error = 0.0

            for step in range(n_steps):
                # Random walk disturbance
                disturbance_increment = np.random.normal(0, 0.01)
                cumulative_disturbance += disturbance_increment

                # Controller with disturbance
                control = -np.dot(controller_gains, state) + cumulative_disturbance

                # System update
                state = state * 0.98 + control * 0.05 + np.random.normal(0, 0.005, 6)

                total_error += np.linalg.norm(state) * 0.01

            return total_error

        # Monte Carlo analysis
        result = StatisticalAnalyzer.monte_carlo_analysis(random_walk_controller_simulation, n_samples=200)

        # Random walk should increase performance variability
        assert result.std > 0.1, "Should have significant variability due to random walk"

        # But system should still be controllable
        assert result.mean < 50.0, "System should remain controllable despite random walk"

    def test_markov_property_validation(self):
        """Test Markov property in state transitions."""

        class MarkovController:
            def __init__(self):
                self.state_history = []

            def simulate_markov_process(self, n_steps=50):
                """Simulate control process with Markov property."""
                state = np.random.normal(0, 0.1, 3)  # Simplified 3D state
                self.state_history = [state.copy()]

                transition_matrix = np.array([
                    [0.9, 0.05, 0.05],
                    [0.05, 0.9, 0.05],
                    [0.05, 0.05, 0.9]
                ])

                for step in range(n_steps):
                    # Markov transition (current state only depends on previous state)
                    state = transition_matrix @ state + np.random.normal(0, 0.01, 3)
                    self.state_history.append(state.copy())

                # Return final deviation from origin
                return np.linalg.norm(state)

        controller = MarkovController()

        # Generate multiple Markov chains
        final_deviations = []
        for _ in range(100):
            final_dev = controller.simulate_markov_process()
            final_deviations.append(final_dev)

        final_deviations = np.array(final_deviations)

        # Statistical properties of Markov chain
        mean_deviation = np.mean(final_deviations)
        std_deviation = np.std(final_deviations)

        # Markov chain should be stable (bounded)
        assert mean_deviation < 5.0, "Markov chain should be bounded"
        assert std_deviation < mean_deviation, "Should have reasonable variability"

        # Test stationarity (simplified)
        # Compare first and second half of samples
        first_half = final_deviations[:50]
        second_half = final_deviations[50:]

        stationary_test = StatisticalAnalyzer.two_sample_test(first_half, second_half)

        # Should NOT reject null hypothesis for stationary process
        assert not stationary_test.reject_null or stationary_test.p_value > 0.01, "Process should be stationary"

    def test_central_limit_theorem_validation(self):
        """Test Central Limit Theorem in control system context."""

        def sample_controller_average_performance():
            """Sample average performance over multiple runs."""
            n_runs = 30  # Average over 30 control runs
            controller = MockStochasticController([2, 4, 3, 1, 2, 1], noise_level=0.02)

            performance_values = []
            for _ in range(n_runs):
                initial_state = np.random.uniform(-0.1, 0.1, 6)  # Uniform initial conditions
                perf = controller.simulate_control_performance(initial_state, 20)
                performance_values.append(perf)

            # Return sample mean (should be approximately normal by CLT)
            return np.mean(performance_values)

        # Generate distribution of sample means
        result = StatisticalAnalyzer.monte_carlo_analysis(sample_controller_average_performance, n_samples=200)

        # Central Limit Theorem validation
        # Distribution of sample means should be approximately normal
        assert result.distribution_test_p_value > 0.01, "Sample means should be approximately normal (CLT)"

        # Should have lower variability than individual samples
        # (This is implicit in the averaging process)
        assert result.std < 10.0, "Sample means should have lower variability"

    def test_confidence_interval_coverage(self):
        """Test confidence interval coverage properties."""

        # Known distribution: control performance ~ N(5, 2)
        true_mean = 5.0

        def sample_known_distribution():
            return np.random.normal(true_mean, 2.0)

        # Generate many confidence intervals
        coverage_95 = []
        coverage_99 = []

        n_experiments = 100
        for _ in range(n_experiments):
            result = StatisticalAnalyzer.monte_carlo_analysis(sample_known_distribution, n_samples=50)

            # Check if true mean is in confidence intervals
            ci_95 = result.confidence_interval_95
            ci_99 = result.confidence_interval_99

            coverage_95.append(ci_95[0] <= true_mean <= ci_95[1])
            coverage_99.append(ci_99[0] <= true_mean <= ci_99[1])

        # Coverage rates
        coverage_rate_95 = np.mean(coverage_95)
        coverage_rate_99 = np.mean(coverage_99)

        # Should be close to nominal coverage rates
        assert 0.90 <= coverage_rate_95 <= 0.98, f"95% CI coverage rate {coverage_rate_95:.3f} out of range"
        assert 0.95 <= coverage_rate_99 <= 1.00, f"99% CI coverage rate {coverage_rate_99:.3f} out of range"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])