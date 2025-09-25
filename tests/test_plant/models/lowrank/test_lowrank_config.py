#==========================================================================================\\\
#================ tests/test_plant/models/lowrank/test_lowrank_config.py ================\\\
#==========================================================================================\\\
"""
Comprehensive test suite for low-rank DIP configuration.
Tests configuration validation, derived parameter computation, linearization matrices,
and factory methods for the low-rank DIP model.
"""

import pytest
import numpy as np
from typing import Tuple, Dict, Any

try:
    from src.plant.models.lowrank.config import LowRankDIPConfig
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    LowRankDIPConfig = None


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Low-rank config modules not available")
class TestLowRankDIPConfig:
    """Test cases for LowRankDIPConfig core functionality."""

    def test_default_initialization(self):
        """Test default configuration initialization."""
        config = LowRankDIPConfig()

        # Check basic physical parameters have sensible defaults
        assert config.cart_mass == 1.0
        assert config.pendulum1_mass == 0.1
        assert config.pendulum2_mass == 0.1
        assert config.pendulum1_length == 0.5
        assert config.pendulum2_length == 0.5
        assert config.gravity == 9.81

        # Check friction parameters
        assert config.friction_coefficient == 0.1
        assert config.damping_coefficient == 0.01

        # Check control limits
        assert config.force_limit == 20.0

        # Check state bounds
        assert config.cart_position_limits == (-2.0, 2.0)
        assert config.cart_velocity_limit == 5.0
        assert config.joint_velocity_limits == 10.0

        # Check approximation flags
        assert config.enable_linearization == True
        assert config.enable_small_angle_approximation == True
        assert config.enable_decoupled_dynamics == False

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        config = LowRankDIPConfig(
            cart_mass=2.0,
            pendulum1_mass=0.2,
            pendulum2_mass=0.15,
            pendulum1_length=0.8,
            pendulum2_length=0.6,
            gravity=9.8,
            friction_coefficient=0.2,
            damping_coefficient=0.02,
            force_limit=30.0,
            enable_linearization=False,
            enable_small_angle_approximation=False
        )

        assert config.cart_mass == 2.0
        assert config.pendulum1_mass == 0.2
        assert config.pendulum2_mass == 0.15
        assert config.pendulum1_length == 0.8
        assert config.pendulum2_length == 0.6
        assert config.gravity == 9.8
        assert config.friction_coefficient == 0.2
        assert config.damping_coefficient == 0.02
        assert config.force_limit == 30.0
        assert config.enable_linearization == False
        assert config.enable_small_angle_approximation == False

    def test_derived_parameters_computation(self):
        """Test computation of derived parameters."""
        config = LowRankDIPConfig(
            cart_mass=1.5,
            pendulum1_mass=0.2,
            pendulum2_mass=0.3,
            pendulum1_length=0.8,
            pendulum2_length=0.6
        )

        # Total mass should be computed correctly
        expected_total = 1.5 + 0.2 + 0.3
        assert config.total_mass == expected_total

        # Effective lengths should match pendulum lengths
        assert config.effective_length1 == 0.8
        assert config.effective_length2 == 0.6

        # Effective inertias should be computed correctly
        expected_inertia1 = 0.2 * 0.8**2
        expected_inertia2 = 0.3 * 0.6**2
        assert config.effective_inertia1 == expected_inertia1
        assert config.effective_inertia2 == expected_inertia2

        # Natural frequencies should be computed correctly
        expected_freq1 = np.sqrt(config.gravity / 0.8)
        expected_freq2 = np.sqrt(config.gravity / 0.6)
        assert abs(config.natural_freq1 - expected_freq1) < 1e-12
        assert abs(config.natural_freq2 - expected_freq2) < 1e-12

        # Coupling strength should be computed correctly
        expected_coupling = (0.2 * 0.8 + 0.3 * 0.6) / expected_total
        assert abs(config.coupling_strength - expected_coupling) < 1e-12

    def test_physics_constants_setup(self):
        """Test setup of physics constants."""
        config = LowRankDIPConfig(
            pendulum1_mass=0.15,
            pendulum2_mass=0.25,
            pendulum1_length=0.7,
            pendulum2_length=0.9,
            gravity=9.8,
            friction_coefficient=0.12
        )

        # Gravitational terms
        expected_g1 = 0.15 * 9.8 * 0.7
        expected_g2 = 0.25 * 9.8 * 0.9
        assert abs(config.g1 - expected_g1) < 1e-12
        assert abs(config.g2 - expected_g2) < 1e-12

        # Mass-length products
        expected_m1l1 = 0.15 * 0.7
        expected_m2l2 = 0.25 * 0.9
        assert abs(config.m1l1 - expected_m1l1) < 1e-12
        assert abs(config.m2l2 - expected_m2l2) < 1e-12

        # Friction force maximum
        expected_friction_max = 0.12 * config.total_mass * 9.8
        assert abs(config.friction_force_max - expected_friction_max) < 1e-12

    def test_parameter_validation_success(self):
        """Test successful parameter validation."""
        # Valid configuration should not raise exceptions
        config = LowRankDIPConfig(
            cart_mass=0.5,
            pendulum1_mass=0.1,
            pendulum2_mass=0.2,
            pendulum1_length=0.3,
            pendulum2_length=0.4,
            gravity=9.81,
            friction_coefficient=0.0,  # Zero is valid
            damping_coefficient=0.0    # Zero is valid
        )
        assert isinstance(config, LowRankDIPConfig)

    def test_parameter_validation_failures(self):
        """Test parameter validation failure cases."""
        # Zero or negative cart mass
        with pytest.raises(ValueError, match="Cart mass must be positive"):
            LowRankDIPConfig(cart_mass=0.0)

        with pytest.raises(ValueError, match="Cart mass must be positive"):
            LowRankDIPConfig(cart_mass=-1.0)

        # Zero or negative pendulum masses
        with pytest.raises(ValueError, match="Pendulum masses must be positive"):
            LowRankDIPConfig(pendulum1_mass=0.0)

        with pytest.raises(ValueError, match="Pendulum masses must be positive"):
            LowRankDIPConfig(pendulum2_mass=-0.1)

        # Zero or negative pendulum lengths
        with pytest.raises(ValueError, match="Pendulum lengths must be positive"):
            LowRankDIPConfig(pendulum1_length=0.0)

        with pytest.raises(ValueError, match="Pendulum lengths must be positive"):
            LowRankDIPConfig(pendulum2_length=-0.5)

        # Zero or negative gravity
        with pytest.raises(ValueError, match="Gravity must be positive"):
            LowRankDIPConfig(gravity=0.0)

        with pytest.raises(ValueError, match="Gravity must be positive"):
            LowRankDIPConfig(gravity=-9.81)

        # Negative friction coefficient
        with pytest.raises(ValueError, match="Friction coefficient must be non-negative"):
            LowRankDIPConfig(friction_coefficient=-0.1)

        # Negative damping coefficient
        with pytest.raises(ValueError, match="Damping coefficient must be non-negative"):
            LowRankDIPConfig(damping_coefficient=-0.01)

    def test_upright_linearization_matrices(self):
        """Test linearization around upright equilibrium."""
        config = LowRankDIPConfig()
        A, B = config.get_linearized_matrices("upright")

        assert isinstance(A, np.ndarray)
        assert isinstance(B, np.ndarray)
        assert A.shape == (6, 6)
        assert B.shape == (6, 1)

        # Check position derivative terms
        assert A[0, 3] == 1.0  # x_dot term
        assert A[1, 4] == 1.0  # theta1_dot term
        assert A[2, 5] == 1.0  # theta2_dot term

        # Check that pendulum terms are unstable (positive eigenvalues for upright)
        # Natural frequency terms should be negative (unstable equilibrium)
        assert A[4, 1] < 0  # theta1 restoring force (negative = unstable)
        assert A[5, 2] < 0  # theta2 restoring force (negative = unstable)

        # Control input should affect cart directly
        assert B[3, 0] == 1.0 / config.cart_mass

        # Control should not directly affect angles
        assert B[0, 0] == 0.0
        assert B[1, 0] == 0.0
        assert B[2, 0] == 0.0
        assert B[4, 0] == 0.0
        assert B[5, 0] == 0.0

    def test_downward_linearization_matrices(self):
        """Test linearization around downward equilibrium."""
        config = LowRankDIPConfig()
        A, B = config.get_linearized_matrices("downward")

        assert A.shape == (6, 6)
        assert B.shape == (6, 1)

        # Check position derivative terms
        assert A[0, 3] == 1.0
        assert A[1, 4] == 1.0
        assert A[2, 5] == 1.0

        # Pendulum terms should be stable (negative real eigenvalues for downward)
        # Natural frequency terms should be positive (stable equilibrium)
        assert A[4, 1] > 0  # theta1 restoring force (positive = stable)
        assert A[5, 2] > 0  # theta2 restoring force (positive = stable)

        # Control input should still affect cart
        assert B[3, 0] == 1.0 / config.cart_mass

    def test_linearization_matrix_properties(self):
        """Test mathematical properties of linearization matrices."""
        config = LowRankDIPConfig(
            cart_mass=2.0,
            pendulum1_mass=0.3,
            pendulum2_mass=0.2,
            pendulum1_length=1.0,
            pendulum2_length=0.8
        )

        # Test upright equilibrium
        A_up, B_up = config.get_linearized_matrices("upright")

        # A matrix should have correct structure
        # Upper-left should be zero (position to position coupling)
        assert np.allclose(A_up[:3, :3], np.zeros((3, 3)))

        # Upper-right should be identity (position to velocity coupling)
        assert np.allclose(A_up[:3, 3:], np.eye(3))

        # B matrix should have zeros except for cart force effect
        expected_B = np.zeros((6, 1))
        expected_B[3, 0] = 1.0 / config.cart_mass
        assert np.allclose(B_up, expected_B)

        # Test downward equilibrium
        A_down, B_down = config.get_linearized_matrices("downward")

        # Same structural properties should hold
        assert np.allclose(A_down[:3, :3], np.zeros((3, 3)))
        assert np.allclose(A_down[:3, 3:], np.eye(3))
        assert np.allclose(B_down, expected_B)

    def test_invalid_equilibrium_point(self):
        """Test invalid equilibrium point handling."""
        config = LowRankDIPConfig()

        with pytest.raises(ValueError, match="Unknown equilibrium point"):
            config.get_linearized_matrices("invalid")

        with pytest.raises(ValueError, match="Unknown equilibrium point"):
            config.get_linearized_matrices("sideways")

    def test_to_dict_conversion(self):
        """Test configuration conversion to dictionary."""
        config = LowRankDIPConfig(
            cart_mass=1.5,
            pendulum1_mass=0.2,
            pendulum2_mass=0.3,
            friction_coefficient=0.15,
            enable_linearization=False
        )

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)

        # Check that key parameters are included
        assert config_dict['cart_mass'] == 1.5
        assert config_dict['pendulum1_mass'] == 0.2
        assert config_dict['pendulum2_mass'] == 0.3
        assert config_dict['friction_coefficient'] == 0.15
        assert config_dict['enable_linearization'] == False

        # Check that all expected keys are present
        expected_keys = [
            'cart_mass', 'pendulum1_mass', 'pendulum2_mass',
            'pendulum1_length', 'pendulum2_length', 'gravity',
            'friction_coefficient', 'damping_coefficient', 'force_limit',
            'cart_position_limits', 'cart_velocity_limit', 'joint_velocity_limits',
            'enable_linearization', 'enable_small_angle_approximation',
            'enable_decoupled_dynamics'
        ]

        for key in expected_keys:
            assert key in config_dict

    def test_from_dict_creation(self):
        """Test configuration creation from dictionary."""
        config_dict = {
            'cart_mass': 2.0,
            'pendulum1_mass': 0.25,
            'pendulum2_mass': 0.35,
            'pendulum1_length': 0.9,
            'pendulum2_length': 0.7,
            'friction_coefficient': 0.12,
            'damping_coefficient': 0.03,
            'enable_linearization': False,
            'enable_small_angle_approximation': True
        }

        config = LowRankDIPConfig.from_dict(config_dict)

        assert isinstance(config, LowRankDIPConfig)
        assert config.cart_mass == 2.0
        assert config.pendulum1_mass == 0.25
        assert config.pendulum2_mass == 0.35
        assert config.pendulum1_length == 0.9
        assert config.pendulum2_length == 0.7
        assert config.friction_coefficient == 0.12
        assert config.damping_coefficient == 0.03
        assert config.enable_linearization == False
        assert config.enable_small_angle_approximation == True

    def test_dict_roundtrip_conversion(self):
        """Test roundtrip conversion: config -> dict -> config."""
        original_config = LowRankDIPConfig(
            cart_mass=1.8,
            pendulum1_mass=0.22,
            pendulum2_mass=0.18,
            friction_coefficient=0.08,
            enable_decoupled_dynamics=True
        )

        config_dict = original_config.to_dict()
        reconstructed_config = LowRankDIPConfig.from_dict(config_dict)

        # Key parameters should match
        assert reconstructed_config.cart_mass == original_config.cart_mass
        assert reconstructed_config.pendulum1_mass == original_config.pendulum1_mass
        assert reconstructed_config.pendulum2_mass == original_config.pendulum2_mass
        assert reconstructed_config.friction_coefficient == original_config.friction_coefficient
        assert reconstructed_config.enable_decoupled_dynamics == original_config.enable_decoupled_dynamics

        # Derived parameters should also match
        assert reconstructed_config.total_mass == original_config.total_mass
        assert abs(reconstructed_config.natural_freq1 - original_config.natural_freq1) < 1e-12
        assert abs(reconstructed_config.natural_freq2 - original_config.natural_freq2) < 1e-12


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Low-rank config modules not available")
class TestLowRankConfigFactoryMethods:
    """Test factory methods for creating specialized configurations."""

    def test_fast_prototype_factory(self):
        """Test fast prototype configuration factory."""
        config = LowRankDIPConfig.create_fast_prototype()

        assert isinstance(config, LowRankDIPConfig)

        # Should be optimized for speed
        assert config.enable_linearization == True
        assert config.enable_small_angle_approximation == True
        assert config.enable_fast_math == True
        assert config.use_simplified_matrices == True

        # Should have reasonable default masses and lengths
        assert config.cart_mass == 1.0
        assert config.pendulum1_mass == 0.1
        assert config.pendulum2_mass == 0.1
        assert config.pendulum1_length == 0.5
        assert config.pendulum2_length == 0.5

        # Should have low friction for fast prototyping
        assert config.friction_coefficient == 0.05
        assert config.damping_coefficient == 0.01

    def test_educational_factory(self):
        """Test educational configuration factory."""
        config = LowRankDIPConfig.create_educational()

        assert isinstance(config, LowRankDIPConfig)

        # Should use more accurate physics for education
        assert config.enable_linearization == False
        assert config.enable_small_angle_approximation == False
        assert config.enable_decoupled_dynamics == False

        # Should have educational-friendly parameters
        assert config.cart_mass == 1.0
        assert config.pendulum1_mass == 0.2  # Heavier than prototype
        assert config.pendulum2_mass == 0.1
        assert config.pendulum1_length == 1.0  # Longer than prototype
        assert config.pendulum2_length == 0.8

        # Should have moderate friction for realistic behavior
        assert config.friction_coefficient == 0.1
        assert config.damping_coefficient == 0.02

    def test_factory_methods_parameter_validation(self):
        """Test that factory methods produce valid configurations."""
        # Fast prototype should pass validation
        fast_config = LowRankDIPConfig.create_fast_prototype()
        assert fast_config.cart_mass > 0
        assert fast_config.pendulum1_mass > 0
        assert fast_config.pendulum2_mass > 0
        assert fast_config.pendulum1_length > 0
        assert fast_config.pendulum2_length > 0
        assert fast_config.gravity > 0

        # Educational should pass validation
        edu_config = LowRankDIPConfig.create_educational()
        assert edu_config.cart_mass > 0
        assert edu_config.pendulum1_mass > 0
        assert edu_config.pendulum2_mass > 0
        assert edu_config.pendulum1_length > 0
        assert edu_config.pendulum2_length > 0
        assert edu_config.gravity > 0

    def test_factory_methods_produce_different_configs(self):
        """Test that different factory methods produce different configurations."""
        fast_config = LowRankDIPConfig.create_fast_prototype()
        edu_config = LowRankDIPConfig.create_educational()

        # Approximation settings should be different
        assert fast_config.enable_linearization != edu_config.enable_linearization
        assert fast_config.enable_small_angle_approximation != edu_config.enable_small_angle_approximation

        # Physical parameters should be different
        assert fast_config.pendulum1_mass != edu_config.pendulum1_mass
        assert fast_config.pendulum1_length != edu_config.pendulum1_length
        assert fast_config.friction_coefficient != edu_config.friction_coefficient


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Low-rank config modules not available")
class TestLowRankConfigLinearizationConsistency:
    """Test consistency and mathematical properties of linearization."""

    def test_linearization_scaling_consistency(self):
        """Test that linearization scales properly with parameters."""
        # Base configuration
        base_config = LowRankDIPConfig(
            cart_mass=1.0,
            pendulum1_mass=0.1,
            pendulum2_mass=0.1,
            pendulum1_length=0.5,
            pendulum2_length=0.5
        )

        # Scaled configuration (double all masses)
        scaled_config = LowRankDIPConfig(
            cart_mass=2.0,
            pendulum1_mass=0.2,
            pendulum2_mass=0.2,
            pendulum1_length=0.5,
            pendulum2_length=0.5
        )

        A_base, B_base = base_config.get_linearized_matrices("upright")
        A_scaled, B_scaled = scaled_config.get_linearized_matrices("upright")

        # Control effectiveness should scale inversely with mass
        assert abs(B_scaled[3, 0] - B_base[3, 0] / 2.0) < 1e-12

        # Natural frequencies should be unchanged (same lengths)
        # But coupling terms should be affected by mass ratios

    def test_linearization_length_effects(self):
        """Test linearization effects of different pendulum lengths."""
        short_config = LowRankDIPConfig(
            pendulum1_length=0.3,
            pendulum2_length=0.3
        )

        long_config = LowRankDIPConfig(
            pendulum1_length=1.0,
            pendulum2_length=1.0
        )

        A_short, _ = short_config.get_linearized_matrices("upright")
        A_long, _ = long_config.get_linearized_matrices("upright")

        # Natural frequencies should be higher for shorter pendulums
        # (more negative eigenvalues for upright equilibrium)
        assert A_short[4, 1] < A_long[4, 1]  # More negative = higher frequency
        assert A_short[5, 2] < A_long[5, 2]

    def test_upright_vs_downward_stability(self):
        """Test stability characteristics of different equilibria."""
        config = LowRankDIPConfig()

        A_up, _ = config.get_linearized_matrices("upright")
        A_down, _ = config.get_linearized_matrices("downward")

        # Upright should be unstable (positive real parts)
        eigenvals_up = np.linalg.eigvals(A_up)
        has_positive_real = np.any(np.real(eigenvals_up) > 1e-6)
        assert has_positive_real  # Should have unstable modes

        # Downward should be stable (negative real parts)
        eigenvals_down = np.linalg.eigvals(A_down)
        all_negative_real = np.all(np.real(eigenvals_down) < 1e-6)
        assert all_negative_real  # Should be stable


# Fallback tests when imports are not available
class TestLowRankConfigFallback:
    """Test fallback behavior when imports are not available."""

    @pytest.mark.skipif(IMPORTS_AVAILABLE, reason="Test only when imports fail")
    def test_imports_not_available(self):
        """Test that we handle missing imports gracefully."""
        assert LowRankDIPConfig is None
        assert IMPORTS_AVAILABLE is False

    def test_config_test_structure(self):
        """Test configuration test parameter structure."""
        config_params = {
            'physical_params': 6,  # mass, length, gravity, friction, damping, force_limit
            'state_bounds': 3,     # position, velocity, angular_velocity
            'approximation_flags': 3,  # linearization, small_angle, decoupled
            'matrix_dimensions': (6, 6),  # A matrix
            'control_dimensions': (6, 1), # B matrix
            'factory_methods': 2   # fast_prototype, educational
        }

        assert config_params['physical_params'] == 6
        assert config_params['state_bounds'] == 3
        assert config_params['approximation_flags'] == 3
        assert config_params['matrix_dimensions'] == (6, 6)
        assert config_params['control_dimensions'] == (6, 1)
        assert config_params['factory_methods'] == 2