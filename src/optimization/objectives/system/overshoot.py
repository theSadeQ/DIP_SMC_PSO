#==========================================================================================\\\
#=============== src/optimization/objectives/system/overshoot.py ====================\\\
#==========================================================================================\\\

"""Overshoot objective functions for control optimization."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union, Callable, Tuple
import numpy as np

from ..base import SimulationBasedObjective


class OvershootObjective(SimulationBasedObjective):
    """Objective function for minimizing system overshoot.

    This objective computes various overshoot metrics:
    - Peak overshoot percentage
    - Absolute overshoot
    - Weighted overshoot for multiple outputs
    - Undershoot penalty
    """

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 overshoot_metric: str = 'percentage',
                 output_weights: Optional[np.ndarray] = None,
                 output_indices: Optional[Union[int, list]] = None,
                 undershoot_penalty: float = 1.0,
                 reference_trajectory: Optional[np.ndarray] = None):
        """Initialize overshoot objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration parameters
        controller_factory : callable
            Function to create controller from parameters
        overshoot_metric : str, default='percentage'
            Overshoot metric: 'percentage', 'absolute', 'normalized'
        output_weights : np.ndarray, optional
            Weights for different outputs (states)
        output_indices : int or list, optional
            Which state indices to consider (default: positions only)
        undershoot_penalty : float, default=1.0
            Penalty weight for undershoot relative to overshoot
        reference_trajectory : np.ndarray, optional
            Reference trajectory (default: step response to final value)
        """
        super().__init__(simulation_config, controller_factory, reference_trajectory)

        self.overshoot_metric = overshoot_metric.lower()
        self.output_weights = output_weights
        self.output_indices = output_indices
        self.undershoot_penalty = undershoot_penalty

        # Validate overshoot metric
        valid_metrics = ['percentage', 'absolute', 'normalized']
        if self.overshoot_metric not in valid_metrics:
            raise ValueError(f"overshoot_metric must be one of {valid_metrics}")

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute overshoot objective from simulation results.

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
            Overshoot objective (lower is better)
        """
        # Determine which outputs to analyze
        if self.output_indices is not None:
            if isinstance(self.output_indices, int):
                output_indices = [self.output_indices]
            else:
                output_indices = list(self.output_indices)
        else:
            # Default: analyze position states only (not velocities)
            output_indices = list(range(min(3, states.shape[1])))

        # Compute overshoot for each output
        overshoot_values = []
        output_weights = self.output_weights

        if output_weights is None:
            output_weights = np.ones(len(output_indices)) / len(output_indices)
        elif len(output_weights) != len(output_indices):
            output_weights = np.ones(len(output_indices)) / len(output_indices)

        for i, output_idx in enumerate(output_indices):
            if output_idx < states.shape[1]:
                overshoot = self._compute_single_output_overshoot(
                    times, states[:, output_idx]
                )
                overshoot_values.append(overshoot)
            else:
                # Invalid output index - high penalty
                overshoot_values.append(100.0)

        # Weighted combination of overshoots
        if overshoot_values:
            weighted_overshoot = np.average(overshoot_values, weights=output_weights)
        else:
            weighted_overshoot = 0.0

        return weighted_overshoot

    def _compute_single_output_overshoot(self,
                                       times: np.ndarray,
                                       output: np.ndarray) -> float:
        """Compute overshoot for a single output signal.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        output : np.ndarray
            Output signal

        Returns
        -------
        float
            Overshoot value for this output
        """
        if len(output) < 2:
            return 0.0

        # Determine reference trajectory and step characteristics
        initial_value, final_value = self._determine_step_characteristics(output)

        # Skip if no step change
        step_size = abs(final_value - initial_value)
        if step_size < 1e-6:
            return 0.0

        # Find peak overshoot
        if final_value > initial_value:  # Positive step
            peak_value = np.max(output)
            overshoot_amount = peak_value - final_value
            direction = 1
        else:  # Negative step
            peak_value = np.min(output)
            overshoot_amount = final_value - peak_value
            direction = -1

        # Find undershoot if applicable
        if final_value > initial_value:
            undershoot_value = np.min(output)
            undershoot_amount = initial_value - undershoot_value if undershoot_value < initial_value else 0.0
        else:
            undershoot_value = np.max(output)
            undershoot_amount = undershoot_value - initial_value if undershoot_value > initial_value else 0.0

        # Compute overshoot metric
        if self.overshoot_metric == 'percentage':
            # Percentage overshoot relative to step size
            if step_size > 0:
                overshoot_percent = (overshoot_amount / step_size) * 100
                undershoot_percent = (undershoot_amount / step_size) * 100
            else:
                overshoot_percent = 0.0
                undershoot_percent = 0.0

            # Combined overshoot penalty
            total_overshoot = overshoot_percent + self.undershoot_penalty * undershoot_percent

        elif self.overshoot_metric == 'absolute':
            # Absolute overshoot
            total_overshoot = overshoot_amount + self.undershoot_penalty * undershoot_amount

        elif self.overshoot_metric == 'normalized':
            # Normalized by signal range
            signal_range = np.max(output) - np.min(output)
            if signal_range > 0:
                overshoot_normalized = overshoot_amount / signal_range
                undershoot_normalized = undershoot_amount / signal_range
            else:
                overshoot_normalized = 0.0
                undershoot_normalized = 0.0

            total_overshoot = overshoot_normalized + self.undershoot_penalty * undershoot_normalized

        else:
            total_overshoot = overshoot_amount

        return max(0.0, total_overshoot)

    def _determine_step_characteristics(self, output: np.ndarray) -> Tuple[float, float]:
        """Determine initial and final values for step response analysis.

        Parameters
        ----------
        output : np.ndarray
            Output signal

        Returns
        -------
        tuple
            (initial_value, final_value)
        """
        if self.reference_trajectory is not None and len(self.reference_trajectory) == len(output):
            # Use reference trajectory
            initial_value = self.reference_trajectory[0]
            final_value = self.reference_trajectory[-1]
        else:
            # Estimate from signal
            initial_samples = max(1, int(len(output) * 0.05))  # First 5%
            final_samples = max(1, int(len(output) * 0.05))    # Last 5%

            initial_value = np.mean(output[:initial_samples])
            final_value = np.mean(output[-final_samples:])

        return initial_value, final_value

    def compute_detailed_overshoot_analysis(self,
                                          times: np.ndarray,
                                          states: np.ndarray,
                                          controls: np.ndarray) -> Dict[str, Any]:
        """Compute detailed overshoot analysis for all outputs.

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
            Detailed overshoot analysis results
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
                output_signal = states[:, output_idx]

                # Get step characteristics
                initial_value, final_value = self._determine_step_characteristics(output_signal)
                step_size = abs(final_value - initial_value)

                if step_size > 1e-6:
                    # Compute overshoot metrics
                    if final_value > initial_value:
                        peak_value = np.max(output_signal)
                        peak_time_idx = np.argmax(output_signal)
                        overshoot_amount = peak_value - final_value
                        overshoot_percent = (overshoot_amount / step_size) * 100

                        # Check for undershoot
                        undershoot_value = np.min(output_signal)
                        undershoot_amount = max(0.0, initial_value - undershoot_value)
                        undershoot_percent = (undershoot_amount / step_size) * 100
                    else:
                        peak_value = np.min(output_signal)
                        peak_time_idx = np.argmin(output_signal)
                        overshoot_amount = final_value - peak_value
                        overshoot_percent = (overshoot_amount / step_size) * 100

                        # Check for undershoot
                        undershoot_value = np.max(output_signal)
                        undershoot_amount = max(0.0, undershoot_value - initial_value)
                        undershoot_percent = (undershoot_amount / step_size) * 100

                    peak_time = times[peak_time_idx]

                    # Store detailed metrics
                    analysis[f'{output_name}_initial_value'] = initial_value
                    analysis[f'{output_name}_final_value'] = final_value
                    analysis[f'{output_name}_step_size'] = step_size
                    analysis[f'{output_name}_peak_value'] = peak_value
                    analysis[f'{output_name}_peak_time'] = peak_time
                    analysis[f'{output_name}_overshoot_amount'] = overshoot_amount
                    analysis[f'{output_name}_overshoot_percent'] = overshoot_percent
                    analysis[f'{output_name}_undershoot_amount'] = undershoot_amount
                    analysis[f'{output_name}_undershoot_percent'] = undershoot_percent

                    # Number of oscillations before settling
                    oscillations = self._count_oscillations_before_settling(
                        times, output_signal, initial_value, final_value
                    )
                    analysis[f'{output_name}_oscillations'] = oscillations

                else:
                    # No significant step change
                    analysis[f'{output_name}_overshoot_percent'] = 0.0
                    analysis[f'{output_name}_undershoot_percent'] = 0.0

        # Overall overshoot objective
        analysis['overall_overshoot'] = self._compute_objective_from_simulation(times, states, controls)

        # Control overshoot analysis
        if len(controls) > 1:
            control_signal = controls.flatten()
            control_peak = np.max(np.abs(control_signal))
            control_mean = np.mean(np.abs(control_signal))
            control_overshoot_ratio = control_peak / (control_mean + 1e-6)

            analysis['control_peak'] = control_peak
            analysis['control_mean'] = control_mean
            analysis['control_overshoot_ratio'] = control_overshoot_ratio

        return analysis

    def _count_oscillations_before_settling(self,
                                          times: np.ndarray,
                                          output: np.ndarray,
                                          initial_value: float,
                                          final_value: float) -> int:
        """Count number of oscillations around final value before settling."""
        if len(output) < 3:
            return 0

        # Define oscillation as crossing the final value
        crossings = []
        for i in range(1, len(output)):
            if ((output[i-1] - final_value) * (output[i] - final_value)) < 0:
                crossings.append(i)

        # Each pair of crossings represents one oscillation
        return len(crossings) // 2

    def get_overshoot_characteristics(self,
                                    times: np.ndarray,
                                    output: np.ndarray) -> Dict[str, float]:
        """Get overshoot characteristics for a single output.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        output : np.ndarray
            Output signal

        Returns
        -------
        dict
            Overshoot characteristics
        """
        initial_value, final_value = self._determine_step_characteristics(output)
        step_size = abs(final_value - initial_value)

        characteristics = {
            'initial_value': initial_value,
            'final_value': final_value,
            'step_size': step_size,
        }

        if step_size > 1e-6:
            if final_value > initial_value:
                peak_value = np.max(output)
                peak_idx = np.argmax(output)
            else:
                peak_value = np.min(output)
                peak_idx = np.argmin(output)

            peak_time = times[peak_idx]
            overshoot_amount = abs(peak_value - final_value)
            overshoot_percent = (overshoot_amount / step_size) * 100

            characteristics.update({
                'peak_value': peak_value,
                'peak_time': peak_time,
                'overshoot_amount': overshoot_amount,
                'overshoot_percent': overshoot_percent,
            })
        else:
            characteristics.update({
                'peak_value': final_value,
                'peak_time': times[-1],
                'overshoot_amount': 0.0,
                'overshoot_percent': 0.0,
            })

        return characteristics


class UndershootObjective(OvershootObjective):
    """Objective function specifically for minimizing undershoot.

    This is a specialized version that focuses on undershoot rather than overshoot.
    """

    def __init__(self, *args, **kwargs):
        """Initialize undershoot objective."""
        # Set undershoot penalty to 0 and invert the problem
        kwargs['undershoot_penalty'] = 0.0
        super().__init__(*args, **kwargs)

    def _compute_single_output_overshoot(self,
                                       times: np.ndarray,
                                       output: np.ndarray) -> float:
        """Compute undershoot instead of overshoot."""
        if len(output) < 2:
            return 0.0

        # Get step characteristics
        initial_value, final_value = self._determine_step_characteristics(output)
        step_size = abs(final_value - initial_value)

        if step_size < 1e-6:
            return 0.0

        # Find undershoot (opposite direction from step)
        if final_value > initial_value:
            # For positive step, undershoot is below initial value
            min_value = np.min(output)
            undershoot_amount = max(0.0, initial_value - min_value)
        else:
            # For negative step, undershoot is above initial value
            max_value = np.max(output)
            undershoot_amount = max(0.0, max_value - initial_value)

        # Compute undershoot metric
        if self.overshoot_metric == 'percentage':
            undershoot_percent = (undershoot_amount / step_size) * 100
            return undershoot_percent
        elif self.overshoot_metric == 'absolute':
            return undershoot_amount
        elif self.overshoot_metric == 'normalized':
            signal_range = np.max(output) - np.min(output)
            if signal_range > 0:
                return undershoot_amount / signal_range
            else:
                return 0.0
        else:
            return undershoot_amount