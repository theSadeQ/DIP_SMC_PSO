#==========================================================================================\\\
#====================== src/analysis/core/data_structures.py ============================\\\
#==========================================================================================\\\

"""Data structures for analysis framework.

This module provides standardized data structures for representing
simulation data, analysis results, and configuration parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from datetime import datetime

from .interfaces import DataProtocol, AnalysisResult, AnalysisStatus


@dataclass
class SimulationData:
    """Standard container for simulation data."""
    times: np.ndarray
    states: np.ndarray
    controls: np.ndarray
    reference: Optional[np.ndarray] = None
    disturbances: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate data consistency after initialization."""
        self._validate_dimensions()

    def _validate_dimensions(self) -> None:
        """Validate dimensional consistency of arrays."""
        n_time_steps = len(self.times)

        if self.states.shape[0] != n_time_steps:
            raise ValueError(f"States array length {self.states.shape[0]} doesn't match times length {n_time_steps}")

        if self.controls.shape[0] != n_time_steps - 1:  # Controls typically have one less sample
            if self.controls.shape[0] != n_time_steps:
                raise ValueError(f"Controls array length {self.controls.shape[0]} is incompatible with times length {n_time_steps}")

    def get_time_range(self) -> Tuple[float, float]:
        """Get time range of the data."""
        return float(self.times[0]), float(self.times[-1])

    def get_sampling_rate(self) -> float:
        """Get average sampling rate."""
        if len(self.times) < 2:
            return 0.0
        return float(1.0 / np.mean(np.diff(self.times)))

    def get_duration(self) -> float:
        """Get total simulation duration."""
        return float(self.times[-1] - self.times[0])

    def extract_slice(self, start_time: float, end_time: float) -> 'SimulationData':
        """Extract a time slice of the data."""
        mask = (self.times >= start_time) & (self.times <= end_time)
        indices = np.where(mask)[0]

        if len(indices) == 0:
            raise ValueError(f"No data found in time range [{start_time}, {end_time}]")

        start_idx, end_idx = indices[0], indices[-1] + 1

        # Handle controls array dimension carefully
        control_end_idx = min(end_idx, len(self.controls))

        return SimulationData(
            times=self.times[start_idx:end_idx],
            states=self.states[start_idx:end_idx],
            controls=self.controls[start_idx:control_end_idx],
            reference=self.reference[start_idx:end_idx] if self.reference is not None else None,
            disturbances=self.disturbances[start_idx:end_idx] if self.disturbances is not None else None,
            metadata=self.metadata.copy()
        )

    def downsample(self, factor: int) -> 'SimulationData':
        """Downsample the data by the given factor."""
        if factor <= 1:
            return self

        indices = np.arange(0, len(self.times), factor)
        control_indices = np.arange(0, len(self.controls), factor)

        return SimulationData(
            times=self.times[indices],
            states=self.states[indices],
            controls=self.controls[control_indices],
            reference=self.reference[indices] if self.reference is not None else None,
            disturbances=self.disturbances[indices] if self.disturbances is not None else None,
            metadata=self.metadata.copy()
        )


@dataclass
class MetricResult:
    """Container for individual metric results."""
    name: str
    value: float
    unit: Optional[str] = None
    description: Optional[str] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """String representation of the metric."""
        unit_str = f" {self.unit}" if self.unit else ""
        ci_str = ""
        if self.confidence_interval:
            ci_str = f" [CI: {self.confidence_interval[0]:.3f}, {self.confidence_interval[1]:.3f}]"
        return f"{self.name}: {self.value:.6f}{unit_str}{ci_str}"


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    metrics: List[MetricResult] = field(default_factory=list)
    computation_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def add_metric(self, metric: MetricResult) -> None:
        """Add a metric to the collection."""
        self.metrics.append(metric)

    def get_metric(self, name: str) -> Optional[MetricResult]:
        """Get a metric by name."""
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None

    def get_metric_value(self, name: str) -> Optional[float]:
        """Get a metric value by name."""
        metric = self.get_metric(name)
        return metric.value if metric else None

    def to_dict(self) -> Dict[str, float]:
        """Convert metrics to dictionary for compatibility."""
        return {metric.name: metric.value for metric in self.metrics}

    def summary_statistics(self) -> Dict[str, float]:
        """Compute summary statistics of all metrics."""
        values = [metric.value for metric in self.metrics]
        if not values:
            return {}

        return {
            'count': len(values),
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'median': np.median(values)
        }


@dataclass
class FaultDetectionResult:
    """Container for fault detection results."""
    status: str  # "OK", "FAULT", "WARNING"
    fault_type: Optional[str] = None
    confidence: Optional[float] = None
    detection_time: Optional[float] = None
    residual_history: List[float] = field(default_factory=list)
    threshold_history: List[float] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def is_fault_detected(self) -> bool:
        """Check if a fault was detected."""
        return self.status == "FAULT"

    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return self.status == "WARNING"


