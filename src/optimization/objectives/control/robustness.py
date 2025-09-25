#==========================================================================================\\\
#=============== src/optimization/objectives/control/robustness.py ===================\\\
#==========================================================================================\\\

"""Robustness objective functions for control optimization."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union, Callable, List
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import warnings

from ..base import SimulationBasedObjective


class RobustnessObjective(SimulationBasedObjective):
    """Objective function for optimizing control robustness.

    This objective evaluates controller performance under various
    uncertainties and disturbances including:
    - Parameter variations (mass, length, damping)
    - Measurement noise
    - External disturbances
    - Model uncertainties
    """

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 robustness_metric: str = 'monte_carlo',
                 n_variations: int = 20,
                 parameter_uncertainty: float = 0.1,
                 noise_level: float = 0.01,
                 disturbance_magnitude: float = 0.5,
                 reference_trajectory: Optional[np.ndarray] = None):
        """Initialize robustness objective.

        Parameters
        ----------
        simulation_config : dict
            Base simulation configuration
        controller_factory : callable
            Function to create controller from parameters
        robustness_metric : str, default='monte_carlo'
            Robustness metric: 'monte_carlo', 'worst_case', 'sensitivity', 'h_infinity'
        n_variations : int, default=20
            Number of parameter variations to test
        parameter_uncertainty : float, default=0.1
            Relative uncertainty in parameters (±10%)
        noise_level : float, default=0.01
            Measurement noise standard deviation
        disturbance_magnitude : float, default=0.5
            External disturbance magnitude
        reference_trajectory : np.ndarray, optional
            Reference trajectory for tracking
        """
        super().__init__(simulation_config, controller_factory, reference_trajectory)

        self.robustness_metric = robustness_metric.lower()
        self.n_variations = n_variations
        self.parameter_uncertainty = parameter_uncertainty
        self.noise_level = noise_level
        self.disturbance_magnitude = disturbance_magnitude

        # Validate robustness metric
        valid_metrics = ['monte_carlo', 'worst_case', 'sensitivity', 'h_infinity', 'composite']
        if self.robustness_metric not in valid_metrics:
            raise ValueError(f"robustness_metric must be one of {valid_metrics}")

        # Store nominal performance for comparison
        self._nominal_performance = None

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute robustness objective.

        This method evaluates robustness by running multiple simulations
        with varied parameters and computing robustness metrics.
        """
        # Get controller parameters from kwargs or assume they're the optimization variables
        controller_params = kwargs.get('controller_parameters', None)

        if controller_params is None:
            # Use the simulation results as nominal case
            return self._compute_robustness_from_results(times, states, controls)

        if self.robustness_metric == 'monte_carlo':
            return self._compute_monte_carlo_robustness(controller_params)

        elif self.robustness_metric == 'worst_case':
            return self._compute_worst_case_robustness(controller_params)

        elif self.robustness_metric == 'sensitivity':
            return self._compute_sensitivity_robustness(controller_params)

        elif self.robustness_metric == 'h_infinity':
            return self._compute_h_infinity_robustness(controller_params, times, states, controls)

        elif self.robustness_metric == 'composite':
            return self._compute_composite_robustness(controller_params, times, states, controls)

        else:
            raise ValueError(f"Unknown robustness metric: {self.robustness_metric}")

    def _compute_robustness_from_results(self,
                                       times: np.ndarray,
                                       states: np.ndarray,
                                       controls: np.ndarray) -> float:
        """Compute robustness metric from single simulation results."""
        # Analyze trajectory characteristics for robustness indicators

        # 1. Control effort variation (smoother control is more robust)
        if len(controls) > 1:
            dt = times[1] - times[0]
            control_variation = np.std(np.gradient(controls.flatten(), dt))
        else:
            control_variation = 0.0

        # 2. State trajectory smoothness
        state_variations = []
        for i in range(states.shape[1]):
            if len(states) > 1:
                state_var = np.std(np.gradient(states[:, i], times[1] - times[0]))
                state_variations.append(state_var)

        avg_state_variation = np.mean(state_variations) if state_variations else 0.0

        # 3. Settling behavior (faster settling suggests less robustness margin)
        settling_speed = self._estimate_settling_speed(times, states)

        # Combine metrics (higher values indicate less robustness)
        robustness_penalty = (
            0.4 * control_variation +
            0.4 * avg_state_variation +
            0.2 * settling_speed
        )

        return robustness_penalty

    def _compute_monte_carlo_robustness(self, controller_params: np.ndarray) -> float:
        """Compute Monte Carlo robustness analysis."""
        try:
            performances = []

            # Generate parameter variations
            variations = self._generate_parameter_variations()

            # Use parallel simulation if possible
            with ThreadPoolExecutor(max_workers=min(4, self.n_variations)) as executor:
                futures = []
                for variation in variations:
                    future = executor.submit(self._simulate_with_variation, controller_params, variation)
                    futures.append(future)

                # Collect results
                for future in futures:
                    try:
                        performance = future.result(timeout=30)  # 30 second timeout
                        if performance is not None:
                            performances.append(performance)
                    except Exception as e:
                        warnings.warn(f"Simulation failed: {e}")
                        performances.append(float('inf'))  # Large penalty for failed simulations

            if not performances:
                return float('inf')  # All simulations failed

            # Robustness metrics
            mean_performance = np.mean(performances)
            std_performance = np.std(performances)
            worst_performance = np.max(performances)

            # Combined robustness measure
            # Lower mean is good, but we also penalize high variance and worst-case
            robustness_metric = (
                0.5 * mean_performance +
                0.3 * std_performance +
                0.2 * (worst_performance - mean_performance)
            )

            return robustness_metric

        except Exception as e:
            warnings.warn(f"Monte Carlo robustness computation failed: {e}")
            return float('inf')

    def _compute_worst_case_robustness(self, controller_params: np.ndarray) -> float:
        """Compute worst-case robustness analysis."""
        worst_performance = 0.0

        # Test extreme parameter combinations
        extreme_variations = self._generate_extreme_variations()

        for variation in extreme_variations:
            try:
                performance = self._simulate_with_variation(controller_params, variation)
                if performance is not None:
                    worst_performance = max(worst_performance, performance)
                else:
                    worst_performance = float('inf')
                    break  # One failure means worst-case failure
            except Exception:
                worst_performance = float('inf')
                break

        return worst_performance

    def _compute_sensitivity_robustness(self, controller_params: np.ndarray) -> float:
        """Compute sensitivity-based robustness analysis."""
        try:
            # Nominal performance
            nominal_performance = self._simulate_with_variation(controller_params, {})

            if nominal_performance is None:
                return float('inf')

            sensitivities = []

            # Test sensitivity to each parameter
            parameter_names = ['cart_mass', 'pend1_mass', 'pend2_mass',
                             'pend1_length', 'pend2_length', 'damping']

            for param_name in parameter_names:
                # Small positive perturbation
                perturbation = {param_name: self.parameter_uncertainty * 0.1}
                perturbed_performance = self._simulate_with_variation(controller_params, perturbation)

                if perturbed_performance is not None:
                    sensitivity = abs(perturbed_performance - nominal_performance) / (self.parameter_uncertainty * 0.1)
                    sensitivities.append(sensitivity)

            # Return average sensitivity (lower is more robust)
            return np.mean(sensitivities) if sensitivities else float('inf')

        except Exception as e:
            warnings.warn(f"Sensitivity analysis failed: {e}")
            return float('inf')

    def _compute_h_infinity_robustness(self,
                                     controller_params: np.ndarray,
                                     times: np.ndarray,
                                     states: np.ndarray,
                                     controls: np.ndarray) -> float:
        """Compute H-infinity norm approximation for robustness."""
        # Simplified H-infinity robustness measure
        # Based on signal norms and disturbance rejection

        # Estimate disturbance rejection from control effort
        if len(controls) > 1:
            control_norm = np.sqrt(np.mean(controls.flatten()**2))

            # Estimate state disturbance (deviation from reference or equilibrium)
            if self.reference_trajectory is not None:
                if len(self.reference_trajectory) == len(states):
                    state_error = states - self.reference_trajectory
                else:
                    # Use zero reference
                    state_error = states
            else:
                state_error = states

            state_norm = np.sqrt(np.mean(np.sum(state_error**2, axis=1)))

            # H-infinity approximation: ||output|| / ||input||
            if control_norm > 1e-12:
                h_inf_estimate = state_norm / control_norm
            else:
                h_inf_estimate = state_norm

            return h_inf_estimate
        else:
            return 0.0

    def _compute_composite_robustness(self,
                                    controller_params: np.ndarray,
                                    times: np.ndarray,
                                    states: np.ndarray,
                                    controls: np.ndarray) -> float:
        """Compute composite robustness metric."""
        try:
            # Monte Carlo component (reduced samples for speed)
            mc_samples = min(10, self.n_variations)
            original_n = self.n_variations
            self.n_variations = mc_samples
            mc_robustness = self._compute_monte_carlo_robustness(controller_params)
            self.n_variations = original_n

            # Sensitivity component
            sensitivity_robustness = self._compute_sensitivity_robustness(controller_params)

            # H-infinity component
            h_inf_robustness = self._compute_h_infinity_robustness(controller_params, times, states, controls)

            # Weighted combination
            composite_robustness = (
                0.5 * mc_robustness +
                0.3 * sensitivity_robustness +
                0.2 * h_inf_robustness
            )

            return composite_robustness

        except Exception as e:
            warnings.warn(f"Composite robustness computation failed: {e}")
            return float('inf')

    def _generate_parameter_variations(self) -> List[Dict[str, float]]:
        """Generate random parameter variations for Monte Carlo analysis."""
        variations = []
        np.random.seed(42)  # For reproducibility

        for _ in range(self.n_variations):
            variation = {}

            # Mass variations
            variation['cart_mass'] = 1.0 + np.random.uniform(-self.parameter_uncertainty, self.parameter_uncertainty)
            variation['pend1_mass'] = 1.0 + np.random.uniform(-self.parameter_uncertainty, self.parameter_uncertainty)
            variation['pend2_mass'] = 1.0 + np.random.uniform(-self.parameter_uncertainty, self.parameter_uncertainty)

            # Length variations
            variation['pend1_length'] = 1.0 + np.random.uniform(-self.parameter_uncertainty, self.parameter_uncertainty)
            variation['pend2_length'] = 1.0 + np.random.uniform(-self.parameter_uncertainty, self.parameter_uncertainty)

            # Damping variations
            variation['damping'] = 1.0 + np.random.uniform(-self.parameter_uncertainty, self.parameter_uncertainty)

            variations.append(variation)

        return variations

    def _generate_extreme_variations(self) -> List[Dict[str, float]]:
        """Generate extreme parameter variations for worst-case analysis."""
        variations = []

        # Generate all combinations of extreme values
        extreme_params = ['cart_mass', 'pend1_mass', 'pend2_mass', 'pend1_length', 'pend2_length']

        # Test a few key extreme combinations (not all 2^5 = 32)
        extreme_combinations = [
            {param: 1.0 + self.parameter_uncertainty for param in extreme_params},  # All high
            {param: 1.0 - self.parameter_uncertainty for param in extreme_params},  # All low
            # Mixed combinations
            {'cart_mass': 1.0 + self.parameter_uncertainty, 'pend1_mass': 1.0 - self.parameter_uncertainty,
             'pend2_mass': 1.0 + self.parameter_uncertainty, 'pend1_length': 1.0 - self.parameter_uncertainty,
             'pend2_length': 1.0 + self.parameter_uncertainty},
        ]

        return extreme_combinations

    def _simulate_with_variation(self,
                               controller_params: np.ndarray,
                               parameter_variation: Dict[str, float]) -> Optional[float]:
        """Simulate system with parameter variations and return performance metric."""
        try:
            # This is a simplified simulation - in practice, you would:
            # 1. Create modified dynamics model with parameter variations
            # 2. Add noise to measurements if specified
            # 3. Add external disturbances
            # 4. Run simulation with controller
            # 5. Compute performance metric (tracking error, stability, etc.)

            # For now, return a placeholder based on parameter variations
            # This would be replaced with actual simulation code

            # Simulate the impact of parameter variations on performance
            variation_impact = 0.0
            for param_name, variation_factor in parameter_variation.items():
                # Each parameter variation contributes to performance degradation
                impact = abs(variation_factor - 1.0)
                if 'mass' in param_name:
                    variation_impact += impact * 2.0  # Mass variations have larger impact
                elif 'length' in param_name:
                    variation_impact += impact * 3.0  # Length variations have largest impact
                else:
                    variation_impact += impact * 1.0

            # Add noise impact
            noise_impact = self.noise_level * 5.0

            # Add disturbance impact
            disturbance_impact = self.disturbance_magnitude * 2.0

            # Total performance degradation
            total_performance = variation_impact + noise_impact + disturbance_impact

            return total_performance

        except Exception as e:
            warnings.warn(f"Simulation with variation failed: {e}")
            return None

    def _estimate_settling_speed(self, times: np.ndarray, states: np.ndarray) -> float:
        """Estimate settling speed from trajectory."""
        if len(times) < 2:
            return 0.0

        # Look at cart position settling
        cart_pos = states[:, 0] if states.shape[1] > 0 else np.zeros(len(times))

        # Find when system reaches 95% of steady state
        final_value = np.mean(cart_pos[-int(len(cart_pos)*0.1):])
        target_value = 0.95 * final_value

        settling_index = len(cart_pos) - 1
        for i, pos in enumerate(cart_pos):
            if abs(pos - final_value) <= abs(target_value - final_value):
                settling_index = i
                break

        settling_time = times[settling_index]

        # Convert to settling speed (inverse of settling time)
        return 1.0 / (settling_time + 1e-6)

    def get_robustness_analysis(self,
                              controller_params: np.ndarray) -> Dict[str, Any]:
        """Get comprehensive robustness analysis.

        Parameters
        ----------
        controller_params : np.ndarray
            Controller parameters to analyze

        Returns
        -------
        dict
            Dictionary with detailed robustness metrics
        """
        analysis = {}

        try:
            # Monte Carlo analysis
            analysis['monte_carlo_robustness'] = self._compute_monte_carlo_robustness(controller_params)

            # Sensitivity analysis
            analysis['sensitivity_robustness'] = self._compute_sensitivity_robustness(controller_params)

            # Worst-case analysis
            analysis['worst_case_robustness'] = self._compute_worst_case_robustness(controller_params)

            # Additional metrics
            variations = self._generate_parameter_variations()
            performances = []
            for variation in variations[:5]:  # Sample a few for analysis
                perf = self._simulate_with_variation(controller_params, variation)
                if perf is not None:
                    performances.append(perf)

            if performances:
                analysis['performance_mean'] = np.mean(performances)
                analysis['performance_std'] = np.std(performances)
                analysis['performance_range'] = np.max(performances) - np.min(performances)

        except Exception as e:
            warnings.warn(f"Robustness analysis failed: {e}")
            analysis['error'] = str(e)

        return analysis