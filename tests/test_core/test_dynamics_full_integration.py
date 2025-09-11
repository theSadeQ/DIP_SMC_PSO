"""
Integration tests for the dynamics step router.

This test suite verifies that the simulation runner dispatches to the
appropriate dynamics implementation based on the ``config.simulation.use_full_dynamics``
flag.  It also ensures that a missing full dynamics module triggers the
expected RuntimeError with the exact message defined in the specification.

These tests are marked with the ``full_dynamics`` marker so they can be
selectively enabled in continuous integration.  See ``pytest.ini`` or
``tests/conftest.py`` for marker registration.
"""

import pytest

import src.core.simulation_runner as runner
from src.config import config


@pytest.mark.full_dynamics
class TestToggle:
    """Verify routing between low‑rank and full dynamics implementations."""

    def test_full_vs_lowrank_path(self):
        """
        When ``config.simulation.use_full_dynamics`` is False the router should
        call ``src.core.dynamics_lowrank.step``.  When the flag is True it
        should call ``src.core.dynamics_full.step``.  Monkeypatch the
        respective ``step`` functions to return a sentinel value and assert
        that the correct path is taken.
        """
        # --- Low‑rank path ---
        config.simulation.use_full_dynamics = False

        # Patch low‑rank step to make the path observable
        import src.core.dynamics_lowrank as lowrank  # type: ignore

        def low_stub(x, u, dt):  # pragma: no cover - test hook
            return ("lowrank", x, u, dt)

        orig_low = lowrank.step
        lowrank.step = low_stub  # type: ignore[assignment]
        try:
            out = runner.step(1, 2, 0.1)
            assert out[0] == "lowrank"
        finally:
            lowrank.step = orig_low  # type: ignore[assignment]

        # --- Full path ---
        config.simulation.use_full_dynamics = True

        # Ensure a real/stub dynamics_full module is importable
        import src.core.dynamics_full as fullmod  # type: ignore

        def full_stub(x, u, dt):  # pragma: no cover - test hook
            return ("full", x, u, dt)

        orig_full = fullmod.step
        fullmod.step = full_stub  # type: ignore[assignment]
        try:
            out = runner.step(3, 4, 0.2)
            assert out[0] == "full"
        finally:
            fullmod.step = orig_full  # type: no cover

    def test_missing_full_model_error_message(self):
        """
        Forcing the router to import a non‑existent full dynamics module
        should raise a RuntimeError with the exact message specified in the
        plan.  Monkeypatch the module path constant to simulate a missing
        module.
        """
        config.simulation.use_full_dynamics = True
        # Monkeypatch the module path constant so import fails
        orig = runner.DYNAMICS_FULL_MODULE
        runner.DYNAMICS_FULL_MODULE = "src.core.dynamics_full_DOES_NOT_EXIST"
        try:
            with pytest.raises(RuntimeError) as excinfo:
                runner.step(0, 0, 0.0)
            # EXACT message required
            assert str(excinfo.value) == (
                "Full dynamics unavailable: module 'dynamics_full' not found. Set config.simulation.use_full_dynamics=false or provide src/core/dynamics_full.py"
            )
        finally:
            runner.DYNAMICS_FULL_MODULE = orig
