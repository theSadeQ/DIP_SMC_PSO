#==========================================================================================\\\
#==================== src/analysis/validation/statistics.py ====================\\\
#==========================================================================================\\\
"""
Statistical analysis utilities for validation and benchmarking.

This module provides statistical functions for analyzing experimental results,
computing confidence intervals, and performing hypothesis testing.
"""

from typing import Dict, List, Tuple, Any, Optional, Union
import numpy as np
from scipy import stats
import warnings


def compute_basic_confidence_intervals(
    data: np.ndarray,
    confidence_level: float = 0.95
) -> Dict[str, float]:
    """
    Compute basic confidence intervals for data.

    Args:
        data: Input data array
        confidence_level: Confidence level (default 0.95)

    Returns:
        Dictionary containing confidence interval statistics
    """
    if len(data) == 0:
        return {
            'mean': 0.0,
            'std_error': 0.0,
            'lower_bound': 0.0,
            'upper_bound': 0.0,
            'confidence_level': confidence_level
        }

    mean = np.mean(data)
    std_error = stats.sem(data)  # Standard error of the mean

    # Degrees of freedom
    df = len(data) - 1

    # Critical value for t-distribution
    alpha = 1 - confidence_level
    t_critical = stats.t.ppf(1 - alpha/2, df)

    # Confidence interval
    margin_of_error = t_critical * std_error
    lower_bound = mean - margin_of_error
    upper_bound = mean + margin_of_error

    return {
        'mean': float(mean),
        'std_error': float(std_error),
        'lower_bound': float(lower_bound),
        'upper_bound': float(upper_bound),
        'confidence_level': confidence_level,
        'margin_of_error': float(margin_of_error),
        'sample_size': len(data)
    }


def bootstrap_confidence_interval(
    data: np.ndarray,
    statistic_func: callable = np.mean,
    confidence_level: float = 0.95,
    n_bootstrap: int = 1000,
    random_seed: Optional[int] = None
) -> Dict[str, float]:
    """
    Compute bootstrap confidence intervals.

    Args:
        data: Input data array
        statistic_func: Function to compute statistic (default: mean)
        confidence_level: Confidence level
        n_bootstrap: Number of bootstrap samples
        random_seed: Optional random seed

    Returns:
        Dictionary containing bootstrap confidence interval
    """
    if len(data) == 0:
        return {
            'statistic': 0.0,
            'lower_bound': 0.0,
            'upper_bound': 0.0,
            'confidence_level': confidence_level
        }

    if random_seed is not None:
        np.random.seed(random_seed)

    # Bootstrap resampling
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        # Resample with replacement
        bootstrap_sample = np.random.choice(data, size=len(data), replace=True)
        bootstrap_stat = statistic_func(bootstrap_sample)
        bootstrap_stats.append(bootstrap_stat)

    bootstrap_stats = np.array(bootstrap_stats)

    # Compute percentiles for confidence interval
    alpha = 1 - confidence_level
    lower_percentile = (alpha/2) * 100
    upper_percentile = (1 - alpha/2) * 100

    lower_bound = np.percentile(bootstrap_stats, lower_percentile)
    upper_bound = np.percentile(bootstrap_stats, upper_percentile)

    original_statistic = statistic_func(data)

    return {
        'statistic': float(original_statistic),
        'lower_bound': float(lower_bound),
        'upper_bound': float(upper_bound),
        'confidence_level': confidence_level,
        'n_bootstrap': n_bootstrap,
        'bootstrap_std': float(np.std(bootstrap_stats))
    }


