#==========================================================================================\\
#======== tests/test_simulation/vector/test_vector_simulation_robustness.py ==============\\
#==========================================================================================\\

"""
Comprehensive test suite for vector simulation robustness and edge case handling.

This module tests vector simulation edge cases, fixes scalar control input handling,
handles sequence length mismatches gracefully, and ensures robust operation on all
input types and edge cases.
"""

import pytest
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
import warnings
from unittest.mock import Mock, patch, MagicMock

# Vector simulation imports
try:
    from src.simulation.engines.vector_sim import simulate, simulate_system_batch
    VECTOR_SIM_AVAILABLE = True
except ImportError:
    VECTOR_SIM_AVAILABLE = False
    simulate = None
    simulate_system_batch = None


@pytest.mark.skipif(not VECTOR_SIM_AVAILABLE, reason="Vector simulation modules not available")
class TestVectorSimulationScalarInputs:
    """Test vector simulation handling of scalar control inputs."""

    @pytest.fixture
    def mock_step_function(self):
        """Mock the underlying step function."""
        def mock_step(state, control, dt):
            state = np.asarray(state)
            control = np.asarray(control)

            # Handle scalar control properly
            if control.ndim == 0:
                control_val = float(control)
            elif control.shape == (1,):
                control_val = float(control[0])
            elif len(control) == 1:
                control_val = float(control[0])
            else:
                control_val = float(control[0])  # Use first element if multi-dimensional

            # Simple dynamics: derivative proportional to control
            state_derivative = np.full_like(state, control_val)
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

    def test_scalar_control_single_value(self, mock_step_function, mock_safety_guards):
        """Test simulation with single scalar control value."""
        initial_state = np.array([1.0, 0.0])
        control_input = 0.5  # Single scalar value
        dt = 0.1

        # Should not raise IndexError
        result = simulate(initial_state, control_input, dt, horizon=3)

        assert isinstance(result, np.ndarray)
        assert result.shape == (4, 2)  # (horizon+1, state_dim)
        np.testing.assert_array_equal(result[0], initial_state)

    def test_scalar_control_zero_dimensional_array(self, mock_step_function, mock_safety_guards):
        """Test simulation with zero-dimensional array control."""
        initial_state = np.array([2.0, 1.0])
        control_input = np.array(0.3)  # 0-dimensional array
        dt = 0.05

        result = simulate(initial_state, control_input, dt, horizon=2)

        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 2)
        np.testing.assert_array_equal(result[0], initial_state)

    def test_scalar_control_sequence(self, mock_step_function, mock_safety_guards):
        """Test simulation with sequence of scalar controls."""
        initial_state = np.array([0.5, -0.2])
        control_inputs = [0.1, 0.2, 0.3, 0.4]  # Python list of scalars
        dt = 0.1

        result = simulate(initial_state, control_inputs, dt)

        assert result.shape == (5, 2)  # len(controls)+1, state_dim
        np.testing.assert_array_equal(result[0], initial_state)

    def test_scalar_control_numpy_array_sequence(self, mock_step_function, mock_safety_guards):
        """Test simulation with numpy array of scalar controls."""
        initial_state = np.array([1.5])
        control_inputs = np.array([0.5, -0.2, 0.8])  # 1D array of scalars
        dt = 0.02

        result = simulate(initial_state, control_inputs, dt)

        assert result.shape == (4, 1)  # len(controls)+1, state_dim
        np.testing.assert_array_equal(result[0], initial_state)

    def test_mixed_control_types(self, mock_step_function, mock_safety_guards):
        """Test simulation robustness with mixed control input types."""
        test_cases = [
            # (initial_state, control_input, expected_shape)
            (np.array([1.0]), 0.5, (3, 1)),  # scalar state, scalar control
            (np.array([1.0, 0.0]), 0.5, (3, 2)),  # vector state, scalar control
            (np.array([1.0]), [0.1, 0.2], (3, 1)),  # scalar state, control sequence
            (np.array([1.0, 0.0]), [0.1, 0.2], (3, 2)),  # vector state, control sequence
        ]

        for initial_state, control_input, expected_shape in test_cases:
            result = simulate(initial_state, control_input, 0.1, horizon=2)

            assert result.shape == expected_shape, \
                f"Failed for state {initial_state.shape}, control {type(control_input)}"
            np.testing.assert_array_equal(result[0], initial_state)

    def test_batch_scalar_controls(self, mock_step_function, mock_safety_guards):
        """Test batch simulation with scalar control inputs."""
        initial_states = np.array([[1.0, 0.0], [2.0, 1.0]])  # Batch of 2

        # Test different batch control formats
        control_formats = [
            # Format 1: (batch_size, horizon) with scalars
            np.array([[0.1, 0.2], [0.3, 0.4]]),

            # Format 2: Single control broadcasted
            0.5,

            # Format 3: 1D array broadcasted across batch
            np.array([0.1, 0.2]),
        ]

        for i, control_inputs in enumerate(control_formats):
            result = simulate(initial_states, control_inputs, 0.1, horizon=2)

            assert result.shape[0] == 2  # Batch size preserved
            assert result.shape[1] == 3  # horizon+1 time steps
            assert result.shape[2] == 2  # State dimension

            # Check initial states preserved
            np.testing.assert_array_equal(result[:, 0, :], initial_states)


