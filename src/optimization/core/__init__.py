#==========================================================================================\\\
#========================== src/optimization/core/__init__.py ==========================\\\
#==========================================================================================\\\

"""Core optimization framework interfaces and abstractions."""

from .interfaces import (
    Optimizer,
    ObjectiveFunction,
    Constraint,
    OptimizationProblem,
    OptimizationResult,
    ParameterSpace,
    ConvergenceMonitor
)
from .problem import OptimizationProblemBuilder, ControlOptimizationProblem
from .parameters import (
    ParameterBounds,
    ParameterMapping,
    ParameterValidator,
    ContinuousParameter,
    DiscreteParameter,
    ContinuousParameterSpace
)
from .context import OptimizationContext, optimize

__all__ = [
    "Optimizer",
    "ObjectiveFunction",
    "Constraint",
    "OptimizationProblem",
    "OptimizationResult",
    "ParameterSpace",
    "ConvergenceMonitor",
    "OptimizationProblemBuilder",
    "ControlOptimizationProblem",
    "ParameterBounds",
    "ParameterMapping",
    "ParameterValidator",
    "ContinuousParameter",
    "DiscreteParameter",
    "ContinuousParameterSpace",
    "OptimizationContext",
    "optimize"
]