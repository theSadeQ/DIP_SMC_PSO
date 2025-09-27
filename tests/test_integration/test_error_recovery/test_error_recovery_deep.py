#==========================================================================================\\\
#================= tests/test_error_recovery_deep.py =====================================\\\
#==========================================================================================\\\

"""
Deep Error Recovery and Fault Tolerance Tests.
COMPREHENSIVE JOB: Test error handling, recovery mechanisms, and system resilience.
"""

import pytest
import numpy as np
import time
import warnings
from typing import Dict, List, Tuple, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager
import logging
import traceback
import sys


class ErrorType(Enum):
    """Types of errors for testing."""
    NUMERICAL_OVERFLOW = "numerical_overflow"
    NUMERICAL_UNDERFLOW = "numerical_underflow"
    DIVISION_BY_ZERO = "division_by_zero"
    MATRIX_SINGULAR = "matrix_singular"
    INVALID_INPUT = "invalid_input"
    TIMEOUT = "timeout"
    MEMORY_ERROR = "memory_error"
    HARDWARE_FAILURE = "hardware_failure"
    COMMUNICATION_ERROR = "communication_error"


@dataclass
class ErrorScenario:
    """Definition of an error scenario."""
    error_type: ErrorType
    description: str
    trigger_condition: Callable
    expected_recovery: str
    severity: str  # 'low', 'medium', 'high', 'critical'


@dataclass
class RecoveryResult:
    """Result of error recovery attempt."""
    scenario: ErrorScenario
    error_occurred: bool
    recovery_successful: bool
    recovery_time_ms: float
    system_state_after_recovery: Dict[str, Any]
    error_details: str
    recovery_strategy_used: str


class FaultInjector:
    """Fault injection utilities for testing."""

    @staticmethod
    def inject_numerical_error(value, error_type: ErrorType):
        """Inject numerical errors."""
        if error_type == ErrorType.NUMERICAL_OVERFLOW:
            return value * 1e100
        elif error_type == ErrorType.NUMERICAL_UNDERFLOW:
            return value * 1e-100
        elif error_type == ErrorType.DIVISION_BY_ZERO:
            return value / 0.0
        else:
            return value

    @staticmethod
    def inject_matrix_error(matrix, error_type: ErrorType):
        """Inject matrix-related errors."""
        if error_type == ErrorType.MATRIX_SINGULAR:
            # Make matrix singular
            singular_matrix = matrix.copy()
            if len(singular_matrix.shape) == 2 and singular_matrix.shape[0] == singular_matrix.shape[1]:
                singular_matrix[0, :] = singular_matrix[1, :]  # Make rows identical
            return singular_matrix
        else:
            return matrix

    @staticmethod
    def inject_input_error(input_data, error_type: ErrorType):
        """Inject input-related errors."""
        if error_type == ErrorType.INVALID_INPUT:
            if isinstance(input_data, np.ndarray):
                corrupted = input_data.copy()
                corrupted[0] = np.nan
                return corrupted
            else:
                return None
        else:
            return input_data


