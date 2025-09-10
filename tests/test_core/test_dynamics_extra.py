"""Additional invariants for the high‑fidelity dynamics model.

This module contains supplementary tests for the full double inverted
pendulum dynamics.  These tests exercise low‑level physics kernels
directly and compare the simplified and full models under zero input.
They are grouped into a single file for clarity and to minimise test
startup overhead.
"""

import numpy as np
import pytest


@pytest.mark.parametrize(
    "state",
    [
        np.array([0.0, np.pi / 6.0, np.pi / 8.0, 0.0, 0.0, 0.0], dtype=float),
        np.array([0.1, np.pi / 4.0, np.pi / 3.0, 0.0, 0.0, 0.0], dtype=float),
    ],
)
def test_inertia_shape_and_symmetry(full_dynamics, state):
    """The inertia matrix must be 3×3 and symmetric for all finite states."""
    H, C, G = full_dynamics._compute_physics_matrices(state)
    # Check inertia matrix shape and symmetry
    assert H.shape == (3, 3)
    assert np.allclose(H, H.T, rtol=1e-9, atol=1e-12)
    # Gravity vector must be length 3 or 3×1
    assert G.shape == (3,) or G.shape == (3, 1)


def test_passivity_energy_conservation_short_step(physics_cfg):
    """In the absence of friction the total energy should not increase under zero input."""
    from src.core.dynamics_full import FullDIPDynamics
    # Create a copy of the physics config with zero frictions
    p = physics_cfg.model_copy(update=dict(
        cart_friction=0.0,
        joint1_friction=0.0,
        joint2_friction=0.0,
    ))
    dyn = FullDIPDynamics(params=p)
    x = np.array([0.0, 0.1, 0.05, 0.1, 0.2, 0.3], dtype=float)
    E0 = dyn.total_energy(x)
    x1 = dyn.step(x, 0.0, 0.005)
    E1 = dyn.total_energy(x1)
    # Without input or friction, energy should not increase
    assert E1 <= E0 + 1e-6


def test_singularity_and_regularization(full_dynamics):
    """The inertia matrix eigenvalues should be finite even near singular configurations."""
    # A challenging configuration numerically (second pendulum inverted)
    x = np.array([0.0, 0.0, np.pi, 0.0, 0.0, 0.0], dtype=float)
    H, C, G = full_dynamics._compute_physics_matrices(x)
    w = np.linalg.eigvals(H)
    assert np.all(np.isfinite(w))


def test_simplified_vs_full_zero_input_close(physics_cfg):
    """Under zero input the simplified and full models should remain close for a short horizon."""
    from src.core.dynamics import DoubleInvertedPendulum
    from src.core.dynamics_full import FullDIPDynamics
    simple = DoubleInvertedPendulum(params=physics_cfg)
    full = FullDIPDynamics(params=physics_cfg)
    x0 = np.array([0.0, np.pi / 6.0, np.pi / 6.0, 0.0, 0.0, 0.0], dtype=float)
    dt, T = 0.01, 3.0
    N = int(T / dt)
    xs = np.zeros((N + 1, 6), dtype=float)
    xf = np.zeros_like(xs)
    xs[0] = x0
    xf[0] = x0
    for k in range(N):
        xs[k + 1] = simple.step(xs[k], 0.0, dt)
        xf[k + 1] = full.step(xf[k], 0.0, dt)
    err = np.linalg.norm(xs[-1] - xf[-1])
    # Models should not diverge dramatically under zero input
    assert np.isfinite(err) and err < 0.2


def test_numba_cache_regression(full_dynamics):
    """Repeated calls should not raise errors due to numba caching."""
    x = np.array([0.0, 0.2, -0.1, 0.0, 0.0, 0.0], dtype=float)
    # Call multiple times to exercise cached dispatch paths
    for _ in range(3):
        H, C, G = full_dynamics._compute_physics_matrices(x)
        assert np.all(np.isfinite(H))