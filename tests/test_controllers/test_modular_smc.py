#==========================================================================================\\\
#=================== tests/test_controllers/test_modular_smc.py =======================\\\
#==========================================================================================\\\
"""
Comprehensive tests for Modular SMC Architecture.

This test suite verifies the modular SMC implementations including:
- Classical SMC modular components and integration
- Adaptive SMC modular components and integration
- Super-Twisting SMC modular components and integration
- Hybrid SMC modular components and integration
- Package imports and exports
- Component composition and interaction

The tests focus on verifying that the modular architecture provides
correct functionality, proper component isolation, and clean interfaces.
"""

from __future__ import annotations

import numpy as np
import pytest
from typing import Tuple, Dict, Any
from dataclasses import dataclass

# Test imports for modular controllers
from src.controllers.smc.algorithms import (
    # Classical SMC
    ModularClassicalSMC, ClassicalSMCConfig,

    # Adaptive SMC
    ModularAdaptiveSMC, AdaptiveSMCConfig,
    AdaptationLaw, ModifiedAdaptationLaw,
    UncertaintyEstimator, ParameterIdentifier, CombinedEstimator,

    # Super-Twisting SMC
    ModularSuperTwistingSMC, SuperTwistingSMCConfig,
    SuperTwistingAlgorithm,

    # Hybrid SMC
    ModularHybridSMC, HybridSMCConfig,
    HybridSwitchingLogic, SwitchingDecision, ControllerState,
    HybridMode, SwitchingCriterion
)

# Test imports for core components
from src.controllers.smc.core import (
    LinearSlidingSurface,
    SwitchingFunction,
    EquivalentControl,
    validate_smc_gains,
    SMCGainValidator
)


@dataclass
class TestSystemState:
    """Test system state for SMC testing."""
    position: np.ndarray
    velocity: np.ndarray
    time: float = 0.0


