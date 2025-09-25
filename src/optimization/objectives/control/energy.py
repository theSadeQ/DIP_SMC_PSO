#==========================================================================================\\\
#================= src/optimization/objectives/control/energy.py ======================\\\
#==========================================================================================\\\

"""Energy consumption objective functions for control optimization."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union, Callable
import numpy as np

from ..base import SimulationBasedObjective


class EnergyConsumptionObjective(SimulationBasedObjective):
    """Objective function for minimizing control energy consumption.

    This objective computes various energy consumption metrics to optimize
    control efficiency while maintaining performance requirements.

    Energy metrics include:
    - Total energy: ∫ u²(t) dt
    - RMS control effort: √(∫ u²(t) dt / T)
    - Peak control effort: max|u(t)|
    - Weighted energy with control rate penalty
    """

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 energy_metric: str = 'total',
                 control_rate_weight: float = 0.0,
                 control_penalty_weight: float = 1.0,
                 max_control_threshold: Optional[float] = None,
                 reference_trajectory: Optional[np.ndarray] = None):
        """Initialize energy consumption objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration parameters
        controller_factory : callable
            Function to create controller from parameters
        energy_metric : str, default='total'
            Energy metric type: 'total', 'rms', 'peak', 'weighted'
        control_rate_weight : float, default=0.0
            Weight for control rate penalty (du/dt)²
        control_penalty_weight : float, default=1.0
            Weight for control effort penalty
        max_control_threshold : float, optional
            Maximum allowable control effort (penalty if exceeded)
        reference_trajectory : np.ndarray, optional
            Reference trajectory if needed for weighted energy
        """
        super().__init__(simulation_config, controller_factory, reference_trajectory)

        self.energy_metric = energy_metric.lower()
        self.control_rate_weight = control_rate_weight
        self.control_penalty_weight = control_penalty_weight
        self.max_control_threshold = max_control_threshold

        # Validate energy metric
        valid_metrics = ['total', 'rms', 'peak', 'weighted']
        if self.energy_metric not in valid_metrics:
            raise ValueError(f"energy_metric must be one of {valid_metrics}")

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute energy consumption objective from simulation results.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        states : np.ndarray
            State trajectory [N_steps x N_states]
        controls : np.ndarray
            Control trajectory [N_steps] or [N_steps x N_controls]

        Returns
        -------
        float
            Energy consumption objective value (lower is better)
        """
        # Ensure controls is 1D for DIP system
        if controls.ndim > 1:
            controls = controls.flatten()

        dt = times[1] - times[0] if len(times) > 1 else 0.001
        T = times[-1] - times[0]

        # Compute base energy metrics
        if self.energy_metric == 'total':
            # Total energy: ∫ u²(t) dt
            energy = np.trapz(controls**2, times)

        elif self.energy_metric == 'rms':
            # RMS control effort: √(∫ u²(t) dt / T)
            total_energy = np.trapz(controls**2, times)
            energy = np.sqrt(total_energy / T)

        elif self.energy_metric == 'peak':
            # Peak control effort: max|u(t)|
            energy = np.max(np.abs(controls))

        elif self.energy_metric == 'weighted':
            # Weighted energy with multiple components
            total_energy = np.trapz(controls**2, times)

            # Add control rate penalty if specified
            if self.control_rate_weight > 0:
                control_rates = np.gradient(controls, dt)
                rate_penalty = self.control_rate_weight * np.trapz(control_rates**2, times)
                total_energy += rate_penalty

            energy = total_energy

        else:
            raise ValueError(f"Unknown energy metric: {self.energy_metric}")

        # Apply control penalty weight
        energy *= self.control_penalty_weight

        # Add penalty for exceeding maximum control threshold
        if self.max_control_threshold is not None:
            max_control = np.max(np.abs(controls))
            if max_control > self.max_control_threshold:
                # Exponential penalty for exceeding threshold
                excess_penalty = 100.0 * (max_control / self.max_control_threshold - 1.0)**2
                energy += excess_penalty

        return energy

    def get_energy_breakdown(self,
                           times: np.ndarray,
                           controls: np.ndarray) -> Dict[str, float]:
        """Get detailed breakdown of energy components.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        controls : np.ndarray
            Control trajectory

        Returns
        -------
        dict
            Dictionary with energy breakdown components
        """
        if controls.ndim > 1:
            controls = controls.flatten()

        dt = times[1] - times[0] if len(times) > 1 else 0.001
        T = times[-1] - times[0]

        breakdown = {}

        # Total energy
        total_energy = np.trapz(controls**2, times)
        breakdown['total_energy'] = total_energy
        breakdown['rms_energy'] = np.sqrt(total_energy / T)
        breakdown['peak_control'] = np.max(np.abs(controls))
        breakdown['mean_abs_control'] = np.mean(np.abs(controls))

        # Control rate components
        if len(controls) > 1:
            control_rates = np.gradient(controls, dt)
            breakdown['control_rate_energy'] = np.trapz(control_rates**2, times)
            breakdown['peak_control_rate'] = np.max(np.abs(control_rates))

        # Threshold violations
        if self.max_control_threshold is not None:
            violations = np.sum(np.abs(controls) > self.max_control_threshold)
            breakdown['threshold_violations'] = violations
            breakdown['violation_percentage'] = violations / len(controls) * 100

        return breakdown

    def evaluate_energy_efficiency(self,
                                 times: np.ndarray,
                                 states: np.ndarray,
                                 controls: np.ndarray,
                                 tracking_error: Optional[float] = None) -> float:
        """Evaluate energy efficiency considering performance trade-offs.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        states : np.ndarray
            State trajectory
        controls : np.ndarray
            Control trajectory
        tracking_error : float, optional
            Tracking error for efficiency computation

        Returns
        -------
        float
            Energy efficiency metric (higher is better)
        """
        energy = self._compute_objective_from_simulation(times, states, controls)

        if tracking_error is not None and tracking_error > 0:
            # Energy efficiency as performance per unit energy
            efficiency = 1.0 / (tracking_error * energy + 1e-12)
        else:
            # Pure energy efficiency (inverse of energy)
            efficiency = 1.0 / (energy + 1e-12)

        return efficiency


