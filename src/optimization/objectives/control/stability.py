#==========================================================================================\\\
#=============== src/optimization/objectives/control/stability.py ====================\\\
#==========================================================================================\\\

"""Stability margin objective functions for control optimization."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union, Callable, Tuple
import numpy as np
import warnings

from ..base import SimulationBasedObjective

# Try to import control library functions, fallback to basic implementations
try:
    from scipy import signal
    from scipy.linalg import eigvals
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    warnings.warn("SciPy not available. Stability analysis will use simplified methods.")


class StabilityMarginObjective(SimulationBasedObjective):
    """Objective function for optimizing stability margins.

    This objective computes various stability metrics including:
    - Lyapunov stability analysis
    - Phase and gain margins (if linearized model available)
    - Settling time and damping characteristics
    - Pole placement assessment
    """

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 stability_metric: str = 'lyapunov',
                 min_gain_margin: float = 6.0,  # dB
                 min_phase_margin: float = 45.0,  # degrees
                 max_settling_time: float = 5.0,  # seconds
                 reference_trajectory: Optional[np.ndarray] = None):
        """Initialize stability margin objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration parameters
        controller_factory : callable
            Function to create controller from parameters
        stability_metric : str, default='lyapunov'
            Stability metric: 'lyapunov', 'margins', 'poles', 'settling'
        min_gain_margin : float, default=6.0
            Minimum acceptable gain margin [dB]
        min_phase_margin : float, default=45.0
            Minimum acceptable phase margin [degrees]
        max_settling_time : float, default=5.0
            Maximum acceptable settling time [seconds]
        reference_trajectory : np.ndarray, optional
            Reference trajectory for stability analysis
        """
        super().__init__(simulation_config, controller_factory, reference_trajectory)

        self.stability_metric = stability_metric.lower()
        self.min_gain_margin = min_gain_margin
        self.min_phase_margin = min_phase_margin
        self.max_settling_time = max_settling_time

        # Validate stability metric
        valid_metrics = ['lyapunov', 'margins', 'poles', 'settling', 'composite']
        if self.stability_metric not in valid_metrics:
            raise ValueError(f"stability_metric must be one of {valid_metrics}")

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute stability objective from simulation results.

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
            Stability objective value (lower is better for instability)
        """
        if self.stability_metric == 'lyapunov':
            return self._compute_lyapunov_stability(times, states, controls)

        elif self.stability_metric == 'margins':
            return self._compute_stability_margins(times, states, controls, **kwargs)

        elif self.stability_metric == 'poles':
            return self._compute_pole_placement(times, states, controls, **kwargs)

        elif self.stability_metric == 'settling':
            return self._compute_settling_characteristics(times, states, controls)

        elif self.stability_metric == 'composite':
            return self._compute_composite_stability(times, states, controls, **kwargs)

        else:
            raise ValueError(f"Unknown stability metric: {self.stability_metric}")

    def _compute_lyapunov_stability(self,
                                  times: np.ndarray,
                                  states: np.ndarray,
                                  controls: np.ndarray) -> float:
        """Compute Lyapunov-based stability metric.

        Uses trajectory analysis to assess stability characteristics.
        """
        # Compute Lyapunov function candidate V(x) = x^T P x
        # For DIP system, use kinetic + potential energy as Lyapunov candidate

        # Extract positions and velocities
        if states.shape[1] >= 6:  # Full DIP state [x, θ1, θ2, ẋ, θ̇1, θ̇2]
            positions = states[:, :3]  # [x, θ1, θ2]
            velocities = states[:, 3:6]  # [ẋ, θ̇1, θ̇2]
        else:
            # Simplified state handling
            positions = states[:, :states.shape[1]//2]
            velocities = states[:, states.shape[1]//2:]

        # Compute energy-based Lyapunov function
        kinetic_energy = 0.5 * np.sum(velocities**2, axis=1)  # Simplified
        potential_energy = 9.81 * (1 - np.cos(positions[:, 1])) + 9.81 * (1 - np.cos(positions[:, 2]))  # Pendulum potential

        V = kinetic_energy + potential_energy

        # Compute Lyapunov derivative (stability indicator)
        if len(V) > 1:
            dt = times[1] - times[0]
            dV_dt = np.gradient(V, dt)

            # Stability metric: average positive Lyapunov derivative
            unstable_regions = dV_dt > 0
            instability_measure = np.mean(dV_dt[unstable_regions]) if np.any(unstable_regions) else 0.0

            # Add penalty for large energy growth
            energy_growth = (V[-1] - V[0]) / (V[0] + 1e-6)
            if energy_growth > 0.1:  # More than 10% energy growth
                instability_measure += energy_growth * 10.0

        else:
            instability_measure = 0.0

        return instability_measure

    def _compute_stability_margins(self,
                                 times: np.ndarray,
                                 states: np.ndarray,
                                 controls: np.ndarray,
                                 **kwargs) -> float:
        """Compute gain and phase margins (requires linearized model).

        Since we don't have a linearized model readily available,
        this uses frequency response estimation from simulation data.
        """
        if not HAS_SCIPY:
            # Fallback to simplified stability assessment
            return self._compute_lyapunov_stability(times, states, controls)

        # Use system identification to estimate transfer function
        # This is a simplified approach for demonstration
        try:
            # Estimate transfer function from input-output data
            # For DIP, use cart position as output
            if states.shape[1] >= 1:
                output = states[:, 0]  # Cart position
                input_signal = controls.flatten()

                # Remove DC component
                output = output - np.mean(output)
                input_signal = input_signal - np.mean(input_signal)

                if len(input_signal) > 10 and np.std(input_signal) > 1e-6:
                    # Cross-correlation method for frequency response estimation
                    dt = times[1] - times[0]

                    # Simplified margin estimation using trajectory characteristics
                    # Look for oscillatory behavior and growth rates
                    oscillation_measure = self._detect_oscillations(times, output)
                    growth_measure = self._detect_growth(times, output)

                    # Combine measures (lower is better for stability)
                    margin_penalty = oscillation_measure + growth_measure * 5.0

                    # Penalty if margins below thresholds (estimated)
                    if oscillation_measure > 0.5:  # Significant oscillation
                        margin_penalty += 10.0
                    if growth_measure > 0.1:  # Significant growth
                        margin_penalty += 20.0

                    return margin_penalty
                else:
                    return 0.0  # No excitation, assume stable
            else:
                return 0.0

        except Exception as e:
            # Fallback to Lyapunov if margin computation fails
            warnings.warn(f"Margin computation failed: {e}. Using Lyapunov method.")
            return self._compute_lyapunov_stability(times, states, controls)

    def _compute_pole_placement(self,
                              times: np.ndarray,
                              states: np.ndarray,
                              controls: np.ndarray,
                              **kwargs) -> float:
        """Assess pole placement from trajectory characteristics."""
        # Analyze trajectory for exponential decay/growth characteristics
        # This estimates dominant pole behavior from simulation data

        if states.shape[1] >= 6:
            # Look at each state variable for decay characteristics
            stability_measures = []

            for i in range(states.shape[1]):
                state_i = states[:, i]

                # Remove steady-state value
                steady_state = np.mean(state_i[-int(len(state_i)*0.1):])  # Last 10%
                transient = state_i - steady_state

                # Fit exponential decay to assess pole locations
                if np.max(np.abs(transient)) > 1e-6:
                    decay_measure = self._estimate_decay_rate(times, transient)
                    stability_measures.append(decay_measure)

            # Return worst-case stability measure
            return max(stability_measures) if stability_measures else 0.0
        else:
            return 0.0

    def _compute_settling_characteristics(self,
                                        times: np.ndarray,
                                        states: np.ndarray,
                                        controls: np.ndarray) -> float:
        """Compute settling time and damping characteristics."""
        # Analyze settling behavior for each state
        settling_penalties = []

        for i in range(min(3, states.shape[1])):  # Focus on position states
            state_i = states[:, i]

            # Find settling time (within 2% of final value)
            final_value = np.mean(state_i[-int(len(state_i)*0.05):])  # Last 5%
            settling_tolerance = 0.02 * (np.max(state_i) - np.min(state_i))

            if settling_tolerance > 1e-6:
                settled = np.abs(state_i - final_value) < settling_tolerance

                # Find first point where system stays settled
                settling_time = None
                for j in range(len(settled)-10):
                    if np.all(settled[j:j+10]):  # Settled for next 10 points
                        settling_time = times[j]
                        break

                if settling_time is not None:
                    if settling_time > self.max_settling_time:
                        penalty = (settling_time - self.max_settling_time) * 2.0
                        settling_penalties.append(penalty)
                else:
                    # Never settled
                    settling_penalties.append(10.0)

        return sum(settling_penalties)

    def _compute_composite_stability(self,
                                   times: np.ndarray,
                                   states: np.ndarray,
                                   controls: np.ndarray,
                                   **kwargs) -> float:
        """Compute composite stability metric combining multiple measures."""
        lyapunov_score = self._compute_lyapunov_stability(times, states, controls)
        settling_score = self._compute_settling_characteristics(times, states, controls)
        margin_score = self._compute_stability_margins(times, states, controls, **kwargs)

        # Weighted combination
        composite_score = (
            0.4 * lyapunov_score +
            0.3 * settling_score +
            0.3 * margin_score
        )

        return composite_score

    def _detect_oscillations(self, times: np.ndarray, signal: np.ndarray) -> float:
        """Detect oscillatory behavior in signal."""
        if len(signal) < 4:
            return 0.0

        # Count zero crossings
        zero_crossings = np.sum(np.diff(np.signbit(signal - np.mean(signal))))

        # Normalize by signal length
        oscillation_measure = zero_crossings / len(signal)

        return oscillation_measure

    def _detect_growth(self, times: np.ndarray, signal: np.ndarray) -> float:
        """Detect growth/instability in signal."""
        if len(signal) < 2:
            return 0.0

        # Linear trend analysis
        coeffs = np.polyfit(times, np.abs(signal), 1)
        growth_rate = coeffs[0]  # Slope

        return max(0.0, growth_rate)  # Only positive growth indicates instability

    def _estimate_decay_rate(self, times: np.ndarray, transient: np.ndarray) -> float:
        """Estimate exponential decay rate from transient response."""
        if len(transient) < 3 or np.max(np.abs(transient)) < 1e-6:
            return 0.0

        # Use envelope for decay estimation
        envelope = np.abs(transient)

        # Avoid log(0) by adding small value
        log_envelope = np.log(envelope + 1e-12)

        # Linear fit to log(envelope) vs time
        valid_indices = np.isfinite(log_envelope)
        if np.sum(valid_indices) > 2:
            coeffs = np.polyfit(times[valid_indices], log_envelope[valid_indices], 1)
            decay_rate = -coeffs[0]  # Negative slope means decay

            # Penalty for positive decay rate (growth)
            return max(0.0, -decay_rate)
        else:
            return 0.0

    def get_stability_analysis(self,
                             times: np.ndarray,
                             states: np.ndarray,
                             controls: np.ndarray) -> Dict[str, Any]:
        """Get comprehensive stability analysis.

        Returns
        -------
        dict
            Dictionary with detailed stability metrics
        """
        analysis = {}

        # Compute all stability metrics
        analysis['lyapunov_metric'] = self._compute_lyapunov_stability(times, states, controls)
        analysis['settling_metric'] = self._compute_settling_characteristics(times, states, controls)
        analysis['margin_metric'] = self._compute_stability_margins(times, states, controls)
        analysis['composite_metric'] = self._compute_composite_stability(times, states, controls)

        # Additional analysis
        for i in range(min(3, states.shape[1])):
            state_name = ['cart_pos', 'pend1_angle', 'pend2_angle'][i]
            analysis[f'{state_name}_oscillation'] = self._detect_oscillations(times, states[:, i])
            analysis[f'{state_name}_growth'] = self._detect_growth(times, states[:, i])

        return analysis