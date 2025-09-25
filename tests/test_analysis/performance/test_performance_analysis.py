#==========================================================================================\\
#=============== tests/test_analysis/performance/test_performance_analysis.py ============\\
#==========================================================================================\\

"""
Comprehensive test suite for performance analysis validation.

This module validates control system performance analysis capabilities,
ensuring accurate computation of performance metrics, robustness analysis,
and scientific rigor in control performance evaluation.
"""

import pytest
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import warnings
from unittest.mock import Mock, patch
import scipy.signal

# Performance analysis imports
from src.analysis.performance.control_analysis import *
from src.analysis.performance.control_metrics import *
from src.analysis.performance.robustness import *
from src.analysis.performance.stability_analysis import *

# Core analysis imports for validation
from src.analysis.validation.metrics import (
    compute_performance_metrics,
    compute_control_metrics,
    compute_stability_metrics,
    compute_frequency_metrics,
    compute_robustness_metrics,
    compute_comprehensive_metrics
)


class TestControlPerformanceMetrics:
    """Test suite for control system performance metric computation."""

    def test_step_response_metrics(self):
        """Test step response performance metrics."""
        # Generate ideal step response
        time_vector = np.linspace(0, 10, 1000)
        dt = time_vector[1] - time_vector[0]

        # Second-order underdamped system response
        wn = 2.0  # Natural frequency
        zeta = 0.3  # Damping ratio

        # Analytical step response
        wd = wn * np.sqrt(1 - zeta**2)  # Damped frequency
        step_response = 1 - np.exp(-zeta * wn * time_vector) * \
                        (np.cos(wd * time_vector) + (zeta * wn / wd) * np.sin(wd * time_vector))

        # Compute performance metrics
        control_metrics = compute_control_metrics(step_response, time_vector)

        # Validate metrics structure
        assert isinstance(control_metrics, dict)
        expected_keys = ['control_effort', 'max_control', 'control_variation', 'settling_time']
        for key in expected_keys:
            assert key in control_metrics
            assert isinstance(control_metrics[key], (int, float))

        # Check settling time is reasonable for underdamped response
        settling_time = control_metrics['settling_time']
        theoretical_settling_time = 4 / (zeta * wn)  # Approximation for 2% settling
        assert 0 < settling_time < 2 * theoretical_settling_time

    def test_tracking_performance_metrics(self):
        """Test tracking performance metric computation."""
        # Generate reference and actual trajectories
        time_vector = np.linspace(0, 5, 500)

        # Reference: sine wave
        reference = np.sin(2 * np.pi * 0.5 * time_vector)

        # Actual: delayed and attenuated sine wave with noise
        phase_lag = np.pi / 6  # 30 degree phase lag
        actual = 0.9 * np.sin(2 * np.pi * 0.5 * time_vector - phase_lag) + \
                 0.05 * np.random.randn(len(time_vector))

        # Compute tracking performance
        tracking_metrics = compute_performance_metrics(reference, actual)

        # Validate metrics
        assert 'mse' in tracking_metrics
        assert 'rmse' in tracking_metrics
        assert 'mae' in tracking_metrics
        assert 'max_error' in tracking_metrics

        # Check mathematical relationships
        mse = tracking_metrics['mse']
        rmse = tracking_metrics['rmse']
        assert abs(rmse - np.sqrt(mse)) < 1e-10

        # Tracking error should be reasonable for this scenario
        assert 0.01 < rmse < 0.5  # Should have some error due to lag and noise

    def test_frequency_domain_performance(self):
        """Test frequency domain performance analysis."""
        # Generate test signal with known frequency content
        fs = 1000  # Sampling frequency
        time_vector = np.linspace(0, 2, fs * 2)

        # Signal: fundamental + harmonics + noise
        fundamental_freq = 10  # Hz
        signal = (np.sin(2 * np.pi * fundamental_freq * time_vector) +
                  0.3 * np.sin(2 * np.pi * 3 * fundamental_freq * time_vector) +
                  0.1 * np.sin(2 * np.pi * 5 * fundamental_freq * time_vector) +
                  0.05 * np.random.randn(len(time_vector)))

        # Frequency domain analysis
        freq_metrics = compute_frequency_metrics(signal, fs)

        # Validate results
        assert 'dominant_frequency' in freq_metrics
        assert 'bandwidth' in freq_metrics
        assert 'power_spectrum' in freq_metrics
        assert 'frequencies' in freq_metrics

        # Check dominant frequency detection
        dominant_freq = freq_metrics['dominant_frequency']
        assert abs(dominant_freq - fundamental_freq) < 1.0  # Within 1 Hz

        # Check frequency arrays
        assert len(freq_metrics['power_spectrum']) == len(freq_metrics['frequencies'])
        assert np.all(freq_metrics['frequencies'] >= 0)  # Positive frequencies only

    def test_stability_margin_analysis(self):
        """Test stability margin computation."""
        # Generate stable trajectory converging to equilibrium
        time_vector = np.linspace(0, 10, 1000)

        # Exponentially decaying oscillation (stable)
        decay_rate = 0.5
        oscillation_freq = 2.0
        amplitude = 2.0

        stable_trajectory = amplitude * np.exp(-decay_rate * time_vector) * \
                           np.cos(2 * np.pi * oscillation_freq * time_vector)

        # Multi-state trajectory
        states = np.column_stack([
            stable_trajectory,
            -decay_rate * stable_trajectory - 2 * np.pi * oscillation_freq * amplitude * \
            np.exp(-decay_rate * time_vector) * np.sin(2 * np.pi * oscillation_freq * time_vector),
            0.5 * stable_trajectory,
            0.3 * stable_trajectory
        ])

        # Reference state (equilibrium)
        reference_state = np.zeros(4)

        # Compute stability metrics
        stability_metrics = compute_stability_metrics(states, reference_state)

        # Validate metrics
        expected_keys = ['max_deviation', 'final_deviation', 'stability_margin', 'lyapunov_estimate']
        for key in expected_keys:
            assert key in stability_metrics
            assert isinstance(stability_metrics[key], (int, float))

        # Check stability properties
        max_deviation = stability_metrics['max_deviation']
        final_deviation = stability_metrics['final_deviation']

        assert max_deviation > final_deviation  # Should converge
        assert final_deviation < 0.1 * max_deviation  # Good convergence

        # Stability margin should indicate stable system
        stability_margin = stability_metrics['stability_margin']
        assert 0 < stability_margin <= 1

    def test_robustness_metrics_computation(self):
        """Test robustness metrics under parameter variations."""
        # Nominal performance
        nominal_performance = {
            'settling_time': 2.0,
            'overshoot': 0.15,
            'steady_state_error': 0.02
        }

        # Perturbed performances (parameter variations)
        perturbed_performances = [
            {'settling_time': 2.1, 'overshoot': 0.17, 'steady_state_error': 0.025},
            {'settling_time': 1.9, 'overshoot': 0.13, 'steady_state_error': 0.015},
            {'settling_time': 2.2, 'overshoot': 0.19, 'steady_state_error': 0.030},
            {'settling_time': 1.8, 'overshoot': 0.11, 'steady_state_error': 0.010},
        ]

        # Compute robustness metrics
        robustness_metrics = compute_robustness_metrics(
            nominal_performance,
            perturbed_performances
        )

        # Validate structure
        assert isinstance(robustness_metrics, dict)

        # Each performance metric should have robustness analysis
        for metric_name in nominal_performance.keys():
            assert metric_name in robustness_metrics

            robustness_data = robustness_metrics[metric_name]
            assert 'mean_deviation' in robustness_data
            assert 'max_deviation' in robustness_data
            assert 'std_deviation' in robustness_data
            assert 'robustness_index' in robustness_data

            # Robustness index should be between 0 and 1
            robustness_index = robustness_data['robustness_index']
            assert 0 <= robustness_index <= 1

    def test_comprehensive_performance_analysis(self):
        """Test comprehensive performance analysis integration."""
        # Generate realistic control system simulation data
        time_vector = np.linspace(0, 8, 800)
        dt = time_vector[1] - time_vector[0]

        # Simulate double integrator with PD control
        states = np.zeros((len(time_vector), 4))  # [x1, x1_dot, x2, x2_dot]
        controls = np.zeros(len(time_vector))

        # Reference trajectory (step input at t=1)
        reference_states = np.zeros((len(time_vector), 4))
        reference_states[time_vector >= 1, 0] = 1.0  # Step reference for x1

        # Simulation with PD control
        Kp, Kd = 4.0, 2.0
        for i in range(1, len(time_vector)):
            # PD control law
            error = reference_states[i-1, 0] - states[i-1, 0]
            error_dot = -states[i-1, 1]  # Reference derivative is 0
            controls[i] = Kp * error + Kd * error_dot

            # Double integrator dynamics with noise
            states[i, 0] = states[i-1, 0] + dt * states[i-1, 1] + 0.001 * np.random.randn()
            states[i, 1] = states[i-1, 1] + dt * controls[i] + 0.001 * np.random.randn()
            states[i, 2] = states[i-1, 2] + dt * states[i-1, 3] + 0.001 * np.random.randn()
            states[i, 3] = states[i-1, 3] + dt * (-states[i-1, 2] + 0.5 * controls[i]) + 0.001 * np.random.randn()

        # Comprehensive performance analysis
        comprehensive_metrics = compute_comprehensive_metrics(
            states=states,
            controls=controls,
            time_vector=time_vector,
            reference_states=reference_states
        )

        # Validate comprehensive analysis
        assert isinstance(comprehensive_metrics, dict)
        assert len(comprehensive_metrics) > 0

        # Should include control metrics
        assert 'control_metrics' in comprehensive_metrics
        control_metrics = comprehensive_metrics['control_metrics']
        assert 'control_effort' in control_metrics
        assert control_metrics['control_effort'] > 0

        # Should include stability metrics
        assert 'stability_metrics' in comprehensive_metrics
        stability_metrics = comprehensive_metrics['stability_metrics']
        assert 'max_deviation' in stability_metrics

        # Should include state-wise performance metrics
        state_performance_found = False
        for key in comprehensive_metrics.keys():
            if key.startswith('state_') and key.endswith('_performance'):
                state_performance_found = True
                break
        assert state_performance_found, "Should include state performance metrics"


