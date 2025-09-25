#==========================================================================================\\\
#======================= src/analysis/validation/metrics.py ======================\\\
#==========================================================================================\\\
"""
Statistical and validation metrics for analysis systems.

This module provides comprehensive metrics computation for validating
control system performance, statistical analysis, and benchmarking.
"""

from typing import Dict, List, Tuple, Any, Optional, Union
import numpy as np
from scipy import stats
import warnings


def compute_basic_metrics(data: np.ndarray) -> Dict[str, float]:
    """
    Compute basic statistical metrics for data analysis.

    Args:
        data: Input data array

    Returns:
        Dictionary containing basic statistical metrics
    """
    if len(data) == 0:
        return {
            'mean': 0.0,
            'std': 0.0,
            'min': 0.0,
            'max': 0.0,
            'median': 0.0,
            'count': 0
        }

    return {
        'mean': float(np.mean(data)),
        'std': float(np.std(data)),
        'min': float(np.min(data)),
        'max': float(np.max(data)),
        'median': float(np.median(data)),
        'count': len(data)
    }


def compute_performance_metrics(
    reference: np.ndarray,
    actual: np.ndarray
) -> Dict[str, float]:
    """
    Compute performance metrics comparing actual vs reference data.

    Args:
        reference: Reference/target data
        actual: Actual measured data

    Returns:
        Dictionary containing performance metrics
    """
    if len(reference) != len(actual):
        raise ValueError("Reference and actual data must have same length")

    if len(reference) == 0:
        return {'mse': 0.0, 'rmse': 0.0, 'mae': 0.0, 'max_error': 0.0}

    error = actual - reference
    mse = float(np.mean(error**2))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(error)))
    max_error = float(np.max(np.abs(error)))

    return {
        'mse': mse,
        'rmse': rmse,
        'mae': mae,
        'max_error': max_error
    }