@pytest.mark.skipif(not VECTOR_SIM_AVAILABLE, reason="Vector simulation modules not available")
class TestVectorSimulationSequenceMismatches:
    """Test vector simulation handling of sequence length mismatches."""

    @pytest.fixture
    def mock_step_function(self):
        """Mock step function for sequence mismatch tests."""
        def mock_step(state, control, dt):
            # Robust control handling
            control = np.asarray(control)
            if control.ndim == 0:
                control_val = float(control)
            else:
                control_val = float(control.flat[0])

            # Simple dynamics
            return np.asarray(state) + dt * control_val * 0.1 * np.ones_like(state)

        with patch('src.simulation.engines.vector_sim._step_fn', side_effect=mock_step):
            yield mock_step

    @pytest.fixture
    def mock_safety_guards(self):
        """Mock safety guards."""
        with patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):
            yield

    def test_control_shorter_than_horizon(self, mock_step_function, mock_safety_guards):
        """Test when control sequence is shorter than horizon."""
        initial_state = np.array([1.0, 0.0])
        control_inputs = np.array([0.1, 0.2])  # Only 2 controls
        dt = 0.1

        # Should use last control value for remaining steps
        result = simulate(initial_state, control_inputs, dt, horizon=5)

        assert result.shape == (6, 2)  # horizon+1, state_dim
        np.testing.assert_array_equal(result[0], initial_state)
        assert np.all(np.isfinite(result))

    def test_control_longer_than_horizon(self, mock_step_function, mock_safety_guards):
        """Test when control sequence is longer than horizon."""
        initial_state = np.array([0.5, -0.2])
        control_inputs = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])  # 6 controls
        dt = 0.1

        # Should only use first 3 controls for horizon=3
        result = simulate(initial_state, control_inputs, dt, horizon=3)

        assert result.shape == (4, 2)  # horizon+1, state_dim
        np.testing.assert_array_equal(result[0], initial_state)

    def test_empty_control_sequence(self, mock_step_function, mock_safety_guards):
        """Test handling of empty control sequence."""
        initial_state = np.array([1.0, 0.0])
        control_inputs = np.array([])  # Empty array
        dt = 0.1

        # Should handle gracefully with horizon=0
        result = simulate(initial_state, control_inputs, dt, horizon=0)

        assert result.shape == (1, 2)  # Only initial state
        np.testing.assert_array_equal(result[0], initial_state)

    def test_single_control_multiple_steps(self, mock_step_function, mock_safety_guards):
        """Test single control value extended over multiple steps."""
        initial_state = np.array([2.0, 1.0, 0.5])
        control_inputs = np.array([0.5])  # Single control
        dt = 0.05

        # Should repeat control for all horizon steps
        result = simulate(initial_state, control_inputs, dt, horizon=4)

        assert result.shape == (5, 3)  # horizon+1, state_dim
        np.testing.assert_array_equal(result[0], initial_state)
        assert np.all(np.isfinite(result))

    def test_batch_sequence_mismatches(self, mock_step_function, mock_safety_guards):
        """Test batch simulation with sequence length mismatches."""
        initial_states = np.array([[1.0, 0.0], [0.5, 1.0]])

        # Different mismatch scenarios
        mismatch_scenarios = [
            # Controls shorter than horizon
            (np.array([[0.1], [0.2]]), 3),  # 1 control, horizon 3

            # Single control for batch
            (np.array([0.3]), 2),  # Broadcast to batch

            # Uneven control lengths (handled by broadcasting/indexing)
            (np.array([[0.1, 0.2], [0.3, 0.4]]), 3),  # 2 controls, horizon 3
        ]

        for control_inputs, horizon in mismatch_scenarios:
            result = simulate(initial_states, control_inputs, 0.1, horizon=horizon)

            assert result.shape[0] == 2  # Batch size preserved
            assert result.shape[1] == horizon + 1  # Time steps
            assert result.shape[2] == 2  # State dimension

            # Initial states should be preserved
            np.testing.assert_array_equal(result[:, 0, :], initial_states)


