#==========================================================================================\\\
#============================== src/controllers/factory.py =============================\\\
#==========================================================================================\\\
"""
Controller factory for creating control system instances.

This module provides a factory pattern for instantiating different types
of controllers with proper configuration and parameter management.
"""

from typing import Any, Dict, Optional, Union
import numpy as np
import logging

# Import the dynamics models from the compatibility layer
try:
    from ..core.dynamics import DIPDynamics as DoubleInvertedPendulum
except ImportError:
    try:
        from src.core.dynamics import DIPDynamics as DoubleInvertedPendulum
    except ImportError:
        # Fallback for legacy import paths
        try:
            from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics as DoubleInvertedPendulum
        except ImportError:
            raise ImportError("Could not import DoubleInvertedPendulum from any expected location")

# Import controller implementations
from src.controllers.smc.algorithms.classical.controller import ModularClassicalSMC
from src.controllers.smc.algorithms.super_twisting.controller import ModularSuperTwistingSMC
from src.controllers.smc.algorithms.adaptive.controller import ModularAdaptiveSMC
from src.controllers.smc.algorithms.hybrid.controller import ModularHybridSMC

# Import enums needed for configuration
from src.controllers.smc.algorithms.hybrid.config import HybridMode

# Import configuration classes
try:
    from src.controllers.smc.algorithms.classical.config import ClassicalSMCConfig
    from src.controllers.smc.algorithms.super_twisting.config import SuperTwistingSMCConfig as STASMCConfig
    from src.controllers.smc.algorithms.adaptive.config import AdaptiveSMCConfig
    from src.controllers.smc.algorithms.hybrid.config import HybridSMCConfig as HybridAdaptiveSTASMCConfig
except ImportError:
    # Create minimal config classes if the full ones don't exist
    from dataclasses import dataclass

    @dataclass
    class ClassicalSMCConfig:
        gains: list
        max_force: float = 150.0
        boundary_layer: float = 0.02
        boundary_layer_slope: float = 1.0
        switch_method: str = "tanh"
        regularization: float = 1e-6
        dynamics_model: Any = None

        def get_surface_gains(self):
            return self.gains[:4] if len(self.gains) >= 4 else self.gains

        def get_effective_controllability_threshold(self):
            return self.regularization

    @dataclass
    class STASMCConfig:
        gains: list
        max_force: float = 150.0
        damping_gain: float = 0.0
        dt: float = 0.001
        switch_method: str = "tanh"
        dynamics_model: Any = None
        K1: float = 4.0
        K2: float = 0.4
        power_exponent: float = 0.5
        regularization: float = 1e-6

        def get_surface_gains(self):
            return self.gains[:4] if len(self.gains) >= 4 else self.gains

        def get_effective_anti_windup_gain(self):
            return self.damping_gain

    @dataclass
    class AdaptiveSMCConfig:
        gains: list
        max_force: float = 150.0
        leak_rate: float = 0.01
        dead_zone: float = 0.05
        adapt_rate_limit: float = 10.0
        K_min: float = 0.1
        K_max: float = 100.0
        dt: float = 0.001
        smooth_switch: bool = True
        boundary_layer: float = 0.1
        gamma: float = 2.0
        dynamics_model: Any = None

        def get_surface_gains(self):
            return self.gains[:4] if len(self.gains) >= 4 else self.gains

        def get_adaptation_bounds(self):
            return (self.K_min, self.K_max)

    @dataclass
    class HybridAdaptiveSTASMCConfig:
        gains: list
        max_force: float = 150.0
        dt: float = 0.001
        k1_init: float = 4.0
        k2_init: float = 0.4
        gamma1: float = 2.0
        gamma2: float = 0.5
        dead_zone: float = 0.05
        dynamics_model: Any = None

        def get_surface_gains(self):
            return self.gains[:4] if len(self.gains) >= 4 else self.gains


# Map controller names to their implementations and configs
# Alias mapping for backwards compatibility and normalization
ALIAS_MAP = {
    'classic_smc': 'classical_smc',
    'smc_classical': 'classical_smc',
    'smc_v1': 'classical_smc',
    'super_twisting': 'sta_smc',
    'sta': 'sta_smc',
    'adaptive': 'adaptive_smc',
    'hybrid': 'hybrid_adaptive_sta_smc',
    'hybrid_sta': 'hybrid_adaptive_sta_smc',
}

