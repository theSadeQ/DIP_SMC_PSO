#==========================================================================================\\\
#================================ scripts/run_tests.py ================================\\\
#==========================================================================================\\\

"""
Run the pytest test suite
Execute: python run_tests.py

"""

import os
os.environ.setdefault("MPLBACKEND", "Agg")

import logging
import subprocess
import sys
import locale
import types
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def main():
    """Run the pytest test suite and propagate the exit code."""

    logging.info("=" * 60)
    logging.info("Running Double Inverted Pendulum Test Suite")
    logging.info("=" * 60)

    # Attempt to import pytest.  If unavailable, fall back to a lightweight
    # smoke test that instantiates each configured controller and executes a
    # short simulation.  This ensures CI environments without pytest can
    # still validate basic functionality.
    try:
        import pytest  # type: ignore
        have_pytest = True
    except Exception:
        have_pytest = False

    if not have_pytest:
        return run_smoke_tests()

    # Run pytest as originally intended
    logging.info("Running unit tests...")
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--capture=no"]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=False,
    )
    if process.stdout is not None:
        for raw_line in iter(process.stdout.readline, b''):
            if not raw_line:
                break
            try:
                decoded = raw_line.decode('utf-8')
            except UnicodeDecodeError:
                decoded = raw_line.decode('utf-8', errors='replace')
            print(decoded.rstrip(), flush=True)
    process.wait()
    if process.returncode != 0:
        logging.error("Pytest reported errors. Exit code: %d", process.returncode)
    else:
        logging.info("All tests passed.")
    logging.info("\n" + "=" * 60)
    logging.info("Test suite complete!")
    return process.returncode


def run_smoke_tests() -> int:
    """
    Execute a minimal set of smoke tests when pytest is not available.

    This function parses ``config.yaml``, instantiates each controller
    listed under the ``controllers`` section using the factory, and runs
    a short 2‑second simulation for those controllers that support it.
    The simulation uses the physics defined in the configuration and
    operates with ``raise_on_warning=True`` to surface numerical
    instabilities.  If any controller fails to construct or the
    simulation raises an exception, the smoke test aborts and returns
    a non‑zero exit code.

    Returns
    -------
    int
        0 if all smoke tests pass, otherwise 1.
    """
    logging.info("Pytest is not available; running smoke tests...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "config.yaml")
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            raw_cfg = yaml.safe_load(f) or {}
    except Exception as e:
        logging.error("Failed to load configuration for smoke tests: %s", e)
        return 1
    controllers_cfg = raw_cfg.get("controllers", {}) or {}
    controller_defaults = raw_cfg.get("controller_defaults", {}) or {}
    physics_cfg = raw_cfg.get("physics", {}) or None
    sim_cfg = raw_cfg.get("simulation", {}) or {}
    sim_dt = float(sim_cfg.get("dt", 0.01))
    sim_time = 2.0
    class _SimpleConfig:
        pass
    simple_config = _SimpleConfig()
    simple_config.controllers = controllers_cfg
    simple_config.controller_defaults = controller_defaults
    simple_config.physics = None
    simple_config.simulation = types.SimpleNamespace(dt=sim_dt, use_full_dynamics=False)
    dyn_model = None
    try:
        if physics_cfg:
            from src.core.dynamics import DoubleInvertedPendulum
            dyn_model = DoubleInvertedPendulum(physics_cfg)
    except Exception as exc:
        logging.warning("Unable to instantiate dynamics model for smoke tests: %s", exc)
        dyn_model = None
    try:
        from src.controllers.factory import create_controller
        from src.core.simulation_runner import run_simulation
    except Exception as exc:
        logging.error("Failed to import factory or simulation runner: %s", exc)
        return 1
    all_ok = True
    for name, ctrl_cfg in controllers_cfg.items():
        key = str(name)
        logging.info("Smoke test: building controller '%s'", key)
        try:
            dt_override = float(ctrl_cfg.get("dt", sim_dt)) if isinstance(ctrl_cfg, dict) else sim_dt
        except Exception:
            dt_override = sim_dt
        try:
            max_force_override = float(ctrl_cfg.get("max_force", 20.0)) if isinstance(ctrl_cfg, dict) else 20.0
        except Exception:
            max_force_override = 20.0
        try:
            ctrl = create_controller(key, config=simple_config, dt=dt_override, max_force=max_force_override)
            if dyn_model is not None:
                run_simulation(ctrl, dyn_model, sim_time=sim_time, dt=dt_override, raise_on_warning=True)
        except Exception as exc:
            logging.error("Smoke test failed for controller '%s': %s", key, exc)
            all_ok = False
            break
    if all_ok:
        logging.info("Smoke tests completed successfully.")
        return 0
    else:
        logging.error("One or more smoke tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
#=================================================================================================================\\\