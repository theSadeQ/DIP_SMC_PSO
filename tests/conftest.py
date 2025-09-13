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