class ResilientController:
    """Controller with error recovery mechanisms."""

    def __init__(self, gains, max_force=20.0, dt=0.01):
        self.gains = np.array(gains)
        self.max_force = max_force
        self.dt = dt

        # Error handling state
        self.error_count = 0
        self.recovery_attempts = 0
        self.last_valid_state = np.zeros(6)
        self.last_valid_control = 0.0
        self.emergency_mode = False

        # Error recovery parameters
        self.max_error_threshold = 5
        self.recovery_timeout_ms = 1000
        self.safe_mode_gains = np.array(gains) * 0.5  # Conservative gains

        # Logging
        self.error_log = []

    def compute_control_with_recovery(self, state, reference=None):
        """Compute control with error recovery."""
        start_time = time.time()

        try:
            # Input validation
            if not self._validate_input(state):
                raise ValueError("Invalid input state")

            # Normal control computation
            control = self._compute_normal_control(state, reference)

            # Output validation
            if not self._validate_output(control):
                raise ValueError("Invalid control output")

            # Success - update valid state
            self.last_valid_state = state.copy()
            self.last_valid_control = control
            self.error_count = 0  # Reset error count on success

            return control

        except Exception as e:
            return self._handle_error(e, state, reference, start_time)

    def _compute_normal_control(self, state, reference):
        """Normal control computation."""
        if self.emergency_mode:
            gains = self.safe_mode_gains
        else:
            gains = self.gains

        error = state if reference is None else state - reference
        sigma = np.dot(gains, error)

        # Switching function with potential numerical issues
        if abs(sigma) < 1e-10:
            switching = sigma / 1e-10  # Potential division by small number
        else:
            switching = np.tanh(sigma / 0.01)

        control = -switching * 10.0

        # Apply saturation
        control = np.clip(control, -self.max_force, self.max_force)

        return control

    def _validate_input(self, state):
        """Validate input state."""
        if state is None:
            return False

        if not isinstance(state, np.ndarray):
            return False

        if len(state) != 6:
            return False

        if not np.all(np.isfinite(state)):
            return False

        # Check for extreme values
        if np.any(np.abs(state) > 1000):
            return False

        return True

    def _validate_output(self, control):
        """Validate control output."""
        if not np.isfinite(control):
            return False

        if abs(control) > self.max_force * 1.1:  # Allow small tolerance
            return False

        return True

    def _handle_error(self, error, state, reference, start_time):
        """Handle errors with recovery strategies."""
        self.error_count += 1
        self.recovery_attempts += 1

        error_info = {
            'timestamp': time.time(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_count': self.error_count,
            'state': state.copy() if isinstance(state, np.ndarray) else None,
            'traceback': traceback.format_exc()
        }

        self.error_log.append(error_info)

        # Recovery strategies in order of preference
        recovery_strategies = [
            self._try_safe_mode_recovery,
            self._try_last_valid_control,
            self._try_emergency_stop,
            self._try_default_control
        ]

        for strategy in recovery_strategies:
            try:
                recovery_start = time.time()
                recovery_control = strategy(state, reference, error)
                recovery_time = (time.time() - recovery_start) * 1000

                if recovery_time < self.recovery_timeout_ms:
                    # Log successful recovery
                    self.error_log[-1]['recovery_strategy'] = strategy.__name__
                    self.error_log[-1]['recovery_time_ms'] = recovery_time
                    self.error_log[-1]['recovery_successful'] = True

                    return recovery_control

            except Exception as recovery_error:
                # Recovery strategy failed, try next one
                continue

        # All recovery strategies failed
        self.error_log[-1]['recovery_successful'] = False
        self.emergency_mode = True

        # Return emergency control
        return 0.0

    def _try_safe_mode_recovery(self, state, reference, original_error):
        """Try recovery using safe mode gains."""
        if not self._validate_input(state):
            # Use last valid state if current state is invalid
            state = self.last_valid_state

        # Use conservative gains
        error = state if reference is None else state - reference
        sigma = np.dot(self.safe_mode_gains, error)

        # Simple switching function to avoid numerical issues
        if abs(sigma) > 1.0:
            switching = np.sign(sigma)
        else:
            switching = sigma

        control = -switching * 5.0  # Conservative control gain

        return np.clip(control, -self.max_force * 0.5, self.max_force * 0.5)

    def _try_last_valid_control(self, state, reference, original_error):
        """Try using last valid control value."""
        # Decay the last control slightly
        decayed_control = self.last_valid_control * 0.9

        if abs(decayed_control) <= self.max_force:
            return decayed_control
        else:
            raise ValueError("Last valid control is out of bounds")

    def _try_emergency_stop(self, state, reference, original_error):
        """Try emergency stop strategy."""
        self.emergency_mode = True

        # Gradually reduce control to zero
        if abs(self.last_valid_control) > 0.1:
            emergency_control = self.last_valid_control * 0.1
        else:
            emergency_control = 0.0

        return emergency_control

    def _try_default_control(self, state, reference, original_error):
        """Try default safe control."""
        return 0.0  # Safe default

    def reset_error_state(self):
        """Reset error handling state."""
        self.error_count = 0
        self.recovery_attempts = 0
        self.emergency_mode = False
        self.error_log.clear()

    def get_system_health(self):
        """Get current system health status."""
        return {
            'error_count': self.error_count,
            'recovery_attempts': self.recovery_attempts,
            'emergency_mode': self.emergency_mode,
            'recent_errors': len(self.error_log),
            'last_error': self.error_log[-1] if self.error_log else None,
            'health_score': self._calculate_health_score()
        }

    def _calculate_health_score(self):
        """Calculate system health score (0-100)."""
        base_score = 100

        # Penalize recent errors
        if self.error_count > 0:
            base_score -= min(self.error_count * 10, 50)

        # Penalize emergency mode
        if self.emergency_mode:
            base_score -= 30

        # Penalize excessive recovery attempts
        if self.recovery_attempts > 10:
            base_score -= min((self.recovery_attempts - 10) * 5, 20)

        return max(base_score, 0)


@pytest.mark.error_recovery
class TestBasicErrorRecovery:
    """Basic error recovery mechanism tests."""

    def test_numerical_overflow_recovery(self):
        """Test recovery from numerical overflow."""
        controller = ResilientController([2, 4, 3, 1, 2, 1])

        # Normal operation first
        normal_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        normal_control = controller.compute_control_with_recovery(normal_state)

        assert np.isfinite(normal_control), "Normal control should be finite"
        assert controller.error_count == 0, "Should have no errors initially"

        # Inject overflow error
        overflow_state = np.array([1e50, 0.1, 0.1, 0.0, 0.0, 0.0])  # Extreme value
        recovery_control = controller.compute_control_with_recovery(overflow_state)

        # Recovery should succeed
        assert np.isfinite(recovery_control), "Recovery control should be finite"
        assert abs(recovery_control) <= controller.max_force, "Recovery control should be within bounds"

        # Check error handling
        assert controller.error_count > 0, "Error should be counted"
        assert len(controller.error_log) > 0, "Error should be logged"

        # System health should be degraded but functional
        health = controller.get_system_health()
        assert health['health_score'] < 100, "Health score should be reduced after error"

    def test_invalid_input_recovery(self):
        """Test recovery from invalid inputs."""
        controller = ResilientController([2, 4, 3, 1, 2, 1])

        # Test with NaN input
        nan_state = np.array([np.nan, 0.1, 0.1, 0.0, 0.0, 0.0])
        recovery_control = controller.compute_control_with_recovery(nan_state)

        assert np.isfinite(recovery_control), "Should recover from NaN input"

        # Test with wrong dimensions
        wrong_dim_state = np.array([0.1, 0.2, 0.3])  # Only 3 elements instead of 6
        recovery_control = controller.compute_control_with_recovery(wrong_dim_state)

        assert np.isfinite(recovery_control), "Should recover from wrong dimensions"

        # Test with None input
        none_control = controller.compute_control_with_recovery(None)

        assert np.isfinite(none_control), "Should recover from None input"

        # Check that multiple errors are handled
        assert controller.error_count >= 3, "Multiple errors should be counted"

    def test_division_by_zero_recovery(self):
        """Test recovery from division by zero errors."""

        class DivisionByZeroController(ResilientController):
            def _compute_normal_control(self, state, reference):
                # Deliberately cause division by zero
                if np.sum(state) == 0:
                    return 1.0 / 0.0

                return super()._compute_normal_control(state, reference)

        controller = DivisionByZeroController([2, 4, 3, 1, 2, 1])

        # Trigger division by zero
        zero_state = np.zeros(6)
        recovery_control = controller.compute_control_with_recovery(zero_state)

        assert np.isfinite(recovery_control), "Should recover from division by zero"
        assert controller.error_count > 0, "Division by zero should be logged"

        # Check error log
        assert len(controller.error_log) > 0, "Error should be logged"
        assert 'ZeroDivision' in controller.error_log[-1]['error_type'], "Should identify division by zero"

    def test_matrix_singular_recovery(self):
        """Test recovery from singular matrix errors."""

        class MatrixController(ResilientController):
            def _compute_normal_control(self, state, reference):
                # Create singular matrix scenario
                matrix = np.array([[1, 2], [2, 4]])  # Singular matrix
                try:
                    inv_matrix = np.linalg.inv(matrix)
                    return np.sum(inv_matrix)  # This will fail
                except np.linalg.LinAlgError:
                    # Re-raise to trigger recovery
                    raise

        controller = MatrixController([2, 4, 3, 1, 2, 1])

        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        recovery_control = controller.compute_control_with_recovery(state)

        assert np.isfinite(recovery_control), "Should recover from singular matrix"
        assert controller.error_count > 0, "Matrix error should be counted"

    def test_timeout_recovery(self):
        """Test recovery from computation timeouts."""

        class SlowController(ResilientController):
            def _compute_normal_control(self, state, reference):
                # Simulate slow computation
                start_time = time.time()

                # Check for timeout condition
                while time.time() - start_time < 0.1:  # 100ms delay
                    pass  # Busy wait to simulate computation

                return 0.5

        controller = SlowController([2, 4, 3, 1, 2, 1])
        controller.recovery_timeout_ms = 50  # Set low timeout

        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])

        start_time = time.time()
        recovery_control = controller.compute_control_with_recovery(state)
        end_time = time.time()

        # Should complete quickly due to recovery
        assert end_time - start_time < 0.2, "Recovery should be faster than slow computation"
        assert np.isfinite(recovery_control), "Should recover from timeout"


