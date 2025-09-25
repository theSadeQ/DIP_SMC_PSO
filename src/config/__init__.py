#==========================================================================================\\\
#=================================== src/config/__init__.py =============================\\\
#==========================================================================================\\\
"""Configuration module for the DIP SMC PSO project."""

# Export main configuration loading functionality
from .loader import load_config, InvalidConfigurationError, ConfigSchema

# Export configuration schemas
from .schemas import (
    PhysicsConfig,
    PhysicsUncertaintySchema,
    SimulationConfig,
    ControllersConfig,
    ControllerConfig,
    PermissiveControllerConfig,
    PSOConfig,
    PSOBounds,
    CostFunctionConfig,
    CostFunctionWeights,
    CombineWeights,
    VerificationConfig,
    SensorsConfig,
    HILConfig,
    FDIConfig,
    StrictModel,
    set_allow_unknown_config,
    redact_value,
)

# Export logging functionality
from .logging import configure_provenance_logging, ProvenanceFilter

# For backward compatibility, also export the legacy namespace
from .schemas import config

__all__ = [
    # Main loader
    "load_config",
    "InvalidConfigurationError",
    "ConfigSchema",

    # Configuration schemas
    "PhysicsConfig",
    "PhysicsUncertaintySchema",
    "SimulationConfig",
    "ControllersConfig",
    "ControllerConfig",
    "PermissiveControllerConfig",
    "PSOConfig",
    "PSOBounds",
    "CostFunctionConfig",
    "CostFunctionWeights",
    "CombineWeights",
    "VerificationConfig",
    "SensorsConfig",
    "HILConfig",
    "FDIConfig",
    "StrictModel",
    "set_allow_unknown_config",
    "redact_value",

    # Logging
    "configure_provenance_logging",
    "ProvenanceFilter",

    # Legacy
    "config",
]