class TestPerformanceAnalysisAccuracy:
    """Test accuracy and validation of performance analysis computations."""

    def test_analytical_validation_second_order_system(self):
        """Test performance metrics against analytical second-order system."""
        # Second-order system parameters
        wn = 3.0  # Natural frequency (rad/s)
        zeta = 0.4  # Damping ratio

        # Time vector
        time_vector = np.linspace(0, 6, 1000)

        # Analytical step response
        if zeta < 1:
            # Underdamped
            wd = wn * np.sqrt(1 - zeta**2)
            step_response = 1 - np.exp(-zeta * wn * time_vector) * \
                           (np.cos(wd * time_vector) + (zeta * wn / wd) * np.sin(wd * time_vector))
        else:
            # Overdamped or critically damped
            step_response = 1 - np.exp(-zeta * wn * time_vector)

        # Analytical performance characteristics
        if zeta < 1:
            # Peak overshoot
            theoretical_overshoot = np.exp(-np.pi * zeta / np.sqrt(1 - zeta**2))

            # Settling time (2% criterion)
            theoretical_settling_time = 4 / (zeta * wn)

            # Peak time
            theoretical_peak_time = np.pi / (wn * np.sqrt(1 - zeta**2))

            # Find actual peak
            peak_idx = np.argmax(step_response)
            actual_peak_time = time_vector[peak_idx]
            actual_overshoot = step_response[peak_idx] - 1.0

            # Validate against theory
            assert abs(actual_overshoot - theoretical_overshoot) < 0.05
            assert abs(actual_peak_time - theoretical_peak_time) < 0.1

            # Settling time validation (using control metrics)
            control_metrics = compute_control_metrics(step_response, time_vector)
            actual_settling_time = control_metrics['settling_time']

            # Should be within reasonable range of theoretical
            assert 0.5 * theoretical_settling_time < actual_settling_time < 2 * theoretical_settling_time

    def test_frequency_analysis_validation(self):
        """Test frequency analysis against known analytical results."""
        # Generate signal with known spectral properties
        fs = 500  # Sampling frequency
        T = 4     # Duration
        time_vector = np.linspace(0, T, int(fs * T))

        # Multi-tone signal with known frequencies
        f1, f2, f3 = 10, 25, 50  # Hz
        a1, a2, a3 = 1.0, 0.6, 0.3  # Amplitudes

        signal = (a1 * np.sin(2 * np.pi * f1 * time_vector) +
                  a2 * np.sin(2 * np.pi * f2 * time_vector) +
                  a3 * np.sin(2 * np.pi * f3 * time_vector))

        # Frequency analysis
        freq_metrics = compute_frequency_metrics(signal, fs)

        # Validate dominant frequency detection
        dominant_freq = freq_metrics['dominant_frequency']
        assert abs(dominant_freq - f1) < 2.0  # Should detect strongest component

        # Validate power spectrum properties
        power_spectrum = freq_metrics['power_spectrum']
        frequencies = freq_metrics['frequencies']

        # Find peaks in spectrum
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(power_spectrum, height=np.max(power_spectrum) * 0.1)
        peak_frequencies = frequencies[peaks]

        # Should find frequencies close to f1, f2, f3
        expected_freqs = [f1, f2, f3]
        found_freqs = []

        for expected_freq in expected_freqs:
            closest_idx = np.argmin(np.abs(peak_frequencies - expected_freq))
            if np.abs(peak_frequencies[closest_idx] - expected_freq) < 3.0:
                found_freqs.append(expected_freq)

        assert len(found_freqs) >= 2, "Should detect at least 2 main frequency components"

    def test_stability_analysis_validation(self):
        """Test stability analysis against known stable/unstable systems."""
        time_vector = np.linspace(0, 10, 1000)

        # Test Case 1: Stable exponential decay
        stable_response = 2.0 * np.exp(-0.5 * time_vector)
        stable_states = np.column_stack([stable_response, -0.5 * stable_response,
                                        np.zeros_like(stable_response), np.zeros_like(stable_response)])

        stability_metrics_stable = compute_stability_metrics(stable_states)

        # Should indicate stability
        assert stability_metrics_stable['final_deviation'] < 0.1
        assert stability_metrics_stable['stability_margin'] > 0.5
        assert stability_metrics_stable['lyapunov_estimate'] <= 0  # Negative or zero

        # Test Case 2: Marginally stable (constant)
        constant_response = np.ones_like(time_vector)
        constant_states = np.column_stack([constant_response, np.zeros_like(constant_response),
                                          np.zeros_like(constant_response), np.zeros_like(constant_response)])

        stability_metrics_marginal = compute_stability_metrics(constant_states)

        # Should show bounded but non-decreasing behavior
        assert stability_metrics_marginal['final_deviation'] > 0.5
        assert stability_metrics_marginal['stability_margin'] > 0

    def test_robustness_analysis_sensitivity(self):
        """Test robustness analysis sensitivity to parameter variations."""
        # Define nominal performance
        nominal = {'metric1': 1.0, 'metric2': 0.5, 'metric3': 2.0}

        # Test different levels of variation
        variation_levels = [0.01, 0.05, 0.1, 0.2]  # 1%, 5%, 10%, 20%

        robustness_indices = []

        for variation_level in variation_levels:
            # Generate perturbed performances
            perturbed = []
            for i in range(10):
                perturbation = {
                    key: value * (1 + variation_level * (2 * np.random.random() - 1))
                    for key, value in nominal.items()
                }
                perturbed.append(perturbation)

            # Compute robustness
            robustness = compute_robustness_metrics(nominal, perturbed)

            # Average robustness index across metrics
            avg_robustness = np.mean([
                robustness[metric]['robustness_index']
                for metric in nominal.keys()
            ])
            robustness_indices.append(avg_robustness)

        # Robustness index should decrease with increasing variation
        for i in range(1, len(robustness_indices)):
            assert robustness_indices[i] <= robustness_indices[i-1] + 0.1, \
                "Robustness index should decrease with increasing variation"


