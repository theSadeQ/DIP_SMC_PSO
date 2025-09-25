#==========================================================================================\\\
#======================== src/utils/analysis/statistics.py =============================\\\
#==========================================================================================\\\

"""
Statistical analysis utilities for control system performance evaluation.

Provides comprehensive statistical tools for analyzing control system
performance, including confidence intervals, hypothesis testing, and
Monte Carlo analysis validation.
"""

from __future__ import annotations
import numpy as np
from scipy.stats import t, f, chi2
from typing import Tuple, Dict, List, Optional
import warnings

def confidence_interval(
    data: np.ndarray,
    confidence: float = 0.95
) -> Tuple[float, float]:
    """Return the mean and half‑width of a Student‑t confidence interval.

    Given an array of samples, compute the sample mean and the half‑width
    of the two‑sided confidence interval at the specified confidence
    level. The half‑width is ``tcrit * s / sqrt(n)``, where ``tcrit`` is
    the t‑distribution critical value, ``s`` is the sample standard
    deviation (ddof=1) and ``n`` is the number of samples.

    Parameters
    ----------
    data : np.ndarray
        One‑dimensional array of observations.
    confidence : float, optional
        Desired confidence level in (0,1). Defaults to 0.95.

    Returns
    -------
    mean : float
        Sample mean.
    half_width : float
        Half‑width of the confidence interval. ``NaN`` when ``n < 2``.
    """
    data = np.asarray(data, dtype=float).ravel()
    n = data.size
    mean = float(np.mean(data)) if n > 0 else np.nan

    if n < 2:
        return mean, float('nan')

    s = float(np.std(data, ddof=1))
    # Two‑sided t‑critical value
    alpha = 1.0 - confidence
    tcrit = float(t.ppf(1.0 - alpha / 2.0, df=n - 1))
    half_width = tcrit * s / np.sqrt(n)

    return mean, half_width

def bootstrap_confidence_interval(
    data: np.ndarray,
    statistic_func: callable = np.mean,
    confidence: float = 0.95,
    n_bootstrap: int = 10000
) -> Tuple[float, Tuple[float, float]]:
    """Compute bootstrap confidence interval for any statistic.

    Parameters
    ----------
    data : np.ndarray
        Original sample data.
    statistic_func : callable
        Function to compute the statistic of interest.
    confidence : float
        Confidence level (default: 0.95).
    n_bootstrap : int
        Number of bootstrap samples.

    Returns
    -------
    statistic : float
        Original statistic value.
    ci : tuple
        (lower_bound, upper_bound) of confidence interval.
    """
    data = np.asarray(data)
    n = len(data)

    # Original statistic
    original_stat = statistic_func(data)

    # Bootstrap samples
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        bootstrap_sample = np.random.choice(data, size=n, replace=True)
        bootstrap_stats.append(statistic_func(bootstrap_sample))

    bootstrap_stats = np.array(bootstrap_stats)

    # Percentile method
    alpha = 1.0 - confidence
    lower_percentile = 100 * (alpha / 2)
    upper_percentile = 100 * (1 - alpha / 2)

    ci_lower = np.percentile(bootstrap_stats, lower_percentile)
    ci_upper = np.percentile(bootstrap_stats, upper_percentile)

    return original_stat, (ci_lower, ci_upper)

