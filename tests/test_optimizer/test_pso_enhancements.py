"""
Tests for PSOTuner enhancements (A‑05): velocity clamping and inertia weight scheduling.

These tests verify that PSOTuner correctly computes and passes the velocity
clamp to ``pyswarms.single.GlobalBestPSO`` and that the linear inertia
weight schedule updates the optimiser’s options across iterations.  The
simulation routine is stubbed out to avoid running the full dynamics.  A
dummy PSO class records the inertia weights supplied during the manual
stepping loop.
"""

from __future__ import annotations

from typing import Any
import numpy as np
import pytest
from unittest.mock import patch

from src.optimizer.pso_optimizer import PSOTuner
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


def _make_minimal_config(*, w_schedule: Any = None, velocity_clamp: Any = None) -> ConfigSchema:
    """Construct a minimal configuration object with optional PSO parameters."""
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
        dt=0.05,
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
    pso_cfg = PSOConfig(
        n_particles=2,
        bounds=PSOBounds(min=[0.0], max=[1.0]),
        w=0.5,
        c1=1.0,
        c2=1.0,
        iters=3,
        n_processes=None,
        hyper_trials=None,
        hyper_search=None,
        study_timeout=None,
        seed=1,
        tune={},
        w_schedule=w_schedule,
        velocity_clamp=velocity_clamp,
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


class DummyController:
    """Simple controller stub used for PSO tests."""
    n_gains = 1
    max_force = 1.0

    def __init__(self, gains: np.ndarray) -> None:
        self.gains = gains

    def validate_gains(self, particles: np.ndarray) -> np.ndarray:
        # Accept all gains
        return np.ones(particles.shape[0], dtype=bool)


def dummy_controller_factory(gains: np.ndarray) -> DummyController:
    return DummyController(gains)

dummy_controller_factory.n_gains = DummyController.n_gains  # type: ignore


def dummy_simulate_system_batch(
    controller_factory: Any,
    gains_batch: np.ndarray,
    sim_time: float,
    dt: float | None = None,
    u_max: float | None = None,
    seed: int | None = None,
    params_list: Any = None,
) -> tuple:
    """Return trivial trajectories for PSO fitness evaluation.

    The returned arrays have minimal shapes required by PSOTuner._compute_cost_from_traj.
    """
    B = gains_batch.shape[0]
    # Two time steps
    t = np.array([0.0, sim_time], dtype=float)
    # State dims arbitrarily set to 3
    x_b = np.zeros((B, 2, 3), dtype=float)
    u_b = np.zeros((B, 1), dtype=float)
    sigma_b = np.zeros((B, 1), dtype=float)
    return t, x_b, u_b, sigma_b


def test_pso_velocity_clamp_passed() -> None:
    """PSOTuner should pass velocity_clamp to GlobalBestPSO with scaled limits."""
    cfg = _make_minimal_config(velocity_clamp=(0.1, 0.2))
    # Expected velocity limits: range = bmax - bmin = 1.0, so limits = (0.1, 0.2)
    expected_vclamp = (np.array([0.1]), np.array([0.2]))
    captured = {}

    class FakePSO:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            captured['velocity_clamp'] = kwargs.get('velocity_clamp')
            # Record options
            captured['options'] = kwargs.get('options')
            self.options = kwargs.get('options')
            self.swarm = type('Swarm', (), {'best_cost': 0.0, 'best_pos': np.zeros(1)})

        def optimize(self, fitness, iters: int):
            return 0.0, np.zeros(1)

    with patch('src.core.vector_sim.simulate_system_batch', dummy_simulate_system_batch):
        with patch('pyswarms.single.GlobalBestPSO', new=FakePSO):
            tuner = PSOTuner(controller_factory=dummy_controller_factory, config=cfg)
            res = tuner.optimise()
    # Check that velocity clamp was computed correctly
    assert 'velocity_clamp' in captured
    vmin, vmax = captured['velocity_clamp']
    assert np.allclose(vmin, expected_vclamp[0])
    assert np.allclose(vmax, expected_vclamp[1])


def test_pso_w_schedule_updates_inertia() -> None:
    """PSOTuner should update inertia weight according to w_schedule each step."""
    cfg = _make_minimal_config(w_schedule=(0.9, 0.4))
    w_history: list[float] = []

    class FakePSO:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.options = kwargs.get('options').copy()
            self.swarm = type('Swarm', (), {'best_cost': 0.0, 'best_pos': np.zeros(1)})

        def step(self, fitness):
            # Record current inertia weight
            w_history.append(float(self.options['w']))
            return 0.0, np.zeros(1)

        def optimize(self, fitness, iters: int):
            return 0.0, np.zeros(1)

    with patch('src.core.vector_sim.simulate_system_batch', dummy_simulate_system_batch):
        with patch('pyswarms.single.GlobalBestPSO', new=FakePSO):
            tuner = PSOTuner(controller_factory=dummy_controller_factory, config=cfg)
            _ = tuner.optimise()
    # Inertia weight should decrease linearly from 0.9 to 0.4 over 3 iterations
    assert len(w_history) == cfg.pso.iters
    assert np.isclose(w_history[0], 0.9)
    assert np.isclose(w_history[-1], 0.4)