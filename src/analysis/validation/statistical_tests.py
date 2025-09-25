#==========================================================================================\\\
#=================== src/analysis/validation/statistical_tests.py =======================\\\
#==========================================================================================\\\

"""Statistical testing framework for analysis validation.

This module provides comprehensive statistical testing capabilities for
validating analysis results, comparing methods, and ensuring statistical
rigor in control engineering applications.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
from scipy import stats
import warnings
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import StatisticalValidator, AnalysisResult, AnalysisStatus
from ..core.data_structures import StatisticalTestResult, ConfidenceInterval


class TestType(Enum):
    """Types of statistical tests."""
    NORMALITY = "normality"
    STATIONARITY = "stationarity"
    INDEPENDENCE = "independence"
    HOMOSCEDASTICITY = "homoscedasticity"
    HYPOTHESIS = "hypothesis"
    GOODNESS_OF_FIT = "goodness_of_fit"


class AlternativeHypothesis(Enum):
    """Alternative hypothesis types."""
    TWO_SIDED = "two-sided"
    GREATER = "greater"
    LESS = "less"


@dataclass
class StatisticalTestConfig:
    """Configuration for statistical tests."""
    # General settings
    significance_level: float = 0.05
    confidence_level: float = 0.95
    minimum_sample_size: int = 10

    # Normality tests
    normality_tests: List[str] = field(default_factory=lambda: ["shapiro", "anderson", "kolmogorov_smirnov"])

    # Hypothesis testing
    multiple_comparisons_correction: str = "bonferroni"  # "bonferroni", "holm", "fdr_bh"
    equal_variance_assumption: bool = False

    # Robustness settings
    robust_tests: bool = True
    bootstrap_samples: int = 1000
    permutation_samples: int = 1000

    # Power analysis
    desired_power: float = 0.8
    effect_size_convention: str = "cohen"  # "cohen", "glass", "hedges"


class StatisticalTestSuite(StatisticalValidator):
    """Comprehensive statistical testing suite."""

    def __init__(self, config: Optional[StatisticalTestConfig] = None):
        """Initialize statistical test suite.

        Parameters
        ----------
        config : StatisticalTestConfig, optional
            Configuration for statistical tests
        """
        self.config = config or StatisticalTestConfig()

    @property
    def validation_methods(self) -> List[str]:
        """List of validation methods supported."""
        return [
            "normality_tests",
            "stationarity_tests",
            "independence_tests",
            "homoscedasticity_tests",
            "hypothesis_tests",
            "goodness_of_fit_tests",
            "power_analysis",
            "effect_size_analysis"
        ]

    def validate(self, data: Union[List[Dict[str, float]], np.ndarray], **kwargs) -> AnalysisResult:
        """Perform comprehensive statistical validation.

        Parameters
        ----------
        data : Union[List[Dict[str, float]], np.ndarray]
            Data for statistical validation
        **kwargs
            Additional validation parameters:
            - test_types: List of specific tests to run
            - compare_groups: Additional data groups for comparison
            - reference_distribution: Expected distribution for goodness-of-fit

        Returns
        -------
        AnalysisResult
            Comprehensive statistical validation results
        """
        try:
            # Convert data to appropriate format
            processed_data = self._preprocess_data(data)

            if processed_data is None or len(processed_data) < self.config.minimum_sample_size:
                return AnalysisResult(
                    status=AnalysisStatus.ERROR,
                    message=f"Insufficient data for statistical testing (need >= {self.config.minimum_sample_size})",
                    data={}
                )

            results = {}

            # Determine which tests to run
            test_types = kwargs.get('test_types', self.validation_methods)

            # 1. Normality tests
            if "normality_tests" in test_types:
                normality_results = self._perform_normality_tests(processed_data)
                results['normality_tests'] = normality_results

            # 2. Stationarity tests
            if "stationarity_tests" in test_types:
                stationarity_results = self._perform_stationarity_tests(processed_data)
                results['stationarity_tests'] = stationarity_results

            # 3. Independence tests
            if "independence_tests" in test_types:
                independence_results = self._perform_independence_tests(processed_data)
                results['independence_tests'] = independence_results

            # 4. Homoscedasticity tests
            if "homoscedasticity_tests" in test_types:
                homoscedasticity_results = self._perform_homoscedasticity_tests(processed_data)
                results['homoscedasticity_tests'] = homoscedasticity_results

            # 5. Hypothesis tests
            if "hypothesis_tests" in test_types:
                compare_groups = kwargs.get('compare_groups', [])
                hypothesis_results = self._perform_hypothesis_tests(processed_data, compare_groups)
                results['hypothesis_tests'] = hypothesis_results

            # 6. Goodness of fit tests
            if "goodness_of_fit_tests" in test_types:
                reference_dist = kwargs.get('reference_distribution', 'normal')
                goodness_results = self._perform_goodness_of_fit_tests(processed_data, reference_dist)
                results['goodness_of_fit_tests'] = goodness_results

            # 7. Power analysis
            if "power_analysis" in test_types:
                power_results = self._perform_power_analysis(processed_data)
                results['power_analysis'] = power_results

            # 8. Effect size analysis
            if "effect_size_analysis" in test_types:
                effect_size_results = self._perform_effect_size_analysis(processed_data, compare_groups)
                results['effect_size_analysis'] = effect_size_results

            # Overall validation summary
            validation_summary = self._generate_validation_summary(results)
            results['validation_summary'] = validation_summary

            return AnalysisResult(
                status=AnalysisStatus.SUCCESS,
                message="Statistical validation completed successfully",
                data=results,
                metadata={
                    'validator': 'StatisticalTestSuite',
                    'config': self.config.__dict__,
                    'sample_size': len(processed_data)
                }
            )

        except Exception as e:
            return AnalysisResult(
                status=AnalysisStatus.ERROR,
                message=f"Statistical validation failed: {str(e)}",
                data={'error_details': str(e)}
            )

    def _preprocess_data(self, data: Union[List[Dict[str, float]], np.ndarray]) -> Optional[np.ndarray]:
        """Preprocess data for statistical testing."""
        if isinstance(data, list):
            if not data:
                return None

            # Extract numeric values from list of dictionaries
            if isinstance(data[0], dict):
                # Use first numeric value found
                for key, value in data[0].items():
                    if isinstance(value, (int, float)):
                        return np.array([d.get(key, np.nan) for d in data])
                return None
            else:
                return np.array(data)

        elif isinstance(data, np.ndarray):
            if data.ndim > 1:
                # Use first column if multidimensional
                return data[:, 0].flatten()
            else:
                return data.flatten()

        else:
            return None

    def _perform_normality_tests(self, data: np.ndarray) -> Dict[str, Any]:
        """Perform normality tests."""
        results = {}
        valid_data = data[np.isfinite(data)]

        if len(valid_data) < 3:
            return {'error': 'Insufficient data for normality tests'}

        # Shapiro-Wilk test
        if "shapiro" in self.config.normality_tests and len(valid_data) <= 5000:
            try:
                stat, p_value = stats.shapiro(valid_data)
                results['shapiro_wilk'] = StatisticalTestResult(
                    test_name="Shapiro-Wilk",
                    statistic=float(stat),
                    p_value=float(p_value),
                    critical_value=None,
                    confidence_level=self.config.confidence_level,
                    conclusion="Normal" if p_value > self.config.significance_level else "Non-normal"
                ).__dict__
            except Exception as e:
                results['shapiro_wilk'] = {'error': str(e)}

        # Anderson-Darling test
        if "anderson" in self.config.normality_tests:
            try:
                result = stats.anderson(valid_data, dist='norm')
                # Use 5% significance level
                critical_value = result.critical_values[2] if len(result.critical_values) > 2 else result.critical_values[-1]
                p_value = 0.05 if result.statistic > critical_value else 0.1  # Approximate

                results['anderson_darling'] = StatisticalTestResult(
                    test_name="Anderson-Darling",
                    statistic=float(result.statistic),
                    p_value=float(p_value),
                    critical_value=float(critical_value),
                    confidence_level=self.config.confidence_level,
                    conclusion="Normal" if result.statistic <= critical_value else "Non-normal"
                ).__dict__
            except Exception as e:
                results['anderson_darling'] = {'error': str(e)}

        # Kolmogorov-Smirnov test
        if "kolmogorov_smirnov" in self.config.normality_tests:
            try:
                # Test against standard normal
                normalized_data = (valid_data - np.mean(valid_data)) / np.std(valid_data)
                stat, p_value = stats.kstest(normalized_data, 'norm')

                results['kolmogorov_smirnov'] = StatisticalTestResult(
                    test_name="Kolmogorov-Smirnov",
                    statistic=float(stat),
                    p_value=float(p_value),
                    critical_value=None,
                    confidence_level=self.config.confidence_level,
                    conclusion="Normal" if p_value > self.config.significance_level else "Non-normal"
                ).__dict__
            except Exception as e:
                results['kolmogorov_smirnov'] = {'error': str(e)}

        # D'Agostino-Pearson test
        try:
            stat, p_value = stats.normaltest(valid_data)
            results['dagostino_pearson'] = StatisticalTestResult(
                test_name="D'Agostino-Pearson",
                statistic=float(stat),
                p_value=float(p_value),
                critical_value=None,
                confidence_level=self.config.confidence_level,
                conclusion="Normal" if p_value > self.config.significance_level else "Non-normal"
            ).__dict__
        except Exception as e:
            results['dagostino_pearson'] = {'error': str(e)}

        return results

    def _perform_stationarity_tests(self, data: np.ndarray) -> Dict[str, Any]:
        """Perform stationarity tests."""
        results = {}
        valid_data = data[np.isfinite(data)]

        if len(valid_data) < 10:
            return {'error': 'Insufficient data for stationarity tests'}

        # Augmented Dickey-Fuller test (simplified implementation)
        results['augmented_dickey_fuller'] = self._adf_test(valid_data)

        # KPSS test (simplified implementation)
        results['kpss'] = self._kpss_test(valid_data)

        # Variance ratio test
        results['variance_ratio'] = self._variance_ratio_test(valid_data)

        return results

    def _perform_independence_tests(self, data: np.ndarray) -> Dict[str, Any]:
        """Perform independence tests."""
        results = {}
        valid_data = data[np.isfinite(data)]

        if len(valid_data) < 10:
            return {'error': 'Insufficient data for independence tests'}

        # Ljung-Box test for autocorrelation
        results['ljung_box'] = self._ljung_box_test(valid_data)

        # Durbin-Watson test
        results['durbin_watson'] = self._durbin_watson_test(valid_data)

        # Runs test
        results['runs_test'] = self._runs_test(valid_data)

        return results

    def _perform_homoscedasticity_tests(self, data: np.ndarray) -> Dict[str, Any]:
        """Perform homoscedasticity tests."""
        results = {}
        valid_data = data[np.isfinite(data)]

        if len(valid_data) < 20:
            return {'error': 'Insufficient data for homoscedasticity tests'}

        # Split data into groups and test for equal variances
        mid_point = len(valid_data) // 2
        group1 = valid_data[:mid_point]
        group2 = valid_data[mid_point:]

        # Levene's test
        try:
            stat, p_value = stats.levene(group1, group2)
            results['levene'] = StatisticalTestResult(
                test_name="Levene",
                statistic=float(stat),
                p_value=float(p_value),
                confidence_level=self.config.confidence_level,
                conclusion="Homoscedastic" if p_value > self.config.significance_level else "Heteroscedastic"
            ).__dict__
        except Exception as e:
            results['levene'] = {'error': str(e)}

        # Bartlett's test
        try:
            stat, p_value = stats.bartlett(group1, group2)
            results['bartlett'] = StatisticalTestResult(
                test_name="Bartlett",
                statistic=float(stat),
                p_value=float(p_value),
                confidence_level=self.config.confidence_level,
                conclusion="Homoscedastic" if p_value > self.config.significance_level else "Heteroscedastic"
            ).__dict__
        except Exception as e:
            results['bartlett'] = {'error': str(e)}

        return results

    def _perform_hypothesis_tests(self, data: np.ndarray, compare_groups: List[np.ndarray]) -> Dict[str, Any]:
        """Perform hypothesis tests."""
        results = {}

        # One-sample tests
        results['one_sample'] = self._one_sample_tests(data)

        # Two-sample tests (if comparison groups provided)
        if compare_groups:
            results['two_sample'] = {}
            for i, group in enumerate(compare_groups):
                group_valid = group[np.isfinite(group)]
                if len(group_valid) >= self.config.minimum_sample_size:
                    results['two_sample'][f'group_{i}'] = self._two_sample_tests(data, group_valid)

        return results

    def _perform_goodness_of_fit_tests(self, data: np.ndarray, reference_distribution: str) -> Dict[str, Any]:
        """Perform goodness of fit tests."""
        results = {}
        valid_data = data[np.isfinite(data)]

        if len(valid_data) < 5:
            return {'error': 'Insufficient data for goodness of fit tests'}

        # Chi-square goodness of fit test
        results['chi_square'] = self._chi_square_goodness_of_fit(valid_data, reference_distribution)

        # Kolmogorov-Smirnov goodness of fit
        results['ks_goodness_of_fit'] = self._ks_goodness_of_fit(valid_data, reference_distribution)

        return results

    def _perform_power_analysis(self, data: np.ndarray) -> Dict[str, Any]:
        """Perform power analysis."""
        valid_data = data[np.isfinite(data)]

        if len(valid_data) < self.config.minimum_sample_size:
            return {'error': 'Insufficient data for power analysis'}

        # Estimate effect size
        effect_size = abs(np.mean(valid_data)) / (np.std(valid_data) + 1e-12)

        # Power calculation (simplified)
        sample_size = len(valid_data)
        alpha = self.config.significance_level

        # Approximate power for one-sample t-test
        from scipy.stats import norm, t

        df = sample_size - 1
        t_critical = t.ppf(1 - alpha/2, df)
        t_obs = effect_size * np.sqrt(sample_size)

        power = 1 - t.cdf(t_critical - t_obs, df) + t.cdf(-t_critical - t_obs, df)

        return {
            'estimated_effect_size': float(effect_size),
            'sample_size': int(sample_size),
            'estimated_power': float(power),
            'desired_power': self.config.desired_power,
            'power_adequate': bool(power >= self.config.desired_power),
            'recommended_sample_size': self._calculate_required_sample_size(effect_size, self.config.desired_power, alpha)
        }

    def _perform_effect_size_analysis(self, data: np.ndarray, compare_groups: List[np.ndarray]) -> Dict[str, Any]:
        """Perform effect size analysis."""
        results = {}
        valid_data = data[np.isfinite(data)]

        # Cohen's d for each comparison group
        if compare_groups:
            for i, group in enumerate(compare_groups):
                group_valid = group[np.isfinite(group)]
                if len(group_valid) >= self.config.minimum_sample_size:
                    cohens_d = self._calculate_cohens_d(valid_data, group_valid)
                    results[f'cohens_d_group_{i}'] = {
                        'value': float(cohens_d),
                        'interpretation': self._interpret_effect_size(cohens_d)
                    }

        # Effect size within group (standardized mean)
        standardized_mean = abs(np.mean(valid_data)) / (np.std(valid_data) + 1e-12)
        results['within_group_effect_size'] = {
            'standardized_mean': float(standardized_mean),
            'interpretation': self._interpret_effect_size(standardized_mean)
        }

        return results

    # Helper methods for specific tests

    def _adf_test(self, data: np.ndarray) -> Dict[str, Any]:
        """Simplified Augmented Dickey-Fuller test."""
        # Simplified implementation - in practice would use statsmodels
        try:
            # Simple regression: diff(y) = alpha + beta*y_lag + error
            y = data[1:]
            y_lag = data[:-1]
            y_diff = np.diff(data)

            # OLS regression
            X = np.column_stack([np.ones(len(y_lag)), y_lag])
            beta = np.linalg.lstsq(X, y_diff, rcond=None)[0]

            # Test statistic (simplified)
            residuals = y_diff - X @ beta
            std_error = np.sqrt(np.sum(residuals**2) / (len(residuals) - 2))
            t_stat = beta[1] / (std_error / np.sqrt(np.sum((y_lag - np.mean(y_lag))**2)))

            # Approximate critical value
            critical_value = -2.86  # 5% critical value approximation

            return {
                'test_statistic': float(t_stat),
                'critical_value': critical_value,
                'p_value': 0.05 if t_stat > critical_value else 0.01,  # Approximate
                'conclusion': "Stationary" if t_stat < critical_value else "Non-stationary"
            }

        except Exception as e:
            return {'error': str(e)}

    def _kpss_test(self, data: np.ndarray) -> Dict[str, Any]:
        """Simplified KPSS test."""
        try:
            # Compute cumulative sum
            demeaned = data - np.mean(data)
            cumsum = np.cumsum(demeaned)

            # Compute test statistic
            n = len(data)
            variance_estimate = np.sum(demeaned**2) / n
            kpss_stat = np.sum(cumsum**2) / (n**2 * variance_estimate)

            # Critical value (5% level)
            critical_value = 0.463

            return {
                'test_statistic': float(kpss_stat),
                'critical_value': critical_value,
                'p_value': 0.05 if kpss_stat > critical_value else 0.1,  # Approximate
                'conclusion': "Stationary" if kpss_stat < critical_value else "Non-stationary"
            }

        except Exception as e:
            return {'error': str(e)}

    def _variance_ratio_test(self, data: np.ndarray) -> Dict[str, Any]:
        """Variance ratio test for random walk."""
        try:
            n = len(data)
            if n < 16:
                return {'error': 'Insufficient data for variance ratio test'}

            # Compute variance ratio for lag 2
            returns = np.diff(data)

            # Variance of 1-period returns
            var_1 = np.var(returns, ddof=1)

            # Variance of 2-period returns (non-overlapping)
            returns_2 = returns[::2] + returns[1::2]  # Sum of pairs
            var_2 = np.var(returns_2, ddof=1)

            # Variance ratio
            vr = var_2 / (2 * var_1) if var_1 > 0 else 1.0

            # Test statistic (simplified)
            vr_stat = np.sqrt(n) * (vr - 1)

            return {
                'variance_ratio': float(vr),
                'test_statistic': float(vr_stat),
                'expected_vr': 1.0,
                'conclusion': "Random walk" if abs(vr - 1) < 0.1 else "Not random walk"
            }

        except Exception as e:
            return {'error': str(e)}

    def _ljung_box_test(self, data: np.ndarray) -> Dict[str, Any]:
        """Ljung-Box test for autocorrelation."""
        try:
            n = len(data)
            max_lag = min(10, n // 4)

            if max_lag < 1:
                return {'error': 'Insufficient data for Ljung-Box test'}

            # Compute autocorrelations
            autocorrs = []
            for lag in range(1, max_lag + 1):
                if lag < n:
                    autocorr = np.corrcoef(data[:-lag], data[lag:])[0, 1]
                    if np.isfinite(autocorr):
                        autocorrs.append(autocorr)

            if not autocorrs:
                return {'error': 'Could not compute autocorrelations'}

            # Ljung-Box statistic
            lb_stat = n * (n + 2) * sum((autocorr**2) / (n - lag - 1)
                                       for lag, autocorr in enumerate(autocorrs, 1))

            # Chi-square critical value
            critical_value = stats.chi2.ppf(1 - self.config.significance_level, len(autocorrs))
            p_value = 1 - stats.chi2.cdf(lb_stat, len(autocorrs))

            return {
                'test_statistic': float(lb_stat),
                'degrees_of_freedom': len(autocorrs),
                'critical_value': float(critical_value),
                'p_value': float(p_value),
                'conclusion': "Independent" if p_value > self.config.significance_level else "Autocorrelated"
            }

        except Exception as e:
            return {'error': str(e)}

    def _durbin_watson_test(self, data: np.ndarray) -> Dict[str, Any]:
        """Durbin-Watson test for autocorrelation."""
        try:
            if len(data) < 3:
                return {'error': 'Insufficient data for Durbin-Watson test'}

            # Compute residuals (using data as residuals)
            residuals = data - np.mean(data)

            # Durbin-Watson statistic
            diff_squared = np.sum(np.diff(residuals)**2)
            residuals_squared = np.sum(residuals**2)

            dw_stat = diff_squared / residuals_squared if residuals_squared > 0 else 2.0

            return {
                'test_statistic': float(dw_stat),
                'interpretation': self._interpret_durbin_watson(dw_stat),
                'expected_value': 2.0
            }

        except Exception as e:
            return {'error': str(e)}

    def _runs_test(self, data: np.ndarray) -> Dict[str, Any]:
        """Runs test for randomness."""
        try:
            if len(data) < 10:
                return {'error': 'Insufficient data for runs test'}

            median = np.median(data)

            # Convert to binary sequence
            binary_seq = (data > median).astype(int)

            # Count runs
            runs = 1
            for i in range(1, len(binary_seq)):
                if binary_seq[i] != binary_seq[i-1]:
                    runs += 1

            # Expected number of runs
            n1 = np.sum(binary_seq)
            n2 = len(binary_seq) - n1

            if n1 == 0 or n2 == 0:
                return {'error': 'No variation in data above/below median'}

            expected_runs = (2 * n1 * n2) / (n1 + n2) + 1
            variance_runs = (2 * n1 * n2 * (2 * n1 * n2 - n1 - n2)) / ((n1 + n2)**2 * (n1 + n2 - 1))

            # Test statistic
            if variance_runs > 0:
                z_stat = (runs - expected_runs) / np.sqrt(variance_runs)
                p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
            else:
                z_stat = 0.0
                p_value = 1.0

            return {
                'observed_runs': int(runs),
                'expected_runs': float(expected_runs),
                'test_statistic': float(z_stat),
                'p_value': float(p_value),
                'conclusion': "Random" if p_value > self.config.significance_level else "Non-random"
            }

        except Exception as e:
            return {'error': str(e)}

    def _one_sample_tests(self, data: np.ndarray) -> Dict[str, Any]:
        """One-sample statistical tests."""
        results = {}
        valid_data = data[np.isfinite(data)]

        if len(valid_data) < 3:
            return {'error': 'Insufficient data for one-sample tests'}

        # One-sample t-test (test if mean is significantly different from 0)
        try:
            t_stat, p_value = stats.ttest_1samp(valid_data, 0)
            results['t_test_zero_mean'] = StatisticalTestResult(
                test_name="One-sample t-test (mean=0)",
                statistic=float(t_stat),
                p_value=float(p_value),
                confidence_level=self.config.confidence_level,
                conclusion="Mean ≠ 0" if p_value < self.config.significance_level else "Mean = 0"
            ).__dict__
        except Exception as e:
            results['t_test_zero_mean'] = {'error': str(e)}

        # Wilcoxon signed-rank test (non-parametric alternative)
        try:
            if len(valid_data) >= 6:  # Minimum for Wilcoxon
                stat, p_value = stats.wilcoxon(valid_data)
                results['wilcoxon_signed_rank'] = StatisticalTestResult(
                    test_name="Wilcoxon signed-rank",
                    statistic=float(stat),
                    p_value=float(p_value),
                    confidence_level=self.config.confidence_level,
                    conclusion="Median ≠ 0" if p_value < self.config.significance_level else "Median = 0"
                ).__dict__
        except Exception as e:
            results['wilcoxon_signed_rank'] = {'error': str(e)}

        return results

    def _two_sample_tests(self, data1: np.ndarray, data2: np.ndarray) -> Dict[str, Any]:
        """Two-sample statistical tests."""
        results = {}

        # Independent t-test
        try:
            if self.config.equal_variance_assumption:
                t_stat, p_value = stats.ttest_ind(data1, data2, equal_var=True)
                test_name = "Two-sample t-test (equal variances)"
            else:
                t_stat, p_value = stats.ttest_ind(data1, data2, equal_var=False)
                test_name = "Welch's t-test (unequal variances)"

            results['t_test'] = StatisticalTestResult(
                test_name=test_name,
                statistic=float(t_stat),
                p_value=float(p_value),
                confidence_level=self.config.confidence_level,
                conclusion="Means differ" if p_value < self.config.significance_level else "Means equal"
            ).__dict__
        except Exception as e:
            results['t_test'] = {'error': str(e)}

        # Mann-Whitney U test (non-parametric)
        try:
            u_stat, p_value = stats.mannwhitneyu(data1, data2, alternative='two-sided')
            results['mann_whitney'] = StatisticalTestResult(
                test_name="Mann-Whitney U",
                statistic=float(u_stat),
                p_value=float(p_value),
                confidence_level=self.config.confidence_level,
                conclusion="Distributions differ" if p_value < self.config.significance_level else "Distributions equal"
            ).__dict__
        except Exception as e:
            results['mann_whitney'] = {'error': str(e)}

        return results

    def _chi_square_goodness_of_fit(self, data: np.ndarray, distribution: str) -> Dict[str, Any]:
        """Chi-square goodness of fit test."""
        try:
            # Create bins
            n_bins = min(10, int(np.sqrt(len(data))))
            observed_freq, bin_edges = np.histogram(data, bins=n_bins)

            # Expected frequencies based on distribution
            if distribution == 'normal':
                mean, std = np.mean(data), np.std(data)
                expected_freq = []
                for i in range(len(bin_edges) - 1):
                    p = stats.norm.cdf(bin_edges[i+1], mean, std) - stats.norm.cdf(bin_edges[i], mean, std)
                    expected_freq.append(p * len(data))
                expected_freq = np.array(expected_freq)
            else:
                expected_freq = np.full(n_bins, len(data) / n_bins)

            # Remove bins with very low expected frequency
            mask = expected_freq >= 5
            if np.sum(mask) < 3:
                return {'error': 'Too few bins with adequate expected frequency'}

            observed_freq = observed_freq[mask]
            expected_freq = expected_freq[mask]

            # Chi-square statistic
            chi2_stat = np.sum((observed_freq - expected_freq)**2 / expected_freq)
            df = len(observed_freq) - 1 - (2 if distribution == 'normal' else 0)  # Subtract parameters estimated
            p_value = 1 - stats.chi2.cdf(chi2_stat, df)

            return {
                'test_statistic': float(chi2_stat),
                'degrees_of_freedom': int(df),
                'p_value': float(p_value),
                'conclusion': f"Fits {distribution}" if p_value > self.config.significance_level else f"Does not fit {distribution}"
            }

        except Exception as e:
            return {'error': str(e)}

    def _ks_goodness_of_fit(self, data: np.ndarray, distribution: str) -> Dict[str, Any]:
        """Kolmogorov-Smirnov goodness of fit test."""
        try:
            if distribution == 'normal':
                mean, std = np.mean(data), np.std(data)
                stat, p_value = stats.kstest(data, lambda x: stats.norm.cdf(x, mean, std))
            elif distribution == 'uniform':
                min_val, max_val = np.min(data), np.max(data)
                stat, p_value = stats.kstest(data, lambda x: stats.uniform.cdf(x, min_val, max_val - min_val))
            else:
                return {'error': f'Distribution {distribution} not supported'}

            return {
                'test_statistic': float(stat),
                'p_value': float(p_value),
                'conclusion': f"Fits {distribution}" if p_value > self.config.significance_level else f"Does not fit {distribution}"
            }

        except Exception as e:
            return {'error': str(e)}

    def _calculate_cohens_d(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """Calculate Cohen's d effect size."""
        mean1, mean2 = np.mean(group1), np.mean(group2)
        std1, std2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
        n1, n2 = len(group1), len(group2)

        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))

        return (mean1 - mean2) / pooled_std if pooled_std > 0 else 0.0

    def _interpret_effect_size(self, effect_size: float) -> str:
        """Interpret effect size magnitude."""
        abs_effect = abs(effect_size)
        if abs_effect < 0.2:
            return "negligible"
        elif abs_effect < 0.5:
            return "small"
        elif abs_effect < 0.8:
            return "medium"
        else:
            return "large"

    def _interpret_durbin_watson(self, dw_stat: float) -> str:
        """Interpret Durbin-Watson statistic."""
        if dw_stat < 1.5:
            return "Positive autocorrelation"
        elif dw_stat > 2.5:
            return "Negative autocorrelation"
        else:
            return "No significant autocorrelation"

    def _calculate_required_sample_size(self, effect_size: float, power: float, alpha: float) -> int:
        """Calculate required sample size for given power."""
        # Simplified calculation for one-sample t-test
        from scipy.stats import norm, t

        z_alpha = norm.ppf(1 - alpha/2)
        z_beta = norm.ppf(power)

        # Approximate sample size
        n_approx = ((z_alpha + z_beta) / effect_size)**2

        return max(10, int(np.ceil(n_approx)))

    def _generate_validation_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall validation summary."""
        summary = {
            'overall_validity': True,
            'failed_tests': [],
            'warnings': [],
            'recommendations': []
        }

        # Check normality
        if 'normality_tests' in results:
            normality_passed = False
            for test_name, test_result in results['normality_tests'].items():
                if isinstance(test_result, dict) and 'conclusion' in test_result:
                    if 'Normal' in test_result['conclusion']:
                        normality_passed = True
                        break

            if not normality_passed:
                summary['warnings'].append('Data does not appear to be normally distributed')
                summary['recommendations'].append('Consider non-parametric tests or data transformation')

        # Check stationarity
        if 'stationarity_tests' in results:
            stationarity_issues = []
            for test_name, test_result in results['stationarity_tests'].items():
                if isinstance(test_result, dict) and 'conclusion' in test_result:
                    if 'Non-stationary' in test_result['conclusion']:
                        stationarity_issues.append(test_name)

            if stationarity_issues:
                summary['warnings'].append('Data shows non-stationarity in some tests')
                summary['recommendations'].append('Consider differencing or trend removal')

        # Check power
        if 'power_analysis' in results:
            power_result = results['power_analysis']
            if isinstance(power_result, dict) and not power_result.get('power_adequate', True):
                summary['warnings'].append('Statistical power may be insufficient')
                summary['recommendations'].append(f"Consider increasing sample size to {power_result.get('recommended_sample_size', 'unknown')}")

        return summary


def create_statistical_test_suite(config: Optional[Dict[str, Any]] = None) -> StatisticalTestSuite:
    """Factory function to create statistical test suite.

    Parameters
    ----------
    config : Dict[str, Any], optional
        Configuration parameters

    Returns
    -------
    StatisticalTestSuite
        Configured statistical test suite
    """
    if config is not None:
        test_config = StatisticalTestConfig(**config)
    else:
        test_config = StatisticalTestConfig()

    return StatisticalTestSuite(test_config)