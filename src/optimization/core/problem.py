#==========================================================================================\\\
#========================== src/optimization/core/problem.py ==========================\\\
#==========================================================================================\\\

"""Optimization problem builders and specialized problem types."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Union
import numpy as np

from .interfaces import (
    OptimizationProblem, ObjectiveFunction, ParameterSpace, Constraint, OptimizationType
)
from .parameters import ContinuousParameterSpace


class OptimizationProblemBuilder:
    """Builder for constructing optimization problems."""

    def __init__(self):
        """Initialize problem builder."""
        self._objective = None
        self._parameter_space = None
        self._optimization_type = OptimizationType.MINIMIZATION
        self._constraints = []
        self._name = "Optimization Problem"

    def with_objective(self, objective: ObjectiveFunction) -> 'OptimizationProblemBuilder':
        """Set objective function."""
        self._objective = objective
        return self

    def with_parameter_space(self, parameter_space: ParameterSpace) -> 'OptimizationProblemBuilder':
        """Set parameter space."""
        self._parameter_space = parameter_space
        return self

    def with_bounds(self, lower: np.ndarray, upper: np.ndarray) -> 'OptimizationProblemBuilder':
        """Set parameter bounds (creates continuous parameter space)."""
        self._parameter_space = ContinuousParameterSpace(lower, upper)
        return self

    def minimize(self) -> 'OptimizationProblemBuilder':
        """Set optimization type to minimization."""
        self._optimization_type = OptimizationType.MINIMIZATION
        return self

    def maximize(self) -> 'OptimizationProblemBuilder':
        """Set optimization type to maximization."""
        self._optimization_type = OptimizationType.MAXIMIZATION
        return self

    def with_constraint(self, constraint: Constraint) -> 'OptimizationProblemBuilder':
        """Add constraint."""
        self._constraints.append(constraint)
        return self

    def with_name(self, name: str) -> 'OptimizationProblemBuilder':
        """Set problem name."""
        self._name = name
        return self

    def build(self) -> OptimizationProblem:
        """Build optimization problem."""
        if self._objective is None:
            raise ValueError("Objective function must be specified")
        if self._parameter_space is None:
            raise ValueError("Parameter space must be specified")

        return OptimizationProblem(
            objective=self._objective,
            parameter_space=self._parameter_space,
            optimization_type=self._optimization_type,
            constraints=self._constraints,
            name=self._name
        )


class ControlOptimizationProblem(OptimizationProblem):
    """Specialized optimization problem for control parameter tuning."""

    def __init__(self,
                 objective: ObjectiveFunction,
                 parameter_space: ParameterSpace,
                 controller_factory: Callable,
                 simulation_config: Dict[str, Any],
                 optimization_type: OptimizationType = OptimizationType.MINIMIZATION,
                 constraints: Optional[List[Constraint]] = None,
                 name: str = "Control Optimization Problem"):
        """Initialize control optimization problem.

        Parameters
        ----------
        objective : ObjectiveFunction
            Objective function (e.g., tracking error, energy consumption)
        parameter_space : ParameterSpace
            Controller parameter space
        controller_factory : callable
            Function to create controller from parameters
        simulation_config : dict
            Simulation configuration
        optimization_type : OptimizationType, optional
            Minimization or maximization
        constraints : List[Constraint], optional
            Controller constraints (stability, performance)
        name : str, optional
            Problem name
        """
        super().__init__(objective, parameter_space, optimization_type, constraints, name)
        self.controller_factory = controller_factory
        self.simulation_config = simulation_config

    def create_controller(self, parameters: np.ndarray) -> Any:
        """Create controller from optimization parameters."""
        return self.controller_factory(parameters)

    def simulate_controller(self, parameters: np.ndarray, **kwargs) -> Dict[str, Any]:
        """Simulate controller with given parameters."""
        controller = self.create_controller(parameters)

        # Import simulation functionality
        from ...simulation import run_simulation
        from ...simulation.core import SimulationContext

        # Create simulation context
        context = SimulationContext()
        dynamics_model = context.get_dynamics_model()

        # Run simulation
        sim_config = {**self.simulation_config, **kwargs}
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


class MultiObjectiveProblem(OptimizationProblem):
    """Multi-objective optimization problem."""

    def __init__(self,
                 objectives: List[ObjectiveFunction],
                 parameter_space: ParameterSpace,
                 weights: Optional[np.ndarray] = None,
                 optimization_type: OptimizationType = OptimizationType.MINIMIZATION,
                 constraints: Optional[List[Constraint]] = None,
                 name: str = "Multi-Objective Problem"):
        """Initialize multi-objective problem.

        Parameters
        ----------
        objectives : List[ObjectiveFunction]
            List of objective functions
        parameter_space : ParameterSpace
            Parameter space
        weights : np.ndarray, optional
            Weights for weighted sum approach
        optimization_type : OptimizationType, optional
            Optimization type
        constraints : List[Constraint], optional
            Constraints
        name : str, optional
            Problem name
        """
        # Create combined objective function
        combined_objective = WeightedSumObjective(objectives, weights)

        super().__init__(combined_objective, parameter_space, optimization_type, constraints, name)
        self.objectives = objectives
        self.weights = weights if weights is not None else np.ones(len(objectives)) / len(objectives)

    def evaluate_objectives(self, parameters: np.ndarray) -> List[float]:
        """Evaluate all individual objectives."""
        return [obj.evaluate(parameters) for obj in self.objectives]

    def evaluate_objectives_batch(self, parameters: np.ndarray) -> np.ndarray:
        """Evaluate all objectives for batch of parameters."""
        return np.array([obj.evaluate_batch(parameters) for obj in self.objectives]).T


class WeightedSumObjective(ObjectiveFunction):
    """Weighted sum of multiple objectives."""

    def __init__(self, objectives: List[ObjectiveFunction], weights: Optional[np.ndarray] = None):
        """Initialize weighted sum objective.

        Parameters
        ----------
        objectives : List[ObjectiveFunction]
            List of objective functions
        weights : np.ndarray, optional
            Weights for each objective
        """
        self.objectives = objectives
        self.weights = weights if weights is not None else np.ones(len(objectives)) / len(objectives)
        self._evaluation_count = 0

        if len(self.weights) != len(self.objectives):
            raise ValueError("Number of weights must match number of objectives")

    def evaluate(self, parameters: np.ndarray, **kwargs) -> float:
        """Evaluate weighted sum of objectives."""
        values = [obj.evaluate(parameters, **kwargs) for obj in self.objectives]
        self._evaluation_count += 1
        return float(np.sum(self.weights * values))

    def evaluate_batch(self, parameters: np.ndarray, **kwargs) -> np.ndarray:
        """Evaluate weighted sum for batch of parameters."""
        batch_size = parameters.shape[0]
        all_values = np.zeros((batch_size, len(self.objectives)))

        for i, obj in enumerate(self.objectives):
            all_values[:, i] = obj.evaluate_batch(parameters, **kwargs)

        self._evaluation_count += batch_size
        return np.sum(all_values * self.weights, axis=1)

    @property
    def is_vectorized(self) -> bool:
        """Vectorized if all component objectives are vectorized."""
        return all(obj.is_vectorized for obj in self.objectives)