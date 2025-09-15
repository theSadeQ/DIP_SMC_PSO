#==========================================================================================\\\
#====================== tests/test_app/test_streamlit_disturbance.py =====================\\\
#==========================================================================================\\\
"""
Streamlit app — disturbance wrapper correctness for DisturbedDynamics.
"""

from __future__ import annotations

import numpy as np

from streamlit_app import DisturbedDynamics


class _BaseModel:
    def __init__(self):
        self.state_dim = 3
        self.flag = 123  # arbitrary attribute to test forwarding via __getattr__

    def default_state(self):
        return np.zeros(self.state_dim)

    def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        # Simple integrator: x_{k+1} = x_k + dt * [u, 2u, 3u]
        return state + dt * np.array([u, 2 * u, 3 * u], dtype=float)


def test_disturbance_applies_in_window_and_time_advances():
    base = _BaseModel()
    # Rect pulse of magnitude 2.0 on [0.1, 0.3)
    def d_fn(t: float) -> float:
        return 2.0 if (0.1 <= t < 0.3) else 0.0

    dd = DisturbedDynamics(base, d_fn)
    x = dd.default_state()
    dt = 0.1

    # t=0.0 -> no disturbance
    x = dd.step(x, u=1.0, dt=dt)
    np.testing.assert_allclose(x, np.array([0.1, 0.2, 0.3]), atol=1e-12)

    # t=0.1 -> disturbance active, u_eff = 1.0 + 2.0 = 3.0
    x = dd.step(x, u=1.0, dt=dt)
    np.testing.assert_allclose(x, np.array([0.4, 0.8, 1.2]), atol=1e-12)

    # t=0.2 -> still active
    x2 = dd.step(x, u=1.0, dt=dt)
    np.testing.assert_allclose(x2 - x, np.array([0.3, 0.6, 0.9]), atol=1e-12)

    # t=0.3 -> inactive again
    x3 = dd.step(x2, u=1.0, dt=dt)
    np.testing.assert_allclose(x3 - x2, np.array([0.1, 0.2, 0.3]), atol=1e-12)

    # Attribute forwarding works
    assert dd.flag == 123

