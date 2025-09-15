#==========================================================================================\\\
#================= tests/config_validation/test_config_validation.py ===================\\\
#==========================================================================================\\\
"""
Strict configuration validation tests with aggregated error messages.

This module tests the configuration validation system's ability to:
- Reject unknown keys with aggregated error messages  
- Reject wrong types with aggregated error messages
- Provide deterministic error message structure
- Handle both positive and negative validation cases
"""

import pytest
import yaml
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Any

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
    """Deterministic error message constants matching existing patterns."""
    
    # From Pydantic validation - these are the actual strings used
    EXTRA_FORBIDDEN = "Extra inputs are not permitted"
    TYPE_STR = "Input should be a valid string"  
    TYPE_INT = "Input should be a valid integer"
    TYPE_FLOAT = "Input should be a valid number"
    TYPE_BOOL = "Input should be a valid boolean"
    TYPE_LIST = "Input should be a valid list"
    TYPE_DICT = "Input should be a valid dictionary"
    
    # From existing config.py error handling
    VALIDATION_FAILED_PREFIX = "Configuration validation failed:"
    ERROR_FORMAT = "  - {}: {}"  # Matches config.py:498 format


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
            "hil": {"plant_ip": "127.0.0.1", "plant_port": 9000, "controller_ip": "127.0.0.1", "controller_port": 9001}
        }

        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml.safe_dump(config_data))

        with pytest.raises(InvalidConfigurationError) as exc_info:
            load_config(str(config_file))

        error_msg = str(exc_info.value)
        assert ErrorMessages.VALIDATION_FAILED_PREFIX in error_msg
        assert "physics.unknown_physics_param" in error_msg
        assert ErrorMessages.EXTRA_FORBIDDEN in error_msg

    def test_multiple_unknown_keys_aggregated(self, tmp_path: Path):
        """Test aggregation of multiple unknown keys across different sections."""
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
                "unknown_param_1": 1.0,  # Unknown in physics
                "unknown_param_2": 2.0   # Another unknown in physics
            },
            "simulation": {
                "duration": 1.0,
                "dt": 0.01,
                "unknown_sim_param": True  # Unknown in simulation
            },
            # Minimal required sections
            "controller_defaults": {},
            "controllers": {},
            "pso": {"n_particles": 10, "bounds": {"min": [1.0], "max": [2.0]}, "iters": 5},
            "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.01},
            "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "hil": {"plant_ip": "127.0.0.1", "plant_port": 9000, "controller_ip": "127.0.0.1", "controller_port": 9001}
        }

        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml.safe_dump(config_data))

        with pytest.raises(InvalidConfigurationError) as exc_info:
            load_config(str(config_file))

        error_msg = str(exc_info.value)

        # Verify aggregated error structure
        assert ErrorMessages.VALIDATION_FAILED_PREFIX in error_msg

        # Verify all unknown keys are mentioned
        assert "unknown_root_key" in error_msg
        assert "physics.unknown_param_1" in error_msg
        assert "physics.unknown_param_2" in error_msg  
        assert "simulation.unknown_sim_param" in error_msg

        # Verify deterministic error pattern
        assert ErrorMessages.EXTRA_FORBIDDEN in error_msg


