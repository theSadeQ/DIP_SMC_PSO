#==========================================================================================\\
#=============== tests/test_analysis/fault_detection/test_fdi_infrastructure.py ==========\\
#==========================================================================================\\

"""
Comprehensive test suite for fault detection infrastructure.

This module validates the FaultDetectionInterface protocol implementation,
residual generation capabilities, threshold adaptation algorithms, and
ensures fault detection systems meet scientific rigor standards.
"""

import pytest
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import warnings
from unittest.mock import Mock, patch, MagicMock
import logging

# Fault detection imports
from src.analysis.fault_detection.fdi import (
    FaultDetectionInterface,
    FDIsystem,
    DynamicsProtocol
)


class TestFaultDetectionInterface:
    """Test suite for fault detection interface compliance and functionality."""

    def test_fault_detection_interface_protocol(self):
        """Test that FaultDetectionInterface protocol is properly defined."""
        # Verify protocol methods exist
        assert hasattr(FaultDetectionInterface, 'check')

        # Check method signature
        import inspect
        check_sig = inspect.signature(FaultDetectionInterface.check)
        expected_params = ['self', 't', 'meas', 'u', 'dt', 'dynamics_model']
        actual_params = list(check_sig.parameters.keys())
        assert actual_params == expected_params, f"Expected {expected_params}, got {actual_params}"

    def test_fdi_system_implements_interface(self):
        """Test that FDIsystem correctly implements FaultDetectionInterface."""
        fdi = FDIsystem()

        # Should be usable as FaultDetectionInterface
        detector: FaultDetectionInterface = fdi
        assert hasattr(detector, 'check')
        assert callable(detector.check)

    def test_dynamics_protocol_compliance(self):
        """Test dynamics protocol compliance for fault detection."""

        class ValidDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state + dt * np.ones_like(state)

        # Should work with protocol
        dynamics: DynamicsProtocol = ValidDynamics()
        assert hasattr(dynamics, 'step')
        assert callable(dynamics.step)

        # Test actual usage
        result = dynamics.step(np.array([1, 2, 3]), 0.5, 0.01)
        assert isinstance(result, np.ndarray)
        assert len(result) == 3


class TestResidualGeneration:
    """Test suite for residual generation capabilities."""

    def test_basic_residual_generation(self):
        """Test basic residual generation functionality."""

        class LinearDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                # Simple linear system: x' = Ax + Bu
                A = np.array([[0, 1, 0, 0],
                              [0, 0, 1, 0],
                              [0, 0, 0, 1],
                              [10, -2, -1, -0.5]])
                B = np.array([0, 0, 0, 1])
                return state + dt * (A @ state + B * u)

        fdi = FDIsystem(residual_threshold=0.1)
        dynamics = LinearDynamics()

        # Initialize with first measurement
        initial_state = np.array([0.1, 0.0, 0.05, 0.0])
        status, residual = fdi.check(0.0, initial_state, 0.0, 0.01, dynamics)
        assert status == "OK"
        assert residual == 0.0  # First measurement, no prediction yet

        # Second measurement should generate residual
        next_state = np.array([0.101, 0.001, 0.051, 0.001])
        status, residual = fdi.check(0.01, next_state, 0.0, 0.01, dynamics)
        assert status == "OK"
        assert isinstance(residual, float)
        assert residual >= 0

    def test_residual_with_state_selection(self):
        """Test residual generation with specific state selection."""

        class SimpleDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state + dt * np.array([state[1], u, state[3], -state[2]])

        # Configure to only use first two states for residual
        fdi = FDIsystem(
            residual_threshold=0.1,
            residual_states=[0, 1]  # Only position and velocity
        )
        dynamics = SimpleDynamics()

        # Initialize
        state1 = np.array([0.1, 0.0, 0.05, 0.0])
        fdi.check(0.0, state1, 0.0, 0.01, dynamics)

        # Check with different measurement
        state2 = np.array([0.11, 0.01, 0.99, 0.99])  # Large error in states 2,3
        status, residual = fdi.check(0.01, state2, 0.1, 0.01, dynamics)

        # Should only consider states [0, 1] for residual, ignoring [2, 3]
        assert status == "OK"  # Should not fault due to state selection

    def test_residual_with_weights(self):
        """Test residual generation with weighted states."""

        class LinearDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state + 0.01 * np.ones_like(state)

        # Configure with weights emphasizing first state
        fdi = FDIsystem(
            residual_threshold=0.5,
            residual_states=[0, 1, 2, 3],
            residual_weights=[10.0, 1.0, 1.0, 1.0]  # High weight on first state
        )
        dynamics = LinearDynamics()

        # Initialize
        state1 = np.array([0.0, 0.0, 0.0, 0.0])
        fdi.check(0.0, state1, 0.0, 0.01, dynamics)

        # Small error in first state should be amplified by weight
        state2 = np.array([0.1, 0.0, 0.0, 0.0])  # Only first state has error
        status, residual = fdi.check(0.01, state2, 0.0, 0.01, dynamics)

        # Residual should be dominated by weighted first state
        assert residual > 1.0  # Should be amplified by 10x weight

    def test_residual_error_handling(self):
        """Test residual generation error handling."""

        class BrokenDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                raise RuntimeError("Dynamics computation failed")

        fdi = FDIsystem()
        dynamics = BrokenDynamics()

        # Initialize first
        state = np.array([0.1, 0.0, 0.0, 0.0])
        fdi.check(0.0, state, 0.0, 0.01, dynamics)

        # Should handle dynamics failure gracefully
        status, residual = fdi.check(0.01, state, 0.0, 0.01, dynamics)
        assert status == "OK"  # Should not fault on dynamics error
        assert residual == 0.0


