#==========================================================================================\\
#=============== src/optimization/objectives/multi/pareto.py ========================\\
#==========================================================================================\\

"""Pareto-based multi-objective optimization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, Tuple
import numpy as np
import warnings

from ..base import SimulationBasedObjective
from ...core.interfaces import ObjectiveFunction


class ParetoObjective(SimulationBasedObjective):
    """Multi-objective optimization using Pareto dominance.

    This objective handles true multi-objective optimization by maintaining
    a Pareto frontier of non-dominated solutions. Unlike weighted sum approaches,
    this can find solutions on non-convex portions of the Pareto frontier.

    The objective returns a composite metric but also maintains detailed
    Pareto analysis for optimization algorithms that can handle it.
    """

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 objectives: List[ObjectiveFunction],
                 scalarization_method: str = 'hypervolume',
                 reference_point: Optional[List[float]] = None,
                 normalization: str = 'adaptive',
                 reference_trajectory: Optional[np.ndarray] = None):
        """Initialize Pareto multi-objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration parameters
        controller_factory : callable
            Function to create controller from parameters
        objectives : list of ObjectiveFunction
            List of objective functions to optimize
        scalarization_method : str, default='hypervolume'
            Method to convert Pareto metrics to scalar: 'hypervolume', 'crowding', 'epsilon'
        reference_point : list of float, optional
            Reference point for hypervolume calculation
        normalization : str, default='adaptive'
            Normalization method: 'none', 'min_max', 'adaptive'
        reference_trajectory : np.ndarray, optional
            Reference trajectory passed to sub-objectives
        """
        super().__init__(simulation_config, controller_factory, reference_trajectory)

        if not objectives:
            raise ValueError("At least one objective function must be provided")

        self.objectives = objectives
        self.n_objectives = len(objectives)
        self.scalarization_method = scalarization_method.lower()
        self.reference_point = reference_point
        self.normalization = normalization.lower()

        # Validate scalarization method
        valid_methods = ['hypervolume', 'crowding', 'epsilon', 'weighted_sum']
        if self.scalarization_method not in valid_methods:
            raise ValueError(f"scalarization_method must be one of {valid_methods}")

        # Initialize Pareto frontier storage
        self._pareto_solutions = []
        self._pareto_objectives = []
        self._evaluation_history = []
        self._normalization_bounds = None

        # Set default reference point for hypervolume
        if self.reference_point is None:
            self.reference_point = [1.0] * self.n_objectives

    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute Pareto-based objective from simulation results."""
        # Evaluate all objectives
        objective_values = []

        for i, objective in enumerate(self.objectives):
            try:
                if hasattr(objective, '_compute_objective_from_simulation'):
                    value = objective._compute_objective_from_simulation(times, states, controls, **kwargs)
                elif hasattr(objective, 'evaluate'):
                    parameters = kwargs.get('controller_parameters', np.array([]))
                    value = objective.evaluate(parameters, **kwargs)
                else:
                    warnings.warn(f"Objective {i} does not have expected evaluation methods")
                    value = 0.0

                objective_values.append(value)

            except Exception as e:
                warnings.warn(f"Evaluation of objective {i} failed: {e}")
                objective_values.append(float('inf'))

        objective_values = np.array(objective_values)

        # Store current solution
        current_parameters = kwargs.get('controller_parameters', np.array([]))
        self._evaluation_history.append({
            'parameters': current_parameters.copy() if len(current_parameters) > 0 else None,
            'objectives': objective_values.copy(),
            'timestamp': len(self._evaluation_history)
        })

        # Update Pareto frontier
        self._update_pareto_frontier(current_parameters, objective_values)

        # Normalize objectives if needed
        normalized_values = self._normalize_objectives(objective_values)

        # Convert to scalar using selected method
        scalar_value = self._scalarize_objectives(normalized_values)

        return scalar_value

    def _update_pareto_frontier(self, parameters: np.ndarray, objectives: np.ndarray):
        """Update the Pareto frontier with new solution."""
        if len(parameters) == 0:
            return

        # Check if this solution dominates any existing solutions
        dominated_indices = []
        is_dominated = False

        for i, pareto_obj in enumerate(self._pareto_objectives):
            dominance = self._check_dominance(objectives, pareto_obj)

            if dominance == 1:  # New solution dominates existing
                dominated_indices.append(i)
            elif dominance == -1:  # Existing solution dominates new
                is_dominated = True
                break

        # If new solution is not dominated, add it to frontier
        if not is_dominated:
            # Remove dominated solutions
            for idx in sorted(dominated_indices, reverse=True):
                del self._pareto_solutions[idx]
                del self._pareto_objectives[idx]

            # Add new solution
            self._pareto_solutions.append(parameters.copy())
            self._pareto_objectives.append(objectives.copy())

    def _check_dominance(self, obj1: np.ndarray, obj2: np.ndarray) -> int:
        """Check dominance relationship between two objective vectors.

        Returns:
        -------
        int
            1 if obj1 dominates obj2, -1 if obj2 dominates obj1, 0 if non-dominated
        """
        # Assuming minimization for all objectives
        better_count = 0
        worse_count = 0

        for i in range(len(obj1)):
            if obj1[i] < obj2[i]:
                better_count += 1
            elif obj1[i] > obj2[i]:
                worse_count += 1

        if better_count > 0 and worse_count == 0:
            return 1  # obj1 dominates obj2
        elif worse_count > 0 and better_count == 0:
            return -1  # obj2 dominates obj1
        else:
            return 0  # Non-dominated

    def _normalize_objectives(self, objective_values: np.ndarray) -> np.ndarray:
        """Normalize objective values."""
        if self.normalization == 'none':
            return objective_values

        elif self.normalization == 'adaptive':
            if len(self._evaluation_history) < 2:
                return objective_values

            # Use statistics from evaluation history
            all_objectives = np.array([eval_data['objectives'] for eval_data in self._evaluation_history])
            mins = np.min(all_objectives, axis=0)
            maxs = np.max(all_objectives, axis=0)

            # Normalize to [0, 1]
            normalized = np.zeros_like(objective_values)
            for i in range(self.n_objectives):
                range_i = maxs[i] - mins[i]
                if range_i > 1e-12:
                    normalized[i] = (objective_values[i] - mins[i]) / range_i
                else:
                    normalized[i] = 0.0

            return normalized

        elif self.normalization == 'min_max':
            if self._normalization_bounds is None:
                self._normalization_bounds = {
                    'mins': objective_values.copy(),
                    'maxs': objective_values.copy()
                }
            else:
                self._normalization_bounds['mins'] = np.minimum(
                    self._normalization_bounds['mins'], objective_values)
                self._normalization_bounds['maxs'] = np.maximum(
                    self._normalization_bounds['maxs'], objective_values)

            # Normalize to [0, 1]
            normalized = np.zeros_like(objective_values)
            for i in range(self.n_objectives):
                range_i = self._normalization_bounds['maxs'][i] - self._normalization_bounds['mins'][i]
                if range_i > 1e-12:
                    normalized[i] = ((objective_values[i] - self._normalization_bounds['mins'][i]) / range_i)
                else:
                    normalized[i] = 0.0

            return normalized

        else:
            return objective_values

    def _scalarize_objectives(self, objectives: np.ndarray) -> float:
        """Convert multi-objective values to scalar."""
        if self.scalarization_method == 'hypervolume':
            return self._compute_hypervolume_contribution(objectives)

        elif self.scalarization_method == 'crowding':
            return self._compute_crowding_distance(objectives)

        elif self.scalarization_method == 'epsilon':
            return self._compute_epsilon_indicator(objectives)

        elif self.scalarization_method == 'weighted_sum':
            # Equal weights for simplicity
            weights = np.ones(self.n_objectives) / self.n_objectives
            return np.dot(weights, objectives)

        else:
            # Default to weighted sum
            return np.mean(objectives)

    def _compute_hypervolume_contribution(self, objectives: np.ndarray) -> float:
        """Compute hypervolume contribution (approximation)."""
        if len(self._pareto_objectives) == 0:
            # First solution - use reference point distance
            ref_point = np.array(self.reference_point[:self.n_objectives])
            return np.prod(np.maximum(0, ref_point - objectives))

        # Simplified hypervolume contribution
        # Better solutions have higher hypervolume contribution (lower return value for minimization)
        dominated_volume = 0.0
        ref_point = np.array(self.reference_point[:self.n_objectives])

        # Volume dominated by this solution
        volume = np.prod(np.maximum(0, ref_point - objectives))

        # Penalty for being dominated by existing solutions
        for pareto_obj in self._pareto_objectives:
            if self._check_dominance(pareto_obj, objectives) == 1:
                dominated_volume += 1.0

        return -(volume - dominated_volume)  # Negative because we minimize

    def _compute_crowding_distance(self, objectives: np.ndarray) -> float:
        """Compute crowding distance metric."""
        if len(self._pareto_objectives) <= 1:
            return -float('inf')  # Infinite crowding distance for boundary solutions

        # Add current objectives to existing Pareto set for distance calculation
        extended_objectives = self._pareto_objectives + [objectives]
        extended_objectives = np.array(extended_objectives)

        n_solutions = len(extended_objectives)
        crowding_distance = 0.0

        # Calculate crowding distance for each objective
        for m in range(self.n_objectives):
            # Sort solutions by objective m
            sorted_indices = np.argsort(extended_objectives[:, m])

            # Find position of current solution
            current_position = np.where(sorted_indices == (n_solutions - 1))[0][0]

            # Boundary solutions have infinite distance
            if current_position == 0 or current_position == n_solutions - 1:
                return -float('inf')

            # Calculate distance to neighbors
            obj_range = extended_objectives[sorted_indices[-1], m] - extended_objectives[sorted_indices[0], m]
            if obj_range > 1e-12:
                distance = (extended_objectives[sorted_indices[current_position + 1], m] -
                           extended_objectives[sorted_indices[current_position - 1], m]) / obj_range
                crowding_distance += distance

        return -crowding_distance  # Negative because we want to maximize crowding distance

    def _compute_epsilon_indicator(self, objectives: np.ndarray) -> float:
        """Compute epsilon indicator metric."""
        if len(self._pareto_objectives) == 0:
            return np.mean(objectives)

        # Epsilon indicator measures minimum epsilon such that current solution
        # epsilon-dominates the reference set (Pareto frontier)
        min_epsilon = 0.0

        for pareto_obj in self._pareto_objectives:
            # For each objective, find required epsilon for domination
            max_ratio = 0.0
            for i in range(self.n_objectives):
                if pareto_obj[i] > 1e-12:
                    ratio = objectives[i] / pareto_obj[i]
                    max_ratio = max(max_ratio, ratio)
                elif objectives[i] > pareto_obj[i]:
                    max_ratio = float('inf')
                    break

            min_epsilon = max(min_epsilon, max_ratio)

        return min_epsilon

    def get_pareto_frontier(self) -> Dict[str, Any]:
        """Get current Pareto frontier information.

        Returns
        -------
        dict
            Pareto frontier data including solutions and objectives
        """
        return {
            'solutions': [sol.copy() for sol in self._pareto_solutions],
            'objectives': [obj.copy() for obj in self._pareto_objectives],
            'n_solutions': len(self._pareto_solutions),
            'frontier_metrics': self._compute_frontier_metrics()
        }

    def _compute_frontier_metrics(self) -> Dict[str, Any]:
        """Compute metrics about the current Pareto frontier."""
        if len(self._pareto_objectives) == 0:
            return {}

        objectives_array = np.array(self._pareto_objectives)

        metrics = {
            'hypervolume': self._compute_frontier_hypervolume(),
            'spread': self._compute_frontier_spread(objectives_array),
            'extent': self._compute_frontier_extent(objectives_array)
        }

        return metrics

    def _compute_frontier_hypervolume(self) -> float:
        """Compute hypervolume of current Pareto frontier."""
        if len(self._pareto_objectives) == 0:
            return 0.0

        # Simplified hypervolume calculation for 2D case
        if self.n_objectives == 2:
            objectives_array = np.array(self._pareto_objectives)
            ref_point = np.array(self.reference_point[:2])

            # Sort by first objective
            sorted_indices = np.argsort(objectives_array[:, 0])
            sorted_objs = objectives_array[sorted_indices]

            hypervolume = 0.0
            for i, obj in enumerate(sorted_objs):
                if i == 0:
                    width = ref_point[0] - obj[0]
                    height = ref_point[1] - obj[1]
                else:
                    width = sorted_objs[i-1, 0] - obj[0]
                    height = ref_point[1] - obj[1]

                if width > 0 and height > 0:
                    hypervolume += width * height

            return hypervolume

        else:
            # For higher dimensions, use approximation
            objectives_array = np.array(self._pareto_objectives)
            ref_point = np.array(self.reference_point[:self.n_objectives])

            total_volume = 0.0
            for obj in objectives_array:
                volume = np.prod(np.maximum(0, ref_point - obj))
                total_volume += volume

            return total_volume / len(self._pareto_objectives)

    def _compute_frontier_spread(self, objectives_array: np.ndarray) -> float:
        """Compute spread (diversity) of Pareto frontier."""
        if len(objectives_array) <= 1:
            return 0.0

        # Average distance between consecutive solutions
        total_distance = 0.0
        for i in range(len(objectives_array) - 1):
            distance = np.linalg.norm(objectives_array[i+1] - objectives_array[i])
            total_distance += distance

        return total_distance / (len(objectives_array) - 1)

    def _compute_frontier_extent(self, objectives_array: np.ndarray) -> float:
        """Compute extent (range) of Pareto frontier."""
        if len(objectives_array) == 0:
            return 0.0

        # Maximum range across all objectives
        max_extent = 0.0
        for i in range(self.n_objectives):
            obj_extent = np.max(objectives_array[:, i]) - np.min(objectives_array[:, i])
            max_extent = max(max_extent, obj_extent)

        return max_extent

    def evaluate_solution_quality(self,
                                 times: np.ndarray,
                                 states: np.ndarray,
                                 controls: np.ndarray,
                                 **kwargs) -> Dict[str, Any]:
        """Evaluate solution quality in multi-objective context.

        Returns
        -------
        dict
            Comprehensive evaluation including Pareto ranking
        """
        # Get individual objective values
        objective_values = []
        for objective in self.objectives:
            try:
                if hasattr(objective, '_compute_objective_from_simulation'):
                    value = objective._compute_objective_from_simulation(times, states, controls, **kwargs)
                elif hasattr(objective, 'evaluate'):
                    parameters = kwargs.get('controller_parameters', np.array([]))
                    value = objective.evaluate(parameters, **kwargs)
                else:
                    value = 0.0
                objective_values.append(value)
            except:
                objective_values.append(float('inf'))

        objective_values = np.array(objective_values)

        # Analyze solution relative to Pareto frontier
        pareto_rank = self._compute_pareto_rank(objective_values)
        crowding_distance = self._compute_crowding_distance(objective_values)

        results = {
            'objective_values': objective_values.tolist(),
            'normalized_values': self._normalize_objectives(objective_values).tolist(),
            'pareto_rank': pareto_rank,
            'crowding_distance': crowding_distance,
            'dominates_count': self._count_dominated_solutions(objective_values),
            'dominated_by_count': self._count_dominating_solutions(objective_values),
            'scalarized_value': self._scalarize_objectives(objective_values)
        }

        # Add objective names if available
        objective_names = []
        for obj in self.objectives:
            if hasattr(obj, '__class__'):
                objective_names.append(obj.__class__.__name__)
            else:
                objective_names.append('UnknownObjective')
        results['objective_names'] = objective_names

        return results

    def _compute_pareto_rank(self, objectives: np.ndarray) -> int:
        """Compute Pareto rank (1 = non-dominated, higher = more dominated)."""
        if len(self._pareto_objectives) == 0:
            return 1

        # Count how many solutions dominate this one
        dominated_by_count = 0
        for pareto_obj in self._pareto_objectives:
            if self._check_dominance(pareto_obj, objectives) == 1:
                dominated_by_count += 1

        return dominated_by_count + 1

    def _count_dominated_solutions(self, objectives: np.ndarray) -> int:
        """Count how many solutions this one dominates."""
        dominated_count = 0
        for pareto_obj in self._pareto_objectives:
            if self._check_dominance(objectives, pareto_obj) == 1:
                dominated_count += 1
        return dominated_count

    def _count_dominating_solutions(self, objectives: np.ndarray) -> int:
        """Count how many solutions dominate this one."""
        dominating_count = 0
        for pareto_obj in self._pareto_objectives:
            if self._check_dominance(pareto_obj, objectives) == 1:
                dominating_count += 1
        return dominating_count

    def reset_pareto_frontier(self):
        """Reset the Pareto frontier and evaluation history."""
        self._pareto_solutions.clear()
        self._pareto_objectives.clear()
        self._evaluation_history.clear()
        self._normalization_bounds = None

    def get_optimization_progress(self) -> Dict[str, Any]:
        """Get optimization progress information."""
        if len(self._evaluation_history) == 0:
            return {}

        progress = {
            'total_evaluations': len(self._evaluation_history),
            'pareto_size': len(self._pareto_solutions),
            'convergence_metrics': self._compute_convergence_metrics()
        }

        # Evolution of frontier size
        frontier_evolution = []
        temp_frontier = []

        for eval_data in self._evaluation_history:
            objectives = eval_data['objectives']

            # Update temporary frontier
            dominated_indices = []
            is_dominated = False

            for i, front_obj in enumerate(temp_frontier):
                dominance = self._check_dominance(objectives, front_obj)
                if dominance == 1:
                    dominated_indices.append(i)
                elif dominance == -1:
                    is_dominated = True
                    break

            if not is_dominated:
                for idx in sorted(dominated_indices, reverse=True):
                    del temp_frontier[idx]
                temp_frontier.append(objectives)

            frontier_evolution.append(len(temp_frontier))

        progress['frontier_size_evolution'] = frontier_evolution

        return progress

    def _compute_convergence_metrics(self) -> Dict[str, Any]:
        """Compute convergence metrics for the optimization."""
        if len(self._evaluation_history) < 10:
            return {}

        # Analyze recent frontier changes
        recent_evaluations = self._evaluation_history[-10:]
        recent_objectives = [eval_data['objectives'] for eval_data in recent_evaluations]

        convergence_metrics = {
            'recent_improvement': self._measure_recent_improvement(recent_objectives),
            'objective_std': np.std(recent_objectives, axis=0).tolist(),
            'frontier_stability': self._measure_frontier_stability()
        }

        return convergence_metrics

    def _measure_recent_improvement(self, recent_objectives: List[np.ndarray]) -> float:
        """Measure improvement in recent evaluations."""
        if len(recent_objectives) < 2:
            return 0.0

        # Compare first and last objective values
        first_objectives = np.array(recent_objectives[0])
        last_objectives = np.array(recent_objectives[-1])

        # Count objectives that improved (decreased for minimization)
        improvements = np.sum(last_objectives < first_objectives)
        return improvements / self.n_objectives

    def _measure_frontier_stability(self) -> float:
        """Measure stability of Pareto frontier."""
        if len(self._evaluation_history) < 20:
            return 0.0

        # Check how many evaluations since last frontier change
        recent_frontier_size = len(self._pareto_solutions)
        evaluations_since_change = 0

        for eval_data in reversed(self._evaluation_history[-20:]):
            evaluations_since_change += 1
            # This is a simplified check - in practice would track actual frontier changes
            if evaluations_since_change > 10:
                break

        return min(1.0, evaluations_since_change / 10.0)