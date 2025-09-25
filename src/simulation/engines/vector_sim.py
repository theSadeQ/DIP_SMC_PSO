#==========================================================================================\\\
#======================= src/simulation/engines/vector_sim.py =======================\\\
#==========================================================================================\\\
"""
Unified simulation façade with vectorized safety guards.

This module provides a high‑level ``simulate`` function that accepts either
scalar or batched initial states and control inputs.  It dispatches the
underlying dynamics step through ``src.simulation.engines.simulation_runner.step`` and
invokes safety guards after each step and before returning results.  The
interface maintains shape parity between scalar and batch modes: a single
simulation returns an array of shape ``(H+1, D)`` while a batch of B
simulations returns a tensor of shape ``(B, H+1, D)``.  The initial state is
always included at index ``0`` of the time dimension.

Early stopping is supported via a simple stop callback: if ``stop_fn`` is
provided and returns True given the current state, all remaining steps are
skipped and the output is truncated to the elapsed horizon plus one.  To
preserve uniform batch shapes, the earliest stopping time across batch
elements truncates the entire batch.
"""

from __future__ import annotations

import numpy as np
from typing import Any, Callable, Optional, Tuple

from .simulation_runner import step as _step_fn  # dispatches on config flag
from ..context.safety_guards import _guard_no_nan, _guard_energy, _guard_bounds
try:
    from src.config.schemas import config  # type: ignore
except Exception:
    from types import SimpleNamespace
    config = SimpleNamespace(simulation=SimpleNamespace(safety=None))


