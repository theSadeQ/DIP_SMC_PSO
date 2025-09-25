#==========================================================================================\\\
#========================== src/simulation/core/time_domain.py =========================\\\
#==========================================================================================\\\

"""Time domain management and scheduling utilities for simulation framework."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, Callable
import numpy as np


class TimeManager:
    """Manages time-related aspects of simulation execution."""

    def __init__(self, dt: float, total_time: Optional[float] = None, horizon: Optional[int] = None):
        """Initialize time manager.

        Parameters
        ----------
        dt : float
            Base time step
        total_time : float, optional
            Total simulation time
        horizon : int, optional
            Number of time steps
        """
        self.dt = dt
        self.total_time = total_time
        self.horizon = horizon

        # Validate inputs
        if total_time is not None and horizon is not None:
            computed_time = horizon * dt
            if not np.isclose(computed_time, total_time):
                raise ValueError(f"Inconsistent time specification: {horizon} * {dt} != {total_time}")

        # Compute missing parameter
        if total_time is None and horizon is not None:
            self.total_time = horizon * dt
        elif horizon is None and total_time is not None:
            self.horizon = int(np.ceil(total_time / dt))

        self._current_time = 0.0
        self._current_step = 0
        self._start_wall_time = None

    @property
    def current_time(self) -> float:
        """Current simulation time."""
        return self._current_time

    @property
    def current_step(self) -> int:
        """Current simulation step."""
        return self._current_step

    @property
    def progress(self) -> float:
        """Simulation progress as fraction (0.0 to 1.0)."""
        if self.total_time is None:
            return 0.0
        return min(self._current_time / self.total_time, 1.0)

    def start_simulation(self) -> None:
        """Mark simulation start time."""
        self._start_wall_time = time.perf_counter()
        self._current_time = 0.0
        self._current_step = 0

    def advance_step(self, dt: Optional[float] = None) -> Tuple[float, int]:
        """Advance simulation by one time step.

        Parameters
        ----------
        dt : float, optional
            Time step (uses default if None)

        Returns
        -------
        tuple
            (new_time, new_step)
        """
        if dt is None:
            dt = self.dt

        self._current_time += dt
        self._current_step += 1

        return self._current_time, self._current_step

    def is_finished(self) -> bool:
        """Check if simulation is complete."""
        if self.total_time is not None:
            return self._current_time >= self.total_time
        elif self.horizon is not None:
            return self._current_step >= self.horizon
        return False

    def remaining_time(self) -> float:
        """Get remaining simulation time."""
        if self.total_time is None:
            return float('inf')
        return max(0.0, self.total_time - self._current_time)

    def remaining_steps(self) -> int:
        """Get remaining simulation steps."""
        if self.horizon is None:
            return int(float('inf'))
        return max(0, self.horizon - self._current_step)

    def get_time_vector(self) -> np.ndarray:
        """Generate time vector for current simulation."""
        if self.horizon is None:
            raise ValueError("Cannot generate time vector without horizon")
        return np.linspace(0, self.horizon * self.dt, self.horizon + 1)

    def wall_clock_elapsed(self) -> float:
        """Get elapsed wall clock time since simulation start."""
        if self._start_wall_time is None:
            return 0.0
        return time.perf_counter() - self._start_wall_time

    def real_time_factor(self) -> float:
        """Compute real-time factor (simulation_time / wall_clock_time)."""
        wall_elapsed = self.wall_clock_elapsed()
        if wall_elapsed == 0.0:
            return float('inf')
        return self._current_time / wall_elapsed


class RealTimeScheduler:
    """Scheduler for real-time simulation execution."""

    def __init__(self, target_dt: float, tolerance: float = 0.001):
        """Initialize real-time scheduler.

        Parameters
        ----------
        target_dt : float
            Target time step for real-time execution
        tolerance : float, optional
            Timing tolerance (default: 1ms)
        """
        self.target_dt = target_dt
        self.tolerance = tolerance
        self._next_deadline = None
        self._missed_deadlines = 0
        self._total_steps = 0

    def start_step(self) -> None:
        """Mark start of a real-time step."""
        current_time = time.perf_counter()
        if self._next_deadline is None:
            self._next_deadline = current_time + self.target_dt
        else:
            self._next_deadline += self.target_dt

    def wait_for_next_step(self) -> bool:
        """Wait until next step deadline.

        Returns
        -------
        bool
            True if deadline was met, False if deadline was missed
        """
        if self._next_deadline is None:
            return True

        current_time = time.perf_counter()
        deadline_miss = current_time > (self._next_deadline + self.tolerance)

        if deadline_miss:
            self._missed_deadlines += 1
        else:
            # Sleep until deadline
            sleep_time = self._next_deadline - current_time
            if sleep_time > 0:
                time.sleep(sleep_time)

        self._total_steps += 1
        return not deadline_miss

    def get_timing_stats(self) -> Dict[str, Any]:
        """Get real-time execution statistics."""
        if self._total_steps == 0:
            return {"deadline_miss_rate": 0.0, "total_steps": 0, "missed_deadlines": 0}

        return {
            "deadline_miss_rate": self._missed_deadlines / self._total_steps,
            "total_steps": self._total_steps,
            "missed_deadlines": self._missed_deadlines,
            "target_dt": self.target_dt,
            "tolerance": self.tolerance
        }

    def reset(self) -> None:
        """Reset scheduler state."""
        self._next_deadline = None
        self._missed_deadlines = 0
        self._total_steps = 0


class AdaptiveTimeStep:
    """Adaptive time step management for integration."""

    def __init__(self,
                 initial_dt: float,
                 min_dt: float = 1e-6,
                 max_dt: float = 1e-1,
                 safety_factor: float = 0.9,
                 growth_factor: float = 1.5,
                 shrink_factor: float = 0.5):
        """Initialize adaptive time step controller.

        Parameters
        ----------
        initial_dt : float
            Initial time step
        min_dt : float, optional
            Minimum allowed time step
        max_dt : float, optional
            Maximum allowed time step
        safety_factor : float, optional
            Safety factor for step size adjustment
        growth_factor : float, optional
            Factor for growing time step when error is small
        shrink_factor : float, optional
            Factor for shrinking time step when error is large
        """
        self.dt = initial_dt
        self.min_dt = min_dt
        self.max_dt = max_dt
        self.safety_factor = safety_factor
        self.growth_factor = growth_factor
        self.shrink_factor = shrink_factor

        self._step_history = []
        self._error_history = []

    def update_step_size(self, error_estimate: float, tolerance: float) -> Tuple[float, bool]:
        """Update time step based on error estimate.

        Parameters
        ----------
        error_estimate : float
            Current error estimate
        tolerance : float
            Error tolerance

        Returns
        -------
        tuple
            (new_dt, accept_step)
        """
        if error_estimate <= tolerance:
            # Accept step and possibly increase dt
            accept_step = True
            if error_estimate < tolerance * 0.1:  # Error is very small
                new_dt = min(self.dt * self.growth_factor, self.max_dt)
            else:
                new_dt = self.dt
        else:
            # Reject step and decrease dt
            accept_step = False
            factor = self.safety_factor * (tolerance / error_estimate) ** (1/4)
            new_dt = max(self.dt * max(factor, self.shrink_factor), self.min_dt)

        self.dt = new_dt
        self._step_history.append(new_dt)
        self._error_history.append(error_estimate)

        return new_dt, accept_step

    def get_statistics(self) -> Dict[str, Any]:
        """Get adaptive time step statistics."""
        if not self._step_history:
            return {}

        return {
            "average_dt": np.mean(self._step_history),
            "min_dt_used": np.min(self._step_history),
            "max_dt_used": np.max(self._step_history),
            "current_dt": self.dt,
            "total_steps": len(self._step_history),
            "average_error": np.mean(self._error_history) if self._error_history else 0.0
        }