#==========================================================================================\\\
#===================================== dev/runner.py =====================================\\\
#==========================================================================================\\\
"""Simple fallback harness for acceptance tests.

This script executes a subset of the functionality required for the
assignment without relying on pytest.  It exercises the full/low‑rank
dynamics router and safety guards and reports pass/fail outcomes via
console messages.  Use the ``c1-02`` and ``c1-03`` lanes to run the
router and safety guard tests respectively.
"""

import importlib
import os
import sys
import traceback
from types import SimpleNamespace

PASSED = 0
FAILED = 0


def ok(msg: str) -> None:
    global PASSED
    PASSED += 1
    print(f"OK: {msg}")


def fail(msg: str, e: Exception | str | None = None) -> None:
    global FAILED
    FAILED += 1
    print(f"FAIL: {msg}")
    if e is not None:
        print(e)


def lane_c102() -> None:
    """Test the dynamics router and missing-module error message."""
    try:
        # Ensure src package is on the path
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        cfg_mod = importlib.import_module("src.config")
        # Ensure config has the expected structure
        cfg = getattr(cfg_mod, "config", SimpleNamespace(simulation=SimpleNamespace(use_full_dynamics=False)))
        runner = importlib.import_module("src.core.simulation_runner")

        # --- Low‑rank path ---
        cfg.simulation.use_full_dynamics = False
        # Patch low‑rank step to make path observable
        lowrank = importlib.import_module("src.core.dynamics_lowrank")
        def low_stub(x, u, dt):
            return ("lowrank", x, u, dt)
        orig_low = lowrank.step
        lowrank.step = low_stub
        try:
            out = runner.step(1, 2, 0.1)
            if isinstance(out, tuple) and out[0] == "lowrank":
                ok("Low‑rank path executed")
            else:
                fail("Low‑rank path returned unexpected result", out)
        finally:
            lowrank.step = orig_low

        # --- Full dynamics path ---
        cfg.simulation.use_full_dynamics = True
        # Ensure a full dynamics module is importable
        fullmod = importlib.import_module("src.core.dynamics_full")
        def full_stub(x, u, dt):
            return ("full", x, u, dt)
        orig_full = getattr(fullmod, "step")
        fullmod.step = full_stub  # type: ignore
        try:
            out = runner.step(3, 4, 0.2)
            if isinstance(out, tuple) and out[0] == "full":
                ok("Full dynamics path executed")
            else:
                fail("Full dynamics path returned unexpected result", out)
        finally:
            fullmod.step = orig_full  # type: ignore

        # --- Missing full dynamics module ---
        cfg.simulation.use_full_dynamics = True
        # Monkeypatch module path to a non‑existent name
        orig_name = runner.DYNAMICS_FULL_MODULE
        runner.DYNAMICS_FULL_MODULE = "src.core.dynamics_full_DOES_NOT_EXIST"
        try:
            try:
                runner.step(0, 0, 0.0)
                fail("Expected missing full dynamics error")
            except Exception as e:  # noqa: BLE001
                exp = (
                    "Full dynamics unavailable: module 'dynamics_full' not found. Set config.simulation.use_full_dynamics=false or provide src/core/dynamics_full.py"
                )
                if str(e) == exp:
                    ok("Exact missing full dynamics error message")
                else:
                    fail("Missing full dynamics message mismatch", str(e))
        finally:
            runner.DYNAMICS_FULL_MODULE = orig_name
    except Exception as e:  # noqa: BLE001
        fail("c1-02 lane setup failed", traceback.format_exc())


def lane_c103() -> None:
    """Test the vectorized safety guards."""
    try:
        # Import guard functions
        # Import the safety guards from the local repo.  The module lives under
        # ``src.core.safety_guards`` when ``repo_root`` is on sys.path.  Avoid
        # referencing the ``workspace.DIP_SMC_PSO`` package which does not exist
        # when running this script directly from within the repository.
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        guards = importlib.import_module("src.core.safety_guards")
        import numpy as np
        # NaN/Inf guard
        try:
            bad = np.array([[1.0, np.nan], [0.0, 1.0]], dtype=float)
            guards._guard_no_nan(bad, step_idx=3)
            fail("Expected NaN guard to raise an exception")
        except Exception as e:  # noqa: BLE001
            if "NaN detected in state at step <i>" in str(e):
                ok("NaN guard substring matches")
            else:
                fail("NaN guard message mismatch", str(e))
        # Energy guard
        try:
            big = np.array([[10.0, 0.0], [0.0, 10.0]], dtype=float)
            # total_energy per row = 100
            guards._guard_energy(big, limits={"max": 1.0})
            fail("Expected energy guard to raise an exception")
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "Energy check failed: total_energy=<val> exceeds <max>" in msg:
                ok("Energy guard substring matches")
            else:
                fail("Energy guard message mismatch", msg)
        # Bounds guard
        try:
            x = np.array([[-0.5, 0.0], [1.5, 0.0]], dtype=float)
            bounds = (np.array([0.0, -1.0]), np.array([1.0, 1.0]))
            guards._guard_bounds(x, bounds=bounds, t=0.25)
            fail("Expected bounds guard to raise an exception")
        except Exception as e:  # noqa: BLE001
            if "State bounds violated at t=<t>" in str(e):
                ok("Bounds guard substring matches")
            else:
                fail("Bounds guard message mismatch", str(e))
    except Exception as e:  # noqa: BLE001
        fail("c1-03 lane setup failed", traceback.format_exc())


def main() -> None:
    lane = sys.argv[1] if len(sys.argv) > 1 else "all"
    if lane in ("c1-02", "all"):
        lane_c102()
    if lane in ("c1-03", "all"):
        lane_c103()
    if FAILED:
        print(f"\nFAILED: {FAILED}, PASSED: {PASSED}")
        sys.exit(FAILED)
    else:
        print(f"\nSUCCESS: All {PASSED} checks passed.")
        sys.exit(0)


if __name__ == "__main__":  # pragma: no cover
    main()