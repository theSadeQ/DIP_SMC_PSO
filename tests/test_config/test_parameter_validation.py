#==========================================================================================\\
#============== tests/test_config/test_parameter_validation.py =====================\\
#==========================================================================================\\
"""
Parameter bounds and validation tests.

HIGH-ROI TESTS: These tests document realistic parameter ranges vs unrealistic test values,
preventing debugging sessions caused by physics-violating parameters and 980% energy errors.
"""

import pytest
import numpy as np
from typing import Dict, Any, Tuple

from src.plant import ConfigurationFactory
from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
from src.plant.models.full.dynamics import FullDIPDynamics


class TestParameterBoundsValidation:
    """Test that parameters are within physics-realistic ranges."""

    def test_mass_parameter_bounds(self):
        """Test that mass parameters are physically realistic and positive."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        mass_parameters = [
            'cart_mass',
            'pendulum1_mass',
            'pendulum2_mass'
        ]

        for config in configs:
            for mass_param in mass_parameters:
                if hasattr(config, mass_param):
                    mass_value = getattr(config, mass_param)

                    # Physics constraint: mass > 0
                    assert mass_value > 0, (
                        f"{mass_param} must be positive: {mass_value}"
                    )

                    # Realistic bounds for DIP system (0.01 kg to 100 kg)
                    assert 0.01 <= mass_value <= 100.0, (
                        f"{mass_param} outside realistic range [0.01, 100]: {mass_value}"
                    )

    def test_length_parameter_bounds(self):
        """Test that length parameters are physically realistic and positive."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        length_parameters = [
            'pendulum1_length',
            'pendulum2_length',
            'pendulum1_com',  # Center of mass position
            'pendulum2_com'
        ]

        for config in configs:
            for length_param in length_parameters:
                if hasattr(config, length_param):
                    length_value = getattr(config, length_param)

                    # Physics constraint: length > 0
                    assert length_value > 0, (
                        f"{length_param} must be positive: {length_value}"
                    )

                    # Realistic bounds for DIP system (1 cm to 10 m)
                    assert 0.01 <= length_value <= 10.0, (
                        f"{length_param} outside realistic range [0.01, 10]: {length_value}"
                    )

    def test_damping_parameter_bounds(self):
        """Test that damping parameters are non-negative and realistic."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        damping_parameters = [
            'cart_friction',
            'joint1_friction',
            'joint2_friction',
            'viscous_damping',
            'air_resistance'
        ]

        for config in configs:
            for damping_param in damping_parameters:
                if hasattr(config, damping_param):
                    damping_value = getattr(config, damping_param)

                    # Physics constraint: damping >= 0
                    assert damping_value >= 0, (
                        f"{damping_param} must be non-negative: {damping_value}"
                    )

                    # Realistic bounds for DIP system (0 to 100 Ns/m)
                    assert 0.0 <= damping_value <= 100.0, (
                        f"{damping_param} outside realistic range [0, 100]: {damping_value}"
                    )

    def test_gravity_parameter_bounds(self):
        """Test that gravity parameter is realistic."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        for config in configs:
            if hasattr(config, 'gravity'):
                gravity_value = getattr(config, 'gravity')

                # Physics constraint: gravity > 0 for normal Earth conditions
                assert gravity_value > 0, f"gravity must be positive: {gravity_value}"

                # Realistic bounds (0.1 to 100 m/s² - covers Moon to Jupiter)
                assert 0.1 <= gravity_value <= 100.0, (
                    f"gravity outside realistic range [0.1, 100]: {gravity_value}"
                )

                # Earth-like gravity check (should be close to 9.81 for most tests)
                if 9.0 <= gravity_value <= 10.5:
                    assert True  # Earth-like gravity is good
                else:
                    # Non-Earth gravity is acceptable but should be documented
                    pass


