# test_hybrid_extra
"""Additional invariants for the hybrid adaptive SMC controller.

This module complements the existing controller tests by covering edge
behaviours of the hybrid adaptive super‑twisting sliding mode controller.
Tests are intentionally grouped into a single file to minimise overhead
and to make it easy to see all invariants at a glance.  The fixtures
``make_hybrid``, ``full_dynamics`` and ``initial_state`` are defined in
``tests/conftest.py``.
"""

# F‑4.HybridController.4 / RC‑04 / D‑01,D‑02 — This module exercises a variety of
# invariants on the hybrid adaptive STA controller.  Tests cover the dead‑zone
# freeze, anti‑windup roll‑back of the integral state, adaptation rate limits,
# actuator saturation, safe equivalent control, reproducibility, robustness sweeps
# and gain growth.  These behaviours correspond to design‑review findings on
# boundary‑layer relationships, adaptive gain clipping and soft saturation width
# constraints.  Additional findings such as F‑5.VectorSim.2 (adapt rate limit),
# F‑3.SimulationLoop.1 (buffer sizing) and F‑8.Seeding.1 (reproducibility) are
# implicitly validated by these invariants.

import numpy as np
import pytest
import inspect


def _init_sv_hist(ctrl):
    """Return (state_vars, history) regardless of controller API.

    Some controller implementations expose `initialize_state`/`initialize_history` and
    return (u, new_vars, history) from `compute_control`.  Others store internal
    state as attributes and return only `u`.  This helper hides the differences
    and always returns a tuple of state variables and a history dict.
    """
    if hasattr(ctrl, "initialize_state") and hasattr(ctrl, "initialize_history"):
        return ctrl.initialize_state(), ctrl.initialize_history()
    # Fallback: synthesise from known attributes or defaults
    k1 = getattr(ctrl, "k1", 0.0)
    k2 = getattr(ctrl, "k2", 0.0)
    u_int = getattr(ctrl, "u_int", 0.0)
    sv = (k1, k2, u_int)
    hist = {
        "k1": list(getattr(ctrl, "k1_hist", [])),
        "k2": list(getattr(ctrl, "k2_hist", [])),
    }
    return sv, hist


def _compute(ctrl, state, state_vars=None, history=None):
    """Call compute_control in a signature‑agnostic way.

    Always returns `(u, (k1, k2, u_int), history_dict)` regardless of the
    controller's API surface.  When the controller exposes only a single
    argument `compute_control(state)` it reads internals to
    construct the returned state vars and history.
    """
    # Inspect the signature to determine how many positional parameters are expected
    try:
        sig = inspect.signature(ctrl.compute_control)
    except (ValueError, TypeError):
        sig = None

    if sig and len(sig.parameters) == 1:
        # API: u = compute_control(state); read internals
        u = ctrl.compute_control(state)
        k1 = getattr(ctrl, "k1", None)
        k2 = getattr(ctrl, "k2", None)
        u_int = getattr(ctrl, "u_int", 0.0)
        hist = {
            "k1": list(getattr(ctrl, "k1_hist", [])),
            "k2": list(getattr(ctrl, "k2_hist", [])),
        }
        return u, (k1, k2, u_int), hist

    # API: HybridSTAOutput = compute_control(state, state_vars, history)
    if state_vars is None or history is None:
        state_vars, history = _init_sv_hist(ctrl)

    result = ctrl.compute_control(state, state_vars, history)

    # Handle HybridSTAOutput (NamedTuple with u, state, history, sigma fields)
    if hasattr(result, 'u') and hasattr(result, 'state') and hasattr(result, 'history'):
        return result.u, result.state, result.history

    # Fallback for tuple unpacking (old API)
    return result