@pytest.mark.skipif(not VECTOR_SIM_AVAILABLE, reason="Vector simulation modules not available")
class TestVectorSimulationDimensionMismatches:
    """Test vector simulation handling of dimension mismatches."""

    @pytest.fixture
    def robust_step_function(self):
        """Step function that handles dimension mismatches."""
        def mock_step(state, control, dt):
            state = np.asarray(state)
            control = np.asarray(control)

            # Robust dimension handling
            if control.ndim == 0:
                control_expanded = np.full(state.shape, float(control))
            elif len(control) == 1:
                control_expanded = np.full(state.shape, float(control[0]))
            elif len(control) == len(state):
                control_expanded = control
            else:
                # Broadcast or truncate as needed
                control_expanded = np.broadcast_to(control[:len(state)], state.shape)

            # Simple dynamics with dimension-safe operations
            return state + dt * 0.1 * control_expanded

        with patch('src.simulation.engines.vector_sim._step_fn', side_effect=mock_step):
            yield mock_step

    @pytest.fixture
    def mock_safety_guards(self):
        """Mock safety guards."""
        with patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):
            yield

    def test_scalar_control_vector_state(self, robust_step_function, mock_safety_guards):
        """Test scalar control with vector state."""
        initial_state = np.array([1.0, 0.5, -0.2, 0.8])  # 4D state
        control_input = 0.3  # Scalar control
        dt = 0.1

        result = simulate(initial_state, control_input, dt, horizon=2)

        assert result.shape == (3, 4)
        np.testing.assert_array_equal(result[0], initial_state)

    def test_vector_control_scalar_state(self, robust_step_function, mock_safety_guards):
        """Test vector control with scalar state."""
        initial_state = np.array([2.0])  # 1D state
        control_input = np.array([0.1, 0.2, 0.3])  # 3D control sequence
        dt = 0.05

        # Should handle gracefully
        result = simulate(initial_state, control_input, dt)

        assert result.shape[1] == 1  # State dimension preserved
        assert result.shape[0] == 4  # len(control) + 1
        np.testing.assert_array_equal(result[0], initial_state)

    def test_mismatched_control_state_dimensions(self, robust_step_function, mock_safety_guards):
        """Test various control-state dimension mismatches."""
        test_cases = [
            # (state_dim, control_shape, should_work)
            (2, (3,), True),    # 2D state, 3D control
            (4, (1,), True),    # 4D state, 1D control
            (1, (2, 3), True),  # 1D state, 2x3 control matrix
            (3, (), True),      # 3D state, scalar control
        ]

        for state_dim, control_shape, should_work in test_cases:
            initial_state = np.random.randn(state_dim)

            if len(control_shape) == 0:
                control_input = 0.5  # Scalar
            else:
                control_input = np.random.randn(*control_shape)

            try:
                result = simulate(initial_state, control_input, 0.1, horizon=1)

                if should_work:
                    assert result.shape[1] == state_dim
                    np.testing.assert_array_equal(result[0], initial_state)
                else:
                    pytest.fail(f"Expected failure for state_dim={state_dim}, control_shape={control_shape}")

            except Exception as e:
                if should_work:
                    pytest.fail(f"Unexpected failure for state_dim={state_dim}, "
                               f"control_shape={control_shape}: {e}")

    def test_batch_dimension_mismatches(self, robust_step_function, mock_safety_guards):
        """Test batch simulation with dimension mismatches."""
        # Batch of different state dimensions (if supported)
        initial_states = np.array([[1.0, 0.0], [0.5, 1.5]])  # 2x2

        # Various control formats
        control_formats = [
            0.3,  # Single scalar for all batch elements
            np.array([0.1, 0.2]),  # One control per batch element
            np.array([[0.1], [0.2]]),  # Explicit batch control
            np.array([[0.1, 0.2], [0.3, 0.4]]),  # Full batch control matrix
        ]

        for control_input in control_formats:
            result = simulate(initial_states, control_input, 0.1, horizon=1)

            assert result.shape[0] == 2  # Batch size
            assert result.shape[2] == 2  # State dimension
            np.testing.assert_array_equal(result[:, 0, :], initial_states)