def _canonicalize_controller_type(name: str) -> str:
    """Normalize and alias controller type names.

    - Lowercases and replaces dashes/spaces with underscores
    - Applies common aliases (e.g., classic_smc -> classical_smc)
    """
    if not isinstance(name, str):
        return name
    key = name.strip().lower().replace('-', '_').replace(' ', '_')
    return ALIAS_MAP.get(key, key)
CONTROLLER_REGISTRY = {
    'classical_smc': {
        'class': ModularClassicalSMC,
        'config_class': ClassicalSMCConfig,
        'default_gains': [5.0, 5.0, 5.0, 0.5, 0.5, 0.5]
    },
    'sta_smc': {
        'class': ModularSuperTwistingSMC,
        'config_class': STASMCConfig,
        'default_gains': [5.0, 3.0, 4.0, 4.0, 0.4, 0.4]  # K1=5.0 > K2=3.0 for stability
    },
    'adaptive_smc': {
        'class': ModularAdaptiveSMC,
        'config_class': AdaptiveSMCConfig,
        'default_gains': [10.0, 8.0, 5.0, 4.0, 1.0]
    },
    'hybrid_adaptive_sta_smc': {
        'class': ModularHybridSMC,
        'config_class': HybridAdaptiveSTASMCConfig,
        'default_gains': [5.0, 5.0, 5.0, 0.5]
    }
}


