#==========================================================================================\\\
#======================= src/optimization/objectives/base.py =======================\\\
#==========================================================================================\\\

"""Base classes for optimization objective functions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable
import numpy as np

from ..core.interfaces import ObjectiveFunction


class SimulationBasedObjective(ObjectiveFunction):
    """Base class for objectives that require simulation."""

    def __init__(self,
                 simulation_config: Dict[str, Any],
                 controller_factory: Callable,
                 reference_trajectory: Optional[np.ndarray] = None):
        """Initialize simulation-based objective.

        Parameters
        ----------
        simulation_config : dict
            Simulation configuration parameters
        controller_factory : callable
            Function to create controller from parameters
        reference_trajectory : np.ndarray, optional
            Reference trajectory for tracking objectives
        """
        self.simulation_config = simulation_config
        self.controller_factory = controller_factory
        self.reference_trajectory = reference_trajectory
        self._evaluation_count = 0

    @abstractmethod
    def _compute_objective_from_simulation(self,
                                         times: np.ndarray,
                                         states: np.ndarray,
                                         controls: np.ndarray,
                                         **kwargs) -> float:
        """Compute objective value from simulation results."""
        pass

    def evaluate(self, parameters: np.ndarray, **kwargs) -> float:
        """Evaluate objective for single parameter set."""
        # Run simulation
        simulation_result = self._run_simulation(parameters, **kwargs)

        # Compute objective
        objective_value = self._compute_objective_from_simulation(**simulation_result)

        self._evaluation_count += 1
        return objective_value

    def evaluate_batch(self, parameters: np.ndarray, **kwargs) -> np.ndarray:
        """Evaluate objective for batch of parameters."""
        batch_size = parameters.shape[0]
        objectives = np.zeros(batch_size)

        for i, param_set in enumerate(parameters):
            objectives[i] = self.evaluate(param_set, **kwargs)

        return objectives

    def _run_simulation(self, parameters: np.ndarray, **kwargs) -> Dict[str, Any]:
        """Run simulation with given parameters."""
        # Create controller
        controller = self.controller_factory(parameters)

        # Import simulation functionality
        from ...simulation import run_simulation
        from ...simulation.core import SimulationContext

        # Create simulation context
        context = SimulationContext()
        dynamics_model = context.get_dynamics_model()

        # Merge configuration
        sim_config = {**self.simulation_config, **kwargs}

        # Run simulation
        times, states, controls = run_simulation(
            controller=controller,
            dynamics_model=dynamics_model,
            **sim_config
        )

        return {
            'times': times,
            'states': states,
            'controls': controls,
            'controller': controller
        }

    @property
    def is_vectorized(self) -> bool:
        """Simulation-based objectives are not inherently vectorized."""
        return False


class AnalyticalObjective(ObjectiveFunction):
    """Base class for analytical objective functions."""

    def __init__(self):
        """Initialize analytical objective."""
        self._evaluation_count = 0

    @abstractmethod
    def _compute_analytical_objective(self, parameters: np.ndarray) -> Union[float, np.ndarray]:
        """Compute objective analytically."""
        pass

    def evaluate(self, parameters: np.ndarray, **kwargs) -> float:
        """Evaluate objective for single parameter set."""
        value = self._compute_analytical_objective(parameters)
        self._evaluation_count += 1
        return float(value)

    def evaluate_batch(self, parameters: np.ndarray, **kwargs) -> np.ndarray:
        """Evaluate objective for batch of parameters."""
        values = self._compute_analytical_objective(parameters)
        self._evaluation_count += parameters.shape[0]

        if np.isscalar(values):
            return np.full(parameters.shape[0], values)
        return np.asarray(values)

    @property
    def is_vectorized(self) -> bool:
        """Analytical objectives can be vectorized."""
        return True


class CompositeObjective(ObjectiveFunction):
    """Composite objective combining multiple objectives."""

    def __init__(self,
                 objectives: List[ObjectiveFunction],
                 weights: Optional[np.ndarray] = None,
                 combination_method: str = 'weighted_sum'):
        """Initialize composite objective.

        Parameters
        ----------
        objectives : List[ObjectiveFunction]
            List of objective functions to combine
        weights : np.ndarray, optional
            Weights for each objective (default: equal weights)
        combination_method : str, optional
            Method to combine objectives ('weighted_sum', 'product', 'max')
        """
        self.objectives = objectives
        self.weights = weights if weights is not None else np.ones(len(objectives)) / len(objectives)
        self.combination_method = combination_method
        self._evaluation_count = 0

        if len(self.weights) != len(self.objectives):
            raise ValueError("Number of weights must match number of objectives")

    def evaluate(self, parameters: np.ndarray, **kwargs) -> float:
        """Evaluate composite objective."""
        values = [obj.evaluate(parameters, **kwargs) for obj in self.objectives]
        combined_value = self._combine_objectives(values)
        self._evaluation_count += 1
        return combined_value

    def evaluate_batch(self, parameters: np.ndarray, **kwargs) -> np.ndarray:
        """Evaluate composite objective for batch."""
        batch_size = parameters.shape[0]
        all_values = np.zeros((batch_size, len(self.objectives)))

        for i, obj in enumerate(self.objectives):
            all_values[:, i] = obj.evaluate_batch(parameters, **kwargs)

        combined_values = np.array([
            self._combine_objectives(all_values[j])
            for j in range(batch_size)
        ])

        self._evaluation_count += batch_size
        return combined_values

    def _combine_objectives(self, values: List[float]) -> float:
        """Combine objective values according to method."""
        values = np.array(values)

        if self.combination_method == 'weighted_sum':
            return float(np.sum(self.weights * values))

        elif self.combination_method == 'product':
            # Weighted geometric mean
            return float(np.prod(values ** self.weights))

        elif self.combination_method == 'max':
            # Weighted maximum
            return float(np.max(self.weights * values))

        else:
            raise ValueError(f"Unknown combination method: {self.combination_method}")

    @property
    def is_vectorized(self) -> bool:
        """Composite objective is vectorized if all components are."""
        return all(obj.is_vectorized for obj in self.objectives)

    def get_individual_evaluations(self, parameters: np.ndarray, **kwargs) -> List[float]:
        """Get individual objective evaluations."""
        return [obj.evaluate(parameters, **kwargs) for obj in self.objectives]


class PenaltyObjective(ObjectiveFunction):
    """Objective with constraint penalties."""

    def __init__(self,
                 base_objective: ObjectiveFunction,
                 constraints: List[Callable],
                 penalty_factor: float = 1000.0):
        """Initialize penalty objective.

        Parameters
        ----------
        base_objective : ObjectiveFunction
            Base objective function
        constraints : List[Callable]
            List of constraint functions (should return 0 if satisfied, >0 if violated)
        penalty_factor : float, optional
            Penalty factor for constraint violations
        """
        self.base_objective = base_objective
        self.constraints = constraints
        self.penalty_factor = penalty_factor
        self._evaluation_count = 0

    def evaluate(self, parameters: np.ndarray, **kwargs) -> float:
        """Evaluate objective with penalties."""
        base_value = self.base_objective.evaluate(parameters, **kwargs)
        penalty = self._compute_penalty(parameters)
        self._evaluation_count += 1
        return base_value + penalty

    def evaluate_batch(self, parameters: np.ndarray, **kwargs) -> np.ndarray:
        """Evaluate objective with penalties for batch."""
        base_values = self.base_objective.evaluate_batch(parameters, **kwargs)
        penalties = np.array([self._compute_penalty(p) for p in parameters])
        self._evaluation_count += parameters.shape[0]
        return base_values + penalties

    def _compute_penalty(self, parameters: np.ndarray) -> float:
        """Compute constraint penalty."""
        total_violation = 0.0

        for constraint in self.constraints:
            violation = constraint(parameters)
            total_violation += max(0, violation)

        return self.penalty_factor * total_violation

    @property
    def is_vectorized(self) -> bool:
        """Penalty objective inherits vectorization from base."""
        return self.base_objective.is_vectorized