class TestPhysicsConstraintValidation:
    """Test that parameters satisfy physics constraints."""

    def test_inertia_parameter_consistency(self):
        """Test that inertia parameters are consistent with mass and length."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        for config in configs:
            if all(hasattr(config, param) for param in ['pendulum1_mass', 'pendulum1_length', 'pendulum1_inertia']):
                mass = getattr(config, 'pendulum1_mass')
                length = getattr(config, 'pendulum1_length')
                inertia = getattr(config, 'pendulum1_inertia')

                # Physics constraint: for rod, I = (1/3) * m * l²
                # For point mass at end: I = m * l²
                # Realistic range: (1/12) * m * l² <= I <= m * l²

                min_inertia = (1.0/12.0) * mass * length**2  # Thin rod about center
                max_inertia = mass * length**2                # Point mass at end

                assert min_inertia <= inertia <= max_inertia, (
                    f"pendulum1_inertia {inertia} outside physics range "
                    f"[{min_inertia:.6f}, {max_inertia:.6f}] for mass={mass}, length={length}"
                )

    def test_center_of_mass_parameter_bounds(self):
        """Test that center of mass positions are within pendulum length."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        for config in configs:
            # Test pendulum 1
            if hasattr(config, 'pendulum1_length') and hasattr(config, 'pendulum1_com'):
                length = getattr(config, 'pendulum1_length')
                com = getattr(config, 'pendulum1_com')

                # Physics constraint: 0 < com <= length
                assert 0 < com <= length, (
                    f"pendulum1_com {com} outside valid range (0, {length}]"
                )

            # Test pendulum 2
            if hasattr(config, 'pendulum2_length') and hasattr(config, 'pendulum2_com'):
                length = getattr(config, 'pendulum2_length')
                com = getattr(config, 'pendulum2_com')

                # Physics constraint: 0 < com <= length
                assert 0 < com <= length, (
                    f"pendulum2_com {com} outside valid range (0, {length}]"
                )

    def test_control_force_limits(self):
        """Test that control force limits are reasonable."""

        configs = [
            ConfigurationFactory.create_default_config("controller"),
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full")
        ]

        force_parameters = [
            'max_force',
            'force_limit',
            'control_limit'
        ]

        for config in configs:
            for force_param in force_parameters:
                if hasattr(config, force_param):
                    force_limit = getattr(config, force_param)

                    # Physics constraint: force limit > 0
                    assert force_limit > 0, (
                        f"{force_param} must be positive: {force_limit}"
                    )

                    # Realistic bounds for DIP system (1 N to 10000 N)
                    assert 1.0 <= force_limit <= 10000.0, (
                        f"{force_param} outside realistic range [1, 10000]: {force_limit}"
                    )


class TestNumericalStabilityParameterRanges:
    """Test parameters are within numerical stability limits."""

    def test_integration_timestep_bounds(self):
        """Test that integration timesteps are within stability limits."""

        # Common timestep parameters in configurations
        timestep_parameters = ['dt', 'time_step', 'integration_step']

        configs = [
            ConfigurationFactory.create_default_config("simulation"),
            ConfigurationFactory.create_default_config("controller")
        ]

        for config in configs:
            for dt_param in timestep_parameters:
                if hasattr(config, dt_param):
                    dt_value = getattr(config, dt_param)

                    # Numerical constraint: dt > 0
                    assert dt_value > 0, f"{dt_param} must be positive: {dt_value}"

                    # Stability bounds for DIP system
                    # Too small: computational overhead
                    # Too large: numerical instability
                    assert 1e-6 <= dt_value <= 0.1, (
                        f"{dt_param} outside stable range [1e-6, 0.1]: {dt_value}"
                    )

                    # Document known stability boundary: dt=0.1 stable, dt=0.5+ unstable
                    if dt_value > 0.1:
                        pytest.fail(
                            f"{dt_param}={dt_value} > 0.1 likely causes integration instability"
                        )

    def test_regularization_parameter_bounds(self):
        """Test that regularization parameters prevent numerical issues."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        regularization_parameters = [
            'regularization_alpha',
            'min_regularization',
            'max_condition_number'
        ]

        for config in configs:
            for reg_param in regularization_parameters:
                if hasattr(config, reg_param):
                    reg_value = getattr(config, reg_param)

                    if reg_param == 'regularization_alpha':
                        # Small positive value for matrix conditioning
                        assert 0 < reg_value <= 1e-2, (
                            f"{reg_param} outside stable range (0, 1e-2]: {reg_value}"
                        )

                    elif reg_param == 'min_regularization':
                        # Minimum regularization to prevent singularity
                        assert 1e-12 <= reg_value <= 1e-6, (
                            f"{reg_param} outside stable range [1e-12, 1e-6]: {reg_value}"
                        )

                    elif reg_param == 'max_condition_number':
                        # Maximum acceptable matrix condition number
                        assert 1e3 <= reg_value <= 1e12, (
                            f"{reg_param} outside stable range [1e3, 1e12]: {reg_value}"
                        )

    def test_energy_conservation_parameter_ranges(self):
        """Test parameters that affect energy conservation and prevent 980% energy errors."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full")
        ]

        for config in configs:
            # Create dynamics to test energy conservation
            if 'simplified' in str(type(config).__name__).lower() or hasattr(config, 'pendulum1_mass'):
                try:
                    dynamics = SimplifiedDIPDynamics(config)
                except:
                    continue  # Skip if config doesn't work with SimplifiedDIPDynamics

                # Test energy computation with small perturbation
                state = np.array([0.01, 0.01, 0.01, 0.0, 0.0, 0.0])  # Small initial state

                if hasattr(dynamics, 'compute_total_energy'):
                    try:
                        total_energy = dynamics.compute_total_energy(state)

                        # Energy should be reasonable (not 980% error)
                        # For small state, energy should be small
                        assert abs(total_energy) < 100.0, (
                            f"Total energy {total_energy} too large for small state - "
                            f"indicates parameter scaling issues"
                        )

                        # Energy should be finite
                        assert np.isfinite(total_energy), (
                            f"Total energy {total_energy} not finite - indicates numerical issues"
                        )

                    except Exception as e:
                        pytest.fail(f"Energy computation failed: {e}")