def compute_control_metrics(
    control_signals: np.ndarray,
    time_vector: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """
    Compute control-specific performance metrics.

    Args:
        control_signals: Control input signals over time
        time_vector: Optional time vector for time-based metrics

    Returns:
        Dictionary containing control metrics
    """
    if len(control_signals) == 0:
        return {
            'control_effort': 0.0,
            'max_control': 0.0,
            'control_variation': 0.0,
            'settling_time': 0.0
        }

    # Basic control metrics
    control_effort = float(np.sum(np.abs(control_signals)))
    max_control = float(np.max(np.abs(control_signals)))

    # Control variation (total variation)
    if len(control_signals) > 1:
        control_variation = float(np.sum(np.abs(np.diff(control_signals))))
    else:
        control_variation = 0.0

    # Settling time estimation (time to reach within 5% of final value)
    settling_time = 0.0
    if time_vector is not None and len(time_vector) == len(control_signals):
        final_value = control_signals[-1]
        tolerance = 0.05 * abs(final_value) if abs(final_value) > 1e-10 else 0.05

        # Find last time control signal was outside tolerance
        for i in range(len(control_signals) - 1, -1, -1):
            if abs(control_signals[i] - final_value) > tolerance:
                settling_time = float(time_vector[min(i + 1, len(time_vector) - 1)])
                break

    return {
        'control_effort': control_effort,
        'max_control': max_control,
        'control_variation': control_variation,
        'settling_time': settling_time
    }


def compute_stability_metrics(
    states: np.ndarray,
    reference_state: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """
    Compute stability-related metrics for state trajectories.

    Args:
        states: State trajectory matrix (time x state_dim)
        reference_state: Optional reference state for deviation metrics

    Returns:
        Dictionary containing stability metrics
    """
    if len(states) == 0:
        return {
            'max_deviation': 0.0,
            'final_deviation': 0.0,
            'stability_margin': 0.0,
            'lyapunov_estimate': 0.0
        }

    if reference_state is None:
        reference_state = np.zeros(states.shape[1])

    # Deviation from reference
    deviations = states - reference_state
    deviation_norms = np.linalg.norm(deviations, axis=1)

    max_deviation = float(np.max(deviation_norms))
    final_deviation = float(deviation_norms[-1])

    # Simple stability margin (inverse of max deviation)
    stability_margin = 1.0 / (1.0 + max_deviation)

    # Rough Lyapunov exponent estimate
    lyapunov_estimate = 0.0
    if len(deviation_norms) > 10:
        # Use log of deviation growth
        nonzero_deviations = deviation_norms[deviation_norms > 1e-12]
        if len(nonzero_deviations) > 5:
            log_deviations = np.log(nonzero_deviations)
            if len(log_deviations) > 1:
                lyapunov_estimate = float(np.mean(np.diff(log_deviations)))

    return {
        'max_deviation': max_deviation,
        'final_deviation': final_deviation,
        'stability_margin': stability_margin,
        'lyapunov_estimate': lyapunov_estimate
    }


def compute_frequency_metrics(
    signal: np.ndarray,
    sampling_rate: float,
    frequency_bands: Optional[List[Tuple[float, float]]] = None
) -> Dict[str, Any]:
    """
    Compute frequency domain metrics for signal analysis.

    Args:
        signal: Input signal
        sampling_rate: Sampling rate in Hz
        frequency_bands: Optional list of (low, high) frequency bands

    Returns:
        Dictionary containing frequency domain metrics
    """
    if len(signal) < 2:
        return {
            'dominant_frequency': 0.0,
            'bandwidth': 0.0,
            'power_spectrum': np.array([]),
            'frequencies': np.array([])
        }

    # Compute power spectral density
    frequencies = np.fft.fftfreq(len(signal), 1/sampling_rate)
    fft_signal = np.fft.fft(signal)
    power_spectrum = np.abs(fft_signal)**2

    # Only consider positive frequencies
    positive_freq_idx = frequencies >= 0
    frequencies = frequencies[positive_freq_idx]
    power_spectrum = power_spectrum[positive_freq_idx]

    # Find dominant frequency
    if len(power_spectrum) > 0:
        dominant_freq_idx = np.argmax(power_spectrum)
        dominant_frequency = float(frequencies[dominant_freq_idx])
    else:
        dominant_frequency = 0.0

    # Estimate bandwidth (90% power)
    total_power = np.sum(power_spectrum)
    cumulative_power = np.cumsum(power_spectrum)

    if total_power > 0:
        # Find frequencies where cumulative power is 5% and 95%
        low_idx = np.argmax(cumulative_power >= 0.05 * total_power)
        high_idx = np.argmax(cumulative_power >= 0.95 * total_power)
        bandwidth = float(frequencies[high_idx] - frequencies[low_idx])
    else:
        bandwidth = 0.0

    # Compute power in frequency bands if specified
    band_power = {}
    if frequency_bands:
        for i, (low, high) in enumerate(frequency_bands):
            band_mask = (frequencies >= low) & (frequencies <= high)
            band_power[f'band_{i}_power'] = float(np.sum(power_spectrum[band_mask]))

    result = {
        'dominant_frequency': dominant_frequency,
        'bandwidth': bandwidth,
        'power_spectrum': power_spectrum,
        'frequencies': frequencies,
        **band_power
    }

    return result


def compute_statistical_significance(
    data1: np.ndarray,
    data2: np.ndarray,
    test_type: str = 'ttest'
) -> Dict[str, float]:
    """
    Compute statistical significance between two data sets.

    Args:
        data1: First data set
        data2: Second data set
        test_type: Type of statistical test ('ttest', 'mannwhitney', 'ks')

    Returns:
        Dictionary containing test statistics and p-value
    """
    if len(data1) == 0 or len(data2) == 0:
        return {'statistic': 0.0, 'p_value': 1.0, 'significant': False}

    try:
        if test_type == 'ttest':
            statistic, p_value = stats.ttest_ind(data1, data2)
        elif test_type == 'mannwhitney':
            statistic, p_value = stats.mannwhitneyu(data1, data2, alternative='two-sided')
        elif test_type == 'ks':
            statistic, p_value = stats.ks_2samp(data1, data2)
        else:
            raise ValueError(f"Unknown test type: {test_type}")

        significant = p_value < 0.05  # Standard significance level

        return {
            'statistic': float(statistic),
            'p_value': float(p_value),
            'significant': bool(significant)
        }

    except Exception as e:
        warnings.warn(f"Statistical test failed: {e}")
        return {'statistic': 0.0, 'p_value': 1.0, 'significant': False}


def compute_robustness_metrics(
    nominal_performance: Dict[str, float],
    perturbed_performances: List[Dict[str, float]],
    metric_names: Optional[List[str]] = None
) -> Dict[str, Dict[str, float]]:
    """
    Compute robustness metrics comparing nominal vs perturbed performance.

    Args:
        nominal_performance: Performance metrics for nominal conditions
        perturbed_performances: List of performance metrics under perturbations
        metric_names: Optional list of metric names to analyze

    Returns:
        Dictionary of robustness metrics for each performance metric
    """
    if not perturbed_performances:
        return {}

    if metric_names is None:
        metric_names = list(nominal_performance.keys())

    robustness_metrics = {}

    for metric_name in metric_names:
        if metric_name not in nominal_performance:
            continue

        nominal_value = nominal_performance[metric_name]
        perturbed_values = []

        for perf in perturbed_performances:
            if metric_name in perf:
                perturbed_values.append(perf[metric_name])

        if not perturbed_values:
            continue

        perturbed_array = np.array(perturbed_values)

        # Compute robustness metrics
        mean_deviation = float(np.mean(np.abs(perturbed_array - nominal_value)))
        max_deviation = float(np.max(np.abs(perturbed_array - nominal_value)))
        std_deviation = float(np.std(perturbed_array))

        # Robustness index (inverse of relative deviation)
        if abs(nominal_value) > 1e-12:
            relative_deviation = mean_deviation / abs(nominal_value)
            robustness_index = 1.0 / (1.0 + relative_deviation)
        else:
            robustness_index = 1.0 if mean_deviation < 1e-6 else 0.0

        robustness_metrics[metric_name] = {
            'mean_deviation': mean_deviation,
            'max_deviation': max_deviation,
            'std_deviation': std_deviation,
            'robustness_index': float(robustness_index)
        }

    return robustness_metrics


def compute_comprehensive_metrics(
    states: np.ndarray,
    controls: np.ndarray,
    time_vector: np.ndarray,
    reference_states: Optional[np.ndarray] = None,
    reference_controls: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Compute comprehensive metrics for control system analysis.

    Args:
        states: State trajectory matrix
        controls: Control signal vector
        time_vector: Time vector
        reference_states: Optional reference state trajectory
        reference_controls: Optional reference control signals

    Returns:
        Dictionary containing comprehensive metrics
    """
    metrics = {}

    # Basic state metrics
    if len(states) > 0:
        for i in range(states.shape[1]):
            state_data = states[:, i]
            metrics[f'state_{i}_metrics'] = compute_basic_metrics(state_data)

    # Control metrics
    if len(controls) > 0:
        metrics['control_metrics'] = compute_control_metrics(controls, time_vector)

    # Performance metrics vs reference
    if reference_states is not None and len(reference_states) > 0:
        if len(states) > 0 and states.shape == reference_states.shape:
            for i in range(states.shape[1]):
                metrics[f'state_{i}_performance'] = compute_performance_metrics(
                    reference_states[:, i], states[:, i]
                )

    if reference_controls is not None and len(reference_controls) > 0:
        if len(controls) == len(reference_controls):
            metrics['control_performance'] = compute_performance_metrics(
                reference_controls, controls
            )

    # Stability metrics
    if len(states) > 0:
        ref_state = reference_states[-1] if reference_states is not None else None
        metrics['stability_metrics'] = compute_stability_metrics(states, ref_state)

    return metrics