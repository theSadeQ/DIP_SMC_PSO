#==========================================================================================\\\
#=============== src/optimization/objectives/system/settling_time.py ==================\\\
#==========================================================================================\\\

"""Settling time objective functions for control optimization."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union, Callable, Tuple
import numpy as np

from ..base import SimulationBasedObjective


class SettlingTimeObjective(SimulationBasedObjective):
    """Objective function for minimizing system settling time.

    This objective computes settling time based on various criteria:
    - 2% settling time (default)
    - 5% settling time
    - Custom settling tolerance
    - Weighted settling time for multiple outputs
    """

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 settling_tolerance: float = 0.02,
                 settling_metric: str = 'percentage',
                 output_weights: Optional[np.ndarray] = None,
                 output_indices: Optional[Union[int, list]] = None,
                 min_settled_duration: float = 0.1,
                 reference_trajectory: Optional[np.ndarray] = None):
        """Initialize settling time objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration parameters
        controller_factory : callable
            Function to create controller from parameters
        settling_tolerance : float, default=0.02
            Settling tolerance (0.02 = 2%, 0.05 = 5%)
        settling_metric : str, default='percentage'
            Settling metric: 'percentage', 'absolute', 'adaptive'
        output_weights : np.ndarray, optional
            Weights for different outputs (states)
        output_indices : int or list, optional
            Which state indices to consider (default: all)
        min_settled_duration : float, default=0.1
            Minimum duration system must stay settled [seconds]
        reference_trajectory : np.ndarray, optional
            Reference trajectory (default: final steady-state value)
        """
        super().__init__(simulation_config, controller_factory, reference_trajectory)

        self.settling_tolerance = settling_tolerance
        self.settling_metric = settling_metric.lower()
        self.output_weights = output_weights
        self.output_indices = output_indices
        self.min_settled_duration = min_settled_duration

        # Validate settling metric
        valid_metrics = ['percentage', 'absolute', 'adaptive']
        if self.settling_metric not in valid_metrics:
            raise ValueError(f"settling_metric must be one of {valid_metrics}")

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute settling time objective from simulation results.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        states : np.ndarray
            State trajectory [N_steps x N_states]
        controls : np.ndarray
            Control trajectory [N_steps]

        Returns
        -------
        float
            Settling time objective (lower is better)
        """
        # Determine which outputs to analyze
        if self.output_indices is not None:
            if isinstance(self.output_indices, int):
                output_indices = [self.output_indices]
            else:
                output_indices = list(self.output_indices)
        else:
            # Default: analyze position states (cart position and pendulum angles)
            output_indices = list(range(min(3, states.shape[1])))

        # Compute settling time for each output
        settling_times = []
        output_weights = self.output_weights

        if output_weights is None:
            output_weights = np.ones(len(output_indices)) / len(output_indices)
        elif len(output_weights) != len(output_indices):
            # Adjust weights to match number of outputs
            output_weights = np.ones(len(output_indices)) / len(output_indices)

        for i, output_idx in enumerate(output_indices):
            if output_idx < states.shape[1]:
                settling_time = self._compute_single_output_settling_time(
                    times, states[:, output_idx]
                )
                settling_times.append(settling_time)
            else:
                # Invalid output index
                settling_times.append(times[-1])  # Use full simulation time as penalty

        # Weighted combination of settling times
        if settling_times:
            weighted_settling_time = np.average(settling_times, weights=output_weights)
        else:
            weighted_settling_time = times[-1]  # Full simulation time if no valid outputs

        return weighted_settling_time

    def _compute_single_output_settling_time(self,
                                           times: np.ndarray,
                                           output: np.ndarray) -> float:
        """Compute settling time for a single output signal.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        output : np.ndarray
            Output signal

        Returns
        -------
        float
            Settling time for this output
        """
        if len(output) < 2:
            return times[-1] if len(times) > 0 else 0.0

        # Determine reference value (steady-state)
        if self.reference_trajectory is not None and len(self.reference_trajectory) == len(output):
            reference_values = self.reference_trajectory
        else:
            # Use final value as steady-state reference
            steady_state_samples = max(1, int(len(output) * 0.05))  # Last 5%
            steady_state_value = np.mean(output[-steady_state_samples:])
            reference_values = np.full_like(output, steady_state_value)

        # Compute settling tolerance band
        tolerance_bands = self._compute_tolerance_band(output, reference_values)

        # Find settling time
        settling_time = self._find_settling_time(times, output, reference_values, tolerance_bands)

        return settling_time

    def _compute_tolerance_band(self,
                              output: np.ndarray,
                              reference_values: np.ndarray) -> np.ndarray:
        """Compute settling tolerance band for the output signal.

        Parameters
        ----------
        output : np.ndarray
            Output signal
        reference_values : np.ndarray
            Reference values (same length as output)

        Returns
        -------
        np.ndarray
            Tolerance band values
        """
        if self.settling_metric == 'percentage':
            # Percentage-based tolerance (e.g., 2% of steady-state value)
            steady_state_value = reference_values[0] if len(reference_values) > 0 else np.mean(output[-10:])

            if abs(steady_state_value) > 1e-6:
                tolerance_band = abs(steady_state_value) * self.settling_tolerance
            else:
                # If steady-state is near zero, use absolute tolerance based on signal range
                signal_range = np.max(output) - np.min(output)
                tolerance_band = max(signal_range * self.settling_tolerance, 1e-6)

            tolerance_bands = np.full_like(reference_values, tolerance_band)

        elif self.settling_metric == 'absolute':
            # Absolute tolerance
            tolerance_bands = np.full_like(reference_values, self.settling_tolerance)

        elif self.settling_metric == 'adaptive':
            # Adaptive tolerance based on signal characteristics
            signal_range = np.max(output) - np.min(output)
            base_tolerance = max(signal_range * self.settling_tolerance, 1e-6)

            # Adapt based on local signal behavior
            tolerance_bands = np.full_like(reference_values, base_tolerance)

            # Increase tolerance in regions with high variability
            if len(output) > 10:
                window_size = min(10, len(output) // 10)
                for i in range(len(output)):
                    start_idx = max(0, i - window_size // 2)
                    end_idx = min(len(output), i + window_size // 2)
                    local_std = np.std(output[start_idx:end_idx])
                    tolerance_bands[i] = max(tolerance_bands[i], local_std * self.settling_tolerance)

        else:
            # Default to percentage
            tolerance_bands = np.full_like(reference_values, abs(reference_values[0]) * self.settling_tolerance)

        return tolerance_bands

    def _find_settling_time(self,
                          times: np.ndarray,
                          output: np.ndarray,
                          reference_values: np.ndarray,
                          tolerance_bands: np.ndarray) -> float:
        """Find the settling time based on tolerance criteria.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        output : np.ndarray
            Output signal
        reference_values : np.ndarray
            Reference values
        tolerance_bands : np.ndarray
            Tolerance band values

        Returns
        -------
        float
            Settling time
        """
        # Check which points are within settling tolerance
        errors = np.abs(output - reference_values)
        within_tolerance = errors <= tolerance_bands

        # Find settling time requiring sustained settlement
        if self.min_settled_duration > 0 and len(times) > 1:
            dt = times[1] - times[0]
            min_settled_points = max(1, int(self.min_settled_duration / dt))

            # Look for sustained settlement
            for i in range(len(within_tolerance) - min_settled_points):
                if np.all(within_tolerance[i:i + min_settled_points]):
                    return times[i]

            # If never sustained, return full simulation time
            return times[-1]

        else:
            # Simple settling time (first time within tolerance)
            settling_indices = np.where(within_tolerance)[0]
            if len(settling_indices) > 0:
                return times[settling_indices[0]]
            else:
                return times[-1]

    def compute_detailed_settling_analysis(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray) -> Dict[str, Any]:
        """Compute detailed settling time analysis for all outputs.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        states : np.ndarray
            State trajectory
        controls : np.ndarray
            Control trajectory

        Returns
        -------
        dict
            Detailed settling analysis results
        """
        analysis = {}

        # Determine outputs to analyze
        if self.output_indices is not None:
            if isinstance(self.output_indices, int):
                output_indices = [self.output_indices]
            else:
                output_indices = list(self.output_indices)
        else:
            output_indices = list(range(min(3, states.shape[1])))

        output_names = ['cart_position', 'pendulum1_angle', 'pendulum2_angle']

        # Analyze each output
        for i, output_idx in enumerate(output_indices):
            if output_idx < states.shape[1]:
                output_name = output_names[output_idx] if output_idx < len(output_names) else f'output_{output_idx}'

                # Compute settling time
                settling_time = self._compute_single_output_settling_time(times, states[:, output_idx])

                # Compute additional metrics
                output_signal = states[:, output_idx]
                steady_state_value = np.mean(output_signal[-max(1, int(len(output_signal) * 0.05)):])

                # Peak deviation
                peak_deviation = np.max(np.abs(output_signal - steady_state_value))

                # Oscillation characteristics
                zero_crossings = self._count_zero_crossings(output_signal - steady_state_value)

                # Store results
                analysis[f'{output_name}_settling_time'] = settling_time
                analysis[f'{output_name}_steady_state'] = steady_state_value
                analysis[f'{output_name}_peak_deviation'] = peak_deviation
                analysis[f'{output_name}_oscillations'] = zero_crossings

        # Overall settling time
        analysis['overall_settling_time'] = self._compute_objective_from_simulation(times, states, controls)

        # Control effort during settling
        if len(controls) > 0:
            control_energy = np.trapz(controls.flatten()**2, times)
            analysis['control_energy'] = control_energy

        return analysis

    def _count_zero_crossings(self, signal: np.ndarray) -> int:
        """Count zero crossings in a signal (indicator of oscillations)."""
        if len(signal) < 2:
            return 0

        # Find sign changes
        signs = np.sign(signal)
        sign_changes = np.diff(signs) != 0
        return np.sum(sign_changes)

    def get_settling_criteria(self) -> Dict[str, Any]:
        """Get the settling criteria used by this objective.

        Returns
        -------
        dict
            Dictionary describing settling criteria
        """
        return {
            'settling_tolerance': self.settling_tolerance,
            'settling_metric': self.settling_metric,
            'min_settled_duration': self.min_settled_duration,
            'output_indices': self.output_indices,
            'output_weights': self.output_weights.tolist() if self.output_weights is not None else None
        }


class RiseTimeObjective(SettlingTimeObjective):
    """Objective function for minimizing rise time (10%-90% rise time).

    Rise time is the time required for the system response to rise from
    10% to 90% of its final steady-state value.
    """

    def __init__(self, *args, **kwargs):
        """Initialize rise time objective."""
        super().__init__(*args, **kwargs)

    def _compute_single_output_settling_time(self,
                                           times: np.ndarray,
                                           output: np.ndarray) -> float:
        """Compute rise time (10%-90%) instead of settling time."""
        if len(output) < 2:
            return times[-1] if len(times) > 0 else 0.0

        # Determine steady-state value
        steady_state_samples = max(1, int(len(output) * 0.05))
        steady_state_value = np.mean(output[-steady_state_samples:])
        initial_value = output[0]

        # 10% and 90% levels
        response_range = steady_state_value - initial_value
        ten_percent_level = initial_value + 0.1 * response_range
        ninety_percent_level = initial_value + 0.9 * response_range

        # Find rise time
        ten_percent_time = None
        ninety_percent_time = None

        for i, value in enumerate(output):
            if ten_percent_time is None and value >= ten_percent_level:
                ten_percent_time = times[i]
            if ninety_percent_time is None and value >= ninety_percent_level:
                ninety_percent_time = times[i]
                break

        if ten_percent_time is not None and ninety_percent_time is not None:
            return ninety_percent_time - ten_percent_time
        else:
            return times[-1]  # Use full simulation time if rise time not found