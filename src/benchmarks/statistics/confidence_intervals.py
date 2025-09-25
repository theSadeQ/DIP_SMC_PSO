#==========================================================================================\\\
#========== src/benchmarks/statistics/confidence_intervals.py ============================\\\
#==========================================================================================\\\
"""
Statistical analysis and confidence interval computation for benchmarks.

This module implements statistical methods for analyzing performance metrics
collected from multiple simulation trials. The Central Limit Theorem ensures
that sample means approach normal distributions for sufficiently large samples,
enabling reliable confidence interval estimation.

Statistical Methods:
* **T-distribution confidence intervals** for small samples
* **Normal approximation** for large samples
* **Bootstrap confidence intervals** for non-parametric estimation
* **Effect size calculations** for practical significance
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import stats
from dataclasses import dataclass


@dataclass
class ConfidenceIntervalResult:
    """Container for confidence interval analysis results."""
    mean: float
    std_error: float
    confidence_level: float
    lower_bound: float
    upper_bound: float
    margin_of_error: float
    sample_size: int
    method: str


def compute_basic_confidence_intervals(
    metrics_list: List[Dict[str, float]],
    confidence_level: float = 0.95
) -> Dict[str, Tuple[float, float]]:
    """Compute 95% confidence intervals using normal approximation.

    This function replicates the original statistical_benchmarks.py behavior
    for backward compatibility.

    Parameters
    ----------
    metrics_list : list of dict
        List of metric dictionaries from individual trials
    confidence_level : float, optional
        Confidence level (default 0.95 for 95% intervals)

    Returns
    -------
    dict
        Mapping from metric names to (mean, margin_of_error) tuples
    """
    if not metrics_list:
        return {}

    # Convert metrics to arrays
    keys = metrics_list[0].keys()
    data = {k: np.array([m[k] for m in metrics_list], dtype=float) for k in keys}

    # Compute confidence intervals using normal approximation
    z_score = stats.norm.ppf((1 + confidence_level) / 2)
    ci_results: Dict[str, Tuple[float, float]] = {}

    for k, vals in data.items():
        mean_val = float(np.mean(vals))
        # Sample standard error with Bessel's correction
        sem = float(np.std(vals, ddof=1) / np.sqrt(len(vals)))
        margin_of_error = float(z_score * sem)
        ci_results[k] = (mean_val, margin_of_error)

    return ci_results


def compute_t_confidence_intervals(
    metrics_list: List[Dict[str, float]],
    confidence_level: float = 0.95
) -> Dict[str, ConfidenceIntervalResult]:
    """Compute confidence intervals using t-distribution.

    The t-distribution provides more accurate confidence intervals for
    small sample sizes and unknown population variance. For large samples
    (n > 30), t-distribution converges to normal distribution.

    Parameters
    ----------
    metrics_list : list of dict
        List of metric dictionaries from individual trials
    confidence_level : float, optional
        Confidence level between 0 and 1

    Returns
    -------
    dict
        Mapping from metric names to ConfidenceIntervalResult objects
    """
    if not metrics_list:
        return {}

    keys = metrics_list[0].keys()
    data = {k: np.array([m[k] for m in metrics_list], dtype=float) for k in keys}
    results = {}

    for k, vals in data.items():
        n = len(vals)
        mean_val = np.mean(vals)
        std_val = np.std(vals, ddof=1)  # Sample standard deviation
        sem = std_val / np.sqrt(n)

        # t-distribution critical value
        alpha = 1 - confidence_level
        t_critical = stats.t.ppf(1 - alpha/2, df=n-1)
        margin_of_error = t_critical * sem

        results[k] = ConfidenceIntervalResult(
            mean=float(mean_val),
            std_error=float(sem),
            confidence_level=confidence_level,
            lower_bound=float(mean_val - margin_of_error),
            upper_bound=float(mean_val + margin_of_error),
            margin_of_error=float(margin_of_error),
            sample_size=n,
            method="t-distribution"
        )

    return results


def compute_bootstrap_confidence_intervals(
    metrics_list: List[Dict[str, float]],
    confidence_level: float = 0.95,
    n_bootstrap: int = 1000,
    random_seed: int = 42
) -> Dict[str, ConfidenceIntervalResult]:
    """Compute bootstrap confidence intervals.

    Bootstrap resampling provides non-parametric confidence intervals
    that don't assume normality. This is particularly useful for metrics
    with skewed distributions or outliers.

    Parameters
    ----------
    metrics_list : list of dict
        List of metric dictionaries from individual trials
    confidence_level : float, optional
        Confidence level between 0 and 1
    n_bootstrap : int, optional
        Number of bootstrap samples
    random_seed : int, optional
        Random seed for reproducibility

    Returns
    -------
    dict
        Mapping from metric names to ConfidenceIntervalResult objects
    """
    if not metrics_list:
        return {}

    rng = np.random.default_rng(random_seed)
    keys = metrics_list[0].keys()
    data = {k: np.array([m[k] for m in metrics_list], dtype=float) for k in keys}
    results = {}

    alpha = 1 - confidence_level
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    for k, vals in data.items():
        n = len(vals)
        bootstrap_means = []

        # Generate bootstrap samples
        for _ in range(n_bootstrap):
            bootstrap_sample = rng.choice(vals, size=n, replace=True)
            bootstrap_means.append(np.mean(bootstrap_sample))

        bootstrap_means = np.array(bootstrap_means)

        # Compute percentile-based confidence interval
        lower_bound = np.percentile(bootstrap_means, lower_percentile)
        upper_bound = np.percentile(bootstrap_means, upper_percentile)

        original_mean = np.mean(vals)
        margin_of_error = max(
            abs(upper_bound - original_mean),
            abs(original_mean - lower_bound)
        )

        results[k] = ConfidenceIntervalResult(
            mean=float(original_mean),
            std_error=float(np.std(bootstrap_means)),
            confidence_level=confidence_level,
            lower_bound=float(lower_bound),
            upper_bound=float(upper_bound),
            margin_of_error=float(margin_of_error),
            sample_size=n,
            method="bootstrap"
        )

    return results


def perform_statistical_tests(
    metrics_list: List[Dict[str, float]]
) -> Dict[str, Dict[str, float]]:
    """Perform statistical tests on collected metrics.

    Parameters
    ----------
    metrics_list : list of dict
        List of metric dictionaries from individual trials

    Returns
    -------
    dict
        Statistical test results for each metric
    """
    if not metrics_list:
        return {}

    keys = metrics_list[0].keys()
    data = {k: np.array([m[k] for m in metrics_list], dtype=float) for k in keys}
    test_results = {}

    for k, vals in data.items():
        # Normality test (Shapiro-Wilk)
        if len(vals) >= 3:  # Minimum sample size for test
            shapiro_stat, shapiro_p = stats.shapiro(vals)
        else:
            shapiro_stat, shapiro_p = np.nan, np.nan

        # Outlier detection using IQR method
        q25, q75 = np.percentile(vals, [25, 75])
        iqr = q75 - q25
        outlier_threshold = 1.5 * iqr
        outliers = np.sum((vals < q25 - outlier_threshold) |
                         (vals > q75 + outlier_threshold))

        test_results[k] = {
            "shapiro_stat": float(shapiro_stat),
            "shapiro_p_value": float(shapiro_p),
            "is_normal": float(shapiro_p) > 0.05 if not np.isnan(shapiro_p) else False,
            "n_outliers": int(outliers),
            "outlier_percentage": float(outliers / len(vals) * 100),
            "skewness": float(stats.skew(vals)),
            "kurtosis": float(stats.kurtosis(vals))
        }

    return test_results


def compare_metric_distributions(
    metrics_list_a: List[Dict[str, float]],
    metrics_list_b: List[Dict[str, float]],
    alpha: float = 0.05
) -> Dict[str, Dict[str, float]]:
    """Compare metric distributions between two groups.

    Parameters
    ----------
    metrics_list_a, metrics_list_b : list of dict
        Metric lists from two different conditions
    alpha : float, optional
        Significance level for hypothesis tests

    Returns
    -------
    dict
        Comparison results for each metric
    """
    if not metrics_list_a or not metrics_list_b:
        return {}

    keys = set(metrics_list_a[0].keys()) & set(metrics_list_b[0].keys())
    comparison_results = {}

    for k in keys:
        vals_a = np.array([m[k] for m in metrics_list_a], dtype=float)
        vals_b = np.array([m[k] for m in metrics_list_b], dtype=float)

        # Independent t-test
        t_stat, t_p = stats.ttest_ind(vals_a, vals_b)

        # Mann-Whitney U test (non-parametric)
        u_stat, u_p = stats.mannwhitneyu(vals_a, vals_b, alternative='two-sided')

        # Effect size (Cohen's d)
        pooled_std = np.sqrt((np.var(vals_a, ddof=1) + np.var(vals_b, ddof=1)) / 2)
        cohens_d = (np.mean(vals_a) - np.mean(vals_b)) / pooled_std if pooled_std > 0 else 0

        comparison_results[k] = {
            "mean_a": float(np.mean(vals_a)),
            "mean_b": float(np.mean(vals_b)),
            "mean_difference": float(np.mean(vals_a) - np.mean(vals_b)),
            "t_statistic": float(t_stat),
            "t_p_value": float(t_p),
            "is_significant": float(t_p) < alpha,
            "u_statistic": float(u_stat),
            "u_p_value": float(u_p),
            "cohens_d": float(cohens_d),
            "effect_size": "small" if abs(cohens_d) < 0.5 else
                          "medium" if abs(cohens_d) < 0.8 else "large"
        }

    return comparison_results