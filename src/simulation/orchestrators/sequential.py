#==========================================================================================\\\
#=================== src/simulation/orchestrators/sequential.py ====================\\\
#==========================================================================================\\\

"""Sequential simulation orchestrator for single-threaded execution."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional, Tuple
import numpy as np

from .base import BaseOrchestrator
from ..core.interfaces import ResultContainer
from ..results.containers import StandardResultContainer
from ..safety.guards import apply_safety_guards


class SequentialOrchestrator(BaseOrchestrator):
    """Sequential simulation orchestrator for single-threaded execution.

    This orchestrator executes simulations step-by-step in a single thread,
    providing compatibility with the original simulation_runner functionality.
    """

    def execute(self,
               initial_state: np.ndarray,
               control_inputs: np.ndarray,
               dt: float,
               horizon: int,
               **kwargs) -> ResultContainer:
        """Execute sequential simulation.

        Parameters
        ----------
        initial_state : np.ndarray
            Initial state vector
        control_inputs : np.ndarray
            Control input sequence (horizon,) or (horizon, m)
        dt : float
            Time step
        horizon : int
            Simulation horizon
        **kwargs
            Additional options (safety_guards, stop_fn, etc.)

        Returns
        -------
        ResultContainer
            Simulation results
        """
        self._validate_simulation_inputs(initial_state, control_inputs, dt, horizon)

        start_time = time.perf_counter()

        # Extract options
        safety_guards = kwargs.get("safety_guards", True)
        stop_fn = kwargs.get("stop_fn", None)
        t0 = kwargs.get("t0", 0.0)

        # Prepare arrays
        times = np.linspace(t0, t0 + horizon * dt, horizon + 1)
        states = np.zeros((horizon + 1, len(initial_state)))
        controls = np.zeros(horizon)
        states[0] = initial_state

        # Ensure control inputs have correct shape
        if control_inputs.ndim == 1 and len(control_inputs) == horizon:
            control_sequence = control_inputs
        elif control_inputs.ndim == 2 and control_inputs.shape[0] == horizon:
            control_sequence = control_inputs[:, 0]  # Take first column
        else:
            # Broadcast single control value
            control_sequence = np.full(horizon, control_inputs.flat[0])

        # Main simulation loop
        current_state = initial_state.copy()
        for i in range(horizon):
            # Get control input
            control = control_sequence[i]
            controls[i] = control

            # Check stop condition
            if stop_fn is not None and stop_fn(current_state):
                # Truncate arrays and break
                times = times[:i+1]
                states = states[:i+1]
                controls = controls[:i]
                break

            # Apply safety guards
            if safety_guards:
                apply_safety_guards(current_state, i, self.config)

            # Simulation step
            try:
                next_state = self.step(current_state, np.array([control]), dt, t=times[i])

                # Validate state
                if not np.isfinite(next_state).all():
                    # Truncate on invalid state
                    times = times[:i+1]
                    states = states[:i+1]
                    controls = controls[:i]
                    break

                states[i+1] = next_state
                current_state = next_state

            except Exception as e:
                # Simulation failed, truncate results
                times = times[:i+1]
                states = states[:i+1]
                controls = controls[:i]
                break

        # Update statistics
        execution_time = time.perf_counter() - start_time
        actual_steps = len(controls)
        self._update_stats(actual_steps, execution_time)

        # Create result container
        result = self._create_result_container()
        result.add_trajectory(states, times, controls=controls)

        return result


def get_step_fn():
    """Legacy function for backward compatibility.

    Returns
    -------
    callable
        Step function that dispatches to appropriate dynamics model
    """
    try:
        from src.config.schemas import config
        use_full = getattr(getattr(config, "simulation", None), "use_full_dynamics", False)
    except Exception:
        use_full = False

    if use_full:
        return _load_full_step()
    else:
        return _load_lowrank_step()


def _load_full_step():
    """Load full dynamics step function."""
    try:
        from ...plant.models.dip_full import step
        return step
    except Exception:
        raise RuntimeError(
            "Full dynamics unavailable: module 'dynamics_full' not found. "
            "Set config.simulation.use_full_dynamics=false or provide src/core/dynamics_full.py"
        )


def _load_lowrank_step():
    """Load low-rank dynamics step function."""
    from ...plant.models.dip_lowrank import step
    return step


def step(x, u, dt):
    """Legacy step function for backward compatibility.

    Parameters
    ----------
    x : array-like
        Current state
    u : array-like
        Control input
    dt : float
        Time step

    Returns
    -------
    array-like
        Next state
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
    """Legacy simulation runner for backward compatibility.

    This function maintains the exact interface and behavior of the original
    run_simulation function from simulation_runner.py.

    Parameters
    ----------
    controller : Any
        Controller object with __call__ or compute_control method
    dynamics_model : Any
        Dynamics model with step method
    sim_time : float
        Total simulation time
    dt : float
        Time step
    initial_state : array-like
        Initial state vector
    u_max : float, optional
        Control saturation limit
    seed : int, optional
        Random seed (deprecated, use rng)
    rng : np.random.Generator, optional
        Random number generator
    latency_margin : float, optional
        Unused (for future latency control)
    fallback_controller : callable, optional
        Fallback controller for deadline misses
    **_kwargs
        Additional arguments (ignored)

    Returns
    -------
    tuple
        (times, states, controls) arrays
    """
    # Input validation
    dt = float(dt)
    if dt <= 0.0:
        raise ValueError("dt must be positive")

    n_steps = int(round(float(sim_time) / dt)) if sim_time > 0 else 0
    x0 = np.asarray(initial_state, dtype=float).reshape(-1)
    state_dim = x0.shape[0]

    # Prepare output arrays
    t_arr = np.zeros(n_steps + 1, dtype=float)
    x_arr = np.zeros((n_steps + 1, state_dim), dtype=float)
    u_arr = np.zeros(n_steps, dtype=float)

    # Set initial conditions
    t_arr[0] = 0.0
    x_arr[0] = x0

    # Determine control saturation
    u_lim = None
    if u_max is not None:
        try:
            u_lim = float(u_max)
        except Exception:
            u_lim = None
    elif hasattr(controller, "max_force"):
        try:
            u_lim = float(getattr(controller, "max_force"))
        except Exception:
            u_lim = None

    # Setup random generator
    if rng is None and seed is not None:
        try:
            rng = np.random.default_rng(int(seed))
        except Exception:
            rng = None

    # Initialize controller state
    ctrl_state = None
    history = None

    try:
        if hasattr(controller, "initialize_state"):
            ctrl_state = controller.initialize_state()
    except Exception:
        pass

    try:
        if hasattr(controller, "initialize_history"):
            history = controller.initialize_history()
    except Exception:
        pass

    use_compute = hasattr(controller, "compute_control")
    use_fallback = False

    # Main simulation loop
    x_curr = x0.copy()
    for i in range(n_steps):
        t_now = i * dt

        # Compute control
        start_time = time.perf_counter()
        try:
            if use_fallback and fallback_controller is not None:
                u_val = float(fallback_controller(t_now, x_curr))
            else:
                if use_compute:
                    ret = controller.compute_control(x_curr, ctrl_state, history)
                    try:
                        u_val = float(ret[0])
                        if len(ret) >= 2:
                            ctrl_state = ret[1]
                        if len(ret) >= 3:
                            history = ret[2]
                    except Exception:
                        u_val = float(ret)
                else:
                    u_val = float(controller(t_now, x_curr))
        except Exception:
            # Terminate on control exception
            t_arr = t_arr[:i+1]
            x_arr = x_arr[:i+1]
            u_arr = u_arr[:i]
            break

        end_time = time.perf_counter()
        if (not use_fallback) and (fallback_controller is not None) and ((end_time - start_time) > dt):
            use_fallback = True

        # Saturate control
        if u_lim is not None:
            u_val = np.clip(u_val, -u_lim, u_lim)

        u_arr[i] = u_val

        # Propagate dynamics
        try:
            x_next = dynamics_model.step(x_curr, u_val, dt)
            x_next = np.asarray(x_next, dtype=float).reshape(-1)

            if not np.all(np.isfinite(x_next)):
                t_arr = t_arr[:i+1]
                x_arr = x_arr[:i+1]
                u_arr = u_arr[:i]
                break

            t_arr[i+1] = (i+1) * dt
            x_arr[i+1] = x_next
            x_curr = x_next

        except Exception:
            t_arr = t_arr[:i+1]
            x_arr = x_arr[:i+1]
            u_arr = u_arr[:i]
            break

    # Store final history
    if history is not None:
        try:
            setattr(controller, "_last_history", history)
        except Exception:
            pass

    return t_arr, x_arr, u_arr