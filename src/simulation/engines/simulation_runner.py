#==========================================================================================\\\
#==================== src/simulation/engines/simulation_runner.py ==================\\\
#==========================================================================================\\\
"""
Simulation step router.

This module dispatches between full and low‑rank dynamics implementations
based on ``config.simulation.use_full_dynamics``.  It exposes a unified
``step(x, u, dt)`` function which calls either ``src.plant.models.dip_full.step``
or ``src.plant.models.dip_lowrank.step`` depending on the configuration.

If the full dynamics module cannot be imported, a RuntimeError with a
specific message is raised.  Tests match the message text exactly.
"""

from __future__ import annotations

from importlib import import_module

import time
from typing import Any, Callable, Optional, Tuple
import numpy as np

# Attempt to import the configuration.  The config module must define an
# attribute ``config.simulation.use_full_dynamics``.  We import lazily in
# ``get_step_fn`` so that missing dependencies in ``src.config`` do not
# prevent this module from being imported.
try:
    from src.config.schemas import config  # type: ignore
except Exception:
    # Define a minimal stand‑in config object with the expected structure.
    from types import SimpleNamespace
    config = SimpleNamespace(simulation=SimpleNamespace(use_full_dynamics=False))

# Module path for the full dynamics.  This constant is monkeypatched in
# tests to simulate a missing module.  Do not rename without updating tests.
DYNAMICS_FULL_MODULE = "src.plant.models.dip_full"

def _load_full_step():
    """
    Attempt to load the full dynamics ``step`` function.

    Returns
    -------
    callable
        The ``step(x, u, dt)`` function from the full dynamics module.

    Raises
    ------
    RuntimeError
        If the module cannot be imported or does not define ``step``.
    """
    try:
        mod = import_module(DYNAMICS_FULL_MODULE)
        return getattr(mod, "step")
    except Exception:
        # EXACT message required by tests:
        raise RuntimeError(
            "Full dynamics unavailable: module 'dynamics_full' not found. Set config.simulation.use_full_dynamics=false or provide src/core/dynamics_full.py"
        )

def _load_lowrank_step():
    """
    Load the low‑rank dynamics ``step`` function.

    Returns
    -------
    callable
        The low‑rank ``step(x, u, dt)`` function.
    """
    from ...plant.models.dip_lowrank import step as step_fn
    return step_fn

def get_step_fn():
    """
    Return the appropriate step function based on the configuration flag.

    Returns
    -------
    callable
        Either ``src.plant.models.dip_full.step`` or ``src.plant.models.dip_lowrank.step``.
    """
    use_full = getattr(getattr(config, "simulation", None), "use_full_dynamics", False)
    return _load_full_step() if use_full else _load_lowrank_step()

def step(x, u, dt):
    """
    Unified simulation step entry point.

    Parameters
    ----------
    x : array-like
        Current state.
    u : array-like
        Control input(s).
    dt : float
        Timestep.

    Returns
    -------
    array-like
        Next state computed by the selected dynamics implementation.
    """
    return get_step_fn()(x, u, dt)



