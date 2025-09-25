#==========================================================================================\\\
#=================== src/benchmarks/statistics/__init__.py ==============================\\\
#==========================================================================================\\\
"""
Statistical analysis package for control system benchmarking.

This package provides comprehensive statistical tools for analyzing
performance metrics collected from simulation trials:

- **Confidence Intervals**: Normal, t-distribution, and bootstrap methods
- **Hypothesis Testing**: Normality tests, group comparisons
- **Effect Size Analysis**: Practical significance assessment
- **Outlier Detection**: Robust statistical validation
"""

from __future__ import annotations

from .confidence_intervals import (
    ConfidenceIntervalResult,
    compute_basic_confidence_intervals,
    compute_t_confidence_intervals,
    compute_bootstrap_confidence_intervals,
    perform_statistical_tests,
    compare_metric_distributions
)

__all__ = [
    # Data structures
    'ConfidenceIntervalResult',

    # Confidence interval methods
    'compute_basic_confidence_intervals',
    'compute_t_confidence_intervals',
    'compute_bootstrap_confidence_intervals',

    # Statistical analysis
    'perform_statistical_tests',
    'compare_metric_distributions'
]