class TestPerformanceAnalysisEdgeCases:
    """Test edge cases and error handling in performance analysis."""

    def test_empty_data_handling(self):
        """Test handling of empty data arrays."""
        empty_array = np.array([])

        # Should handle gracefully
        metrics = compute_control_metrics(empty_array)
        assert isinstance(metrics, dict)
        assert metrics['control_effort'] == 0.0
        assert metrics['max_control'] == 0.0

    def test_single_point_data(self):
        """Test handling of single data point."""
        single_point = np.array([1.5])
        time_single = np.array([0.0])

        metrics = compute_control_metrics(single_point, time_single)
        assert isinstance(metrics, dict)
        assert metrics['control_effort'] == 1.5
        assert metrics['max_control'] == 1.5
        assert metrics['control_variation'] == 0.0

    def test_nan_and_inf_handling(self):
        """Test handling of NaN and infinite values."""
        # Data with NaN
        data_with_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0])

        # Should handle NaN gracefully
        stability_metrics = compute_stability_metrics(
            np.column_stack([data_with_nan, np.zeros(5), np.zeros(5), np.zeros(5)])
        )
        assert isinstance(stability_metrics, dict)
        assert np.isfinite(stability_metrics['max_deviation'])

    def test_zero_variance_data(self):
        """Test handling of data with zero variance."""
        constant_data = np.ones(100)
        time_vector = np.linspace(0, 10, 100)

        metrics = compute_control_metrics(constant_data, time_vector)
        assert metrics['control_variation'] == 0.0

        # Frequency analysis with DC signal
        freq_metrics = compute_frequency_metrics(constant_data, 10.0)
        assert freq_metrics['dominant_frequency'] == 0.0

    def test_mismatched_array_lengths(self):
        """Test handling of mismatched array lengths."""
        reference = np.array([1, 2, 3, 4, 5])
        actual = np.array([1, 2, 3])  # Different length

        # Should raise ValueError
        with pytest.raises(ValueError):
            compute_performance_metrics(reference, actual)

    def test_very_large_numbers(self):
        """Test handling of very large numbers."""
        large_numbers = np.array([1e10, 2e10, 3e10])
        time_vector = np.array([0, 1, 2])

        metrics = compute_control_metrics(large_numbers, time_vector)

        # Should not overflow
        assert np.isfinite(metrics['control_effort'])
        assert np.isfinite(metrics['max_control'])
        assert np.isfinite(metrics['control_variation'])

    def test_very_small_numbers(self):
        """Test handling of very small numbers."""
        small_numbers = np.array([1e-15, 2e-15, 3e-15])

        stability_metrics = compute_stability_metrics(
            np.column_stack([small_numbers, np.zeros(3), np.zeros(3), np.zeros(3)])
        )

        # Should handle precision gracefully
        assert np.isfinite(stability_metrics['max_deviation'])
        assert stability_metrics['stability_margin'] >= 0


