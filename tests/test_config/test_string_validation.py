#==========================================================================================\\\
#=================== tests/test_config/test_string_validation.py ========================\\\
#==========================================================================================\\\
"""
String Type Validation Tests.

SINGLE JOB: Test only string field validation in configuration.
- String field type checking
- String field rejection of non-string types
- String field error message validation
"""

import pytest
import yaml
from pathlib import Path

from src.config import (
    load_config,
    InvalidConfigurationError
)


class TestStringValidation:
    """Test string type validation."""

    def test_integrator_string_validation(self, tmp_path: Path):
        """Test that integrator field requires string values."""
        config_data = {
            "global_seed": 42,
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
            "verification": {
                "test_conditions": [],
                "integrators": [123],  # Should be string, not int
                "criteria": {}
            },
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
        # Should indicate string type requirement
        assert "integrators" in error_msg.lower() or "verification" in error_msg.lower()

    def test_valid_string_acceptance(self, tmp_path: Path):
        """Test that valid strings are accepted."""
        config_data = {
            "global_seed": 42,
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
            "verification": {
                "test_conditions": [],
                "integrators": ["euler", "rk4"],  # Valid strings
                "criteria": {}
            },
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "fdi": None
        }

        config_file = tmp_path / "test_config.yaml"
        with config_file.open('w') as f:
            yaml.dump(config_data, f)

        # Should load successfully
        try:
            config = load_config(str(config_file))
            assert config is not None
        except Exception as e:
            pytest.fail(f"Valid string configuration was rejected: {e}")

    def test_empty_string_validation(self, tmp_path: Path):
        """Test validation of empty strings."""
        config_data = {
            "global_seed": 42,
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
            "verification": {
                "test_conditions": [],
                "integrators": ["", "euler"],  # Empty string
                "criteria": {}
            },
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "fdi": None
        }

        config_file = tmp_path / "test_config.yaml"
        with config_file.open('w') as f:
            yaml.dump(config_data, f)

        # May be rejected depending on validation rules
        try:
            config = load_config(str(config_file))
            # If accepted, empty strings should be preserved
            if hasattr(config, 'verification') and hasattr(config.verification, 'integrators'):
                integrators = config.verification.integrators
                assert "" in integrators
        except InvalidConfigurationError:
            # May be rejected for empty string - this is acceptable
            pass

    def test_numeric_string_conversion(self, tmp_path: Path):
        """Test handling of numeric strings."""
        config_data = {
            "global_seed": 42,
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
            "verification": {
                "test_conditions": [],
                "integrators": ["123", "euler"],  # Numeric string
                "criteria": {}
            },
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "fdi": None
        }

        config_file = tmp_path / "test_config.yaml"
        with config_file.open('w') as f:
            yaml.dump(config_data, f)

        # Numeric strings should be valid strings
        try:
            config = load_config(str(config_file))
            if hasattr(config, 'verification') and hasattr(config.verification, 'integrators'):
                integrators = config.verification.integrators
                assert "123" in integrators
        except InvalidConfigurationError as e:
            pytest.fail(f"Numeric string was rejected: {e}")

    def test_boolean_to_string_rejection(self, tmp_path: Path):
        """Test that boolean values are rejected for string fields."""
        config_data = {
            "global_seed": 42,
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
            "verification": {
                "test_conditions": [],
                "integrators": [True, "euler"],  # Boolean instead of string
                "criteria": {}
            },
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