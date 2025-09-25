#==========================================================================================\\\
#================== tests/test_config/test_unknown_key_validation.py ====================\\\
#==========================================================================================\\\
"""
Unknown Key Validation Tests.

This test suite focuses specifically on validating rejection of unknown configuration keys:
- Single unknown keys in different sections
- Multiple unknown keys with aggregated errors
- Error message formatting and consistency
"""

import pytest
import yaml
from pathlib import Path
from tempfile import NamedTemporaryFile

from src.config import (
    load_config,
    ConfigSchema,
    InvalidConfigurationError,
    PhysicsConfig,
    ControllersConfig,
    PSOConfig,
    SimulationConfig
)


class ErrorMessages:
    """Deterministic error message constants."""
    EXTRA_FORBIDDEN = "Extra inputs are not permitted"
    VALIDATION_FAILED_PREFIX = "Configuration validation failed:"
    ERROR_FORMAT = "  - {}: {}"


class TestUnknownKeyValidation:
    """Test rejection of unknown configuration keys with aggregated errors."""

    def test_single_unknown_key_physics(self, tmp_path: Path):
        """Test rejection of single unknown key in physics section."""
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
                "singularity_cond_threshold": 100000000.0,
                "unknown_physics_param": 42.0  # Unknown key
            },
            # Minimal required sections
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
        assert ErrorMessages.VALIDATION_FAILED_PREFIX in error_msg
        assert "physics.unknown_physics_param" in error_msg
        assert ErrorMessages.EXTRA_FORBIDDEN in error_msg

    def test_single_unknown_key_simulation(self, tmp_path: Path):
        """Test rejection of single unknown key in simulation section."""
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
            "simulation": {
                "duration": 1.0,
                "dt": 0.01,
                "unknown_sim_param": "invalid"  # Unknown key
            },
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
        assert ErrorMessages.VALIDATION_FAILED_PREFIX in error_msg
        assert "simulation.unknown_sim_param" in error_msg
        assert ErrorMessages.EXTRA_FORBIDDEN in error_msg

    def test_multiple_unknown_keys_aggregated(self, tmp_path: Path):
        """Test aggregated error messages for multiple unknown keys."""
        config_data = {
            "global_seed": 42,
            "unknown_root_key": "invalid",  # Unknown at root
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
                "singularity_cond_threshold": 100000000.0,
                "unknown_physics_1": 42.0,  # Unknown key 1
                "unknown_physics_2": 99.0   # Unknown key 2
            },
            "simulation": {
                "duration": 1.0,
                "dt": 0.01,
                "unknown_sim_key": "also_invalid"  # Another unknown key
            },
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
        assert ErrorMessages.VALIDATION_FAILED_PREFIX in error_msg

        # Should contain all unknown keys
        assert "unknown_root_key" in error_msg
        assert "physics.unknown_physics_1" in error_msg
        assert "physics.unknown_physics_2" in error_msg
        assert "simulation.unknown_sim_key" in error_msg

        # Should have consistent error format
        assert ErrorMessages.EXTRA_FORBIDDEN in error_msg

    def test_nested_unknown_keys(self, tmp_path: Path):
        """Test rejection of unknown keys in nested structures."""
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
            "pso": {
                "n_particles": 10,
                "bounds": {"min": [1.0], "max": [2.0]},
                "iters": 5,
                "unknown_nested_key": {  # Unknown nested structure
                    "deep_unknown": "value"
                }
            },
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
        assert ErrorMessages.VALIDATION_FAILED_PREFIX in error_msg
        assert "pso.unknown_nested_key" in error_msg

    def test_unknown_key_error_determinism(self, tmp_path: Path):
        """Test that unknown key errors are deterministic."""
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
                "singularity_cond_threshold": 100000000.0,
                "unknown_param": 42.0
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

        error_messages = []

        # Load same config multiple times
        for i in range(3):
            with config_file.open('w') as f:
                yaml.dump(config_data, f)

            with pytest.raises(InvalidConfigurationError) as exc_info:
                load_config(str(config_file))

            error_messages.append(str(exc_info.value))

        # All error messages should be identical
        assert len(set(error_messages)) == 1, "Error messages were not deterministic"