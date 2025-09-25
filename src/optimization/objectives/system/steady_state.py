#==========================================================================================\\\
#=============== src/optimization/objectives/system/steady_state.py ===================\\\
#==========================================================================================\\\

"""Steady-state error objective functions for control optimization."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union, Callable, Tuple
import numpy as np

from ..base import SimulationBasedObjective


class SteadyStateErrorObjective(SimulationBasedObjective):
    """Objective function for minimizing steady-state tracking error.

    This objective computes various steady-state error metrics:
    - Absolute steady-state error
    - Percentage steady-state error
    - RMS steady-state error
    - Weighted error for multiple outputs
    """

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 error_metric: str = 'absolute',
                 steady_state_window: float = 0.1,
                 output_weights: Optional[np.ndarray] = None,
                 output_indices: Optional[Union[int, list]] = None,
                 reference_trajectory: Optional[np.ndarray] = None):
        """Initialize steady-state error objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration parameters
        controller_factory : callable
            Function to create controller from parameters
        error_metric : str, default='absolute'
            Error metric: 'absolute', 'percentage', 'rms', 'normalized'
        steady_state_window : float, default=0.1
            Fraction of simulation time to consider as steady-state (0.1 = last 10%)
        output_weights : np.ndarray, optional
            Weights for different outputs (states)
        output_indices : int or list, optional
            Which state indices to consider (default: positions only)
        reference_trajectory : np.ndarray, optional
            Reference trajectory for tracking (default: zero reference)
        """
        super().__init__(simulation_config, controller_factory, reference_trajectory)

        self.error_metric = error_metric.lower()
        self.steady_state_window = steady_state_window
        self.output_weights = output_weights
        self.output_indices = output_indices

        # Validate error metric
        valid_metrics = ['absolute', 'percentage', 'rms', 'normalized', 'ise', 'iae']
        if self.error_metric not in valid_metrics:
            raise ValueError(f"error_metric must be one of {valid_metrics}")

        # Validate steady-state window
        if not 0.0 < steady_state_window <= 1.0:
            raise ValueError("steady_state_window must be between 0 and 1")

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute steady-state error objective from simulation results.

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
            Steady-state error objective (lower is better)
        """
        # Determine which outputs to analyze
        if self.output_indices is not None:
            if isinstance(self.output_indices, int):
                output_indices = [self.output_indices]
            else:
                output_indices = list(self.output_indices)
        else:
            # Default: analyze position states only (cart position and pendulum angles)
            output_indices = list(range(min(3, states.shape[1])))

        # Get reference trajectory
        reference_values = self._get_reference_values(times, states.shape[1])

        # Compute steady-state error for each output
        ss_errors = []
        output_weights = self.output_weights

        if output_weights is None:
            output_weights = np.ones(len(output_indices)) / len(output_indices)
        elif len(output_weights) != len(output_indices):
            output_weights = np.ones(len(output_indices)) / len(output_indices)

        for i, output_idx in enumerate(output_indices):
            if output_idx < states.shape[1]:
                ss_error = self._compute_single_output_steady_state_error(
                    times, states[:, output_idx], reference_values[:, output_idx]
                )
                ss_errors.append(ss_error)
            else:
                # Invalid output index - high penalty
                ss_errors.append(1000.0)

        # Weighted combination of steady-state errors
        if ss_errors:
            weighted_ss_error = np.average(ss_errors, weights=output_weights)
        else:
            weighted_ss_error = 0.0

        return weighted_ss_error

    def _compute_single_output_steady_state_error(self,
                                                times: np.ndarray,
                                                output: np.ndarray,
                                                reference: np.ndarray) -> float:
        """Compute steady-state error for a single output.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        output : np.ndarray
            Output signal
        reference : np.ndarray
            Reference signal

        Returns
        -------
        float
            Steady-state error for this output
        """
        if len(output) < 2:
            return 0.0

        # Determine steady-state region
        steady_state_start_idx = max(0, int(len(output) * (1.0 - self.steady_state_window)))

        steady_state_output = output[steady_state_start_idx:]
        steady_state_reference = reference[steady_state_start_idx:]
        steady_state_times = times[steady_state_start_idx:]

        # Compute error
        error = steady_state_output - steady_state_reference

        # Compute error metric
        if self.error_metric == 'absolute':
            # Mean absolute error
            ss_error = np.mean(np.abs(error))

        elif self.error_metric == 'percentage':
            # Percentage error relative to reference
            reference_magnitude = np.mean(np.abs(steady_state_reference))
            if reference_magnitude > 1e-6:
                ss_error = np.mean(np.abs(error)) / reference_magnitude * 100
            else:
                # If reference is near zero, use absolute error
                ss_error = np.mean(np.abs(error))

        elif self.error_metric == 'rms':
            # Root mean square error
            ss_error = np.sqrt(np.mean(error**2))

        elif self.error_metric == 'normalized':
            # Normalized by output range
            output_range = np.max(output) - np.min(output)
            if output_range > 1e-6:
                ss_error = np.mean(np.abs(error)) / output_range
            else:
                ss_error = np.mean(np.abs(error))

        elif self.error_metric == 'ise':
            # Integral Square Error in steady-state
            dt = steady_state_times[1] - steady_state_times[0] if len(steady_state_times) > 1 else 1.0
            ss_error = np.trapz(error**2, dx=dt)

        elif self.error_metric == 'iae':
            # Integral Absolute Error in steady-state
            dt = steady_state_times[1] - steady_state_times[0] if len(steady_state_times) > 1 else 1.0
            ss_error = np.trapz(np.abs(error), dx=dt)

        else:
            # Default to absolute
            ss_error = np.mean(np.abs(error))

        return ss_error

    def _get_reference_values(self, times: np.ndarray, n_states: int) -> np.ndarray:
        """Get reference trajectory for all states.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        n_states : int
            Number of states

        Returns
        -------
        np.ndarray
            Reference trajectory [N_times x N_states]
        """
        if self.reference_trajectory is not None:
            if self.reference_trajectory.shape[0] == len(times):
                # Reference trajectory has correct time dimension
                if len(self.reference_trajectory.shape) == 1:
                    # 1D reference - apply to first state only
                    ref_values = np.zeros((len(times), n_states))
                    ref_values[:, 0] = self.reference_trajectory
                elif self.reference_trajectory.shape[1] == n_states:
                    # Full state reference
                    ref_values = self.reference_trajectory
                else:
                    # Partial state reference - pad with zeros
                    ref_values = np.zeros((len(times), n_states))
                    n_ref_states = min(self.reference_trajectory.shape[1], n_states)
                    ref_values[:, :n_ref_states] = self.reference_trajectory[:, :n_ref_states]
            else:
                # Reference has wrong time dimension - use constant reference
                if len(self.reference_trajectory.shape) == 1:
                    if len(self.reference_trajectory) == n_states:
                        # Constant reference for all states
                        ref_values = np.tile(self.reference_trajectory, (len(times), 1))
                    else:
                        # Use first element as reference for first state
                        ref_values = np.zeros((len(times), n_states))
                        ref_values[:, 0] = self.reference_trajectory[0]
                else:
                    # Use first row as constant reference
                    ref_values = np.tile(self.reference_trajectory[0], (len(times), 1))
        else:
            # Default: zero reference
            ref_values = np.zeros((len(times), n_states))

        return ref_values

    def compute_detailed_steady_state_analysis(self,
                                             times: np.ndarray,
                                             states: np.ndarray,
                                             controls: np.ndarray) -> Dict[str, Any]:
        """Compute detailed steady-state analysis for all outputs.

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
            Detailed steady-state analysis results
        """
        analysis = {}

        # Get reference values
        reference_values = self._get_reference_values(times, states.shape[1])

        # Determine steady-state region
        steady_state_start_idx = max(0, int(len(states) * (1.0 - self.steady_state_window)))
        steady_state_start_time = times[steady_state_start_idx]

        analysis['steady_state_window'] = self.steady_state_window
        analysis['steady_state_start_time'] = steady_state_start_time
        analysis['steady_state_duration'] = times[-1] - steady_state_start_time

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

                # Get signals
                output_signal = states[:, output_idx]
                reference_signal = reference_values[:, output_idx]

                # Steady-state values
                ss_output = output_signal[steady_state_start_idx:]
                ss_reference = reference_signal[steady_state_start_idx:]
                ss_error = ss_output - ss_reference

                # Compute various error metrics
                mean_ss_output = np.mean(ss_output)
                mean_ss_reference = np.mean(ss_reference)
                mean_ss_error = np.mean(ss_error)
                abs_ss_error = np.mean(np.abs(ss_error))
                rms_ss_error = np.sqrt(np.mean(ss_error**2))
                max_ss_error = np.max(np.abs(ss_error))
                std_ss_error = np.std(ss_error)

                # Store results
                analysis[f'{output_name}_ss_output_mean'] = mean_ss_output
                analysis[f'{output_name}_ss_reference_mean'] = mean_ss_reference
                analysis[f'{output_name}_ss_error_mean'] = mean_ss_error
                analysis[f'{output_name}_ss_error_abs'] = abs_ss_error
                analysis[f'{output_name}_ss_error_rms'] = rms_ss_error
                analysis[f'{output_name}_ss_error_max'] = max_ss_error
                analysis[f'{output_name}_ss_error_std'] = std_ss_error

                # Percentage error
                if abs(mean_ss_reference) > 1e-6:
                    percent_error = abs_ss_error / abs(mean_ss_reference) * 100
                    analysis[f'{output_name}_ss_error_percent'] = percent_error

                # Steady-state variation (how much the output varies in steady-state)
                ss_variation = np.std(ss_output)
                analysis[f'{output_name}_ss_variation'] = ss_variation

        # Overall steady-state error
        analysis['overall_ss_error'] = self._compute_objective_from_simulation(times, states, controls)

        # Control steady-state analysis
        if len(controls) > 0:
            ss_controls = controls[steady_state_start_idx:] if len(controls.shape) == 1 else controls[steady_state_start_idx:].flatten()

            analysis['control_ss_mean'] = np.mean(ss_controls)
            analysis['control_ss_std'] = np.std(ss_controls)
            analysis['control_ss_max'] = np.max(np.abs(ss_controls))

            # Control effort in steady-state
            if len(times) > steady_state_start_idx:
                ss_times = times[steady_state_start_idx:]
                if len(ss_times) > 1:
                    dt = ss_times[1] - ss_times[0]
                    control_ss_energy = np.trapz(ss_controls**2, dx=dt)
                    analysis['control_ss_energy'] = control_ss_energy

        return analysis

    def get_steady_state_convergence(self,
                                   times: np.ndarray,
                                   output: np.ndarray,
                                   reference: np.ndarray,
                                   tolerance: float = 0.02) -> Dict[str, Any]:
        """Analyze steady-state convergence characteristics.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        output : np.ndarray
            Output signal
        reference : np.ndarray
            Reference signal
        tolerance : float, default=0.02
            Convergence tolerance (2%)

        Returns
        -------
        dict
            Convergence analysis results
        """
        convergence_info = {}

        if len(output) < 2:
            return convergence_info

        # Compute error signal
        error = output - reference
        abs_error = np.abs(error)

        # Determine tolerance band
        final_reference = reference[-1]
        if abs(final_reference) > 1e-6:
            tolerance_value = abs(final_reference) * tolerance
        else:
            signal_range = np.max(output) - np.min(output)
            tolerance_value = signal_range * tolerance

        # Find convergence time (when error stays within tolerance)
        converged = abs_error <= tolerance_value

        # Look for sustained convergence
        min_converged_duration = max(1, int(len(converged) * 0.05))  # At least 5% of simulation
        convergence_time = None

        for i in range(len(converged) - min_converged_duration):
            if np.all(converged[i:i + min_converged_duration]):
                convergence_time = times[i]
                break

        convergence_info['convergence_time'] = convergence_time
        convergence_info['tolerance_value'] = tolerance_value
        convergence_info['final_error'] = abs_error[-1]
        convergence_info['converged'] = convergence_time is not None

        # Convergence rate analysis
        if convergence_time is not None:
            convergence_idx = np.where(times >= convergence_time)[0][0]
            transient_error = abs_error[:convergence_idx + 1]

            if len(transient_error) > 1:
                # Fit exponential decay to estimate convergence rate
                log_error = np.log(transient_error + 1e-12)
                valid_indices = np.isfinite(log_error)

                if np.sum(valid_indices) > 1:
                    coeffs = np.polyfit(times[:convergence_idx + 1][valid_indices],
                                      log_error[valid_indices], 1)
                    convergence_rate = -coeffs[0]  # Decay rate
                    convergence_info['convergence_rate'] = max(0.0, convergence_rate)

        return convergence_info

    def get_error_statistics(self,
                           times: np.ndarray,
                           states: np.ndarray,
                           reference_values: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """Get comprehensive error statistics.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        states : np.ndarray
            State trajectory
        reference_values : np.ndarray, optional
            Reference trajectory

        Returns
        -------
        dict
            Error statistics
        """
        if reference_values is None:
            reference_values = self._get_reference_values(times, states.shape[1])

        stats = {}

        # Global error statistics
        errors = states - reference_values

        stats['mean_absolute_error'] = np.mean(np.abs(errors))
        stats['rms_error'] = np.sqrt(np.mean(errors**2))
        stats['max_absolute_error'] = np.max(np.abs(errors))
        stats['error_variance'] = np.var(errors)

        # Per-output error statistics
        output_names = ['cart_position', 'pendulum1_angle', 'pendulum2_angle']

        for i in range(min(3, states.shape[1])):
            output_name = output_names[i] if i < len(output_names) else f'output_{i}'
            output_error = errors[:, i]

            stats[f'{output_name}_mae'] = np.mean(np.abs(output_error))
            stats[f'{output_name}_rmse'] = np.sqrt(np.mean(output_error**2))
            stats[f'{output_name}_max_error'] = np.max(np.abs(output_error))

        return stats