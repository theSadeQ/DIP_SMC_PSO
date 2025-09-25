#==========================================================================================\\\
#================= src/optimization/objectives/control/tracking.py ====================\\\
#==========================================================================================\\\

"""Tracking performance objective functions for control optimization."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union, Callable
import numpy as np

from ..base import SimulationBasedObjective


class TrackingErrorObjective(SimulationBasedObjective):
    """Objective function for minimizing tracking error.

    This objective computes various tracking error metrics including
    ISE (Integral Square Error), IAE (Integral Absolute Error),
    and ITAE (Integral Time Absolute Error).
    """

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 reference_trajectory: np.ndarray,
                 error_metric: str = 'ise',
                 state_weights: Optional[np.ndarray] = None,
                 output_indices: Optional[Union[int, list]] = None):
        """Initialize tracking error objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration
        controller_factory : callable
            Function to create controller from parameters
        reference_trajectory : np.ndarray
            Reference trajectory to track (time_steps x n_outputs)
        error_metric : str, optional
            Error metric ('ise', 'iae', 'itae', 'mse', 'mae')
        state_weights : np.ndarray, optional
            Weights for different state variables
        output_indices : int or list, optional
            Indices of states to consider as outputs (default: all states)
        """
        super().__init__(simulation_config, controller_factory, reference_trajectory)

        self.error_metric = error_metric.lower()
        self.state_weights = state_weights
        self.output_indices = output_indices

        # Validate error metric
        valid_metrics = {'ise', 'iae', 'itae', 'mse', 'mae', 'rmse'}
        if self.error_metric not in valid_metrics:
            raise ValueError(f"Error metric must be one of {valid_metrics}")

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute tracking error from simulation results."""
        # Extract outputs
        if self.output_indices is None:
            outputs = states
            reference = self.reference_trajectory
        else:
            if isinstance(self.output_indices, int):
                outputs = states[:, [self.output_indices]]
                reference = self.reference_trajectory[:, [self.output_indices]]
            else:
                outputs = states[:, self.output_indices]
                reference = self.reference_trajectory[:, self.output_indices]

        # Ensure compatible dimensions
        min_length = min(len(outputs), len(reference))
        outputs = outputs[:min_length]
        reference = reference[:min_length]
        dt = times[1] - times[0] if len(times) > 1 else 0.01

        # Compute tracking error
        error = outputs - reference

        # Apply state weights if provided
        if self.state_weights is not None:
            error = error * self.state_weights

        # Compute error metric
        return self._compute_error_metric(error, times[:min_length], dt)

    def _compute_error_metric(self, error: np.ndarray, times: np.ndarray, dt: float) -> float:
        """Compute specific error metric."""
        if self.error_metric == 'ise':
            # Integral Square Error
            return float(np.trapz(np.sum(error**2, axis=1), dx=dt))

        elif self.error_metric == 'iae':
            # Integral Absolute Error
            return float(np.trapz(np.sum(np.abs(error), axis=1), dx=dt))

        elif self.error_metric == 'itae':
            # Integral Time Absolute Error
            return float(np.trapz(times * np.sum(np.abs(error), axis=1), dx=dt))

        elif self.error_metric == 'mse':
            # Mean Square Error
            return float(np.mean(np.sum(error**2, axis=1)))

        elif self.error_metric == 'mae':
            # Mean Absolute Error
            return float(np.mean(np.sum(np.abs(error), axis=1)))

        elif self.error_metric == 'rmse':
            # Root Mean Square Error
            return float(np.sqrt(np.mean(np.sum(error**2, axis=1))))

        else:
            raise ValueError(f"Unknown error metric: {self.error_metric}")


