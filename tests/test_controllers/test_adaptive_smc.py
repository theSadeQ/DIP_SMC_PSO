# tests/test_controllers/test_adaptive_smc.py ===============================\\\
import numpy as np
import pytest

from src.config import load_config
from src.controllers.factory import create_controller
from src.core.simulation_runner import run_simulation
from src.core.dynamics import DIPDynamics

class DisturbanceDynamics:
    def __init__(self, base_dynamics, disturbance_force=0.0):
        self._base = base_dynamics
        self.disturbance_force = disturbance_force
        self.state_dim = self._base.state_dim
    def step(self, state, u, dt):
        return self._base.step(state, u + self.disturbance_force, dt)

@pytest.fixture
def cfg():
    # Use the uploaded config path explicitly if needed
    return load_config('config.yaml')

@pytest.fixture
def adaptive_controller(cfg):
    # Build via factory so we exercise the config->factory->controller path
    return create_controller("adaptive_smc", config=cfg)

@pytest.fixture
def dynamics(cfg):
    return DIPDynamics(params=cfg.physics)

def test_adaptive_smc_gains_are_configurable(cfg, adaptive_controller):
    expected = cfg.controller_defaults.adaptive_smc.gains
    assert adaptive_controller.k1 == pytest.approx(expected[0])
    assert adaptive_controller.k2 == pytest.approx(expected[1])
    assert adaptive_controller.lam1 == pytest.approx(expected[2])
    assert adaptive_controller.lam2 == pytest.approx(expected[3])
    assert adaptive_controller.gamma == pytest.approx(expected[4])

def test_adaptive_gain_increases_on_large_error(adaptive_controller):
    state = np.array([0, 0.2, 0.2, 0, 0, 0], dtype=float)
    state_vars = adaptive_controller.initialize_state()
    history = adaptive_controller.initialize_history()
    initial_K = state_vars[0]
    for _ in range(10):
        _u, state_vars, history, _sigma = adaptive_controller.compute_control(state, state_vars, history)
    final_K = state_vars[0]
    assert final_K > initial_K
    assert final_K < adaptive_controller.K_max

def test_gain_remains_bounded_under_chattering(adaptive_controller, dynamics):
    disturbed = DisturbanceDynamics(dynamics, disturbance_force=1.0)
    initial_state = np.array([0.0, 0.01, -0.01, 0.0, 0.0, 0.0], dtype=float)
    t, states, u = run_simulation(
        controller=adaptive_controller,
        dynamics_model=disturbed,
        sim_time=5.0,
        dt=0.01,
        initial_state=initial_state,
    )
    # replay to recover K since runner doesn't expose internal state
    state_vars = adaptive_controller.initialize_state()
    history = adaptive_controller.initialize_history()
    for i in range(len(u)):
        _, state_vars, history, _ = adaptive_controller.compute_control(states[i], state_vars, history)
    final_K = state_vars[0]
    assert final_K < adaptive_controller.K_max
    assert final_K < 0.8 * adaptive_controller.K_max
#=======================================================================================================\\\