class ControlEffortObjective(EnergyConsumptionObjective):
    """Specialized objective for minimizing control effort with saturation handling.

    This is a specialized version of EnergyConsumptionObjective that includes
    specific handling for control saturation and actuator limitations.
    """

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 max_control_force: float = 150.0,
                 saturation_penalty: float = 10.0,
                 smoothness_weight: float = 1.0,
                 **kwargs):
        """Initialize control effort objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration
        controller_factory : callable
            Controller factory function
        max_control_force : float, default=150.0
            Maximum allowable control force [N]
        saturation_penalty : float, default=10.0
            Penalty weight for control saturation
        smoothness_weight : float, default=1.0
            Weight for control smoothness (du/dt)²
        **kwargs
            Additional arguments passed to EnergyConsumptionObjective
        """
        # Set up energy objective with smoothness penalty
        kwargs.setdefault('energy_metric', 'weighted')
        kwargs.setdefault('control_rate_weight', smoothness_weight)
        kwargs.setdefault('max_control_threshold', max_control_force)

        super().__init__(simulation_config, controller_factory, **kwargs)

        self.max_control_force = max_control_force
        self.saturation_penalty = saturation_penalty

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute control effort objective with saturation penalties."""
        # Get base energy consumption
        base_energy = super()._compute_objective_from_simulation(times, states, controls, **kwargs)

        # Add saturation penalties
        if controls.ndim > 1:
            controls = controls.flatten()

        # Count saturation instances
        saturated_controls = np.abs(controls) >= self.max_control_force * 0.95  # Near saturation
        saturation_fraction = np.mean(saturated_controls)

        # Add penalty for excessive saturation
        if saturation_fraction > 0.1:  # More than 10% saturation
            saturation_penalty = self.saturation_penalty * (saturation_fraction - 0.1)**2
            base_energy += saturation_penalty

        return base_energy