def compare_groups_ttest(
    group1: np.ndarray,
    group2: np.ndarray,
    equal_var: bool = False
) -> Dict[str, Any]:
    """
    Compare two groups using t-test.

    Args:
        group1: First group data
        group2: Second group data
        equal_var: Assume equal variances

    Returns:
        Dictionary containing t-test results
    """
    if len(group1) == 0 or len(group2) == 0:
        return {
            'statistic': 0.0,
            'p_value': 1.0,
            'significant': False,
            'effect_size': 0.0
        }

    try:
        # Perform t-test
        statistic, p_value = stats.ttest_ind(group1, group2, equal_var=equal_var)

        # Compute effect size (Cohen's d)
        pooled_std = np.sqrt(((len(group1)-1)*np.var(group1, ddof=1) +
                              (len(group2)-1)*np.var(group2, ddof=1)) /
                             (len(group1) + len(group2) - 2))

        if pooled_std > 0:
            effect_size = (np.mean(group1) - np.mean(group2)) / pooled_std
        else:
            effect_size = 0.0

        return {
            'statistic': float(statistic),
            'p_value': float(p_value),
            'significant': p_value < 0.05,
            'effect_size': float(effect_size),
            'group1_mean': float(np.mean(group1)),
            'group2_mean': float(np.mean(group2)),
            'group1_std': float(np.std(group1, ddof=1)),
            'group2_std': float(np.std(group2, ddof=1))
        }

    except Exception as e:
        warnings.warn(f"T-test failed: {e}")
        return {
            'statistic': 0.0,
            'p_value': 1.0,
            'significant': False,
            'effect_size': 0.0,
            'error': str(e)
        }


def anova_one_way(*groups) -> Dict[str, Any]:
    """
    Perform one-way ANOVA on multiple groups.

    Args:
        *groups: Variable number of group arrays

    Returns:
        Dictionary containing ANOVA results
    """
    if len(groups) < 2:
        return {
            'f_statistic': 0.0,
            'p_value': 1.0,
            'significant': False
        }

    # Remove empty groups
    valid_groups = [g for g in groups if len(g) > 0]

    if len(valid_groups) < 2:
        return {
            'f_statistic': 0.0,
            'p_value': 1.0,
            'significant': False
        }

    try:
        f_statistic, p_value = stats.f_oneway(*valid_groups)

        return {
            'f_statistic': float(f_statistic),
            'p_value': float(p_value),
            'significant': p_value < 0.05,
            'num_groups': len(valid_groups),
            'total_samples': sum(len(g) for g in valid_groups)
        }

    except Exception as e:
        warnings.warn(f"ANOVA failed: {e}")
        return {
            'f_statistic': 0.0,
            'p_value': 1.0,
            'significant': False,
            'error': str(e)
        }


def correlation_analysis(
    x: np.ndarray,
    y: np.ndarray,
    method: str = 'pearson'
) -> Dict[str, float]:
    """
    Compute correlation between two variables.

    Args:
        x: First variable
        y: Second variable
        method: Correlation method ('pearson', 'spearman', 'kendall')

    Returns:
        Dictionary containing correlation results
    """
    if len(x) != len(y) or len(x) == 0:
        return {
            'correlation': 0.0,
            'p_value': 1.0,
            'significant': False
        }

    try:
        if method == 'pearson':
            correlation, p_value = stats.pearsonr(x, y)
        elif method == 'spearman':
            correlation, p_value = stats.spearmanr(x, y)
        elif method == 'kendall':
            correlation, p_value = stats.kendalltau(x, y)
        else:
            raise ValueError(f"Unknown correlation method: {method}")

        return {
            'correlation': float(correlation),
            'p_value': float(p_value),
            'significant': p_value < 0.05,
            'method': method,
            'sample_size': len(x)
        }

    except Exception as e:
        warnings.warn(f"Correlation analysis failed: {e}")
        return {
            'correlation': 0.0,
            'p_value': 1.0,
            'significant': False,
            'error': str(e)
        }


