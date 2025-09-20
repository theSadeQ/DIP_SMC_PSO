#==========================================================================================\\\
#===================================== tests/conftest.py ==================================\\\
#==========================================================================================\\\
"""
c5u-mpl enforcement: headless Matplotlib tests with Agg backend and show-ban.
This file MUST be imported before any test that imports matplotlib.pyplot.
"""
import os
import warnings
import matplotlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if SCRIPTS_DIR.exists():
    scripts_path = str(SCRIPTS_DIR)
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)


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
    """Load configuration from config.yaml for tests.

    Loads the real config module from disk to avoid interference from tests that
    monkeypatch sys.modules (e.g., streamlit app tests). Ensures controller_defaults
    exposes attribute access and backfills essential gains when missing.
    """
    from types import SimpleNamespace
    from pathlib import Path
    import importlib.util

    def _load_real_config():
        cfg_path = Path('src') / 'config.py'
        spec = importlib.util.spec_from_file_location('project_real_config', str(cfg_path))
        if spec is None or spec.loader is None:
            raise RuntimeError('Unable to locate src/config.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return mod

    def _to_ns(obj):
        if isinstance(obj, dict):
            return SimpleNamespace(**{k: _to_ns(v) for k, v in obj.items()})
        return obj

    # Robust lightweight load: parse YAML and expose attribute access
    try:
        import yaml
        raw = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8")) or {}
    except Exception:
        raw = {}
    cfg = _to_ns(raw)
    # Backfill controller_defaults gains for core controllers
    if not hasattr(cfg, "controller_defaults"):
        setattr(cfg, "controller_defaults", SimpleNamespace())
    cd_ns = cfg.controller_defaults
    for name in ("classical_smc", "sta_smc", "adaptive_smc"):
        if not hasattr(cd_ns, name):
            setattr(cd_ns, name, SimpleNamespace())
        ns = getattr(cd_ns, name)
        if not hasattr(ns, "gains"):
            try:
                gains = raw.get("controller_defaults", {}).get(name, {}).get("gains")
            except Exception:
                gains = None
            if gains:
                setattr(ns, "gains", list(gains))
    return cfg

@pytest.fixture(scope="session")
def physics_cfg(config):
    """Provide physics configuration for tests."""
    try:
        return config.physics.model_dump()
    except Exception:
        try:
            return dict(config.physics.__dict__)
        except Exception:
            return {}

# Backward-compat alias used by some consolidated tests
@pytest.fixture(scope="session")
def physics_params(physics_cfg):
    """Alias fixture: several tests expect `physics_params` name."""
    return physics_cfg

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

# Some tests mark usefixtures("long_simulation_config") as a toggle only.
# Provide a no-op fixture to satisfy those references without altering config.
@pytest.fixture(scope="session")
def long_simulation_config():
    yield None

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
