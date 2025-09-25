#==========================================================================================\\\
#======================================= src/plant/__init__.py ===================================\\\
#==========================================================================================\\\

"""
Plant Dynamics and Physical Models for the Double Inverted Pendulum System.

This package provides a modular architecture for DIP dynamics with three implementations:

Modular Architecture:
- Simplified DIP: High-performance simplified dynamics
- Full DIP: High-fidelity complete dynamics
- Low-rank DIP: Reduced-order approximations
- Core components: Shared physics computation, validation, stability
- Configurations: Unified type-safe parameter management

The modular architecture provides:
- Clear separation of concerns
- Comprehensive validation and error handling
- Numerical stability features
- Performance optimizations
- Type safety and documentation
- Unified configuration system with factory patterns
"""

# Note: Legacy models have been removed in favor of the new modular architecture

# New modular architecture (recommended)
from .models.simplified import (
    SimplifiedDIPConfig,
    SimplifiedPhysicsComputer,
    SimplifiedDIPDynamics
)

from .models.full import (
    FullDIPConfig,
    FullFidelityPhysicsComputer,
    FullDIPDynamics
)

from .models.lowrank import (
    LowRankDIPConfig,
    LowRankPhysicsComputer,
    LowRankDIPDynamics
)

from .models.base import (
    DynamicsModel,
    DynamicsResult,
    IntegrationMethod,
    BaseDynamicsModel,
    LinearDynamicsModel
)

from .core import (
    # Physics computation
    DIPPhysicsMatrices,
    SimplifiedDIPPhysicsMatrices,

    # Numerical stability
    NumericalInstabilityError,
    AdaptiveRegularizer,
    MatrixInverter,
    NumericalStabilityMonitor,

    # State validation
    StateValidationError,
    DIPStateValidator,
    MinimalStateValidator
)

from .configurations import (
    BasePhysicsConfig,
    BaseDIPConfig,
    ConfigurationFactory,
    UnifiedConfiguration,
    DIPModelType,
    ConfigurationError,
    ConfigurationWarning,
    PhysicsParameterValidator,
    validate_physics_parameters
)

# Convenient aliases for the most common classes
DoubleInvertedPendulum = SimplifiedDIPDynamics  # New default
DIPConfig = SimplifiedDIPConfig
PhysicsMatrices = DIPPhysicsMatrices

__all__ = [
    # New modular models (recommended)
    "DoubleInvertedPendulum",  # Alias for SimplifiedDIPDynamics
    "SimplifiedDIPDynamics",
    "FullDIPDynamics",
    "LowRankDIPDynamics",

    # Configuration classes
    "DIPConfig",  # Alias for SimplifiedDIPConfig
    "SimplifiedDIPConfig",
    "FullDIPConfig",
    "LowRankDIPConfig",

    # Physics computers
    "SimplifiedPhysicsComputer",
    "FullFidelityPhysicsComputer",
    "LowRankPhysicsComputer",

    # Base classes and interfaces
    "DynamicsModel",
    "DynamicsResult",
    "IntegrationMethod",
    "BaseDynamicsModel",
    "LinearDynamicsModel",

    # Core physics computation
    "PhysicsMatrices",  # Alias for DIPPhysicsMatrices
    "DIPPhysicsMatrices",
    "SimplifiedDIPPhysicsMatrices",

    # Numerical stability
    "NumericalInstabilityError",
    "AdaptiveRegularizer",
    "MatrixInverter",
    "NumericalStabilityMonitor",

    # State validation
    "StateValidationError",
    "DIPStateValidator",
    "MinimalStateValidator",

    # Configuration and validation
    "BasePhysicsConfig",
    "BaseDIPConfig",
    "ConfigurationFactory",
    "UnifiedConfiguration",
    "DIPModelType",
    "ConfigurationError",
    "ConfigurationWarning",
    "PhysicsParameterValidator",
    "validate_physics_parameters"
]