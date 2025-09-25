#==========================================================================================\\\
#================= benchmarks/analysis/accuracy_metrics.py ==============================\\\
#==========================================================================================\\\
"""
Accuracy and conservation metrics for numerical integration analysis.

This module provides sophisticated metrics for evaluating the quality of
numerical integration schemes in dynamic system simulation:

Conservation Metrics:
* **Energy Drift**: Violation of energy conservation in Hamiltonian systems
* **Momentum Conservation**: Linear and angular momentum preservation
* **Symplectic Error**: Phase space volume preservation metrics

Accuracy Metrics:
* **Global Error**: Comparison with reference solutions
* **Order of Accuracy**: Empirical convergence rate analysis
* **Step Size Efficiency**: Accuracy per computational cost
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.plant import SimplifiedDIPDynamics


@dataclass
class AccuracyAnalysis:
    """Container for comprehensive accuracy analysis results."""
    method_name: str
    energy_drift: np.ndarray
    max_energy_drift: float
    mean_energy_drift: float
    relative_energy_error: float
    conservation_violated: bool
    performance_ratio: float  # accuracy per computational cost


class EnergyAnalyzer:
    """Analyzes energy conservation properties of integration results."""

    def __init__(self, physics_params: Dict):
        self.dynamics = SimplifiedDIPDynamics(physics_params)
        self.physics = physics_params

        # Use the correct energy computation method from SimplifiedDIPDynamics
        self._energy_fn = self.dynamics.compute_total_energy

    def compute_energy_drift(self, result) -> np.ndarray:
        """Compute energy drift throughout simulation trajectory.

        For conservative systems (no friction), total mechanical energy
        should be conserved. Energy drift indicates numerical dissipation
        or instability in the integration scheme.

        Parameters
        ----------
        result : IntegrationResult or dict
            Integration result containing state trajectory

        Returns
        -------
        np.ndarray
            Energy drift relative to initial energy at each time step
        """
        if hasattr(result, 'states'):
            states = result.states
        else:
            states = result['states']

        # Compute total energy at each time step
        energies = np.array([
            self._energy_fn(state)
            for state in states
        ])

        # Energy drift relative to initial value
        initial_energy = energies[0]
        energy_drift = energies - initial_energy

        return energy_drift

    def analyze_energy_conservation(self, result) -> AccuracyAnalysis:
        """Comprehensive energy conservation analysis.

        Parameters
        ----------
        result : IntegrationResult or dict
            Integration result to analyze

        Returns
        -------
        AccuracyAnalysis
            Comprehensive analysis of energy conservation
        """
        energy_drift = self.compute_energy_drift(result)
        if hasattr(result, 'states'):
            initial_state = result.states[0]
        else:
            initial_state = result['states'][0]
        initial_energy = self.compute_total_energy(initial_state)

        # Key conservation metrics
        max_drift = np.max(np.abs(energy_drift))
        mean_drift = np.mean(np.abs(energy_drift))
        # Use absolute error if initial energy is too small for meaningful relative error
        min_energy_threshold = 1e-6
        if abs(initial_energy) > min_energy_threshold:
            relative_error = max_drift / abs(initial_energy)
        else:
            relative_error = max_drift  # Use absolute error when initial energy is negligible

        # Conservation violation threshold (1% of initial energy)
        violation_threshold = 0.01 * abs(initial_energy)
        conservation_violated = max_drift > violation_threshold

        # Performance ratio (accuracy per computational cost)
        if hasattr(result, 'elapsed_time'):
            execution_time = result.elapsed_time
        elif hasattr(result, 'get'):
            execution_time = result.get('time', 1.0)
        else:
            execution_time = 1.0
        performance_ratio = 1.0 / (mean_drift * execution_time) if mean_drift > 0 else np.inf

        if hasattr(result, 'method'):
            method_name = result.method
        elif hasattr(result, 'get'):
            method_name = result.get('method', 'Unknown')
        else:
            method_name = 'Unknown'

        return AccuracyAnalysis(
            method_name=method_name,
            energy_drift=energy_drift,
            max_energy_drift=max_drift,
            mean_energy_drift=mean_drift,
            relative_energy_error=relative_error,
            conservation_violated=conservation_violated,
            performance_ratio=performance_ratio
        )

    def compute_total_energy(self, state: np.ndarray) -> float:
        """Compute total mechanical energy for a single state."""
        return self._energy_fn(state)

    def check_hamiltonian_structure(self, result) -> Dict[str, float]:
        """Verify Hamiltonian structure preservation.

        For Hamiltonian systems, the flow should preserve the symplectic
        structure. This function checks basic symplectic properties.

        Parameters
        ----------
        result : IntegrationResult or dict
            Integration result to analyze

        Returns
        -------
        dict
            Symplectic structure analysis results
        """
        if hasattr(result, 'states'):
            states = result.states
        else:
            states = result['states']

        n_states = states.shape[1] // 2  # Assuming [q, p] structure

        # Phase space volume preservation (simplified check)
        initial_volume = self._compute_phase_volume(states[0])
        final_volume = self._compute_phase_volume(states[-1])
        # Avoid divide by zero for volume change calculation
        if abs(initial_volume) > 1e-12:
            volume_change = abs(final_volume - initial_volume) / initial_volume
        else:
            volume_change = abs(final_volume - initial_volume)  # Use absolute change

        return {
            "initial_phase_volume": initial_volume,
            "final_phase_volume": final_volume,
            "relative_volume_change": volume_change,
            "symplectic_preserved": volume_change < 0.1  # 10% tolerance
        }

    def _compute_phase_volume(self, state: np.ndarray) -> float:
        """Simplified phase space volume computation."""
        # For demonstration - in practice, this would compute
        # the determinant of appropriate Jacobian matrices
        positions = state[:len(state)//2]
        velocities = state[len(state)//2:]
        return np.linalg.norm(positions) * np.linalg.norm(velocities)


class ConvergenceAnalyzer:
    """Analyzes convergence properties and order of accuracy."""

    def __init__(self, physics_params: Dict):
        self.physics = physics_params

    def estimate_convergence_order(self,
                                 integration_method: callable,
                                 x0: np.ndarray,
                                 sim_time: float,
                                 dt_values: List[float],
                                 reference_solution: Optional[np.ndarray] = None) -> Dict[str, float]:
        """Estimate empirical order of convergence.

        Parameters
        ----------
        integration_method : callable
            Integration method to test
        x0 : np.ndarray
            Initial condition
        sim_time : float
            Simulation time
        dt_values : list of float
            List of time steps to test (should be decreasing)
        reference_solution : np.ndarray, optional
            High-accuracy reference solution

        Returns
        -------
        dict
            Convergence analysis results
        """
        errors = []

        for dt in dt_values:
            result = integration_method(x0, sim_time, dt, controller=None)

            if reference_solution is not None:
                # Compare with reference solution
                # Interpolate to common time points
                error = self._compute_global_error(result, reference_solution)
            else:
                # Use Richardson extrapolation approach
                error = self._estimate_error_richardson(result, dt)

            errors.append(error)

        # Estimate order from log-log slope
        log_dt = np.log(dt_values)
        log_errors = np.log(errors)

        # Linear regression to find slope
        coeffs = np.polyfit(log_dt, log_errors, 1)
        estimated_order = -coeffs[0]  # Negative because error decreases with dt

        return {
            "estimated_order": estimated_order,
            "dt_values": dt_values,
            "errors": errors,
            "theoretical_order": self._get_theoretical_order(integration_method),
            "convergence_achieved": abs(estimated_order - self._get_theoretical_order(integration_method)) < 0.5
        }

    def _compute_global_error(self, result, reference_solution: np.ndarray) -> float:
        """Compute global error against reference solution."""
        # Simplified global error computation
        if hasattr(result, 'states'):
            states = result.states
        else:
            states = result['states']

        # Assume reference solution is at final time
        final_state = states[-1]
        reference_final = reference_solution[-1]

        return np.linalg.norm(final_state - reference_final)

    def _estimate_error_richardson(self, result, dt: float) -> float:
        """Estimate error using Richardson extrapolation."""
        # Simplified error estimation
        if hasattr(result, 'states'):
            states = result.states
        else:
            states = result['states']

        # Use energy drift as error proxy for conservative systems
        energy_analyzer = EnergyAnalyzer(self.physics)
        drift = energy_analyzer.compute_energy_drift(result)
        return np.max(np.abs(drift))

    def _get_theoretical_order(self, integration_method: callable) -> int:
        """Get theoretical order of accuracy for known methods."""
        method_name = getattr(integration_method, '__name__', str(integration_method))

        if 'euler' in method_name.lower():
            return 1
        elif 'rk4' in method_name.lower():
            return 4
        elif 'rk45' in method_name.lower():
            return 5
        else:
            return 2  # Default assumption


class PerformanceProfiler:
    """Profiles computational performance of integration methods."""

    @staticmethod
    def create_performance_profile(results: List) -> Dict[str, Dict[str, float]]:
        """Create performance profile comparing multiple integration results.

        Parameters
        ----------
        results : list
            List of IntegrationResult objects or dictionaries

        Returns
        -------
        dict
            Performance profile with timing and accuracy metrics
        """
        profile = {}

        for result in results:
            if hasattr(result, 'method'):
                method_name = result.method
                execution_time = result.elapsed_time
            else:
                method_name = result['method']
                execution_time = result['time']

            # Extract performance metrics
            if hasattr(result, 'metadata'):
                n_steps = result.metadata.get('n_steps', len(result.states))
                nfev = result.metadata.get('nfev', n_steps)  # Function evaluations
            else:
                n_steps = len(result['states']) if 'states' in result else 1
                nfev = result['nfev'] if 'nfev' in result else n_steps

            profile[method_name] = {
                "execution_time": execution_time,
                "steps_per_second": n_steps / execution_time if execution_time > 0 else np.inf,
                "function_evaluations": nfev,
                "efficiency_ratio": n_steps / nfev if nfev > 0 else 1.0,
                "total_steps": n_steps
            }

        return profile

    @staticmethod
    def compare_efficiency(results: List, accuracy_metric: str = 'energy_drift') -> Dict[str, float]:
        """Compare computational efficiency relative to accuracy.

        Parameters
        ----------
        results : list
            List of integration results with accuracy analysis
        accuracy_metric : str
            Metric to use for accuracy comparison

        Returns
        -------
        dict
            Efficiency ratios (accuracy per computational cost)
        """
        efficiency_ratios = {}

        for result in results:
            if hasattr(result, 'method'):
                method_name = result.method
                execution_time = result.elapsed_time
            else:
                method_name = result['method']
                execution_time = result['time']

            # Get accuracy metric (lower is better, so invert)
            if hasattr(result, 'accuracy_analysis'):
                accuracy = getattr(result.accuracy_analysis, accuracy_metric, 1.0)
            else:
                accuracy = result[accuracy_metric] if accuracy_metric in result else 1.0

            # Efficiency = 1 / (error × time)
            efficiency = 1.0 / (accuracy * execution_time) if accuracy > 0 and execution_time > 0 else 0

            efficiency_ratios[method_name] = efficiency

        return efficiency_ratios