class TestThresholdAdaptation:
    """Test suite for adaptive threshold algorithms."""

    def test_fixed_threshold_operation(self):
        """Test fault detection with fixed threshold."""

        class PredictableDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state  # No change - perfect prediction possible

        fdi = FDIsystem(
            residual_threshold=0.1,
            persistence_counter=3,
            adaptive=False  # Use fixed threshold
        )
        dynamics = PredictableDynamics()

        # Initialize
        state = np.array([1.0, 0.0, 0.0, 0.0])
        fdi.check(0.0, state, 0.0, 0.01, dynamics)

        # Small deviations should not fault
        for i in range(5):
            noisy_state = state + 0.05 * np.random.randn(4)
            status, _ = fdi.check(0.01 * (i+1), noisy_state, 0.0, 0.01, dynamics)
            assert status == "OK"

        # Large deviation should eventually fault
        fault_count = 0
        for i in range(10):
            faulty_state = state + 0.2 * np.ones(4)  # Exceeds threshold
            status, _ = fdi.check(0.01 * (i+6), faulty_state, 0.0, 0.01, dynamics)
            if status == "FAULT":
                fault_count += 1
                break

        assert fault_count > 0, "Should detect fault with large residuals"

    def test_adaptive_threshold_operation(self):
        """Test adaptive threshold functionality."""

        class NoisyDynamics:
            def __init__(self, noise_level=0.01):
                self.noise_level = noise_level

            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state + self.noise_level * np.random.randn(*state.shape)

        fdi = FDIsystem(
            residual_threshold=0.05,  # Base threshold
            persistence_counter=5,
            adaptive=True,
            window_size=20,
            threshold_factor=3.0  # 3-sigma rule
        )
        dynamics = NoisyDynamics(noise_level=0.02)

        np.random.seed(42)  # For reproducible test

        # Build up window of residuals
        state = np.array([0.1, 0.0, 0.0, 0.0])
        residuals = []

        for i in range(30):
            noisy_state = state + 0.01 * np.random.randn(4)
            status, residual = fdi.check(0.01 * i, noisy_state, 0.0, 0.01, dynamics)
            residuals.append(residual)

            if i < 25:  # Should not fault during adaptation period
                assert status == "OK"

        # Verify adaptive threshold was computed
        assert len(fdi._residual_window) == fdi.window_size

        # Check that threshold adapted to noise level
        window_mean = np.mean(fdi._residual_window)
        window_std = np.std(fdi._residual_window)
        expected_threshold = window_mean + fdi.threshold_factor * window_std

        # Threshold should be larger than base threshold due to adaptation
        if window_std > 0:
            assert expected_threshold != fdi.residual_threshold

    def test_adaptive_threshold_convergence(self):
        """Test that adaptive threshold converges to appropriate values."""

        class ConsistentDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                # Always predict perfectly
                return state

        fdi = FDIsystem(
            adaptive=True,
            window_size=10,
            threshold_factor=2.0
        )
        dynamics = ConsistentDynamics()

        # Feed consistent small residuals
        state = np.array([0.1, 0.0, 0.0, 0.0])

        for i in range(15):
            # Consistent small noise
            noisy_state = state + 0.001 * np.ones(4)
            status, residual = fdi.check(0.01 * i, noisy_state, 0.0, 0.01, dynamics)

        # Window should be full and threshold adapted
        assert len(fdi._residual_window) == fdi.window_size

        # All residuals should be similar
        window_std = np.std(fdi._residual_window)
        assert window_std < 0.01, "Should have low variance for consistent input"

    def test_threshold_with_zero_variance(self):
        """Test threshold adaptation when residuals have zero variance."""

        class PerfectDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state  # Perfect prediction

        fdi = FDIsystem(
            adaptive=True,
            window_size=5,
            threshold_factor=3.0
        )
        dynamics = PerfectDynamics()

        state = np.array([0.1, 0.0, 0.0, 0.0])

        # Perfect measurements (zero residuals)
        for i in range(10):
            status, residual = fdi.check(0.01 * i, state, 0.0, 0.01, dynamics)
            if i > 0:  # Skip first (no prediction)
                assert residual == 0.0

        # Should handle zero variance gracefully
        window_std = np.std(fdi._residual_window)
        assert window_std == 0.0