def normality_test(data: np.ndarray) -> Dict[str, Any]:
    """
    Test for normality using multiple methods.

    Args:
        data: Data to test

    Returns:
        Dictionary containing normality test results
    """
    if len(data) < 3:
        return {
            'shapiro_statistic': 0.0,
            'shapiro_p_value': 1.0,
            'normal': False
        }

    results = {}

    try:
        # Shapiro-Wilk test (good for small samples)
        if len(data) <= 5000:  # Shapiro-Wilk has limitations for large samples
            shapiro_stat, shapiro_p = stats.shapiro(data)
            results.update({
                'shapiro_statistic': float(shapiro_stat),
                'shapiro_p_value': float(shapiro_p),
                'shapiro_normal': shapiro_p > 0.05
            })

        # Kolmogorov-Smirnov test
        ks_stat, ks_p = stats.kstest(data, 'norm', args=(np.mean(data), np.std(data)))
        results.update({
            'ks_statistic': float(ks_stat),
            'ks_p_value': float(ks_p),
            'ks_normal': ks_p > 0.05
        })

        # Overall assessment
        normal_tests = []
        if 'shapiro_normal' in results:
            normal_tests.append(results['shapiro_normal'])
        normal_tests.append(results['ks_normal'])

        results['normal'] = all(normal_tests)

    except Exception as e:
        warnings.warn(f"Normality test failed: {e}")
        results = {
            'shapiro_statistic': 0.0,
            'shapiro_p_value': 1.0,
            'ks_statistic': 0.0,
            'ks_p_value': 1.0,
            'normal': False,
            'error': str(e)
        }

    return results


def outlier_detection(
    data: np.ndarray,
    method: str = 'iqr',
    threshold: float = 1.5
) -> Dict[str, Any]:
    """
    Detect outliers in data.

    Args:
        data: Input data
        method: Detection method ('iqr', 'zscore')
        threshold: Threshold for outlier detection

    Returns:
        Dictionary containing outlier information
    """
    if len(data) == 0:
        return {
            'outliers': np.array([]),
            'outlier_indices': np.array([]),
            'num_outliers': 0,
            'outlier_percentage': 0.0
        }

    outlier_mask = np.zeros(len(data), dtype=bool)

    try:
        if method == 'iqr':
            # Interquartile range method
            q25 = np.percentile(data, 25)
            q75 = np.percentile(data, 75)
            iqr = q75 - q25

            lower_bound = q25 - threshold * iqr
            upper_bound = q75 + threshold * iqr

            outlier_mask = (data < lower_bound) | (data > upper_bound)

        elif method == 'zscore':
            # Z-score method
            z_scores = np.abs(stats.zscore(data))
            outlier_mask = z_scores > threshold

        else:
            raise ValueError(f"Unknown outlier detection method: {method}")

        outlier_indices = np.where(outlier_mask)[0]
        outliers = data[outlier_mask]

        return {
            'outliers': outliers,
            'outlier_indices': outlier_indices,
            'num_outliers': len(outliers),
            'outlier_percentage': (len(outliers) / len(data)) * 100,
            'method': method,
            'threshold': threshold
        }

    except Exception as e:
        warnings.warn(f"Outlier detection failed: {e}")
        return {
            'outliers': np.array([]),
            'outlier_indices': np.array([]),
            'num_outliers': 0,
            'outlier_percentage': 0.0,
            'error': str(e)
        }


def statistical_summary(data: np.ndarray) -> Dict[str, Any]:
    """
    Compute comprehensive statistical summary.

    Args:
        data: Input data

    Returns:
        Dictionary containing comprehensive statistics
    """
    if len(data) == 0:
        return {
            'count': 0,
            'mean': 0.0,
            'std': 0.0,
            'min': 0.0,
            'max': 0.0,
            'median': 0.0
        }

    summary = {
        'count': len(data),
        'mean': float(np.mean(data)),
        'std': float(np.std(data, ddof=1)) if len(data) > 1 else 0.0,
        'min': float(np.min(data)),
        'max': float(np.max(data)),
        'median': float(np.median(data)),
        'q25': float(np.percentile(data, 25)),
        'q75': float(np.percentile(data, 75)),
        'skewness': float(stats.skew(data)),
        'kurtosis': float(stats.kurtosis(data))
    }

    # Add confidence intervals
    if len(data) > 1:
        confidence_intervals = compute_basic_confidence_intervals(data)
        summary['confidence_interval'] = confidence_intervals

    # Add normality test
    normality = normality_test(data)
    summary['normality'] = normality

    # Add outlier detection
    outliers = outlier_detection(data)
    summary['outliers'] = outliers

    return summary