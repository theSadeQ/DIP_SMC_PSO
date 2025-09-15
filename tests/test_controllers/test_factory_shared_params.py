#==========================================================================================\\
#================= tests/test_controllers/test_factory_shared_params.py =================\\
#==========================================================================================\\
"""
Controller factory — shared parameter inference & validation.

Checks that:
- Missing dt inherits from simulation.dt with a warning
- Missing max_force uses default with a warning
- Non-positive dt or max_force raise ConfigValueError
"""

from __future__ import annotations

import pytest

from src.controllers.factory import build_controller, ConfigValueError


@pytest.fixture
def cfg_mock():
    class Cfg:
        class simulation:  # noqa: N801
            dt = 0.02
        physics: dict = {}
        controllers = {"classical_smc": {}, "sta_smc": {}}
        controller_defaults = {
            "classical_smc": {"gains": [1, 2, 3, 4, 5, 6]},
            "sta_smc": {"gains": [1, 2, 3, 4, 5, 6]},
        }
    return Cfg()


def test_dt_inherits_from_simulation_with_warning(cfg_mock, caplog):
    caplog.set_level("WARNING")
    ctrl = build_controller(
        "sta_smc",
        {"gains": [1, 2, 3, 4, 5, 6], "boundary_layer": 0.02},
        config=cfg_mock,
        allow_unknown=False,
    )
    assert getattr(ctrl, "dt", None) == pytest.approx(0.02)
    # Warning about dt inheritance
    assert any("no 'dt' specified; inheriting dt=0.02" in rec.message for rec in caplog.records)


def test_max_force_defaults_with_warning(cfg_mock, caplog):
    caplog.set_level("WARNING")
    ctrl = build_controller(
        "classical_smc",
        {"gains": [1, 2, 3, 4, 5, 6], "boundary_layer": 0.02, "dt": 0.01},
        config=cfg_mock,
        allow_unknown=False,
    )
    assert getattr(ctrl, "max_force", None) == pytest.approx(20.0)
    assert any("no 'max_force' specified; using default max_force=20.0" in rec.message for rec in caplog.records)


@pytest.mark.parametrize("bad_dt", [0.0, -1e-3])
def test_invalid_dt_raises(bad_dt, cfg_mock):
    with pytest.raises(ConfigValueError):
        build_controller(
            "classical_smc",
            {"gains": [1, 2, 3, 4, 5, 6], "boundary_layer": 0.01, "dt": bad_dt, "max_force": 10.0},
            config=cfg_mock,
            allow_unknown=False,
        )


@pytest.mark.parametrize("bad_mf", [0.0, -5.0])
def test_invalid_max_force_raises(bad_mf, cfg_mock):
    with pytest.raises(ConfigValueError):
        build_controller(
            "sta_smc",
            {"gains": [1, 2, 3, 4, 5, 6], "boundary_layer": 0.02, "dt": 0.01, "max_force": bad_mf},
            config=cfg_mock,
            allow_unknown=False,
        )