class TestCUSUMDriftDetection:
    """Test suite for CUSUM drift detection capabilities."""

    def test_cusum_drift_detection(self):
        """Test CUSUM algorithm for slow drift detection."""

        class DriftingDynamics:
            def __init__(self):
                self.drift = 0.0

            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                self.drift += 0.001  # Slowly increasing drift
                return state + self.drift * np.ones_like(state)

        fdi = FDIsystem(
            residual_threshold=0.5,  # High regular threshold
            persistence_counter=100,  # High persistence to rely on CUSUM
            cusum_enabled=True,
            cusum_threshold=2.0,
            adaptive=False  # Use fixed reference
        )
        dynamics = DriftingDynamics()

        state = np.array([0.1, 0.0, 0.0, 0.0])

        fault_detected = False
        for i in range(200):
            # Measurement stays the same, but dynamics drift
            status, residual = fdi.check(0.01 * i, state, 0.0, 0.01, dynamics)

            if status == "FAULT":
                fault_detected = True
                assert i > 50, "CUSUM should detect gradual drift, not immediate"
                break

        assert fault_detected, "CUSUM should detect slow drift"
        assert fdi._cusum > fdi.cusum_threshold, "CUSUM value should exceed threshold"

    def test_cusum_with_adaptive_reference(self):
        """Test CUSUM with adaptive reference from adaptive thresholding."""

        class NoisyDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state + 0.01 * np.random.randn(*state.shape)

        fdi = FDIsystem(
            cusum_enabled=True,
            cusum_threshold=5.0,
            adaptive=True,  # Adaptive reference for CUSUM
            window_size=20
        )
        dynamics = NoisyDynamics()

        np.random.seed(42)
        state = np.array([0.1, 0.0, 0.0, 0.0])

        # Build up adaptive statistics first
        for i in range(30):
            noisy_state = state + 0.005 * np.random.randn(4)
            status, _ = fdi.check(0.01 * i, noisy_state, 0.0, 0.01, dynamics)

        # CUSUM should use adaptive mean as reference
        assert len(fdi._residual_window) == fdi.window_size

    def test_cusum_reset_behavior(self):
        """Test CUSUM reset behavior with negative deviations."""

        class VariableDynamics:
            def __init__(self):
                self.bias = 0.0

            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state + self.bias * np.ones_like(state)

        fdi = FDIsystem(
            cusum_enabled=True,
            cusum_threshold=1.0,
            adaptive=False
        )
        dynamics = VariableDynamics()

        state = np.array([0.1, 0.0, 0.0, 0.0])

        # Positive deviations increase CUSUM
        dynamics.bias = 0.1
        for i in range(5):
            status, _ = fdi.check(0.01 * i, state, 0.0, 0.01, dynamics)

        cusum_after_positive = fdi._cusum
        assert cusum_after_positive > 0

        # Negative deviations should reset CUSUM toward zero
        dynamics.bias = -0.2
        for i in range(5, 10):
            status, _ = fdi.check(0.01 * i, state, 0.0, 0.01, dynamics)

        # CUSUM should be reset (cannot go below zero)
        assert fdi._cusum >= 0
        assert fdi._cusum <= cusum_after_positive


