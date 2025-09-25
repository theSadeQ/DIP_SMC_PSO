#==========================================================================================\\\
#===================== src/simulation/orchestrators/batch.py =======================\\\
#==========================================================================================\\\

"""Batch simulation orchestrator for vectorized execution."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional
import numpy as np

from .base import BaseOrchestrator
from ..core.interfaces import ResultContainer
from ..results.containers import BatchResultContainer


class BatchOrchestrator(BaseOrchestrator):
    """Batch simulation orchestrator for vectorized execution.

    This orchestrator can execute multiple simulations simultaneously
    using vectorized operations, providing significant performance improvements
    for Monte Carlo analysis and parameter sweeps.
    """

    def execute(self,
               initial_state: np.ndarray,
               control_inputs: np.ndarray,
               dt: float,
               horizon: int,
               **kwargs) -> ResultContainer:
        """Execute batch simulation.

        Parameters
        ----------
        initial_state : np.ndarray
            Initial state(s) - shape (state_dim,) or (batch_size, state_dim)
        control_inputs : np.ndarray
            Control input sequence - shape (horizon,), (horizon, m), or (batch_size, horizon, m)
        dt : float
            Time step
        horizon : int
            Simulation horizon
        **kwargs
            Additional options

        Returns
        -------
        ResultContainer
            Batch simulation results
        """
        self._validate_simulation_inputs(initial_state, control_inputs, dt, horizon)

        start_time = time.perf_counter()

        # Determine batch size and normalize arrays
        initial_state = np.atleast_2d(initial_state)
        if initial_state.shape[0] == 1:
            batch_size = 1
            state_dim = initial_state.shape[1]
        else:
            batch_size = initial_state.shape[0]
            state_dim = initial_state.shape[1]

        # Normalize control inputs
        control_inputs = self._normalize_control_inputs(control_inputs, batch_size, horizon)

        # Extract options
        safety_guards = kwargs.get("safety_guards", True)
        stop_fn = kwargs.get("stop_fn", None)
        t0 = kwargs.get("t0", 0.0)

        # Prepare result arrays
        times = np.linspace(t0, t0 + horizon * dt, horizon + 1)
        states = np.zeros((batch_size, horizon + 1, state_dim))
        controls = np.zeros((batch_size, horizon))

        # Set initial states
        states[:, 0, :] = initial_state

        # Track which simulations are still active
        active_mask = np.ones(batch_size, dtype=bool)
        current_states = initial_state.copy()

        # Main simulation loop
        for i in range(horizon):
            if not np.any(active_mask):
                break

            # Get control inputs for this step
            if control_inputs.ndim == 3:
                step_controls = control_inputs[:, i, :]
            else:
                step_controls = control_inputs[:, i:i+1]

            controls[:, i] = step_controls.flat[:batch_size]

            # Apply stop condition
            if stop_fn is not None:
                for b in range(batch_size):
                    if active_mask[b] and stop_fn(current_states[b]):
                        active_mask[b] = False

            # Apply safety guards if enabled
            if safety_guards:
                for b in range(batch_size):
                    if active_mask[b]:
                        try:
                            from ..safety.guards import apply_safety_guards
                            apply_safety_guards(current_states[b], i, self.config)
                        except Exception:
                            active_mask[b] = False

            # Vectorized simulation step for active simulations
            next_states = current_states.copy()

            for b in range(batch_size):
                if active_mask[b]:
                    try:
                        control = step_controls[b] if step_controls.ndim > 1 else step_controls[b:b+1]
                        next_state = self.step(current_states[b], control, dt, t=times[i])

                        if np.isfinite(next_state).all():
                            next_states[b] = next_state
                            states[b, i+1, :] = next_state
                        else:
                            active_mask[b] = False

                    except Exception:
                        active_mask[b] = False

            current_states = next_states

        # Update statistics
        execution_time = time.perf_counter() - start_time
        total_steps = batch_size * horizon
        self._update_stats(total_steps, execution_time)

        # Create batch result container
        result = BatchResultContainer()
        for b in range(batch_size):
            # Find last valid step for this trajectory
            last_step = horizon
            for step in range(horizon, 0, -1):
                if np.isfinite(states[b, step, :]).all():
                    last_step = step
                    break

            batch_times = times[:last_step+1]
            batch_states = states[b, :last_step+1, :]
            batch_controls = controls[b, :last_step]

            result.add_trajectory(batch_states, batch_times,
                                controls=batch_controls, batch_index=b)

        return result

    def _normalize_control_inputs(self,
                                control_inputs: np.ndarray,
                                batch_size: int,
                                horizon: int) -> np.ndarray:
        """Normalize control inputs to consistent batch format."""
        control_inputs = np.atleast_2d(control_inputs)

        if control_inputs.shape[0] == horizon:
            # Shape (horizon, m) - broadcast to all batch elements
            if control_inputs.ndim == 2:
                # Expand to (batch_size, horizon, m)
                return np.tile(control_inputs[None, :, :], (batch_size, 1, 1))
            else:
                # Expand to (batch_size, horizon)
                return np.tile(control_inputs[None, :], (batch_size, 1))

        elif control_inputs.shape[0] == batch_size:
            # Already in batch format
            return control_inputs

        else:
            # Single control value - broadcast to all
            control_value = control_inputs.flat[0]
            return np.full((batch_size, horizon), control_value)


def simulate_batch(
    initial_states: np.ndarray,
    control_inputs: np.ndarray,
    dt: float,
    horizon: Optional[int] = None,
    *,
    energy_limits: Optional[float] = None,
    state_bounds: Optional[tuple] = None,
    stop_fn: Optional[Callable[[np.ndarray], bool]] = None,
    t0: float = 0.0,
    **kwargs
) -> np.ndarray:
    """Vectorized batch simulation function for backward compatibility.

    This function provides a simplified interface similar to the original
    vector_sim.simulate function.

    Parameters
    ----------
    initial_states : np.ndarray
        Initial states - shape (batch_size, state_dim)
    control_inputs : np.ndarray
        Control inputs - shape (batch_size, horizon) or (batch_size, horizon, m)
    dt : float
        Time step
    horizon : int, optional
        Simulation horizon (inferred from control_inputs if None)
    energy_limits : float, optional
        Energy limit for safety guards
    state_bounds : tuple, optional
        State bounds for safety guards
    stop_fn : callable, optional
        Early stopping function
    t0 : float, optional
        Initial time
    **kwargs
        Additional arguments

    Returns
    -------
    np.ndarray
        Batch state trajectories - shape (batch_size, horizon+1, state_dim)
    """
    from ..core.simulation_context import SimulationContext

    # Create context and orchestrator
    context = SimulationContext()
    orchestrator = BatchOrchestrator(context)

    # Infer horizon if not provided
    if horizon is None:
        if control_inputs.ndim >= 2:
            horizon = control_inputs.shape[1]
        else:
            raise ValueError("Cannot infer horizon from control_inputs shape")

    # Execute simulation
    result = orchestrator.execute(
        initial_states, control_inputs, dt, horizon,
        energy_limits=energy_limits,
        state_bounds=state_bounds,
        stop_fn=stop_fn,
        t0=t0,
        **kwargs
    )

    # Extract state trajectories
    trajectories = []
    batch_size = len(initial_states) if initial_states.ndim > 1 else 1

    for b in range(batch_size):
        states = result.get_states(batch_index=b)
        trajectories.append(states)

    return np.array(trajectories)