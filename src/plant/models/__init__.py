#==========================================================================================\\\
#=================================== src/plant/models/__init__.py ============================\\\
#==========================================================================================\\\

"""
Plant Dynamics Models.

Collection of dynamics models for the double inverted pendulum system
organized in a modular architecture for clarity and maintainability.
"""

# Note: Legacy models have been removed in favor of the new modular architecture

# Base classes and interfaces
from .base import (
    DynamicsModel,
    DynamicsResult,
    IntegrationMethod,
    BaseDynamicsModel,
    LinearDynamicsModel
)

# Modular implementations
from .simplified import (
    SimplifiedDIPConfig,
    SimplifiedPhysicsComputer,
    SimplifiedDIPDynamics
)

from .full import (
    FullDIPConfig,
    FullFidelityPhysicsComputer,
    FullDIPDynamics
)

from .lowrank import (
    LowRankDIPConfig,
    LowRankPhysicsComputer,
    LowRankDIPDynamics as ModularLowRankDynamics
)

__all__ = [
    # Base classes
    "DynamicsModel",
    "DynamicsResult",
    "IntegrationMethod",
    "BaseDynamicsModel",
    "LinearDynamicsModel",

    # Modular implementations
    "SimplifiedDIPConfig",
    "SimplifiedPhysicsComputer",
    "SimplifiedDIPDynamics",
    "FullDIPConfig",
    "FullFidelityPhysicsComputer",
    "FullDIPDynamics",
    "LowRankDIPConfig",
    "LowRankPhysicsComputer",
    "ModularLowRankDynamics"
]