def test_dead_zone_freezes_int_and_gains(make_hybrid):
    """Inside the dead‑zone the STA integral and adaptation gains must not change."""
    ctrl = make_hybrid(gains=[5.0, 3.0, 5.0, 1.8], use_relative_surface=True)  # Use relative formulation as mentioned in comment
    # Choose angles so that the sliding surface s ≈ 0.  With the relative
    # formulation s = c1*(θ̇₁ + λ₁ θ₁) + c2*((θ̇₂ − θ̇₁) + λ₂ (θ₂ − θ₁)) and zero
    # velocities this reduces to  s = c1*λ₁ θ₁ + c2*λ₂ (θ₂−θ₁).  Using the
    # default gains [5.0, 3.0, 5.0, 1.8] yields  s ≈ 15·θ₁ + 9·(θ₂−θ₁) =
    # 6·θ₁ + 9·θ₂.  Setting θ₂ = −(2/3)·θ₁ makes s≈0.
    theta1 = 1.0e-3
    theta2 = -(2.0 / 3.0) * theta1
    state = np.array([0.0, theta1, theta2, 0.0, 0.0, 0.0], dtype=float)
    # Initialise state variables and history via compatibility helper
    state_vars, history = _init_sv_hist(ctrl)
    # Compute control once using the agnostic wrapper
    _, new_vars, _ = _compute(ctrl, state, state_vars, history)
    # Gains and integral should remain unchanged within small numerical tolerances
    assert new_vars[0] == pytest.approx(state_vars[0], abs=5e-5)  # k1
    assert new_vars[1] == pytest.approx(state_vars[1], abs=5e-5)  # k2
    assert new_vars[2] == pytest.approx(state_vars[2], abs=5e-7)  # u_int


def test_anti_windup_rolls_back_integral(make_hybrid):
    """When the control saturates the integral component should roll back."""
    # Use a small max_force to force saturation
    ctrl = make_hybrid(max_force=10.0)
    # Large sliding surface to drive the controller into saturation
    state = np.array([0.0, 0.6, -0.5, 0.0, 0.0, 0.0], dtype=float)
    # Initialise state variables and history
    state_vars, history = _init_sv_hist(ctrl)
    _, new_vars, _ = _compute(ctrl, state, state_vars, history)
    # The integral should be rolled back to its previous value (zero)
    assert abs(new_vars[2]) < 1e-6, "Integral should rollback on saturation"


def test_adaptation_rate_limit_and_clip(make_hybrid):
    """Gains must respect the adaptation rate limit and remain within [0, max_force]."""
    ctrl = make_hybrid(max_force=20.0)
    # Exaggerate the sliding surface to drive adaptation aggressively
    state = np.array([0.0, 1.0, -1.0, 0.0, 0.0, 0.0], dtype=float)
    state_vars, history = _init_sv_hist(ctrl)
    # Perform many iterations to approach the adaptation upper bound
    for _ in range(2000):
        _, state_vars, history = _compute(ctrl, state, state_vars, history)
    k1_final, k2_final, _ = state_vars
    assert 0.0 <= k1_final <= ctrl.max_force
    assert 0.0 <= k2_final <= ctrl.max_force


def test_saturation_respected(make_hybrid):
    """The final control should never exceed ±max_force."""
    ctrl = make_hybrid(max_force=25.0)
    for th in [0.5, 1.0, -0.7]:
        state_vars, history = _init_sv_hist(ctrl)
        # Create a state with opposing pendulum angles to produce large s
        state = np.array([0.0, th, -th / 2.0, 0.0, 0.0, 0.0], dtype=float)
        u, _, _ = _compute(ctrl, state, state_vars, history)
        assert abs(u) <= ctrl.max_force + 1e-9


def test_u_eq_safety_zero_on_bad_condition(make_hybrid, full_dynamics):
    """Equivalent control path must not produce NaN or inf when ill‑conditioned."""
    ctrl = make_hybrid()
    # Attach the full dynamics to enable u_eq if the controller supports it
    if hasattr(ctrl, "set_dynamics"):
        ctrl.set_dynamics(full_dynamics)
    # Near origin; check that the returned control is finite
    state = np.zeros(6, dtype=float)
    u, _, _ = _compute(ctrl, state)
    assert np.isfinite(u)