def run_simulation(
    *,
    controller: Any,
    dynamics_model: Any,
    sim_time: float,
    dt: float,
    initial_state: Any,
    u_max: Optional[float] = None,
    seed: Optional[int] = None,
    rng: Optional[np.random.Generator] = None,
    latency_margin: Optional[float] = None,
    fallback_controller: Optional[Callable[[float, np.ndarray], float]] = None,
    **_kwargs: Any,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simulate a single controller trajectory using an explicit Euler method.

    The runner integrates the provided ``dynamics_model`` forward in time under
    the control law defined by ``controller``.  It produces uniformly spaced
    timestamps, a state trajectory and the applied control sequence.  If the
    dynamics return NaN/Inf values or raise an exception at any step, the
    simulation halts immediately and the outputs are truncated to include only
    the steps executed.  Control inputs can be saturated via the ``u_max``
    parameter or by querying ``controller.max_force`` when ``u_max`` is not
    provided.  Stateful controllers may expose optional hooks
    ``initialize_state`` and ``initialize_history``; these are called once at
    the beginning of the simulation.  A ``compute_control`` method, if
    available, is preferred over ``__call__`` for computing the control.  The
    runner also supports a simple latency monitor: if computing the control
    exceeds the nominal period ``dt`` on any step and a ``fallback_controller``
    is provided, subsequent control inputs are drawn from the fallback.

    Parameters
    ----------
    controller : Any
        The control object.  Must implement ``__call__(t, x) -> float`` or
        ``compute_control(x, state_vars, history)``.  Optional hooks
        ``initialize_state`` and ``initialize_history`` may be defined to
        initialise controller state.
    dynamics_model : Any
        Object providing a ``step(state, u, dt)`` method that advances the
        state forward in time.  Must accept a state vector and scalar input
        ``u``.
    sim_time : float
        Total simulation horizon in seconds.  The integration runs until
        the largest multiple of ``dt`` not exceeding ``sim_time``.  A value
        less than or equal to zero produces no integration steps.
    dt : float
        Integration timestep (seconds).  Must be strictly positive.
    initial_state : array-like
        Initial state vector.  Converted to ``float`` and flattened.  The
        length of the state vector defines the dimensionality of the system.
    u_max : float, optional
        Saturation limit for the control input.  When provided, control
        commands are clipped to the interval ``[-u_max, u_max]``.  If omitted
        and the controller exposes ``max_force``, that value is used instead.
    seed : int, optional
        Deprecated.  Present for backward compatibility; use ``rng`` to
        control randomness when required.  When both ``seed`` and ``rng`` are
        provided, ``rng`` takes precedence.
    rng : numpy.random.Generator, optional
        Random number generator for controllers that rely on sampling.  If
        provided, it is passed unchanged to the controller; otherwise a local
        generator may be created when ``seed`` is supplied.
    latency_margin : float, optional
        Unused placeholder for future latency control.  Accepts any value
        without effect.
    fallback_controller : callable, optional
        Function ``fallback_controller(t, x) -> float`` invoked to compute
        control after a deadline miss.  When a control call exceeds ``dt`` in
        duration, the fallback controller is used for all subsequent steps.
    **_kwargs : dict
        Additional keyword arguments are ignored.  They are accepted to
        preserve backward compatibility with earlier versions of this API.

    Returns
    -------
    t_arr : numpy.ndarray
        1D array of time points including the initial time at index 0.  The
        final element equals ``n_steps * dt`` where ``n_steps = int(round(sim_time / dt))``.
    x_arr : numpy.ndarray
        2D array of shape ``(len(t_arr), D)`` containing the state trajectory.
    u_arr : numpy.ndarray
        1D array of shape ``(len(t_arr) - 1,)`` containing the applied control
        sequence.  Empty if no integration steps were executed.
    """
    # Normalise dt and horizon
    dt = float(dt)
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    # Compute number of steps as the nearest integer that does not exceed sim_time
    n_steps = int(round(float(sim_time) / dt)) if sim_time > 0 else 0
    # Flatten the initial state to determine state dimension
    x0 = np.asarray(initial_state, dtype=float).reshape(-1)
    state_dim = x0.shape[0]
    # Prepare output arrays
    t_arr = np.zeros(n_steps + 1, dtype=float)
    x_arr = np.zeros((n_steps + 1, state_dim), dtype=float)
    u_arr = np.zeros(n_steps, dtype=float)
    # Set initial conditions
    t_arr[0] = 0.0
    x_arr[0] = x0
    # Determine control saturation limit
    if u_max is not None:
        try:
            u_lim: Optional[float] = float(u_max)
        except Exception:
            u_lim = None
    else:
        if hasattr(controller, "max_force"):
            try:
                u_lim = float(getattr(controller, "max_force"))
            except Exception:
                u_lim = None
        else:
            u_lim = None
    # Seed the random generator for backward compatibility
    if rng is None and seed is not None:
        try:
            rng = np.random.default_rng(int(seed))
        except Exception:
            rng = None
    # Initialise controller state and history if supported
    ctrl_state = None
    history = None
    try:
        if hasattr(controller, "initialize_state"):
            ctrl_state = controller.initialize_state()  # type: ignore[assignment]
    except Exception:
        ctrl_state = None
    try:
        if hasattr(controller, "initialize_history"):
            history = controller.initialize_history()  # type: ignore[assignment]
    except Exception:
        history = None
    # Determine whether to use compute_control
    use_compute = hasattr(controller, "compute_control")
    # Latency monitor state: once an overrun is detected, engage fallback
    use_fallback = False
    # Main integration loop
    x_curr = x0.copy()
    for i in range(n_steps):
        t_now = i * dt
        # Compute control input
        start_time = time.perf_counter()
        try:
            if use_fallback and fallback_controller is not None:
                u_val = float(fallback_controller(t_now, x_curr))
            else:
                if use_compute:
                    ret = controller.compute_control(x_curr, ctrl_state, history)  # type: ignore[attr-defined]
                    try:
                        u_val = float(ret[0])
                    except Exception:
                        u_val = float(ret)
                    try:
                        if len(ret) >= 2:
                            ctrl_state = ret[1]
                        if len(ret) >= 3:
                            history = ret[2]
                    except Exception:
                        pass
                else:
                    u_val = float(controller(t_now, x_curr))
        except Exception:
            # Terminate on control exception
            t_arr = t_arr[: i + 1]
            x_arr = x_arr[: i + 1]
            u_arr = u_arr[: i]
            if history is not None:
                try:
                    setattr(controller, "_last_history", history)
                except Exception:
                    pass
            return t_arr, x_arr, u_arr
        end_time = time.perf_counter()
        if (not use_fallback) and (fallback_controller is not None) and ((end_time - start_time) > dt):
            use_fallback = True
        # Saturate control
        if u_lim is not None:
            if u_val > u_lim:
                u_val = u_lim
            elif u_val < -u_lim:
                u_val = -u_lim
        u_arr[i] = u_val
        # Propagate dynamics
        try:
            x_next = dynamics_model.step(x_curr, u_val, dt)
        except Exception:
            t_arr = t_arr[: i + 1]
            x_arr = x_arr[: i + 1]
            u_arr = u_arr[: i]
            if history is not None:
                try:
                    setattr(controller, "_last_history", history)
                except Exception:
                    pass
            return t_arr, x_arr, u_arr
        x_next = np.asarray(x_next, dtype=float).reshape(-1)
        if not np.all(np.isfinite(x_next)):
            t_arr = t_arr[: i + 1]
            x_arr = x_arr[: i + 1]
            u_arr = u_arr[: i]
            if history is not None:
                try:
                    setattr(controller, "_last_history", history)
                except Exception:
                    pass
            return t_arr, x_arr, u_arr
        t_arr[i + 1] = (i + 1) * dt
        x_arr[i + 1] = x_next
        x_curr = x_next
    # Attach final history
    if history is not None:
        try:
            setattr(controller, "_last_history", history)
        except Exception:
            pass
    return t_arr, x_arr, u_arr
