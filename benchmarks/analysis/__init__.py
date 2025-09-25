#==========================================================================================\\\
#====================== benchmarks/analysis/__init__.py =================================\\\
#==========================================================================================\\\
"""
Analysis tools for evaluating numerical integration accuracy and performance.

This package provides comprehensive analysis capabilities for assessing
the quality of numerical integration schemes.
"""

from __future__ import annotations

from .accuracy_metrics import (
    AccuracyAnalysis,
    EnergyAnalyzer,
    ConvergenceAnalyzer,
    PerformanceProfiler
)

__all__ = [
    'AccuracyAnalysis',
    'EnergyAnalyzer',
    'ConvergenceAnalyzer',
    'PerformanceProfiler'
]