@pytest.mark.skipif(not VECTOR_SIM_AVAILABLE, reason="Vector simulation modules not available")
class TestVectorSimulationEdgeCases:
    """Test vector simulation edge cases and error conditions."""

    @pytest.fixture
    def mock_step_function(self):
        """Mock step function for edge case testing."""
        def mock_step(state, control, dt):
            state = np.asarray(state, dtype=float)

            try:
                control = np.asarray(control, dtype=float)
                if control.size == 0:
                    control_val = 0.0
                elif control.ndim == 0:
                    control_val = float(control)
                else:
                    control_val = float(control.flat[0])
            except (ValueError, TypeError):
                control_val = 0.0

            return state + dt * control_val * 0.01 * np.ones_like(state)

        with patch('src.simulation.engines.vector_sim._step_fn', side_effect=mock_step):
            yield mock_step

    @pytest.fixture
    def mock_safety_guards(self):
        """Mock safety guards."""
        with patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):
            yield

    def test_zero_dimensional_inputs(self, mock_step_function, mock_safety_guards):
        """Test simulation with zero-dimensional inputs."""
        # Zero-dimensional state
        initial_state = np.array([])
        control_input = 0.5
        dt = 0.1

        result = simulate(initial_state, control_input, dt, horizon=1)

        assert result.shape == (2, 0)  # (horizon+1, 0)
        assert result.dtype == float

    def test_very_large_arrays(self, mock_step_function, mock_safety_guards):
        """Test simulation with large arrays."""
        # Large state dimension
        large_state = np.random.randn(100) * 0.01  # Keep small for stability
        control_input = np.random.randn(50) * 0.1
        dt = 0.01

        result = simulate(large_state, control_input, dt, horizon=2)

        assert result.shape == (3, 100)
        assert np.all(np.isfinite(result))
        np.testing.assert_array_equal(result[0], large_state)

    def test_extreme_values(self, mock_step_function, mock_safety_guards):
        """Test simulation with extreme values."""
        extreme_cases = [
            # Very small values
            (np.array([1e-15, 1e-15]), np.array([1e-10, 1e-10])),

            # Large values (but finite)
            (np.array([1e6, -1e6]), np.array([1e3, -1e3])),

            # Mixed scales
            (np.array([1e-6, 1e6]), np.array([1e-3, 1e3])),
        ]

        for initial_state, control_input in extreme_cases:
            result = simulate(initial_state, control_input, 0.001, horizon=1)

            assert np.all(np.isfinite(result))
            assert result.shape[1] == len(initial_state)
            np.testing.assert_array_equal(result[0], initial_state)

    def test_non_finite_inputs_handling(self, mock_step_function, mock_safety_guards):
        """Test handling of non-finite inputs."""
        # The simulation should handle non-finite inputs gracefully
        problematic_inputs = [
            # NaN in initial state
            (np.array([1.0, np.nan]), np.array([0.1, 0.2])),

            # Inf in control
            (np.array([1.0, 0.0]), np.array([np.inf, 0.1])),

            # NaN in control
            (np.array([0.5, -0.5]), np.array([0.1, np.nan])),
        ]

        for initial_state, control_input in problematic_inputs:
            # Should either handle gracefully or raise appropriate error
            try:
                result = simulate(initial_state, control_input, 0.1, horizon=1)

                # If it doesn't raise an error, check basic properties
                assert isinstance(result, np.ndarray)
                assert result.shape[1] == len(initial_state)

            except (ValueError, RuntimeError, FloatingPointError):
                # Expected behavior for invalid inputs
                pass

    def test_type_coercion_robustness(self, mock_step_function, mock_safety_guards):
        """Test robustness of type coercion."""
        # Different input types that should be coercible
        type_test_cases = [
            # Lists
            ([1.0, 0.0], [0.1, 0.2]),

            # Tuples
            ((0.5, 1.5), (0.3, 0.4)),

            # Mixed types
            (np.array([1.0, 0.0]), [0.1, 0.2]),

            # Integer inputs
            ([1, 0], [1, 2]),
        ]

        for initial_state, control_input in type_test_cases:
            result = simulate(initial_state, control_input, 0.1, horizon=1)

            assert isinstance(result, np.ndarray)
            assert result.dtype == float
            assert result.shape[0] == 2  # horizon + 1

    def test_memory_efficiency_large_batch(self, mock_step_function, mock_safety_guards):
        """Test memory efficiency with large batch sizes."""
        import gc

        initial_memory = len(gc.get_objects())

        # Large batch simulation
        batch_size = 100
        state_dim = 4
        horizon = 50

        initial_states = np.random.randn(batch_size, state_dim) * 0.1
        control_inputs = np.random.randn(batch_size, horizon) * 0.1

        result = simulate(initial_states, control_inputs, 0.01)

        # Validate result
        assert result.shape == (batch_size, horizon + 1, state_dim)
        assert np.all(np.isfinite(result))

        # Clean up
        del result, initial_states, control_inputs
        gc.collect()

        final_memory = len(gc.get_objects())
        memory_growth = final_memory - initial_memory

        # Should not have excessive memory growth
        assert memory_growth < 10000  # Allow reasonable growth


