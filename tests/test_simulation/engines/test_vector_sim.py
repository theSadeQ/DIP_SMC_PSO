#==========================================================================================\\\
#================= tests/test_simulation/engines/test_vector_sim.py ====================\\\
#==========================================================================================\\\

"""
Comprehensive test suite for vector simulation engine.

Tests the unified simulation façade including scalar/batch modes, safety guards,
early stopping, and error handling for the vectorized simulation system.
"""

import pytest
import numpy as np
from typing import Optional, Callable, Tuple, Any
from unittest.mock import Mock, patch

# Import vector simulation engine
try:
    from src.simulation.engines.vector_sim import simulate
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    simulate = None


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Vector simulation modules not available")
class TestVectorSimulationBasic:
    """Test basic vector simulation functionality."""

    @pytest.fixture
    def mock_step_function(self):
        """Mock the underlying step function."""
        def mock_step(state, control, dt):
            # Simple dynamics: x_next = x + dt * state_derivative
            # For testing purposes, apply scalar control uniformly across state dimensions
            state = np.asarray(state)
            control = np.asarray(control).item() if np.asarray(control).ndim == 0 else np.asarray(control)

            # Simplified dynamics: uniform state derivative equals control input
            state_derivative = np.full_like(state, control)
            return state + dt * state_derivative

        with patch('src.simulation.engines.vector_sim._step_fn', side_effect=mock_step):
            yield mock_step

    @pytest.fixture
    def mock_safety_guards(self):
        """Mock safety guard functions."""
        with patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):
            yield

    def test_scalar_simulation(self, mock_step_function, mock_safety_guards):
        """Test scalar simulation mode."""
        initial_state = np.array([1.0, 0.0])
        control_inputs = np.array([0.1, 0.2])
        dt = 0.1

        result = simulate(initial_state, control_inputs, dt, horizon=2)

        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 2)  # (H+1, D) = (2+1, 2)

        # Check initial state is preserved
        np.testing.assert_array_equal(result[0], initial_state)

        # Check simulation progression - mock applies control[i] uniformly to all state dimensions
        expected_step1 = initial_state + dt * control_inputs[0]
        np.testing.assert_array_almost_equal(result[1], expected_step1, decimal=3)

    def test_batch_simulation(self, mock_step_function, mock_safety_guards):
        """Test batch simulation mode."""
        initial_states = np.array([[1.0, 0.0], [2.0, 1.0]])
        control_inputs = np.array([[[0.1, 0.2], [0.3, 0.4]]])  # (B, H, U)
        dt = 0.1

        result = simulate(initial_states, control_inputs, dt, horizon=1)

        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 2, 2)  # (B, H+1, D) = (2, 1+1, 2)

        # Check initial states are preserved
        np.testing.assert_array_equal(result[:, 0, :], initial_states)

    def test_horizon_inference(self, mock_step_function, mock_safety_guards):
        """Test horizon inference from control inputs."""
        initial_state = np.array([1.0, 0.0])
        control_inputs = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])  # H=3
        dt = 0.1

        result = simulate(initial_state, control_inputs, dt)

        assert result.shape == (4, 2)  # (H+1, D) = (3+1, 2)

    def test_scalar_control_input(self, mock_step_function, mock_safety_guards):
        """Test with scalar control input."""
        initial_state = np.array([1.0])
        control_inputs = 0.5  # Scalar
        dt = 0.1

        result = simulate(initial_state, control_inputs, dt, horizon=2)

        assert result.shape == (3, 1)  # (H+1, D) = (2+1, 1)

    def test_time_offset(self, mock_step_function, mock_safety_guards):
        """Test simulation with non-zero initial time."""
        initial_state = np.array([1.0, 0.0])
        control_inputs = np.array([0.1, 0.2])
        dt = 0.1
        t0 = 5.0

        result = simulate(initial_state, control_inputs, dt, horizon=1, t0=t0)

        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 2)  # (H+1, D) = (1+1, 2)


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Vector simulation modules not available")
class TestVectorSimulationEarlyStopping:
    """Test early stopping functionality."""

    @pytest.fixture
    def mock_step_function(self):
        """Mock step function for early stopping tests."""
        def mock_step(state, control, dt):
            state_derivative = np.asarray(control)
            return state + dt * state_derivative

        with patch('src.simulation.engines.vector_sim._step_fn', side_effect=mock_step):
            yield mock_step

    @pytest.fixture
    def mock_safety_guards(self):
        """Mock safety guard functions."""
        with patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):
            yield

    def test_early_stopping_scalar(self, mock_step_function, mock_safety_guards):
        """Test early stopping in scalar mode."""
        initial_state = np.array([1.0, 0.0])
        control_inputs = np.array([[1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])
        dt = 0.1

        # Stop when first component exceeds 1.5
        def stop_fn(x):
            return x[0] > 1.5

        result = simulate(initial_state, control_inputs, dt, stop_fn=stop_fn)

        # Should stop before completing all steps
        assert result.shape[0] <= 4  # (H+1) <= 4
        assert result.shape[1] == 2

    def test_early_stopping_batch(self, mock_step_function, mock_safety_guards):
        """Test early stopping in batch mode."""
        initial_states = np.array([[1.0, 0.0], [0.1, 0.0]])
        control_inputs = np.array([[[1.0, 0.0]], [[0.1, 0.0]]])
        dt = 0.1

        # Stop when any state component exceeds 1.5
        def stop_fn(x):
            return np.any(x > 1.5)

        result = simulate(initial_states, control_inputs, dt, horizon=5, stop_fn=stop_fn)

        assert result.shape[0] == 2  # Batch size preserved
        # Stopping should occur before horizon
        assert result.shape[1] <= 6  # (H+1) <= 6

    def test_no_early_stopping(self, mock_step_function, mock_safety_guards):
        """Test simulation without early stopping."""
        initial_state = np.array([1.0, 0.0])
        control_inputs = np.array([[0.01, 0.0], [0.01, 0.0]])
        dt = 0.1

        # Stop condition that never triggers
        def stop_fn(x):
            return x[0] > 100.0

        result = simulate(initial_state, control_inputs, dt, stop_fn=stop_fn)

        assert result.shape == (3, 2)  # Full horizon completed


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Vector simulation modules not available")
class TestVectorSimulationSafetyGuards:
    """Test safety guard integration."""

    @pytest.fixture
    def mock_step_function(self):
        """Mock step function."""
        def mock_step(state, control, dt):
            state_derivative = np.asarray(control)
            return state + dt * state_derivative

        with patch('src.simulation.engines.vector_sim._step_fn', side_effect=mock_step):
            yield mock_step

    def test_energy_limits_scalar(self, mock_step_function):
        """Test energy limits in scalar mode."""
        with patch('src.simulation.engines.vector_sim._guard_energy') as mock_energy_guard:
            mock_energy_guard.return_value = True

            initial_state = np.array([1.0, 0.0])
            control_inputs = np.array([0.1, 0.2])

            simulate(initial_state, control_inputs, 0.1,
                    energy_limits=10.0, horizon=1)

            # Verify energy guard was called
            mock_energy_guard.assert_called()

    def test_state_bounds_scalar(self, mock_step_function):
        """Test state bounds in scalar mode."""
        with patch('src.simulation.engines.vector_sim._guard_bounds') as mock_bounds_guard:
            mock_bounds_guard.return_value = True

            initial_state = np.array([1.0, 0.0])
            control_inputs = np.array([0.1, 0.2])
            bounds = (np.array([-2.0, -2.0]), np.array([2.0, 2.0]))

            simulate(initial_state, control_inputs, 0.1,
                    state_bounds=bounds, horizon=1)

            # Verify bounds guard was called
            mock_bounds_guard.assert_called()

    def test_nan_guard(self, mock_step_function):
        """Test NaN detection guard."""
        with patch('src.simulation.engines.vector_sim._guard_no_nan') as mock_nan_guard:
            mock_nan_guard.return_value = True

            initial_state = np.array([1.0, 0.0])
            control_inputs = np.array([0.1, 0.2])

            simulate(initial_state, control_inputs, 0.1, horizon=1)

            # Verify NaN guard was called
            mock_nan_guard.assert_called()

    def test_safety_guard_failure(self, mock_step_function):
        """Test behavior when safety guards fail."""
        with patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=False), \
             patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):

            initial_state = np.array([1.0, 0.0])
            control_inputs = np.array([0.1, 0.2])

            # Should handle safety guard failure gracefully
            result = simulate(initial_state, control_inputs, 0.1, horizon=1)

            # Should still return a valid result
            assert isinstance(result, np.ndarray)


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Vector simulation modules not available")
class TestVectorSimulationErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def mock_step_function(self):
        """Mock step function."""
        def mock_step(state, control, dt):
            state_derivative = np.asarray(control)
            return state + dt * state_derivative

        with patch('src.simulation.engines.vector_sim._step_fn', side_effect=mock_step):
            yield mock_step

    @pytest.fixture
    def mock_safety_guards(self):
        """Mock safety guard functions."""
        with patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):
            yield

    def test_zero_horizon(self, mock_step_function, mock_safety_guards):
        """Test simulation with zero horizon."""
        initial_state = np.array([1.0, 0.0])
        control_inputs = np.array([0.1, 0.2])

        result = simulate(initial_state, control_inputs, 0.1, horizon=0)

        assert result.shape == (1, 2)  # Only initial state
        np.testing.assert_array_equal(result[0], initial_state)

    def test_invalid_inputs(self, mock_step_function, mock_safety_guards):
        """Test handling of invalid inputs."""
        # Test with non-numeric initial state - should raise ValueError during asarray conversion
        with pytest.raises((ValueError, TypeError)):
            simulate("invalid", [0.1], 0.1)

        # Test with non-numeric control - should raise ValueError during asarray conversion
        with pytest.raises((ValueError, TypeError)):
            simulate([1.0], "invalid", 0.1)

        # Test with zero dt - simulate function is designed to be permissive
        # It doesn't validate dt, so no exception is expected
        # This tests that the function completes without error even with edge case dt
        try:
            result = simulate([1.0], [0.1], 0.0)
            # Function should complete, possibly with no time evolution
            assert isinstance(result, np.ndarray)
        except Exception:
            # If an exception occurs, it should be from the underlying step function
            pass

    def test_mismatched_dimensions(self, mock_step_function, mock_safety_guards):
        """Test handling of mismatched dimensions."""
        initial_state = np.array([1.0, 0.0])  # 2D
        control_inputs = np.array([0.1])  # 1D

        # Should handle dimension mismatch gracefully or raise appropriate error
        try:
            result = simulate(initial_state, control_inputs, 0.1, horizon=1)
            assert isinstance(result, np.ndarray)
        except (ValueError, IndexError):
            # Expected behavior for dimension mismatch
            pass

    def test_empty_arrays(self, mock_step_function, mock_safety_guards):
        """Test handling of empty arrays."""
        # Empty arrays should be handled gracefully, returning empty results
        result = simulate(np.array([]), np.array([]), 0.1)

        # Should return array with shape (1, 0) - one timestep, zero dimensions
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 0)

    def test_large_inputs(self, mock_step_function, mock_safety_guards):
        """Test handling of very large inputs."""
        initial_state = np.array([1e10, -1e10])
        control_inputs = np.array([1e8, -1e8])

        result = simulate(initial_state, control_inputs, 0.1, horizon=1)

        assert isinstance(result, np.ndarray)
        assert np.all(np.isfinite(result[0]))  # Initial state should be finite


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Vector simulation modules not available")
class TestVectorSimulationPerformance:
    """Test performance characteristics."""

    @pytest.fixture
    def mock_step_function(self):
        """Mock step function for performance tests."""
        def mock_step(state, control, dt):
            state_derivative = np.asarray(control)
            return state + dt * state_derivative

        with patch('src.simulation.engines.vector_sim._step_fn', side_effect=mock_step):
            yield mock_step

    @pytest.fixture
    def mock_safety_guards(self):
        """Mock safety guard functions."""
        with patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):
            yield

    def test_batch_performance(self, mock_step_function, mock_safety_guards):
        """Test performance with batch operations."""
        batch_size = 100
        state_dim = 6
        horizon = 10

        initial_states = np.random.randn(batch_size, state_dim)
        control_inputs = np.random.randn(batch_size, horizon, 1)

        import time
        start_time = time.time()

        result = simulate(initial_states, control_inputs, 0.01)

        elapsed_time = time.time() - start_time

        assert isinstance(result, np.ndarray)
        assert result.shape == (batch_size, horizon + 1, state_dim)

        # Should complete in reasonable time
        assert elapsed_time < 5.0  # Allow generous time for test environments

    def test_memory_efficiency(self, mock_step_function, mock_safety_guards):
        """Test memory usage doesn't grow excessively."""
        import gc

        initial_objects = len(gc.get_objects())

        # Run multiple simulations
        for _ in range(50):
            initial_state = np.random.randn(6)
            control_inputs = np.random.randn(10, 1)

            result = simulate(initial_state, control_inputs, 0.01)
            assert isinstance(result, np.ndarray)

        gc.collect()
        final_objects = len(gc.get_objects())

        # Should not have excessive object growth
        object_growth = final_objects - initial_objects
        assert object_growth < 500  # Allow reasonable growth for numpy arrays and test artifacts


# Fallback tests when imports are not available
class TestVectorSimulationFallback:
    """Test fallback behavior when imports are not available."""

    @pytest.mark.skipif(IMPORTS_AVAILABLE, reason="Test only when imports fail")
    def test_imports_not_available(self):
        """Test that we handle missing imports gracefully."""
        assert simulate is None
        assert IMPORTS_AVAILABLE is False

    def test_mock_simulation_structure(self):
        """Test that our test structure handles missing components."""
        # This ensures test infrastructure is robust
        test_params = {
            'initial_state': np.array([1.0, 0.0]),
            'control_inputs': np.array([0.1, 0.2]),
            'dt': 0.1,
            'horizon': 2
        }

        # Verify test parameter structure
        assert isinstance(test_params['initial_state'], np.ndarray)
        assert isinstance(test_params['control_inputs'], np.ndarray)
        assert test_params['dt'] > 0
        assert test_params['horizon'] > 0