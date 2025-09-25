#==========================================================================================\\\
#========================== src/analysis/core/metrics.py ===============================\\\
#==========================================================================================\\\

"""Core metric computation framework.

This module provides the foundation for computing various performance
metrics from simulation data, with emphasis on control engineering
applications and statistical rigor.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy import signal, integrate
import warnings

from .interfaces import MetricCalculator, DataProtocol
from .data_structures import MetricResult, PerformanceMetrics


class BaseMetricCalculator(MetricCalculator):
    """Base implementation of metric calculator with common functionality."""

    def __init__(self, validate_inputs: bool = True):
        """Initialize base metric calculator.

        Parameters
        ----------
        validate_inputs : bool, optional
            Whether to validate inputs before computation
        """
        self.validate_inputs = validate_inputs

    def compute(self, data: DataProtocol, **kwargs) -> Dict[str, float]:
        """Compute metrics from simulation data."""
        if self.validate_inputs and not self.validate_data(data):
            raise ValueError("Invalid input data for metric calculation")

        metrics = {}
        for metric_name in self.supported_metrics:
            try:
                value = self._compute_metric(metric_name, data, **kwargs)
                metrics[metric_name] = value
            except Exception as e:
                warnings.warn(f"Failed to compute metric {metric_name}: {e}")
                metrics[metric_name] = np.nan

        return metrics

    def _compute_metric(self, metric_name: str, data: DataProtocol, **kwargs) -> float:
        """Compute a specific metric. Override in subclasses."""
        raise NotImplementedError(f"Metric {metric_name} not implemented")

    @property
    def supported_metrics(self) -> List[str]:
        """List of supported metrics."""
        return []


class ControlPerformanceMetrics(BaseMetricCalculator):
    """Calculator for control performance metrics."""

    def __init__(self, reference_tolerance: float = 0.02, **kwargs):
        """Initialize control performance metrics calculator.

        Parameters
        ----------
        reference_tolerance : float, optional
            Tolerance for settling time calculation (default 2%)
        """
        super().__init__(**kwargs)
        self.reference_tolerance = reference_tolerance

    @property
    def supported_metrics(self) -> List[str]:
        """List of supported control performance metrics."""
        return [
            'ise',           # Integral Square Error
            'iae',           # Integral Absolute Error
            'itae',          # Integral Time Absolute Error
            'mse',           # Mean Square Error
            'mae',           # Mean Absolute Error
            'rmse',          # Root Mean Square Error
            'settling_time', # Settling time
            'overshoot',     # Maximum overshoot
            'rise_time',     # Rise time
            'steady_state_error',  # Steady-state error
            'control_effort',      # RMS control effort
            'peak_control'         # Peak control effort
        ]

    def _compute_metric(self, metric_name: str, data: DataProtocol, **kwargs) -> float:
        """Compute specific control performance metric."""
        reference = kwargs.get('reference', None)
        output_indices = kwargs.get('output_indices', [0, 1])  # Default to first two states

        if metric_name in ['ise', 'iae', 'itae', 'mse', 'mae', 'rmse']:
            return self._compute_tracking_error_metric(metric_name, data, reference, output_indices)
        elif metric_name in ['settling_time', 'overshoot', 'rise_time', 'steady_state_error']:
            return self._compute_transient_metric(metric_name, data, reference, output_indices)
        elif metric_name in ['control_effort', 'peak_control']:
            return self._compute_control_metric(metric_name, data)
        else:
            raise ValueError(f"Unknown metric: {metric_name}")

    def _compute_tracking_error_metric(self, metric_name: str, data: DataProtocol,
                                     reference: Optional[np.ndarray],
                                     output_indices: List[int]) -> float:
        """Compute tracking error metrics."""
        # Extract outputs
        if hasattr(data, 'states') and data.states.ndim > 1:
            outputs = data.states[:, output_indices]
        else:
            outputs = data.states.reshape(-1, 1)

        # Use reference if provided, otherwise assume zero reference
        if reference is not None:
            if reference.ndim == 1:
                reference = reference.reshape(-1, 1)
            ref = reference[:len(outputs), :outputs.shape[1]]
        else:
            ref = np.zeros_like(outputs)

        # Compute error
        error = outputs - ref
        dt = np.mean(np.diff(data.times)) if len(data.times) > 1 else 0.01

        if metric_name == 'ise':
            return float(np.trapz(np.sum(error**2, axis=1), dx=dt))
        elif metric_name == 'iae':
            return float(np.trapz(np.sum(np.abs(error), axis=1), dx=dt))
        elif metric_name == 'itae':
            return float(np.trapz(data.times * np.sum(np.abs(error), axis=1), dx=dt))
        elif metric_name == 'mse':
            return float(np.mean(np.sum(error**2, axis=1)))
        elif metric_name == 'mae':
            return float(np.mean(np.sum(np.abs(error), axis=1)))
        elif metric_name == 'rmse':
            return float(np.sqrt(np.mean(np.sum(error**2, axis=1))))

    def _compute_transient_metric(self, metric_name: str, data: DataProtocol,
                                reference: Optional[np.ndarray],
                                output_indices: List[int]) -> float:
        """Compute transient response metrics."""
        # For simplicity, use first output index
        output_idx = output_indices[0] if output_indices else 0

        if hasattr(data, 'states') and data.states.ndim > 1:
            output = data.states[:, output_idx]
        else:
            output = data.states.flatten()

        if metric_name == 'settling_time':
            return self._compute_settling_time(data.times, output)
        elif metric_name == 'overshoot':
            return self._compute_overshoot(output)
        elif metric_name == 'rise_time':
            return self._compute_rise_time(data.times, output)
        elif metric_name == 'steady_state_error':
            return self._compute_steady_state_error(output, reference)

    def _compute_control_metric(self, metric_name: str, data: DataProtocol) -> float:
        """Compute control effort metrics."""
        controls = data.controls.flatten() if data.controls.ndim > 1 else data.controls

        if metric_name == 'control_effort':
            # RMS control effort
            return float(np.sqrt(np.mean(controls**2)))
        elif metric_name == 'peak_control':
            # Peak control effort
            return float(np.max(np.abs(controls)))

    def _compute_settling_time(self, times: np.ndarray, output: np.ndarray) -> float:
        """Compute settling time using percentage criteria."""
        final_value = output[-1]
        tolerance_band = self.reference_tolerance * abs(final_value)

        # Find last time outside tolerance band
        outside_band = np.abs(output - final_value) > tolerance_band
        if not np.any(outside_band):
            return 0.0

        last_outside_index = np.where(outside_band)[0][-1]
        return float(times[last_outside_index])

    def _compute_overshoot(self, output: np.ndarray) -> float:
        """Compute maximum overshoot percentage."""
        final_value = output[-1]
        if final_value == 0:
            return 0.0

        max_value = np.max(output)
        overshoot = (max_value - final_value) / abs(final_value) * 100
        return max(0.0, float(overshoot))

    def _compute_rise_time(self, times: np.ndarray, output: np.ndarray) -> float:
        """Compute rise time (10% to 90% of final value)."""
        final_value = output[-1]
        ten_percent = 0.1 * final_value
        ninety_percent = 0.9 * final_value

        try:
            idx_10 = np.where(output >= ten_percent)[0][0]
            idx_90 = np.where(output >= ninety_percent)[0][0]
            return float(times[idx_90] - times[idx_10])
        except IndexError:
            return float(times[-1])  # Return total time if criteria not met

    def _compute_steady_state_error(self, output: np.ndarray,
                                  reference: Optional[np.ndarray]) -> float:
        """Compute steady-state error."""
        final_output = output[-1]

        if reference is not None:
            final_reference = reference[-1] if hasattr(reference, '__len__') else reference
            return float(abs(final_reference - final_output))
        else:
            # Assume zero reference
            return float(abs(final_output))


class StabilityMetrics(BaseMetricCalculator):
    """Calculator for stability-related metrics."""

    @property
    def supported_metrics(self) -> List[str]:
        """List of supported stability metrics."""
        return [
            'lyapunov_exponent',
            'phase_margin',
            'gain_margin',
            'stability_margin',
            'bounded_states'
        ]

    def _compute_metric(self, metric_name: str, data: DataProtocol, **kwargs) -> float:
        """Compute specific stability metric."""
        if metric_name == 'lyapunov_exponent':
            return self._compute_lyapunov_exponent(data)
        elif metric_name == 'bounded_states':
            return self._compute_bounded_states(data, kwargs.get('bounds'))
        else:
            # Frequency domain metrics require system model
            warnings.warn(f"Stability metric {metric_name} requires system model")
            return np.nan

    def _compute_lyapunov_exponent(self, data: DataProtocol) -> float:
        """Estimate largest Lyapunov exponent from time series."""
        # Simplified estimation - would need more sophisticated method for accurate results
        states = data.states
        if states.ndim > 1:
            # Use first state variable
            x = states[:, 0]
        else:
            x = states

        # Compute divergence rate (simplified)
        try:
            log_divergence = np.log(np.abs(np.diff(x)))
            valid_idx = np.isfinite(log_divergence)
            if np.any(valid_idx):
                return float(np.mean(log_divergence[valid_idx]))
            else:
                return 0.0
        except:
            return 0.0

    def _compute_bounded_states(self, data: DataProtocol, bounds: Optional[Dict[str, Tuple[float, float]]]) -> float:
        """Compute fraction of time states remain within bounds."""
        if bounds is None:
            return 1.0  # No bounds specified

        states = data.states
        total_violations = 0
        total_checks = 0

        for state_idx, (lower, upper) in bounds.items():
            if isinstance(state_idx, str):
                continue  # Skip non-numeric indices

            state_idx = int(state_idx)
            if state_idx < states.shape[1]:
                state_traj = states[:, state_idx]
                violations = np.sum((state_traj < lower) | (state_traj > upper))
                total_violations += violations
                total_checks += len(state_traj)

        if total_checks == 0:
            return 1.0

        return float(1.0 - total_violations / total_checks)


class RobustnessMetrics(BaseMetricCalculator):
    """Calculator for robustness metrics."""

    @property
    def supported_metrics(self) -> List[str]:
        """List of supported robustness metrics."""
        return [
            'sensitivity_norm',
            'disturbance_rejection',
            'parameter_variation_tolerance'
        ]

    def _compute_metric(self, metric_name: str, data: DataProtocol, **kwargs) -> float:
        """Compute specific robustness metric."""
        # Placeholder implementations - would need more sophisticated analysis
        warnings.warn(f"Robustness metric {metric_name} requires advanced analysis")
        return np.nan


def create_comprehensive_metrics(data: DataProtocol,
                               reference: Optional[np.ndarray] = None,
                               include_stability: bool = False,
                               include_robustness: bool = False,
                               **kwargs) -> PerformanceMetrics:
    """Create comprehensive performance metrics from simulation data.

    Parameters
    ----------
    data : DataProtocol
        Simulation data
    reference : np.ndarray, optional
        Reference trajectory for tracking metrics
    include_stability : bool, optional
        Whether to include stability metrics
    include_robustness : bool, optional
        Whether to include robustness metrics
    **kwargs
        Additional parameters for metric calculation

    Returns
    -------
    PerformanceMetrics
        Comprehensive collection of performance metrics
    """
    metrics = PerformanceMetrics()

    # Control performance metrics
    control_calculator = ControlPerformanceMetrics()
    control_metrics = control_calculator.compute(data, reference=reference, **kwargs)

    for name, value in control_metrics.items():
        if np.isfinite(value):
            metric = MetricResult(name=name, value=value, unit=_get_metric_unit(name))
            metrics.add_metric(metric)

    # Stability metrics (if requested)
    if include_stability:
        stability_calculator = StabilityMetrics()
        stability_metrics = stability_calculator.compute(data, **kwargs)

        for name, value in stability_metrics.items():
            if np.isfinite(value):
                metric = MetricResult(name=name, value=value, unit=_get_metric_unit(name))
                metrics.add_metric(metric)

    # Robustness metrics (if requested)
    if include_robustness:
        robustness_calculator = RobustnessMetrics()
        robustness_metrics = robustness_calculator.compute(data, **kwargs)

        for name, value in robustness_metrics.items():
            if np.isfinite(value):
                metric = MetricResult(name=name, value=value, unit=_get_metric_unit(name))
                metrics.add_metric(metric)

    return metrics


def _get_metric_unit(metric_name: str) -> Optional[str]:
    """Get appropriate unit for a metric."""
    unit_map = {
        'ise': 'rad²·s',
        'iae': 'rad·s',
        'itae': 'rad·s²',
        'mse': 'rad²',
        'mae': 'rad',
        'rmse': 'rad',
        'settling_time': 's',
        'rise_time': 's',
        'overshoot': '%',
        'steady_state_error': 'rad',
        'control_effort': 'N',
        'peak_control': 'N',
        'bounded_states': 'fraction'
    }
    return unit_map.get(metric_name)