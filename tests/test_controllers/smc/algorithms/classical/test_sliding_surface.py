#==========================================================================================\\\
#========= tests/test_controllers/smc/algorithms/classical/test_sliding_surface.py ==========\\\
#==========================================================================================\\\
"""
Classical SMC Sliding Surface Computation Tests.

SINGLE JOB: Test only sliding surface computation for Classical SMC controllers.
- Surface value computation
- Surface linearity properties
- Surface zero-crossing behavior
- Surface gradient computation
"""

import numpy as np
import pytest

from tests.test_controllers.smc.test_fixtures import MockDynamics, classical_smc_config
from src.controllers.smc.algorithms import ModularClassicalSMC


class TestSlidingSurfaceComputation:
    """Test sliding surface computation for Classical SMC."""

    @pytest.fixture
    def controller(self, classical_smc_config):
        """Create Classical SMC controller with mock dynamics."""
        return ModularClassicalSMC(config=classical_smc_config)

    def test_surface_computation_returns_finite_values(self, controller):
        """Test that sliding surface computation returns finite values."""
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
        surface = controller._surface.compute(state)

        assert isinstance(surface, (float, np.ndarray))
        if isinstance(surface, np.ndarray):
            assert np.all(np.isfinite(surface))
        else:
            assert np.isfinite(surface)

    def test_surface_linearity_property(self, controller):
        """Test sliding surface linearity: surface(a*x) = a*surface(x)."""
        state = np.array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
        scale = 2.5

        surface1 = controller._surface.compute(state)
        surface2 = controller._surface.compute(scale * state)

        if isinstance(surface1, np.ndarray) and isinstance(surface2, np.ndarray):
            np.testing.assert_allclose(surface2, scale * surface1, rtol=1e-10)
        elif isinstance(surface1, (int, float)) and isinstance(surface2, (int, float)):
            np.testing.assert_allclose(surface2, scale * surface1, rtol=1e-10)

    def test_surface_zero_at_equilibrium(self, controller):
        """Test that surface is zero at desired equilibrium."""
        # Assuming equilibrium is at origin for upright pendulums
        equilibrium_state = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        surface = controller._surface.compute(equilibrium_state)

        if isinstance(surface, np.ndarray):
            np.testing.assert_allclose(surface, 0.0, atol=1e-10)
        else:
            np.testing.assert_allclose(surface, 0.0, atol=1e-10)

    def test_surface_depends_on_position_error(self, controller):
        """Test that surface depends on position errors."""
        state_zero_error = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        state_with_error = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])

        surface_zero = controller._surface.compute(state_zero_error)
        surface_error = controller._surface.compute(state_with_error)

        # Should be different when position errors exist
        if isinstance(surface_zero, np.ndarray) and isinstance(surface_error, np.ndarray):
            assert not np.allclose(surface_zero, surface_error, rtol=1e-6)
        else:
            assert not np.allclose(surface_zero, surface_error, rtol=1e-6)

    def test_surface_depends_on_velocity(self, controller):
        """Test that surface depends on velocities."""
        state_zero_vel = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        state_with_vel = np.array([0.1, 0.1, 0.1, 0.5, 0.3, -0.2])

        surface_zero_vel = controller._surface.compute(state_zero_vel)
        surface_with_vel = controller._surface.compute(state_with_vel)

        # Should be different when velocities are different
        if isinstance(surface_zero_vel, np.ndarray):
            assert not np.allclose(surface_zero_vel, surface_with_vel, rtol=1e-6)
        else:
            assert not np.allclose(surface_zero_vel, surface_with_vel, rtol=1e-6)

    def test_surface_continuity(self, controller):
        """Test surface continuity with small state changes."""
        base_state = np.array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
        delta = 1e-6

        surface_base = controller._surface.compute(base_state)

        # Test continuity in each state dimension
        for i in range(len(base_state)):
            perturbed_state = base_state.copy()
            perturbed_state[i] += delta

            surface_perturbed = controller._surface.compute(perturbed_state)

            # Surface should change smoothly with small perturbations
            if isinstance(surface_base, np.ndarray):
                surface_diff = np.abs(surface_perturbed - surface_base)
                assert np.all(surface_diff < 1e-4), f"Surface discontinuous in dimension {i}"
            else:
                surface_diff = abs(surface_perturbed - surface_base)
                assert surface_diff < 1e-4, f"Surface discontinuous in dimension {i}"

    def test_surface_sign_consistency(self, controller):
        """Test that surface sign is consistent with error direction."""
        # Positive position error should give consistent surface sign
        positive_error_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        negative_error_state = np.array([-0.1, -0.1, -0.1, 0.0, 0.0, 0.0])

        surface_pos = controller._surface.compute(positive_error_state)
        surface_neg = controller._surface.compute(negative_error_state)

        # Signs should be opposite for opposite errors (if surface is scalar)
        if isinstance(surface_pos, (int, float)) and isinstance(surface_neg, (int, float)):
            assert np.sign(surface_pos) == -np.sign(surface_neg) or (surface_pos == 0 and surface_neg == 0)

    def test_surface_gain_sensitivity(self):
        """Test surface sensitivity to gain changes."""
        dynamics = MockDynamics()

        # Low gain configuration
        low_gain_config = classical_smc_config()
        low_gain_config.gains = [0.5, 0.5, 0.5, 0.5, 5.0, 0.25]
        low_controller = ModularClassicalSMC(config=low_gain_config)

        # High gain configuration
        high_gain_config = classical_smc_config()
        high_gain_config.gains = [2.0, 2.0, 2.0, 2.0, 20.0, 1.0]
        high_controller = ModularClassicalSMC(config=high_gain_config)

        state = np.array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1])

        surface_low = low_controller._surface.compute(state)
        surface_high = high_controller._surface.compute(state)

        # Higher gains should generally give larger surface values
        if isinstance(surface_low, np.ndarray):
            assert np.any(np.abs(surface_high) >= np.abs(surface_low) * 0.5)
        else:
            assert abs(surface_high) >= abs(surface_low) * 0.5