def simulate(
    initial_state: Any,
    control_inputs: Any,
    dt: float,
    horizon: Optional[int] = None,
    *,
    energy_limits: Optional[float | dict] = None,
    state_bounds: Optional[Tuple[Any, Any]] = None,
    stop_fn: Optional[Callable[[np.ndarray], bool]] = None,
    t0: float = 0.0,
) -> np.ndarray:
    """Simulate a dynamical system forward in time.

    Parameters
    ----------
    initial_state : array-like
        Initial state of shape ``(D,)`` or ``(B, D)``.  A missing batch
        dimension implies ``B=1``.
    control_inputs : array-like
        Control sequence with shape ``(H,)`` or ``(H, U)`` for scalar runs or
        ``(B, H)``/``(B, H, U)`` for batched runs.  The control dimension U
        must be broadcastable to the state dimension.
    dt : float
        Timestep between control inputs.
    horizon : int, optional
        Number of simulation steps ``H``.  If not provided it is inferred
        from the length of ``control_inputs``.
    energy_limits : float, optional
        Maximum allowed total energy.  When provided the energy guard
        compares ``sum(state**2)`` against this limit after each step.
    state_bounds : tuple, optional
        Pair ``(lower, upper)`` specifying per‑dimension bounds.  Bounds may
        be scalars or arrays broadcastable to the state shape.  A ``None``
        value disables that side of the bound.
    stop_fn : callable, optional
        Optional predicate ``stop_fn(state)``.  If provided and returns
        True, the simulation stops early and the output is truncated.
    t0 : float, default 0.0
        Initial simulation time used in bound violation messages.

    Returns
    -------
    numpy.ndarray
        Array of simulated states including the initial state.  Shape is
        ``(H_stop+1, D)`` for scalar runs or ``(B, H_stop+1, D)`` for
        batched runs, where ``H_stop <= horizon`` if early stopping
        occurred.

    Examples
    --------
    Scalar simulation:
    
    >>> import numpy as np
    >>> x0 = np.array([1.0, 0.0])
    >>> u = np.array([0.1, 0.2])
    >>> result = simulate(x0, u, 0.1)
    >>> result.shape
    (3, 2)
    >>> result[0]  # initial state
    array([1., 0.])
    
    Batch simulation with early stopping:
    
    >>> x0_batch = np.array([[1.0, 0.0], [2.0, 1.0]])  
    >>> u_batch = np.array([[0.1, 0.2], [0.3, 0.4]])
    >>> stop_fn = lambda x: np.sum(x**2) > 10.0
    >>> result = simulate(x0_batch, u_batch, 0.1, stop_fn=stop_fn)
    >>> result.shape[0] == 2  # batch size preserved
    True
    >>> result.shape[1] <= 3  # may be truncated due to early stop
    True
    """
    # Convert state to array and normalise batch dimension
    x = np.asarray(initial_state, dtype=float)
    # Determine if batch: ndim > 1 implies (B, D)
    batch_mode = x.ndim > 1
    if not batch_mode:
        x_b = x[np.newaxis, :]
    else:
        x_b = x

    # Convert controls to array and infer horizon
    u = np.asarray(control_inputs, dtype=float)
    # If horizon is not provided, infer from the length of u along its first time axis
    if horizon is None:
        # For shapes (H,) or (H,U) we treat the first dimension as time
        # For shapes (B,H) or (B,H,U) we use the second dimension
        if u.ndim == 0:
            H = 1
        elif not batch_mode:
            H = u.shape[0]
        else:
            H = u.shape[1]
    else:
        H = int(horizon)

    # Prepare output array with maximum possible horizon; will truncate on early stop
    n_batches = x_b.shape[0]
    state_dim = x_b.shape[1]
    states = np.zeros((n_batches, H + 1, state_dim), dtype=float)
    states[:, 0, :] = x_b
    t = float(t0)

    # If no explicit energy or bounds limits were provided, attempt to
    # retrieve them from the global configuration.  The config object may
    # expose ``simulation.safety`` with optional ``energy`` and ``bounds``
    # attributes.  When present these values are used as defaults for
    # the corresponding guard limits.  This lookup is performed once at
    # the start of the simulation to avoid repeated attribute access in
    # the inner loop.
    if energy_limits is None or state_bounds is None:
        try:
            sim_cfg = getattr(config, "simulation", None)
            safety_cfg = getattr(sim_cfg, "safety", None)
            if safety_cfg:
                # Populate defaults only if not explicitly provided
                if energy_limits is None and getattr(safety_cfg, "energy", None):
                    try:
                        energy_limits = float(safety_cfg.energy.max)  # type: ignore[attr-defined]
                    except Exception:
                        energy_limits = None
                if state_bounds is None and getattr(safety_cfg, "bounds", None):
                    try:
                        lower = getattr(safety_cfg.bounds, "lower", None)  # type: ignore[attr-defined]
                        upper = getattr(safety_cfg.bounds, "upper", None)  # type: ignore[attr-defined]
                        state_bounds = (lower, upper)
                    except Exception:
                        state_bounds = None
        except Exception:
            # If config is not available or lacks expected structure, ignore
            pass

    # Iterate through time steps
    stop_index = H
    for i in range(H):
        # Extract control input for this time step, broadcasting batch dimension
        if batch_mode:
            # u shape could be (B,H,U) or (H,U) or (H,) or (B,H)
            if u.ndim == 3:
                # Handle case where horizon > control sequence length
                control_idx = min(i, u.shape[1] - 1)
                u_i = u[:, control_idx, ...]
            elif u.ndim == 2:
                # Could be (B,H) or (H,U)
                if u.shape[0] == n_batches and u.shape[1] >= 1:
                    # (B,H) format - use last available control if i exceeds length
                    control_idx = min(i, u.shape[1] - 1)
                    u_i = u[:, control_idx]
                else:
                    # (H,U) broadcast across batches
                    control_idx = min(i, u.shape[0] - 1)
                    u_i = np.broadcast_to(u[control_idx], (n_batches,) + u[control_idx].shape)
            elif u.ndim == 1:
                # Scalar control input per step
                control_idx = min(i, u.shape[0] - 1)
                u_i = np.broadcast_to(u[control_idx], (n_batches,))
            else:
                control_idx = min(i, u.shape[1] - 1)
                u_i = u[:, control_idx]
        else:
            # Non‑batch: shapes (H,) or (H,U) or scalar
            if u.ndim == 0:
                # Scalar control input - use same value for all steps
                u_i = u.item()
            elif u.ndim == 1:
                control_idx = min(i, u.shape[0] - 1)
                u_i = u[control_idx]
            else:
                control_idx = min(i, u.shape[0] - 1)
                u_i = u[control_idx]
        # Advance one step using the router
        x_next = _step_fn(x_b, u_i, dt)
        # Post‑step guards
        _guard_no_nan(x_next, step_idx=i)
        if energy_limits is not None:
            limits = energy_limits if isinstance(energy_limits, dict) else {"max": float(energy_limits)}
            _guard_energy(x_next, limits=limits)
        if state_bounds is not None:
            _guard_bounds(x_next, bounds=state_bounds, t=t + dt)
        # Record and update state
        states[:, i + 1, :] = x_next
        x_b = x_next
        t += dt
        # Early stop check: call predicate on batch or scalar state
        if stop_fn is not None:
            # Evaluate stop predicate on each batch element; stop if any returns True
            if batch_mode:
                stop_mask = np.array([bool(stop_fn(s)) for s in x_b])
                if np.any(stop_mask):
                    stop_index = i + 1
                    break
            else:
                if stop_fn(x_b.squeeze() if hasattr(x_b, "squeeze") else x_b):
                    stop_index = i + 1
                    break

    # Pre‑emit guards on the final state (or truncated state)
    _guard_no_nan(x_b, step_idx=stop_index)
    if energy_limits is not None:
        _guard_energy(x_b, limits={"max": float(energy_limits)})
    if state_bounds is not None:
        _guard_bounds(x_b, bounds=state_bounds, t=t)

    # Truncate output on early stop
    result = states[:, : stop_index + 1, :]
    # Return squeezed array for scalar runs
    if not batch_mode:
        return result[0]
    return result