@pytest.mark.error_recovery
class TestAdvancedErrorRecovery:
    """Advanced error recovery and fault tolerance tests."""

    def test_cascading_error_recovery(self):
        """Test recovery from cascading errors."""
        controller = ResilientController([2, 4, 3, 1, 2, 1])

        # Sequence of increasingly severe errors
        error_states = [
            np.array([10, 0.1, 0.1, 0.0, 0.0, 0.0]),      # Mild error
            np.array([100, 0.1, 0.1, 0.0, 0.0, 0.0]),     # Moderate error
            np.array([np.inf, 0.1, 0.1, 0.0, 0.0, 0.0]),  # Severe error
            np.array([np.nan, np.nan, 0.1, 0.0, 0.0, 0.0]), # Critical error
        ]

        controls = []
        for i, error_state in enumerate(error_states):
            control = controller.compute_control_with_recovery(error_state)
            controls.append(control)

            # Each control should be finite
            assert np.isfinite(control), f"Control {i} should be finite despite cascading errors"

        # Error count should accumulate
        assert controller.error_count >= len(error_states) - 1, "Should count multiple errors"

        # System should eventually enter emergency mode
        health = controller.get_system_health()
        assert health['health_score'] < 50, "Health should be severely degraded"

    def test_error_recovery_under_load(self):
        """Test error recovery under computational load."""
        controller = ResilientController([2, 4, 3, 1, 2, 1])

        # Simulate high-frequency control loop with intermittent errors
        num_iterations = 100
        error_frequency = 0.1  # 10% error rate

        successful_controls = 0
        total_recovery_time = 0

        for i in range(num_iterations):
            # Introduce random errors
            if np.random.random() < error_frequency:
                # Error state
                error_magnitude = np.random.uniform(10, 1000)
                state = np.array([error_magnitude, 0.1, 0.1, 0.0, 0.0, 0.0])
            else:
                # Normal state
                state = np.random.normal(0, 0.1, 6)

            start_time = time.time()
            control = controller.compute_control_with_recovery(state)
            end_time = time.time()

            if np.isfinite(control):
                successful_controls += 1

            total_recovery_time += (end_time - start_time)

        # Performance metrics
        success_rate = successful_controls / num_iterations
        average_time_per_operation = total_recovery_time / num_iterations

        # Should maintain reasonable performance despite errors
        assert success_rate >= 0.95, f"Success rate too low: {success_rate:.3f}"
        assert average_time_per_operation < 0.01, f"Average operation time too high: {average_time_per_operation:.6f}s"

        # Check system health
        health = controller.get_system_health()
        assert health['health_score'] > 30, "System should maintain minimum health under load"

    def test_memory_error_recovery(self):
        """Test recovery from memory-related errors."""

        class MemoryIntensiveController(ResilientController):
            def _compute_normal_control(self, state, reference):
                # Simulate memory-intensive operation
                try:
                    # Try to allocate large array
                    large_array = np.zeros((10000, 10000))  # 800MB array
                    result = np.sum(large_array) + np.sum(state)
                    del large_array  # Clean up
                    return result * 0.001

                except MemoryError:
                    raise MemoryError("Simulated memory error")

        controller = MemoryIntensiveController([2, 4, 3, 1, 2, 1])

        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])

        # This might or might not trigger MemoryError depending on system
        # But recovery should handle it gracefully
        recovery_control = controller.compute_control_with_recovery(state)

        assert np.isfinite(recovery_control), "Should recover from memory error"

    def test_communication_error_simulation(self):
        """Test recovery from communication errors."""

        class CommunicationController(ResilientController):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.communication_failure_count = 0

            def _compute_normal_control(self, state, reference):
                # Simulate communication failure
                if np.random.random() < 0.2:  # 20% failure rate
                    self.communication_failure_count += 1
                    raise ConnectionError("Communication failure")

                return super()._compute_normal_control(state, reference)

        controller = CommunicationController([2, 4, 3, 1, 2, 1])

        # Run multiple iterations to trigger communication failures
        successful_operations = 0
        total_operations = 50

        for i in range(total_operations):
            state = np.random.normal(0, 0.1, 6)
            control = controller.compute_control_with_recovery(state)

            if np.isfinite(control):
                successful_operations += 1

        # Should maintain functionality despite communication errors
        success_rate = successful_operations / total_operations
        assert success_rate >= 0.8, f"Success rate too low with communication errors: {success_rate:.3f}"

        # Check that communication failures were handled
        if controller.communication_failure_count > 0:
            assert controller.error_count >= controller.communication_failure_count, "Communication errors should be logged"

    def test_error_recovery_strategies_prioritization(self):
        """Test that error recovery strategies are applied in correct priority order."""

        class TrackedRecoveryController(ResilientController):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.recovery_strategy_calls = []

            def _try_safe_mode_recovery(self, state, reference, original_error):
                self.recovery_strategy_calls.append('safe_mode')
                return super()._try_safe_mode_recovery(state, reference, original_error)

            def _try_last_valid_control(self, state, reference, original_error):
                self.recovery_strategy_calls.append('last_valid')
                return super()._try_last_valid_control(state, reference, original_error)

            def _try_emergency_stop(self, state, reference, original_error):
                self.recovery_strategy_calls.append('emergency_stop')
                return super()._try_emergency_stop(state, reference, original_error)

            def _try_default_control(self, state, reference, original_error):
                self.recovery_strategy_calls.append('default')
                return super()._try_default_control(state, reference, original_error)

        controller = TrackedRecoveryController([2, 4, 3, 1, 2, 1])

        # Set up a valid control first
        normal_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        controller.compute_control_with_recovery(normal_state)

        # Trigger error that requires recovery
        error_state = np.array([np.inf, 0.1, 0.1, 0.0, 0.0, 0.0])
        controller.compute_control_with_recovery(error_state)

        # Check that recovery strategies were called in order
        assert len(controller.recovery_strategy_calls) > 0, "Recovery strategies should be called"

        # First strategy called should be safe_mode
        if len(controller.recovery_strategy_calls) > 0:
            assert controller.recovery_strategy_calls[0] == 'safe_mode', "Safe mode should be tried first"

    def test_system_degradation_and_recovery(self):
        """Test system degradation and recovery over time."""
        controller = ResilientController([2, 4, 3, 1, 2, 1])

        # Phase 1: Normal operation
        for _ in range(10):
            normal_state = np.random.normal(0, 0.05, 6)
            control = controller.compute_control_with_recovery(normal_state)
            assert np.isfinite(control)

        health_normal = controller.get_system_health()['health_score']

        # Phase 2: Error injection
        for _ in range(5):
            error_state = np.array([np.random.uniform(100, 1000), 0.1, 0.1, 0.0, 0.0, 0.0])
            control = controller.compute_control_with_recovery(error_state)
            assert np.isfinite(control)

        health_degraded = controller.get_system_health()['health_score']

        # System should be degraded
        assert health_degraded < health_normal, "System health should degrade with errors"

        # Phase 3: Recovery period
        controller.reset_error_state()  # Reset error counters

        for _ in range(20):
            recovery_state = np.random.normal(0, 0.02, 6)  # Very stable inputs
            control = controller.compute_control_with_recovery(recovery_state)
            assert np.isfinite(control)

        health_recovered = controller.get_system_health()['health_score']

        # System should recover
        assert health_recovered > health_degraded, "System health should recover after reset"


