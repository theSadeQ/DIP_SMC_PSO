#==========================================================================================\\\
#============================== tests/test_app/test_cli.py =============================\\\
#==========================================================================================\\\

import subprocess
import sys
from pathlib import Path
import pytest

from unittest.mock import patch, MagicMock


# Note: A second definition of ``_run_cli`` existed in this file due to test
# consolidation.  That duplicate helper has been removed to ensure there is
# exactly one implementation.  The definition above (at the top of this
# module) should be used for all CLI invocations.  See the docstring on thef
# first ``_run_cli`` for details.

def test_app_fails_fast_on_invalid_controller():
    """
    Verify that simulate.py exits with a non-zero code and logs a ValueError
    when an unknown controller name is provided, instead of silently falling back.
    """
    # Arrange: Use a controller name that does not exist in config.yaml
    invalid_controller_name = "this_controller_does_not_exist"

    # Act: Run the simulate.py CLI with the invalid controller argument
    result = _run_cli(["--controller", invalid_controller_name])

    # Assert
    # 1. The process should fail (non-zero exit code).
    assert result.returncode != 0, \
        "simulate.py should exit with an error code on invalid controller, but it exited cleanly."

    # 2. The stderr should contain an error indicating the root cause.
    assert ("not found in config.controllers" in result.stderr or
            "Validation error" in result.stderr), \
        "Expected an error message in stderr for an unknown controller."

    # 3. The error message should mention the invalid controller name.
    assert invalid_controller_name in result.stderr, \
        f"Stderr should contain the invalid controller name '{invalid_controller_name}'."

    # 4. There should be NO warning about falling back to a PD controller.
    assert "Falling back to a simple PD controller" not in result.stdout, \
        "The silent fallback warning should NOT be present."
    assert "Falling back to a simple PD controller" not in result.stderr, \
        "The silent fallback warning should NOT be present."

def test_app_fails_on_backend_error_in_hil(monkeypatch):
    """
    Verify that a critical backend error during the HIL baseline sim
    causes a non-zero exit code instead of being silently caught.

    Why: This ensures that backend failures (like numpy computation errors,
    missing dependencies, or corrupted data structures) are immediately
    visible rather than producing invalid results.
    """
    # Arrange: Prepare a tiny script that injects a TypeError during the baseline
    # simulation of the HIL run.  Patching ``simulate._get_run_simulation`` inside
    # this script ensures that the baseline simulation uses the injected
    # function even though the CLI is executed in a separate subprocess.
    test_script = """
import sys
from unittest.mock import patch
import simulate

def boom(*args, **kwargs):
    raise TypeError("A critical backend error occurred")

with patch('simulate._get_run_simulation', return_value=boom):
    try:
        exit_code = simulate.main(['--run-hil'])
        sys.exit(exit_code)
    except Exception:
        # Re-raise to cause a non-zero exit code and print the traceback
        raise
"""

    # Act: run the script in a new Python interpreter.  Running via -c ensures
    # that the patch is applied inside the same process that calls simulate.main.
    cmd = [sys.executable, '-c', test_script]
    result = subprocess.run(
        cmd,
        cwd=(Path(__file__).resolve().parents[2]),
        capture_output=True,
        text=True,
    )

    # Assert: the process should have exited with a non-zero code and the
    # injected TypeError should be visible in stderr.
    assert result.returncode != 0, "simulate.py should fail when the baseline simulation fails."
    assert "TypeError: A critical backend error occurred" in result.stderr, \
        "The specific backend error should be propagated to stderr."

def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    """Run simulate.py with given arguments and capture output."""
    # Correct path: go up two levels from tests/test_app/ to reach project root
    app_path = (Path(__file__).resolve().parents[2] / "simulate.py").resolve()
    cmd = [sys.executable, str(app_path), *args]

    result = subprocess.run(
        cmd,
        cwd=app_path.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    return result


class TestDynamicsFailFast:
    """Test that dynamics loading fails fast on errors."""

    def test_dynamics_import_error_propagates(self):
        """Verify that ImportError in _build_dynamics causes app to fail."""
        # Create a temporary simulate.py that will fail on dynamics import
        test_script = """
import sys
import logging
import os
sys.path.insert(0, os.getcwd())
from simulate import _build_dynamics

# Mock the import to fail
class MockImportError:
    def find_spec(self, name, path=None, target=None):
        if 'dynamics' in name:
            raise ModuleNotFoundError("Simulated import failure")
        return None

sys.meta_path.insert(0, MockImportError())

try:
    _build_dynamics({})
    print("ERROR: Should have failed!")
    sys.exit(1)
except RuntimeError as e:
    print(f"SUCCESS: {e}")
    sys.exit(0)
except Exception as e:
    print(f"UNEXPECTED: {type(e).__name__}: {e}")
    sys.exit(2)
"""
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).resolve().parents[2],  # Run from project root
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Expected success exit, got {result.returncode}. Output: {result.stdout}, Stderr: {result.stderr}"
        assert "SUCCESS:" in result.stdout
        assert "Double inverted pendulum dynamics model not found" in result.stdout

    def test_dynamics_syntax_error_propagates(self):
        """Verify that syntax errors in dynamics module cause immediate failure."""
        # Corrected: Patch the import function specifically within the 'app' module's scope.
        # This prevents the patch from affecting imports of simulate.py's dependencies.
        with patch('simulate.importlib.import_module', side_effect=SyntaxError("Invalid syntax in module")):
            # Now, importing from app will succeed, but calling the function that
            # USES the patched import will fail as intended.
            from simulate import _build_dynamics

            with pytest.raises(SyntaxError):
                _build_dynamics({})


