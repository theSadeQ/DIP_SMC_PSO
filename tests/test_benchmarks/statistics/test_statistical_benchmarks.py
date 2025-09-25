#==========================================================================================\\
#================ tests/test_benchmarks/test_statistical_benchmarks.py ==================\\
#==========================================================================================\\
"""
Tests for the statistical benchmarking harness (A‑06).

These tests validate that ``run_trials`` executes the requested number of
trials, produces a metrics list of the correct length and that confidence
interval widths decrease with increased sample size.  The simulation
function is stubbed to generate random but deterministic trajectories using
the provided seed to emulate variability across trials.  A simple
controller factory is used with a single gain dimension.
"""

from __future__ import annotations

import numpy as np
from unittest.mock import patch

from src.benchmarks.statistical_benchmarks_v2 import run_trials
from src.config import (
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


def _make_cfg() -> ConfigSchema:
    """Create a minimal configuration for benchmarking tests."""
    hil_cfg = HILConfig(
        plant_ip="127.0.0.1",
        plant_port=9000,
        controller_ip="127.0.0.1",
        controller_port=9001,
        extra_latency_ms=0.0,
        sensor_noise_std=0.0,
    )
    sim_cfg = SimulationConfig(
        duration=0.2,
        dt=0.1,
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
        n_evals=1,
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
    # Minimal PSO config (not used in benchmarks)
    pso_cfg = PSOConfig(
        n_particles=1,
        bounds=PSOBounds(min=[0.0], max=[1.0]),
        w=0.5,
        c1=1.0,
        c2=1.0,
        iters=1,
        n_processes=None,
        hyper_trials=None,
        hyper_search=None,
        study_timeout=None,
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


class SimpleController:
    """Controller stub providing required attributes."""
    n_gains = 1
    max_force = 1.0

    def __init__(self, gains: np.ndarray) -> None:
        self.gains = gains


def controller_factory(gains: np.ndarray) -> SimpleController:
    return SimpleController(gains)

controller_factory.n_gains = SimpleController.n_gains  # type: ignore


def dummy_simulate_system_batch_stat(
    controller_factory_func,
    gains_batch: np.ndarray,
    sim_time: float,
    dt: float | None = None,
    u_max: float | None = None,
    seed: int | None = None,
    params_list: Any = None,
) -> tuple:
    """Return random trajectories seeded by ``seed`` to emulate variability."""
    B = gains_batch.shape[0]
    # Two time steps; x dimensionality 1 for simplicity
    t = np.array([0.0, sim_time], dtype=float)
    rng = np.random.default_rng(seed)
    # Create random state trajectories depending on seed
    x_b = rng.normal(0.0, 1.0, size=(B, 2, 1))
    u_b = rng.normal(0.0, 0.5, size=(B, 1))
    sigma_b = rng.normal(0.0, 0.2, size=(B, 1))
    return t, x_b, u_b, sigma_b


def test_statistical_harness_sample_size_and_ci() -> None:
    """run_trials should return n_trials metrics and narrower CIs for larger n."""
    cfg = _make_cfg()
    with patch('src.core.vector_sim.simulate_system_batch', dummy_simulate_system_batch_stat):
        # 30 trials
        metrics30, ci30 = run_trials(
            controller_factory=controller_factory,
            cfg=cfg,
            n_trials=30,
            seed=42,
            randomise_physics=False,
            noise_std=0.0,
        )
        assert len(metrics30) == 30
        # 60 trials
        metrics60, ci60 = run_trials(
            controller_factory=controller_factory,
            cfg=cfg,
            n_trials=60,
            seed=42,
            randomise_physics=False,
            noise_std=0.0,
        )
        assert len(metrics60) == 60
    # Compare confidence interval widths: should shrink with more samples
    for key in ci30:
        mean30, ci_width30 = ci30[key]
        mean60, ci_width60 = ci60[key]
        # Avoid division by zero; if variance is zero, widths will be zero
        assert ci_width60 <= ci_width30 + 1e-9