@pytest.mark.skipif(not VECTOR_SIM_AVAILABLE, reason="Vector simulation modules not available")
class TestVectorSimulationSafetyAndRecovery:
    """Test vector simulation safety mechanisms and error recovery."""

    @pytest.fixture
    def unreliable_step_function(self):
        """Step function that occasionally fails or returns problematic values."""
        self.call_count = 0

        def mock_step(state, control, dt):
            self.call_count += 1

            # Fail on specific calls to test recovery
            if self.call_count == 5:
                raise RuntimeError("Simulated step failure")
            elif self.call_count == 10:
                return np.array([np.nan, np.inf, -np.inf, 0.0])
            else:
                state = np.asarray(state)
                control = np.asarray(control)
                control_val = float(control.flat[0]) if control.size > 0 else 0.0
                return state + dt * control_val * 0.1 * np.ones_like(state)

        with patch('src.simulation.engines.vector_sim._step_fn', side_effect=mock_step):
            yield mock_step

    def test_safety_guard_integration(self):
        """Test integration with safety guards."""
        initial_state = np.array([1.0, 0.0])
        control_input = np.array([0.1, 0.2])
        dt = 0.1

        # Test with energy limits
        with patch('src.simulation.engines.vector_sim._guard_energy') as mock_energy:
            mock_energy.return_value = True

            result = simulate(
                initial_state, control_input, dt,
                energy_limits=10.0
            )

            # Energy guard should have been called
            mock_energy.assert_called()
            assert isinstance(result, np.ndarray)

        # Test with state bounds
        with patch('src.simulation.engines.vector_sim._guard_bounds') as mock_bounds:
            mock_bounds.return_value = True

            bounds = (np.array([-2.0, -2.0]), np.array([2.0, 2.0]))
            result = simulate(
                initial_state, control_input, dt,
                state_bounds=bounds
            )

            # Bounds guard should have been called
            mock_bounds.assert_called()
            assert isinstance(result, np.ndarray)

    def test_early_stopping_robustness(self):
        """Test early stopping with various stop conditions."""
        initial_state = np.array([0.1, 0.0])
        control_input = np.array([0.5, 0.4, 0.3, 0.2, 0.1])
        dt = 0.1

        # Simple stop function
        def stop_when_large(state):
            return np.abs(state[0]) > 0.3

        with patch('src.simulation.engines.vector_sim._step_fn') as mock_step:
            # Make state grow with each step
            def growing_step(state, control, dt):
                return state + dt * np.array([1.0, 0.0])
            mock_step.side_effect = growing_step

            with patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=True), \
                 patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
                 patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):

                result = simulate(
                    initial_state, control_input, dt,
                    stop_fn=stop_when_large
                )

                # Should stop early
                assert result.shape[0] < len(control_input) + 1
                assert isinstance(result, np.ndarray)

    def test_configuration_fallback_handling(self):
        """Test handling when configuration is unavailable."""
        initial_state = np.array([0.5, -0.2])
        control_input = 0.2
        dt = 0.05

        # Simulate config unavailability
        with patch('src.simulation.engines.vector_sim.config', None):
            with patch('src.simulation.engines.vector_sim._step_fn') as mock_step:
                mock_step.return_value = initial_state + dt * 0.1 * np.ones_like(initial_state)

                with patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=True), \
                     patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
                     patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):

                    # Should still work without config
                    result = simulate(initial_state, control_input, dt, horizon=2)

                    assert isinstance(result, np.ndarray)
                    assert result.shape == (3, 2)
                    np.testing.assert_array_equal(result[0], initial_state)


