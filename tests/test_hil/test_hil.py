"""
Tests for the hardware‑in‑the‑loop (HIL) orchestration of the double inverted
pendulum project.  These tests exercise the UDP server/client loop using the
project’s own code and validate that resources are cleaned up correctly.

The goal of this suite is to verify basic functionality without relying on an
external configuration file.  A minimal configuration is generated at runtime
and written into a temporary directory for each test.  Where possible the
project’s own modules are used directly rather than mocking internals.  This
approach ensures that the tests remain resilient to refactoring while still
running quickly.
"""

from __future__ import annotations

import socket
import struct
import threading
from pathlib import Path

import numpy as np
import pytest

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # pragma: no cover

from src.hil.plant_server import PlantServer
from src.hil.controller_client import HILControllerClient, run_client


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
# A YAML template for a minimal configuration.  Double braces are used to
# escape literal braces within the string so that str.format only replaces
# plant_port and controller_port placeholders.  All required fields for the
# project's ConfigSchema are present to ensure Pydantic validation succeeds.
CONFIG_TEMPLATE = """
global_seed: 42
controller_defaults: {{}}
controllers: {{}}
pso:
  n_particles: 1
  bounds:
    min: [0.0]
    max: [1.0]
  w: 0.5
  c1: 1.0
  c2: 1.0
  iters: 1
  n_processes: 1
  hyper_trials: 1
  hyper_search: {{}}
  study_timeout: 1
  seed: 42
  tune: {{}}
physics:
  cart_mass: 1.0
  pendulum1_mass: 1.0
  pendulum2_mass: 1.0
  pendulum1_length: 1.0
  pendulum2_length: 1.0
  pendulum1_com: 0.5
  pendulum2_com: 0.5
  pendulum1_inertia: 0.1
  pendulum2_inertia: 0.1
  gravity: 9.81
  cart_friction: 0.0
  joint1_friction: 0.0
  joint2_friction: 0.0
physics_uncertainty:
  n_evals: 1
  cart_mass: 0.0
  pendulum1_mass: 0.0
  pendulum2_mass: 0.0
  pendulum1_length: 0.0
  pendulum2_length: 0.0
  pendulum1_com: 0.0
  pendulum2_com: 0.0
  pendulum1_inertia: 0.0
  pendulum2_inertia: 0.0
  gravity: 0.0
  cart_friction: 0.0
  joint1_friction: 0.0
  joint2_friction: 0.0
simulation:
  duration: 0.2
  dt: 0.02
  initial_state: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  use_full_dynamics: false
verification:
  test_conditions: []
  integrators: ["euler"]
  criteria: {{}}
cost_function:
  weights:
    state_error: 1.0
    control_effort: 0.1
    control_rate: 0.1
    stability: 0.1
  baseline: {{}}
  instability_penalty: 1.0
sensors:
  angle_noise_std: 0.0
  position_noise_std: 0.0
  quantization_angle: 0.0
  quantization_position: 0.0
hil:
  plant_ip: "127.0.0.1"
  plant_port: {plant_port}
  controller_ip: "127.0.0.1"
  controller_port: {controller_port}
  extra_latency_ms: 0.0
  sensor_noise_std: 0.0
fdi: null
""".strip()


def _write_config(tmp_path: Path, plant_port: int, controller_port: int) -> Path:
    """
    Write a minimal YAML configuration into tmp_path for the given ports.

    This helper returns the path to the created file.  The configuration
    includes all required fields for the project’s ConfigSchema and is small
    enough to run in under a second.
    """
    content = CONFIG_TEMPLATE.format(plant_port=plant_port, controller_port=controller_port)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(content, encoding="utf-8")
    return cfg_path


def _load_raw_config(cfg_path: Path) -> dict:
    """
    Load a raw configuration dictionary from the given YAML path using PyYAML.

    PlantServer expects a plain dict when instantiated directly.  Using
    yaml.safe_load here avoids importing the project’s validated loader.
    """
    if yaml is None:
        raise RuntimeError("PyYAML is required to load the test configuration.")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_struct_compatibility() -> None:
    """
    Ensure that the command and state formats used by the PlantServer match
    those defined by the HILControllerClient.

    This test guards against accidental divergence in the struct formats, which
    would result in corrupted UDP packets at runtime.
    """
    # Compare packet sizes for commands and state vectors
    assert PlantServer.CMD_SIZE == struct.calcsize(HILControllerClient.CMD_FMT)
    assert PlantServer.STATE_SIZE == struct.calcsize(HILControllerClient.STATE_FMT)


def test_plant_server_sets_ready_event() -> None:
    """
    Verify that PlantServer signals readiness on its event once it has bound to
    the UDP socket.

    The server is started in a background thread on an automatically assigned
    port (port=0) so that no fixed ports are required.  After the ready
    event is observed the server is stopped and joined.
    """
    # Bind to port 0 to allow the OS to select an available port
    ready_event = threading.Event()
    srv = PlantServer(
        cfg={},  # empty config is acceptable for start/stop purposes
        bind_addr=("127.0.0.1", 0),
        dt=0.02,
        server_ready_event=ready_event,
    )
    th = threading.Thread(target=srv.start, daemon=True)
    th.start()
    try:
        # Wait for readiness; should be set within a reasonable time
        assert ready_event.wait(2.0), "PlantServer did not signal ready in time"
    finally:
        # Cleanly stop and join the server thread
        try:
            srv.stop()
        except Exception:
            pass
        th.join(timeout=2.0)


