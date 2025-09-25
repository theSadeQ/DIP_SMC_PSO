#==========================================================================================\\\
#==================== benchmarks/comparison/__init__.py ================================\\\
#==========================================================================================\\\
"""
Comparison framework for systematic evaluation of integration methods.

This package provides tools for comprehensive comparison of numerical
integration schemes across multiple performance criteria.
"""

from __future__ import annotations

from .method_comparison import (
    ComparisonScenario,
    MethodComparisonResult,
    IntegrationMethodComparator
)

__all__ = [
    'ComparisonScenario',
    'MethodComparisonResult',
    'IntegrationMethodComparator'
]