# ======================================================================================\\\
# tsts/conftest.py ======================================================================================\\\
# ========================================================================================================\\\
"""Shared test configuration and fixtures.

This module centralises test configuration for the project.  It exposes
fixtures used across the existing test suite and adds a handful of new
helpers required by the additional hybrid controller and dynamics tests.

The early environment configuration ensures that the source tree can be
imported without relying on the developer's shell, sets a UTF‑8 encoding on
Windows, and configures a local Numba cache directory.  These are
idempotent and will not override values already set by the user or CI.
"""

# --- begin: early, process-wide test env setup (before any src import) ---
import os
import sys
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# Make src importable no matter where pytest is launched
sys.path[:0] = [str(SRC)]
os.environ["PYTHONPATH"] = str(SRC)

# Force UTF-8 on Windows to avoid YAML/IO decoding surprises
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Isolate Numba cache to this repo and purge stale cache each test session
nb_cache = ROOT / ".numba_cache"
try:
    if nb_cache.exists():
        shutil.rmtree(nb_cache)
except Exception:
    pass
nb_cache.mkdir(parents=True, exist_ok=True)
os.environ["NUMBA_CACHE_DIR"] = str(nb_cache)

# Best-effort: also purge any global user caches that can hold stale pickles
for p in (
    pathlib.Path(os.getenv("LOCALAPPDATA", "")) / "Numba" / "Cache",  # Windows
    pathlib.Path.home() / ".numba" / "Cache",
):
    try:
        shutil.rmtree(p)
    except Exception:
        pass
# --- end: early env setup ---

import pytest

# Import core modules after the early env block
import src.config as src_config  # noqa: E402
from src.config import load_config, ConfigSchema, PhysicsConfig  # noqa: E402

# Prefer a resilient name for the simplified dynamics class
try:  # noqa: E402
    from src.core.dynamics import DoubleInvertedPendulum as DIPDynamics  # type: ignore
except Exception:  # noqa: E402
    from src.core.dynamics import DIPDynamics  # type: ignore

# Ensure downstream imports like "from src.core.dynamics import DoubleInvertedPendulum"
# never fail due to reloads or missing alias.
try:
    import src.core.dynamics as _dyn_mod  # noqa: E402

    if not hasattr(_dyn_mod, "DoubleInvertedPendulum") and hasattr(
        _dyn_mod, "DIPDynamics"
    ):
        setattr(_dyn_mod, "DoubleInvertedPendulum", _dyn_mod.DIPDynamics)
except Exception:
    pass

from src.core.dynamics_full import FullDIPDynamics  # noqa: E402


# --------------------------------------------------------------------------------------
# Autouse guard: keeps the DoubleInvertedPendulum alias present even if a test
# reloads src.core.dynamics and drops the alias.
# --------------------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _ensure_dynamics_alias():
    import importlib

    try:
        import src.core.dynamics as m

        if not hasattr(m, "DoubleInvertedPendulum") and hasattr(m, "DIPDynamics"):
            # Reload then restore the alias if needed
            try:
                importlib.reload(m)
            except Exception:
                pass
            if hasattr(m, "DIPDynamics"):
                setattr(m, "DoubleInvertedPendulum", m.DIPDynamics)
    except Exception:
        # Non-fatal: tests that don't touch this module will continue
        pass


# ------------------------------ Optional speed / duration fixtures ------------------------------


@pytest.fixture
def fast_pso(monkeypatch):
    """
    Reduce PSO workload and simulation time for tests that explicitly use this fixture.
    """
    original_load_config = load_config

    def mock_load_config(*args, **kwargs):
        cfg = original_load_config(*args, **kwargs)
        cfg.pso.iters = 5
        cfg.pso.n_particles = 10
        cfg.simulation.duration = 1.0  # keep PSO-driven sims fast
        print("\n[conftest] fast_pso: duration=1.0, iters=5, particles=10")
        return cfg

    monkeypatch.setattr(src_config, "load_config", mock_load_config)


@pytest.fixture
def long_simulation_config(monkeypatch):
    """
    Restore a longer simulation duration for tests that need it.
    """
    original_load_config = load_config

    def mock_load_config(*args, **kwargs):
        cfg = original_load_config(*args, **kwargs)
        cfg.simulation.duration = 10.0
        print("\n[conftest] long_simulation_config: duration=10.0")
        return cfg

    monkeypatch.setattr(src_config, "load_config", mock_load_config)


# ------------------------------------------ Core config / physics ------------------------------------------


@pytest.fixture(scope="session")
def config() -> ConfigSchema:
    """Load the YAML configuration once per test session."""
    return load_config("config.yaml")


@pytest.fixture(scope="session")
def physics_params(config: ConfigSchema) -> PhysicsConfig:
    """Session-scoped physics parameters object used across tests."""
    return config.physics


# ---------------------------------------------- Dynamics fixtures ----------------------------------------------


@pytest.fixture(scope="function")
def dynamics(physics_params: PhysicsConfig) -> DIPDynamics:
    """Simplified 6-state DIP dynamics."""
    return DIPDynamics(params=physics_params)


@pytest.fixture(scope="function")
def full_dynamics(physics_params: PhysicsConfig) -> FullDIPDynamics:
    """Full 6-state DIP dynamics with physics matrices (Numba-accelerated)."""
    return FullDIPDynamics(params=physics_params)


# ---------------------------------------------- Shared helpers ----------------------------------------------


@pytest.fixture(scope="session")
def physics_cfg(physics_params: PhysicsConfig) -> PhysicsConfig:
    """Alias kept for backwards compatibility with some tests."""
    return physics_params


@pytest.fixture
def initial_state() -> "np.ndarray":
    """A reasonable initial state for the double inverted pendulum."""
    import numpy as np

    # [x, θ1, θ2, ẋ, θ̇1, θ̇2]
    return np.array([0.0, 0.1, -0.05, 0.0, 0.0, 0.0], dtype=float)


@pytest.fixture
def make_hybrid() -> "callable":
    """
    Factory for the hybrid adaptive super-twisting SMC controller.

    Adjust defaults here if you need different dt / max_force in a test via
    make_hybrid(dt=..., max_force=...).
    """
    from src.controllers.hybrid_adaptive_sta_smc import HybridAdaptiveSTASMC

    def _make(dt: float = 0.001, max_force: float = 150.0) -> "HybridAdaptiveSTASMC":
        return HybridAdaptiveSTASMC(
            gains=[5.0, 3.0, 5.0, 1.8],
            dt=dt,
            max_force=max_force,
            k1_init=6.0,
            k2_init=1.2,
            gamma1=0.8,
            gamma2=0.4,
            dead_zone=0.02,
        )

    return _make


# ---------------------------------------------- Pytest config ----------------------------------------------


def pytest_configure(config):
    """Register custom markers to avoid 'unknown mark' warnings."""
    config.addinivalue_line("markers", "slow: mark test as long-running")


# ====================================================================================================================================================
