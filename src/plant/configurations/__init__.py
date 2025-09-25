#==========================================================================================\\\
#====================== src/plant/configurations/__init__.py ===========================\\\
#==========================================================================================\\\

"""
Configuration management for plant dynamics.

Provides type-safe configuration classes with validation for different
plant dynamics models. Ensures physical consistency and mathematical
correctness of system parameters.
"""

from .base_config import (
    BasePhysicsConfig,
    BaseDIPConfig,
    ConfigurationError,
    ConfigurationWarning
)
from .unified_config import (
    ConfigurationFactory,
    UnifiedConfiguration,
    DIPModelType
)
from .validation import (
    ParameterValidator,
    PhysicsParameterValidator,
    validate_physics_parameters
)

__all__ = [
    "BasePhysicsConfig",
    "BaseDIPConfig",
    "ConfigurationError",
    "ConfigurationWarning",
    "ConfigurationFactory",
    "UnifiedConfiguration",
    "DIPModelType",
    "ParameterValidator",
    "PhysicsParameterValidator",
    "validate_physics_parameters"
]