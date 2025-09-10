# tests/test_core/test_stateful_simulation.py ==============\\\
import numpy as np

from src.core.simulation_runner import run_simulation

class SimpleStatefulController:
    """
    Minimal stateful controller used only for testing the runner.
    Tracks a scalar 'K' that evolves over time and records it in history.
    """
    def __init__(self, k0: float = 1.0, gain_step: float = 0.1):
        self.k0 = float(k0)
        self.gain_step = float(gain_step)

    # Optional protocol hooks the runner supports:
    def initialize_state(self):
        return {"K": self.k0}

    def initialize_history(self):
        # Start history with initial K for clear first/last comparison
        return {"K": [self.k0]}

    def compute_control(self, x, state_vars, history):
        # x is a numpy array; we use the first state component
        x0 = float(np.asarray(x).reshape(-1)[0])
        K = float(state_vars["K"])

        # Slight adaptation: push K in proportion to |x|
        K_next = K + self.gain_step * abs(x0)

        # Simple stabilizing-ish control
        u = -K * x0

        # Log the *next* K into history (so history length grows with steps)
        history["K"].append(K_next)

        next_state_vars = {"K": K_next}
        return u, next_state_vars, history


class SimpleDynamics:
    """
    Minimal dynamics with 1D state: x_{k+1} = x_k + dt * u
    """
    state_dim = 1

    def step(self, x, u, dt):
        x = np.asarray(x, dtype=float).reshape(-1)
        u = float(u)
        dt = float(dt)
        x_next = x.copy()
        x_next[0] = x[0] + dt * u
        return x_next


def test_stateful_controller_persists_state_and_history_is_exposed():
    ctrl = SimpleStatefulController(k0=1.0, gain_step=0.2)
    dyn = SimpleDynamics()

    t, x, u = run_simulation(
        controller=ctrl,
        dynamics_model=dyn,
        sim_time=1.0,
        dt=0.01,
        initial_state=np.array([1.0], dtype=float),
    )

    # The runner stores final history on the controller (non-breaking API)
    history = getattr(ctrl, "_last_history", None)
    assert isinstance(history, dict), "Runner should attach _last_history dict to controller."
    assert "K" in history and len(history["K"]) > 1, "Adaptive gain history 'K' should be tracked."

    k_initial, k_final = history["K"][0], history["K"][-1]
    assert not np.isclose(k_initial, k_final), (
        f"Adaptive gain K did not change (initial={k_initial}, final={k_final}). "
        "State propagation failed."
    )
#===================================================================================================\\\