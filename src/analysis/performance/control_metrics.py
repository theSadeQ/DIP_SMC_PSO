#==========================================================================================\\\
#===================== src/analysis/performance/control_metrics.py ======================\\\
#==========================================================================================\\\

"""Enhanced control performance metrics and analysis.

This module provides comprehensive control performance analysis tools
including advanced metrics, frequency domain analysis, and statistical
evaluation of controller performance.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
from scipy import signal, optimize, integrate
import warnings

from ..core.interfaces import PerformanceAnalyzer, AnalysisResult, AnalysisStatus, DataProtocol
from ..core.data_structures import MetricResult, PerformanceMetrics, SimulationData
from ..core.metrics import ControlPerformanceMetrics


class AdvancedControlMetrics(PerformanceAnalyzer):
    """Advanced control performance analyzer with frequency domain capabilities."""

    def __init__(self,
                 reference_tolerance: float = 0.02,
                 include_frequency_analysis: bool = True,
                 frequency_range: Optional[Tuple[float, float]] = None):
        """Initialize advanced control metrics analyzer.

        Parameters
        ----------
        reference_tolerance : float, optional
            Tolerance for settling time calculation
        include_frequency_analysis : bool, optional
            Whether to include frequency domain analysis
        frequency_range : tuple, optional
            Frequency range for analysis (min_freq, max_freq) in rad/s
        """
        self.reference_tolerance = reference_tolerance
        self.include_frequency_analysis = include_frequency_analysis
        self.frequency_range = frequency_range or (0.1, 100.0)

    @property
    def analyzer_name(self) -> str:
        """Name of the analyzer."""
        return "AdvancedControlMetrics"

    @property
    def required_data_fields(self) -> List[str]:
        """Required data fields for analysis."""
        return ['times', 'states', 'controls']

    def analyze(self, data: DataProtocol, **kwargs) -> AnalysisResult:
        """Perform comprehensive control performance analysis.

        Parameters
        ----------
        data : DataProtocol
            Simulation data containing times, states, and controls
        **kwargs
            Additional analysis parameters including:
            - reference: reference trajectory
            - output_indices: indices of states to analyze as outputs
            - disturbances: disturbance signals
            - system_matrices: (A, B, C, D) for frequency analysis

        Returns
        -------
        AnalysisResult
            Comprehensive performance analysis results
        """
        try:
            # Validate input data
            if not self._validate_input_data(data):
                return AnalysisResult(
                    status=AnalysisStatus.ERROR,
                    message="Invalid input data for control analysis",
                    data={}
                )

            # Extract analysis parameters
            reference = kwargs.get('reference', None)
            output_indices = kwargs.get('output_indices', [0, 1])
            system_matrices = kwargs.get('system_matrices', None)

            # Perform time domain analysis
            time_domain_results = self._analyze_time_domain(data, reference, output_indices)

            # Perform frequency domain analysis if requested and possible
            frequency_results = {}
            if self.include_frequency_analysis and system_matrices is not None:
                frequency_results = self._analyze_frequency_domain(system_matrices)

            # Compute advanced metrics
            advanced_metrics = self._compute_advanced_metrics(data, reference, output_indices)

            # Combine all results
            analysis_data = {
                'time_domain': time_domain_results,
                'frequency_domain': frequency_results,
                'advanced_metrics': advanced_metrics,
                'analysis_parameters': {
                    'reference_tolerance': self.reference_tolerance,
                    'output_indices': output_indices,
                    'frequency_range': self.frequency_range
                }
            }

            return AnalysisResult(
                status=AnalysisStatus.SUCCESS,
                message="Control performance analysis completed successfully",
                data=analysis_data
            )

        except Exception as e:
            return AnalysisResult(
                status=AnalysisStatus.ERROR,
                message=f"Control analysis failed: {str(e)}",
                data={'error_details': str(e)}
            )

    def _validate_input_data(self, data: DataProtocol) -> bool:
        """Validate input data for analysis."""
        try:
            # Check required attributes
            if not all(hasattr(data, attr) for attr in ['times', 'states', 'controls']):
                return False

            # Check array shapes
            if len(data.times) != len(data.states):
                return False

            # Check for finite values
            if not (np.all(np.isfinite(data.times)) and
                    np.all(np.isfinite(data.states)) and
                    np.all(np.isfinite(data.controls))):
                return False

            return True

        except Exception:
            return False

    def _analyze_time_domain(self, data: DataProtocol,
                           reference: Optional[np.ndarray],
                           output_indices: List[int]) -> Dict[str, Any]:
        """Perform time domain analysis."""
        results = {}

        # Basic time domain metrics
        calculator = ControlPerformanceMetrics(self.reference_tolerance)
        basic_metrics = calculator.compute(
            data,
            reference=reference,
            output_indices=output_indices
        )
        results['basic_metrics'] = basic_metrics

        # Step response characteristics
        step_characteristics = self._analyze_step_response(data, output_indices)
        results['step_response'] = step_characteristics

        # Tracking performance
        if reference is not None:
            tracking_analysis = self._analyze_tracking_performance(data, reference, output_indices)
            results['tracking'] = tracking_analysis

        # Control effort analysis
        control_analysis = self._analyze_control_effort(data)
        results['control_effort'] = control_analysis

        return results

    def _analyze_step_response(self, data: DataProtocol, output_indices: List[int]) -> Dict[str, Any]:
        """Analyze step response characteristics."""
        results = {}

        for i, output_idx in enumerate(output_indices):
            if output_idx >= data.states.shape[1]:
                continue

            output = data.states[:, output_idx]

            # Compute step response metrics
            step_info = {
                'settling_time': self._compute_settling_time_advanced(data.times, output),
                'overshoot': self._compute_overshoot_advanced(output),
                'rise_time': self._compute_rise_time_advanced(data.times, output),
                'peak_time': self._compute_peak_time(data.times, output),
                'steady_state_value': float(output[-1]),
                'initial_value': float(output[0])
            }

            results[f'output_{i}'] = step_info

        return results

    def _analyze_tracking_performance(self, data: DataProtocol,
                                    reference: np.ndarray,
                                    output_indices: List[int]) -> Dict[str, Any]:
        """Analyze tracking performance."""
        results = {}

        # Extract outputs
        outputs = data.states[:, output_indices]

        # Ensure reference has compatible dimensions
        if reference.ndim == 1:
            reference = reference.reshape(-1, 1)

        min_length = min(len(outputs), len(reference))
        outputs = outputs[:min_length]
        ref = reference[:min_length, :outputs.shape[1]]

        # Compute tracking errors
        error = outputs - ref

        # Time-varying error analysis
        error_envelope = np.sqrt(np.sum(error**2, axis=1))

        results['error_statistics'] = {
            'max_error': float(np.max(error_envelope)),
            'mean_error': float(np.mean(error_envelope)),
            'std_error': float(np.std(error_envelope)),
            'final_error': float(error_envelope[-1])
        }

        # Convergence analysis
        convergence_info = self._analyze_error_convergence(data.times, error_envelope)
        results['convergence'] = convergence_info

        return results

    def _analyze_control_effort(self, data: DataProtocol) -> Dict[str, Any]:
        """Analyze control effort characteristics."""
        controls = data.controls.flatten() if data.controls.ndim > 1 else data.controls

        results = {
            'rms_control': float(np.sqrt(np.mean(controls**2))),
            'peak_control': float(np.max(np.abs(controls))),
            'control_variance': float(np.var(controls)),
            'control_smoothness': self._compute_control_smoothness(controls),
            'saturation_analysis': self._analyze_saturation(controls)
        }

        return results

    def _analyze_frequency_domain(self, system_matrices: Tuple[np.ndarray, ...]) -> Dict[str, Any]:
        """Perform frequency domain analysis."""
        try:
            A, B, C, D = system_matrices

            # Create state-space system
            sys = signal.StateSpace(A, B, C, D)

            # Frequency response
            frequencies = np.logspace(
                np.log10(self.frequency_range[0]),
                np.log10(self.frequency_range[1]),
                1000
            )

            w, H = signal.freqresp(sys, frequencies)

            # Extract magnitude and phase
            magnitude_db = 20 * np.log10(np.abs(H.flatten()))
            phase_deg = np.angle(H.flatten()) * 180 / np.pi

            # Compute frequency domain metrics
            bandwidth = self._compute_bandwidth(w, magnitude_db)
            resonance_peak = self._compute_resonance_peak(magnitude_db)

            results = {
                'bandwidth': bandwidth,
                'resonance_peak': resonance_peak,
                'dc_gain': float(magnitude_db[0]),
                'high_frequency_gain': float(magnitude_db[-1]),
                'frequencies': w.tolist(),
                'magnitude_db': magnitude_db.tolist(),
                'phase_deg': phase_deg.tolist()
            }

            # Stability margins
            margins = self._compute_stability_margins(sys)
            results['stability_margins'] = margins

            return results

        except Exception as e:
            warnings.warn(f"Frequency domain analysis failed: {e}")
            return {'error': str(e)}

    def _compute_advanced_metrics(self, data: DataProtocol,
                                reference: Optional[np.ndarray],
                                output_indices: List[int]) -> Dict[str, Any]:
        """Compute advanced performance metrics."""
        results = {}

        # Signal-to-noise ratio estimation
        if reference is not None:
            snr_analysis = self._estimate_snr(data, reference, output_indices)
            results['snr_analysis'] = snr_analysis

        # Transient behavior analysis
        transient_analysis = self._analyze_transient_behavior(data, output_indices)
        results['transient_behavior'] = transient_analysis

        # Energy consumption analysis
        energy_analysis = self._analyze_energy_consumption(data)
        results['energy_consumption'] = energy_analysis

        return results

    # Helper methods for advanced computations
    def _compute_settling_time_advanced(self, times: np.ndarray, output: np.ndarray) -> float:
        """Compute settling time with multiple criteria."""
        final_value = output[-1]
        tolerance = self.reference_tolerance * abs(final_value)

        # Find last excursion outside tolerance band
        outside_band = np.abs(output - final_value) > tolerance

        if not np.any(outside_band):
            return 0.0

        # Find the last time it was outside the band
        last_outside_idx = np.where(outside_band)[0][-1]
        return float(times[last_outside_idx])

    def _compute_overshoot_advanced(self, output: np.ndarray) -> Dict[str, float]:
        """Compute comprehensive overshoot analysis."""
        final_value = output[-1]

        if abs(final_value) < 1e-12:
            return {'max_overshoot': 0.0, 'undershoot': 0.0, 'num_peaks': 0}

        # Find all local maxima and minima
        from scipy.signal import find_peaks

        peaks_idx, _ = find_peaks(output)
        valleys_idx, _ = find_peaks(-output)

        # Compute overshoot and undershoot
        max_overshoot = 0.0
        undershoot = 0.0

        if len(peaks_idx) > 0:
            max_peak = np.max(output[peaks_idx])
            max_overshoot = (max_peak - final_value) / abs(final_value) * 100

        if len(valleys_idx) > 0:
            min_valley = np.min(output[valleys_idx])
            undershoot = (final_value - min_valley) / abs(final_value) * 100

        return {
            'max_overshoot': float(max(0.0, max_overshoot)),
            'undershoot': float(max(0.0, undershoot)),
            'num_peaks': len(peaks_idx)
        }

    def _compute_rise_time_advanced(self, times: np.ndarray, output: np.ndarray) -> Dict[str, float]:
        """Compute rise time with multiple definitions."""
        final_value = output[-1]
        initial_value = output[0]

        if abs(final_value - initial_value) < 1e-12:
            return {'rise_time_10_90': 0.0, 'rise_time_5_95': 0.0}

        # 10%-90% rise time
        threshold_10 = initial_value + 0.1 * (final_value - initial_value)
        threshold_90 = initial_value + 0.9 * (final_value - initial_value)

        try:
            if final_value > initial_value:
                idx_10 = np.where(output >= threshold_10)[0][0]
                idx_90 = np.where(output >= threshold_90)[0][0]
            else:
                idx_10 = np.where(output <= threshold_10)[0][0]
                idx_90 = np.where(output <= threshold_90)[0][0]

            rise_time_10_90 = times[idx_90] - times[idx_10]
        except IndexError:
            rise_time_10_90 = times[-1] - times[0]

        # 5%-95% rise time
        threshold_5 = initial_value + 0.05 * (final_value - initial_value)
        threshold_95 = initial_value + 0.95 * (final_value - initial_value)

        try:
            if final_value > initial_value:
                idx_5 = np.where(output >= threshold_5)[0][0]
                idx_95 = np.where(output >= threshold_95)[0][0]
            else:
                idx_5 = np.where(output <= threshold_5)[0][0]
                idx_95 = np.where(output <= threshold_95)[0][0]

            rise_time_5_95 = times[idx_95] - times[idx_5]
        except IndexError:
            rise_time_5_95 = times[-1] - times[0]

        return {
            'rise_time_10_90': float(rise_time_10_90),
            'rise_time_5_95': float(rise_time_5_95)
        }

    def _compute_peak_time(self, times: np.ndarray, output: np.ndarray) -> float:
        """Compute time to peak value."""
        peak_idx = np.argmax(np.abs(output))
        return float(times[peak_idx])

    def _analyze_error_convergence(self, times: np.ndarray, error_envelope: np.ndarray) -> Dict[str, Any]:
        """Analyze error convergence characteristics."""
        # Fit exponential decay to error envelope
        try:
            def exp_decay(t, a, b, c):
                return a * np.exp(-b * t) + c

            popt, _ = optimize.curve_fit(
                exp_decay, times, error_envelope,
                p0=[error_envelope[0], 1.0, error_envelope[-1]],
                maxfev=1000
            )

            time_constant = 1.0 / popt[1] if popt[1] > 0 else np.inf

            return {
                'time_constant': float(time_constant),
                'decay_rate': float(popt[1]),
                'steady_state_error': float(popt[2]),
                'fit_quality': 'good' if time_constant < np.inf else 'poor'
            }

        except Exception:
            return {
                'time_constant': np.inf,
                'decay_rate': 0.0,
                'steady_state_error': float(error_envelope[-1]),
                'fit_quality': 'failed'
            }

    def _compute_control_smoothness(self, controls: np.ndarray) -> float:
        """Compute control signal smoothness metric."""
        if len(controls) < 2:
            return 0.0

        # Total variation
        total_variation = np.sum(np.abs(np.diff(controls)))
        signal_range = np.max(controls) - np.min(controls)

        if signal_range < 1e-12:
            return 1.0  # Constant signal is perfectly smooth

        # Normalized smoothness (1 = smooth, 0 = very rough)
        smoothness = 1.0 / (1.0 + total_variation / signal_range)
        return float(smoothness)

    def _analyze_saturation(self, controls: np.ndarray, saturation_limit: float = 10.0) -> Dict[str, Any]:
        """Analyze control signal saturation."""
        saturated_samples = np.sum(np.abs(controls) >= saturation_limit)
        saturation_percentage = saturated_samples / len(controls) * 100

        return {
            'saturation_percentage': float(saturation_percentage),
            'max_control': float(np.max(np.abs(controls))),
            'saturation_limit': saturation_limit,
            'is_saturated': saturated_samples > 0
        }

    def _compute_bandwidth(self, frequencies: np.ndarray, magnitude_db: np.ndarray) -> float:
        """Compute -3dB bandwidth."""
        try:
            dc_gain = magnitude_db[0]
            cutoff_level = dc_gain - 3.0

            # Find first frequency where magnitude drops below cutoff
            cutoff_idx = np.where(magnitude_db <= cutoff_level)[0]

            if len(cutoff_idx) > 0:
                return float(frequencies[cutoff_idx[0]])
            else:
                return float(frequencies[-1])  # Bandwidth beyond analysis range

        except Exception:
            return np.nan

    def _compute_resonance_peak(self, magnitude_db: np.ndarray) -> Dict[str, float]:
        """Compute resonance peak information."""
        max_magnitude = np.max(magnitude_db)
        dc_gain = magnitude_db[0]
        resonance_peak_db = max_magnitude - dc_gain

        return {
            'peak_magnitude_db': float(max_magnitude),
            'resonance_peak_db': float(resonance_peak_db),
            'peak_frequency_idx': int(np.argmax(magnitude_db))
        }

    def _compute_stability_margins(self, sys: signal.StateSpace) -> Dict[str, float]:
        """Compute stability margins."""
        try:
            # This would require more sophisticated analysis
            # Placeholder implementation
            return {
                'gain_margin_db': np.nan,
                'phase_margin_deg': np.nan,
                'delay_margin_s': np.nan
            }
        except Exception:
            return {
                'gain_margin_db': np.nan,
                'phase_margin_deg': np.nan,
                'delay_margin_s': np.nan
            }

    def _estimate_snr(self, data: DataProtocol, reference: np.ndarray, output_indices: List[int]) -> Dict[str, float]:
        """Estimate signal-to-noise ratio."""
        # Simplified SNR estimation
        outputs = data.states[:, output_indices]

        if reference.ndim == 1:
            reference = reference.reshape(-1, 1)

        min_length = min(len(outputs), len(reference))
        outputs = outputs[:min_length]
        ref = reference[:min_length, :outputs.shape[1]]

        signal_power = np.mean(ref**2)
        noise_power = np.mean((outputs - ref)**2)

        if noise_power > 0:
            snr_db = 10 * np.log10(signal_power / noise_power)
        else:
            snr_db = np.inf

        return {'snr_db': float(snr_db)}

    def _analyze_transient_behavior(self, data: DataProtocol, output_indices: List[int]) -> Dict[str, Any]:
        """Analyze transient behavior characteristics."""
        results = {}

        for i, output_idx in enumerate(output_indices):
            if output_idx >= data.states.shape[1]:
                continue

            output = data.states[:, output_idx]

            # Transient settling analysis
            settling_info = self._analyze_settling_behavior(data.times, output)
            results[f'output_{i}'] = settling_info

        return results

    def _analyze_settling_behavior(self, times: np.ndarray, output: np.ndarray) -> Dict[str, Any]:
        """Analyze settling behavior in detail."""
        final_value = output[-1]

        # Multiple tolerance bands
        tolerances = [0.01, 0.02, 0.05]  # 1%, 2%, 5%
        settling_times = {}

        for tol in tolerances:
            settling_times[f'settling_time_{int(tol*100)}pct'] = self._compute_settling_time_tolerance(
                times, output, tol
            )

        return settling_times

    def _compute_settling_time_tolerance(self, times: np.ndarray, output: np.ndarray, tolerance: float) -> float:
        """Compute settling time for specific tolerance."""
        final_value = output[-1]
        tolerance_band = tolerance * abs(final_value)

        outside_band = np.abs(output - final_value) > tolerance_band

        if not np.any(outside_band):
            return 0.0

        last_outside_idx = np.where(outside_band)[0][-1]
        return float(times[last_outside_idx])

    def _analyze_energy_consumption(self, data: DataProtocol) -> Dict[str, float]:
        """Analyze energy consumption characteristics."""
        controls = data.controls.flatten() if data.controls.ndim > 1 else data.controls
        dt = np.mean(np.diff(data.times)) if len(data.times) > 1 else 0.01

        # Total energy
        total_energy = np.trapz(controls**2, dx=dt)

        # Average power
        avg_power = total_energy / (data.times[-1] - data.times[0])

        return {
            'total_energy': float(total_energy),
            'average_power': float(avg_power),
            'peak_power': float(np.max(controls**2))
        }


# Legacy compatibility: Original benchmarks control metrics functions
def compute_ise(t: np.ndarray, x: np.ndarray) -> float:
    """Compute Integral of Squared Error (ISE) for all state variables.

    The ISE metric integrates the squared state deviations over time:
    ISE = ∫₀ᵀ ||x(t)||² dt

    This metric penalizes large deviations heavily and provides a measure
    of overall tracking performance. Lower values indicate better control.

    Parameters
    ----------
    t : np.ndarray
        Time vector of length N+1
    x : np.ndarray
        State trajectories of shape (B, N+1, S) for B batches, S states

    Returns
    -------
    float
        ISE value averaged across batch dimension
    """
    # Compute time step differences and broadcast to batch
    dt = np.diff(t)
    dt_b = dt[None, :]  # shape (1, N)

    if dt_b.size == 0:
        # Degenerate case with single time step
        dt_b = np.array([[1.0]])

    # Integral of squared error over all states
    ise = np.sum((x[:, :-1, :] ** 2) * dt_b[:, :, None], axis=(1, 2))
    return float(np.mean(ise))


def compute_itae(t: np.ndarray, x: np.ndarray) -> float:
    """Compute Integral of Time-weighted Absolute Error (ITAE).

    The ITAE metric emphasizes errors that occur later in the trajectory:
    ITAE = ∫₀ᵀ t·||x(t)||₁ dt

    This metric is particularly useful for evaluating settling behavior
    and penalizes persistent steady-state errors more heavily than
    transient errors early in the response.

    Parameters
    ----------
    t : np.ndarray
        Time vector of length N+1
    x : np.ndarray
        State trajectories of shape (B, N+1, S)

    Returns
    -------
    float
        ITAE value averaged across batch dimension
    """
    # Time weights for ITAE calculation
    time_weights = t[:-1]

    # Integral of time-weighted absolute error
    itae = np.sum(
        np.abs(x[:, :-1, :]) * time_weights[None, :, None],
        axis=(1, 2)
    )
    return float(np.mean(itae))


def compute_rms_control_effort(u: np.ndarray) -> float:
    """Compute Root Mean Square (RMS) control effort.

    The RMS control effort measures the average magnitude of control inputs:
    RMS = √(⟨u²(t)⟩)

    This metric quantifies actuator usage and energy consumption. Lower
    values indicate more efficient control that requires less actuation.

    Parameters
    ----------
    u : np.ndarray
        Control input trajectories of shape (B, N)

    Returns
    -------
    float
        RMS control effort averaged across batch dimension
    """
    # RMS control effort for each trajectory in batch
    rms_u = np.sqrt(np.mean(u ** 2, axis=1))
    return float(np.mean(rms_u))