def test_hil_udp_roundtrip(tmp_path: Path) -> None:
    """
    Integration test for the UDP server/client loop.

    A minimal PlantServer is started in a background thread using a unique
    plant_port and controller_port.  The HILControllerClient is executed via
    its helper ``run_client`` with a matching configuration file.  After the
    run completes the results file is inspected to ensure that timesteps,
    states, and control inputs were logged correctly and are non‑trivial.
    """
    # Pick two random, unused ports for the plant and controller
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        plant_port = s.getsockname()[1]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s2:
        s2.bind(("127.0.0.1", 0))
        controller_port = s2.getsockname()[1]

    cfg_path = _write_config(tmp_path, plant_port, controller_port)
    raw_cfg = _load_raw_config(cfg_path)
    steps = 10

    # Start the server with a bounded number of steps and a ready event
    ready_event = threading.Event()
    srv = PlantServer(
        cfg=raw_cfg,
        bind_addr=("127.0.0.1", plant_port),
        dt=raw_cfg.get("simulation", {}).get("dt", 0.02),
        extra_latency_ms=raw_cfg.get("hil", {}).get("extra_latency_ms", 0.0),
        sensor_noise_std=raw_cfg.get("hil", {}).get("sensor_noise_std", 0.0),
        max_steps=steps,
        server_ready_event=ready_event,
    )
    th = threading.Thread(target=srv.start, daemon=True)
    th.start()
    try:
        # Wait for the server to be ready before starting the client
        assert ready_event.wait(2.0), "PlantServer did not signal ready"

        # Run the client for a matching number of steps and save results in tmp_path
        results_path = tmp_path / "hil_results.npz"
        outp = run_client(cfg_path=str(cfg_path), steps=steps, results_path=str(results_path))
        # The run_client helper returns a pathlib.Path; ensure it exists
        assert outp.exists(), "HILControllerClient should create the results file"

        # Load the data and perform basic sanity checks
        data = np.load(outp)
        t = data["t"]
        x = data["x"]
        u = data["u"]

        assert len(u) == steps
        assert x.shape[0] == steps + 1
        # We expect at least one measurement or control command to be non-zero
        assert np.any(np.abs(x) > 0) or np.any(np.abs(u) > 0), (
            "States or controls should not all be zero during a HIL roundtrip"
        )
    finally:
        # Stop the server and ensure the thread terminates
        try:
            srv.stop()
        except Exception:
            pass
        th.join(timeout=2.0)


def test_udp_port_released_after_server_stop(tmp_path: Path) -> None:
    """
    After a bounded HIL run the UDP port used by the PlantServer should be
    released so that it can be rebound without errors.

    This test runs a short server/client interaction on a random port and
    then immediately attempts to bind a new socket to the same port.  If the
    port was not properly closed an OSError would be raised.
    """
    # Obtain a free port for the plant and a separate port for the controller
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        plant_port = s.getsockname()[1]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s2:
        s2.bind(("127.0.0.1", 0))
        controller_port = s2.getsockname()[1]

    cfg_path = _write_config(tmp_path, plant_port, controller_port)
    raw_cfg = _load_raw_config(cfg_path)
    steps = 5

    ready_event = threading.Event()
    srv = PlantServer(
        cfg=raw_cfg,
        bind_addr=("127.0.0.1", plant_port),
        dt=raw_cfg.get("simulation", {}).get("dt", 0.02),
        extra_latency_ms=raw_cfg.get("hil", {}).get("extra_latency_ms", 0.0),
        sensor_noise_std=raw_cfg.get("hil", {}).get("sensor_noise_std", 0.0),
        max_steps=steps,
        server_ready_event=ready_event,
    )
    th = threading.Thread(target=srv.start, daemon=True)
    th.start()
    try:
        assert ready_event.wait(2.0), "PlantServer did not signal ready"
        # Run a very short client session to produce some traffic
        results_path = tmp_path / "port_release_results.npz"
        run_client(cfg_path=str(cfg_path), steps=steps, results_path=str(results_path))
    finally:
        # Stop the server and wait for it to close its socket
        try:
            srv.stop()
        except Exception:
            pass
        th.join(timeout=2.0)

    # After the server thread has finished we should be able to bind to the same port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(1.0)
        # Binding should succeed if the previous socket was closed
        sock.bind(("127.0.0.1", plant_port))
    except OSError as e:
        pytest.fail(f"PlantServer UDP port not released: {e}")
    finally:
        sock.close()


def test_missing_config_path_raises(tmp_path: Path) -> None:
    """
    _run_hil should propagate FileNotFoundError when the configuration file does not exist.

    A non‑existent path is passed directly to the helper; the resulting exception
    is expected to be a FileNotFoundError.
    """
    from app import _run_hil  # imported here to avoid circular import at module level
    missing_path = tmp_path / "does_not_exist.yaml"
    with pytest.raises(FileNotFoundError):
        _run_hil(missing_path, do_plot=False)