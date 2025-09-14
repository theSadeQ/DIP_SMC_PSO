"""
c5u-mpl enforcement: headless Matplotlib tests with Agg backend and show-ban.
This file MUST be imported before any test that imports matplotlib.pyplot.
"""
import os
import warnings
import matplotlib

# 1) Enforce backend as early as possible.
os.environ.setdefault("MPLBACKEND", "Agg")
# Force to Agg before any figures/backends are created/resolved.
matplotlib.use("Agg", force=True)

# 2) Treat Matplotlib-related warnings as errors to ensure a warning-free suite.
warnings.filterwarnings(
    "error",
    message=r".*Matplotlib.*",
    category=UserWarning,
)

def pytest_sessionstart(session):
    # Verify backend very early.
    backend = matplotlib.get_backend().lower()
    assert backend == "agg", (
        f"Matplotlib backend is {backend!r}, expected 'agg'. "
        "Ensure MPLBACKEND=Agg is exported and matplotlib.use('Agg') is called before any pyplot import."
    )

# 3) Runtime ban on plt.show(): monkeypatch at session scope.
#    We patch directly instead of using the monkeypatch fixture to avoid scope constraints.
import matplotlib.pyplot as plt

_old_show = getattr(plt, "show", None)

def _no_show(*args, **kwargs):  # pragma: no cover - simple guard
    raise AssertionError(
        "plt.show() is banned in tests. Use savefig(), return the Figure, or use image comparisons."
    )

plt.show = _no_show  # type: ignore[assignment]

# Do NOT restore plt.show at teardown; enforcement should persist for the test session.

# Import necessary modules for test fixtures
import pytest

@pytest.fixture(scope="session")
def config():
    """Load configuration from config.yaml for tests."""
    from src.config import load_config
    return load_config("config.yaml", allow_unknown=True)

@pytest.fixture(scope="session")
def physics_cfg(config):
    """Provide physics configuration for tests."""
    return config.physics

@pytest.fixture(scope="session")
def dynamics(physics_cfg):
    """Provide simplified DIP dynamics for tests."""
    from src.core.dynamics import DIPDynamics
    return DIPDynamics(params=physics_cfg)

@pytest.fixture(scope="session")
def full_dynamics(physics_cfg):
    """Provide full DIP dynamics for tests."""
    from src.core.dynamics_full import FullDIPDynamics
    return FullDIPDynamics(params=physics_cfg)

@pytest.fixture
def initial_state():
    """Provide a standard initial state for controller tests."""
    import numpy as np
    return np.array([0.0, 0.1, -0.05, 0.0, 0.0, 0.0], dtype=float)

@pytest.fixture
def make_hybrid():
    """
    Factory fixture that constructs a HybridAdaptiveSTASMC controller with sensible defaults.
    Tests can override any keyword (e.g., dt, max_force, gains, dynamics_model, etc.).
    """
    def _make(**overrides):
        from src.controllers.hybrid_adaptive_sta_smc import HybridAdaptiveSTASMC

        # Stronger but still conservative defaults for better robustness
        dt = float(overrides.pop("dt", 0.001))
        max_force = float(overrides.pop("max_force", 150.0))
        gains = overrides.pop("gains", [0.5, 2.0, 0.8, 1.5])  # Extremely conservative for double-inverted pendulum

        dyn = overrides.pop("dynamics_model", None)
        if dyn is None:
            try:
                from src.core.dynamics import DoubleInvertedPendulum, DIPParams
                dyn = DoubleInvertedPendulum(DIPParams.default())
            except Exception:
                dyn = None

        return HybridAdaptiveSTASMC(
            gains=gains,
            dt=dt,
            max_force=max_force,
            k1_init=0.05, k2_init=0.05, gamma1=0.5, gamma2=0.5, dead_zone=0.02,
            dynamics_model=dyn,
            # Ultra-conservative safety defaults for double-inverted pendulum
            gain_leak=0.02,
            k1_max=20.0,
            k2_max=20.0,
            adaptation_sat_threshold=0.20,
            taper_eps=0.30,
            # Disable equivalent control and minimize other terms
            enable_equivalent=False,
            damping_gain=0.1,
            cart_p_gain=0.5,  # Very gentle cart recentering
            **overrides,
        )

    return _make