def simulate_system_batch(
    *,
    controller_factory: Callable[[np.ndarray], Any],
    particles: Any,
    sim_time: float,
    dt: float,
    u_max: Optional[float] = None,
    seed: Optional[int] = None,
    params_list: Optional[Iterable[Any]] = None,
    initial_state: Optional[Any] = None,
    convergence_tol: Optional[float] = None,
    grace_period: float = 0.0,
    rng: Optional[np.random.Generator] = None,
    **_kwargs: Any,
) -> Any:
    """Vectorised batch simulation of multiple controllers.

    This function wraps ``run_simulation`` to simultaneously simulate a batch
    of controllers with distinct gain vectors (``particles``).  It returns
    time, state, control and sliding-surface arrays for the entire batch.
    Optional early stopping is available: once the magnitude of the sliding
    surface ``sigma`` falls below ``convergence_tol`` for all particles (after
    a grace period), integration halts early and the outputs are truncated.

    When ``params_list`` is provided, the simulation is repeated for each
    element in the list.  The return value is then a list of results, one per
    parameter set.  For backward compatibility, the dynamics model is
    determined internally by the controller factory; perturbed physics
    parameters are ignored and results are replicated across the list.

    Parameters
    ----------
    controller_factory : callable
        Factory ``controller_factory(p)`` that returns a controller given a
        gain vector ``p``.  The returned controller must expose a
        ``dynamics_model`` attribute defining the system dynamics.
    particles : array-like
        Array of shape ``(B, G)`` where each row contains a gain vector for
        one particle.  A single particle may be provided as shape ``(G,)``.
    sim_time : float
        Total simulation duration (seconds).
    dt : float
        Timestep for integration (seconds).
    u_max : float, optional
        Control saturation limit.  Overrides controller-specific ``max_force``.
    seed : int, optional
        Deprecated.  Ignored; retained for signature compatibility.
    params_list : iterable, optional
        Optional list of physics parameter objects.  When provided, the
        simulation is repeated for each element.  The current implementation
        ignores these parameters and replicates the base results.
    initial_state : array-like, optional
        Initial state(s) for the batch.  If ``None``, a zero state is used.
        If a 1D array of length ``D`` is provided, it is broadcast across all
        particles.  If a 2D array of shape ``(B, D)`` is provided, it is used
        directly.
    convergence_tol : float, optional
        Threshold for sliding-surface convergence.  When provided and
        positive, the integration stops once ``max(|sigma|) < convergence_tol``
        across all particles (after the grace period).
    grace_period : float, optional
        Duration (seconds) to wait before checking the convergence criterion.
    rng : numpy.random.Generator, optional
        Unused in this implementation.  Present for API compatibility.

    Returns
    -------
    If ``params_list`` is not provided, returns a tuple ``(t, x_b, u_b, sigma_b)``:
    
    - ``t``: ndarray of shape ``(N+1,)`` of time points
    - ``x_b``: ndarray of shape ``(B, N+1, D)`` of states
    - ``u_b``: ndarray of shape ``(B, N)`` of controls
    - ``sigma_b``: ndarray of shape ``(B, N)`` of sliding-surface values

    If ``params_list`` is provided, returns a list of such tuples (one per
    element in ``params_list``).
    """
    import numpy as _np  # local import to avoid polluting namespace
    # Convert particles to array
    part_arr = _np.asarray(particles, dtype=float)
    if part_arr.ndim == 1:
        part_arr = part_arr[_np.newaxis, :]
    B, G = part_arr.shape
    # Determine number of steps
    dt = float(dt)
    sim_time = float(sim_time)
    H = int(round(sim_time / dt)) if sim_time > 0 else 0
    # Instantiate controllers for each particle
    controllers = []
    for j in range(B):
        try:
            ctrl = controller_factory(part_arr[j])
        except Exception:
            ctrl = controller_factory(part_arr[j])
        controllers.append(ctrl)
    # Determine state dimension from first controller's dynamics model
    if initial_state is None:
        # Try to introspect state dimension
        state_dim = None
        try:
            state_dim = int(getattr(controllers[0], "state_dim"))
        except Exception:
            try:
                state_dim = int(getattr(controllers[0], "dynamics_model").state_dim)
            except Exception:
                state_dim = 6  # fall back to DIP dimension
        init_b = _np.zeros((B, state_dim), dtype=float)
    else:
        init = _np.asarray(initial_state, dtype=float)
        if init.ndim == 1:
            # broadcast across batch
            init_b = _np.broadcast_to(init, (B, init.shape[0])).copy()
        else:
            init_b = init.copy()
    # Preallocate outputs
    t_arr = _np.zeros(H + 1, dtype=float)
    x_b = _np.zeros((B, H + 1, init_b.shape[1]), dtype=float)
    u_b = _np.zeros((B, H), dtype=float)
    sigma_b = _np.zeros((B, H), dtype=float)
    x_b[:, 0, :] = init_b
    # Convergence parameters
    check_convergence = (convergence_tol is not None) and (convergence_tol is not False)
    conv_tol = float(convergence_tol) if convergence_tol else 0.0
    grace_steps = int(round(float(grace_period) / dt)) if grace_period > 0 else 0
    # Per-controller state and history
    state_vars = [None] * B
    histories = [None] * B
    for j, ctrl in enumerate(controllers):
        try:
            if hasattr(ctrl, "initialize_state"):
                state_vars[j] = ctrl.initialize_state()  # type: ignore[assignment]
        except Exception:
            state_vars[j] = None
        try:
            if hasattr(ctrl, "initialize_history"):
                histories[j] = ctrl.initialize_history()  # type: ignore[assignment]
        except Exception:
            histories[j] = None
    # Determine per-particle saturation limits
    u_limits = _np.full(B, _np.inf, dtype=float)
    if u_max is not None:
        u_limits[:] = float(u_max)
    else:
        for j, ctrl in enumerate(controllers):
            if hasattr(ctrl, "max_force"):
                try:
                    u_limits[j] = float(getattr(ctrl, "max_force"))
                except Exception:
                    u_limits[j] = _np.inf
    # Simulation loop
    # We will reuse dynamics_model from each controller
    times = t_arr
    for i in range(H):
        t_now = i * dt
        times[i] = t_now
        # Compute controls and sigma for each particle
        for j, ctrl in enumerate(controllers):
            x_curr = x_b[j, i]
            # Use compute_control if available
            try:
                if hasattr(ctrl, "compute_control"):
                    ret = ctrl.compute_control(x_curr, state_vars[j], histories[j])
                    # ret may be namedtuple or tuple
                    try:
                        u_val = float(ret[0])
                    except Exception:
                        u_val = float(ret)
                    # update state and history
                    try:
                        if len(ret) >= 2:
                            state_vars[j] = ret[1]
                        if len(ret) >= 3:
                            histories[j] = ret[2]
                    except Exception:
                        pass
                    # extract sigma if available
                    sigma_val = 0.0
                    if hasattr(ret, "sigma"):
                        sigma_val = float(ret.sigma)
                    elif hasattr(ret, "__len__") and len(ret) >= 4:
                        sigma_val = float(ret[3])
                else:
                    u_val = float(ctrl(t_now, x_curr))
                    sigma_val = 0.0
            except Exception:
                # On error computing control, treat as instability and stop
                H = i
                u_b = u_b[:, :i]
                x_b = x_b[:, : i + 1]
                sigma_b = sigma_b[:, :i]
                times = times[: i + 1]
                # Attach histories
                for jj, c in enumerate(controllers):
                    hist = histories[jj]
                    if hist is not None:
                        try:
                            setattr(c, "_last_history", hist)
                        except Exception:
                            pass
                if params_list is not None:
                    return [(_np.copy(times), _np.copy(x_b), _np.copy(u_b), _np.copy(sigma_b)) for _ in params_list]
                return times, x_b, u_b, sigma_b
            # Saturate and store
            limit = u_limits[j]
            if limit < _np.inf:
                if u_val > limit:
                    u_val = limit
                elif u_val < -limit:
                    u_val = -limit
            u_b[j, i] = u_val
            sigma_b[j, i] = sigma_val
        # Step all particles forward using their dynamics model
        early_stop = False
        for j, ctrl in enumerate(controllers):
            dyn = getattr(ctrl, "dynamics_model", None)
            if dyn is None:
                # If controller lacks dynamics_model, fall back to global step
                try:
                    x_next = ctrl.step(x_b[j, i], u_b[j, i], dt)  # type: ignore[attr-defined]
                except Exception:
                    x_next = None
            else:
                try:
                    x_next = dyn.step(x_b[j, i], u_b[j, i], dt)
                except Exception:
                    x_next = None
            if x_next is None:
                early_stop = True
                break
            x_next_arr = _np.asarray(x_next, dtype=float).reshape(-1)
            if not _np.all(_np.isfinite(x_next_arr)):
                early_stop = True
                break
            x_b[j, i + 1] = x_next_arr
        if early_stop:
            # truncate and exit
            H = i
            u_b = u_b[:, :i]
            x_b = x_b[:, : i + 1]
            sigma_b = sigma_b[:, :i]
            times = times[: i + 1]
            for jj, c in enumerate(controllers):
                hist = histories[jj]
                if hist is not None:
                    try:
                        setattr(c, "_last_history", hist)
                    except Exception:
                        pass
            if params_list is not None:
                return [(_np.copy(times), _np.copy(x_b), _np.copy(u_b), _np.copy(sigma_b)) for _ in params_list]
            return times, x_b, u_b, sigma_b
        # Early convergence check
        if check_convergence and (i >= grace_steps):
            max_sigma = _np.max(_np.abs(sigma_b[:, i]))
            if max_sigma < conv_tol:
                H = i + 1
                u_b = u_b[:, : i + 1]
                x_b = x_b[:, : i + 2]
                sigma_b = sigma_b[:, : i + 1]
                times = times[: i + 2]
                # copy histories
                for jj, c in enumerate(controllers):
                    hist = histories[jj]
                    if hist is not None:
                        try:
                            setattr(c, "_last_history", hist)
                        except Exception:
                            pass
                if params_list is not None:
                    return [(_np.copy(times), _np.copy(x_b), _np.copy(u_b), _np.copy(sigma_b)) for _ in params_list]
                return times, x_b, u_b, sigma_b
    # Finalise times
    times[H] = H * dt
    # attach histories on controllers
    for jj, c in enumerate(controllers):
        hist = histories[jj]
        if hist is not None:
            try:
                setattr(c, "_last_history", hist)
            except Exception:
                pass
    result = (times, x_b, u_b, sigma_b)
    if params_list is None:
        return result
    # replicate results for each params entry
    return [(_np.copy(times), _np.copy(x_b), _np.copy(u_b), _np.copy(sigma_b)) for _ in params_list]