def create_controller(controller_type: str,
                     config: Optional[Any] = None,
                     gains: Optional[Union[list, np.ndarray]] = None) -> Any:
    """
    Create a controller instance of the specified type.

    Args:
        controller_type: Type of controller ('classical_smc', 'sta_smc', etc.)
        config: Configuration object (optional)
        gains: Controller gains array (optional)

    Returns:
        Configured controller instance

    Raises:
        ValueError: If controller_type is not recognized
        ImportError: If required dependencies are missing
    """
    logger = logging.getLogger(__name__)

    # Normalize/alias controller type
    controller_type = _canonicalize_controller_type(controller_type)

    # Validate controller type
    if controller_type not in CONTROLLER_REGISTRY:
        available = list(CONTROLLER_REGISTRY.keys())
        raise ValueError(f"Unknown controller type '{controller_type}'. Available: {available}")

    controller_info = CONTROLLER_REGISTRY[controller_type]
    controller_class = controller_info['class']
    config_class = controller_info['config_class']

    # Determine gains to use
    if gains is not None:
        if isinstance(gains, np.ndarray):
            gains = gains.tolist()
        controller_gains = gains
    else:
        # Try to get gains from config
        if config is not None:
            try:
                # Try different ways to extract gains from config
                if hasattr(config, 'controller_defaults'):
                    controller_gains = getattr(config.controller_defaults.get(controller_type, {}), 'gains', None)
                    if controller_gains is None and isinstance(config.controller_defaults, dict):
                        controller_gains = config.controller_defaults.get(controller_type, {}).get('gains')
                elif hasattr(config, 'controllers'):
                    controller_gains = getattr(config.controllers.get(controller_type, {}), 'gains', None)
                else:
                    controller_gains = None

                if controller_gains is None:
                    controller_gains = controller_info['default_gains']
            except Exception:
                controller_gains = controller_info['default_gains']
        else:
            controller_gains = controller_info['default_gains']

    # Create dynamics model if needed
    dynamics_model = None
    if config is not None:
        try:
            # Try to get existing dynamics model
            if hasattr(config, 'dynamics_model'):
                dynamics_model = config.dynamics_model
            elif hasattr(config, 'physics'):
                dynamics_model = DoubleInvertedPendulum(config.physics)
            elif hasattr(config, 'dip_params'):
                dynamics_model = DoubleInvertedPendulum(config.dip_params)
        except Exception as e:
            logger.warning(f"Could not create dynamics model: {e}")

    # Extract controller-specific parameters from config
    controller_params = {}
    if config is not None:
        try:
            if hasattr(config, 'controllers') and controller_type in config.controllers:
                controller_config = config.controllers[controller_type]
                if hasattr(controller_config, 'model_dump'):
                    controller_params = controller_config.model_dump()
                elif isinstance(controller_config, dict):
                    controller_params = controller_config.copy()
                else:
                    # Extract attributes from config object
                    controller_params = {
                        attr: getattr(controller_config, attr)
                        for attr in dir(controller_config)
                        if not attr.startswith('_') and not callable(getattr(controller_config, attr))
                    }
        except Exception as e:
            logger.warning(f"Could not extract controller parameters: {e}")

    # Create configuration object
    try:
        # Build config parameters based on controller type
        if controller_type == 'hybrid_adaptive_sta_smc':
            # Hybrid controllers require special handling - need sub-configs
            # Import the config classes
            from src.controllers.smc.algorithms.classical.config import ClassicalSMCConfig
            from src.controllers.smc.algorithms.adaptive.config import AdaptiveSMCConfig

            # Create proper sub-configs with all required parameters
            classical_config = ClassicalSMCConfig(
                gains=[5.0, 5.0, 5.0, 0.5, 0.5, 0.5],
                max_force=150.0,
                dt=0.001,
                boundary_layer=0.02
            )
            adaptive_config = AdaptiveSMCConfig(
                gains=[10.0, 8.0, 5.0, 4.0, 1.0],
                max_force=150.0,
                dt=0.001
            )

            config_params = {
                'hybrid_mode': HybridMode.CLASSICAL_ADAPTIVE,  # Default hybrid mode enum
                'dt': 0.001,
                'max_force': 150.0,
                'classical_config': classical_config,
                'adaptive_config': adaptive_config,
                'dynamics_model': dynamics_model,
                **controller_params
            }
        else:
            # Standard controllers use gains
            config_params = {
                'gains': controller_gains,
                'dynamics_model': dynamics_model,
                **controller_params
            }

        # Remove None values and filter to only valid parameters
        config_params = {k: v for k, v in config_params.items() if v is not None}

        controller_config = config_class(**config_params)
    except Exception as e:
        logger.warning(f"Could not create full config, using minimal config: {e}")
        # Fallback to minimal configuration with required defaults
        if controller_type == 'hybrid_adaptive_sta_smc':
            # Hybrid controller has completely different structure
            # Import the config classes
            from src.controllers.smc.algorithms.classical.config import ClassicalSMCConfig
            from src.controllers.smc.algorithms.adaptive.config import AdaptiveSMCConfig

            # Create minimal sub-configs
            classical_config = ClassicalSMCConfig(
                gains=[5.0, 5.0, 5.0, 0.5, 0.5, 0.5],
                max_force=150.0,
                dt=0.001,
                boundary_layer=0.02
            )
            adaptive_config = AdaptiveSMCConfig(
                gains=[10.0, 8.0, 5.0, 4.0, 1.0],
                max_force=150.0,
                dt=0.001
            )

            fallback_params = {
                'hybrid_mode': HybridMode.CLASSICAL_ADAPTIVE,  # Default hybrid mode enum
                'dt': 0.001,
                'max_force': 150.0,
                'classical_config': classical_config,
                'adaptive_config': adaptive_config
            }
        else:
            # Standard controllers use gains
            fallback_params = {
                'gains': controller_gains,
                'max_force': 150.0  # Standard default
            }

            # Only add dynamics_model if not None and controller supports it
            if dynamics_model is not None and controller_type in ['classical_smc', 'sta_smc']:
                fallback_params['dynamics_model'] = dynamics_model

            # Add controller-specific required parameters
            if controller_type == 'classical_smc':
                fallback_params['boundary_layer'] = 0.02
                fallback_params['dt'] = 0.001
            elif controller_type == 'sta_smc':
                fallback_params['dt'] = 0.001
            elif controller_type == 'adaptive_smc':
                fallback_params['dt'] = 0.001

        controller_config = config_class(**fallback_params)

    # Create and return controller instance
    try:
        controller = controller_class(controller_config)
        logger.info(f"Created {controller_type} controller with gains: {controller_gains}")
        return controller
    except Exception as e:
        logger.error(f"Failed to create {controller_type} controller: {e}")
        raise


def list_available_controllers() -> list:
    """
    Get list of available controller types.

    Returns:
        List of controller type names
    """
    return list(CONTROLLER_REGISTRY.keys())


def get_default_gains(controller_type: str) -> list:
    """
    Get default gains for a controller type.

    Args:
        controller_type: Type of controller

    Returns:
        Default gains list

    Raises:
        ValueError: If controller_type is not recognized
    """
    if controller_type not in CONTROLLER_REGISTRY:
        available = list(CONTROLLER_REGISTRY.keys())
        raise ValueError(f"Unknown controller type '{controller_type}'. Available: {available}")

    return CONTROLLER_REGISTRY[controller_type]['default_gains'].copy()


# Backwards compatibility aliases
def create_classical_smc_controller(config=None, gains=None):
    """Create classical SMC controller (backwards compatibility)."""
    return create_controller('classical_smc', config, gains)


def create_sta_smc_controller(config=None, gains=None):
    """Create super-twisting SMC controller (backwards compatibility)."""
    return create_controller('sta_smc', config, gains)


def create_adaptive_smc_controller(config=None, gains=None):
    """Create adaptive SMC controller (backwards compatibility)."""
    return create_controller('adaptive_smc', config, gains)


# Additional backwards compatibility for the existing __init__.py
def create_controller_legacy(controller_type: str, config=None, gains=None):
    """Legacy factory function (backwards compatibility)."""
    return create_controller(controller_type, config, gains)


# Placeholder classes and functions for the existing __init__.py structure
from enum import Enum

class SMCType(Enum):
    """SMC Controller types enumeration."""
    CLASSICAL = "classical_smc"
    ADAPTIVE = "adaptive_smc"
    SUPER_TWISTING = "sta_smc"
    HYBRID = "hybrid_adaptive_sta_smc"


class SMCConfig:
    """Configuration class for SMC controllers."""
    def __init__(self, gains, max_force=150.0, dt=0.001, **kwargs):
        self.gains = gains
        self.max_force = max_force
        self.dt = dt
        for key, value in kwargs.items():
            setattr(self, key, value)


class SMCFactory:
    """Factory class for creating SMC controllers."""

    @staticmethod
    def create_controller(smc_type: SMCType, config: SMCConfig):
        """Create controller using SMCType enum."""
        return create_controller(smc_type.value, config, config.gains)


def create_smc_for_pso(smc_type: SMCType, gains, max_force=150.0, dt=0.001, **kwargs):
    """Create SMC controller optimized for PSO usage."""
    config = SMCConfig(gains=gains, max_force=max_force, dt=dt, **kwargs)
    return SMCFactory.create_controller(smc_type, config)


def get_gain_bounds_for_pso(smc_type: SMCType):
    """Get PSO gain bounds for a controller type."""
    bounds_map = {
        SMCType.CLASSICAL: [(0.1, 50.0)] * 6,  # 6 gains for classical
        SMCType.ADAPTIVE: [(0.1, 50.0)] * 5,   # 5 gains for adaptive
        SMCType.SUPER_TWISTING: [(0.1, 50.0)] * 6,  # 6 gains for STA
        SMCType.HYBRID: [(0.1, 50.0)] * 4,     # 4 gains for hybrid
    }
    return bounds_map.get(smc_type, [(0.1, 50.0)] * 6)


def validate_smc_gains(smc_type: SMCType, gains):
    """Validate gains for a controller type."""
    expected_lengths = {
        SMCType.CLASSICAL: 6,
        SMCType.ADAPTIVE: 5,
        SMCType.SUPER_TWISTING: 6,
        SMCType.HYBRID: 4,
    }
    expected_len = expected_lengths.get(smc_type, 6)
    return len(gains) == expected_len and all(isinstance(g, (int, float)) and g > 0 for g in gains)


# SMC Gain specifications
SMC_GAIN_SPECS = {
    SMCType.CLASSICAL: {
        'count': 6,
        'names': ['c1', 'lambda1', 'c2', 'lambda2', 'K', 'kd'],
        'bounds': [(0.1, 50.0)] * 6,
        'description': 'Classical SMC with sliding surface and switching gains'
    },
    SMCType.ADAPTIVE: {
        'count': 5,
        'names': ['c1', 'lambda1', 'c2', 'lambda2', 'adaptation_rate'],
        'bounds': [(0.1, 50.0)] * 5,
        'description': 'Adaptive SMC with parameter adaptation'
    },
    SMCType.SUPER_TWISTING: {
        'count': 6,
        'names': ['c1', 'lambda1', 'c2', 'lambda2', 'alpha', 'beta'],
        'bounds': [(0.1, 50.0)] * 6,
        'description': 'Super-twisting SMC with second-order sliding mode'
    },
    SMCType.HYBRID: {
        'count': 4,
        'names': ['c1', 'lambda1', 'c2', 'lambda2'],
        'bounds': [(0.1, 50.0)] * 4,
        'description': 'Hybrid adaptive super-twisting SMC'
    }
}
