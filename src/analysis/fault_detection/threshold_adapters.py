#==========================================================================================\\\
#================= src/analysis/fault_detection/threshold_adapters.py ===================\\\
#==========================================================================================\\\

"""Adaptive threshold methods for fault detection.

This module provides various adaptive thresholding techniques to improve
fault detection performance under varying operating conditions and
system uncertainties.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any, Callable
import numpy as np
from scipy import stats, signal
import warnings
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from collections import deque

from ..core.data_structures import ConfidenceInterval


@dataclass
class ThresholdAdapterConfig:
    """Configuration for threshold adapters."""
    # Basic adaptation parameters
    adaptation_window_size: int = 50
    confidence_level: float = 0.95
    min_threshold: float = 0.01
    max_threshold: float = 10.0

    # Statistical parameters
    statistical_method: str = "gaussian"  # "gaussian", "chi_squared", "t_distribution"
    outlier_rejection: bool = True
    outlier_threshold: float = 3.0

    # Learning parameters
    learning_rate: float = 0.1
    forgetting_factor: float = 0.95
    adaptation_rate: float = 0.01

    # Change detection parameters
    change_detection_enabled: bool = True
    change_sensitivity: float = 0.05
    reset_on_change: bool = True

    # Robustness parameters
    robust_estimation: bool = True
    breakdown_point: float = 0.3


class ThresholdAdapter(ABC):
    """Abstract base class for threshold adapters."""

    @abstractmethod
    def update(self, residual: float, timestamp: Optional[float] = None) -> float:
        """Update threshold based on new residual value.

        Parameters
        ----------
        residual : float
            New residual value
        timestamp : float, optional
            Timestamp of the residual

        Returns
        -------
        float
            Updated threshold value
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset adapter state."""
        pass

    @property
    @abstractmethod
    def current_threshold(self) -> float:
        """Current threshold value."""
        pass


class StatisticalThresholdAdapter(ThresholdAdapter):
    """Statistical adaptive threshold based on residual statistics."""

    def __init__(self, config: ThresholdAdapterConfig):
        """Initialize statistical threshold adapter.

        Parameters
        ----------
        config : ThresholdAdapterConfig
            Configuration parameters
        """
        self.config = config
        self.reset()

    def update(self, residual: float, timestamp: Optional[float] = None) -> float:
        """Update threshold using statistical methods."""
        # Add residual to window
        self._residual_window.append(residual)

        # Maintain window size
        if len(self._residual_window) > self.config.adaptation_window_size:
            self._residual_window.popleft()

        # Update threshold if we have enough data
        if len(self._residual_window) >= min(10, self.config.adaptation_window_size // 2):
            self._current_threshold = self._compute_statistical_threshold()
        else:
            # Use initial threshold if insufficient data
            pass

        return self._current_threshold

    def _compute_statistical_threshold(self) -> float:
        """Compute threshold using statistical methods."""
        data = np.array(list(self._residual_window))

        # Outlier rejection if enabled
        if self.config.outlier_rejection:
            data = self._reject_outliers(data)

        if len(data) == 0:
            return self._current_threshold

        # Robust estimation if enabled
        if self.config.robust_estimation:
            location, scale = self._robust_parameter_estimation(data)
        else:
            location = np.mean(data)
            scale = np.std(data)

        # Compute threshold based on statistical method
        if self.config.statistical_method == "gaussian":
            threshold = self._gaussian_threshold(location, scale)
        elif self.config.statistical_method == "chi_squared":
            threshold = self._chi_squared_threshold(data)
        elif self.config.statistical_method == "t_distribution":
            threshold = self._t_distribution_threshold(data)
        else:
            threshold = location + 3.0 * scale  # Default

        # Apply bounds
        threshold = np.clip(threshold, self.config.min_threshold, self.config.max_threshold)

        return float(threshold)

    def _reject_outliers(self, data: np.ndarray) -> np.ndarray:
        """Reject outliers using IQR or Z-score method."""
        if len(data) < 5:
            return data

        # Use IQR method for outlier rejection
        q1, q3 = np.percentile(data, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # Keep data within bounds
        mask = (data >= lower_bound) & (data <= upper_bound)
        return data[mask]

    def _robust_parameter_estimation(self, data: np.ndarray) -> Tuple[float, float]:
        """Robust estimation of location and scale parameters."""
        if len(data) < 3:
            return float(np.mean(data)), float(np.std(data))

        # Use median and MAD for robust estimation
        location = np.median(data)
        mad = np.median(np.abs(data - location))
        scale = mad * 1.4826  # Scale factor for normal distribution

        return float(location), float(scale)

    def _gaussian_threshold(self, location: float, scale: float) -> float:
        """Compute threshold assuming Gaussian distribution."""
        # Compute threshold for given confidence level
        alpha = 1 - self.config.confidence_level
        z_value = stats.norm.ppf(1 - alpha/2)
        return location + z_value * scale

    def _chi_squared_threshold(self, data: np.ndarray) -> float:
        """Compute threshold using chi-squared distribution."""
        # Assume residuals follow chi-squared distribution
        dof = len(data) - 1 if len(data) > 1 else 1
        alpha = 1 - self.config.confidence_level
        chi2_value = stats.chi2.ppf(1 - alpha, dof)

        # Scale by sample variance
        sample_var = np.var(data) if len(data) > 1 else 1.0
        return float(np.sqrt(chi2_value * sample_var))

    def _t_distribution_threshold(self, data: np.ndarray) -> float:
        """Compute threshold using t-distribution."""
        if len(data) < 2:
            return float(np.mean(data) + 3.0 * np.std(data))

        # Use t-distribution for small samples
        location = np.mean(data)
        scale = np.std(data, ddof=1)
        dof = len(data) - 1
        alpha = 1 - self.config.confidence_level
        t_value = stats.t.ppf(1 - alpha/2, dof)

        return location + t_value * scale

    def reset(self) -> None:
        """Reset adapter state."""
        self._residual_window: deque = deque(maxlen=self.config.adaptation_window_size)
        self._current_threshold: float = 1.0  # Initial threshold

    @property
    def current_threshold(self) -> float:
        """Current threshold value."""
        return self._current_threshold


class EWMAThresholdAdapter(ThresholdAdapter):
    """Exponentially Weighted Moving Average threshold adapter."""

    def __init__(self, config: ThresholdAdapterConfig):
        """Initialize EWMA threshold adapter.

        Parameters
        ----------
        config : ThresholdAdapterConfig
            Configuration parameters
        """
        self.config = config
        self.reset()

    def update(self, residual: float, timestamp: Optional[float] = None) -> float:
        """Update threshold using EWMA."""
        alpha = self.config.learning_rate

        # Update EWMA of residual and squared residual
        if self._ewma_residual is None:
            self._ewma_residual = residual
            self._ewma_residual_sq = residual**2
        else:
            self._ewma_residual = alpha * residual + (1 - alpha) * self._ewma_residual
            self._ewma_residual_sq = alpha * residual**2 + (1 - alpha) * self._ewma_residual_sq

        # Compute variance estimate
        variance_estimate = self._ewma_residual_sq - self._ewma_residual**2
        if variance_estimate <= 0:
            variance_estimate = 1e-6

        std_estimate = np.sqrt(variance_estimate)

        # Compute threshold
        z_value = stats.norm.ppf(self.config.confidence_level)
        threshold = abs(self._ewma_residual) + z_value * std_estimate

        # Apply bounds
        threshold = np.clip(threshold, self.config.min_threshold, self.config.max_threshold)

        self._current_threshold = float(threshold)
        return self._current_threshold

    def reset(self) -> None:
        """Reset adapter state."""
        self._ewma_residual: Optional[float] = None
        self._ewma_residual_sq: Optional[float] = None
        self._current_threshold: float = 1.0

    @property
    def current_threshold(self) -> float:
        """Current threshold value."""
        return self._current_threshold


class ChangeDetectionThresholdAdapter(ThresholdAdapter):
    """Threshold adapter with change detection capability."""

    def __init__(self, config: ThresholdAdapterConfig, base_adapter: ThresholdAdapter):
        """Initialize change detection adapter.

        Parameters
        ----------
        config : ThresholdAdapterConfig
            Configuration parameters
        base_adapter : ThresholdAdapter
            Base adapter to enhance with change detection
        """
        self.config = config
        self.base_adapter = base_adapter
        self.reset()

    def update(self, residual: float, timestamp: Optional[float] = None) -> float:
        """Update threshold with change detection."""
        # Store residual for change detection
        self._residual_history.append(residual)

        # Maintain history size
        max_history = self.config.adaptation_window_size * 2
        if len(self._residual_history) > max_history:
            self._residual_history.popleft()

        # Check for change point
        if self.config.change_detection_enabled and len(self._residual_history) >= 20:
            change_detected = self._detect_change()

            if change_detected:
                self._handle_change_detection()

        # Update base adapter
        threshold = self.base_adapter.update(residual, timestamp)

        self._current_threshold = threshold
        return threshold

    def _detect_change(self) -> bool:
        """Detect change points in residual sequence."""
        data = np.array(list(self._residual_history))

        # Use CUSUM for change detection
        return self._cusum_change_detection(data)

    def _cusum_change_detection(self, data: np.ndarray) -> bool:
        """CUSUM-based change detection."""
        if len(data) < 20:
            return False

        # Split data into two halves
        mid_point = len(data) // 2
        first_half = data[:mid_point]
        second_half = data[mid_point:]

        # Compute means
        mean1 = np.mean(first_half)
        mean2 = np.mean(second_half)

        # Compute pooled standard deviation
        var1 = np.var(first_half, ddof=1) if len(first_half) > 1 else 1.0
        var2 = np.var(second_half, ddof=1) if len(second_half) > 1 else 1.0
        pooled_std = np.sqrt(((len(first_half) - 1) * var1 + (len(second_half) - 1) * var2) /
                            (len(first_half) + len(second_half) - 2))

        # Normalized difference
        if pooled_std > 0:
            normalized_diff = abs(mean2 - mean1) / pooled_std
            return normalized_diff > (1.0 / self.config.change_sensitivity)
        else:
            return False

    def _handle_change_detection(self) -> None:
        """Handle detected change point."""
        if self.config.reset_on_change:
            # Reset base adapter
            self.base_adapter.reset()

            # Clear part of history
            history_to_keep = min(10, len(self._residual_history) // 4)
            new_history = deque(list(self._residual_history)[-history_to_keep:],
                              maxlen=self._residual_history.maxlen)
            self._residual_history = new_history

    def reset(self) -> None:
        """Reset adapter state."""
        self.base_adapter.reset()
        self._residual_history: deque = deque(maxlen=self.config.adaptation_window_size * 2)
        self._current_threshold: float = 1.0

    @property
    def current_threshold(self) -> float:
        """Current threshold value."""
        return getattr(self, '_current_threshold', self.base_adapter.current_threshold)


class MultivariatethresholdAdapter(ThresholdAdapter):
    """Multivariate threshold adapter for vector residuals."""

    def __init__(self, config: ThresholdAdapterConfig, dimension: int):
        """Initialize multivariate threshold adapter.

        Parameters
        ----------
        config : ThresholdAdapterConfig
            Configuration parameters
        dimension : int
            Dimension of residual vector
        """
        self.config = config
        self.dimension = dimension
        self.reset()

    def update(self, residual: float, timestamp: Optional[float] = None) -> float:
        """Update threshold for vector residual.

        Parameters
        ----------
        residual : float
            Norm of residual vector (scalar)
        timestamp : float, optional
            Timestamp

        Returns
        -------
        float
            Updated threshold value
        """
        # Store residual norm
        self._residual_norms.append(residual)

        # Maintain window size
        if len(self._residual_norms) > self.config.adaptation_window_size:
            self._residual_norms.popleft()

        # Update threshold if sufficient data
        if len(self._residual_norms) >= min(10, self.config.adaptation_window_size // 2):
            self._current_threshold = self._compute_multivariate_threshold()

        return self._current_threshold

    def _compute_multivariate_threshold(self) -> float:
        """Compute threshold for multivariate residuals."""
        data = np.array(list(self._residual_norms))

        if len(data) == 0:
            return self._current_threshold

        # For multivariate residuals, use chi-squared distribution
        dof = self.dimension
        alpha = 1 - self.config.confidence_level

        # Estimate scale parameter
        if self.config.robust_estimation:
            # Use median for robust estimation
            scale_estimate = np.median(data)
        else:
            scale_estimate = np.mean(data)

        # Chi-squared threshold
        chi2_value = stats.chi2.ppf(1 - alpha, dof)
        threshold = scale_estimate * np.sqrt(chi2_value / dof)

        # Apply bounds
        threshold = np.clip(threshold, self.config.min_threshold, self.config.max_threshold)

        return float(threshold)

    def reset(self) -> None:
        """Reset adapter state."""
        self._residual_norms: deque = deque(maxlen=self.config.adaptation_window_size)
        self._current_threshold: float = 1.0

    @property
    def current_threshold(self) -> float:
        """Current threshold value."""
        return self._current_threshold


class AdaptiveThresholdManager:
    """Manager for multiple threshold adapters with different methods."""

    def __init__(self, methods: List[str], config: Optional[ThresholdAdapterConfig] = None):
        """Initialize adaptive threshold manager.

        Parameters
        ----------
        methods : List[str]
            List of threshold adaptation methods to use
        config : ThresholdAdapterConfig, optional
            Configuration parameters
        """
        self.config = config or ThresholdAdapterConfig()
        self.adapters = {}

        # Create adapters for each method
        for method in methods:
            self.adapters[method] = self._create_adapter(method)

        self.reset()

    def _create_adapter(self, method: str) -> ThresholdAdapter:
        """Create adapter for specified method."""
        if method == "statistical":
            return StatisticalThresholdAdapter(self.config)
        elif method == "ewma":
            return EWMAThresholdAdapter(self.config)
        elif method == "change_detection":
            base_adapter = StatisticalThresholdAdapter(self.config)
            return ChangeDetectionThresholdAdapter(self.config, base_adapter)
        elif method == "multivariate":
            return MultivariatethresholdAdapter(self.config, dimension=1)  # Default dimension
        else:
            raise ValueError(f"Unknown threshold adaptation method: {method}")

    def update(self, residual: float, timestamp: Optional[float] = None) -> Dict[str, float]:
        """Update all adapters and return thresholds.

        Parameters
        ----------
        residual : float
            New residual value
        timestamp : float, optional
            Timestamp of residual

        Returns
        -------
        Dict[str, float]
            Dictionary of method names and their threshold values
        """
        thresholds = {}

        for method, adapter in self.adapters.items():
            try:
                threshold = adapter.update(residual, timestamp)
                thresholds[method] = threshold
            except Exception as e:
                warnings.warn(f"Threshold adapter {method} failed: {e}")
                thresholds[method] = adapter.current_threshold

        return thresholds

    def get_consensus_threshold(self, method: str = "median") -> float:
        """Get consensus threshold from all adapters.

        Parameters
        ----------
        method : str
            Method for combining thresholds ("mean", "median", "min", "max")

        Returns
        -------
        float
            Consensus threshold value
        """
        thresholds = [adapter.current_threshold for adapter in self.adapters.values()]

        if not thresholds:
            return 1.0

        if method == "mean":
            return float(np.mean(thresholds))
        elif method == "median":
            return float(np.median(thresholds))
        elif method == "min":
            return float(np.min(thresholds))
        elif method == "max":
            return float(np.max(thresholds))
        else:
            return float(np.median(thresholds))  # Default

    def get_threshold_statistics(self) -> Dict[str, Any]:
        """Get statistics about current thresholds.

        Returns
        -------
        Dict[str, Any]
            Statistics about threshold values
        """
        thresholds = {method: adapter.current_threshold for method, adapter in self.adapters.items()}

        if not thresholds:
            return {}

        values = list(thresholds.values())

        return {
            "individual_thresholds": thresholds,
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "range": float(np.max(values) - np.min(values))
        }

    def reset(self) -> None:
        """Reset all adapters."""
        for adapter in self.adapters.values():
            adapter.reset()

    def update(self, residual: float, timestamp: Optional[float] = None) -> float:
        """Update and return consensus threshold."""
        # Update all adapters
        individual_thresholds = {}
        for method, adapter in self.adapters.items():
            try:
                threshold = adapter.update(residual, timestamp)
                individual_thresholds[method] = threshold
            except Exception as e:
                warnings.warn(f"Adapter {method} failed: {e}")
                individual_thresholds[method] = adapter.current_threshold

        # Return consensus threshold
        return self.get_consensus_threshold()

    @property
    def current_threshold(self) -> float:
        """Current consensus threshold."""
        return self.get_consensus_threshold()


def create_threshold_adapter(method: str, config: Optional[ThresholdAdapterConfig] = None, **kwargs) -> ThresholdAdapter:
    """Factory function to create threshold adapters.

    Parameters
    ----------
    method : str
        Type of adapter ('statistical', 'ewma', 'change_detection', 'multivariate')
    config : ThresholdAdapterConfig, optional
        Configuration parameters
    **kwargs
        Additional method-specific parameters

    Returns
    -------
    ThresholdAdapter
        Configured threshold adapter
    """
    if config is None:
        config = ThresholdAdapterConfig()

    if method == "statistical":
        return StatisticalThresholdAdapter(config)

    elif method == "ewma":
        return EWMAThresholdAdapter(config)

    elif method == "change_detection":
        base_adapter = kwargs.get('base_adapter')
        if base_adapter is None:
            base_adapter = StatisticalThresholdAdapter(config)
        return ChangeDetectionThresholdAdapter(config, base_adapter)

    elif method == "multivariate":
        dimension = kwargs.get('dimension', 1)
        return MultivariatethresholdAdapter(config, dimension)

    else:
        raise ValueError(f"Unknown threshold adaptation method: {method}")


def create_adaptive_threshold_manager(methods: List[str], config: Optional[ThresholdAdapterConfig] = None) -> AdaptiveThresholdManager:
    """Factory function to create adaptive threshold manager.

    Parameters
    ----------
    methods : List[str]
        List of adaptation methods to use
    config : ThresholdAdapterConfig, optional
        Configuration parameters

    Returns
    -------
    AdaptiveThresholdManager
        Configured threshold manager
    """
    return AdaptiveThresholdManager(methods, config)


class ThresholdAdapterFactory:
    """
    Factory class for creating threshold adapters.

    This class provides a unified interface for creating different types of
    threshold adapters used in fault detection systems.
    """

    @staticmethod
    def create_adapter(method: str, config: Optional[ThresholdAdapterConfig] = None, **kwargs) -> ThresholdAdapter:
        """
        Create a threshold adapter of the specified type.

        Parameters
        ----------
        method : str
            Type of adapter ('statistical', 'ewma', 'change_detection', 'multivariate')
        config : ThresholdAdapterConfig, optional
            Configuration parameters
        **kwargs
            Additional parameters specific to each method

        Returns
        -------
        ThresholdAdapter
            Configured threshold adapter
        """
        return create_threshold_adapter(method, config, **kwargs)

    @staticmethod
    def get_available_methods() -> List[str]:
        """Get list of available threshold adaptation methods."""
        return ['statistical', 'ewma', 'change_detection', 'multivariate']

    @staticmethod
    def create_manager(methods: List[str], config: Optional[ThresholdAdapterConfig] = None) -> AdaptiveThresholdManager:
        """Create an adaptive threshold manager with multiple methods."""
        return create_adaptive_threshold_manager(methods, config)

    @classmethod
    def create_default_statistical(cls) -> StatisticalThresholdAdapter:
        """Create statistical threshold adapter with default configuration."""
        return cls.create_adapter('statistical')

    @classmethod
    def create_default_ewma(cls, alpha: float = 0.1) -> EWMAThresholdAdapter:
        """Create EWMA threshold adapter with default configuration."""
        return cls.create_adapter('ewma', alpha=alpha)