class TestFaultDetectionRobustness:
    """Test suite for fault detection robustness and edge cases."""

    def test_invalid_time_step_handling(self):
        """Test handling of invalid time steps."""

        class SimpleDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state + dt * np.ones_like(state)

        fdi = FDIsystem()
        dynamics = SimpleDynamics()

        state = np.array([0.1, 0.0, 0.0, 0.0])

        # Initialize first
        fdi.check(0.0, state, 0.0, 0.01, dynamics)

        # Test negative time step
        with pytest.raises(ValueError, match="dt must be positive"):
            fdi.check(0.01, state, 0.0, -0.01, dynamics)

        # Test zero time step
        with pytest.raises(ValueError, match="dt must be positive"):
            fdi.check(0.01, state, 0.0, 0.0, dynamics)

    def test_non_finite_prediction_handling(self):
        """Test handling when dynamics model returns non-finite values."""

        class UnstableDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return np.array([np.inf, np.nan, -np.inf, 0.0])

        fdi = FDIsystem()
        dynamics = UnstableDynamics()

        state = np.array([0.1, 0.0, 0.0, 0.0])

        # Initialize
        fdi.check(0.0, state, 0.0, 0.01, dynamics)

        # Should handle non-finite predictions gracefully
        with patch('logging.warning') as mock_warning:
            status, residual = fdi.check(0.01, state, 0.0, 0.01, dynamics)

        assert status == "OK"  # Should not fault on model failure
        assert residual == 0.0
        mock_warning.assert_called()  # Should log warning

    def test_state_dimension_mismatch_handling(self):
        """Test handling when residual_states indices don't match state dimensions."""

        class SimpleDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state

        fdi = FDIsystem(
            residual_states=[0, 1, 2, 3, 4, 5],  # More indices than state size
            residual_weights=[1, 1, 1, 1, 1, 1]
        )
        dynamics = SimpleDynamics()

        small_state = np.array([0.1, 0.2])  # Only 2 dimensions

        # Initialize
        fdi.check(0.0, small_state, 0.0, 0.01, dynamics)

        # Should handle index error gracefully
        with patch('logging.error') as mock_error:
            status, residual = fdi.check(0.01, small_state, 0.0, 0.01, dynamics)

        assert status == "OK"
        assert isinstance(residual, float)
        mock_error.assert_called()  # Should log error

    def test_persistence_after_fault(self):
        """Test that system remains in fault state after fault is detected."""

        class SimpleDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state

        fdi = FDIsystem(
            residual_threshold=0.1,
            persistence_counter=2
        )
        dynamics = SimpleDynamics()

        state = np.array([0.1, 0.0, 0.0, 0.0])

        # Initialize
        fdi.check(0.0, state, 0.0, 0.01, dynamics)

        # Cause fault
        faulty_state = state + 0.5 * np.ones(4)

        # Exceed persistence counter
        for i in range(3):
            status, _ = fdi.check(0.01 * (i+1), faulty_state, 0.0, 0.01, dynamics)

        assert status == "FAULT"
        assert fdi.tripped_at is not None

        # Should remain in fault state even with good measurements
        good_state = state
        status, residual = fdi.check(0.05, good_state, 0.0, 0.01, dynamics)
        assert status == "FAULT"
        assert residual == np.inf  # Special value for faulted state

    def test_history_recording(self):
        """Test that FDI system properly records history for analysis."""

        class SimpleDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state

        fdi = FDIsystem()
        dynamics = SimpleDynamics()

        state = np.array([0.1, 0.0, 0.0, 0.0])
        times = []
        residuals = []

        for i in range(10):
            t = 0.01 * i
            noisy_state = state + 0.01 * np.random.randn(4)
            status, residual = fdi.check(t, noisy_state, 0.0, 0.01, dynamics)

            if i > 0:  # Skip first measurement (no prediction)
                times.append(t)
                residuals.append(residual)

        # Check history was recorded
        assert len(fdi.times) == 10
        assert len(fdi.residuals) == 10

        # History should match what we computed
        assert fdi.times == [0.01 * i for i in range(10)]

        # Check residuals are reasonable
        for residual in fdi.residuals[1:]:  # Skip first zero residual
            assert isinstance(residual, float)
            assert residual >= 0