class TestControllerFailFast:
    """Test that controller creation fails fast on errors."""

    def test_invalid_controller_name_fails(self):
        """Verify the app exits with error for invalid controller names."""
        result = _run_cli(["--controller", "nonexistent_controller"])

        assert result.returncode != 0
        assert "ValueError" in result.stderr or "RuntimeError" in result.stderr
        assert "nonexistent_controller" in result.stderr

    def test_controller_factory_missing_fails(self):
        """Test that missing controller factory causes immediate failure."""
        # Create a test that simulates missing factory
        test_script = """
import sys
import os
sys.path.insert(0, os.getcwd())
from unittest.mock import patch
from simulate import _build_controller

with patch('simulate._import_optional', return_value=None):
    try:
        _build_controller({}, "test")
        print("ERROR: Should have failed!")
        sys.exit(1)
    except RuntimeError as e:
        if "Controller factory not available" in str(e):
            print("SUCCESS: Correct error raised")
            sys.exit(0)
        else:
            print(f"WRONG ERROR: {e}")
            sys.exit(2)
"""
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).resolve().parents[2], # Run from project root
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Expected success exit, got {result.returncode}. Output: {result.stdout}, Stderr: {result.stderr}"
        assert "SUCCESS: Correct error raised" in result.stdout

class TestUIFailFast:
    """Test that UI code fails fast on unexpected errors."""

    def test_visualizer_import_failure_is_fatal(self):
        """Verify that missing Visualizer module causes immediate failure."""
        test_script = """
import sys
import os
sys.path.insert(0, os.getcwd())
# Block import of visualizer modules
sys.modules['src.utils.visualization'] = None
sys.modules['visualization'] = None

try:
    import streamlit_app
    print("ERROR: Import should have failed!")
    sys.exit(1)
except RuntimeError as e:
    if "Visualizer module not found" in str(e):
        print(f"SUCCESS: {e}")
        sys.exit(0)
    else:
        print(f"WRONG ERROR: {e}")
        sys.exit(2)
except Exception as e:
    print(f"UNEXPECTED: {type(e).__name__}: {e}")
    sys.exit(3)
"""

        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Expected exit 0 (correct error raised). Got {result.returncode}. Output: {result.stdout}, Stderr: {result.stderr}"
        assert "SUCCESS:" in result.stdout

class TestGeneralFailFast:
    """Test general fail-fast behavior."""

    def test_no_broad_exception_handlers(self):
        """Verify no broad 'except Exception:' blocks remain in critical paths."""
        # Resolve application modules relative to the project root.  Using
        # ``parents[2]`` here ensures the top‑level ``simulate.py`` and
        # ``streamlit_app.py`` files are located correctly even when the
        # test file resides in a nested directory.  This avoids accidental
        # references to non‑existent modules under the ``tests`` folder.
        app_path = Path(__file__).resolve().parents[2] / "simulate.py"
        streamlit_path = Path(__file__).resolve().parents[2] / "streamlit_app.py"

        # Check simulate.py
        with open(app_path, 'r') as f:
            app_content = f.read()

        # Look for problematic patterns in critical functions
        critical_functions = [
            "_build_dynamics",
            "_build_controller",
            "_get_run_simulation"
        ]

        for func in critical_functions:
            # Extract the function (simplified - assumes no nested functions).
            # We look for the next function definition by searching for a newline followed by
            # "def ".  This avoids multiline string literals and ensures proper termination.
            start = app_content.find(f"def {func}")
            if start == -1:
                continue
            # Find the next occurrence of a function definition header starting on a new line.
            end = app_content.find("\ndef ", start + 1)
            if end == -1:
                end = len(app_content)

            func_content = app_content[start:end]

            # Check for broad exception handlers
            assert "except Exception:" not in func_content, \
                f"Found broad 'except Exception:' in {func}"
            assert "except:" not in func_content, \
                f"Found bare 'except:' in {func}"

    def test_app_crashes_on_missing_numpy(self):
        """Verify simulate.py fails fast if numpy is not installed."""
        app_path = (Path(__file__).resolve().parents[2] / "simulate.py").resolve()

        # A script that blocks numpy and tries to import simulate.py
        test_script = f"""
import sys
import os
sys.modules['numpy'] = None
sys.path.insert(0, os.getcwd())

try:
    import simulate
    # Try to run something that would use numpy
    simulate.main(['--duration', '0.1'])
    sys.exit(0)  # Should not be reached
except (ImportError, ModuleNotFoundError, RuntimeError, AttributeError):
    sys.exit(123)  # Expected failure code
"""

        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=app_path.parent,
            capture_output=True,
            text=True
        )

        assert result.returncode == 123, f"App should fail with exit code 123 when numpy is missing. Got {result.returncode}. Output: {result.stdout}, Stderr: {result.stderr}"


