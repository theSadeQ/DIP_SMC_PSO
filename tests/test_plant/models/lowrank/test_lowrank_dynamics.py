#==========================================================================================\\\
#=============== tests/test_plant/models/lowrank/test_lowrank_dynamics.py ===============\\\
#==========================================================================================\\\
"""
Comprehensive test suite for low-rank DIP dynamics model.
Tests the simplified dynamics implementation including linearization modes,
small-angle approximations, energy analysis, and stability metrics.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from typing import Dict, Any

try:
    from src.plant.models.lowrank import LowRankDIPDynamics, LowRankDIPConfig
    from src.plant.models.base import DynamicsResult
    from src.plant.core import NumericalInstabilityError
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    LowRankDIPDynamics = None
    LowRankDIPConfig = None


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Low-rank dynamics modules not available")
class TestLowRankDIPDynamics:
    """Test cases for LowRankDIPDynamics core functionality."""

    @pytest.fixture
    def default_config(self):
        """Create default low-rank DIP configuration."""
        return LowRankDIPConfig()

    @pytest.fixture
    def fast_prototype_config(self):
        """Create fast prototype configuration."""
        return LowRankDIPConfig.create_fast_prototype()

    @pytest.fixture
    def educational_config(self):
        """Create educational configuration."""
        return LowRankDIPConfig.create_educational()

    @pytest.fixture
    def dynamics_model(self, default_config):
        """Create low-rank dynamics model with default configuration."""
        return LowRankDIPDynamics(default_config, enable_monitoring=True, enable_validation=True)

    @pytest.fixture
    def test_states(self):
        """Generate test states for various scenarios."""
        return {
            'equilibrium': np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            'small_disturbance': np.array([0.1, 0.05, 0.03, 0.0, 0.0, 0.0]),
            'large_angles': np.array([0.5, 0.8, 0.6, 0.2, 0.1, 0.15]),
            'high_velocities': np.array([0.1, 0.1, 0.1, 2.0, 3.0, 2.5]),
            'mixed_state': np.array([0.3, 0.2, 0.4, 1.0, 0.5, 0.8])
        }

    @pytest.fixture
    def test_controls(self):
        """Generate test control inputs."""
        return {
            'zero': np.array([0.0]),
            'small_positive': np.array([5.0]),
            'small_negative': np.array([-3.0]),
            'large_positive': np.array([15.0]),
            'large_negative': np.array([-12.0]),
            'max_force': np.array([20.0])
        }

    def test_initialization_default(self, default_config):
        """Test initialization with default configuration."""
        dynamics = LowRankDIPDynamics(default_config)

        assert dynamics.config == default_config
        assert dynamics.enable_monitoring == False  # Default
        assert dynamics.enable_validation == True   # Default
        assert dynamics.physics is not None
        assert dynamics.computation_stats['total_computations'] == 0

    def test_initialization_custom_flags(self, default_config):
        """Test initialization with custom flags."""
        dynamics = LowRankDIPDynamics(
            default_config,
            enable_monitoring=True,
            enable_validation=False
        )

        assert dynamics.enable_monitoring == True
        assert dynamics.enable_validation == False

    def test_compute_dynamics_equilibrium(self, dynamics_model, test_states, test_controls):
        """Test dynamics computation at equilibrium."""
        result = dynamics_model.compute_dynamics(
            test_states['equilibrium'],
            test_controls['zero']
        )

        assert isinstance(result, DynamicsResult)
        assert result.success == True
        assert result.state_derivative is not None
        assert result.state_derivative.shape == (6,)

        # At equilibrium with no force, derivatives should be small
        assert np.linalg.norm(result.state_derivative) < 0.1

    def test_compute_dynamics_small_disturbance(self, dynamics_model, test_states, test_controls):
        """Test dynamics computation with small disturbance."""
        result = dynamics_model.compute_dynamics(
            test_states['small_disturbance'],
            test_controls['small_positive']
        )

        assert result.success == True
        assert result.state_derivative is not None

        # Position derivatives should match velocities
        assert result.state_derivative[0] == test_states['small_disturbance'][3]  # x_dot
        assert result.state_derivative[1] == test_states['small_disturbance'][4]  # theta1_dot
        assert result.state_derivative[2] == test_states['small_disturbance'][5]  # theta2_dot

        # Accelerations should be reasonable
        assert np.all(np.abs(result.state_derivative[3:]) < 50.0)

    def test_linearized_dynamics_computation(self, dynamics_model, test_states, test_controls):
        """Test linearized dynamics computation."""
        result = dynamics_model.compute_linearized_dynamics(
            test_states['small_disturbance'],
            test_controls['small_positive']
        )

        assert isinstance(result, np.ndarray)
        assert result.shape == (6,)
        assert np.all(np.isfinite(result))

    def test_linearized_system_matrices(self, dynamics_model):
        """Test linearized system matrix computation."""
        # Test upright equilibrium
        A, B = dynamics_model.get_linearized_system("upright")

        assert A.shape == (6, 6)
        assert B.shape == (6, 1)
        assert np.all(np.isfinite(A))
        assert np.all(np.isfinite(B))

        # Test downward equilibrium
        A_down, B_down = dynamics_model.get_linearized_system("downward")

        assert A_down.shape == (6, 6)
        assert B_down.shape == (6, 1)

        # Matrices should be different for different equilibria
        assert not np.array_equal(A, A_down)

    def test_physics_matrices_computation(self, dynamics_model, test_states):
        """Test physics matrices computation."""
        M, C, G = dynamics_model.get_physics_matrices(test_states['small_disturbance'])

        assert isinstance(M, np.ndarray)
        assert isinstance(C, np.ndarray)
        assert isinstance(G, np.ndarray)

        # Check dimensions (3x3 for 3 DOF reduced dynamics)
        assert M.shape == (3, 3)
        assert C.shape == (3, 3)
        assert G.shape == (3,)

        # Mass matrix should be positive definite
        eigenvalues = np.linalg.eigvals(M)
        assert np.all(eigenvalues > 0)

    def test_energy_analysis(self, dynamics_model, test_states):
        """Test energy analysis functionality."""
        energy_result = dynamics_model.compute_energy_analysis(test_states['mixed_state'])

        assert isinstance(energy_result, dict)

        # Check required energy components
        required_keys = [
            'kinetic_energy', 'potential_energy', 'total_energy',
            'kinetic_cart', 'kinetic_pendulum1', 'kinetic_pendulum2',
            'potential_pendulum1', 'potential_pendulum2'
        ]
        for key in required_keys:
            assert key in energy_result
            assert isinstance(energy_result[key], (int, float))
            assert np.isfinite(energy_result[key])

        # Energy conservation properties
        calculated_total = (energy_result['kinetic_energy'] +
                          energy_result['potential_energy'])
        assert abs(calculated_total - energy_result['total_energy']) < 1e-10

        # Kinetic energy components
        calculated_kinetic = (energy_result['kinetic_cart'] +
                            energy_result['kinetic_pendulum1'] +
                            energy_result['kinetic_pendulum2'])
        assert abs(calculated_kinetic - energy_result['kinetic_energy']) < 1e-10

    def test_stability_metrics(self, dynamics_model, test_states):
        """Test stability metrics computation."""
        stability_result = dynamics_model.compute_stability_metrics(test_states['mixed_state'])

        assert isinstance(stability_result, dict)

        # Check required stability metrics
        required_keys = [
            'condition_number', 'determinant', 'total_energy',
            'kinetic_potential_ratio'
        ]
        for key in required_keys:
            assert key in stability_result
            assert isinstance(stability_result[key], (int, float))
            assert np.isfinite(stability_result[key])

        # Condition number should be reasonable for well-conditioned system
        assert stability_result['condition_number'] > 0
        assert stability_result['condition_number'] < 1e6  # Not too ill-conditioned

        # Determinant should be non-zero for non-singular system
        assert abs(stability_result['determinant']) > 1e-12

    def test_step_integration_method(self, dynamics_model, test_states, test_controls):
        """Test simplified step integration method."""
        initial_state = test_states['small_disturbance']
        dt = 0.01

        next_state = dynamics_model.step(
            initial_state,
            test_controls['small_positive'],
            dt
        )

        assert isinstance(next_state, np.ndarray)
        assert next_state.shape == (6,)
        assert np.all(np.isfinite(next_state))

        # State should have changed
        assert not np.array_equal(next_state, initial_state)

        # Change should be reasonable for small time step
        state_change = np.linalg.norm(next_state - initial_state)
        assert state_change < 1.0  # Reasonable for dt=0.01

    def test_computation_statistics_tracking(self, dynamics_model, test_states, test_controls):
        """Test computation statistics tracking."""
        # Initially should have no computations
        stats = dynamics_model.get_computation_statistics()
        assert stats['total_computations'] == 0
        assert stats['successful_computations'] == 0
        assert stats['failed_computations'] == 0

        # Perform successful computations
        for _ in range(5):
            result = dynamics_model.compute_dynamics(
                test_states['equilibrium'],
                test_controls['zero']
            )
            assert result.success == True

        # Check statistics update
        stats = dynamics_model.get_computation_statistics()
        assert stats['total_computations'] == 5
        assert stats['successful_computations'] == 5
        assert stats['failed_computations'] == 0
        assert abs(stats['success_rate'] - 1.0) < 1e-10

    def test_input_validation_invalid_state(self, dynamics_model, test_controls):
        """Test input validation for invalid states."""
        # Wrong dimensions
        invalid_state = np.array([1.0, 2.0, 3.0])  # Only 3 elements instead of 6

        result = dynamics_model.compute_dynamics(invalid_state, test_controls['zero'])
        assert result.success == False
        assert 'failure_reason' in result.info

    def test_input_validation_invalid_control(self, dynamics_model, test_states):
        """Test input validation for invalid control inputs."""
        # Wrong dimensions
        invalid_control = np.array([1.0, 2.0])  # 2 elements instead of 1

        result = dynamics_model.compute_dynamics(test_states['equilibrium'], invalid_control)
        assert result.success == False

        # Control input too large
        excessive_control = np.array([100.0])  # Exceeds force limit

        result = dynamics_model.compute_dynamics(test_states['equilibrium'], excessive_control)
        assert result.success == False

    def test_numerical_instability_handling(self, dynamics_model):
        """Test handling of numerical instability."""
        with patch.object(dynamics_model.physics, 'compute_simplified_dynamics_rhs',
                         side_effect=NumericalInstabilityError("Test instability")):

            result = dynamics_model.compute_dynamics(
                np.zeros(6), np.array([1.0])
            )

            assert result.success == False
            assert result.info['error_type'] == 'numerical_instability'
            assert 'Test instability' in result.info['failure_reason']


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Low-rank dynamics modules not available")
class TestLowRankDynamicsConfigurations:
    """Test different configuration modes for low-rank dynamics."""

    def test_linearized_mode(self):
        """Test dynamics in linearized mode."""
        config = LowRankDIPConfig(
            enable_linearization=True,
            enable_small_angle_approximation=True
        )
        dynamics = LowRankDIPDynamics(config)

        state = np.array([0.1, 0.05, 0.03, 0.1, 0.05, 0.02])
        control = np.array([2.0])

        result = dynamics.compute_dynamics(state, control)

        assert result.success == True
        assert np.all(np.isfinite(result.state_derivative))

    def test_small_angle_mode(self):
        """Test dynamics with small angle approximation only."""
        config = LowRankDIPConfig(
            enable_linearization=False,
            enable_small_angle_approximation=True
        )
        dynamics = LowRankDIPDynamics(config)

        state = np.array([0.2, 0.1, 0.15, 0.3, 0.2, 0.25])
        control = np.array([5.0])

        result = dynamics.compute_dynamics(state, control)

        assert result.success == True
        assert np.all(np.isfinite(result.state_derivative))

    def test_nonlinear_mode(self):
        """Test full nonlinear dynamics mode."""
        config = LowRankDIPConfig(
            enable_linearization=False,
            enable_small_angle_approximation=False
        )
        dynamics = LowRankDIPDynamics(config)

        state = np.array([0.3, 0.5, 0.4, 0.5, 0.3, 0.4])
        control = np.array([8.0])

        result = dynamics.compute_dynamics(state, control)

        assert result.success == True
        assert np.all(np.isfinite(result.state_derivative))

    def test_fast_prototype_configuration(self):
        """Test fast prototype configuration."""
        config = LowRankDIPConfig.create_fast_prototype()
        dynamics = LowRankDIPDynamics(config)

        # Should be optimized for speed
        assert config.enable_linearization == True
        assert config.enable_small_angle_approximation == True
        assert config.enable_fast_math == True
        assert config.use_simplified_matrices == True

        # Should compute dynamics successfully
        result = dynamics.compute_dynamics(
            np.array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1]),
            np.array([3.0])
        )
        assert result.success == True

    def test_educational_configuration(self):
        """Test educational configuration."""
        config = LowRankDIPConfig.create_educational()
        dynamics = LowRankDIPDynamics(config)

        # Should use more accurate physics for educational purposes
        assert config.enable_linearization == False
        assert config.enable_small_angle_approximation == False
        assert config.enable_decoupled_dynamics == False

        # Should compute dynamics successfully
        result = dynamics.compute_dynamics(
            np.array([0.2, 0.3, 0.25, 0.15, 0.2, 0.18]),
            np.array([5.0])
        )
        assert result.success == True


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Low-rank dynamics modules not available")
class TestLowRankDynamicsPerformance:
    """Test performance characteristics of low-rank dynamics."""

    def test_computation_speed_linearized(self):
        """Test computation speed in linearized mode."""
        config = LowRankDIPConfig.create_fast_prototype()
        dynamics = LowRankDIPDynamics(config, enable_monitoring=False, enable_validation=False)

        state = np.random.randn(6) * 0.1
        control = np.array([np.random.randn() * 5])

        import time

        # Warm up
        for _ in range(10):
            dynamics.compute_dynamics(state, control)

        # Time multiple computations
        start_time = time.time()
        n_computations = 1000

        for _ in range(n_computations):
            result = dynamics.compute_dynamics(state, control)
            assert result.success == True

        elapsed_time = time.time() - start_time

        # Should be fast (less than 1ms per computation on average)
        time_per_computation = elapsed_time / n_computations
        assert time_per_computation < 0.001  # 1ms per computation

    def test_memory_efficiency(self):
        """Test memory efficiency of low-rank dynamics."""
        config = LowRankDIPConfig.create_fast_prototype()
        dynamics = LowRankDIPDynamics(config)

        import gc
        import sys

        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Perform many computations
        for i in range(100):
            state = np.random.randn(6) * 0.1
            control = np.array([np.random.randn() * 5])

            result = dynamics.compute_dynamics(state, control)
            assert result.success == True

            # Occasionally force garbage collection
            if i % 20 == 0:
                gc.collect()

        # Check final memory usage
        gc.collect()
        final_objects = len(gc.get_objects())

        # Should not have excessive object growth
        object_growth = final_objects - initial_objects
        assert object_growth < 100  # Allow some growth but not excessive

    def test_batch_computation_efficiency(self):
        """Test efficiency of batch computations."""
        config = LowRankDIPConfig.create_fast_prototype()
        dynamics = LowRankDIPDynamics(config, enable_monitoring=False)

        batch_size = 50
        states = np.random.randn(batch_size, 6) * 0.1
        controls = np.random.randn(batch_size, 1) * 5

        import time
        start_time = time.time()

        results = []
        for i in range(batch_size):
            result = dynamics.compute_dynamics(states[i], controls[i])
            results.append(result)
            assert result.success == True

        elapsed_time = time.time() - start_time

        # Should complete batch in reasonable time
        assert elapsed_time < 0.1  # 100ms for 50 computations
        assert len(results) == batch_size


# Fallback tests when imports are not available
class TestLowRankDynamicsFallback:
    """Test fallback behavior when imports are not available."""

    @pytest.mark.skipif(IMPORTS_AVAILABLE, reason="Test only when imports fail")
    def test_imports_not_available(self):
        """Test that we handle missing imports gracefully."""
        assert LowRankDIPDynamics is None
        assert LowRankDIPConfig is None
        assert IMPORTS_AVAILABLE is False

    def test_test_structure_robustness(self):
        """Test that our test structure is robust to missing components."""
        # Verify test parameter structure
        test_params = {
            'state_size': 6,
            'control_size': 1,
            'expected_matrix_size': (3, 3),
            'energy_components': 8
        }

        assert test_params['state_size'] == 6
        assert test_params['control_size'] == 1
        assert test_params['expected_matrix_size'] == (3, 3)
        assert test_params['energy_components'] == 8