def test_reproducible_trajectories(make_hybrid, full_dynamics, initial_state):
    """Two controllers with identical parameters should produce identical trajectories."""
    from src.core.simulation_runner import run_simulation
    # First controller
    c1 = make_hybrid()
    if hasattr(c1, "set_dynamics"):
        c1.set_dynamics(full_dynamics)
    # Second controller
    c2 = make_hybrid()
    if hasattr(c2, "set_dynamics"):
        c2.set_dynamics(full_dynamics)
    # Run two simulations
    t1, X1, U1 = run_simulation(controller=c1, dynamics_model=full_dynamics, sim_time=6.0, dt=0.001, initial_state=initial_state)
    t2, X2, U2 = run_simulation(controller=c2, dynamics_model=full_dynamics, sim_time=6.0, dt=0.001, initial_state=initial_state)
    # Trajectories and control histories must match exactly
    assert np.allclose(X1, X2)
    assert np.allclose(U1, U2)


@pytest.mark.parametrize(
    "dt,th1,th2",
    [
        (0.0005, 0.15, -0.10),
        (0.0010, 0.20, -0.15),
        (0.0015, 0.12, -0.08),
    ],
)
def test_robustness_sweep(make_hybrid, full_dynamics, dt, th1, th2):
    """Controller should stabilise a range of initial perturbations without NaNs or saturation."""
    from src.core.simulation_runner import run_simulation
    ctrl = make_hybrid(dt=dt)
    if hasattr(ctrl, "set_dynamics"):
        ctrl.set_dynamics(full_dynamics)
    x0 = np.array([0.0, th1, th2, 0.0, 0.0, 0.0], dtype=float)
    _, X, U = run_simulation(controller=ctrl, dynamics_model=full_dynamics, sim_time=5.0, dt=dt, initial_state=x0)
    # Ensure no infinities or NaNs in the state trajectory
    assert np.all(np.isfinite(X))
    # Control should respect the actuator limit
    assert np.max(np.abs(U)) <= ctrl.max_force + 1e-9
    # Final angles should be close to upright
    assert np.all(np.abs(X[-1, :3]) < 0.05)


def test_gain_growth_slows_in_second_half(make_hybrid, full_dynamics, initial_state):
    """Adaptive gains should grow more slowly in the second half of a simulation."""
    from src.core.simulation_runner import run_simulation
    ctrl = make_hybrid()
    if hasattr(ctrl, "set_dynamics"):
        ctrl.set_dynamics(full_dynamics)
    # Run a moderately long simulation to gather a history
    _, X, _ = run_simulation(controller=ctrl, dynamics_model=full_dynamics, sim_time=10.0, dt=0.001, initial_state=initial_state)
    # Recompute control offline to collect gain histories
    state_vars, history = _init_sv_hist(ctrl)
    for state in X:
        _, state_vars, history = _compute(ctrl, state, state_vars, history)
    k1_hist = np.array(history.get("k1", []), dtype=float)
    k2_hist = np.array(history.get("k2", []), dtype=float)
    # Compute mean increment in the first and second halves
    n = len(k1_hist)
    if n < 4:
        pytest.skip("Not enough samples to assess gain growth")
    mid = n // 2
    inc1_k1 = (k1_hist[mid] - k1_hist[0]) / max(1, mid)
    inc2_k1 = (k1_hist[-1] - k1_hist[mid]) / max(1, n - mid)
    inc1_k2 = (k2_hist[mid] - k2_hist[0]) / max(1, mid)
    inc2_k2 = (k2_hist[-1] - k2_hist[mid]) / max(1, n - mid)
    assert inc2_k1 <= inc1_k1 + 1e-9
    assert inc2_k2 <= inc1_k2 + 1e-9


@pytest.mark.slow
def test_long_run_no_drift(make_hybrid, full_dynamics, initial_state):
    """Over a long duration the controller should stabilise without drift."""
    from src.core.simulation_runner import run_simulation
    ctrl = make_hybrid()
    if hasattr(ctrl, "set_dynamics"):
        ctrl.set_dynamics(full_dynamics)
    _, X, U = run_simulation(controller=ctrl, dynamics_model=full_dynamics, sim_time=30.0, dt=0.001, initial_state=initial_state)
    # Actuator should respect its limit even over long horizons
    assert np.max(np.abs(U)) <= ctrl.max_force + 1e-9
    # Final state should be close to the upright equilibrium
    assert np.all(np.abs(X[-1, :3]) < 0.02)
#=============================================================================\\\