#==========================================================================================\\\
#=================== src/plant/configurations/unified_config.py =======================\\\
#==========================================================================================\\\

"""
Unified Configuration System for DIP Models.

Provides a centralized configuration management system that supports
all DIP model types (simplified, full, low-rank) with factory patterns
and automatic configuration selection.
"""

from __future__ import annotations
from typing import Dict, Any, Union, Optional, Type
from enum import Enum
import warnings

from .base_config import BaseDIPConfig, ConfigurationError, ConfigurationWarning


class DIPModelType(Enum):
    """Available DIP model types."""
    SIMPLIFIED = "simplified"
    FULL = "full"
    LOWRANK = "lowrank"
    CONTROLLER = "controller"


class ConfigurationFactory:
    """
    Factory for creating DIP configurations.

    Provides centralized creation and management of configurations
    for different DIP model types with validation and consistency checking.
    """

    # Registry of available configuration classes
    _config_registry: Dict[DIPModelType, Type[BaseDIPConfig]] = {}

    @classmethod
    def register_config(cls, model_type: DIPModelType, config_class: Type[BaseDIPConfig]) -> None:
        """
        Register a configuration class for a model type.

        Args:
            model_type: The model type this configuration supports
            config_class: The configuration class to register
        """
        cls._config_registry[model_type] = config_class

    @classmethod
    def create_config(
        cls,
        model_type: Union[DIPModelType, str],
        config_dict: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> BaseDIPConfig:
        """
        Create a configuration for the specified model type.

        Args:
            model_type: Type of DIP model
            config_dict: Optional configuration dictionary
            **kwargs: Additional configuration parameters

        Returns:
            Configured DIP configuration instance

        Raises:
            ConfigurationError: If model type is not supported or configuration is invalid
        """
        # Convert string to enum if needed
        if isinstance(model_type, str):
            try:
                model_type = DIPModelType(model_type.lower())
            except ValueError:
                raise ConfigurationError(f"Unsupported model type: {model_type}")

        # Get configuration class
        if model_type not in cls._config_registry:
            # Try to import and register the configuration class
            cls._lazy_import_config(model_type)

        if model_type not in cls._config_registry:
            raise ConfigurationError(f"No configuration class registered for {model_type}")

        config_class = cls._config_registry[model_type]

        # Merge config_dict and kwargs
        if config_dict is None:
            config_dict = {}
        config_dict.update(kwargs)

        try:
            if config_dict:
                return config_class.from_dict(config_dict)
            else:
                return config_class.create_default()
        except Exception as e:
            raise ConfigurationError(f"Failed to create {model_type} configuration: {e}")

    @classmethod
    def create_default_config(cls, model_type: Union[DIPModelType, str]) -> BaseDIPConfig:
        """Create default configuration for the specified model type."""
        return cls.create_config(model_type)

    @classmethod
    def create_preset_config(
        cls,
        model_type: Union[DIPModelType, str],
        preset_name: str
    ) -> BaseDIPConfig:
        """
        Create a preset configuration.

        Args:
            model_type: Type of DIP model
            preset_name: Name of the preset configuration

        Returns:
            Configured DIP configuration instance
        """
        preset_configs = cls._get_preset_configs()

        if model_type not in preset_configs:
            raise ConfigurationError(f"No presets available for {model_type}")

        if preset_name not in preset_configs[model_type]:
            available = list(preset_configs[model_type].keys())
            raise ConfigurationError(f"Preset '{preset_name}' not found for {model_type}. Available: {available}")

        preset_dict = preset_configs[model_type][preset_name]
        return cls.create_config(model_type, preset_dict)

    @classmethod
    def get_available_presets(cls, model_type: Union[DIPModelType, str]) -> list[str]:
        """Get list of available preset names for a model type."""
        if isinstance(model_type, str):
            model_type = DIPModelType(model_type.lower())

        preset_configs = cls._get_preset_configs()
        return list(preset_configs.get(model_type, {}).keys())

    @classmethod
    def compare_configurations(
        cls,
        config1: BaseDIPConfig,
        config2: BaseDIPConfig
    ) -> Dict[str, Any]:
        """
        Compare two configurations and return differences.

        Args:
            config1: First configuration
            config2: Second configuration

        Returns:
            Dictionary with comparison results
        """
        dict1 = config1.to_dict()
        dict2 = config2.to_dict()

        differences = {}
        all_keys = set(dict1.keys()) | set(dict2.keys())

        for key in all_keys:
            val1 = dict1.get(key, "NOT_PRESENT")
            val2 = dict2.get(key, "NOT_PRESENT")

            if val1 != val2:
                differences[key] = {
                    'config1': val1,
                    'config2': val2
                }

        return {
            'differences': differences,
            'num_differences': len(differences),
            'config1_type': type(config1).__name__,
            'config2_type': type(config2).__name__
        }

    @classmethod
    def validate_configuration(cls, config: BaseDIPConfig) -> Dict[str, Any]:
        """
        Comprehensive validation of a configuration.

        Args:
            config: Configuration to validate

        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'consistency_checks': {},
            'physical_parameters': {},
            'numerical_parameters': {},
            'system_scales': {}
        }

        try:
            # Basic validation
            validation_results['is_valid'] = config.validate()

            # Consistency checks
            validation_results['consistency_checks'] = config.check_physical_consistency()

            # Parameter extraction
            validation_results['physical_parameters'] = config.get_physical_parameters()
            validation_results['numerical_parameters'] = config.get_numerical_parameters()

            # System scales
            validation_results['system_scales'] = config.get_system_scales()

            # Check for warnings
            failed_checks = [k for k, v in validation_results['consistency_checks'].items() if not v]
            if failed_checks:
                validation_results['warnings'].append(f"Failed consistency checks: {failed_checks}")

        except Exception as e:
            validation_results['is_valid'] = False
            validation_results['errors'].append(str(e))

        return validation_results

    @classmethod
    def _lazy_import_config(cls, model_type: DIPModelType) -> None:
        """Lazy import configuration classes."""
        try:
            if model_type == DIPModelType.SIMPLIFIED:
                from ..models.simplified.config import SimplifiedDIPConfig
                cls.register_config(DIPModelType.SIMPLIFIED, SimplifiedDIPConfig)

            elif model_type == DIPModelType.FULL:
                from ..models.full.config import FullDIPConfig
                cls.register_config(DIPModelType.FULL, FullDIPConfig)

            elif model_type == DIPModelType.LOWRANK:
                from ..models.lowrank.config import LowRankDIPConfig
                cls.register_config(DIPModelType.LOWRANK, LowRankDIPConfig)

            elif model_type == DIPModelType.CONTROLLER:
                # Import controller configuration class
                cls._import_controller_config()

        except ImportError as e:
            warnings.warn(f"Could not import configuration for {model_type}: {e}", ConfigurationWarning)

    @classmethod
    def _import_controller_config(cls) -> None:
        """Import controller configuration class."""
        try:
            from .controller_config import ControllerConfiguration
            cls.register_config(DIPModelType.CONTROLLER, ControllerConfiguration)
        except ImportError:
            # Create a basic controller config if the full one doesn't exist
            from .base_config import BaseDIPConfig

            class BasicControllerConfig(BaseDIPConfig):
                def __init__(self, **kwargs):
                    # Default controller settings
                    defaults = {
                        'max_force': 150.0,
                        'dt': 0.001,
                        'boundary_layer': 0.02,
                        'classical_smc_gains': [5.0, 5.0, 5.0, 0.5, 0.5, 0.5],
                        'adaptive_smc_gains': [10.0, 8.0, 5.0, 4.0, 1.0],
                        'sta_smc_gains': [5.0, 3.0, 4.0, 4.0, 0.4, 0.4]
                    }
                    defaults.update(kwargs)
                    for key, value in defaults.items():
                        setattr(self, key, value)

                def validate(self) -> bool:
                    return True

                def to_dict(self) -> Dict[str, Any]:
                    return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

                @classmethod
                def from_dict(cls, config_dict: Dict[str, Any]) -> 'BasicControllerConfig':
                    return cls(**config_dict)

                @classmethod
                def create_default(cls) -> 'BasicControllerConfig':
                    return cls()

                def get_physical_parameters(self) -> Dict[str, float]:
                    return {'max_force': getattr(self, 'max_force', 150.0)}

                def get_numerical_parameters(self) -> Dict[str, float]:
                    return {'dt': getattr(self, 'dt', 0.001), 'boundary_layer': getattr(self, 'boundary_layer', 0.02)}

                def check_physical_consistency(self) -> Dict[str, bool]:
                    return {'max_force_positive': getattr(self, 'max_force', 150.0) > 0}

                def get_system_scales(self) -> Dict[str, float]:
                    return {'force_scale': getattr(self, 'max_force', 150.0)}

            cls.register_config(DIPModelType.CONTROLLER, BasicControllerConfig)

    @classmethod
    def _get_preset_configs(cls) -> Dict[DIPModelType, Dict[str, Dict[str, Any]]]:
        """Get preset configuration dictionaries."""
        return {
            DIPModelType.SIMPLIFIED: {
                'default': {
                    'cart_mass': 1.0,
                    'pendulum1_mass': 0.1,
                    'pendulum2_mass': 0.1,
                    'pendulum1_length': 0.5,
                    'pendulum2_length': 0.5,
                    'gravity': 9.81,
                },
                'educational': {
                    'cart_mass': 1.0,
                    'pendulum1_mass': 0.2,
                    'pendulum2_mass': 0.15,
                    'pendulum1_length': 1.0,
                    'pendulum2_length': 0.8,
                    'gravity': 9.81,
                },
                'lightweight': {
                    'cart_mass': 0.5,
                    'pendulum1_mass': 0.05,
                    'pendulum2_mass': 0.05,
                    'pendulum1_length': 0.3,
                    'pendulum2_length': 0.3,
                    'gravity': 9.81,
                }
            },
            DIPModelType.FULL: {
                'default': {
                    'cart_mass': 1.0,
                    'pendulum1_mass': 0.1,
                    'pendulum2_mass': 0.1,
                    'pendulum1_length': 0.5,
                    'pendulum2_length': 0.5,
                    'pendulum1_com': 0.25,
                    'pendulum2_com': 0.25,
                    'gravity': 9.81,
                },
                'research': {
                    'cart_mass': 2.0,
                    'pendulum1_mass': 0.3,
                    'pendulum2_mass': 0.2,
                    'pendulum1_length': 0.8,
                    'pendulum2_length': 0.6,
                    'pendulum1_com': 0.4,
                    'pendulum2_com': 0.3,
                    'gravity': 9.81,
                },
                'high_precision': {
                    'cart_mass': 1.0,
                    'pendulum1_mass': 0.1,
                    'pendulum2_mass': 0.1,
                    'pendulum1_length': 0.5,
                    'pendulum2_length': 0.5,
                    'pendulum1_com': 0.25,
                    'pendulum2_com': 0.25,
                    'gravity': 9.81,
                }
            },
            DIPModelType.LOWRANK: {
                'default': {
                    'cart_mass': 1.0,
                    'pendulum1_mass': 0.1,
                    'pendulum2_mass': 0.1,
                    'pendulum1_length': 0.5,
                    'pendulum2_length': 0.5,
                    'gravity': 9.81,
                    'enable_linearization': True,
                },
                'fast_prototype': {
                    'cart_mass': 1.0,
                    'pendulum1_mass': 0.1,
                    'pendulum2_mass': 0.1,
                    'pendulum1_length': 0.5,
                    'pendulum2_length': 0.5,
                    'gravity': 9.81,
                    'enable_linearization': True,
                    'enable_small_angle_approximation': True,
                    'enable_fast_math': True,
                },
                'educational': {
                    'cart_mass': 1.0,
                    'pendulum1_mass': 0.2,
                    'pendulum2_mass': 0.1,
                    'pendulum1_length': 1.0,
                    'pendulum2_length': 0.8,
                    'gravity': 9.81,
                    'enable_linearization': False,
                    'enable_small_angle_approximation': False,
                }
            }
        }


class UnifiedConfiguration:
    """
    Unified configuration management for all DIP models.

    Provides a single interface for configuration management across
    different model types with automatic model selection and validation.
    """

    def __init__(
        self,
        model_type: Union[DIPModelType, str],
        config: Optional[Union[BaseDIPConfig, Dict[str, Any]]] = None
    ):
        """
        Initialize unified configuration.

        Args:
            model_type: Type of DIP model
            config: Configuration instance or dictionary
        """
        self.model_type = DIPModelType(model_type) if isinstance(model_type, str) else model_type

        if config is None:
            self.config = ConfigurationFactory.create_default_config(self.model_type)
        elif isinstance(config, dict):
            self.config = ConfigurationFactory.create_config(self.model_type, config)
        elif isinstance(config, BaseDIPConfig):
            self.config = config
        else:
            raise ConfigurationError(f"Invalid configuration type: {type(config)}")

    def validate(self) -> Dict[str, Any]:
        """Validate the current configuration."""
        return ConfigurationFactory.validate_configuration(self.config)

    def update(self, **kwargs: Any) -> None:
        """Update configuration parameters."""
        current_dict = self.config.to_dict()
        current_dict.update(kwargs)
        self.config = ConfigurationFactory.create_config(self.model_type, current_dict)

    def compare_with(self, other: Union['UnifiedConfiguration', BaseDIPConfig]) -> Dict[str, Any]:
        """Compare with another configuration."""
        if isinstance(other, UnifiedConfiguration):
            other_config = other.config
        else:
            other_config = other

        return ConfigurationFactory.compare_configurations(self.config, other_config)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'model_type': self.model_type.value,
            'config': self.config.to_dict()
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'UnifiedConfiguration':
        """Create from dictionary."""
        model_type = config_dict['model_type']
        config = config_dict['config']
        return cls(model_type, config)

    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        validation = self.validate()
        return {
            'model_type': self.model_type.value,
            'configuration_class': type(self.config).__name__,
            'is_valid': validation['is_valid'],
            'physical_parameters': validation['physical_parameters'],
            'numerical_parameters': validation['numerical_parameters'],
            'system_scales': validation['system_scales'],
            'consistency_checks': validation['consistency_checks']
        }