def welch_t_test(
    group1: np.ndarray,
    group2: np.ndarray,
    alpha: float = 0.05
) -> Dict[str, float]:
    """Perform Welch's t-test for unequal variances.

    Parameters
    ----------
    group1, group2 : np.ndarray
        Two independent samples to compare.
    alpha : float
        Significance level (default: 0.05).

    Returns
    -------
    results : dict
        Dictionary containing test statistic, p-value, degrees of freedom,
        and decision about null hypothesis.
    """
    x1, x2 = np.asarray(group1), np.asarray(group2)
    n1, n2 = len(x1), len(x2)

    if n1 < 2 or n2 < 2:
        raise ValueError("Each group must have at least 2 observations")

    # Sample statistics
    mean1, mean2 = np.mean(x1), np.mean(x2)
    var1, var2 = np.var(x1, ddof=1), np.var(x2, ddof=1)

    # Welch's t-statistic
    t_stat = (mean1 - mean2) / np.sqrt(var1/n1 + var2/n2)

    # Welch's degrees of freedom
    numerator = (var1/n1 + var2/n2)**2
    denominator = (var1/n1)**2/(n1-1) + (var2/n2)**2/(n2-1)
    df = numerator / denominator

    # Two-tailed p-value
    p_value = 2 * (1 - t.cdf(abs(t_stat), df))

    # Decision
    reject_null = p_value < alpha

    return {
        't_statistic': t_stat,
        'p_value': p_value,
        'degrees_of_freedom': df,
        'alpha': alpha,
        'reject_null_hypothesis': reject_null,
        'mean_difference': mean1 - mean2,
        'effect_size': (mean1 - mean2) / np.sqrt((var1 + var2) / 2)  # Cohen's d approximation
    }

def one_way_anova(
    groups: List[np.ndarray],
    alpha: float = 0.05
) -> Dict[str, float]:
    """Perform one-way ANOVA.

    Parameters
    ----------
    groups : list of np.ndarray
        List of independent groups to compare.
    alpha : float
        Significance level.

    Returns
    -------
    results : dict
        ANOVA results including F-statistic, p-value, and effect size.
    """
    groups = [np.asarray(group) for group in groups]
    k = len(groups)  # number of groups

    if k < 2:
        raise ValueError("Need at least 2 groups for ANOVA")

    # Check sample sizes
    group_sizes = [len(group) for group in groups]
    if any(n < 2 for n in group_sizes):
        raise ValueError("Each group must have at least 2 observations")

    # Total sample size
    N = sum(group_sizes)

    # Group means and overall mean
    group_means = [np.mean(group) for group in groups]
    overall_mean = np.mean(np.concatenate(groups))

    # Sum of squares between groups (SSB)
    SSB = sum(n * (mean - overall_mean)**2 for n, mean in zip(group_sizes, group_means))

    # Sum of squares within groups (SSW)
    SSW = sum(np.sum((group - np.mean(group))**2) for group in groups)

    # Degrees of freedom
    df_between = k - 1
    df_within = N - k
    df_total = N - 1

    # Mean squares
    MSB = SSB / df_between
    MSW = SSW / df_within

    # F-statistic
    F_stat = MSB / MSW

    # p-value
    p_value = 1 - f.cdf(F_stat, df_between, df_within)

    # Effect size (eta-squared)
    eta_squared = SSB / (SSB + SSW)

    return {
        'F_statistic': F_stat,
        'p_value': p_value,
        'df_between': df_between,
        'df_within': df_within,
        'alpha': alpha,
        'reject_null_hypothesis': p_value < alpha,
        'eta_squared': eta_squared,
        'sum_squares_between': SSB,
        'sum_squares_within': SSW,
        'mean_square_between': MSB,
        'mean_square_within': MSW
    }

def monte_carlo_analysis(
    simulation_func: callable,
    parameter_distributions: Dict[str, callable],
    n_trials: int = 1000,
    confidence_level: float = 0.95
) -> Dict[str, any]:
    """Perform Monte Carlo analysis of system performance.

    Parameters
    ----------
    simulation_func : callable
        Function that takes parameters and returns performance metrics.
    parameter_distributions : dict
        Dictionary mapping parameter names to random sampling functions.
    n_trials : int
        Number of Monte Carlo trials.
    confidence_level : float
        Confidence level for intervals.

    Returns
    -------
    results : dict
        Monte Carlo analysis results including statistics and confidence intervals.
    """
    results = []

    for trial in range(n_trials):
        # Sample parameters
        parameters = {
            name: dist() for name, dist in parameter_distributions.items()
        }

        # Run simulation
        try:
            performance = simulation_func(**parameters)
            results.append(performance)
        except Exception as e:
            warnings.warn(f"Trial {trial} failed: {e}")
            continue

    if not results:
        raise RuntimeError("All Monte Carlo trials failed")

    # Convert to numpy array for analysis
    results_array = np.array(results)

    # Compute statistics
    mean_performance = np.mean(results_array)
    std_performance = np.std(results_array, ddof=1)
    median_performance = np.median(results_array)

    # Confidence interval
    mean_ci, half_width = confidence_interval(results_array, confidence_level)

    # Percentiles
    percentiles = [5, 25, 75, 95]
    perc_values = [np.percentile(results_array, p) for p in percentiles]

    return {
        'n_successful_trials': len(results),
        'n_failed_trials': n_trials - len(results),
        'mean': mean_performance,
        'std': std_performance,
        'median': median_performance,
        'confidence_interval': {
            'level': confidence_level,
            'mean': mean_ci,
            'half_width': half_width,
            'lower': mean_ci - half_width,
            'upper': mean_ci + half_width
        },
        'percentiles': dict(zip(percentiles, perc_values)),
        'raw_results': results_array
    }