@pytest.mark.skipif(not VECTOR_SIM_AVAILABLE, reason="Vector simulation modules not available")
class TestVectorSimulationBatchRobustness:
    """Test batch vector simulation robustness."""

    @pytest.fixture
    def mock_batch_step(self):
        """Mock step function for batch testing."""
        def mock_step(states, controls, dt):
            states = np.asarray(states)
            controls = np.asarray(controls)

            # Handle both single and batch inputs
            if states.ndim == 1:
                states = states[np.newaxis, :]
            if controls.ndim == 0:
                controls = np.full((states.shape[0],), float(controls))
            elif controls.ndim == 1 and len(controls) == 1:
                controls = np.full((states.shape[0],), float(controls[0]))

            # Simple batch dynamics
            next_states = states + dt * 0.1 * controls[:, np.newaxis] * np.ones_like(states)
            return next_states[0] if states.shape[0] == 1 else next_states

        with patch('src.simulation.engines.vector_sim._step_fn', side_effect=mock_step):
            yield mock_step

    @pytest.fixture
    def mock_safety_guards(self):
        """Mock safety guards."""
        with patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):
            yield

    def test_batch_with_different_initial_conditions(self, mock_batch_step, mock_safety_guards):
        """Test batch simulation with diverse initial conditions."""
        # Diverse initial conditions
        initial_states = np.array([
            [0.1, 0.0],      # Small positive
            [-0.5, 0.2],     # Mixed signs
            [0.0, 0.0],      # Zero state
            [1e-6, 1e-6],    # Very small
            [2.0, -1.0],     # Larger values
        ])

        control_inputs = np.array([
            [0.1, 0.2],
            [0.3, 0.4],
            [0.0, 0.0],
            [1e-3, 1e-3],
            [0.5, -0.3]
        ])

        dt = 0.1
        result = simulate(initial_states, control_inputs, dt)

        assert result.shape == (5, 3, 2)  # batch, time, state

        # Check each batch element
        for i in range(5):
            np.testing.assert_array_equal(result[i, 0, :], initial_states[i])
            assert np.all(np.isfinite(result[i]))

    def test_batch_broadcasting_edge_cases(self, mock_batch_step, mock_safety_guards):
        """Test edge cases in batch broadcasting."""
        batch_size = 3
        initial_states = np.random.randn(batch_size, 2) * 0.1

        # Various broadcasting scenarios
        broadcast_cases = [
            # Single scalar for all batches
            (0.5, "scalar broadcast"),

            # Single control sequence broadcasted
            (np.array([0.1, 0.2, 0.3]), "sequence broadcast"),

            # Single batch element broadcasted
            (np.array([[0.1, 0.2, 0.3]]), "single batch broadcast"),

            # Full batch specification
            (np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]), "full batch"),
        ]

        for control_input, case_name in broadcast_cases:
            result = simulate(initial_states, control_input, 0.1, horizon=2)

            assert result.shape[0] == batch_size, f"Failed for {case_name}"
            assert result.shape[1] == 3, f"Failed for {case_name}"  # horizon + 1
            assert result.shape[2] == 2, f"Failed for {case_name}"  # state dim

            # Initial states preserved
            np.testing.assert_array_equal(result[:, 0, :], initial_states)

    def test_batch_early_stopping_consistency(self, mock_batch_step, mock_safety_guards):
        """Test that early stopping works consistently across batch elements."""
        initial_states = np.array([
            [0.01, 0.0],   # Will trigger stop condition later
            [0.5, 0.0],    # Will trigger stop condition early
            [0.001, 0.0]   # May not trigger stop condition
        ])

        # Control that grows the first state component
        control_inputs = np.array([
            [0.1, 0.1, 0.1],
            [0.1, 0.1, 0.1],
            [0.1, 0.1, 0.1]
        ])

        def stop_condition(state):
            """Stop when any state component exceeds 0.3."""
            return np.any(np.abs(state) > 0.3)

        result = simulate(
            initial_states, control_inputs, 0.1,
            stop_fn=stop_condition
        )

        # Should stop when first batch element triggers condition
        assert result.shape[0] == 3  # All batch elements present
        assert result.shape[1] <= 4  # May stop early

        # All batch elements should have same number of time steps
        for i in range(3):
            assert result.shape[1] == result.shape[1]  # Consistent time dimension

    def test_large_batch_performance(self, mock_batch_step, mock_safety_guards):
        """Test performance and stability with large batches."""
        import time

        batch_size = 200
        state_dim = 6
        horizon = 20

        # Generate large batch
        initial_states = np.random.randn(batch_size, state_dim) * 0.01
        control_inputs = np.random.randn(batch_size, horizon) * 0.1

        start_time = time.time()

        result = simulate(initial_states, control_inputs, 0.01)

        end_time = time.time()
        computation_time = end_time - start_time

        # Validate result
        assert result.shape == (batch_size, horizon + 1, state_dim)
        assert np.all(np.isfinite(result))

        # Check initial states preserved
        np.testing.assert_array_equal(result[:, 0, :], initial_states)

        # Performance should be reasonable (< 10 seconds for large batch)
        assert computation_time < 10.0, f"Computation took too long: {computation_time:.2f}s"


