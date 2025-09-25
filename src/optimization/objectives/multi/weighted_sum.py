#==========================================================================================\\\
#=============== src/optimization/objectives/multi/weighted_sum.py ====================\\\
#==========================================================================================\\\

"""Weighted sum multi-objective optimization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable
import numpy as np
import warnings

from ..base import SimulationBasedObjective
from ...core.interfaces import ObjectiveFunction


class WeightedSumObjective(SimulationBasedObjective):
    """Multi-objective optimization using weighted sum scalarization.

    This objective combines multiple objectives into a single scalar objective
    using weighted sum: f(x) = Σ(wi * fi(x))

    The weighted sum approach is simple but has limitations:
    - Cannot find non-convex portions of Pareto frontier
    - Weight selection can be difficult
    - Scale differences between objectives matter
    """

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 objectives: List[ObjectiveFunction],
                 weights: Optional[List[float]] = None,
                 normalization: str = 'none',
                 reference_values: Optional[List[float]] = None,
                 reference_trajectory: Optional[np.ndarray] = None):
        """Initialize weighted sum multi-objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration parameters
        controller_factory : callable
            Function to create controller from parameters
        objectives : list of ObjectiveFunction
            List of objective functions to combine
        weights : list of float, optional
            Weights for each objective (default: equal weights)
        normalization : str, default='none'
            Normalization method: 'none', 'min_max', 'reference', 'adaptive'
        reference_values : list of float, optional
            Reference values for normalization
        reference_trajectory : np.ndarray, optional
            Reference trajectory passed to sub-objectives
        """
        super().__init__(simulation_config, controller_factory, reference_trajectory)

        if not objectives:
            raise ValueError("At least one objective function must be provided")

        self.objectives = objectives
        self.n_objectives = len(objectives)

        # Set default weights
        if weights is None:
            self.weights = np.ones(self.n_objectives) / self.n_objectives
        else:
            if len(weights) != self.n_objectives:
                raise ValueError("Number of weights must match number of objectives")
            self.weights = np.array(weights)
            # Normalize weights to sum to 1
            if np.sum(self.weights) > 0:
                self.weights = self.weights / np.sum(self.weights)

        self.normalization = normalization.lower()
        self.reference_values = reference_values

        # Validate normalization method
        valid_normalizations = ['none', 'min_max', 'reference', 'adaptive']
        if self.normalization not in valid_normalizations:
            raise ValueError(f"normalization must be one of {valid_normalizations}")

        # Initialize normalization parameters
        self._min_values = None
        self._max_values = None
        self._evaluation_history = []

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute weighted sum objective from simulation results."""
        # Evaluate all objectives
        objective_values = []

        for i, objective in enumerate(self.objectives):
            try:
                if hasattr(objective, '_compute_objective_from_simulation'):
                    # Simulation-based objective
                    value = objective._compute_objective_from_simulation(times, states, controls, **kwargs)
                elif hasattr(objective, 'evaluate'):
                    # Parameter-based objective
                    parameters = kwargs.get('controller_parameters', np.array([]))
                    value = objective.evaluate(parameters, **kwargs)
                else:
                    warnings.warn(f"Objective {i} does not have expected evaluation methods")
                    value = 0.0

                objective_values.append(value)

            except Exception as e:
                warnings.warn(f"Evaluation of objective {i} failed: {e}")
                objective_values.append(float('inf'))  # High penalty for failed objectives

        objective_values = np.array(objective_values)

        # Store for adaptive normalization
        if self.normalization == 'adaptive':
            self._evaluation_history.append(objective_values.copy())
            if len(self._evaluation_history) > 1000:  # Limit history size
                self._evaluation_history = self._evaluation_history[-1000:]

        # Normalize objectives
        normalized_values = self._normalize_objectives(objective_values)

        # Compute weighted sum
        weighted_sum = np.dot(self.weights, normalized_values)

        return weighted_sum

    def _normalize_objectives(self, objective_values: np.ndarray) -> np.ndarray:
        """Normalize objective values based on selected method."""
        if self.normalization == 'none':
            return objective_values

        elif self.normalization == 'reference':
            if self.reference_values is None:
                warnings.warn("Reference normalization requested but no reference values provided")
                return objective_values

            ref_values = np.array(self.reference_values)
            if len(ref_values) != self.n_objectives:
                warnings.warn("Number of reference values does not match number of objectives")
                return objective_values

            # Normalize by reference values
            normalized = np.zeros_like(objective_values)
            for i in range(self.n_objectives):
                if abs(ref_values[i]) > 1e-12:
                    normalized[i] = objective_values[i] / ref_values[i]
                else:
                    normalized[i] = objective_values[i]

            return normalized

        elif self.normalization == 'min_max':
            # Update min/max values
            if self._min_values is None:
                self._min_values = objective_values.copy()
                self._max_values = objective_values.copy()
            else:
                self._min_values = np.minimum(self._min_values, objective_values)
                self._max_values = np.maximum(self._max_values, objective_values)

            # Normalize to [0, 1]
            normalized = np.zeros_like(objective_values)
            for i in range(self.n_objectives):
                range_i = self._max_values[i] - self._min_values[i]
                if range_i > 1e-12:
                    normalized[i] = (objective_values[i] - self._min_values[i]) / range_i
                else:
                    normalized[i] = 0.0

            return normalized

        elif self.normalization == 'adaptive':
            if len(self._evaluation_history) < 2:
                return objective_values

            # Use statistics from evaluation history
            history_array = np.array(self._evaluation_history)
            means = np.mean(history_array, axis=0)
            stds = np.std(history_array, axis=0)

            # Normalize by (value - mean) / std
            normalized = np.zeros_like(objective_values)
            for i in range(self.n_objectives):
                if stds[i] > 1e-12:
                    normalized[i] = (objective_values[i] - means[i]) / stds[i]
                else:
                    normalized[i] = objective_values[i] - means[i]

            return normalized

        else:
            return objective_values

    def evaluate_objectives_separately(self,
                                     times: np.ndarray,
                                     states: np.ndarray,
                                     controls: np.ndarray,
                                     **kwargs) -> Dict[str, float]:
        """Evaluate all objectives separately and return detailed results.

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
            Dictionary with individual objective values and combined result
        """
        results = {}

        # Evaluate individual objectives
        objective_values = []
        for i, objective in enumerate(self.objectives):
            try:
                if hasattr(objective, '_compute_objective_from_simulation'):
                    value = objective._compute_objective_from_simulation(times, states, controls, **kwargs)
                elif hasattr(objective, 'evaluate'):
                    parameters = kwargs.get('controller_parameters', np.array([]))
                    value = objective.evaluate(parameters, **kwargs)
                else:
                    value = 0.0

                objective_values.append(value)
                results[f'objective_{i}'] = value

                # Add objective name if available
                if hasattr(objective, '__class__'):
                    results[f'objective_{i}_name'] = objective.__class__.__name__

            except Exception as e:
                objective_values.append(float('inf'))
                results[f'objective_{i}'] = float('inf')
                results[f'objective_{i}_error'] = str(e)

        # Normalize and combine
        objective_values = np.array(objective_values)
        normalized_values = self._normalize_objectives(objective_values)
        weighted_sum = np.dot(self.weights, normalized_values)

        # Store results
        results['objective_values'] = objective_values.tolist()
        results['normalized_values'] = normalized_values.tolist()
        results['weights'] = self.weights.tolist()
        results['weighted_sum'] = weighted_sum

        return results

    def update_weights(self, new_weights: List[float]) -> None:
        """Update objective weights.

        Parameters
        ----------
        new_weights : list of float
            New weights for objectives
        """
        if len(new_weights) != self.n_objectives:
            raise ValueError("Number of weights must match number of objectives")

        self.weights = np.array(new_weights)
        if np.sum(self.weights) > 0:
            self.weights = self.weights / np.sum(self.weights)

    def get_objective_info(self) -> Dict[str, Any]:
        """Get information about the multi-objective setup.

        Returns
        -------
        dict
            Information about objectives and configuration
        """
        info = {
            'n_objectives': self.n_objectives,
            'weights': self.weights.tolist(),
            'normalization': self.normalization,
            'reference_values': self.reference_values
        }

        # Add objective names if available
        objective_names = []
        for obj in self.objectives:
            if hasattr(obj, '__class__'):
                objective_names.append(obj.__class__.__name__)
            else:
                objective_names.append('UnknownObjective')

        info['objective_names'] = objective_names

        # Add normalization statistics if available
        if self._min_values is not None:
            info['min_values'] = self._min_values.tolist()
            info['max_values'] = self._max_values.tolist()

        if self.normalization == 'adaptive' and self._evaluation_history:
            history_array = np.array(self._evaluation_history)
            info['adaptive_means'] = np.mean(history_array, axis=0).tolist()
            info['adaptive_stds'] = np.std(history_array, axis=0).tolist()

        return info

    def perform_weight_sensitivity_analysis(self,
                                          times: np.ndarray,
                                          states: np.ndarray,
                                          controls: np.ndarray,
                                          n_samples: int = 10,
                                          **kwargs) -> Dict[str, Any]:
        """Perform sensitivity analysis for different weight combinations.

        Parameters
        ----------
        times : np.ndarray
            Time vector
        states : np.ndarray
            State trajectory
        controls : np.ndarray
            Control trajectory
        n_samples : int, default=10
            Number of random weight combinations to test

        Returns
        -------
        dict
            Sensitivity analysis results
        """
        original_weights = self.weights.copy()
        sensitivity_results = []

        try:
            # Generate random weight combinations
            np.random.seed(42)  # For reproducibility
            for i in range(n_samples):
                # Generate random weights
                random_weights = np.random.dirichlet(np.ones(self.n_objectives))
                self.update_weights(random_weights)

                # Evaluate with new weights
                result = self.evaluate_objectives_separately(times, states, controls, **kwargs)
                result['weight_combination'] = random_weights.tolist()
                sensitivity_results.append(result)

            # Analyze sensitivity
            analysis = self._analyze_weight_sensitivity(sensitivity_results)

        finally:
            # Restore original weights
            self.weights = original_weights

        return {
            'sensitivity_results': sensitivity_results,
            'analysis': analysis,
            'original_weights': original_weights.tolist()
        }

    def _analyze_weight_sensitivity(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze weight sensitivity results."""
        if not results:
            return {}

        # Extract weighted sums and objective values
        weighted_sums = [r['weighted_sum'] for r in results]
        objective_matrices = np.array([r['objective_values'] for r in results])

        analysis = {
            'weighted_sum_range': [float(np.min(weighted_sums)), float(np.max(weighted_sums))],
            'weighted_sum_std': float(np.std(weighted_sums)),
            'objective_value_ranges': [],
            'objective_value_stds': []
        }

        # Per-objective analysis
        for i in range(self.n_objectives):
            obj_values = objective_matrices[:, i]
            analysis['objective_value_ranges'].append([float(np.min(obj_values)), float(np.max(obj_values))])
            analysis['objective_value_stds'].append(float(np.std(obj_values)))

        return analysis


class AdaptiveWeightedSumObjective(WeightedSumObjective):
    """Adaptive weighted sum that automatically adjusts weights based on objective performance.

    This variant automatically adjusts weights based on:
    - Objective value ranges (give more weight to objectives with larger ranges)
    - Convergence behavior (reduce weight for objectives that aren't improving)
    - Performance trends (adapt based on optimization progress)
    """

    def __init__(self, *args, adaptation_rate: float = 0.1, **kwargs):
        """Initialize adaptive weighted sum objective.

        Parameters
        ----------
        adaptation_rate : float, default=0.1
            Rate at which weights are adapted (0 = no adaptation, 1 = full adaptation)
        """
        super().__init__(*args, **kwargs)
        self.adaptation_rate = adaptation_rate
        self._weight_history = [self.weights.copy()]
        self._performance_history = []

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute weighted sum with adaptive weights."""
        # Get base result
        weighted_sum = super()._compute_objective_from_simulation(times, states, controls, **kwargs)

        # Adapt weights based on performance
        if len(self._evaluation_history) > 1:
            self._adapt_weights()

        return weighted_sum

    def _adapt_weights(self):
        """Adapt weights based on objective performance."""
        if len(self._evaluation_history) < 2:
            return

        # Get recent objective values
        recent_values = np.array(self._evaluation_history[-10:])  # Last 10 evaluations

        # Compute objective ranges (for normalization-based adaptation)
        obj_ranges = np.ptp(recent_values, axis=0)  # Peak-to-peak (max - min)

        # Compute objective improvement trends
        if len(recent_values) >= 3:
            trends = []
            for i in range(self.n_objectives):
                # Linear trend analysis
                x = np.arange(len(recent_values))
                y = recent_values[:, i]
                coeffs = np.polyfit(x, y, 1)
                trends.append(abs(coeffs[0]))  # Slope magnitude

            trends = np.array(trends)
        else:
            trends = np.ones(self.n_objectives)

        # Adapt weights based on ranges and trends
        # Give more weight to objectives with larger ranges and better trends
        range_weights = obj_ranges / (np.sum(obj_ranges) + 1e-12)
        trend_weights = trends / (np.sum(trends) + 1e-12)

        # Combine adaptation signals
        adaptation_signal = 0.5 * range_weights + 0.5 * trend_weights

        # Update weights with learning rate
        new_weights = ((1 - self.adaptation_rate) * self.weights +
                      self.adaptation_rate * adaptation_signal)

        # Normalize
        self.weights = new_weights / np.sum(new_weights)
        self._weight_history.append(self.weights.copy())

    def get_adaptation_info(self) -> Dict[str, Any]:
        """Get information about weight adaptation."""
        info = super().get_objective_info()

        info['adaptation_rate'] = self.adaptation_rate
        info['weight_history'] = [w.tolist() for w in self._weight_history]

        if len(self._weight_history) > 1:
            # Compute weight changes
            weight_changes = []
            for i in range(1, len(self._weight_history)):
                change = np.linalg.norm(self._weight_history[i] - self._weight_history[i-1])
                weight_changes.append(change)

            info['weight_change_history'] = weight_changes
            info['total_weight_change'] = sum(weight_changes)

        return info