#==========================================================================================\\\
#======================= src/configuration/config_resilient.py ==========================\\\
#==========================================================================================\\\
"""
RESILIENT Configuration Management System - SPOF Elimination
This module eliminates the single config file SPOF by implementing:

1. Multiple configuration sources with automatic failover
2. Configuration redundancy and validation
3. Graceful degradation when config files are corrupted
4. Runtime configuration healing and recovery
5. Built-in default configurations for emergency operation

PRODUCTION SAFETY: System can operate even if config.yaml is deleted or corrupted.
"""

import os
import yaml
import json
import copy
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging


class ConfigSource(Enum):
    """Configuration source types."""
    PRIMARY_FILE = "primary_file"
    BACKUP_FILE = "backup_file"
    ENVIRONMENT = "environment"
    DEFAULTS = "defaults"
    RUNTIME = "runtime"


class ConfigState(Enum):
    """Configuration system state."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"
    FAILED = "failed"


@dataclass
class ConfigHealth:
    """Configuration health status."""
    state: ConfigState = ConfigState.HEALTHY
    last_check: float = field(default_factory=time.time)
    source_status: Dict[ConfigSource, bool] = field(default_factory=dict)
    load_errors: List[str] = field(default_factory=list)
    fallback_count: int = 0

    def update_source_status(self, source: ConfigSource, success: bool, error: str = None):
        """Update status for a configuration source."""
        self.source_status[source] = success
        self.last_check = time.time()

        if not success and error:
            self.load_errors.append(f"{source.value}: {error}")
            # Keep only last 10 errors
            self.load_errors = self.load_errors[-10:]

        # Update overall state
        healthy_sources = sum(1 for status in self.source_status.values() if status)
        total_sources = len(self.source_status)

        if healthy_sources == 0:
            self.state = ConfigState.FAILED
        elif healthy_sources == 1 and ConfigSource.DEFAULTS in self.source_status:
            self.state = ConfigState.EMERGENCY
        elif healthy_sources < total_sources / 2:
            self.state = ConfigState.DEGRADED
        else:
            self.state = ConfigState.HEALTHY


class ResilientConfigManager:
    """
    Production-safe configuration manager with SPOF elimination.

    Features:
    - Multiple configuration sources with automatic failover
    - Built-in defaults for emergency operation
    - Configuration validation and healing
    - Runtime configuration updates
    - Thread-safe operations
    """

    def __init__(self, primary_config_path: str = "config.yaml",
                 backup_config_path: str = "config_backup.yaml"):
        """Initialize resilient configuration manager."""
        self.primary_path = Path(primary_config_path)
        self.backup_path = Path(backup_config_path)

        self._config_data: Dict[str, Any] = {}
        self._config_lock = threading.RLock()

        self._health = ConfigHealth()
        self._health_lock = threading.RLock()

        self._logger = logging.getLogger("resilient_config")

        # Configuration sources (in priority order)
        self._sources = [
            (ConfigSource.PRIMARY_FILE, self._load_from_file, self.primary_path),
            (ConfigSource.BACKUP_FILE, self._load_from_file, self.backup_path),
            (ConfigSource.ENVIRONMENT, self._load_from_environment, None),
            (ConfigSource.DEFAULTS, self._load_defaults, None),
        ]

        # Initialize configuration
        self._load_configuration()

    def get_config(self, key: str = None, default: Any = None) -> Any:
        """Get configuration value with safe access."""
        with self._config_lock:
            if key is None:
                return copy.deepcopy(self._config_data)

            # Support nested keys like "controllers.classical_smc.max_force"
            keys = key.split('.')
            current = self._config_data

            try:
                for k in keys:
                    current = current[k]
                return copy.deepcopy(current)
            except (KeyError, TypeError):
                return default

    def set_config(self, key: str, value: Any, persist: bool = False) -> bool:
        """Set configuration value at runtime."""
        try:
            with self._config_lock:
                keys = key.split('.')
                current = self._config_data

                # Navigate to the parent dictionary
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]

                # Set the value
                current[keys[-1]] = copy.deepcopy(value)

            # Optionally persist to file
            if persist:
                self._save_to_backup()

            self._logger.info(f"Configuration updated: {key} = {value}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to set configuration {key}: {e}")
            return False

    def reload_configuration(self) -> bool:
        """Reload configuration from all sources."""
        return self._load_configuration()

    def get_health_status(self) -> ConfigHealth:
        """Get configuration health status."""
        with self._health_lock:
            return copy.deepcopy(self._health)

    def validate_configuration(self) -> List[str]:
        """Validate current configuration and return any issues."""
        issues = []

        try:
            with self._config_lock:
                config = self._config_data

            # Basic structure validation
            required_sections = ['controllers', 'pso', 'physics', 'simulation']
            for section in required_sections:
                if section not in config:
                    issues.append(f"Missing required section: {section}")

            # Controller validation
            if 'controllers' in config:
                for controller_name, controller_config in config['controllers'].items():
                    if 'max_force' not in controller_config:
                        issues.append(f"Controller {controller_name} missing max_force")
                    elif not isinstance(controller_config['max_force'], (int, float)):
                        issues.append(f"Controller {controller_name} max_force must be numeric")

            # Physics validation
            if 'physics' in config:
                physics = config['physics']
                required_physics = ['cart_mass', 'pendulum1_mass', 'pendulum2_mass', 'gravity']
                for param in required_physics:
                    if param not in physics:
                        issues.append(f"Missing physics parameter: {param}")
                    elif not isinstance(physics[param], (int, float)):
                        issues.append(f"Physics parameter {param} must be numeric")

            # Simulation validation
            if 'simulation' in config:
                sim = config['simulation']
                if 'duration' not in sim or sim['duration'] <= 0:
                    issues.append("Simulation duration must be positive")
                if 'dt' not in sim or sim['dt'] <= 0:
                    issues.append("Simulation timestep (dt) must be positive")

        except Exception as e:
            issues.append(f"Configuration validation error: {e}")

        return issues

    def heal_configuration(self) -> bool:
        """Attempt to heal corrupted configuration."""
        try:
            issues = self.validate_configuration()
            if not issues:
                return True  # Already healthy

            self._logger.info(f"Attempting to heal {len(issues)} configuration issues")

            # Load defaults and merge with current config
            defaults = self._get_default_config()

            with self._config_lock:
                # Merge defaults for missing sections
                for key, default_value in defaults.items():
                    if key not in self._config_data:
                        self._config_data[key] = copy.deepcopy(default_value)
                        self._logger.info(f"Healed missing section: {key}")

            # Save healed configuration
            self._save_to_backup()

            # Re-validate
            remaining_issues = self.validate_configuration()
            healed_count = len(issues) - len(remaining_issues)

            self._logger.info(f"Configuration healing completed: {healed_count} issues resolved")
            return healed_count > 0

        except Exception as e:
            self._logger.error(f"Configuration healing failed: {e}")
            return False

    def create_config_backup(self) -> bool:
        """Create backup of current configuration."""
        try:
            backup_path = self.backup_path
            with self._config_lock:
                config_data = copy.deepcopy(self._config_data)

            # Save as YAML
            with open(backup_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)

            self._logger.info(f"Configuration backup created: {backup_path}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to create configuration backup: {e}")
            return False

    def _load_configuration(self) -> bool:
        """Load configuration from all available sources."""
        loaded_any = False

        with self._health_lock:
            self._health = ConfigHealth()  # Reset health

        for source, load_func, source_path in self._sources:
            try:
                config_data = load_func(source_path)
                if config_data:
                    with self._config_lock:
                        if not loaded_any:
                            # First successful load - use as base
                            self._config_data = copy.deepcopy(config_data)
                            loaded_any = True
                        else:
                            # Subsequent loads - merge missing keys
                            self._merge_config(config_data)

                    with self._health_lock:
                        self._health.update_source_status(source, True)

                    self._logger.info(f"Loaded configuration from {source.value}")

            except Exception as e:
                error_msg = str(e)
                with self._health_lock:
                    self._health.update_source_status(source, False, error_msg)

                self._logger.warning(f"Failed to load from {source.value}: {error_msg}")

        if not loaded_any:
            self._logger.critical("No configuration sources available - system cannot start")
            return False

        # Validate and heal if necessary
        issues = self.validate_configuration()
        if issues:
            self._logger.warning(f"Configuration validation found {len(issues)} issues, attempting to heal")
            self.heal_configuration()

        return True

    def _load_from_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load configuration from YAML file."""
        if not file_path or not file_path.exists():
            return None

        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise Exception(f"Failed to parse {file_path}: {e}")

    def _load_from_environment(self, _) -> Optional[Dict[str, Any]]:
        """Load configuration overrides from environment variables."""
        env_config = {}

        # Map environment variables to config keys
        env_mappings = {
            'DIP_CONTROLLER_MAX_FORCE': 'controllers.classical_smc.max_force',
            'DIP_SIMULATION_DURATION': 'simulation.duration',
            'DIP_SIMULATION_DT': 'simulation.dt',
            'DIP_PSO_N_PARTICLES': 'pso.n_particles',
            'DIP_PSO_ITERATIONS': 'pso.iters',
            'DIP_PHYSICS_CART_MASS': 'physics.cart_mass',
            'DIP_PHYSICS_GRAVITY': 'physics.gravity',
        }

        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    # Try to parse as number
                    if '.' in value:
                        parsed_value = float(value)
                    else:
                        parsed_value = int(value)

                    # Set nested key
                    keys = config_key.split('.')
                    current = env_config
                    for key in keys[:-1]:
                        if key not in current:
                            current[key] = {}
                        current = current[key]
                    current[keys[-1]] = parsed_value

                except ValueError:
                    # Use as string if not numeric
                    keys = config_key.split('.')
                    current = env_config
                    for key in keys[:-1]:
                        if key not in current:
                            current[key] = {}
                        current = current[key]
                    current[keys[-1]] = value

        return env_config if env_config else None

    def _load_defaults(self, _) -> Dict[str, Any]:
        """Load built-in default configuration."""
        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get built-in default configuration (emergency fallback)."""
        return {
            'global_seed': 42,
            'controllers': {
                'classical_smc': {
                    'max_force': 150.0,
                    'boundary_layer': 0.02
                }
            },
            'controller_defaults': {
                'classical_smc': {
                    'gains': [5.0, 5.0, 5.0, 0.5, 0.5, 0.5]
                }
            },
            'pso': {
                'n_particles': 20,
                'bounds': {
                    'min': [1.0, 1.0, 1.0, 1.0, 5.0, 0.1],
                    'max': [100.0, 100.0, 20.0, 20.0, 150.0, 10.0]
                },
                'w': 0.7,
                'c1': 2.0,
                'c2': 2.0,
                'iters': 200,
                'seed': 42
            },
            'physics': {
                'cart_mass': 1.5,
                'pendulum1_mass': 0.2,
                'pendulum2_mass': 0.15,
                'pendulum1_length': 0.4,
                'pendulum2_length': 0.3,
                'pendulum1_com': 0.2,
                'pendulum2_com': 0.15,
                'pendulum1_inertia': 0.00265,
                'pendulum2_inertia': 0.00115,
                'gravity': 9.81,
                'cart_friction': 0.2,
                'joint1_friction': 0.005,
                'joint2_friction': 0.004,
                'singularity_cond_threshold': 100000000.0
            },
            'simulation': {
                'duration': 10.0,
                'dt': 0.01,
                'initial_state': [0.0, 0.05, -0.03, 0.0, 0.0, 0.0],
                'use_full_dynamics': True
            },
            'cost_function': {
                'weights': {
                    'state_error': 50.0,
                    'control_effort': 0.2,
                    'control_rate': 0.1,
                    'stability': 0.1
                },
                'instability_penalty': 1000.0
            },
            'sensors': {
                'angle_noise_std': 0.005,
                'position_noise_std': 0.001,
                'quantization_angle': 0.01,
                'quantization_position': 0.0005
            },
            'hil': {
                'plant_ip': '127.0.0.1',
                'plant_port': 9000,
                'controller_ip': '127.0.0.1',
                'controller_port': 9001,
                'extra_latency_ms': 0.0,
                'sensor_noise_std': 0.0
            }
        }

    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """Merge new configuration with existing, preserving existing values."""
        def merge_dict(target: Dict[str, Any], source: Dict[str, Any]):
            for key, value in source.items():
                if key not in target:
                    target[key] = copy.deepcopy(value)
                elif isinstance(target[key], dict) and isinstance(value, dict):
                    merge_dict(target[key], value)

        merge_dict(self._config_data, new_config)

    def _save_to_backup(self) -> bool:
        """Save current configuration to backup file."""
        try:
            return self.create_config_backup()
        except Exception as e:
            self._logger.error(f"Failed to save configuration backup: {e}")
            return False


# Global resilient config manager (replaceable, not singleton)
_global_config_manager: Optional[ResilientConfigManager] = None
_config_lock = threading.RLock()


def get_config_manager() -> ResilientConfigManager:
    """Get configuration manager (creates if not exists)."""
    global _global_config_manager

    with _config_lock:
        if _global_config_manager is None:
            _global_config_manager = ResilientConfigManager()
        return _global_config_manager


def set_config_manager(manager: ResilientConfigManager) -> None:
    """Replace configuration manager (eliminates singleton dependency)."""
    global _global_config_manager
    with _config_lock:
        _global_config_manager = manager


# Convenience functions (no singleton dependencies)
def get_config(key: str = None, default: Any = None) -> Any:
    """Get configuration value using resilient manager."""
    manager = get_config_manager()
    return manager.get_config(key, default)


def set_config(key: str, value: Any, persist: bool = False) -> bool:
    """Set configuration value using resilient manager."""
    manager = get_config_manager()
    return manager.set_config(key, value, persist)


def reload_config() -> bool:
    """Reload configuration from all sources."""
    manager = get_config_manager()
    return manager.reload_configuration()


def get_config_health() -> ConfigHealth:
    """Get configuration system health."""
    manager = get_config_manager()
    return manager.get_health_status()