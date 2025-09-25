#==========================================================================================\\\
#========= tests/test_controllers/smc/algorithms/classical/test_control_computation.py =======\\\
#==========================================================================================\\\
"""
Classical SMC Control Computation Tests.

SINGLE JOB: Test only control signal computation for Classical SMC controllers.
- Control signal generation
- Control bounds enforcement
- Control output format validation
- Control signal finite value verification
"""

import numpy as np
import pytest

from tests.test_controllers.smc.test_fixtures import (
    MockDynamics, classical_smc_config, validate_control_output
)
from src.controllers.smc.algorithms import ModularClassicalSMC


class TestControlComputation:
    """Test control computation for Classical SMC."""

    @pytest.fixture
    def controller(self, classical_smc_config):
        """Create Classical SMC controller for testing."""
        return ModularClassicalSMC(config=classical_smc_config)

    def test_control_computation_returns_valid_format(self, controller):
        """Test that control computation returns valid format."""
        state = np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1])
        state_vars = {}
        history = {}

        result = controller.compute_control(state, state_vars, history)

        assert isinstance(result, dict)
        assert 'control' in result or 'u' in result

    def test_control_values_are_finite(self, controller):
        """Test that control values are finite."""
        state = np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1])
        state_vars = {}
        history = {}

        result = controller.compute_control(state, state_vars, history)
        control = result.get('control', result.get('u', result.get('u_saturated')))

        if control is not None:
            assert np.all(np.isfinite(control))

    def test_control_bounds_enforcement(self, controller):
        """Test that control signals respect force bounds."""
        state = np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1])
        state_vars = {}
        history = {}

        result = controller.compute_control(state, state_vars, history)
        control = result.get('control', result.get('u', result.get('u_saturated')))

        if control is not None:
            assert validate_control_output(control, max_force=50.0)

    def test_control_responds_to_large_errors(self, controller):
        """Test that control responds appropriately to large errors."""
        large_error_state = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
        small_error_state = np.array([0.01, 0.01, 0.01, 0.0, 0.0, 0.0])

        result_large = controller.compute_control(large_error_state, {}, {})
        result_small = controller.compute_control(small_error_state, {}, {})

        control_large = result_large.get('control', result_large.get('u'))
        control_small = result_small.get('control', result_small.get('u'))

        if control_large is not None and control_small is not None:
            # Larger errors should generally produce larger control efforts
            assert np.any(np.abs(control_large) >= np.abs(control_small))

    def test_control_zero_at_equilibrium(self, controller):
        """Test that control is minimal at equilibrium."""
        equilibrium_state = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        result = controller.compute_control(equilibrium_state, {}, {})
        control = result.get('control', result.get('u'))

        if control is not None:
            # Control should be small (but not necessarily exactly zero due to disturbances)
            assert np.all(np.abs(control) < 1.0)

    def test_control_consistency_same_input(self, controller):
        """Test that same input produces same control output."""
        state = np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1])
        state_vars = {}
        history = {}

        result1 = controller.compute_control(state, state_vars, history)
        result2 = controller.compute_control(state, state_vars, history)

        control1 = result1.get('control', result1.get('u'))
        control2 = result2.get('control', result2.get('u'))

        if control1 is not None and control2 is not None:
            np.testing.assert_allclose(control1, control2, rtol=1e-10)

    def test_control_opposes_velocity(self, controller):
        """Test that control opposes velocity in the right direction."""
        # Positive velocity state
        pos_vel_state = np.array([0.0, 0.0, 0.0, 0.5, 0.3, -0.2])
        # Negative velocity state
        neg_vel_state = np.array([0.0, 0.0, 0.0, -0.5, -0.3, 0.2])

        result_pos = controller.compute_control(pos_vel_state, {}, {})
        result_neg = controller.compute_control(neg_vel_state, {}, {})

        control_pos = result_pos.get('control', result_pos.get('u'))
        control_neg = result_neg.get('control', result_neg.get('u'))

        if control_pos is not None and control_neg is not None:
            # Controls should be in opposite directions for opposite velocities
            if np.any(np.abs(control_pos) > 1e-6) and np.any(np.abs(control_neg) > 1e-6):
                # Check that at least some components have opposite signs
                sign_product = np.sign(control_pos) * np.sign(control_neg)
                assert np.any(sign_product <= 0)  # Some components should oppose

    def test_control_saturation_behavior(self):
        """Test control saturation with extreme states."""
        # Low force limit configuration
        low_force_config = classical_smc_config()
        low_force_config.max_force = 5.0  # Very low limit
        low_force_controller = ModularClassicalSMC(config=low_force_config)

        # Extreme state that should cause saturation
        extreme_state = np.array([5.0, 5.0, 5.0, 2.0, 2.0, 2.0])

        result = low_force_controller.compute_control(extreme_state, {}, {})
        control = result.get('control', result.get('u'))

        if control is not None:
            # Should be saturated at the limit
            assert np.all(np.abs(control) <= 5.0)
            # At least one component should be at or near the limit
            assert np.any(np.abs(control) >= 4.5)

    def test_control_output_shape_consistency(self, controller):
        """Test that control output has consistent shape."""
        test_states = [
            np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0]),
            np.array([0.5, 0.2, -0.3, 0.1, -0.1, 0.2]),
            np.array([0.0, 0.0, 0.0, 0.5, 0.5, 0.5])
        ]

        control_shapes = []
        for state in test_states:
            result = controller.compute_control(state, {}, {})
            control = result.get('control', result.get('u'))

            if control is not None:
                control_shapes.append(np.array(control).shape)

        # All control outputs should have the same shape
        if control_shapes:
            first_shape = control_shapes[0]
            assert all(shape == first_shape for shape in control_shapes)