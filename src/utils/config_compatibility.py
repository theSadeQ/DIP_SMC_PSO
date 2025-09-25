#==========================================================================================\\\
#======================= src/utils/config_compatibility.py =======================\\\
#==========================================================================================\\\
"""
Configuration compatibility utilities.

This module provides compatibility between dictionary-based and object-based
configuration access patterns, enabling seamless integration between different
configuration systems used throughout the project.
"""

from typing import Dict, Any, Union, Optional
import warnings


class AttributeDictionary:
    """
    Dictionary-like object that supports both dictionary and attribute access.

    This class wraps dictionaries to provide attribute access (obj.key) while
    maintaining dictionary access (obj['key']) for maximum compatibility.
    """

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize with dictionary data.

        Args:
            data: Dictionary to wrap with attribute access
        """
        self._data = data

    def __getattr__(self, name: str) -> Any:
        """Get attribute using dot notation."""
        if name.startswith('_'):
            # Avoid infinite recursion for internal attributes
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __getitem__(self, key: str) -> Any:
        """Get item using dictionary notation."""
        return self._data[key]

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute."""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            if not hasattr(self, '_data'):
                super().__setattr__('_data', {})
            self._data[name] = value

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item using dictionary notation."""
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        """Get value with default."""
        return self._data.get(key, default)

    def keys(self):
        """Get dictionary keys."""
        return self._data.keys()

    def values(self):
        """Get dictionary values."""
        return self._data.values()

    def items(self):
        """Get dictionary items."""
        return self._data.items()

    def to_dict(self) -> Dict[str, Any]:
        """Convert back to plain dictionary."""
        return self._data.copy()

    def __repr__(self) -> str:
        """String representation."""
        return f"AttributeDictionary({self._data})"


def ensure_attribute_access(config: Union[Dict[str, Any], Any]) -> Any:
    """
    Ensure configuration supports attribute access.

    This function takes either a dictionary or an object and ensures that
    the result supports attribute access (obj.key) for compatibility with
    code that expects configuration objects.

    Args:
        config: Configuration as dictionary or object

    Returns:
        Configuration object supporting attribute access
    """
    if config is None:
        return None

    # If it's already an object with the attributes we need, return as-is
    if hasattr(config, '__dict__') and not isinstance(config, dict):
        return config

    # If it's a dictionary, wrap it
    if isinstance(config, dict):
        return AttributeDictionary(config)

    # Otherwise assume it's already compatible
    return config


def ensure_dict_access(config: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
    """
    Ensure configuration is a dictionary.

    This function takes either a dictionary or an object and ensures that
    the result is a plain dictionary for compatibility with code that
    expects dictionary access.

    Args:
        config: Configuration as dictionary or object

    Returns:
        Configuration as dictionary
    """
    if config is None:
        return {}

    # If it's already a dictionary, return as-is
    if isinstance(config, dict):
        return config

    # If it's an AttributeDictionary, extract the data
    if isinstance(config, AttributeDictionary):
        return config.to_dict()

    # If it has a model_dump method (Pydantic), use it
    if hasattr(config, 'model_dump'):
        return config.model_dump()

    # If it has a dict method, use it
    if hasattr(config, 'dict'):
        return config.dict()

    # If it has __dict__, use it
    if hasattr(config, '__dict__'):
        return config.__dict__

    # Last resort: try to convert
    try:
        return dict(config)
    except (TypeError, ValueError):
        warnings.warn(f"Could not convert configuration of type {type(config)} to dictionary")
        return {}


class ConfigCompatibilityMixin:
    """
    Mixin class for components that need configuration compatibility.

    This mixin provides methods to handle both dictionary and object-based
    configurations seamlessly.
    """

    def _ensure_config_compatibility(self, config: Union[Dict[str, Any], Any]) -> Any:
        """Ensure configuration has attribute access."""
        return ensure_attribute_access(config)

    def _ensure_config_dict(self, config: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        """Ensure configuration is a dictionary."""
        return ensure_dict_access(config)


def wrap_physics_config(physics_config: Union[Dict[str, Any], Any]) -> Any:
    """
    Wrap physics configuration for compatibility with plant models.

    This function specifically handles physics configurations that need
    to work with both the configuration loading system and the plant
    model implementations. It also provides parameter name mapping
    and default values for missing parameters.

    Args:
        physics_config: Physics configuration from config loading

    Returns:
        Configuration compatible with plant model requirements
    """
    # Convert to dictionary first
    config_dict = ensure_dict_access(physics_config)

    # Handle parameter name mappings and add missing defaults
    enhanced_config = config_dict.copy()

    # Parameter name mappings
    if 'regularization' in config_dict and 'regularization_alpha' not in config_dict:
        enhanced_config['regularization_alpha'] = config_dict['regularization']

    # Add missing default parameters
    defaults = {
        'regularization_alpha': enhanced_config.get('regularization', 1e-8),
        'max_condition_number': 1e12,
        'min_regularization': 1e-10,
        'use_fixed_regularization': False,
        # Additional parameters needed for full dynamics validation
        'cart_position_limits': (-5.0, 5.0),  # meters
        'cart_velocity_limit': 10.0,  # m/s
        'joint_velocity_limits': 20.0,  # rad/s
        'max_control_force': 200.0,  # N
        'control_rate_limit': 1000.0,  # N/s
        # Full dynamics specific parameters
        'include_coriolis_effects': True,
        'include_centrifugal_effects': True,
        'include_friction': True,
        'include_disturbances': False,
        'nonlinear_effects': True,
        'advanced_integration': True,
        'wind_effects': False
    }

    for key, default_value in defaults.items():
        if key not in enhanced_config:
            enhanced_config[key] = default_value

    # Return as AttributeDictionary for attribute access
    return ensure_attribute_access(enhanced_config)


# Commonly used physics parameters for validation
REQUIRED_PHYSICS_PARAMS = {
    'cart_mass', 'pendulum1_mass', 'pendulum2_mass',
    'pendulum1_length', 'pendulum2_length',
    'pendulum1_com', 'pendulum2_com',
    'pendulum1_inertia', 'pendulum2_inertia',
    'gravity'
}

def validate_physics_config(config: Any) -> bool:
    """
    Validate that physics configuration has required parameters.

    Args:
        config: Configuration to validate

    Returns:
        True if configuration has all required physics parameters
    """
    for param in REQUIRED_PHYSICS_PARAMS:
        if not hasattr(config, param) and (not isinstance(config, dict) or param not in config):
            return False
    return True


def create_minimal_physics_config() -> AttributeDictionary:
    """
    Create a minimal physics configuration with default values.

    Returns:
        Minimal configuration with default physics parameters
    """
    return AttributeDictionary({
        'cart_mass': 1.0,
        'pendulum1_mass': 0.1,
        'pendulum2_mass': 0.1,
        'pendulum1_length': 0.5,
        'pendulum2_length': 0.5,
        'pendulum1_com': 0.25,
        'pendulum2_com': 0.25,
        'pendulum1_inertia': 0.01,
        'pendulum2_inertia': 0.01,
        'gravity': 9.81,
        'regularization_alpha': 1e-8,
        'max_condition_number': 1e12,
        'min_regularization': 1e-10,
        'use_fixed_regularization': False,
    })