def test_app_fails_fast_on_invalid_fdi_config(tmp_path):
    """
    Verify that simulate.py exits with a non-zero code if FDI is enabled but misconfigured.
    """
    # Create a config file with an invalid FDI parameter type
    config_content = """
global_seed: 42
fdi:
  enabled: true
  residual_threshold: "this-is-not-a-float"  # Invalid type
  persistence_counter: 5
# Minimal other keys to make the config valid enough to load
controllers:
  classical_smc:
    max_force: 150.0
controller_defaults:
  classical_smc:
    gains: [1,1,1,1,1,1]
physics:
  cart_mass: 1.0
  pendulum1_mass: 0.1
  pendulum2_mass: 0.1
  pendulum1_length: 0.5
  pendulum2_length: 0.4
  pendulum1_com: 0.25
  pendulum2_com: 0.2
  pendulum1_inertia: 0.005
  pendulum2_inertia: 0.002
  gravity: 9.81
  cart_friction: 0.1
  joint1_friction: 0.01
  joint2_friction: 0.01
simulation:
  duration: 0.1
  dt: 0.01
pso:
  n_particles: 1
  bounds: {min: [1], max: [2]}
  w: 0.5
  c1: 1.5
  c2: 1.5
  iters: 1
  n_processes: 1
  hyper_trials: 1
  hyper_search: {inertia: [0.4, 0.9], cognitive: [0.5, 2.5], social: [0.5, 2.5]}
  study_timeout: 10
  seed: 42
  tune: {cart_mass: {min: 1, max: 2}, pendulum1_mass: {min: 0.1, max: 0.2}, pendulum2_mass: {min: 0.1, max: 0.2}, pendulum1_length: {min: 0.3, max: 0.5}, pendulum2_length: {min: 0.2, max: 0.4}, pendulum1_com: {min: 0.15, max: 0.25}, pendulum2_com: {min: 0.1, max: 0.2}, pendulum1_inertia: {min: 0.002, max: 0.005}, pendulum2_inertia: {min: 0.001, max: 0.002}, cart_friction: {min: 0.1, max: 0.2}, joint1_friction: {min: 0.005, max: 0.01}, joint2_friction: {min: 0.005, max: 0.01}, boundary_layer: {min: 0.01, max: 0.05}}
physics_uncertainty:
  n_evals: 1
  cart_mass: 0
  pendulum1_mass: 0
  pendulum2_mass: 0
  pendulum1_length: 0
  pendulum2_length: 0
  pendulum1_com: 0
  pendulum2_com: 0
  pendulum1_inertia: 0
  pendulum2_inertia: 0
  gravity: 0
  cart_friction: 0
  joint1_friction: 0
  joint2_friction: 0
verification:
  test_conditions: []
  integrators: []
  criteria: {max_angle: 1, settling_time: 1}
cost_function:
  weights: {state_error: 1, control_effort: 1, control_rate: 1, stability: 1}
  baseline: {gains: [1]}
  instability_penalty: 1000
sensors:
  angle_noise_std: 0
  position_noise_std: 0
  quantization_angle: 0
  quantization_position: 0
hil:
  plant_ip: "127.0.0.1"
  plant_port: 9000
  controller_ip: "127.0.0.1"
  controller_port: 9001
  extra_latency_ms: 0
  sensor_noise_std: 0
    """
    config_path = tmp_path / "invalid_fdi_config.yaml"
    config_path.write_text(config_content)

    # Act: Run the simulate.py CLI with the invalid config
    result = _run_cli(["--config", str(config_path)])

    # Assert
    assert result.returncode != 0, "simulate.py should fail with a misconfigured FDI"
    # Depending on validation implementation, Pydantic's ValidationError is typical
    assert ("ValidationError" in result.stderr) or ("TypeError" in result.stderr) or ("ValueError" in result.stderr)
    assert "residual_threshold" in result.stderr or "FDIsystem" in result.stderr
#===================================================================================================================\\\