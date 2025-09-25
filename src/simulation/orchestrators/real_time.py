#==========================================================================================\\\
#=================== src/simulation/orchestrators/real_time.py =====================\\\
#==========================================================================================\\\

"""Real-time simulation orchestrator with timing constraints."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional
import numpy as np

from .base import BaseOrchestrator
from ..core.interfaces import ResultContainer
from ..core.time_domain import RealTimeScheduler
from ..results.containers import StandardResultContainer


class RealTimeOrchestrator(BaseOrchestrator):
    """Real-time simulation orchestrator with timing constraints.

    This orchestrator executes simulations with real-time timing constraints,
    useful for hardware-in-the-loop testing and real-time control verification.
    """

    def __init__(self, context, real_time_factor: float = 1.0, tolerance: float = 0.001):
        """Initialize real-time orchestrator.

        Parameters
        ----------
        context : SimulationContext
            Simulation context
        real_time_factor : float, optional
            Real-time scaling factor (1.0 = real-time, 0.5 = half-speed, etc.)
        tolerance : float, optional
            Timing tolerance in seconds
        """
        super().__init__(context)
        self.real_time_factor = real_time_factor
        self.tolerance = tolerance
        self._scheduler = None

    def execute(self,
               initial_state: np.ndarray,
               control_inputs: np.ndarray,
               dt: float,
               horizon: int,
               **kwargs) -> ResultContainer:
        """Execute real-time simulation.

        Parameters
        ----------
        initial_state : np.ndarray
            Initial state vector
        control_inputs : np.ndarray
            Control input sequence or controller function
        dt : float
            Time step
        horizon : int
            Simulation horizon
        **kwargs
            Additional options

        Returns
        -------
        ResultContainer
            Real-time simulation results
        """
        self._validate_simulation_inputs(initial_state, control_inputs, dt, horizon)

        # Adjust dt for real-time factor
        scaled_dt = dt / self.real_time_factor

        # Initialize real-time scheduler
        self._scheduler = RealTimeScheduler(scaled_dt, self.tolerance)

        start_time = time.perf_counter()

        # Extract options
        controller = kwargs.get("controller", None)
        safety_guards = kwargs.get("safety_guards", True)
        stop_fn = kwargs.get("stop_fn", None)
        t0 = kwargs.get("t0", 0.0)
        deadline_miss_handler = kwargs.get("deadline_miss_handler", None)

        # Prepare arrays
        times = np.linspace(t0, t0 + horizon * dt, horizon + 1)
        states = np.zeros((horizon + 1, len(initial_state)))
        controls = np.zeros(horizon)
        deadline_misses = []

        states[0] = initial_state

        # Main real-time simulation loop
        current_state = initial_state.copy()

        for i in range(horizon):
            # Start timing for this step
            self._scheduler.start_step()

            # Check stop condition
            if stop_fn is not None and stop_fn(current_state):
                times = times[:i+1]
                states = states[:i+1]
                controls = controls[:i]
                break

            # Apply safety guards
            if safety_guards:
                try:
                    from ..safety.guards import apply_safety_guards
                    apply_safety_guards(current_state, i, self.config)
                except Exception:
                    break

            # Compute control input
            if controller is not None:
                try:
                    control = self._compute_control(controller, times[i], current_state, i)
                except Exception as e:
                    if deadline_miss_handler:
                        control = deadline_miss_handler(times[i], current_state)
                    else:
                        control = 0.0  # Safe fallback
            else:
                # Use pre-computed control sequence
                if control_inputs.ndim == 1:
                    control = control_inputs[i] if i < len(control_inputs) else 0.0
                else:
                    control = control_inputs[i, 0] if i < control_inputs.shape[0] else 0.0

            controls[i] = control

            # Execute simulation step
            try:
                next_state = self.step(current_state, np.array([control]), dt, t=times[i])

                if not np.isfinite(next_state).all():
                    times = times[:i+1]
                    states = states[:i+1]
                    controls = controls[:i]
                    break

                states[i+1] = next_state
                current_state = next_state

            except Exception:
                times = times[:i+1]
                states = states[:i+1]
                controls = controls[:i]
                break

            # Wait for next step deadline
            deadline_met = self._scheduler.wait_for_next_step()
            if not deadline_met:
                deadline_misses.append(i)

        # Update statistics
        execution_time = time.perf_counter() - start_time
        actual_steps = len(controls)
        self._update_stats(actual_steps, execution_time)

        # Create result container with timing information
        result = self._create_result_container()
        result.add_trajectory(states, times, controls=controls)

        # Add timing statistics
        timing_stats = self._scheduler.get_timing_stats()
        timing_stats['deadline_misses'] = deadline_misses
        timing_stats['execution_time'] = execution_time
        timing_stats['real_time_factor'] = self.real_time_factor

        result.metadata = getattr(result, 'metadata', {})
        result.metadata['timing'] = timing_stats

        return result

    def _compute_control(self,
                        controller: Any,
                        t: float,
                        state: np.ndarray,
                        step: int) -> float:
        """Compute control input with timing measurement."""
        start_time = time.perf_counter()

        try:
            if hasattr(controller, 'compute_control'):
                result = controller.compute_control(state, None, None)
                if isinstance(result, (list, tuple)):
                    control = float(result[0])
                else:
                    control = float(result)
            elif callable(controller):
                control = float(controller(t, state))
            else:
                raise ValueError("Controller must be callable or have compute_control method")

            computation_time = time.perf_counter() - start_time

            # Check if computation exceeded time budget
            time_budget = self._scheduler.target_dt
            if computation_time > time_budget:
                print(f"Warning: Control computation at step {step} took {computation_time:.6f}s "
                      f"(budget: {time_budget:.6f}s)")

            return control

        except Exception as e:
            print(f"Control computation failed at step {step}: {e}")
            raise

    def get_real_time_statistics(self) -> dict:
        """Get real-time execution statistics."""
        if self._scheduler is None:
            return {}

        stats = self._scheduler.get_timing_stats()
        stats.update(self.get_execution_statistics())
        return stats

    def set_real_time_factor(self, factor: float) -> None:
        """Set real-time scaling factor.

        Parameters
        ----------
        factor : float
            Real-time factor (1.0 = real-time, 0.5 = half-speed, etc.)
        """
        self.real_time_factor = factor
        if self._scheduler:
            self._scheduler.target_dt = self.default_dt / factor


class HardwareInLoopOrchestrator(RealTimeOrchestrator):
    """Hardware-in-the-loop simulation orchestrator.

    Extends real-time orchestrator with hardware interface capabilities.
    """

    def __init__(self,
                 context,
                 hardware_interface=None,
                 real_time_factor: float = 1.0,
                 tolerance: float = 0.001):
        """Initialize HIL orchestrator.

        Parameters
        ----------
        context : SimulationContext
            Simulation context
        hardware_interface : Any, optional
            Hardware interface object with read_sensors/write_actuators methods
        real_time_factor : float, optional
            Real-time scaling factor
        tolerance : float, optional
            Timing tolerance
        """
        super().__init__(context, real_time_factor, tolerance)
        self.hardware_interface = hardware_interface

    def _read_hardware_state(self) -> np.ndarray:
        """Read state from hardware sensors."""
        if self.hardware_interface and hasattr(self.hardware_interface, 'read_sensors'):
            return self.hardware_interface.read_sensors()
        else:
            raise RuntimeError("Hardware interface not available or missing read_sensors method")

    def _write_hardware_control(self, control: float) -> None:
        """Write control to hardware actuators."""
        if self.hardware_interface and hasattr(self.hardware_interface, 'write_actuators'):
            self.hardware_interface.write_actuators(control)
        else:
            raise RuntimeError("Hardware interface not available or missing write_actuators method")

    def execute_hil(self,
                   controller: Any,
                   horizon: int,
                   dt: float,
                   **kwargs) -> ResultContainer:
        """Execute hardware-in-the-loop simulation.

        Parameters
        ----------
        controller : Any
            Controller object
        horizon : int
            Number of simulation steps
        dt : float
            Time step
        **kwargs
            Additional options

        Returns
        -------
        ResultContainer
            HIL simulation results
        """
        if self.hardware_interface is None:
            raise RuntimeError("Hardware interface required for HIL simulation")

        # Read initial state from hardware
        initial_state = self._read_hardware_state()

        # Create dummy control inputs (not used in HIL mode)
        control_inputs = np.zeros(horizon)

        # Execute real-time simulation with hardware integration
        result = self.execute(
            initial_state, control_inputs, dt, horizon,
            controller=controller,
            hardware_mode=True,
            **kwargs
        )

        return result