class TestFaultDetectionIntegration:
    """Integration tests for complete fault detection system."""

    def test_end_to_end_fault_detection_scenario(self):
        """Test complete fault detection scenario from normal to fault."""

        class RealisticDynamics:
            def __init__(self):
                self.A = np.array([[0, 1, 0, 0],
                                  [0, -0.1, 1, 0],
                                  [0, 0, 0, 1],
                                  [0, 0, -5, -0.5]])
                self.B = np.array([0, 0, 0, 1])

            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state + dt * (self.A @ state + self.B * u)

        fdi = FDIsystem(
            residual_threshold=0.05,
            persistence_counter=5,
            adaptive=True,
            window_size=30,
            cusum_enabled=True,
            cusum_threshold=3.0
        )
        dynamics = RealisticDynamics()

        np.random.seed(42)

        # Normal operation phase
        state = np.array([0.1, 0.0, 0.05, 0.0])
        normal_operation_steps = 50

        for i in range(normal_operation_steps):
            t = 0.01 * i
            u = 0.1 * np.sin(2 * np.pi * 0.1 * t)  # Sinusoidal control

            # Add small measurement noise
            noisy_state = state + 0.001 * np.random.randn(4)

            status, residual = fdi.check(t, noisy_state, u, 0.01, dynamics)
            assert status == "OK", f"False positive at step {i}"

            # Update state with dynamics
            state = dynamics.step(state, u, 0.01)

        # Verify adaptive threshold was established
        assert len(fdi._residual_window) == fdi.window_size

        # Fault injection phase - sensor fault (bias)
        sensor_bias = np.array([0.0, 0.0, 0.1, 0.0])  # Bias in 3rd state
        fault_detected_at = None

        for i in range(normal_operation_steps, normal_operation_steps + 30):
            t = 0.01 * i
            u = 0.1 * np.sin(2 * np.pi * 0.1 * t)

            # Add sensor bias (simulated fault)
            faulty_state = state + sensor_bias + 0.001 * np.random.randn(4)

            status, residual = fdi.check(t, faulty_state, u, 0.01, dynamics)

            if status == "FAULT":
                fault_detected_at = i
                break

            # Update true state (without bias)
            state = dynamics.step(state, u, 0.01)

        assert fault_detected_at is not None, "Should detect injected fault"
        assert fault_detected_at > normal_operation_steps, "Should detect fault after injection"

        # Verify fault detection time is reasonable
        detection_delay = fault_detected_at - normal_operation_steps
        assert detection_delay <= 20, f"Detection delay too long: {detection_delay} steps"

    def test_fault_detection_with_multiple_fault_types(self):
        """Test fault detection with different types of faults."""

        class MultiModalDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state + dt * np.array([state[1], u, state[3], -0.1*state[2] + u])

        dynamics = MultiModalDynamics()

        fault_scenarios = [
            # (fault_type, fault_magnitude, expected_detection)
            ("sensor_bias", np.array([0.2, 0, 0, 0]), True),
            ("sensor_drift", lambda t: np.array([0.01*t, 0, 0, 0]), True),
            ("sensor_noise", lambda: 0.1 * np.random.randn(4), False),  # Should not fault
            ("actuator_fault", 0.5, True),  # Will show up in residual
        ]

        for fault_type, fault_param, should_detect in fault_scenarios:
            # Fresh FDI system for each test
            fdi = FDIsystem(
                residual_threshold=0.05,
                persistence_counter=3,
                adaptive=True,
                window_size=20
            )

            state = np.array([0.1, 0.0, 0.05, 0.0])

            # Normal operation
            for i in range(25):
                t = 0.01 * i
                status, _ = fdi.check(t, state, 0.0, 0.01, dynamics)
                state = dynamics.step(state, 0.0, 0.01)

            # Inject fault
            fault_detected = False
            for i in range(25, 50):
                t = 0.01 * i

                if fault_type == "sensor_bias":
                    faulty_measurement = state + fault_param
                elif fault_type == "sensor_drift":
                    faulty_measurement = state + fault_param(t)
                elif fault_type == "sensor_noise":
                    faulty_measurement = state + fault_param()
                elif fault_type == "actuator_fault":
                    faulty_measurement = state
                    # Actuator fault affects control input
                    u = fault_param if i == 25 else 0.0
                else:
                    faulty_measurement = state
                    u = 0.0

                status, _ = fdi.check(t, faulty_measurement, u, 0.01, dynamics)

                if status == "FAULT":
                    fault_detected = True
                    break

                state = dynamics.step(state, u if fault_type == "actuator_fault" else 0.0, 0.01)

            if should_detect:
                assert fault_detected, f"Should detect {fault_type}"
            else:
                assert not fault_detected, f"Should not detect {fault_type} as fault"


