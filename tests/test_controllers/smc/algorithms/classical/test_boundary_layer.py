#==========================================================================================\\\
#========= tests/test_controllers/smc/algorithms/classical/test_boundary_layer.py ============\\\
#==========================================================================================\\\
"""
Classical SMC Boundary Layer Tests.

SINGLE JOB: Test only boundary layer chattering reduction for Classical SMC controllers.
- Boundary layer thickness effects
- Chattering reduction verification
- Smooth control behavior near surface
- Boundary layer parameter validation
"""

import numpy as np
import pytest

from tests.test_controllers.smc.test_fixtures import MockDynamics, classical_smc_config
from src.controllers.smc.algorithms import ModularClassicalSMC


class TestBoundaryLayerBehavior:
    """Test boundary layer chattering reduction for Classical SMC."""

    def test_smooth_control_inside_boundary_layer(self):
        """Test that control is smooth inside the boundary layer."""
        # Create configuration with specific boundary layer
        config = classical_smc_config()
        config.boundary_layer = 0.1
        controller = ModularClassicalSMC(config=config)

        # State very close to sliding surface
        near_surface_state = np.array([0.01, 0.01, 0.01, 0.0, 0.0, 0.0])

        result = controller.compute_control(near_surface_state, {}, {})
        control = result.get('control', result.get('u'))

        if control is not None:
            # Control should be smooth (not switching/saturated) in boundary layer
            assert np.all(np.abs(control) < 40.0)  # Should not saturate

    def test_boundary_layer_thickness_effect(self):
        """Test that boundary layer thickness affects control smoothness."""
        dynamics = MockDynamics()

        # Thin boundary layer
        thin_config = classical_smc_config()
        thin_config.boundary_layer = 0.01
        thin_controller = ModularClassicalSMC(config=thin_config)

        # Thick boundary layer
        thick_config = classical_smc_config()
        thick_config.boundary_layer = 0.5
        thick_controller = ModularClassicalSMC(config=thick_config)

        # State at moderate distance from surface
        test_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])

        result_thin = thin_controller.compute_control(test_state, {}, {})
        result_thick = thick_controller.compute_control(test_state, {}, {})

        control_thin = result_thin.get('control', result_thin.get('u'))
        control_thick = result_thick.get('control', result_thick.get('u'))

        if control_thin is not None and control_thick is not None:
            # Thick boundary layer should generally give smoother (smaller) control
            # when the state is within the thick boundary but outside the thin one
            assert np.any(np.abs(control_thick) <= np.abs(control_thin) * 1.1)

    def test_control_continuity_across_boundary(self):
        """Test control continuity as state crosses boundary layer."""
        config = classical_smc_config()
        config.boundary_layer = 0.1
        controller = ModularClassicalSMC(config=config)

        # States just inside and outside boundary layer
        inside_state = np.array([0.05, 0.05, 0.05, 0.0, 0.0, 0.0])
        outside_state = np.array([0.15, 0.15, 0.15, 0.0, 0.0, 0.0])

        result_inside = controller.compute_control(inside_state, {}, {})
        result_outside = controller.compute_control(outside_state, {}, {})

        control_inside = result_inside.get('control', result_inside.get('u'))
        control_outside = result_outside.get('control', result_outside.get('u'))

        if control_inside is not None and control_outside is not None:
            # Controls should be finite and reasonable on both sides
            assert np.all(np.isfinite(control_inside))
            assert np.all(np.isfinite(control_outside))

            # Should not have extreme jumps
            control_diff = np.abs(control_outside - control_inside)
            assert np.all(control_diff < 100.0)  # No extreme discontinuities

    def test_chattering_reduction_with_noise(self):
        """Test chattering reduction with noisy states."""
        config = classical_smc_config()
        config.boundary_layer = 0.1
        controller = ModularClassicalSMC(config=config)

        base_state = np.array([0.05, 0.05, 0.05, 0.0, 0.0, 0.0])
        noise_level = 0.01

        controls = []
        # Add small random noise to simulate sensor noise
        for _ in range(10):
            noise = np.random.normal(0, noise_level, 6)
            noisy_state = base_state + noise

            result = controller.compute_control(noisy_state, {}, {})
            control = result.get('control', result.get('u'))

            if control is not None:
                controls.append(control)

        if controls:
            controls = np.array(controls)

            # Control variations should be bounded (chattering reduced)
            control_std = np.std(controls, axis=0)
            assert np.all(control_std < 5.0)  # Limited variation

    def test_boundary_layer_parameter_validation(self):
        """Test boundary layer parameter validation."""
        # Zero boundary layer should be rejected or handled specially
        with pytest.raises((ValueError, AssertionError)):
            config = classical_smc_config()
            config.boundary_layer = 0.0
            ModularClassicalSMC(config=config)

        # Negative boundary layer should be rejected
        with pytest.raises((ValueError, AssertionError)):
            config = classical_smc_config()
            config.boundary_layer = -0.1
            ModularClassicalSMC(config=config)

    def test_boundary_layer_scaling_with_gains(self):
        """Test that boundary layer effectiveness scales with controller gains."""
        # High gain configuration
        high_gain_config = classical_smc_config()
        high_gain_config.gains = [10.0, 10.0, 10.0, 10.0, 100.0, 5.0]
        high_gain_config.boundary_layer = 0.1
        high_controller = ModularClassicalSMC(config=high_gain_config)

        # Low gain configuration
        low_gain_config = classical_smc_config()
        low_gain_config.gains = [1.0, 1.0, 1.0, 1.0, 10.0, 0.5]
        low_gain_config.boundary_layer = 0.1
        low_controller = ModularClassicalSMC(config=low_gain_config)

        # State inside boundary layer
        test_state = np.array([0.05, 0.05, 0.05, 0.0, 0.0, 0.0])

        result_high = high_controller.compute_control(test_state, {}, {})
        result_low = low_controller.compute_control(test_state, {}, {})

        control_high = result_high.get('control', result_high.get('u'))
        control_low = result_low.get('control', result_low.get('u'))

        if control_high is not None and control_low is not None:
            # Higher gains should generally produce larger control effort
            # even within boundary layer
            assert np.any(np.abs(control_high) >= np.abs(control_low) * 0.8)

    def test_boundary_layer_vs_switching_control(self):
        """Test difference between boundary layer and pure switching control."""
        # Very thin boundary layer (nearly switching)
        switching_config = classical_smc_config()
        switching_config.boundary_layer = 1e-6
        switching_controller = ModularClassicalSMC(config=switching_config)

        # Thick boundary layer (smooth)
        smooth_config = classical_smc_config()
        smooth_config.boundary_layer = 0.2
        smooth_controller = ModularClassicalSMC(config=smooth_config)

        # State close to surface
        test_state = np.array([0.05, 0.05, 0.05, 0.0, 0.0, 0.0])

        result_switching = switching_controller.compute_control(test_state, {}, {})
        result_smooth = smooth_controller.compute_control(test_state, {}, {})

        control_switching = result_switching.get('control', result_switching.get('u'))
        control_smooth = result_smooth.get('control', result_smooth.get('u'))

        if control_switching is not None and control_smooth is not None:
            # Smooth controller should have smaller control effort for this state
            assert np.any(np.abs(control_smooth) <= np.abs(control_switching))

    def test_boundary_layer_energy_considerations(self):
        """Test that boundary layer reduces high-frequency control energy."""
        config = classical_smc_config()
        config.boundary_layer = 0.1
        controller = ModularClassicalSMC(config=config)

        # Simulate rapid state changes near surface
        states = []
        base_state = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        for i in range(20):
            # Oscillate around surface
            perturbation = 0.05 * np.sin(i * np.pi / 2) * np.array([1, 1, 1, 0, 0, 0])
            states.append(base_state + perturbation)

        controls = []
        for state in states:
            result = controller.compute_control(state, {}, {})
            control = result.get('control', result.get('u'))
            if control is not None:
                controls.append(control)

        if len(controls) > 1:
            controls = np.array(controls)

            # Control changes should be bounded (no excessive switching)
            control_changes = np.diff(controls, axis=0)
            max_change = np.max(np.abs(control_changes))

            assert max_change < 50.0  # Bounded control rate changes