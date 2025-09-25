"""
Tests for latency monitoring and provenance logging.

These tests verify that the simulation runner engages a fallback controller
when the control loop overruns its deadline and that the provenance
logging infrastructure attaches commit, configuration hash and seed
metadata to log records.  Only lightweight dummy dynamics and
controllers are used so that the tests execute quickly.
"""
from __future__ import annotations

import time
from typing import List

import numpy as np
import pytest
import logging

from src.core.simulation_runner import run_simulation
from src.config.logging import configure_provenance_logging


class DummyDyn:
    """Very simple single‑state dynamics for latency tests.

    The state is updated as ``x_{k+1} = u``.  The dimension of the state
    vector is fixed at 1 for simplicity.  Using such a trivial model
    decouples latency tests from the dynamics implementation.
    """
    state_dim = 1

    def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        # Ignore dt; simply copy the applied control into the state
        return np.array([u], dtype=float)


class SlowController:
    """Controller that deliberately sleeps to exceed the control period.

    Sleeping inside ``__call__`` simulates a heavy computation that causes
    the control loop to run longer than the nominal timestep.  The
    returned control is always 1.0.  State initialisation methods are
    provided to satisfy the controller protocol.
    """

    def __call__(self, t: float, x: np.ndarray) -> float:
        # Sleep longer than dt to force a deadline miss.  Use 2 ms to
        # ensure that a dt of 1 ms triggers an overrun.
        time.sleep(0.002)
        return 1.0

    def initialize_state(self):  # type: ignore[override]
        return ()

    def initialize_history(self):  # type: ignore[override]
        return {}


def test_latency_monitor_fallback_engaged() -> None:
    """Simulation should switch to the fallback controller after a deadline miss."""
    dyn = DummyDyn()
    slow_ctrl = SlowController()
    fallback_calls: List[float] = []

    def fallback(t: float, x: np.ndarray) -> float:
        # Record invocation times for assertions
        fallback_calls.append(t)
        return 42.0

    sim_time = 0.005  # 5 ms total
    dt = 0.001       # 1 ms period
    # Run simulation with a small horizon to induce one overrun.  The
    # latency monitor should detect the first iteration's overrun and
    # engage the fallback controller on subsequent steps.
    t_arr, x_arr, u_arr = run_simulation(
        controller=slow_ctrl,
        dynamics_model=dyn,
        sim_time=sim_time,
        dt=dt,
        initial_state=np.zeros(1),
        latency_margin=0.5,  # margin unused but accepted
        fallback_controller=fallback,
    )
    # The applied control sequence should include the fallback value (42.0)
    # once the fallback controller has been engaged.  Use np.isclose to
    # avoid floating‑point equality issues.
    assert np.isclose(u_arr, 42.0).any(), (
        "Fallback control value not present in control sequence; latency monitor "
        "may not have engaged fallback."
    )
    # The fallback should have been called at least once.
    assert len(fallback_calls) >= 1


def test_provenance_logging_attaches_metadata(caplog) -> None:
    """The provenance logging setup should inject commit, config hash and seed."""
    # Ensure a clean logging environment.  Remove existing handlers
    logger = logging.getLogger()
    for h in list(logger.handlers):
        logger.removeHandler(h)
    # Configure logging with a dummy config and known seed
    config = {"foo": 1}
    seed_val = 123
    configure_provenance_logging(config, seed_val, level=logging.INFO)
    # Capture logging output
    with caplog.at_level(logging.INFO):
        logging.info("test message")
    # The first log record corresponds to the call to logging.info("test message")
    # There may be an earlier record from the configure_provenance_logging
    # startup message; filter records accordingly
    records = [r for r in caplog.records if r.getMessage() == "test message"]
    assert records, "No log record captured for test message"
    record = records[0]
    # The provenance filter should have injected commit, cfg_hash and seed
    assert hasattr(record, "commit"), "commit attribute missing in log record"
    assert hasattr(record, "cfg_hash"), "cfg_hash attribute missing in log record"
    assert hasattr(record, "seed"), "seed attribute missing in log record"
    # Seed must match the configured value
    assert record.seed == seed_val
    # Config hash should be an 8‑character hexadecimal string
    assert isinstance(record.cfg_hash, str) and len(record.cfg_hash) == 8
    # The formatted log message should include the provenance prefix
    formatted = caplog.text
    assert f"seed={seed_val}]" in formatted