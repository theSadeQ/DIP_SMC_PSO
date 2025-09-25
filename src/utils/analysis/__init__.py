#==========================================================================================\\\
#======================== src/utils/analysis/__init__.py ===============================\\\
#==========================================================================================\\\

"""
Statistical analysis package for control system performance evaluation.

This package provides comprehensive statistical tools for rigorous
analysis of control system performance, including confidence intervals,
hypothesis testing, and Monte Carlo validation.
"""

from .statistics import (
    confidence_interval,
    bootstrap_confidence_interval,
    welch_t_test,
    one_way_anova,
    monte_carlo_analysis,
    performance_comparison_summary,
    sample_size_calculation
)

__all__ = [
    "confidence_interval",
    "bootstrap_confidence_interval",
    "welch_t_test",
    "one_way_anova",
    "monte_carlo_analysis",
    "performance_comparison_summary",
    "sample_size_calculation"
]