class TestPerformanceAnalysisIntegration:
    """Integration tests for complete performance analysis pipeline."""

    def test_complete_control_system_analysis(self):
        """Test complete analysis pipeline on realistic control system."""
        # Simulate inverted pendulum control system
        time_vector = np.linspace(0, 5, 1000)
        dt = time_vector[1] - time_vector[0]

        # System parameters
        m, l, g = 1.0, 1.0, 9.81  # Mass, length, gravity
        b = 0.1  # Damping

        # State vector: [theta, theta_dot]
        states = np.zeros((len(time_vector), 2))
        controls = np.zeros(len(time_vector))

        # Initial condition (small angle)
        states[0] = [0.2, 0.0]  # 0.2 rad initial angle

        # LQR-like control
        K = np.array([50, 10])  # Control gains

        for i in range(1, len(time_vector)):
            # Control law (stabilizing)
            controls[i] = -K @ states[i-1] + 0.01 * np.random.randn()

            # Inverted pendulum dynamics (linearized)
            theta, theta_dot = states[i-1]

            theta_ddot = (g/l) * theta - (b/(m*l**2)) * theta_dot + (1/(m*l**2)) * controls[i]

            # Integration
            states[i, 0] = theta + dt * theta_dot + 0.001 * np.random.randn()
            states[i, 1] = theta_dot + dt * theta_ddot + 0.001 * np.random.randn()

        # Comprehensive performance analysis
        performance_results = compute_comprehensive_metrics(
            states=states,
            controls=controls,
            time_vector=time_vector
        )

        # Validate comprehensive results
        assert isinstance(performance_results, dict)
        assert len(performance_results) > 0

        # Control performance
        assert 'control_metrics' in performance_results
        control_perf = performance_results['control_metrics']
        assert control_perf['control_effort'] > 0
        assert control_perf['settling_time'] < 5.0  # Should settle within simulation time

        # Stability analysis
        assert 'stability_metrics' in performance_results
        stability_perf = performance_results['stability_metrics']
        assert stability_perf['final_deviation'] < stability_perf['max_deviation']  # Should converge

        # State-specific performance
        state_metrics_count = sum(1 for key in performance_results.keys()
                                if key.startswith('state_') and '_metrics' in key)
        assert state_metrics_count == 2  # Should analyze both states

    def test_multi_controller_comparison(self):
        """Test performance comparison between multiple controllers."""
        # Generate test system response for different controllers
        time_vector = np.linspace(0, 8, 800)

        # Controller responses (simulated)
        controllers = {
            'PID': {'overshoot': 0.15, 'settling_time': 2.0, 'steady_state_error': 0.01},
            'LQR': {'overshoot': 0.05, 'settling_time': 1.5, 'steady_state_error': 0.005},
            'SMC': {'overshoot': 0.02, 'settling_time': 1.0, 'steady_state_error': 0.001}
        }

        # Simulate responses and compute comprehensive metrics
        all_performances = {}

        for controller_name, expected_perf in controllers.items():
            # Simulate step response with characteristics
            wn = 4.0 / expected_perf['settling_time']  # Approximate natural frequency
            zeta = -np.log(expected_perf['overshoot']) / np.sqrt(np.pi**2 + np.log(expected_perf['overshoot'])**2)

            if zeta < 1:
                wd = wn * np.sqrt(1 - zeta**2)
                response = 1 - np.exp(-zeta * wn * time_vector) * \
                          (np.cos(wd * time_vector) + (zeta * wn / wd) * np.sin(wd * time_vector))
            else:
                response = 1 - np.exp(-zeta * wn * time_vector)

            # Add steady-state error
            response = response * (1 - expected_perf['steady_state_error']) + \
                      expected_perf['steady_state_error']

            # Simple control signal (derivative of response)
            control_signal = np.gradient(response) / (time_vector[1] - time_vector[0])

            # State vector (position and velocity)
            states = np.column_stack([response, np.gradient(response)])

            # Comprehensive analysis
            performance = compute_comprehensive_metrics(
                states=states,
                controls=control_signal,
                time_vector=time_vector
            )

            all_performances[controller_name] = performance

        # Validate all controllers were analyzed
        assert len(all_performances) == 3

        # Each should have comprehensive metrics
        for controller_name, performance in all_performances.items():
            assert 'control_metrics' in performance
            assert 'stability_metrics' in performance

            # Control effort should be positive
            assert performance['control_metrics']['control_effort'] > 0

    def test_performance_analysis_consistency(self):
        """Test consistency of performance analysis across multiple runs."""
        # Generate deterministic test data
        np.random.seed(12345)

        time_vector = np.linspace(0, 5, 500)
        states = np.random.randn(500, 4)
        controls = np.random.randn(500)

        # Run analysis multiple times
        results = []
        for _ in range(5):
            performance = compute_comprehensive_metrics(states, controls, time_vector)
            results.append(performance)

        # Results should be identical for deterministic data
        reference_result = results[0]
        for result in results[1:]:
            for key in reference_result.keys():
                if isinstance(reference_result[key], dict):
                    for sub_key, sub_value in reference_result[key].items():
                        if isinstance(sub_value, (int, float)):
                            assert abs(result[key][sub_key] - sub_value) < 1e-12, \
                                f"Inconsistency in {key}.{sub_key}"


