#==========================================================================================\\\
#======= tests/test_controllers/smc/algorithms/adaptive/test_modular_adaptive_smc.py =======\\\
#==========================================================================================\\\
"""
Tests for Modular Adaptive SMC implementation.

This test suite focuses specifically on the Adaptive SMC modular components:
- Adaptation law functionality
- Uncertainty estimation
- Parameter identification
- Online adaptation behavior
"""

from __future__ import annotations

import numpy as np
import pytest

from tests.test_controllers.smc.test_fixtures import (
    MockDynamics, TestSystemState, adaptive_smc_config,
    validate_control_output, compute_tracking_error
)

from src.controllers.smc.algorithms import (
    ModularAdaptiveSMC, AdaptiveSMCConfig,
    AdaptationLaw, ModifiedAdaptationLaw,
    UncertaintyEstimator, ParameterIdentifier, CombinedEstimator
)


class TestModularAdaptiveSMC:
    """Test the Modular Adaptive SMC implementation."""

    @pytest.fixture
    def config(self) -> AdaptiveSMCConfig:
        """Create test configuration for Adaptive SMC."""
        return AdaptiveSMCConfig(
            gains=[1.0, 1.0, 1.0, 1.0, 5.0],  # [k1, k2, lam1, lam2, gamma]
            max_force=50.0,
            dt=0.01,
            K_init=10.0
        )

    @pytest.fixture
    def dynamics(self) -> MockDynamics:
        """Create mock dynamics for testing."""
        return MockDynamics(n_dof=3)

    @pytest.fixture
    def controller(self, config: AdaptiveSMCConfig, dynamics: MockDynamics) -> ModularAdaptiveSMC:
        """Create Adaptive SMC controller for testing."""
        return ModularAdaptiveSMC(config=config, dynamics=dynamics)

    def test_controller_initialization(self, controller: ModularAdaptiveSMC):
        """Test that adaptive controller initializes correctly."""
        assert controller.config is not None
        assert hasattr(controller, 'uncertainty_estimator')
        assert hasattr(controller, 'adaptation_law')

    def test_adaptation_law_initialization(self, config: AdaptiveSMCConfig):
        """Test adaptation law component initialization."""
        adaptation_law = AdaptationLaw(config.adaptation_rate, config.uncertainty_bound)

        assert adaptation_law.adaptation_rate.shape == (3,)
        assert adaptation_law.uncertainty_bound == 10.0

    def test_uncertainty_estimator(self, config: AdaptiveSMCConfig):
        """Test uncertainty estimation component."""
        estimator = UncertaintyEstimator(config.initial_estimates)

        # Test initial state
        assert estimator.current_estimates.shape == (3,)

        # Test update
        sliding_surface = np.array([0.1, 0.2, 0.3])
        adaptation_rate = config.adaptation_rate
        updated = estimator.update_estimates(sliding_surface, adaptation_rate, dt=0.01)

        assert updated.shape == (3,)
        assert np.all(np.isfinite(updated))

    def test_adaptive_control_computation(self, controller: ModularAdaptiveSMC):
        """Test adaptive control computation."""
        state = np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1])
        control = controller.compute_control(state, dt=0.01)

        assert control.shape == (3,)
        assert np.all(np.isfinite(control))
        # Control should be bounded
        assert validate_control_output(control, max_force=50.0)

    def test_parameter_adaptation(self, controller: ModularAdaptiveSMC):
        """Test that parameters adapt over time."""
        state = np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1])

        # Get initial estimates
        initial_estimates = controller.uncertainty_estimator.current_estimates.copy()

        # Run several control steps
        for _ in range(10):
            controller.compute_control(state, dt=0.01)

        # Estimates should have changed
        final_estimates = controller.uncertainty_estimator.current_estimates
        assert not np.allclose(initial_estimates, final_estimates)

    def test_adaptation_stability(self, controller: ModularAdaptiveSMC):
        """Test that adaptation remains stable."""
        states = [
            np.array([0.1, 0.0, 0.0, 0.1, 0.0, 0.0]),
            np.array([0.0, 0.1, 0.0, 0.0, 0.1, 0.0]),
            np.array([0.0, 0.0, 0.1, 0.0, 0.0, 0.1])
        ]

        for state in states:
            for _ in range(5):
                control = controller.compute_control(state, dt=0.01)
                # Parameters should remain bounded
                estimates = controller.uncertainty_estimator.current_estimates
                assert np.all(np.isfinite(estimates))
                assert np.all(np.abs(estimates) < 1000)  # Reasonable bound

    def test_convergence_properties(self, controller: ModularAdaptiveSMC):
        """Test convergence properties of adaptation."""
        # Create a trajectory with consistent error
        trajectory_length = 50
        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])

        estimate_history = []

        for i in range(trajectory_length):
            control = controller.compute_control(state, dt=0.01)
            estimates = controller.uncertainty_estimator.current_estimates.copy()
            estimate_history.append(estimates)

            # Simulate some dynamics (simplified)
            state[:3] += 0.01 * state[3:6]  # Position integration

        estimate_history = np.array(estimate_history)

        # Check that estimates converge (variance decreases over time)
        early_var = np.var(estimate_history[:10], axis=0)
        late_var = np.var(estimate_history[-10:], axis=0)

        # At least one parameter should show reduced variance (convergence)
        assert np.any(late_var < early_var)


