#==========================================================================================\\
#=================== tests/test_config/test_unknown_params_modes.py ====================\\
#==========================================================================================\\
"""
Config loader — permissive vs. strict unknown controller keys (end-to-end).
"""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from src.config import load_config, InvalidConfigurationError


def _write_cfg_with_unknown(p: Path) -> Path:
    cfg = {
        "global_seed": 42,
        "controller_defaults": {},
        "controllers": {
            "classical_smc": {
                "gains": [1, 1, 1, 1, 1, 1],
                "boundary_layer": 0.02,
                "unknown_toggle": True,
            }
        },
        "pso": {
            "n_particles": 1,
            "bounds": {"min": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "max": [1, 1, 1, 1, 1, 1]},
            "w": 0.5,
            "c1": 1.0,
            "c2": 1.0,
            "iters": 1,
        },
        "physics": {
            "cart_mass": 1.0,
            "pendulum1_mass": 1.0,
            "pendulum2_mass": 1.0,
            "pendulum1_length": 1.0,
            "pendulum2_length": 1.0,
            "pendulum1_com": 0.5,
            "pendulum2_com": 0.5,
            "pendulum1_inertia": 0.1,
            "pendulum2_inertia": 0.1,
            "gravity": 9.81,
            "cart_friction": 0.0,
            "joint1_friction": 0.0,
            "joint2_friction": 0.0,
        },
        "physics_uncertainty": {"n_evals": 1, "cart_mass": 0.0, "pendulum1_mass": 0.0, "pendulum2_mass": 0.0,
            "pendulum1_length": 0.0, "pendulum2_length": 0.0, "pendulum1_com": 0.0, "pendulum2_com": 0.0,
            "pendulum1_inertia": 0.0, "pendulum2_inertia": 0.0, "gravity": 0.0, "cart_friction": 0.0,
            "joint1_friction": 0.0, "joint2_friction": 0.0 },
        "simulation": {"duration": 0.1, "dt": 0.01, "initial_state": [0, 0, 0, 0, 0, 0], "use_full_dynamics": False},
        "verification": {"test_conditions": [], "integrators": ["euler"], "criteria": {}},
        "cost_function": {"weights": {"state_error": 1.0, "control_effort": 0.1, "control_rate": 0.1, "stability": 0.1},
            "baseline": {}, "instability_penalty": 1.0},
        "sensors": {"angle_noise_std": 0.0, "position_noise_std": 0.0, "quantization_angle": 0.0, "quantization_position": 0.0},
        "hil": {"plant_ip": "127.0.0.1", "plant_port": 5555, "controller_ip": "127.0.0.1", "controller_port": 5556,
            "extra_latency_ms": 0.0, "sensor_noise_std": 0.0},
        "fdi": None,
    }
    p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return p


def test_strict_mode_rejects_unknown_keys(tmp_path: Path):
    cfg_path = _write_cfg_with_unknown(tmp_path / "cfg_unknown.yaml")
    with pytest.raises(InvalidConfigurationError):
        load_config(cfg_path, allow_unknown=False)


def test_permissive_mode_collects_unknown_params(tmp_path: Path):
    cfg_path = _write_cfg_with_unknown(tmp_path / "cfg_unknown.yaml")
    cfg = load_config(cfg_path, allow_unknown=True)
    ctrl_cfg = cfg.controllers["classical_smc"]
    assert getattr(ctrl_cfg, "unknown_params", {}).get("unknown_toggle") is True