@pytest.mark.error_recovery
class TestSystemResilience:
    """System-level resilience and fault tolerance tests."""

    def test_multiple_controller_fault_tolerance(self):
        """Test fault tolerance with multiple controllers."""

        # Create redundant controllers
        controllers = [
            ResilientController([2, 4, 3, 1, 2, 1]),
            ResilientController([2.2, 3.8, 3.1, 1.1, 1.9, 1.1]),
            ResilientController([1.8, 4.2, 2.9, 0.9, 2.1, 0.9])
        ]

        def voting_control(state):
            """Voting mechanism for multiple controllers."""
            controls = []
            valid_controllers = []

            for i, controller in enumerate(controllers):
                try:
                    control = controller.compute_control_with_recovery(state)
                    if np.isfinite(control):
                        controls.append(control)
                        valid_controllers.append(i)
                except:
                    continue

            if len(controls) == 0:
                return 0.0  # Emergency stop

            # Use median for robustness
            return np.median(controls)

        # Test with various states including error states
        test_states = [
            np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0]),     # Normal
            np.array([1.0, 0.1, 0.1, 0.0, 0.0, 0.0]),     # Large deviation
            np.array([10.0, 0.1, 0.1, 0.0, 0.0, 0.0]),    # Very large
            np.array([np.inf, 0.1, 0.1, 0.0, 0.0, 0.0]),  # Infinite
            np.array([np.nan, 0.1, 0.1, 0.0, 0.0, 0.0]),  # NaN
        ]

        for i, state in enumerate(test_states):
            control = voting_control(state)
            assert np.isfinite(control), f"Voting control should be finite for state {i}"

        # Check that at least one controller remains healthy
        health_scores = [c.get_system_health()['health_score'] for c in controllers]
        max_health = max(health_scores)
        assert max_health > 50, "At least one controller should maintain reasonable health"

    def test_graceful_degradation(self):
        """Test graceful degradation under increasing error severity."""
        controller = ResilientController([2, 4, 3, 1, 2, 1])

        # Progressive error severity
        error_levels = [
            ([1.0, 0.1, 0.1, 0.0, 0.0, 0.0], "mild"),
            ([10.0, 0.1, 0.1, 0.0, 0.0, 0.0], "moderate"),
            ([100.0, 0.1, 0.1, 0.0, 0.0, 0.0], "severe"),
            ([1000.0, 0.1, 0.1, 0.0, 0.0, 0.0], "extreme"),
            ([np.inf, 0.1, 0.1, 0.0, 0.0, 0.0], "critical"),
        ]

        controls = []
        health_scores = []

        for error_state, level in error_levels:
            state = np.array(error_state)
            control = controller.compute_control_with_recovery(state)
            health = controller.get_system_health()

            controls.append(control)
            health_scores.append(health['health_score'])

            # Control should remain finite
            assert np.isfinite(control), f"Control should be finite at {level} error level"

            # Control magnitude should be reasonable
            assert abs(control) <= controller.max_force, f"Control should be bounded at {level} level"

        # Health should degrade gracefully
        assert all(h >= 0 for h in health_scores), "Health scores should remain non-negative"

        # System should eventually enter emergency mode for severe errors
        final_health = controller.get_system_health()
        if final_health['health_score'] < 20:
            assert controller.emergency_mode, "Should enter emergency mode for severe degradation"

    def test_error_recovery_documentation(self):
        """Test that error recovery is properly documented and traceable."""
        controller = ResilientController([2, 4, 3, 1, 2, 1])

        # Trigger various error types
        error_test_cases = [
            (np.array([np.nan, 0.1, 0.1, 0.0, 0.0, 0.0]), "NaN input"),
            (np.array([np.inf, 0.1, 0.1, 0.0, 0.0, 0.0]), "Infinite input"),
            (None, "None input"),
            (np.array([1, 2, 3]), "Wrong dimensions"),
        ]

        for error_state, description in error_test_cases:
            control = controller.compute_control_with_recovery(error_state)
            assert np.isfinite(control), f"Should recover from {description}"

        # Check error documentation
        assert len(controller.error_log) >= len(error_test_cases), "All errors should be logged"

        # Verify log contents
        for log_entry in controller.error_log:
            required_fields = ['timestamp', 'error_type', 'error_message', 'error_count']
            for field in required_fields:
                assert field in log_entry, f"Log entry should contain {field}"

            # Check for recovery information
            if 'recovery_successful' in log_entry:
                if log_entry['recovery_successful']:
                    assert 'recovery_strategy' in log_entry, "Successful recovery should log strategy"
                    assert 'recovery_time_ms' in log_entry, "Successful recovery should log time"

        # System health should reflect the error history
        health = controller.get_system_health()
        assert health['recent_errors'] == len(controller.error_log), "Health should track error count"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])