class TestTypeValidation:
    """Test rejection of wrong types with aggregated errors."""

    def test_single_wrong_type(self, tmp_path: Path):
        """Test rejection of single wrong type with clear error message."""
        config_data = {
            "global_seed": "not_an_integer",  # Should be int
            # Minimal required sections
            "physics": {
                "cart_mass": 1.5, "pendulum1_mass": 0.2, "pendulum2_mass": 0.15,
                "pendulum1_length": 0.4, "pendulum2_length": 0.3,
                "pendulum1_com": 0.2, "pendulum2_com": 0.15,
                "pendulum1_inertia": 0.00265, "pendulum2_inertia": 0.00115,
                "gravity": 9.81, "cart_friction": 0.2,
                "joint1_friction": 0.005, "joint2_friction": 0.004,
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
            "hil": {"plant_ip": "127.0.0.1", "plant_port": 9000, "controller_ip": "127.0.0.1", "controller_port": 9001}
        }

        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml.safe_dump(config_data))

        with pytest.raises(InvalidConfigurationError) as exc_info:
            load_config(str(config_file))

        error_msg = str(exc_info.value)
        assert ErrorMessages.VALIDATION_FAILED_PREFIX in error_msg
        assert "global_seed" in error_msg
        assert ErrorMessages.TYPE_INT in error_msg

    def test_multiple_wrong_types_aggregated(self, tmp_path: Path):
        """Test aggregation of multiple type errors across sections."""
        config_data = {
            "global_seed": "not_int",  # Should be int
            "physics": {
                "cart_mass": "not_float",  # Should be float
                "pendulum1_mass": 0.2,
                "pendulum2_mass": 0.15,
                "pendulum1_length": 0.4,
                "pendulum2_length": 0.3,
                "pendulum1_com": 0.2,
                "pendulum2_com": 0.15,
                "pendulum1_inertia": 0.00265,
                "pendulum2_inertia": 0.00115,
                "gravity": 9.81,
                "cart_friction": ["not_float"],  # Should be float
                "joint1_friction": 0.005,
                "joint2_friction": 0.004,
                "singularity_cond_threshold": 100000000.0
            },
            "simulation": {
                "duration": 1.0,
                "dt": 0.01,
                "use_full_dynamics": "not_bool"  # Should be bool
            },
            # Minimal required sections
            "controller_defaults": {},
            "controllers": {},
            "pso": {"n_particles": 10, "bounds": {"min": [1.0], "max": [2.0]}, "iters": 5},
            "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.01},
            "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "hil": {"plant_ip": "127.0.0.1", "plant_port": 9000, "controller_ip": "127.0.0.1", "controller_port": 9001}
        }

        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml.safe_dump(config_data))

        with pytest.raises(InvalidConfigurationError) as exc_info:
            load_config(str(config_file))

        error_msg = str(exc_info.value)

        # Verify aggregated structure
        assert ErrorMessages.VALIDATION_FAILED_PREFIX in error_msg

        # Verify all type errors are mentioned
        assert "global_seed" in error_msg
        assert "physics.cart_mass" in error_msg
        assert "physics.cart_friction" in error_msg
        assert "simulation.use_full_dynamics" in error_msg

        # Verify deterministic type error messages
        assert ErrorMessages.TYPE_INT in error_msg
        # At least one of the number/string type errors should appear
        type_errors = [ErrorMessages.TYPE_FLOAT, ErrorMessages.TYPE_STR]
        assert any(err in error_msg for err in type_errors)


class TestPositiveValidation:
    """Test that valid configurations are accepted."""

    def test_minimal_valid_config(self, tmp_path: Path):
        """Test that a minimal valid configuration loads successfully."""
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
                "w": 0.7,
                "c1": 2.0,
                "c2": 2.0
            },
            "physics_uncertainty": {
                "n_evals": 1,
                "cart_mass": 0.01,
                "pendulum1_mass": 0.01,
                "pendulum2_mass": 0.01,
                "pendulum1_length": 0.01,
                "pendulum2_length": 0.01,
                "pendulum1_com": 0.01,
                "pendulum2_com": 0.01,
                "pendulum1_inertia": 0.01,
                "pendulum2_inertia": 0.01,
                "gravity": 0.0,
                "cart_friction": 0.01,
                "joint1_friction": 0.01,
                "joint2_friction": 0.01
            },
            "verification": {
                "test_conditions": [],
                "integrators": ["euler"],
                "criteria": {}
            },
            "cost_function": {
                "weights": {
                    "state_error": 50.0,
                    "control_effort": 0.2,
                    "control_rate": 0.1,
                    "stability": 0.1
                },
                "baseline": {"gains": [1.0, 2.0, 3.0]},
                "instability_penalty": 1000.0
            },
            "sensors": {},
            "hil": {
                "plant_ip": "127.0.0.1",
                "plant_port": 9000,
                "controller_ip": "127.0.0.1",
                "controller_port": 9001
            }
        }

        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml.safe_dump(config_data))

        # Should load without error
        cfg = load_config(str(config_file))
        assert isinstance(cfg, ConfigSchema)
        assert cfg.global_seed == 42
        assert cfg.physics.cart_mass == 1.5
        assert cfg.simulation.duration == 1.0

    def test_full_config_loads(self):
        """Test that the actual config.yaml loads successfully."""
        cfg = load_config("config.yaml", allow_unknown=True)
        assert isinstance(cfg, ConfigSchema)
        assert cfg.global_seed is not None
        assert isinstance(cfg.physics, PhysicsConfig)
        assert isinstance(cfg.controllers, ControllersConfig)


class TestMixedValidationErrors:
    """Test combinations of unknown keys and type errors."""

    def test_unknown_keys_and_wrong_types_combined(self, tmp_path: Path):
        """Test that both unknown keys and type errors are aggregated together."""
        config_data = {
            "global_seed": "not_int",  # Type error
            "unknown_root": "value",   # Unknown key
            "physics": {
                "cart_mass": "not_float",  # Type error
                "unknown_physics": 42,     # Unknown key
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
            # Minimal required sections
            "simulation": {"duration": 1.0, "dt": 0.01},
            "controller_defaults": {},
            "controllers": {},
            "pso": {"n_particles": 10, "bounds": {"min": [1.0], "max": [2.0]}, "iters": 5},
            "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.01},
            "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "hil": {"plant_ip": "127.0.0.1", "plant_port": 9000, "controller_ip": "127.0.0.1", "controller_port": 9001}
        }

        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml.safe_dump(config_data))

        with pytest.raises(InvalidConfigurationError) as exc_info:
            load_config(str(config_file))

        error_msg = str(exc_info.value)

        # Verify both types of errors are present
        assert ErrorMessages.VALIDATION_FAILED_PREFIX in error_msg

        # Type errors
        assert "global_seed" in error_msg
        assert "physics.cart_mass" in error_msg
        assert ErrorMessages.TYPE_INT in error_msg

        # Unknown key errors  
        assert "unknown_root" in error_msg
        assert "physics.unknown_physics" in error_msg
        assert ErrorMessages.EXTRA_FORBIDDEN in error_msg


class TestErrorMessageDeterminism:
    """Test that error messages are deterministic and predictable."""

    def test_error_message_structure_consistent(self, tmp_path: Path):
        """Test that error message structure is consistent across runs."""
        config_data = {
            "unknown_key": "value",
            "global_seed": "not_int",
            # Minimal required sections with errors
            "physics": {"cart_mass": "not_float", "unknown_physics": 1},
            "simulation": {"duration": 1.0, "dt": 0.01},
            "controller_defaults": {},
            "controllers": {},
            "pso": {"n_particles": 10, "bounds": {"min": [1.0], "max": [2.0]}, "iters": 5},
            "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.01},
            "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
            "cost_function": {"weights": {}, "baseline": {}},
            "sensors": {},
            "hil": {"plant_ip": "127.0.0.1", "plant_port": 9000, "controller_ip": "127.0.0.1", "controller_port": 9001}
        }

        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml.safe_dump(config_data))

        # Run twice to ensure deterministic output
        errors = []
        for i in range(2):
            with pytest.raises(InvalidConfigurationError) as exc_info:
                load_config(str(config_file))
            errors.append(str(exc_info.value))

        # Error messages should be identical
        assert errors[0] == errors[1], "Error messages should be deterministic"

        # Verify structure matches config.py:504-506 format
        error_msg = errors[0]
        assert error_msg.startswith(ErrorMessages.VALIDATION_FAILED_PREFIX)
        assert "  - " in error_msg  # Dot-path format from config.py:498