@dataclass
class StatisticalTestResult:
    """Container for statistical test results."""
    test_name: str
    statistic: float
    p_value: float
    critical_value: Optional[float] = None
    confidence_level: float = 0.95
    conclusion: str = ""
    effect_size: Optional[float] = None
    power: Optional[float] = None

    def is_significant(self, alpha: float = 0.05) -> bool:
        """Check if result is statistically significant."""
        return self.p_value < alpha

    def __str__(self) -> str:
        """String representation of test result."""
        return (f"{self.test_name}: statistic={self.statistic:.4f}, "
                f"p-value={self.p_value:.4f}, significant={self.is_significant()}")


@dataclass
class ConfidenceInterval:
    """Container for confidence intervals."""
    lower: float
    upper: float
    confidence_level: float
    method: str = "t-distribution"

    @property
    def width(self) -> float:
        """Width of the confidence interval."""
        return self.upper - self.lower

    @property
    def center(self) -> float:
        """Center of the confidence interval."""
        return (self.lower + self.upper) / 2

    def contains(self, value: float) -> bool:
        """Check if value is within the confidence interval."""
        return self.lower <= value <= self.upper

    def __str__(self) -> str:
        """String representation of confidence interval."""
        return f"[{self.lower:.4f}, {self.upper:.4f}] ({self.confidence_level*100:.0f}% CI)"


@dataclass
class ComparisonResult:
    """Container for comparison analysis results."""
    method_a_name: str
    method_b_name: str
    metric_comparisons: Dict[str, StatisticalTestResult] = field(default_factory=dict)
    effect_sizes: Dict[str, float] = field(default_factory=dict)
    confidence_intervals: Dict[str, ConfidenceInterval] = field(default_factory=dict)
    overall_conclusion: str = ""
    recommendation: str = ""

    def get_winner(self, metric: str, lower_is_better: bool = True) -> Optional[str]:
        """Determine the winning method for a specific metric."""
        if metric not in self.metric_comparisons:
            return None

        test_result = self.metric_comparisons[metric]
        if not test_result.is_significant():
            return "No significant difference"

        # This would need to be implemented based on the specific test used
        # For now, return a placeholder
        return "Requires specific test interpretation"


@dataclass
class AnalysisConfiguration:
    """Configuration for analysis operations."""
    metrics_config: Dict[str, Any] = field(default_factory=dict)
    performance_config: Dict[str, Any] = field(default_factory=dict)
    fault_detection_config: Dict[str, Any] = field(default_factory=dict)
    validation_config: Dict[str, Any] = field(default_factory=dict)
    visualization_config: Dict[str, Any] = field(default_factory=dict)

    # Default configurations
    def __post_init__(self):
        """Set default configurations if not provided."""
        if not self.metrics_config:
            self.metrics_config = {
                'include_basic_metrics': True,
                'include_control_metrics': True,
                'include_stability_metrics': False,
                'time_window': None
            }

        if not self.performance_config:
            self.performance_config = {
                'reference_tracking_tolerance': 0.02,
                'settling_time_criteria': 0.02,
                'overshoot_threshold': 0.1
            }

        if not self.fault_detection_config:
            self.fault_detection_config = {
                'enable_adaptive_threshold': True,
                'residual_threshold': 0.5,
                'persistence_counter': 10
            }

        if not self.validation_config:
            self.validation_config = {
                'confidence_level': 0.95,
                'bootstrap_samples': 1000,
                'monte_carlo_runs': 30
            }

    def validate(self) -> bool:
        """Validate configuration parameters."""
        try:
            # Validate confidence level
            if not 0 < self.validation_config.get('confidence_level', 0.95) < 1:
                return False

            # Validate thresholds are positive
            if self.fault_detection_config.get('residual_threshold', 0.5) <= 0:
                return False

            return True
        except (KeyError, TypeError, ValueError):
            return False


# Utility functions for creating data structures
def create_simulation_data_from_arrays(times: np.ndarray,
                                     states: np.ndarray,
                                     controls: np.ndarray,
                                     **kwargs) -> SimulationData:
    """Factory function for creating SimulationData."""
    return SimulationData(
        times=times,
        states=states,
        controls=controls,
        reference=kwargs.get('reference'),
        disturbances=kwargs.get('disturbances'),
        metadata=kwargs.get('metadata', {})
    )


def create_analysis_result(status: AnalysisStatus,
                         message: str,
                         data: Dict[str, Any],
                         **kwargs) -> AnalysisResult:
    """Factory function for creating AnalysisResult."""
    return AnalysisResult(
        status=status,
        message=message,
        data=data,
        timestamp=kwargs.get('timestamp'),
        metadata=kwargs.get('metadata')
    )