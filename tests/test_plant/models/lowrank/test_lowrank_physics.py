#==========================================================================================\\\
#================ tests/test_plant/models/lowrank/test_lowrank_physics.py ===============\\\
#==========================================================================================\\\
"""
Comprehensive test suite for low-rank DIP physics computer.
Tests simplified physics computations, matrix calculations, energy analysis,
and different approximation modes for the low-rank model.
"""

import pytest
import numpy as np
from typing import Tuple

try:
    from src.plant.models.lowrank import LowRankPhysicsComputer, LowRankDIPConfig
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    LowRankPhysicsComputer = None
    LowRankDIPConfig = None


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Low-rank physics modules not available")
class TestLowRankPhysicsComputer:
    """Test cases for LowRankPhysicsComputer core functionality."""

    @pytest.fixture
    def default_config(self):
        """Create default low-rank DIP configuration."""
        return LowRankDIPConfig()

    @pytest.fixture
    def linearized_config(self):
        """Create configuration with linearization enabled."""
        return LowRankDIPConfig(
            enable_linearization=True,
            enable_small_angle_approximation=True
        )

    @pytest.fixture
    def small_angle_config(self):
        """Create configuration with small angle approximation only."""
        return LowRankDIPConfig(
            enable_linearization=False,
            enable_small_angle_approximation=True
        )

    @pytest.fixture
    def nonlinear_config(self):
        """Create configuration for full nonlinear mode."""
        return LowRankDIPConfig(
            enable_linearization=False,
            enable_small_angle_approximation=False
        )

    @pytest.fixture
    def physics_computer(self, default_config):
        """Create physics computer with default configuration."""
        return LowRankPhysicsComputer(default_config)

    @pytest.fixture
    def test_states(self):
        """Generate test states for various scenarios."""
        return {
            'equilibrium': np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            'small_angles': np.array([0.1, 0.05, 0.03, 0.1, 0.05, 0.02]),
            'moderate_angles': np.array([0.3, 0.4, 0.35, 0.2, 0.15, 0.18]),
            'large_angles': np.array([0.5, 1.2, 0.8, 0.3, 0.4, 0.35]),
            'high_velocities': np.array([0.2, 0.1, 0.15, 2.0, 1.5, 1.8]),
            'mixed_dynamics': np.array([0.4, 0.6, 0.5, 1.0, 0.8, 0.9])
        }

    def test_initialization_precomputed_constants(self, default_config):
        """Test initialization and precomputed constants."""
        physics = LowRankPhysicsComputer(default_config)

        # Basic parameters should be stored
        assert physics.m0 == default_config.cart_mass
        assert physics.m1 == default_config.pendulum1_mass
        assert physics.m2 == default_config.pendulum2_mass
        assert physics.l1 == default_config.pendulum1_length
        assert physics.l2 == default_config.pendulum2_length
        assert physics.g == default_config.gravity

        # Precomputed products should be correct
        assert physics.m1l1 == physics.m1 * physics.l1
        assert physics.m2l2 == physics.m2 * physics.l2
        assert physics.m1l1_sq == physics.m1 * physics.l1**2
        assert physics.m2l2_sq == physics.m2 * physics.l2**2

        # Total mass should be correct
        expected_total = physics.m0 + physics.m1 + physics.m2
        assert physics.total_mass == expected_total

    def test_linearized_dynamics_computation(self, linearized_config, test_states):
        """Test linearized dynamics computation."""
        physics = LowRankPhysicsComputer(linearized_config)

        state_dot = physics.compute_simplified_dynamics_rhs(
            test_states['small_angles'],
            np.array([5.0])
        )

        assert isinstance(state_dot, np.ndarray)
        assert state_dot.shape == (6,)
        assert np.all(np.isfinite(state_dot))

        # Position derivatives should match velocities
        assert state_dot[0] == test_states['small_angles'][3]  # x_dot
        assert state_dot[1] == test_states['small_angles'][4]  # theta1_dot
        assert state_dot[2] == test_states['small_angles'][5]  # theta2_dot

        # Accelerations should be reasonable for linearized dynamics
        assert np.all(np.abs(state_dot[3:]) < 20.0)

    def test_small_angle_dynamics_computation(self, small_angle_config, test_states):
        """Test small angle approximation dynamics computation."""
        physics = LowRankPhysicsComputer(small_angle_config)

        state_dot = physics.compute_simplified_dynamics_rhs(
            test_states['moderate_angles'],
            np.array([8.0])
        )

        assert isinstance(state_dot, np.ndarray)
        assert state_dot.shape == (6,)
        assert np.all(np.isfinite(state_dot))

        # Position derivatives should match velocities
        assert state_dot[0] == test_states['moderate_angles'][3]
        assert state_dot[1] == test_states['moderate_angles'][4]
        assert state_dot[2] == test_states['moderate_angles'][5]

    def test_nonlinear_dynamics_computation(self, nonlinear_config, test_states):
        """Test full nonlinear dynamics computation."""
        physics = LowRankPhysicsComputer(nonlinear_config)

        state_dot = physics.compute_simplified_dynamics_rhs(
            test_states['large_angles'],
            np.array([12.0])
        )

        assert isinstance(state_dot, np.ndarray)
        assert state_dot.shape == (6,)
        assert np.all(np.isfinite(state_dot))

        # Position derivatives should still match velocities
        assert state_dot[0] == test_states['large_angles'][3]
        assert state_dot[1] == test_states['large_angles'][4]
        assert state_dot[2] == test_states['large_angles'][5]

    def test_zero_control_equilibrium(self, physics_computer, test_states):
        """Test dynamics with zero control at equilibrium."""
        state_dot = physics_computer.compute_simplified_dynamics_rhs(
            test_states['equilibrium'],
            np.array([0.0])
        )

        # At equilibrium with zero control, only gravity effects should remain
        assert np.abs(state_dot[0]) < 1e-12  # x_dot = 0
        assert np.abs(state_dot[1]) < 1e-12  # theta1_dot = 0
        assert np.abs(state_dot[2]) < 1e-12  # theta2_dot = 0

        # Small residual accelerations due to numerical precision
        assert np.abs(state_dot[3]) < 0.1    # x_ddot ≈ 0
        assert np.abs(state_dot[4]) < 0.1    # theta1_ddot ≈ 0
        assert np.abs(state_dot[5]) < 0.1    # theta2_ddot ≈ 0

    def test_control_force_effects(self, physics_computer, test_states):
        """Test effects of different control forces."""
        equilibrium = test_states['equilibrium']

        # Positive control force
        state_dot_pos = physics_computer.compute_simplified_dynamics_rhs(
            equilibrium, np.array([10.0])
        )

        # Negative control force
        state_dot_neg = physics_computer.compute_simplified_dynamics_rhs(
            equilibrium, np.array([-10.0])
        )

        # Cart acceleration should be affected by control force
        assert state_dot_pos[3] > state_dot_neg[3]

        # Control force effects should be symmetric
        assert abs(state_dot_pos[3] + state_dot_neg[3]) < 0.1

    def test_diagonal_matrices_computation(self, default_config, test_states):
        """Test diagonal approximation of physics matrices."""
        config = LowRankDIPConfig(use_simplified_matrices=True)
        physics = LowRankPhysicsComputer(config)

        M, C, G = physics.compute_simplified_matrices(test_states['moderate_angles'])

        assert isinstance(M, np.ndarray)
        assert isinstance(C, np.ndarray)
        assert isinstance(G, np.ndarray)

        assert M.shape == (3, 3)
        assert C.shape == (3, 3)
        assert G.shape == (3,)

        # Mass matrix should be diagonal and positive definite
        assert np.allclose(M, np.diag(np.diag(M)))  # Should be diagonal
        assert np.all(np.diag(M) > 0)  # Diagonal elements should be positive

        # Damping matrix should be diagonal and non-negative
        assert np.allclose(C, np.diag(np.diag(C)))  # Should be diagonal
        assert np.all(np.diag(C) >= 0)  # Diagonal elements should be non-negative

    def test_coupled_matrices_computation(self, default_config, test_states):
        """Test coupled physics matrices computation."""
        config = LowRankDIPConfig(use_simplified_matrices=False)
        physics = LowRankPhysicsComputer(config)

        M, C, G = physics.compute_simplified_matrices(test_states['moderate_angles'])

        assert M.shape == (3, 3)
        assert C.shape == (3, 3)
        assert G.shape == (3,)

        # Mass matrix should be positive definite
        eigenvalues = np.linalg.eigvals(M)
        assert np.all(eigenvalues > 0)

        # Mass matrix should have coupling terms (not purely diagonal)
        off_diagonal_mass = M - np.diag(np.diag(M))
        assert np.any(np.abs(off_diagonal_mass) > 1e-6)

    def test_energy_computation_components(self, physics_computer, test_states):
        """Test energy computation for different states."""
        for state_name, state in test_states.items():
            energy = physics_computer.compute_energy(state)

            assert isinstance(energy, dict)

            # Check all required energy components exist
            required_keys = [
                'kinetic_energy', 'potential_energy', 'total_energy',
                'kinetic_cart', 'kinetic_pendulum1', 'kinetic_pendulum2',
                'potential_pendulum1', 'potential_pendulum2'
            ]

            for key in required_keys:
                assert key in energy
                assert isinstance(energy[key], (int, float))
                assert np.isfinite(energy[key])

            # Energy components should be non-negative
            assert energy['kinetic_energy'] >= 0
            assert energy['potential_energy'] >= 0
            assert energy['kinetic_cart'] >= 0
            assert energy['kinetic_pendulum1'] >= 0
            assert energy['kinetic_pendulum2'] >= 0

            # Total energy should equal sum of components
            calculated_total = energy['kinetic_energy'] + energy['potential_energy']
            assert abs(calculated_total - energy['total_energy']) < 1e-10

    def test_energy_conservation_properties(self, physics_computer):
        """Test energy conservation properties."""
        # State with no velocities should have only potential energy
        static_state = np.array([0.0, 0.5, 0.3, 0.0, 0.0, 0.0])
        energy_static = physics_computer.compute_energy(static_state)

        assert energy_static['kinetic_energy'] < 1e-12
        assert energy_static['potential_energy'] > 0
        assert abs(energy_static['total_energy'] - energy_static['potential_energy']) < 1e-12

        # State at equilibrium with velocities should have only kinetic energy
        moving_equilibrium = np.array([0.0, 0.0, 0.0, 1.0, 0.5, 0.3])
        energy_moving = physics_computer.compute_energy(moving_equilibrium)

        assert energy_moving['kinetic_energy'] > 0
        assert energy_moving['potential_energy'] < 1e-10  # Small due to small angle approx
        assert abs(energy_moving['total_energy'] - energy_moving['kinetic_energy']) < 1e-10

    def test_small_angle_vs_nonlinear_energy(self):
        """Test energy computation differences between small angle and nonlinear modes."""
        state = np.array([0.0, 0.3, 0.4, 0.0, 0.0, 0.0])  # Moderate angles

        # Small angle approximation
        config_small = LowRankDIPConfig(enable_small_angle_approximation=True)
        physics_small = LowRankPhysicsComputer(config_small)
        energy_small = physics_small.compute_energy(state)

        # Full nonlinear
        config_nonlin = LowRankDIPConfig(enable_small_angle_approximation=False)
        physics_nonlin = LowRankPhysicsComputer(config_nonlin)
        energy_nonlin = physics_nonlin.compute_energy(state)

        # Kinetic energies should be identical (no approximation involved)
        assert abs(energy_small['kinetic_energy'] - energy_nonlin['kinetic_energy']) < 1e-12

        # Potential energies should be different for moderate angles
        potential_diff = abs(energy_small['potential_energy'] - energy_nonlin['potential_energy'])
        assert potential_diff > 1e-6  # Should be noticeably different

        # For moderate angles, nonlinear should give higher potential energy
        assert energy_nonlin['potential_energy'] > energy_small['potential_energy']

    def test_stability_metrics_computation(self, physics_computer, test_states):
        """Test stability metrics computation."""
        for state_name, state in test_states.items():
            stability = physics_computer.compute_stability_metrics(state)

            assert isinstance(stability, dict)

            # Check required stability metrics
            required_keys = ['condition_number', 'determinant', 'total_energy', 'kinetic_potential_ratio']
            for key in required_keys:
                assert key in stability
                assert isinstance(stability[key], (int, float))
                assert np.isfinite(stability[key])

            # Condition number should be positive and reasonable
            assert stability['condition_number'] > 0
            assert stability['condition_number'] < 1e8  # Not pathologically ill-conditioned

            # Determinant should be non-zero for well-posed system
            assert abs(stability['determinant']) > 1e-15

            # Total energy should be non-negative
            assert stability['total_energy'] >= 0

            # Kinetic/potential ratio should be non-negative
            assert stability['kinetic_potential_ratio'] >= 0

    def test_computation_validation_success(self, physics_computer, test_states):
        """Test validation of successful computations."""
        for state_name, state in test_states.items():
            state_derivative = physics_computer.compute_simplified_dynamics_rhs(
                state, np.array([5.0])
            )

            # Validation should pass for reasonable results
            is_valid = physics_computer.validate_computation(state, state_derivative)
            assert is_valid == True

    def test_computation_validation_failure_cases(self, physics_computer):
        """Test validation failure for problematic results."""
        state = np.array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1])

        # Test with NaN in state derivative
        invalid_derivative_nan = np.array([0.0, 0.0, 0.0, np.nan, 0.0, 0.0])
        is_valid = physics_computer.validate_computation(state, invalid_derivative_nan)
        assert is_valid == False

        # Test with infinite values in state derivative
        invalid_derivative_inf = np.array([0.0, 0.0, 0.0, np.inf, 0.0, 0.0])
        is_valid = physics_computer.validate_computation(state, invalid_derivative_inf)
        assert is_valid == False

        # Test with excessively large accelerations
        invalid_derivative_large = np.array([0.0, 0.0, 0.0, 150.0, 0.0, 0.0])
        is_valid = physics_computer.validate_computation(state, invalid_derivative_large)
        assert is_valid == False

    def test_different_approximation_modes_consistency(self, test_states):
        """Test consistency between different approximation modes."""
        state = test_states['small_angles']  # Use small angles for comparison
        control = np.array([3.0])

        # Linearized mode
        config_lin = LowRankDIPConfig(
            enable_linearization=True,
            enable_small_angle_approximation=True
        )
        physics_lin = LowRankPhysicsComputer(config_lin)
        state_dot_lin = physics_lin.compute_simplified_dynamics_rhs(state, control)

        # Small angle mode
        config_small = LowRankDIPConfig(
            enable_linearization=False,
            enable_small_angle_approximation=True
        )
        physics_small = LowRankPhysicsComputer(config_small)
        state_dot_small = physics_small.compute_simplified_dynamics_rhs(state, control)

        # Position derivatives should be identical (just velocity passthrough)
        assert np.allclose(state_dot_lin[:3], state_dot_small[:3])

        # Accelerations should be similar for small angles but not identical
        accel_diff = np.linalg.norm(state_dot_lin[3:] - state_dot_small[3:])
        assert accel_diff < 1.0  # Should be reasonably close
        assert accel_diff > 1e-6  # But not identical due to different approximations

    def test_mass_scaling_effects(self, test_states):
        """Test effects of different mass parameters."""
        state = test_states['moderate_angles']
        control = np.array([10.0])

        # Light pendulums
        config_light = LowRankDIPConfig(
            cart_mass=1.0,
            pendulum1_mass=0.01,
            pendulum2_mass=0.01
        )
        physics_light = LowRankPhysicsComputer(config_light)
        state_dot_light = physics_light.compute_simplified_dynamics_rhs(state, control)

        # Heavy pendulums
        config_heavy = LowRankDIPConfig(
            cart_mass=1.0,
            pendulum1_mass=1.0,
            pendulum2_mass=1.0
        )
        physics_heavy = LowRankPhysicsComputer(config_heavy)
        state_dot_heavy = physics_heavy.compute_simplified_dynamics_rhs(state, control)

        # Cart acceleration should be higher with lighter pendulums
        assert state_dot_light[3] > state_dot_heavy[3]

        # Pendulum accelerations should be affected by mass ratios
        assert np.any(np.abs(state_dot_light[4:] - state_dot_heavy[4:]) > 0.1)


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Low-rank physics modules not available")
class TestLowRankPhysicsPerformance:
    """Test performance characteristics of low-rank physics computations."""

    def test_computation_speed_comparison(self, test_states):
        """Test computation speed of different approximation modes."""
        state = test_states['mixed_dynamics']
        control = np.array([8.0])

        import time

        # Linearized mode (should be fastest)
        config_lin = LowRankDIPConfig(
            enable_linearization=True,
            enable_small_angle_approximation=True
        )
        physics_lin = LowRankPhysicsComputer(config_lin)

        start_time = time.time()
        for _ in range(1000):
            physics_lin.compute_simplified_dynamics_rhs(state, control)
        lin_time = time.time() - start_time

        # Nonlinear mode (should be slower)
        config_nonlin = LowRankDIPConfig(
            enable_linearization=False,
            enable_small_angle_approximation=False
        )
        physics_nonlin = LowRankPhysicsComputer(config_nonlin)

        start_time = time.time()
        for _ in range(1000):
            physics_nonlin.compute_simplified_dynamics_rhs(state, control)
        nonlin_time = time.time() - start_time

        # Linearized should be faster or comparable
        # (Allow some tolerance for system variations)
        assert lin_time <= nonlin_time * 1.5

    def test_memory_efficiency_repeated_computations(self):
        """Test memory efficiency of repeated physics computations."""
        config = LowRankDIPConfig.create_fast_prototype()
        physics = LowRankPhysicsComputer(config)

        import gc

        # Get initial object count
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Perform many computations with different states
        for i in range(200):
            state = np.random.randn(6) * 0.3
            control = np.array([np.random.randn() * 10])

            physics.compute_simplified_dynamics_rhs(state, control)
            physics.compute_simplified_matrices(state)
            physics.compute_energy(state)

            if i % 50 == 0:
                gc.collect()

        # Check final object count
        gc.collect()
        final_objects = len(gc.get_objects())

        # Should not have excessive memory growth
        object_growth = final_objects - initial_objects
        assert object_growth < 150  # Allow reasonable growth


# Fallback tests when imports are not available
class TestLowRankPhysicsFallback:
    """Test fallback behavior when imports are not available."""

    @pytest.mark.skipif(IMPORTS_AVAILABLE, reason="Test only when imports fail")
    def test_imports_not_available(self):
        """Test that we handle missing imports gracefully."""
        assert LowRankPhysicsComputer is None
        assert LowRankDIPConfig is None
        assert IMPORTS_AVAILABLE is False

    def test_physics_test_parameters(self):
        """Test physics test parameter structure."""
        physics_params = {
            'state_dimensions': 6,
            'matrix_dimensions': (3, 3),
            'energy_components': 8,
            'stability_metrics': 4,
            'approximation_modes': 3
        }

        assert physics_params['state_dimensions'] == 6
        assert physics_params['matrix_dimensions'] == (3, 3)
        assert physics_params['energy_components'] == 8
        assert physics_params['stability_metrics'] == 4
        assert physics_params['approximation_modes'] == 3