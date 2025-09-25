#==========================================================================================\\\
#======================= src/optimization/core/interfaces.py =======================\\\
#==========================================================================================\\\

"""Core interfaces for professional optimization framework."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
import numpy as np
from enum import Enum


class OptimizationType(Enum):
    """Types of optimization problems."""
    MINIMIZATION = "minimize"
    MAXIMIZATION = "maximize"


class ConvergenceStatus(Enum):
    """Convergence status indicators."""
    CONVERGED = "converged"
    MAX_ITERATIONS = "max_iterations"
    MAX_EVALUATIONS = "max_evaluations"
    TOLERANCE_REACHED = "tolerance_reached"
    USER_TERMINATED = "user_terminated"
    FAILED = "failed"
    RUNNING = "running"


class ParameterSpace(ABC):
    """Abstract base class for parameter spaces."""

    @abstractmethod
    def sample(self, n_samples: int, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        """Sample parameters from the space."""
        pass

    @abstractmethod
    def validate(self, parameters: np.ndarray) -> bool:
        """Validate parameters are within the space."""
        pass

    @abstractmethod
    def clip(self, parameters: np.ndarray) -> np.ndarray:
        """Clip parameters to valid bounds."""
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Number of optimization dimensions."""
        pass

    @property
    @abstractmethod
    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Lower and upper bounds for each parameter."""
        pass


class ObjectiveFunction(ABC):
    """Abstract base class for optimization objective functions."""

    @abstractmethod
    def evaluate(self, parameters: np.ndarray, **kwargs) -> Union[float, np.ndarray]:
        """Evaluate objective function at given parameters.

        Parameters
        ----------
        parameters : np.ndarray
            Parameter vector(s) to evaluate
        **kwargs
            Additional evaluation arguments

        Returns
        -------
        Union[float, np.ndarray]
            Objective value(s)
        """
        pass

    @abstractmethod
    def evaluate_batch(self, parameters: np.ndarray, **kwargs) -> np.ndarray:
        """Evaluate objective function for batch of parameters.

        Parameters
        ----------
        parameters : np.ndarray
            Parameter matrix (n_samples x n_dims)
        **kwargs
            Additional evaluation arguments

        Returns
        -------
        np.ndarray
            Objective values for each parameter set
        """
        pass

    @property
    @abstractmethod
    def is_vectorized(self) -> bool:
        """Whether function supports vectorized evaluation."""
        pass

    @property
    def supports_gradients(self) -> bool:
        """Whether function provides gradient information."""
        return False

    def gradient(self, parameters: np.ndarray, **kwargs) -> np.ndarray:
        """Compute gradient at given parameters."""
        raise NotImplementedError("Gradient not available for this objective")

    @property
    def evaluation_count(self) -> int:
        """Number of function evaluations performed."""
        return getattr(self, '_evaluation_count', 0)

    def reset_evaluation_count(self) -> None:
        """Reset evaluation counter."""
        self._evaluation_count = 0


class Constraint(ABC):
    """Abstract base class for optimization constraints."""

    @abstractmethod
    def evaluate(self, parameters: np.ndarray) -> Union[float, np.ndarray]:
        """Evaluate constraint at given parameters.

        Returns
        -------
        Union[float, np.ndarray]
            Constraint value (0 = satisfied, >0 = violated)
        """
        pass

    @abstractmethod
    def is_satisfied(self, parameters: np.ndarray, tolerance: float = 1e-6) -> bool:
        """Check if constraint is satisfied."""
        pass

    @property
    @abstractmethod
    def constraint_type(self) -> str:
        """Type of constraint ('equality' or 'inequality')."""
        pass


class OptimizationResult:
    """Container for optimization results."""

    def __init__(self,
                 x: np.ndarray,
                 fun: float,
                 success: bool,
                 status: ConvergenceStatus,
                 message: str = "",
                 nit: int = 0,
                 nfev: int = 0,
                 **kwargs):
        """Initialize optimization result.

        Parameters
        ----------
        x : np.ndarray
            Optimal parameter vector
        fun : float
            Optimal objective value
        success : bool
            Whether optimization succeeded
        status : ConvergenceStatus
            Convergence status
        message : str, optional
            Status message
        nit : int, optional
            Number of iterations
        nfev : int, optional
            Number of function evaluations
        **kwargs
            Additional result data
        """
        self.x = x
        self.fun = fun
        self.success = success
        self.status = status
        self.message = message
        self.nit = nit
        self.nfev = nfev

        # Store additional data
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'x': self.x,
            'fun': self.fun,
            'success': self.success,
            'status': self.status.value,
            'message': self.message,
            'nit': self.nit,
            'nfev': self.nfev,
            **{k: v for k, v in self.__dict__.items()
               if k not in ['x', 'fun', 'success', 'status', 'message', 'nit', 'nfev']}
        }


class OptimizationProblem:
    """Complete optimization problem specification."""

    def __init__(self,
                 objective: ObjectiveFunction,
                 parameter_space: ParameterSpace,
                 optimization_type: OptimizationType = OptimizationType.MINIMIZATION,
                 constraints: Optional[List[Constraint]] = None,
                 name: str = "Optimization Problem"):
        """Initialize optimization problem.

        Parameters
        ----------
        objective : ObjectiveFunction
            Objective function to optimize
        parameter_space : ParameterSpace
            Parameter space definition
        optimization_type : OptimizationType, optional
            Minimization or maximization
        constraints : List[Constraint], optional
            Optimization constraints
        name : str, optional
            Problem name
        """
        self.objective = objective
        self.parameter_space = parameter_space
        self.optimization_type = optimization_type
        self.constraints = constraints or []
        self.name = name

    def evaluate_objective(self, parameters: np.ndarray, **kwargs) -> float:
        """Evaluate objective with proper sign handling."""
        value = self.objective.evaluate(parameters, **kwargs)
        if self.optimization_type == OptimizationType.MAXIMIZATION:
            return -value
        return value

    def evaluate_objective_batch(self, parameters: np.ndarray, **kwargs) -> np.ndarray:
        """Evaluate objective batch with proper sign handling."""
        values = self.objective.evaluate_batch(parameters, **kwargs)
        if self.optimization_type == OptimizationType.MAXIMIZATION:
            return -values
        return values

    def check_constraints(self, parameters: np.ndarray) -> Tuple[bool, List[float]]:
        """Check all constraints."""
        violations = []
        satisfied = True

        for constraint in self.constraints:
            violation = constraint.evaluate(parameters)
            violations.append(violation)
            if not constraint.is_satisfied(parameters):
                satisfied = False

        return satisfied, violations


class Optimizer(ABC):
    """Abstract base class for optimization algorithms."""

    def __init__(self, parameter_space: ParameterSpace, **kwargs):
        """Initialize optimizer.

        Parameters
        ----------
        parameter_space : ParameterSpace
            Parameter space to optimize over
        **kwargs
            Algorithm-specific parameters
        """
        self.parameter_space = parameter_space
        self.convergence_monitor = None
        self._callback = None

    @abstractmethod
    def optimize(self, problem: OptimizationProblem, **kwargs) -> OptimizationResult:
        """Perform optimization.

        Parameters
        ----------
        problem : OptimizationProblem
            Problem to optimize
        **kwargs
            Algorithm-specific options

        Returns
        -------
        OptimizationResult
            Optimization results
        """
        pass

    def set_convergence_monitor(self, monitor: 'ConvergenceMonitor') -> None:
        """Set convergence monitor."""
        self.convergence_monitor = monitor

    def set_callback(self, callback: Callable) -> None:
        """Set iteration callback function."""
        self._callback = callback

    @property
    @abstractmethod
    def algorithm_name(self) -> str:
        """Name of the optimization algorithm."""
        pass

    @property
    @abstractmethod
    def supports_constraints(self) -> bool:
        """Whether algorithm supports constraints."""
        pass

    @property
    @abstractmethod
    def supports_bounds(self) -> bool:
        """Whether algorithm supports parameter bounds."""
        pass

    @property
    @abstractmethod
    def is_population_based(self) -> bool:
        """Whether algorithm uses a population of candidates."""
        pass


class ConvergenceMonitor(ABC):
    """Abstract base class for convergence monitoring."""

    @abstractmethod
    def update(self, iteration: int, best_value: float, parameters: np.ndarray, **kwargs) -> None:
        """Update convergence monitor with new iteration data."""
        pass

    @abstractmethod
    def check_convergence(self) -> Tuple[bool, ConvergenceStatus, str]:
        """Check if convergence criteria are met.

        Returns
        -------
        tuple
            (converged, status, message)
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset convergence monitor."""
        pass

    @property
    @abstractmethod
    def convergence_history(self) -> Dict[str, List]:
        """Get convergence history data."""
        pass


class PopulationBasedOptimizer(Optimizer):
    """Base class for population-based optimizers."""

    def __init__(self, parameter_space: ParameterSpace, population_size: int, **kwargs):
        """Initialize population-based optimizer.

        Parameters
        ----------
        parameter_space : ParameterSpace
            Parameter space
        population_size : int
            Size of population
        **kwargs
            Additional parameters
        """
        super().__init__(parameter_space, **kwargs)
        self.population_size = population_size

    @property
    def is_population_based(self) -> bool:
        """Population-based optimizers return True."""
        return True

    @abstractmethod
    def initialize_population(self, rng: np.random.Generator) -> np.ndarray:
        """Initialize population of parameter vectors."""
        pass

    @abstractmethod
    def update_population(self, population: np.ndarray, fitness: np.ndarray, **kwargs) -> np.ndarray:
        """Update population based on fitness values."""
        pass