class StepResponseObjective(SimulationBasedObjective):
    """Objective for step response characteristics."""

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 step_amplitude: float = 1.0,
                 output_index: int = 0,
                 target_settling_time: Optional[float] = None,
                 target_overshoot: Optional[float] = None):
        """Initialize step response objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration
        controller_factory : callable
            Controller factory function
        step_amplitude : float, optional
            Step input amplitude
        output_index : int, optional
            Index of output to analyze
        target_settling_time : float, optional
            Target settling time for penalty
        target_overshoot : float, optional
            Target maximum overshoot for penalty
        """
        super().__init__(simulation_config, controller_factory)

        self.step_amplitude = step_amplitude
        self.output_index = output_index
        self.target_settling_time = target_settling_time
        self.target_overshoot = target_overshoot

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute step response objective."""
        output = states[:, self.output_index]

        # Compute step response characteristics
        settling_time = self._compute_settling_time(times, output)
        overshoot = self._compute_overshoot(output)
        steady_state_error = self._compute_steady_state_error(output)

        # Combine metrics
        objective = 0.0

        # Settling time penalty
        if self.target_settling_time is not None:
            if settling_time > self.target_settling_time:
                objective += 10 * (settling_time - self.target_settling_time)**2

        # Overshoot penalty
        if self.target_overshoot is not None:
            if overshoot > self.target_overshoot:
                objective += 100 * (overshoot - self.target_overshoot)**2

        # Steady-state error
        objective += 10 * steady_state_error**2

        # Base performance metric
        objective += settling_time + overshoot + abs(steady_state_error)

        return objective

    def _compute_settling_time(self, times: np.ndarray, output: np.ndarray, tolerance: float = 0.02) -> float:
        """Compute settling time (2% criterion)."""
        final_value = output[-1]
        tolerance_band = tolerance * abs(final_value)

        # Find last time outside tolerance band
        outside_band = np.abs(output - final_value) > tolerance_band
        if not np.any(outside_band):
            return 0.0

        last_outside_index = np.where(outside_band)[0][-1]
        return times[last_outside_index]

    def _compute_overshoot(self, output: np.ndarray) -> float:
        """Compute maximum overshoot percentage."""
        final_value = output[-1]
        if final_value == 0:
            return 0.0

        max_value = np.max(output)
        overshoot = (max_value - final_value) / abs(final_value) * 100
        return max(0.0, overshoot)

    def _compute_steady_state_error(self, output: np.ndarray) -> float:
        """Compute steady-state error."""
        final_value = output[-1]
        desired_value = self.step_amplitude
        return abs(desired_value - final_value)


class FrequencyResponseObjective(SimulationBasedObjective):
    """Objective based on frequency response characteristics."""

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 frequency_range: np.ndarray,
                 desired_bandwidth: Optional[float] = None,
                 desired_phase_margin: Optional[float] = None,
                 desired_gain_margin: Optional[float] = None):
        """Initialize frequency response objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration
        controller_factory : callable
            Controller factory function
        frequency_range : np.ndarray
            Frequency range for analysis
        desired_bandwidth : float, optional
            Desired closed-loop bandwidth
        desired_phase_margin : float, optional
            Desired phase margin (degrees)
        desired_gain_margin : float, optional
            Desired gain margin (dB)
        """
        super().__init__(simulation_config, controller_factory)

        self.frequency_range = frequency_range
        self.desired_bandwidth = desired_bandwidth
        self.desired_phase_margin = desired_phase_margin
        self.desired_gain_margin = desired_gain_margin

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute frequency response objective."""
        # This would require system identification or analytical computation
        # For now, return a placeholder based on time-domain characteristics

        # Estimate bandwidth from step response
        dt = times[1] - times[0] if len(times) > 1 else 0.01
        estimated_bandwidth = self._estimate_bandwidth_from_time_domain(states, dt)

        objective = 0.0

        # Bandwidth penalty
        if self.desired_bandwidth is not None:
            bandwidth_error = abs(estimated_bandwidth - self.desired_bandwidth)
            objective += bandwidth_error**2

        return objective

    def _estimate_bandwidth_from_time_domain(self, states: np.ndarray, dt: float) -> float:
        """Estimate bandwidth from time-domain response."""
        # Simple estimation based on rise time
        # Bandwidth ≈ 0.35 / rise_time (for first-order systems)

        output = states[:, 0]  # Assume first state is output
        final_value = output[-1]

        # Find 10% and 90% of final value
        ten_percent = 0.1 * final_value
        ninety_percent = 0.9 * final_value

        # Find indices
        try:
            idx_10 = np.where(output >= ten_percent)[0][0]
            idx_90 = np.where(output >= ninety_percent)[0][0]

            rise_time = (idx_90 - idx_10) * dt
            bandwidth = 0.35 / max(rise_time, 0.001)  # Avoid division by zero
        except IndexError:
            bandwidth = 1.0  # Default value

        return bandwidth