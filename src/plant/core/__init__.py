#==========================================================================================\\\
#=========================== src/plant/core/__init__.py ==============================\\\
#==========================================================================================\\\

"""
Core Plant Components - Shared utilities for plant dynamics.

Provides fundamental building blocks for plant dynamics computation:
- Physics matrix computation (M, C, G matrices)
- Numerical stability and regularization
- State validation and sanitization
- Integration utilities

These components are designed for reuse across different plant models
while maintaining mathematical correctness and numerical robustness.
"""

from .physics_matrices import (
    PhysicsMatrixComputer,
    DIPPhysicsMatrices,
    SimplifiedDIPPhysicsMatrices
)
from .numerical_stability import (
    NumericalInstabilityError,
    MatrixRegularizer,
    AdaptiveRegularizer,
    MatrixInverter,
    fast_condition_estimate,
    NumericalStabilityMonitor
)
from .state_validation import (
    StateValidationError,
    StateValidator,
    DIPStateValidator,
    MinimalStateValidator
)

__all__ = [
    # Physics matrix computation
    "PhysicsMatrixComputer",
    "DIPPhysicsMatrices",
    "SimplifiedDIPPhysicsMatrices",

    # Numerical stability
    "NumericalInstabilityError",
    "MatrixRegularizer",
    "AdaptiveRegularizer",
    "MatrixInverter",
    "fast_condition_estimate",
    "NumericalStabilityMonitor",

    # State validation
    "StateValidationError",
    "StateValidator",
    "DIPStateValidator",
    "MinimalStateValidator"
]