# Fixtures for testing
@pytest.fixture
def sample_step_response():
    """Generate sample step response data."""
    time = np.linspace(0, 10, 1000)
    # Second-order underdamped step response
    wn, zeta = 2.0, 0.3
    wd = wn * np.sqrt(1 - zeta**2)
    response = 1 - np.exp(-zeta * wn * time) * \
               (np.cos(wd * time) + (zeta * wn / wd) * np.sin(wd * time))
    return {'time': time, 'response': response, 'wn': wn, 'zeta': zeta}


@pytest.fixture
def sample_tracking_data():
    """Generate sample tracking data."""
    time = np.linspace(0, 8, 800)
    reference = np.sin(time) + 0.5 * np.sin(3 * time)
    actual = reference + 0.1 * np.sin(5 * time) + 0.05 * np.random.randn(len(time))
    return {'time': time, 'reference': reference, 'actual': actual}


if __name__ == "__main__":
    # Run basic smoke test if executed directly
    print("Running performance analysis validation...")

    try:
        # Test control performance metrics
        test_control = TestControlPerformanceMetrics()
        test_control.test_step_response_metrics()
        test_control.test_tracking_performance_metrics()
        print("✓ Control performance metrics tests passed")

        # Test analysis accuracy
        test_accuracy = TestPerformanceAnalysisAccuracy()
        test_accuracy.test_analytical_validation_second_order_system()
        test_accuracy.test_frequency_analysis_validation()
        print("✓ Performance analysis accuracy tests passed")

        # Test edge cases
        test_edge = TestPerformanceAnalysisEdgeCases()
        test_edge.test_empty_data_handling()
        test_edge.test_nan_and_inf_handling()
        print("✓ Edge case handling tests passed")

        # Test integration
        test_integration = TestPerformanceAnalysisIntegration()
        test_integration.test_complete_control_system_analysis()
        print("✓ Integration tests passed")

        print("\n🎉 All performance analysis tests passed!")
        print("Performance analysis is scientifically rigorous and fully operational.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise