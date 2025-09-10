"""
Unit tests for the PSO core routines in ``src/optimizer/pso_optimizer.py``.

These tests cover the helper functions ``_normalise`` and ``_combine_costs``, as
well as the robust sampling mechanism in ``PSOTuner._iter_perturbed_physics``.
They intentionally avoid integration over the full PSO tuning pipeline to
remain fast and deterministic.  All tests rely on minimal configuration
objects created programmatically rather than reading from disk.

To ensure that modules under ``src/`` in the project can be imported when
these tests execute outside of the project root, we insert the project's
``DIP_SMC_PSO/src`` directory onto ``sys.path`` at runtime.  Without this
insertion ``import src.optimizer`` would fail when ``pytest`` collects the
test suite from a different working directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Dynamically add the project’s ``src`` directory to ``sys.path``.
#
# These tests reside outside of the ``DIP_SMC_PSO`` package.  During test
# discovery the working directory may not include the package root, so we
# insert the absolute path to ``DIP_SMC_PSO/src`` to ensure that imports
# such as ``controllers.factory`` and ``core.simulation_runner`` resolve
# correctly in a location‑agnostic way.
project_root = Path(__file__).resolve().parents[2] / "DIP_SMC_PSO/src"
sys.path.insert(0, str(project_root))

import numpy as np
import pytest

from src.optimizer.pso_optimizer import _normalise, PSOTuner  # type: ignore
from src.config import (  # type: ignore
    ConfigSchema,
    HILConfig,
    SimulationConfig,
    PhysicsConfig,
    PhysicsUncertaintySchema,
    ControllersConfig,
    PSOConfig,
    PSOBounds,
    CostFunctionConfig,
    CostFunctionWeights,
    VerificationConfig,
    SensorsConfig,
)


def _create_config(n_evals: int) -> ConfigSchema:
    """Create a minimal ConfigSchema with a specified number of uncertainty samples."""
    hil_cfg = HILConfig(
        plant_ip="127.0.0.1",
        plant_port=9000,
        controller_ip="127.0.0.1",
        controller_port=9001,
        extra_latency_ms=0.0,
        sensor_noise_std=0.0,
    )
    sim_cfg = SimulationConfig(
        duration=0.1,
        dt=0.01,
        initial_state=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        use_full_dynamics=False,
    )
    physics_cfg = PhysicsConfig(
        cart_mass=1.0,
        pendulum1_mass=1.0,
        pendulum2_mass=1.0,
        pendulum1_length=1.0,
        pendulum2_length=1.0,
        pendulum1_com=0.5,
        pendulum2_com=0.5,
        pendulum1_inertia=0.1,
        pendulum2_inertia=0.1,
        gravity=9.81,
        cart_friction=0.1,
        joint1_friction=0.01,
        joint2_friction=0.01,
    )
    uncertainty_cfg = PhysicsUncertaintySchema(
        n_evals=int(n_evals),
        cart_mass=0.0,
        pendulum1_mass=0.0,
        pendulum2_mass=0.0,
        pendulum1_length=0.0,
        pendulum2_length=0.0,
        pendulum1_com=0.0,
        pendulum2_com=0.0,
        pendulum1_inertia=0.0,
        pendulum2_inertia=0.0,
        gravity=0.0,
        cart_friction=0.0,
        joint1_friction=0.0,
        joint2_friction=0.0,
    )
    controllers_cfg = ControllersConfig()
    pso_cfg = PSOConfig(
        n_particles=1,
        bounds=PSOBounds(min=[0.0], max=[1.0]),
        w=0.5,
        c1=1.0,
        c2=1.0,
        iters=1,
        n_processes=1,
        hyper_trials=1,
        hyper_search={},
        study_timeout=1,
        seed=1,
        tune={},
    )
    weights = CostFunctionWeights(
        state_error=1.0,
        control_effort=0.1,
        control_rate=0.1,
        stability=0.1,
    )
    cost_cfg = CostFunctionConfig(weights=weights, baseline={}, instability_penalty=1.0)
    verification_cfg = VerificationConfig(test_conditions=[], integrators=["euler"], criteria={})
    sensors_cfg = SensorsConfig(
        angle_noise_std=0.0,
        position_noise_std=0.0,
        quantization_angle=0.0,
        quantization_position=0.0,
    )
    return ConfigSchema(
        global_seed=1,
        controller_defaults=controllers_cfg,
        controllers=controllers_cfg,
        pso=pso_cfg,
        physics=physics_cfg,
        physics_uncertainty=uncertainty_cfg,
        simulation=sim_cfg,
        verification=verification_cfg,
        cost_function=cost_cfg,
        sensors=sensors_cfg,
        hil=hil_cfg,
        fdi=None,
    )


def test_normalise_division_by_zero() -> None:
    """When the denominator is near zero, _normalise should return the input unchanged."""
    arr = np.array([1.0, 2.0, 3.0])
    out = _normalise(arr, 0.0)
    assert np.allclose(out, arr)


def test_normalise_regular_division() -> None:
    """_normalise should divide by denom when it is sufficiently large."""
    arr = np.array([2.0, 4.0, 6.0])
    out = _normalise(arr, 2.0)
    assert np.allclose(out, arr / 2.0)


def test_combine_costs_1d() -> None:
    """For a 1D array, _combine_costs should return 0.7*mean + 0.3*max."""
    arr = np.array([1.0, 2.0, 3.0])
    expected = 0.7 * arr.mean() + 0.3 * arr.max()
    out = PSOTuner._combine_costs(arr)
    assert np.isclose(out, expected)


def test_combine_costs_2d() -> None:
    """For a 2D array, _combine_costs should operate column-wise."""
    arr = np.array([[1.0, 2.0], [3.0, 4.0]])
    # mean over rows per column: [2, 3]; max per column: [3, 4]
    expected = 0.7 * np.array([2.0, 3.0]) + 0.3 * np.array([3.0, 4.0])
    out = PSOTuner._combine_costs(arr)
    assert out.shape == expected.shape
    assert np.allclose(out, expected)


def test_combine_costs_invalid_returns_penalty() -> None:
    """NaN or Inf in costs should trigger the instability penalty."""
    # 1D with NaN
    arr_nan = np.array([1.0, np.nan, 2.0])
    out = PSOTuner._combine_costs(arr_nan)
    assert out == PSOTuner.INSTABILITY_PENALTY
    # 2D with Inf in one column
    arr_inf = np.array([[np.inf, 1.0], [2.0, 3.0]])
    out2 = PSOTuner._combine_costs(arr_inf)
    # Both columns should be penalized
    assert out2.shape == (2,)
    assert np.allclose(out2, np.full(2, PSOTuner.INSTABILITY_PENALTY))


def test_iter_perturbed_physics_nominal() -> None:
    """When n_evals=1, PSOTuner should yield only the nominal parameters."""
    cfg = _create_config(n_evals=1)
    tuner = PSOTuner(controller_factory=lambda *args, **kwargs: None, config=cfg)
    params_list = list(tuner._iter_perturbed_physics())
    assert len(params_list) == 1


def test_iter_perturbed_physics_multiple() -> None:
    """When n_evals>1, PSOTuner should yield n_evals sets of parameters."""
    cfg = _create_config(n_evals=3)
    tuner = PSOTuner(controller_factory=lambda *args, **kwargs: None, config=cfg)
    params_list = list(tuner._iter_perturbed_physics())
    assert len(params_list) == 3