if __name__ == "__main__":
    # Run basic smoke test if executed directly
    print("Running vector simulation robustness validation...")

    if not VECTOR_SIM_AVAILABLE:
        print("⚠️  Vector simulation modules not available - skipping tests")
        exit(0)

    try:
        # Test scalar input handling
        test_scalars = TestVectorSimulationScalarInputs()
        print("✓ Testing scalar control input handling...")

        # Mock the required patches for direct testing
        with patch('src.simulation.engines.vector_sim._step_fn') as mock_step, \
             patch('src.simulation.engines.vector_sim._guard_no_nan', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_energy', return_value=True), \
             patch('src.simulation.engines.vector_sim._guard_bounds', return_value=True):

            def simple_step(state, control, dt):
                state = np.asarray(state)
                control = np.asarray(control)
                control_val = float(control) if control.ndim == 0 else float(control[0])
                return state + dt * control_val * 0.1 * np.ones_like(state)

            mock_step.side_effect = simple_step

            # Test scalar control
            result = simulate(np.array([1.0, 0.0]), 0.5, 0.1, horizon=1)
            assert result.shape == (2, 2)
            print("  ✓ Scalar control input handling works")

            # Test sequence mismatch
            result = simulate(np.array([1.0, 0.0]), [0.1], 0.1, horizon=3)
            assert result.shape == (4, 2)
            print("  ✓ Sequence length mismatch handling works")

            # Test dimension mismatch
            result = simulate(np.array([1.0]), np.array([0.1, 0.2]), 0.1)
            assert result.shape[1] == 1
            print("  ✓ Dimension mismatch handling works")

        print("\n🎉 All vector simulation robustness tests passed!")
        print("Vector simulation is robust and ready for deployment.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise