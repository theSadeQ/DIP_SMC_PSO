#=======================================================================================================\\\
# tests\test_core\test_config.py =======================================================================\\\
#=======================================================================================================\\\

import pytest
import yaml
from pathlib import Path
from pydantic import ValidationError
from src.config import load_config, ControllersConfig, ConfigSchema, PhysicsConfig, ControllerConfig, InvalidConfigurationError

def test_config_loads_and_maps_controllers():
    cfg = load_config("config.yaml", allow_unknown=True)
    assert isinstance(cfg, ConfigSchema)
    assert isinstance(cfg.controllers, ControllersConfig)
    keys = set(cfg.controllers.keys())
    assert {"classical_smc", "sta_smc", "adaptive_smc"}.issubset(keys)
    adaptive = cfg.controllers["adaptive_smc"]
    assert getattr(adaptive, "max_force") is not None
    assert getattr(adaptive, "dt") is not None

@pytest.fixture
def valid_physics_data() -> dict:
    """Baseline valid dict for physics config (assumes config.yaml exists)."""
    return load_config("config.yaml", allow_unknown=True).physics.model_dump()

def test_physics_config_rejects_zero_mass(valid_physics_data):
    invalid = dict(valid_physics_data)
    invalid["pendulum2_mass"] = 0.0
    with pytest.raises(ValidationError) as exc_info:
        PhysicsConfig(**invalid)
    assert "pendulum2_mass must be strictly positive" in str(exc_info.value)

def test_physics_config_rejects_negative_inertia(valid_physics_data):
    invalid = dict(valid_physics_data)
    invalid["pendulum1_inertia"] = -0.001
    with pytest.raises(ValidationError) as exc_info:
        PhysicsConfig(**invalid)
    assert "pendulum1_inertia must be strictly positive" in str(exc_info.value)

def test_physics_config_rejects_invalid_com(valid_physics_data):
    invalid = dict(valid_physics_data)
    # CoM equal to length (invalid)
    invalid["pendulum1_com"] = invalid["pendulum1_length"]
    with pytest.raises(ValidationError) as exc_info:
        PhysicsConfig(**invalid)
    assert "pendulum1_com" in str(exc_info.value) and "must be less than pendulum1_length" in str(exc_info.value)

    # CoM greater than length (invalid)
    invalid["pendulum1_com"] = valid_physics_data["pendulum1_length"] + 0.1
    with pytest.raises(ValidationError) as exc_info:
        PhysicsConfig(**invalid)
    assert "pendulum1_com" in str(exc_info.value) and "must be less than pendulum1_length" in str(exc_info.value)

def test_physics_config_rejects_nonpositive_com(valid_physics_data):
    invalid = dict(valid_physics_data)
    invalid["pendulum2_com"] = 0.0
    with pytest.raises(ValidationError) as exc_info:
        PhysicsConfig(**invalid)
    assert "pendulum2_com must be strictly positive" in str(exc_info.value)



def test_controller_config_forbids_extra_rate_weight_unit():
    with pytest.raises(ValidationError):
        ControllerConfig(
            gains=[1.0],  # required field
            rate_weight=1.0,  # forbidden
        )





def test_load_config_rejects_rate_weight_in_yaml(tmp_path: Path):
    cfg = {
        "controllers": {
            "classical_smc": {
                "max_force": 10.0,
                "boundary_layer": 0.1,
                "rate_weight": 1.0,  # forbidden
            }
        }
    }
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    with pytest.raises(InvalidConfigurationError):
        load_config(str(p))
#========================================================================\\\