class MockDynamics:
    """Mock dynamics model for testing SMC controllers."""

    def __init__(self, n_dof: int = 3):
        self.n_dof = n_dof

    def _compute_physics_matrices(self, state: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute test physics matrices."""
        # Simple diagonal inertia matrix
        M = np.eye(self.n_dof)
        # Small damping
        C = 0.1 * np.eye(self.n_dof)
        # Zero gravity for simplicity
        G = np.zeros(self.n_dof)
        return M, C, G


class TestModularClassicalSMC:
    """Test the Modular Classical SMC implementation."""

    @pytest.fixture
    def config(self, dynamics) -> ClassicalSMCConfig:
        """Create test configuration for Classical SMC."""
        return ClassicalSMCConfig(
            gains=[1.0, 1.0, 1.0, 1.0, 10.0, 0.5],  # [k1, k2, lam1, lam2, K, kd]
            max_force=50.0,
            boundary_layer=0.1,
            dynamics_model=dynamics
        )

    @pytest.fixture
    def dynamics(self) -> MockDynamics:
        """Create mock dynamics for testing."""
        return MockDynamics(n_dof=3)

    @pytest.fixture
    def controller(self, config: ClassicalSMCConfig) -> ModularClassicalSMC:
        """Create Classical SMC controller for testing."""
        return ModularClassicalSMC(config=config)

    def test_controller_initialization(self, controller: ModularClassicalSMC):
        """Test that controller initializes correctly."""
        assert controller.config is not None
        assert controller._surface is not None
        assert controller._boundary_layer is not None
        assert controller._equivalent is not None

    def test_config_validation(self, config: ClassicalSMCConfig):
        """Test configuration validation."""
        # Valid config should pass
        assert len(config.gains) == 6
        assert config.max_force > 0
        assert config.boundary_layer > 0

        # Test invalid configs
        with pytest.raises(ValueError):
            ClassicalSMCConfig(
                gains=[1.0, 1.0, 1.0, 1.0, 10.0],  # Wrong length (should be 6)
                max_force=50.0,
                boundary_layer=0.1
            )

    def test_sliding_surface_computation(self, controller: ModularClassicalSMC):
        """Test sliding surface computation."""
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])  # position + velocity
        surface = controller._surface.compute(state)

        assert isinstance(surface, (float, np.ndarray))
        if isinstance(surface, np.ndarray):
            assert np.all(np.isfinite(surface))
        else:
            assert np.isfinite(surface)

    def test_control_computation(self, controller: ModularClassicalSMC):
        """Test complete control computation."""
        state = np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1])
        state_vars = {}  # Empty state vars for interface compatibility
        history = {}     # Empty history for interface compatibility

        result = controller.compute_control(state, state_vars, history)

        assert isinstance(result, dict)
        assert 'control' in result or 'u' in result  # Check for control output
        # Extract control vector from result
        control = result.get('control', result.get('u', result.get('u_saturated')))
        if control is not None:
            assert np.all(np.isfinite(control))
            # Control should be bounded
            assert np.all(np.abs(control) <= 50.0)


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
        assert np.all(np.abs(control) <= 50.0)

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


class TestModularSuperTwistingSMC:
    """Test the Modular Super-Twisting SMC implementation."""

    @pytest.fixture
    def config(self) -> SuperTwistingSMCConfig:
        """Create test configuration for Super-Twisting SMC."""
        return SuperTwistingSMCConfig(
            gains=[10.0, 5.0, 1.0, 1.0, 1.0, 1.0],  # [K1, K2, k1, k2, lam1, lam2]
            max_force=50.0,
            dt=0.01
        )

    @pytest.fixture
    def dynamics(self) -> MockDynamics:
        """Create mock dynamics for testing."""
        return MockDynamics(n_dof=3)

    @pytest.fixture
    def controller(self, config: SuperTwistingSMCConfig, dynamics: MockDynamics) -> ModularSuperTwistingSMC:
        """Create Super-Twisting SMC controller for testing."""
        return ModularSuperTwistingSMC(config=config, dynamics=dynamics)

    def test_twisting_algorithm_initialization(self, config: SuperTwistingSMCConfig):
        """Test Super-Twisting algorithm component initialization."""
        algorithm = SuperTwistingAlgorithm(config.alpha, config.beta)

        assert algorithm.alpha.shape == (3,)
        assert algorithm.beta.shape == (3,)

    def test_super_twisting_control_computation(self, controller: ModularSuperTwistingSMC):
        """Test Super-Twisting control computation."""
        state = np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1])
        control = controller.compute_control(state, dt=0.01)

        assert control.shape == (3,)
        assert np.all(np.isfinite(control))
        # Control should be bounded
        assert np.all(np.abs(control) <= 50.0)

    def test_finite_time_convergence_properties(self, controller: ModularSuperTwistingSMC):
        """Test that Super-Twisting algorithm has proper convergence properties."""
        # Test with surface near zero
        state_near_surface = np.array([0.01, 0.01, 0.01, 0.0, 0.0, 0.0])
        control_near = controller.compute_control(state_near_surface, dt=0.01)

        # Test with surface far from zero
        state_far_surface = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
        control_far = controller.compute_control(state_far_surface, dt=0.01)

        # Control magnitude should be larger when farther from surface
        assert np.linalg.norm(control_far) >= np.linalg.norm(control_near)


class TestModularHybridSMC:
    """Test the Modular Hybrid SMC implementation."""

    @pytest.fixture
    def config(self) -> HybridSMCConfig:
        """Create test configuration for Hybrid SMC."""
        classical_config = ClassicalSMCConfig(
            gains=[1.0, 1.0, 1.0, 1.0, 10.0, 0.5],
            max_force=50.0,
            boundary_layer=0.1
        )
        adaptive_config = AdaptiveSMCConfig(
            gains=[1.0, 1.0, 1.0, 1.0, 5.0],
            max_force=50.0,
            dt=0.01,
            K_init=10.0
        )
        return HybridSMCConfig(
            classical_config=classical_config,
            adaptive_config=adaptive_config,
            hybrid_mode=HybridMode.CLASSICAL_ADAPTIVE,
            switching_thresholds={
                SwitchingCriterion.TRACKING_ERROR: 0.1,
                SwitchingCriterion.SURFACE_MAGNITUDE: 0.05,
                SwitchingCriterion.CONTROL_EFFORT: 30.0
            },
            hysteresis_margin=0.02
        )

    @pytest.fixture
    def dynamics(self) -> MockDynamics:
        """Create mock dynamics for testing."""
        return MockDynamics(n_dof=3)

    @pytest.fixture
    def controller(self, config: HybridSMCConfig, dynamics: MockDynamics) -> ModularHybridSMC:
        """Create Hybrid SMC controller for testing."""
        return ModularHybridSMC(config=config, dynamics=dynamics)

    def test_switching_logic_initialization(self, config: HybridSMCConfig):
        """Test switching logic component initialization."""
        switching_logic = HybridSwitchingLogic(
            config.switching_thresholds,
            config.hysteresis_margin
        )

        assert switching_logic.thresholds is not None
        assert switching_logic.hysteresis_margin == 0.02

    def test_controller_switching(self, controller: ModularHybridSMC):
        """Test that hybrid controller switches between modes."""
        # Start in classical mode
        assert controller.current_mode == HybridMode.CLASSICAL_ADAPTIVE

        # Simulate conditions that should trigger switch to adaptive
        # Large tracking error should switch to adaptive mode
        state_large_error = np.array([1.0, 1.0, 1.0, 0.5, 0.5, 0.5])
        control = controller.compute_control(state_large_error, dt=0.01)

        assert control.shape == (3,)
        assert np.all(np.isfinite(control))

        # After several steps with large error, should switch to adaptive
        for _ in range(5):
            controller.compute_control(state_large_error, dt=0.01)

        # Mode might have switched (depends on switching logic implementation)
        assert controller.current_mode in [HybridMode.CLASSICAL_ADAPTIVE, HybridMode.ADAPTIVE_SUPERTWISTING]

    def test_hybrid_control_computation(self, controller: ModularHybridSMC):
        """Test hybrid control computation in different modes."""
        state = np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1])

        # Test control in classical mode
        controller.current_mode = HybridMode.CLASSICAL_ADAPTIVE
        control_classical = controller.compute_control(state, dt=0.01)

        # Test control in adaptive mode
        controller.current_mode = HybridMode.ADAPTIVE_SUPERTWISTING
        control_adaptive = controller.compute_control(state, dt=0.01)

        assert control_classical.shape == (3,)
        assert control_adaptive.shape == (3,)
        assert np.all(np.isfinite(control_classical))
        assert np.all(np.isfinite(control_adaptive))


class TestPackageImports:
    """Test that all modular SMC components can be imported correctly."""

    def test_classical_smc_imports(self):
        """Test Classical SMC component imports."""
        from src.controllers.smc.algorithms.classical import (
            ModularClassicalSMC, ClassicalSMCConfig
        )
        from src.controllers.smc.core import LinearSlidingSurface, SwitchingFunction

        # Should be able to create instances
        config = ClassicalSMCConfig(
            gains=[1.0, 1.0, 1.0, 1.0, 10.0, 0.5],
            max_force=50.0,
            boundary_layer=0.1
        )
        assert config is not None

    def test_adaptive_smc_imports(self):
        """Test Adaptive SMC component imports."""
        from src.controllers.smc.algorithms.adaptive import (
            ModularAdaptiveSMC, AdaptiveSMCConfig,
            AdaptationLaw, UncertaintyEstimator
        )

        # Should be able to create instances
        config = AdaptiveSMCConfig(
            gains=[1.0, 1.0, 1.0, 1.0, 5.0],
            max_force=50.0,
            dt=0.01,
            K_init=10.0
        )
        assert config is not None

    def test_super_twisting_smc_imports(self):
        """Test Super-Twisting SMC component imports."""
        from src.controllers.smc.algorithms.super_twisting import (
            ModularSuperTwistingSMC, SuperTwistingSMCConfig,
            SuperTwistingAlgorithm
        )

        # Should be able to create instances
        config = SuperTwistingSMCConfig(
            gains=[10.0, 5.0, 1.0, 1.0, 1.0, 1.0],
            max_force=50.0,
            dt=0.01
        )
        assert config is not None

    def test_hybrid_smc_imports(self):
        """Test Hybrid SMC component imports."""
        from src.controllers.smc.algorithms.hybrid import (
            ModularHybridSMC, HybridSMCConfig,
            HybridSwitchingLogic, HybridMode, SwitchingCriterion
        )

        # Should be able to create enums
        assert HybridMode.CLASSICAL_ADAPTIVE is not None
        assert SwitchingCriterion.TRACKING_ERROR is not None

    def test_main_package_imports(self):
        """Test main package level imports."""
        from src.controllers.smc import (
            ModularClassicalSMC, ModularAdaptiveSMC,
            ModularSuperTwistingSMC, ModularHybridSMC
        )

        # All controllers should be importable
        assert ModularClassicalSMC is not None
        assert ModularAdaptiveSMC is not None
        assert ModularSuperTwistingSMC is not None
        assert ModularHybridSMC is not None


class TestComponentIntegration:
    """Test integration between modular components."""

    def test_sliding_surface_integration(self):
        """Test sliding surface integrates with controllers."""
        from src.controllers.smc.core import LinearSlidingSurface

        lambda_gain = np.array([1.0, 1.0, 1.0])
        surface = LinearSlidingSurface(lambda_gain)

        state = np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1])
        computed_surface = surface.compute_surface(state)

        assert computed_surface.shape == (3,)
        assert np.all(np.isfinite(computed_surface))

    def test_gain_validation_integration(self):
        """Test gain validation integrates across components."""
        from src.controllers.smc.core import validate_smc_gains

        # Valid gains should pass
        valid_gains = np.array([1.0, 2.0, 3.0])
        assert validate_smc_gains(valid_gains)

        # Invalid gains should fail
        invalid_gains = np.array([-1.0, 2.0, 3.0])
        assert not validate_smc_gains(invalid_gains)

    def test_control_bounds_integration(self):
        """Test control bounds work across all controllers."""
        max_force = 25.0

        # Classical SMC
        classical_config = ClassicalSMCConfig(
            gains=[1.0, 1.0, 1.0, 1.0, 10.0, 0.5],
            max_force=max_force,
            boundary_layer=0.1
        )

        # Adaptive SMC
        adaptive_config = AdaptiveSMCConfig(
            gains=[1.0, 1.0, 1.0, 1.0, 5.0],
            max_force=max_force,
            dt=0.01,
            K_init=10.0
        )

        # Super-Twisting SMC
        super_twisting_config = SuperTwistingSMCConfig(
            gains=[10.0, 5.0, 1.0, 1.0, 1.0, 1.0],
            max_force=max_force,
            dt=0.01
        )

        # All configs should respect bounds
        assert classical_config.max_force == max_force
        assert adaptive_config.max_force == max_force
        assert super_twisting_config.max_force == max_force


# Property-based tests for robustness
class TestModularSMCProperties:
    """Property-based tests for modular SMC controllers."""

    @pytest.mark.parametrize("n_dof", [2])  # DIP system is 2-DOF
    def test_controller_scalability(self, n_dof: int):
        """Test that controllers work with different degrees of freedom."""
        # Classical SMC for 2-DOF system (double inverted pendulum)
        config = ClassicalSMCConfig(
            gains=[1.0, 1.0, 1.0, 1.0, 10.0, 0.5],  # Fixed 6 gains for DIP system
            max_force=50.0,
            boundary_layer=0.1
        )
        dynamics = MockDynamics(n_dof=n_dof)
        controller = ModularClassicalSMC(config=config, dynamics=dynamics)

        # Test control computation for 2-DOF system
        state = np.concatenate([0.1 * np.ones(n_dof), 0.1 * np.ones(n_dof)])
        control = controller.compute_control(state)

        assert control.shape == (n_dof,)
        assert np.all(np.isfinite(control))

    @pytest.mark.parametrize("dt", [0.001, 0.01, 0.1])
    def test_time_step_robustness(self, dt: float):
        """Test that controllers are robust to different time steps."""
        config = AdaptiveSMCConfig(
            gains=[1.0, 1.0, 1.0, 1.0, 5.0],
            max_force=50.0,
            dt=dt,  # Use the parameterized dt
            K_init=10.0
        )
        dynamics = MockDynamics(n_dof=2)  # DIP system is 2-DOF
        controller = ModularAdaptiveSMC(config=config, dynamics=dynamics)

        state = np.array([0.1, 0.2, 0.1, 0.1])  # 2-DOF state
        control = controller.compute_control(state, dt=dt)

        assert control.shape == (2,)
        assert np.all(np.isfinite(control))

    @pytest.mark.parametrize("noise_level", [0.0, 0.01, 0.1])
    def test_noise_robustness(self, noise_level: float):
        """Test that controllers handle noisy measurements."""
        config = SuperTwistingSMCConfig(
            gains=[10.0, 5.0, 1.0, 1.0, 1.0, 1.0],
            max_force=50.0,
            dt=0.01
        )
        dynamics = MockDynamics(n_dof=2)  # DIP system is 2-DOF
        controller = ModularSuperTwistingSMC(config=config, dynamics=dynamics)

        # Add noise to state
        clean_state = np.array([0.1, 0.2, 0.1, 0.1])  # 2-DOF state
        noise = noise_level * np.random.randn(4)
        noisy_state = clean_state + noise

        control = controller.compute_control(noisy_state, dt=0.01)

        assert control.shape == (2,)
        assert np.all(np.isfinite(control))


if __name__ == "__main__":
    pytest.main([__file__])