#==========================================================================================\\\
#========================= src/analysis/core/interfaces.py ==============================\\\
#==========================================================================================\\\

"""Core interfaces for the analysis framework.

This module defines abstract base classes and protocols that establish
the contract for analysis components, ensuring consistency and extensibility
across the framework.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np


class AnalysisStatus(Enum):
    """Status of analysis operations."""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INCOMPLETE = "incomplete"


@dataclass
class AnalysisResult:
    """Base class for analysis results."""
    status: AnalysisStatus
    message: str
    data: Dict[str, Any]
    timestamp: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    def is_success(self) -> bool:
        """Check if analysis was successful."""
        return self.status == AnalysisStatus.SUCCESS

    def has_warnings(self) -> bool:
        """Check if analysis has warnings."""
        return self.status == AnalysisStatus.WARNING

    def has_errors(self) -> bool:
        """Check if analysis has errors."""
        return self.status == AnalysisStatus.ERROR


class DataProtocol(Protocol):
    """Protocol for simulation data."""
    times: np.ndarray
    states: np.ndarray
    controls: np.ndarray

    def get_time_range(self) -> Tuple[float, float]:
        """Get time range of the data."""
        ...

    def get_sampling_rate(self) -> float:
        """Get average sampling rate."""
        ...


class MetricCalculator(ABC):
    """Abstract base class for metric calculators."""

    @abstractmethod
    def compute(self, data: DataProtocol, **kwargs) -> Dict[str, float]:
        """Compute metrics from simulation data.

        Parameters
        ----------
        data : DataProtocol
            Simulation data containing times, states, and controls
        **kwargs
            Additional parameters for metric calculation

        Returns
        -------
        Dict[str, float]
            Dictionary mapping metric names to values
        """
        pass

    @property
    @abstractmethod
    def supported_metrics(self) -> List[str]:
        """List of metrics supported by this calculator."""
        pass

    def validate_data(self, data: DataProtocol) -> bool:
        """Validate input data for metric calculation."""
        if not hasattr(data, 'times') or not hasattr(data, 'states'):
            return False
        return len(data.times) > 0 and len(data.states) > 0


class PerformanceAnalyzer(ABC):
    """Abstract base class for performance analyzers."""

    @abstractmethod
    def analyze(self, data: DataProtocol, **kwargs) -> AnalysisResult:
        """Perform performance analysis.

        Parameters
        ----------
        data : DataProtocol
            Simulation data to analyze
        **kwargs
            Analysis-specific parameters

        Returns
        -------
        AnalysisResult
            Comprehensive analysis results
        """
        pass

    @property
    @abstractmethod
    def analyzer_name(self) -> str:
        """Name of the analyzer."""
        pass

    @property
    @abstractmethod
    def required_data_fields(self) -> List[str]:
        """List of required data fields for analysis."""
        pass


class FaultDetector(ABC):
    """Abstract base class for fault detection systems."""

    @abstractmethod
    def detect(self, data: DataProtocol, **kwargs) -> AnalysisResult:
        """Detect faults in the system.

        Parameters
        ----------
        data : DataProtocol
            Real-time or batch data for fault detection
        **kwargs
            Detection-specific parameters

        Returns
        -------
        AnalysisResult
            Fault detection results including status and diagnostics
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset detector state for new analysis."""
        pass

    @property
    @abstractmethod
    def detector_type(self) -> str:
        """Type of fault detector."""
        pass


class StatisticalValidator(ABC):
    """Abstract base class for statistical validation."""

    @abstractmethod
    def validate(self,
                data: Union[List[Dict[str, float]], np.ndarray],
                **kwargs) -> AnalysisResult:
        """Perform statistical validation.

        Parameters
        ----------
        data : Union[List[Dict[str, float]], np.ndarray]
            Data for statistical validation
        **kwargs
            Validation-specific parameters

        Returns
        -------
        AnalysisResult
            Statistical validation results
        """
        pass

    @property
    @abstractmethod
    def validation_methods(self) -> List[str]:
        """List of validation methods supported."""
        pass


class VisualizationGenerator(ABC):
    """Abstract base class for visualization generators."""

    @abstractmethod
    def generate(self,
                analysis_result: AnalysisResult,
                **kwargs) -> str:
        """Generate visualization from analysis results.

        Parameters
        ----------
        analysis_result : AnalysisResult
            Analysis results to visualize
        **kwargs
            Visualization-specific parameters

        Returns
        -------
        str
            Path to generated visualization file
        """
        pass

    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """List of supported output formats."""
        pass


class ReportGenerator(ABC):
    """Abstract base class for report generators."""

    @abstractmethod
    def generate_report(self,
                       analysis_results: List[AnalysisResult],
                       **kwargs) -> str:
        """Generate comprehensive analysis report.

        Parameters
        ----------
        analysis_results : List[AnalysisResult]
            List of analysis results to include in report
        **kwargs
            Report generation parameters

        Returns
        -------
        str
            Path to generated report file
        """
        pass

    @property
    @abstractmethod
    def report_formats(self) -> List[str]:
        """List of supported report formats."""
        pass


# Factory protocols for creating analysis components
class AnalyzerFactory(Protocol):
    """Protocol for analyzer factories."""

    def create_metric_calculator(self, calculator_type: str, **kwargs) -> MetricCalculator:
        """Create a metric calculator of specified type."""
        ...

    def create_performance_analyzer(self, analyzer_type: str, **kwargs) -> PerformanceAnalyzer:
        """Create a performance analyzer of specified type."""
        ...

    def create_fault_detector(self, detector_type: str, **kwargs) -> FaultDetector:
        """Create a fault detector of specified type."""
        ...

    def create_statistical_validator(self, validator_type: str, **kwargs) -> StatisticalValidator:
        """Create a statistical validator of specified type."""
        ...


# Configuration protocols
class AnalysisConfiguration(Protocol):
    """Protocol for analysis configuration."""

    metrics_config: Dict[str, Any]
    performance_config: Dict[str, Any]
    fault_detection_config: Dict[str, Any]
    validation_config: Dict[str, Any]
    visualization_config: Dict[str, Any]

    def validate(self) -> bool:
        """Validate configuration parameters."""
        ...


# Analysis pipeline interfaces
class AnalysisPipeline(ABC):
    """Abstract base class for analysis pipelines."""

    @abstractmethod
    def add_analyzer(self, analyzer: Union[PerformanceAnalyzer, FaultDetector, StatisticalValidator]) -> None:
        """Add an analyzer to the pipeline."""
        pass

    @abstractmethod
    def run_pipeline(self, data: DataProtocol, **kwargs) -> List[AnalysisResult]:
        """Run the complete analysis pipeline."""
        pass

    @abstractmethod
    def get_summary(self) -> AnalysisResult:
        """Get summary of pipeline results."""
        pass

    @property
    @abstractmethod
    def pipeline_name(self) -> str:
        """Name of the analysis pipeline."""
        pass


# Context manager for analysis sessions
class AnalysisSession(ABC):
    """Abstract base class for analysis sessions."""

    @abstractmethod
    def __enter__(self) -> 'AnalysisSession':
        """Enter analysis session context."""
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit analysis session context."""
        pass

    @abstractmethod
    def add_data(self, name: str, data: DataProtocol) -> None:
        """Add data to the session."""
        pass

    @abstractmethod
    def run_analysis(self, analysis_type: str, **kwargs) -> AnalysisResult:
        """Run analysis on session data."""
        pass

    @abstractmethod
    def export_results(self, format: str = 'json') -> str:
        """Export session results."""
        pass