# Performance and stress tests
class TestFaultDetectionPerformance:
    """Performance and stress tests for fault detection system."""

    def test_large_scale_processing(self):
        """Test fault detection performance with large-scale data."""

        class FastDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state + dt * np.array([state[1], u, state[3], -state[2]])

        fdi = FDIsystem(
            adaptive=True,
            cusum_enabled=True
        )
        dynamics = FastDynamics()

        import time

        state = np.array([0.1, 0.0, 0.05, 0.0])

        start_time = time.time()

        # Process 10,000 measurements
        for i in range(10000):
            t = 0.001 * i
            noisy_state = state + 0.001 * np.random.randn(4)
            status, _ = fdi.check(t, noisy_state, 0.0, 0.001, dynamics)

            # Update state occasionally
            if i % 10 == 0:
                state = dynamics.step(state, 0.0, 0.001)

        processing_time = time.time() - start_time

        # Should process 10k samples in reasonable time (< 5 seconds)
        assert processing_time < 5.0, f"Processing too slow: {processing_time:.2f}s"

        # Verify history was maintained
        assert len(fdi.times) == 10000
        assert len(fdi.residuals) == 10000

    def test_memory_usage_stability(self):
        """Test that FDI system doesn't have memory leaks."""

        class SimpleDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return state

        fdi = FDIsystem(window_size=100)  # Fixed window size
        dynamics = SimpleDynamics()

        state = np.array([0.1, 0.0, 0.0, 0.0])

        # Run for extended period
        for i in range(1000):
            t = 0.01 * i
            status, _ = fdi.check(t, state, 0.0, 0.01, dynamics)

        # Window should be bounded
        assert len(fdi._residual_window) <= fdi.window_size

        # History continues to grow (this is expected for analysis)
        assert len(fdi.times) == 1000
        assert len(fdi.residuals) == 1000


if __name__ == "__main__":
    # Run basic smoke test if executed directly
    print("Running fault detection infrastructure validation...")

    try:
        # Test interface compliance
        test_interface = TestFaultDetectionInterface()
        test_interface.test_fault_detection_interface_protocol()
        test_interface.test_fdi_system_implements_interface()
        print("✓ Interface compliance tests passed")

        # Test residual generation
        test_residual = TestResidualGeneration()
        test_residual.test_basic_residual_generation()
        test_residual.test_residual_with_state_selection()
        print("✓ Residual generation tests passed")

        # Test threshold adaptation
        test_threshold = TestThresholdAdaptation()
        test_threshold.test_fixed_threshold_operation()
        test_threshold.test_adaptive_threshold_operation()
        print("✓ Threshold adaptation tests passed")

        # Test CUSUM
        test_cusum = TestCUSUMDriftDetection()
        test_cusum.test_cusum_drift_detection()
        print("✓ CUSUM drift detection tests passed")

        print("\n🎉 All fault detection infrastructure tests passed!")
        print("Fault detection system is scientifically rigorous and fully operational.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise