#==========================================================================================\\\
#========================= src/controllers/factory/__init__.py ========================\\\
#==========================================================================================\\\

"""
Controller Factory Package

Provides clean, focused factory interfaces for creating controllers:
- SMC Factory: Type-safe, PSO-optimized interface for 4 core SMC controllers
- Legacy Factory: Backward-compatible factory for existing code

Recommended Usage:
    # Use the clean SMC factory for new code
    from controllers.factory import SMCFactory, SMCType, create_smc_for_pso

    # Use legacy factory only for backward compatibility
    from controllers.factory import create_controller_legacy
"""

# Export the clean SMC factory as primary interface
from .smc_factory import (
    # Core types
    SMCType,
    SMCConfig,
    SMCGainSpec,
    SMCProtocol,
    SMCFactory,

    # PSO convenience functions
    create_smc_for_pso,
    get_gain_bounds_for_pso,
    validate_smc_gains,

    # Specifications
    SMC_GAIN_SPECS
)

# Export legacy factory for backward compatibility
from .legacy_factory import create_controller as create_controller_legacy
from .legacy_factory import create_controller  # Also export with original name
from .legacy_factory import build_controller as build_controller_legacy
from .legacy_factory import build_controller  # Also export with original name
from .legacy_factory import build_all as build_all_legacy
from .legacy_factory import _canonical  # For test compatibility
from .legacy_factory import FactoryConfigurationError, ConfigValueError, UnknownConfigKeyError  # Exception types

# Import the new factory functions from the factory.py module for compatibility
import sys
import os
import importlib.util

# Get the factory.py module path
factory_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'factory.py')

if os.path.exists(factory_py_path):
    spec = importlib.util.spec_from_file_location('factory_module', factory_py_path)
    factory_module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(factory_module)

        # Export the functions from factory.py module
        list_available_controllers = factory_module.list_available_controllers
        get_default_gains = factory_module.get_default_gains
        CONTROLLER_REGISTRY = factory_module.CONTROLLER_REGISTRY
        create_controller_new = factory_module.create_controller
        # Override the legacy create_controller with the new one
        create_controller = factory_module.create_controller

    except Exception as e:
        # Fallback if the factory.py module can't be loaded
        def list_available_controllers():
            """Fallback function when factory.py is not available."""
            return ['classical_smc', 'sta_smc', 'adaptive_smc', 'hybrid_adaptive_sta_smc']

        def get_default_gains(controller_type: str):
            """Fallback function when factory.py is not available."""
            defaults = {
                'classical_smc': [5.0, 5.0, 5.0, 0.5, 0.5, 0.5],
                'sta_smc': [4.0, 4.0, 4.0, 0.4, 0.4, 0.4],
                'adaptive_smc': [10.0, 8.0, 5.0, 4.0, 1.0],
                'hybrid_adaptive_sta_smc': [5.0, 5.0, 5.0, 0.5]
            }
            return defaults.get(controller_type, [1.0, 1.0, 1.0, 1.0])

        CONTROLLER_REGISTRY = {}
        create_controller_new = create_controller

# Add missing deprecation mapping function for backward compatibility
def apply_deprecation_mapping(controller_type: str) -> str:
    """
    Apply deprecation mapping for controller types.

    This function handles mapping of deprecated controller type names
    to their current equivalents for backward compatibility.

    Args:
        controller_type: The controller type string to map

    Returns:
        Mapped controller type string
    """
    # Define deprecation mappings
    deprecation_map = {
        'smc_classical': 'classical_smc',
        'smc_sta': 'sta_smc',
        'smc_adaptive': 'adaptive_smc',
        'smc_sliding': 'sliding_smc',
        'mpc': 'mpc_controller',
        'lqr': 'lqr_controller',
        'pid': 'pid_controller'
    }

    # Return mapped type or original if no mapping exists
    return deprecation_map.get(controller_type, controller_type)

# Clean public API - prioritize new SMC factory
__all__ = [
    # ========================================
    # PRIMARY INTERFACE - Clean SMC Factory
    # ========================================

    # Core types
    "SMCType",
    "SMCConfig",
    "SMCGainSpec",
    "SMCProtocol",
    "SMCFactory",

    # PSO integration
    "create_smc_for_pso",
    "get_gain_bounds_for_pso",
    "validate_smc_gains",

    # Specifications
    "SMC_GAIN_SPECS",

    # ========================================
    # LEGACY COMPATIBILITY
    # ========================================

    "create_controller",          # Original name for backward compatibility
    "create_controller_legacy",
    "build_controller",           # Original name for backward compatibility
    "build_controller_legacy",
    "build_all_legacy",
    "_canonical",                 # For test compatibility
    "apply_deprecation_mapping",  # Deprecation mapping function

    # New factory.py functions for test compatibility
    "list_available_controllers",
    "get_default_gains",
    "CONTROLLER_REGISTRY",
    "create_controller_new",

    # Exception types
    "FactoryConfigurationError",
    "ConfigValueError",
    "UnknownConfigKeyError"
]