class TestAdaptationComponents:
    """Test individual adaptation components."""

    def test_modified_adaptation_law(self):
        """Test modified adaptation law implementation."""
        try:
            adaptation_rate = np.array([1.0, 1.0, 1.0])
            uncertainty_bound = 5.0
            modified_law = ModifiedAdaptationLaw(adaptation_rate, uncertainty_bound)

            sliding_surface = np.array([0.1, 0.2, 0.3])
            dt = 0.01

            adaptation = modified_law.compute_adaptation(sliding_surface, dt)
            assert np.all(np.isfinite(adaptation))
        except (ImportError, NotImplementedError):
            pytest.skip("ModifiedAdaptationLaw not implemented")

    def test_parameter_identifier(self):
        """Test parameter identification component."""
        try:
            identifier = ParameterIdentifier(n_params=3)

            # Test identification update
            measurement = np.array([1.0, 2.0, 3.0])
            regressor = np.eye(3)

            identified = identifier.update_parameters(measurement, regressor)
            assert np.all(np.isfinite(identified))
        except (ImportError, NotImplementedError):
            pytest.skip("ParameterIdentifier not implemented")

    def test_combined_estimator(self):
        """Test combined uncertainty and parameter estimator."""
        try:
            estimator = CombinedEstimator(
                uncertainty_params=3,
                system_params=2
            )

            sliding_surface = np.array([0.1, 0.2, 0.3])
            system_output = np.array([1.0, 2.0])

            uncertainty_est, param_est = estimator.update_combined(
                sliding_surface, system_output, dt=0.01
            )

            assert np.all(np.isfinite(uncertainty_est))
            assert np.all(np.isfinite(param_est))
        except (ImportError, NotImplementedError):
            pytest.skip("CombinedEstimator not implemented")


class TestAdaptationScenarios:
    """Test adaptation in different scenarios."""

    def test_constant_disturbance_adaptation(self, adaptive_smc_config: AdaptiveSMCConfig):
        """Test adaptation to constant disturbances."""
        dynamics = MockDynamics(n_dof=3)
        controller = ModularAdaptiveSMC(config=adaptive_smc_config, dynamics=dynamics)

        # Simulate constant disturbance
        disturbance = np.array([1.0, 0.5, 0.2])
        state = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        initial_estimates = controller.uncertainty_estimator.current_estimates.copy()

        # Apply consistent disturbance pattern
        for _ in range(30):
            # Add disturbance effect to state
            state[:3] += 0.001 * disturbance
            control = controller.compute_control(state, dt=0.01)

        final_estimates = controller.uncertainty_estimator.current_estimates

        # Estimates should have adapted to compensate for disturbance
        assert not np.allclose(initial_estimates, final_estimates, rtol=1e-3)

    def test_time_varying_disturbance_adaptation(self, adaptive_smc_config: AdaptiveSMCConfig):
        """Test adaptation to time-varying disturbances."""
        dynamics = MockDynamics(n_dof=3)
        controller = ModularAdaptiveSMC(config=adaptive_smc_config, dynamics=dynamics)

        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])

        # Time-varying disturbance
        for i in range(25):
            t = i * 0.01
            disturbance = np.array([np.sin(t), np.cos(t), 0.5 * np.sin(2*t)])

            # Apply time-varying disturbance
            state[:3] += 0.001 * disturbance
            control = controller.compute_control(state, dt=0.01)

            # Parameters should adapt continuously
            estimates = controller.uncertainty_estimator.current_estimates
            assert np.all(np.isfinite(estimates))
            assert np.all(np.abs(estimates) < 100)  # Should remain bounded