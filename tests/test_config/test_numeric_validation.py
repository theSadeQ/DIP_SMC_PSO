#==========================================================================================\\\
#================== tests/test_config/test_numeric_validation.py =======================\\\
#==========================================================================================\\\
"""
Numeric Type Validation Tests.

SINGLE JOB: Test only numeric field validation in configuration.
- Integer field validation
- Float field validation
- Numeric field rejection of non-numeric types
- Numeric range validation
"""

import pytest
import yaml
from pathlib import Path

from src.config import (
    load_config,
    InvalidConfigurationError
)


class TestNumericValidation:
    """Test numeric type validation."""

    def test_integer_field_validation(self, tmp_path: Path):
        """Test that integer fields reject non-integer values."""
        config_data = {
            "global_seed": "not_an_integer",  # Should be int
            "physics": {
                "cart_mass": 1.5,
                "pendulum1_mass": 0.2,
                "pendulum2_mass": 0.15,
                "pendulum1_length": 0.4,
                "pendulum2_length": 0.3,
                "pendulum1_com": 0.2,
                "pendulum2_com": 0.15,
                "pendulum1_inertia": 0.00265,
                "pendulum2_inertia": 0.00115,
                "gravity": 9.81,
                "cart_friction": 0.2,
                "joint1_friction": 0.005,
                "joint2_friction": 0.004,
                "singularity_cond_threshold": 100000000.0
            },
            "simulation": {"duration": 1.0, "dt": 0.01},
            "controller_defaults": {},
            "controllers": {},
            "pso": {"n_particles": 10, "bounds": {"min": [1.0], "max": [2.0]}, "iters": 5},
            "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.01},
            "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "fdi": None
        }

        config_file = tmp_path / "test_config.yaml"
        with config_file.open('w') as f:
            yaml.dump(config_data, f)

        with pytest.raises(InvalidConfigurationError) as exc_info:
            load_config(str(config_file))

        error_msg = str(exc_info.value)
        assert "Configuration validation failed:" in error_msg
        assert "global_seed" in error_msg

    def test_float_field_validation(self, tmp_path: Path):
        """Test that float fields reject non-numeric values."""
        config_data = {
            "global_seed": 42,
            "physics": {
                "cart_mass": "not_a_number",  # Should be float
                "pendulum1_mass": 0.2,
                "pendulum2_mass": 0.15,
                "pendulum1_length": 0.4,
                "pendulum2_length": 0.3,
                "pendulum1_com": 0.2,
                "pendulum2_com": 0.15,
                "pendulum1_inertia": 0.00265,
                "pendulum2_inertia": 0.00115,
                "gravity": 9.81,
                "cart_friction": 0.2,
                "joint1_friction": 0.005,
                "joint2_friction": 0.004,
                "singularity_cond_threshold": 100000000.0
            },
            "simulation": {"duration": 1.0, "dt": 0.01},
            "controller_defaults": {},
            "controllers": {},
            "pso": {"n_particles": 10, "bounds": {"min": [1.0], "max": [2.0]}, "iters": 5},
            "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.01},
            "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "fdi": None
        }

        config_file = tmp_path / "test_config.yaml"
        with config_file.open('w') as f:
            yaml.dump(config_data, f)

        with pytest.raises(InvalidConfigurationError) as exc_info:
            load_config(str(config_file))

        error_msg = str(exc_info.value)
        assert "Configuration validation failed:" in error_msg
        assert "cart_mass" in error_msg

    def test_valid_numeric_values_acceptance(self, tmp_path: Path):
        """Test that valid numeric values are accepted."""
        config_data = {
            "global_seed": 42,  # Valid integer
            "physics": {
                "cart_mass": 1.5,  # Valid float
                "pendulum1_mass": 0.2,
                "pendulum2_mass": 0.15,
                "pendulum1_length": 0.4,
                "pendulum2_length": 0.3,
                "pendulum1_com": 0.2,
                "pendulum2_com": 0.15,
                "pendulum1_inertia": 0.00265,
                "pendulum2_inertia": 0.00115,
                "gravity": 9.81,
                "cart_friction": 0.2,
                "joint1_friction": 0.005,
                "joint2_friction": 0.004,
                "singularity_cond_threshold": 100000000.0
            },
            "simulation": {"duration": 1.0, "dt": 0.01},
            "controller_defaults": {},
            "controllers": {},
            "pso": {"n_particles": 10, "bounds": {"min": [1.0], "max": [2.0]}, "iters": 5},
            "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.01},
            "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "fdi": None
        }

        config_file = tmp_path / "test_config.yaml"
        with config_file.open('w') as f:
            yaml.dump(config_data, f)

        try:
            config = load_config(str(config_file))
            assert config is not None
        except Exception as e:
            pytest.fail(f"Valid numeric configuration was rejected: {e}")

    def test_integer_to_float_conversion(self, tmp_path: Path):
        """Test that integers are accepted for float fields."""
        config_data = {
            "global_seed": 42,
            "physics": {
                "cart_mass": 2,  # Integer for float field
                "pendulum1_mass": 0.2,
                "pendulum2_mass": 0.15,
                "pendulum1_length": 0.4,
                "pendulum2_length": 0.3,
                "pendulum1_com": 0.2,
                "pendulum2_com": 0.15,
                "pendulum1_inertia": 0.00265,
                "pendulum2_inertia": 0.00115,
                "gravity": 10,  # Integer for gravity
                "cart_friction": 0.2,
                "joint1_friction": 0.005,
                "joint2_friction": 0.004,
                "singularity_cond_threshold": 100000000.0
            },
            "simulation": {"duration": 1.0, "dt": 0.01},
            "controller_defaults": {},
            "controllers": {},
            "pso": {"n_particles": 10, "bounds": {"min": [1.0], "max": [2.0]}, "iters": 5},
            "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.01},
            "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "fdi": None
        }

        config_file = tmp_path / "test_config.yaml"
        with config_file.open('w') as f:
            yaml.dump(config_data, f)

        try:
            config = load_config(str(config_file))
            # Integers should be converted to floats
            assert config.physics.cart_mass == 2.0
            assert config.physics.gravity == 10.0
        except Exception as e:
            pytest.fail(f"Integer to float conversion failed: {e}")

    def test_negative_numeric_values(self, tmp_path: Path):
        """Test handling of negative numeric values."""
        config_data = {
            "global_seed": -42,  # Negative integer
            "physics": {
                "cart_mass": 1.5,
                "pendulum1_mass": 0.2,
                "pendulum2_mass": 0.15,
                "pendulum1_length": 0.4,
                "pendulum2_length": 0.3,
                "pendulum1_com": 0.2,
                "pendulum2_com": 0.15,
                "pendulum1_inertia": 0.00265,
                "pendulum2_inertia": 0.00115,
                "gravity": -9.81,  # Negative gravity (unusual but numeric)
                "cart_friction": 0.2,
                "joint1_friction": 0.005,
                "joint2_friction": 0.004,
                "singularity_cond_threshold": 100000000.0
            },
            "simulation": {"duration": 1.0, "dt": 0.01},
            "controller_defaults": {},
            "controllers": {},
            "pso": {"n_particles": 10, "bounds": {"min": [1.0], "max": [2.0]}, "iters": 5},
            "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.01},
            "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "fdi": None
        }

        config_file = tmp_path / "test_config.yaml"
        with config_file.open('w') as f:
            yaml.dump(config_data, f)

        # Negative values may be accepted or rejected based on validation rules
        try:
            config = load_config(str(config_file))
            # If accepted, verify values
            assert config.global_seed == -42
            assert config.physics.gravity == -9.81
        except InvalidConfigurationError:
            # Rejection of negative values is acceptable for physics parameters
            pass

    def test_zero_numeric_values(self, tmp_path: Path):
        """Test handling of zero numeric values."""
        config_data = {
            "global_seed": 0,  # Zero integer
            "physics": {
                "cart_mass": 1.5,
                "pendulum1_mass": 0.2,
                "pendulum2_mass": 0.15,
                "pendulum1_length": 0.4,
                "pendulum2_length": 0.3,
                "pendulum1_com": 0.2,
                "pendulum2_com": 0.15,
                "pendulum1_inertia": 0.00265,
                "pendulum2_inertia": 0.00115,
                "gravity": 9.81,
                "cart_friction": 0.0,  # Zero friction
                "joint1_friction": 0.0,
                "joint2_friction": 0.0,
                "singularity_cond_threshold": 100000000.0
            },
            "simulation": {"duration": 1.0, "dt": 0.01},
            "controller_defaults": {},
            "controllers": {},
            "pso": {"n_particles": 10, "bounds": {"min": [1.0], "max": [2.0]}, "iters": 5},
            "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.01},
            "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "fdi": None
        }

        config_file = tmp_path / "test_config.yaml"
        with config_file.open('w') as f:
            yaml.dump(config_data, f)

        try:
            config = load_config(str(config_file))
            # Zero values should be preserved
            assert config.global_seed == 0
            assert config.physics.cart_friction == 0.0
        except Exception as e:
            pytest.fail(f"Zero numeric values were rejected: {e}")

    def test_extreme_numeric_values(self, tmp_path: Path):
        """Test handling of extreme numeric values."""
        config_data = {
            "global_seed": 2147483647,  # Large integer
            "physics": {
                "cart_mass": 1e6,  # Very large mass
                "pendulum1_mass": 1e-9,  # Very small mass
                "pendulum2_mass": 0.15,
                "pendulum1_length": 0.4,
                "pendulum2_length": 0.3,
                "pendulum1_com": 0.2,
                "pendulum2_com": 0.15,
                "pendulum1_inertia": 0.00265,
                "pendulum2_inertia": 0.00115,
                "gravity": 9.81,
                "cart_friction": 0.2,
                "joint1_friction": 0.005,
                "joint2_friction": 0.004,
                "singularity_cond_threshold": 1e15  # Very large threshold
            },
            "simulation": {"duration": 1.0, "dt": 1e-6},  # Very small timestep
            "controller_defaults": {},
            "controllers": {},
            "pso": {"n_particles": 10, "bounds": {"min": [1.0], "max": [2.0]}, "iters": 5},
            "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.01},
            "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "fdi": None
        }

        config_file = tmp_path / "test_config.yaml"
        with config_file.open('w') as f:
            yaml.dump(config_data, f)

        # Extreme values may be accepted or rejected based on validation rules
        try:
            config = load_config(str(config_file))
            # If accepted, values should be preserved
            assert config.global_seed == 2147483647
            assert config.physics.cart_mass == 1e6
            assert config.simulation.dt == 1e-6
        except InvalidConfigurationError:
            # Rejection of extreme values is acceptable
            pass