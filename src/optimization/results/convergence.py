#==========================================================================================\\\
#====================== src/optimization/results/convergence.py =====================\\\
#==========================================================================================\\\

"""Convergence monitoring and analysis for optimization algorithms."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ..core.interfaces import ConvergenceMonitor as IConvergenceMonitor, ConvergenceStatus


class ConvergenceMonitor(IConvergenceMonitor):
    """Professional convergence monitor with multiple criteria."""

    def __init__(self,
                 max_iterations: int = 1000,
                 tolerance: float = 1e-6,
                 patience: int = 50,
                 min_improvement: float = 1e-8,
                 target_fitness: Optional[float] = None):
        """Initialize convergence monitor.

        Parameters
        ----------
        max_iterations : int, optional
            Maximum number of iterations
        tolerance : float, optional
            Convergence tolerance
        patience : int, optional
            Number of iterations without improvement before stopping
        min_improvement : float, optional
            Minimum improvement required
        target_fitness : float, optional
            Target fitness value for early stopping
        """
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.patience = patience
        self.min_improvement = min_improvement
        self.target_fitness = target_fitness

        # Convergence history
        self.history = {
            'iteration': [],
            'best_fitness': [],
            'parameters': [],
            'improvement': [],
            'stagnation_count': []
        }

        # State
        self.last_improvement_iteration = 0
        self.best_fitness_ever = np.inf
        self.stagnation_count = 0

    def update(self, iteration: int, best_value: float, parameters: np.ndarray, **kwargs) -> None:
        """Update convergence monitor with new iteration data."""
        # Compute improvement
        improvement = self.best_fitness_ever - best_value
        if best_value < self.best_fitness_ever:
            self.best_fitness_ever = best_value
            self.last_improvement_iteration = iteration
            self.stagnation_count = 0
        else:
            self.stagnation_count += 1

        # Store history
        self.history['iteration'].append(iteration)
        self.history['best_fitness'].append(best_value)
        self.history['parameters'].append(parameters.copy())
        self.history['improvement'].append(improvement)
        self.history['stagnation_count'].append(self.stagnation_count)

    def check_convergence(self) -> Tuple[bool, ConvergenceStatus, str]:
        """Check if convergence criteria are met."""
        if not self.history['iteration']:
            return False, ConvergenceStatus.RUNNING, "No data"

        current_iteration = self.history['iteration'][-1]
        current_fitness = self.history['best_fitness'][-1]

        # Check maximum iterations
        if current_iteration >= self.max_iterations:
            return True, ConvergenceStatus.MAX_ITERATIONS, "Maximum iterations reached"

        # Check target fitness
        if self.target_fitness is not None and current_fitness <= self.target_fitness:
            return True, ConvergenceStatus.CONVERGED, "Target fitness reached"

        # Check tolerance
        if len(self.history['best_fitness']) > 1:
            recent_improvement = (
                self.history['best_fitness'][-min(10, len(self.history['best_fitness']))] - current_fitness
            )
            if recent_improvement < self.tolerance:
                return True, ConvergenceStatus.TOLERANCE_REACHED, "Tolerance reached"

        # Check stagnation
        if self.stagnation_count >= self.patience:
            return True, ConvergenceStatus.CONVERGED, f"No improvement for {self.patience} iterations"

        return False, ConvergenceStatus.RUNNING, "Optimization continuing"

    def reset(self) -> None:
        """Reset convergence monitor."""
        self.history = {
            'iteration': [],
            'best_fitness': [],
            'parameters': [],
            'improvement': [],
            'stagnation_count': []
        }
        self.last_improvement_iteration = 0
        self.best_fitness_ever = np.inf
        self.stagnation_count = 0

    @property
    def convergence_history(self) -> Dict[str, List]:
        """Get convergence history data."""
        return self.history.copy()


class ConvergenceAnalyzer:
    """Analyze optimization convergence characteristics."""

    def __init__(self):
        """Initialize convergence analyzer."""
        pass

    def analyze_convergence_rate(self, fitness_history: List[float]) -> Dict[str, Any]:
        """Analyze convergence rate characteristics.

        Parameters
        ----------
        fitness_history : List[float]
            Fitness values over iterations

        Returns
        -------
        dict
            Convergence rate analysis
        """
        if len(fitness_history) < 10:
            return {'error': 'Insufficient data for convergence analysis'}

        fitness_array = np.array(fitness_history)

        # Linear convergence rate (in log space)
        log_fitness = np.log10(np.maximum(fitness_array, 1e-12))
        linear_rate = self._compute_linear_rate(log_fitness)

        # Exponential convergence detection
        exponential_fit = self._fit_exponential_decay(fitness_array)

        # Plateau detection
        plateau_info = self._detect_plateaus(fitness_array)

        # Convergence phases
        phases = self._identify_convergence_phases(fitness_array)

        return {
            'linear_convergence_rate': linear_rate,
            'exponential_decay': exponential_fit,
            'plateaus': plateau_info,
            'convergence_phases': phases,
            'total_improvement': float(fitness_array[0] - fitness_array[-1]),
            'relative_improvement': float((fitness_array[0] - fitness_array[-1]) / fitness_array[0]),
            'final_fitness': float(fitness_array[-1])
        }

    def _compute_linear_rate(self, log_fitness: np.ndarray) -> Dict[str, Any]:
        """Compute linear convergence rate in log space."""
        iterations = np.arange(len(log_fitness))

        # Fit linear trend
        coeffs = np.polyfit(iterations, log_fitness, 1)
        slope = coeffs[0]

        # R-squared
        fitted = np.polyval(coeffs, iterations)
        ss_res = np.sum((log_fitness - fitted) ** 2)
        ss_tot = np.sum((log_fitness - np.mean(log_fitness)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return {
            'slope': float(slope),
            'r_squared': float(r_squared),
            'is_linear': r_squared > 0.8,
            'convergence_order': 'linear' if abs(slope) < 0.1 else 'superlinear'
        }

    def _fit_exponential_decay(self, fitness: np.ndarray) -> Dict[str, Any]:
        """Fit exponential decay model to fitness."""
        iterations = np.arange(len(fitness))

        try:
            # Fit y = a * exp(-b * x) + c
            from scipy.optimize import curve_fit

            def exp_decay(x, a, b, c):
                return a * np.exp(-b * x) + c

            # Initial guess
            p0 = [fitness[0] - fitness[-1], 0.01, fitness[-1]]

            popt, pcov = curve_fit(exp_decay, iterations, fitness, p0=p0)

            # Compute R-squared
            fitted = exp_decay(iterations, *popt)
            ss_res = np.sum((fitness - fitted) ** 2)
            ss_tot = np.sum((fitness - np.mean(fitness)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            return {
                'amplitude': float(popt[0]),
                'decay_rate': float(popt[1]),
                'asymptote': float(popt[2]),
                'r_squared': float(r_squared),
                'is_exponential': r_squared > 0.9
            }
        except Exception:
            return {'error': 'Failed to fit exponential model'}

    def _detect_plateaus(self, fitness: np.ndarray, threshold: float = 1e-6) -> List[Dict[str, Any]]:
        """Detect plateau regions in fitness curve."""
        plateaus = []

        # Compute local gradients
        gradients = np.abs(np.diff(fitness))

        # Find flat regions
        flat_mask = gradients < threshold

        # Group consecutive flat regions
        if np.any(flat_mask):
            changes = np.diff(np.concatenate(([False], flat_mask, [False])).astype(int))
            starts = np.where(changes == 1)[0]
            ends = np.where(changes == -1)[0]

            for start, end in zip(starts, ends):
                if end - start > 5:  # Minimum plateau length
                    plateaus.append({
                        'start_iteration': int(start),
                        'end_iteration': int(end),
                        'length': int(end - start),
                        'fitness_level': float(np.mean(fitness[start:end]))
                    })

        return plateaus

    def _identify_convergence_phases(self, fitness: np.ndarray) -> List[Dict[str, Any]]:
        """Identify different phases of convergence."""
        phases = []

        if len(fitness) < 20:
            return phases

        # Compute improvement rates in overlapping windows
        window_size = max(10, len(fitness) // 10)
        improvement_rates = []

        for i in range(0, len(fitness) - window_size, window_size // 2):
            window = fitness[i:i + window_size]
            rate = (window[0] - window[-1]) / len(window)
            improvement_rates.append(rate)

        # Classify phases based on improvement rate
        for i, rate in enumerate(improvement_rates):
            start_iter = i * window_size // 2
            end_iter = min(start_iter + window_size, len(fitness))

            if rate > 0.01:
                phase_type = 'rapid_improvement'
            elif rate > 0.001:
                phase_type = 'moderate_improvement'
            elif rate > 0.0001:
                phase_type = 'slow_improvement'
            else:
                phase_type = 'stagnation'

            phases.append({
                'start_iteration': start_iter,
                'end_iteration': end_iter,
                'phase_type': phase_type,
                'improvement_rate': float(rate)
            })

        return phases

    def compare_convergence_curves(self,
                                 curves: Dict[str, List[float]]) -> Dict[str, Any]:
        """Compare multiple convergence curves.

        Parameters
        ----------
        curves : Dict[str, List[float]]
            Dictionary of algorithm names to fitness histories

        Returns
        -------
        dict
            Comparison analysis
        """
        comparison = {}

        for name, curve in curves.items():
            analysis = self.analyze_convergence_rate(curve)
            comparison[name] = analysis

        # Overall comparison
        final_fitness = {name: curve[-1] for name, curve in curves.items()}
        best_algorithm = min(final_fitness, key=final_fitness.get)

        convergence_speeds = {}
        for name, curve in curves.items():
            # Find iteration where 90% of final improvement is achieved
            total_improvement = curve[0] - curve[-1]
            target_improvement = 0.9 * total_improvement

            for i, fitness in enumerate(curve):
                if curve[0] - fitness >= target_improvement:
                    convergence_speeds[name] = i
                    break
            else:
                convergence_speeds[name] = len(curve)

        fastest_algorithm = min(convergence_speeds, key=convergence_speeds.get)

        return {
            'individual_analysis': comparison,
            'best_final_fitness': {
                'algorithm': best_algorithm,
                'fitness': final_fitness[best_algorithm]
            },
            'fastest_convergence': {
                'algorithm': fastest_algorithm,
                'iterations_to_90_percent': convergence_speeds[fastest_algorithm]
            },
            'convergence_speeds': convergence_speeds,
            'final_fitness_ranking': sorted(final_fitness.items(), key=lambda x: x[1])
        }