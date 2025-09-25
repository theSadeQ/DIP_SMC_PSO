#==========================================================================================\\
#==================== src/optimization/algorithms/base.py =========================\\
#==========================================================================================\\

"""Base classes for optimization algorithms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..core.interfaces import OptimizationProblem, ParameterSpace, OptimizationResult


class OptimizationAlgorithm(ABC):
    """Abstract base class for optimization algorithms.

    This class defines the common interface that all optimization algorithms
    must implement. It provides a standard structure for algorithm initialization,
    execution, and result reporting.
    """

    def __init__(self):
        """Initialize the optimization algorithm."""
        self.name = self.__class__.__name__
        self.is_initialized = False
        self.current_iteration = 0

    @abstractmethod
    def optimize(self,
                problem: OptimizationProblem,
                parameter_space: ParameterSpace,
                **kwargs) -> OptimizationResult:
        """Run the optimization algorithm.

        Parameters
        ----------
        problem : OptimizationProblem
            The optimization problem to solve
        parameter_space : ParameterSpace
            The parameter space to search over
        **kwargs
            Additional algorithm-specific parameters

        Returns
        -------
        OptimizationResult
            The optimization results
        """
        pass

    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the algorithm.

        Returns
        -------
        dict
            Algorithm information including name, parameters, and current state
        """
        return {
            'name': self.name,
            'is_initialized': self.is_initialized,
            'current_iteration': self.current_iteration
        }

    def reset(self):
        """Reset the algorithm to initial state."""
        self.is_initialized = False
        self.current_iteration = 0

    def supports_constraints(self) -> bool:
        """Check if algorithm supports constraints.

        Returns
        -------
        bool
            True if constraints are supported
        """
        return False

    def supports_parallel_evaluation(self) -> bool:
        """Check if algorithm supports parallel function evaluation.

        Returns
        -------
        bool
            True if parallel evaluation is supported
        """
        return False

    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default algorithm parameters.

        Returns
        -------
        dict
            Default parameter values
        """
        return {}


class PopulationBasedAlgorithm(OptimizationAlgorithm):
    """Base class for population-based optimization algorithms.

    This class extends OptimizationAlgorithm with common functionality
    for algorithms that maintain a population of candidate solutions.
    """

    def __init__(self, population_size: int = 50):
        """Initialize population-based algorithm.

        Parameters
        ----------
        population_size : int
            Size of the population
        """
        super().__init__()
        self.population_size = population_size
        self.population = None
        self.generation = 0

    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get algorithm information including population details."""
        info = super().get_algorithm_info()
        info.update({
            'population_size': self.population_size,
            'generation': self.generation,
            'has_population': self.population is not None
        })
        return info

    def reset(self):
        """Reset the algorithm including population."""
        super().reset()
        self.population = None
        self.generation = 0

    def supports_parallel_evaluation(self) -> bool:
        """Population-based algorithms typically support parallel evaluation."""
        return True


class GradientBasedAlgorithm(OptimizationAlgorithm):
    """Base class for gradient-based optimization algorithms.

    This class extends OptimizationAlgorithm with common functionality
    for algorithms that use gradient information.
    """

    def __init__(self, gradient_tolerance: float = 1e-6):
        """Initialize gradient-based algorithm.

        Parameters
        ----------
        gradient_tolerance : float
            Tolerance for gradient convergence
        """
        super().__init__()
        self.gradient_tolerance = gradient_tolerance
        self.current_gradient = None
        self.gradient_evaluations = 0

    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get algorithm information including gradient details."""
        info = super().get_algorithm_info()
        info.update({
            'gradient_tolerance': self.gradient_tolerance,
            'gradient_evaluations': self.gradient_evaluations,
            'has_gradient': self.current_gradient is not None
        })
        return info

    def reset(self):
        """Reset the algorithm including gradient information."""
        super().reset()
        self.current_gradient = None
        self.gradient_evaluations = 0

    def requires_gradients(self) -> bool:
        """Check if algorithm requires analytical gradients.

        Returns
        -------
        bool
            True if analytical gradients are required
        """
        return False