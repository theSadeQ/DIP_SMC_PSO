#==========================================================================================\\\
#=================== src/plant/configurations/base_config.py ==========================\\\
#==========================================================================================\\\

"""
Base Configuration Classes for Plant Dynamics.

Provides abstract base classes and common functionality for physics
configuration with validation and type safety.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np


class PhysicsConfig(Protocol):
    """Protocol for physics configuration classes."""

    def validate(self) -> bool:
        """Validate physics parameters."""
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        ...

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'PhysicsConfig':
        """Create from dictionary."""
        ...


@dataclass(frozen=True)
class BasePhysicsConfig(ABC):
    """
    Abstract base class for physics configurations.

    Provides common functionality for validation, serialization,
    and parameter management across different physics models.
    """

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate physics parameters for consistency and physical realizability.

        Returns:
            True if all parameters are valid

        Raises:
            ValueError: If validation fails and strict_validation is enabled
        """
        pass

    @abstractmethod
    def get_physical_parameters(self) -> Dict[str, float]:
        """Get dictionary of physical parameters."""
        pass

    @abstractmethod
    def get_numerical_parameters(self) -> Dict[str, float]:
        """Get dictionary of numerical parameters."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        result = {}
        result.update(self.get_physical_parameters())
        result.update(self.get_numerical_parameters())
        return result

    @classmethod
    @abstractmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BasePhysicsConfig':
        """Create configuration from dictionary."""
        pass

    @classmethod
    @abstractmethod
    def create_default(cls) -> 'BasePhysicsConfig':
        """Create configuration with default parameters."""
        pass

    def get_mass_properties(self) -> Dict[str, float]:
        """Get mass-related parameters."""
        physical_params = self.get_physical_parameters()
        return {k: v for k, v in physical_params.items() if 'mass' in k}

    def get_length_properties(self) -> Dict[str, float]:
        """Get length-related parameters."""
        physical_params = self.get_physical_parameters()
        return {k: v for k, v in physical_params.items() if 'length' in k or 'com' in k}

    def get_inertia_properties(self) -> Dict[str, float]:
        """Get inertia-related parameters."""
        physical_params = self.get_physical_parameters()
        return {k: v for k, v in physical_params.items() if 'inertia' in k}

    def get_friction_properties(self) -> Dict[str, float]:
        """Get friction-related parameters."""
        physical_params = self.get_physical_parameters()
        return {k: v for k, v in physical_params.items() if 'friction' in k}

    def estimate_characteristic_scales(self) -> Dict[str, float]:
        """
        Estimate characteristic scales for the system.

        Returns:
            Dictionary with characteristic mass, length, time, energy scales
        """
        masses = self.get_mass_properties()
        lengths = self.get_length_properties()
        physical_params = self.get_physical_parameters()

        # Characteristic mass (total system mass)
        char_mass = sum(masses.values())

        # Characteristic length (maximum length scale)
        char_length = max(lengths.values()) if lengths else 1.0

        # Characteristic time (gravitational time scale)
        gravity = physical_params.get('gravity', 9.81)
        char_time = np.sqrt(char_length / abs(gravity)) if gravity != 0 else 1.0

        # Characteristic energy (gravitational potential energy scale)
        char_energy = char_mass * abs(gravity) * char_length

        return {
            'characteristic_mass': char_mass,
            'characteristic_length': char_length,
            'characteristic_time': char_time,
            'characteristic_energy': char_energy,
            'characteristic_frequency': 1.0 / char_time if char_time > 0 else 1.0
        }

    def check_physical_consistency(self) -> Dict[str, bool]:
        """
        Check physical consistency of parameters.

        Returns:
            Dictionary with consistency check results
        """
        checks = {}

        # Check positive masses
        masses = self.get_mass_properties()
        checks['positive_masses'] = all(m > 0 for m in masses.values())

        # Check positive lengths
        lengths = self.get_length_properties()
        checks['positive_lengths'] = all(l > 0 for l in lengths.values())

        # Check non-negative friction
        frictions = self.get_friction_properties()
        checks['non_negative_friction'] = all(f >= 0 for f in frictions.values())

        # Check positive inertias
        inertias = self.get_inertia_properties()
        checks['positive_inertias'] = all(I > 0 for I in inertias.values())

        return checks

    def get_dimensionless_parameters(self) -> Dict[str, float]:
        """
        Compute dimensionless parameter groups.

        Returns:
            Dictionary with dimensionless parameter combinations
        """
        scales = self.estimate_characteristic_scales()
        physical_params = self.get_physical_parameters()

        dimensionless = {}

        # Mass ratios
        masses = self.get_mass_properties()
        if len(masses) > 1:
            mass_values = list(masses.values())
            for i, (name, mass) in enumerate(masses.items()):
                dimensionless[f'{name}_ratio'] = mass / scales['characteristic_mass']

        # Length ratios
        lengths = self.get_length_properties()
        if len(lengths) > 1:
            for name, length in lengths.items():
                dimensionless[f'{name}_ratio'] = length / scales['characteristic_length']

        # Friction numbers (dimensionless friction)
        frictions = self.get_friction_properties()
        char_damping = scales['characteristic_mass'] / scales['characteristic_time']
        for name, friction in frictions.items():
            dimensionless[f'{name}_number'] = friction / char_damping

        return dimensionless


@dataclass(frozen=True)
class BaseDIPConfig(BasePhysicsConfig):
    """
    Base configuration class for Double Inverted Pendulum models.

    Provides common interface and validation for all DIP implementations
    (simplified, full, low-rank) with essential physical parameters.
    """

    # Essential physical parameters
    cart_mass: float = 1.0
    pendulum1_mass: float = 0.1
    pendulum2_mass: float = 0.1
    pendulum1_length: float = 0.5
    pendulum2_length: float = 0.5
    gravity: float = 9.81

    # Control limits
    force_limit: float = 20.0

    # State bounds
    cart_position_limits: Optional[tuple[float, float]] = None
    cart_velocity_limit: float = 10.0
    joint_velocity_limits: float = 20.0

    # Numerical parameters
    integration_tolerance: float = 1e-6
    max_condition_number: float = 1e8
    regularization_epsilon: float = 1e-8

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        if not self.validate():
            raise ConfigurationError("Configuration validation failed")

    def validate(self) -> bool:
        """Validate DIP configuration parameters."""
        checks = self.check_physical_consistency()
        return all(checks.values())

    def get_physical_parameters(self) -> Dict[str, float]:
        """Get dictionary of physical parameters."""
        return {
            'cart_mass': self.cart_mass,
            'pendulum1_mass': self.pendulum1_mass,
            'pendulum2_mass': self.pendulum2_mass,
            'pendulum1_length': self.pendulum1_length,
            'pendulum2_length': self.pendulum2_length,
            'gravity': self.gravity,
            'force_limit': self.force_limit,
            'cart_velocity_limit': self.cart_velocity_limit,
            'joint_velocity_limits': self.joint_velocity_limits,
        }

    def get_numerical_parameters(self) -> Dict[str, float]:
        """Get dictionary of numerical parameters."""
        return {
            'integration_tolerance': self.integration_tolerance,
            'max_condition_number': self.max_condition_number,
            'regularization_epsilon': self.regularization_epsilon,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BaseDIPConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)

    @classmethod
    def create_default(cls) -> 'BaseDIPConfig':
        """Create configuration with default parameters."""
        return cls()

    def check_physical_consistency(self) -> Dict[str, bool]:
        """Check physical consistency of DIP parameters."""
        checks = super().check_physical_consistency()

        # Additional DIP-specific checks
        checks['positive_gravity'] = self.gravity > 0
        checks['positive_force_limit'] = self.force_limit > 0
        checks['positive_velocity_limits'] = (
            self.cart_velocity_limit > 0 and
            self.joint_velocity_limits > 0
        )

        # Check reasonable parameter ranges
        checks['reasonable_mass_ratios'] = (
            0.01 <= self.pendulum1_mass / self.cart_mass <= 10.0 and
            0.01 <= self.pendulum2_mass / self.cart_mass <= 10.0
        )

        checks['reasonable_length_ratios'] = (
            0.1 <= self.pendulum1_length <= 5.0 and
            0.1 <= self.pendulum2_length <= 5.0
        )

        return checks

    def get_system_scales(self) -> Dict[str, float]:
        """Get characteristic scales for the DIP system."""
        scales = self.estimate_characteristic_scales()

        # DIP-specific scales
        total_length = self.pendulum1_length + self.pendulum2_length
        scales['total_pendulum_length'] = total_length
        scales['pendulum_frequency'] = np.sqrt(self.gravity / total_length)

        return scales


class ConfigurationError(ValueError):
    """Raised when configuration validation fails."""
    pass


class ConfigurationWarning(UserWarning):
    """Issued when configuration parameters are unusual but valid."""
    pass