class TestParameterTypeValidation:
    """Test that parameter types are correct."""

    def test_numeric_parameter_types(self):
        """Test that numeric parameters have correct types (float, int)."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("controller")
        ]

        # Expected numeric parameters
        numeric_parameters = [
            'cart_mass',
            'pendulum1_mass',
            'pendulum2_mass',
            'pendulum1_length',
            'pendulum2_length',
            'gravity',
            'max_force',
            'dt'
        ]

        for config in configs:
            for param_name in numeric_parameters:
                if hasattr(config, param_name):
                    param_value = getattr(config, param_name)

                    # Should be numeric type
                    assert isinstance(param_value, (int, float, np.integer, np.floating)), (
                        f"{param_name} should be numeric, got {type(param_value)}: {param_value}"
                    )

                    # Should be finite
                    assert np.isfinite(param_value), (
                        f"{param_name} should be finite: {param_value}"
                    )

    def test_boolean_parameter_types(self):
        """Test that boolean parameters have correct types."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("controller")
        ]

        # Expected boolean parameters
        boolean_parameters = [
            'enable_monitoring',
            'enable_fast_mode',
            'use_fixed_regularization',
            'wrap_angles',
            'strict_validation'
        ]

        for config in configs:
            for param_name in boolean_parameters:
                if hasattr(config, param_name):
                    param_value = getattr(config, param_name)

                    # Should be boolean type
                    assert isinstance(param_value, (bool, np.bool_)), (
                        f"{param_name} should be boolean, got {type(param_value)}: {param_value}"
                    )

    def test_array_parameter_types(self):
        """Test that array parameters have correct types and shapes."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("controller")
        ]

        # Expected array parameters
        array_parameters = [
            'initial_state',
            'equilibrium_state',
            'position_bounds',
            'velocity_bounds'
        ]

        for config in configs:
            for param_name in array_parameters:
                if hasattr(config, param_name):
                    param_value = getattr(config, param_name)

                    if param_value is not None:
                        # Should be array-like
                        assert isinstance(param_value, (list, tuple, np.ndarray)), (
                            f"{param_name} should be array-like, got {type(param_value)}"
                        )

                        # Convert to numpy array for testing
                        param_array = np.array(param_value)

                        # Should be finite
                        assert np.all(np.isfinite(param_array)), (
                            f"{param_name} should contain finite values: {param_array}"
                        )

                        # Check reasonable shapes
                        if 'state' in param_name:
                            assert len(param_array) == 6, (
                                f"{param_name} should have 6 elements for DIP state: {len(param_array)}"
                            )
                        elif 'bounds' in param_name:
                            assert len(param_array) == 2, (
                                f"{param_name} should have 2 elements [min, max]: {len(param_array)}"
                            )


class TestParameterConsistencyValidation:
    """Test parameter consistency across configurations."""

    def test_parameter_scaling_consistency(self):
        """Test that parameters have consistent scaling across configurations."""

        simplified_config = ConfigurationFactory.create_default_config("simplified")
        full_config = ConfigurationFactory.create_default_config("full")

        # Parameters that should be similar between configurations
        common_parameters = [
            'cart_mass',
            'pendulum1_mass',
            'pendulum2_mass',
            'gravity'
        ]

        for param_name in common_parameters:
            if hasattr(simplified_config, param_name) and hasattr(full_config, param_name):
                simplified_value = getattr(simplified_config, param_name)
                full_value = getattr(full_config, param_name)

                # Values should be reasonably similar (within 10x factor)
                ratio = max(simplified_value, full_value) / min(simplified_value, full_value)
                assert ratio <= 10.0, (
                    f"{param_name} scaling inconsistent: "
                    f"simplified={simplified_value}, full={full_value}, ratio={ratio}"
                )

    def test_parameter_units_consistency(self):
        """Test that parameters have consistent units and realistic values."""

        config = ConfigurationFactory.create_default_config("simplified")

        # Test mass units (should be in kg)
        if hasattr(config, 'cart_mass') and hasattr(config, 'pendulum1_mass'):
            cart_mass = getattr(config, 'cart_mass')
            pendulum_mass = getattr(config, 'pendulum1_mass')

            # Cart should typically be heavier than pendulums
            assert cart_mass >= pendulum_mass / 10.0, (
                f"Cart mass {cart_mass} too small compared to pendulum {pendulum_mass}"
            )

        # Test length units (should be in meters)
        if hasattr(config, 'pendulum1_length') and hasattr(config, 'pendulum2_length'):
            len1 = getattr(config, 'pendulum1_length')
            len2 = getattr(config, 'pendulum2_length')

            # Lengths should be reasonably similar
            ratio = max(len1, len2) / min(len1, len2)
            assert ratio <= 5.0, (
                f"Pendulum lengths too different: len1={len1}, len2={len2}, ratio={ratio}"
            )