def performance_comparison_summary(
    controller_results: Dict[str, np.ndarray],
    metric_name: str = "Performance",
    confidence_level: float = 0.95
) -> Dict[str, any]:
    """Generate comprehensive comparison summary for multiple controllers.

    Parameters
    ----------
    controller_results : dict
        Dictionary mapping controller names to performance arrays.
    metric_name : str
        Name of the performance metric being compared.
    confidence_level : float
        Confidence level for intervals.

    Returns
    -------
    summary : dict
        Comprehensive comparison summary with statistics and tests.
    """
    summary = {
        'metric_name': metric_name,
        'confidence_level': confidence_level,
        'controllers': {},
        'pairwise_comparisons': {},
        'anova': None
    }

    # Individual controller statistics
    for name, results in controller_results.items():
        mean, half_width = confidence_interval(results, confidence_level)

        summary['controllers'][name] = {
            'n_samples': len(results),
            'mean': mean,
            'std': np.std(results, ddof=1),
            'median': np.median(results),
            'confidence_interval': {
                'lower': mean - half_width,
                'upper': mean + half_width,
                'half_width': half_width
            },
            'min': np.min(results),
            'max': np.max(results)
        }

    # Pairwise comparisons (Welch's t-tests)
    controller_names = list(controller_results.keys())
    for i, name1 in enumerate(controller_names):
        for name2 in controller_names[i+1:]:
            comparison_key = f"{name1}_vs_{name2}"
            test_result = welch_t_test(
                controller_results[name1],
                controller_results[name2]
            )
            summary['pairwise_comparisons'][comparison_key] = test_result

    # One-way ANOVA (if more than 2 controllers)
    if len(controller_results) > 2:
        groups = list(controller_results.values())
        summary['anova'] = one_way_anova(groups)

    return summary

def sample_size_calculation(
    effect_size: float,
    power: float = 0.8,
    alpha: float = 0.05,
    test_type: str = 't_test'
) -> int:
    """Calculate required sample size for statistical tests.

    Parameters
    ----------
    effect_size : float
        Expected effect size (Cohen's d for t-test).
    power : float
        Desired statistical power (1 - beta).
    alpha : float
        Significance level (Type I error rate).
    test_type : str
        Type of test ('t_test' or 'anova').

    Returns
    -------
    sample_size : int
        Required sample size per group.
    """
    if test_type == 't_test':
        # Approximation for two-sample t-test
        from scipy.stats import norm
        z_alpha = norm.ppf(1 - alpha/2)
        z_beta = norm.ppf(power)

        n = 2 * ((z_alpha + z_beta) / effect_size)**2
        return int(np.ceil(n))

    elif test_type == 'anova':
        # Simplified approximation for ANOVA
        # This is a rough estimate and should be refined for production use
        t_test_n = sample_size_calculation(effect_size, power, alpha, 't_test')
        return int(np.ceil(t_test_n * 1.2))  # Conservative adjustment

    else:
        raise ValueError(f"Unknown test type: {test_type}")

__all__ = [
    "confidence_interval",
    "bootstrap_confidence_interval",
    "welch_t_test",
    "one_way_anova",
    "monte_carlo_analysis",
    "performance_comparison_summary",
    "sample_size_calculation"
]