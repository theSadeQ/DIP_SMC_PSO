#==========================================================================================\\\
#====================================== src/analysis/__init__.py =============================\\\
#==========================================================================================\\\

"""
Professional analysis framework for control system evaluation and validation.

This module provides a comprehensive analysis framework including:
- Core analysis interfaces and data structures
- Performance metrics and evaluation
- Fault detection and isolation
- Statistical validation and testing
- Monte Carlo analysis
- Cross-validation methods
- Visualization and reporting

The framework follows control engineering best practices and provides both
legacy compatibility and modern enhanced capabilities.
"""

# Core framework exports
from .core.interfaces import (
    AnalysisResult, AnalysisStatus, DataProtocol, MetricCalculator,
    PerformanceAnalyzer, FaultDetector, StatisticalValidator
)

from .core.data_structures import (
    SimulationData, MetricResult, PerformanceMetrics, FaultDetectionResult,
    StatisticalTestResult, ConfidenceInterval
)

from .core.metrics import (
    BaseMetricCalculator, ControlPerformanceMetrics, StabilityMetrics
)

# Performance analysis exports
from .performance.control_metrics import (
    AdvancedControlMetrics,
    # Legacy compatibility functions
    compute_ise, compute_itae, compute_rms_control_effort
)

from .performance.stability_analysis import StabilityAnalyzer
from .performance.robustness import RobustnessAnalyzer

# Fault detection exports
from .fault_detection.fdi_system import (
    EnhancedFaultDetector, FaultDetectionConfig, FaultType, DetectionMethod,
    create_enhanced_fault_detector,
    # Legacy compatibility
    FDIsystem, FaultDetectionInterface, DynamicsProtocol
)

from .fault_detection.residual_generators import (
    ResidualGeneratorFactory, ObserverBasedGenerator,
    KalmanFilterGenerator, ParitySpaceGenerator
)

from .fault_detection.threshold_adapters import (
    ThresholdAdapterFactory, StatisticalThresholdAdapter,
    EWMAThresholdAdapter, AdaptiveThresholdManager
)

# Validation and statistical testing exports
from .validation.statistical_tests import StatisticalTestSuite
from .validation.monte_carlo import MonteCarloAnalyzer
from .validation.cross_validation import CrossValidator
from .validation.benchmarking import BenchmarkSuite

# Visualization exports
from .visualization.analysis_plots import AnalysisPlotter
from .visualization.statistical_plots import StatisticalPlotter
from .visualization.diagnostic_plots import DiagnosticPlotter
from .visualization.report_generator import ReportGenerator

# Factory functions for easy component creation
def create_performance_analyzer(analyzer_type: str = "advanced", **kwargs):
    """Create performance analyzer instance.

    Parameters
    ----------
    analyzer_type : str
        Type of analyzer ('advanced', 'stability', 'robustness')
    **kwargs
        Additional configuration parameters

    Returns
    -------
    PerformanceAnalyzer
        Configured performance analyzer
    """
    if analyzer_type == "advanced":
        return AdvancedControlMetrics(**kwargs)
    elif analyzer_type == "stability":
        return StabilityAnalyzer(**kwargs)
    elif analyzer_type == "robustness":
        return RobustnessAnalyzer(**kwargs)
    else:
        raise ValueError(f"Unknown analyzer type: {analyzer_type}")


def create_fault_detector(detector_type: str = "enhanced", **kwargs):
    """Create fault detector instance.

    Parameters
    ----------
    detector_type : str
        Type of detector ('enhanced', 'legacy')
    **kwargs
        Additional configuration parameters

    Returns
    -------
    FaultDetector
        Configured fault detector
    """
    if detector_type == "enhanced":
        return create_enhanced_fault_detector(kwargs if kwargs else None)
    elif detector_type == "legacy":
        return FDIsystem(**kwargs)
    else:
        raise ValueError(f"Unknown detector type: {detector_type}")


def create_statistical_validator(**kwargs):
    """Create statistical validator instance."""
    return StatisticalTestSuite(**kwargs)


def create_monte_carlo_analyzer(**kwargs):
    """Create Monte Carlo analyzer instance."""
    return MonteCarloAnalyzer(**kwargs)


def create_visualization_suite():
    """Create complete visualization suite."""
    return {
        'analysis_plotter': AnalysisPlotter(),
        'statistical_plotter': StatisticalPlotter(),
        'diagnostic_plotter': DiagnosticPlotter(),
        'report_generator': ReportGenerator()
    }


# Comprehensive exports for public API
__all__ = [
    # Core framework
    'AnalysisResult', 'AnalysisStatus', 'DataProtocol', 'MetricCalculator',
    'PerformanceAnalyzer', 'FaultDetector', 'StatisticalValidator',
    'SimulationData', 'MetricResult', 'PerformanceMetrics', 'FaultDetectionResult',
    'StatisticalTestResult', 'ConfidenceInterval',
    'BaseMetricCalculator', 'ControlPerformanceMetrics', 'StabilityMetrics',

    # Performance analysis
    'AdvancedControlMetrics', 'StabilityAnalyzer', 'RobustnessAnalyzer',

    # Fault detection
    'EnhancedFaultDetector', 'FaultDetectionConfig', 'FaultType', 'DetectionMethod',
    'ResidualGeneratorFactory', 'ObserverBasedGenerator', 'KalmanFilterGenerator', 'ParitySpaceGenerator',
    'ThresholdAdapterFactory', 'StatisticalThresholdAdapter', 'EWMAThresholdAdapter', 'AdaptiveThresholdManager',

    # Validation and testing
    'StatisticalTestSuite', 'MonteCarloAnalyzer', 'CrossValidator', 'BenchmarkSuite',

    # Visualization
    'AnalysisPlotter', 'StatisticalPlotter', 'DiagnosticPlotter', 'ReportGenerator',

    # Factory functions
    'create_performance_analyzer', 'create_fault_detector', 'create_statistical_validator',
    'create_monte_carlo_analyzer', 'create_visualization_suite',
    'create_enhanced_fault_detector',

    # Legacy compatibility exports
    'compute_ise', 'compute_itae', 'compute_rms_control_effort',
    'FaultDetectionInterface', 'FDIsystem', 'DynamicsProtocol',
]