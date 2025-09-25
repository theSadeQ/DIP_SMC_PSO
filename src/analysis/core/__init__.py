#==========================================================================================\\\
#=========================== src/analysis/core/__init__.py ==============================\\\
#==========================================================================================\\\

"""Core analysis framework components.

This module provides the foundational interfaces, data structures, and
metric computation capabilities for the analysis framework.
"""

# Core interfaces and protocols
from .interfaces import (
    AnalysisStatus, AnalysisResult, DataProtocol,
    MetricCalculator, PerformanceAnalyzer, FaultDetector,
    StatisticalValidator, VisualizationGenerator, ReportGenerator,
    AnalyzerFactory, AnalysisConfiguration, AnalysisPipeline, AnalysisSession
)

# Data structures
from .data_structures import (
    SimulationData, MetricResult, PerformanceMetrics,
    FaultDetectionResult, StatisticalTestResult, ConfidenceInterval,
    ComparisonResult, AnalysisConfiguration,
    create_simulation_data_from_arrays, create_analysis_result
)

# Metric computation
from .metrics import (
    BaseMetricCalculator, ControlPerformanceMetrics, StabilityMetrics,
    RobustnessMetrics, create_comprehensive_metrics
)

__all__ = [
    # Interfaces and protocols
    "AnalysisStatus", "AnalysisResult", "DataProtocol",
    "MetricCalculator", "PerformanceAnalyzer", "FaultDetector",
    "StatisticalValidator", "VisualizationGenerator", "ReportGenerator",
    "AnalyzerFactory", "AnalysisConfiguration", "AnalysisPipeline", "AnalysisSession",

    # Data structures
    "SimulationData", "MetricResult", "PerformanceMetrics",
    "FaultDetectionResult", "StatisticalTestResult", "ConfidenceInterval",
    "ComparisonResult", "AnalysisConfiguration",
    "create_simulation_data_from_arrays", "create_analysis_result",

    # Metric calculators
    "BaseMetricCalculator", "ControlPerformanceMetrics", "StabilityMetrics",
    "RobustnessMetrics", "create_comprehensive_metrics"
]