#==========================================================================================\\\
#==================== src/plant/configurations/validation.py ==========================\\\
#==========================================================================================\\\

"""
Parameter Validation for Plant Configurations.

Comprehensive validation utilities for physics parameters ensuring
mathematical correctness, physical realizability, and numerical stability.
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional, Protocol
import numpy as np
import warnings
from .base_config import ConfigurationError, ConfigurationWarning


class ParameterValidator(Protocol):
    """Protocol for parameter validation strategies."""

    def validate_parameter(self, name: str, value: Any) -> bool:
        """Validate a single parameter."""
        ...

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """Validate multiple parameters, return list of errors."""
        ...


class PhysicsParameterValidator:
    """
    Comprehensive validator for physics parameters.

    Provides validation for common physics parameter types with
    appropriate bounds checking and consistency verification.
    """

    def __init__(
        self,
        strict_mode: bool = False,
        warn_on_unusual: bool = True
    ):
        """
        Initialize parameter validator.

        Args:
            strict_mode: Raise exceptions for warnings if True
            warn_on_unusual: Issue warnings for unusual but valid parameters
        """
        self.strict_mode = strict_mode
        self.warn_on_unusual = warn_on_unusual

        # Define parameter bounds and validation rules
        self._setup_validation_rules()

    def validate_mass(self, name: str, mass: float) -> bool:
        """Validate mass parameter."""
        if not isinstance(mass, (int, float)):
            raise ConfigurationError(f"Mass {name} must be numeric, got {type(mass)}")

        if mass <= 0:
            raise ConfigurationError(f"Mass {name} must be positive, got {mass}")

        if mass > 1000:  # kg - unusually large for laboratory systems
            if self.warn_on_unusual:
                warnings.warn(f"Mass {name} = {mass} kg is unusually large", ConfigurationWarning)

        if mass < 1e-6:  # kg - unusually small
            if self.warn_on_unusual:
                warnings.warn(f"Mass {name} = {mass} kg is unusually small", ConfigurationWarning)

        return True

    def validate_length(self, name: str, length: float) -> bool:
        """Validate length parameter."""
        if not isinstance(length, (int, float)):
            raise ConfigurationError(f"Length {name} must be numeric, got {type(length)}")

        if length <= 0:
            raise ConfigurationError(f"Length {name} must be positive, got {length}")

        if length > 10:  # meters - unusually large for laboratory systems
            if self.warn_on_unusual:
                warnings.warn(f"Length {name} = {length} m is unusually large", ConfigurationWarning)

        if length < 1e-4:  # meters - unusually small
            if self.warn_on_unusual:
                warnings.warn(f"Length {name} = {length} m is unusually small", ConfigurationWarning)

        return True

    def validate_inertia(self, name: str, inertia: float) -> bool:
        """Validate moment of inertia parameter."""
        if not isinstance(inertia, (int, float)):
            raise ConfigurationError(f"Inertia {name} must be numeric, got {type(inertia)}")

        if inertia <= 0:
            raise ConfigurationError(f"Inertia {name} must be positive, got {inertia}")

        # Inertia bounds are harder to estimate without geometry details
        if inertia > 100:  # kg⋅m² - very large for typical systems
            if self.warn_on_unusual:
                warnings.warn(f"Inertia {name} = {inertia} kg⋅m² is unusually large", ConfigurationWarning)

        return True

    def validate_friction(self, name: str, friction: float) -> bool:
        """Validate friction coefficient."""
        if not isinstance(friction, (int, float)):
            raise ConfigurationError(f"Friction {name} must be numeric, got {type(friction)}")

        if friction < 0:
            raise ConfigurationError(f"Friction {name} must be non-negative, got {friction}")

        if friction > 1000:  # Very high friction
            if self.warn_on_unusual:
                warnings.warn(f"Friction {name} = {friction} is unusually large", ConfigurationWarning)

        return True

    def validate_gravity(self, gravity: float) -> bool:
        """Validate gravity parameter."""
        if not isinstance(gravity, (int, float)):
            raise ConfigurationError(f"Gravity must be numeric, got {type(gravity)}")

        if abs(gravity) < 0.1:  # Very low gravity
            if self.warn_on_unusual:
                warnings.warn(f"Gravity = {gravity} m/s² is unusually low", ConfigurationWarning)

        if abs(gravity) > 50:  # Very high gravity
            if self.warn_on_unusual:
                warnings.warn(f"Gravity = {gravity} m/s² is unusually high", ConfigurationWarning)

        return True

    def validate_numerical_parameter(
        self,
        name: str,
        value: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> bool:
        """Validate generic numerical parameter with bounds."""
        if not isinstance(value, (int, float)):
            raise ConfigurationError(f"Parameter {name} must be numeric, got {type(value)}")

        if not np.isfinite(value):
            raise ConfigurationError(f"Parameter {name} must be finite, got {value}")

        if min_value is not None and value < min_value:
            raise ConfigurationError(f"Parameter {name} = {value} below minimum {min_value}")

        if max_value is not None and value > max_value:
            raise ConfigurationError(f"Parameter {name} = {value} above maximum {max_value}")

        return True

    def validate_geometric_consistency(
        self,
        pendulum_length: float,
        com_distance: float,
        pendulum_name: str = ""
    ) -> bool:
        """Validate geometric consistency between pendulum length and COM."""
        if com_distance > pendulum_length:
            raise ConfigurationError(
                f"{pendulum_name} COM distance ({com_distance}) cannot exceed "
                f"pendulum length ({pendulum_length})"
            )

        if com_distance < 0.1 * pendulum_length:
            if self.warn_on_unusual:
                warnings.warn(
                    f"{pendulum_name} COM distance ({com_distance}) is very close to pivot "
                    f"(< 10% of length {pendulum_length})",
                    ConfigurationWarning
                )

        return True

    def validate_inertia_consistency(
        self,
        mass: float,
        length: float,
        com_distance: float,
        inertia: float,
        pendulum_name: str = ""
    ) -> bool:
        """Validate inertia consistency with geometry."""
        # Physical bounds for moment of inertia
        # Minimum: point mass at COM
        min_inertia = mass * com_distance**2

        # Maximum: uniform rod about end (conservative estimate)
        max_inertia = mass * length**2

        if inertia < min_inertia:
            raise ConfigurationError(
                f"{pendulum_name} inertia ({inertia}) below physical minimum "
                f"({min_inertia:.6f}) for point mass at COM"
            )

        if inertia > max_inertia:
            raise ConfigurationError(
                f"{pendulum_name} inertia ({inertia}) above physical maximum "
                f"({max_inertia:.6f}) for uniform rod"
            )

        # Check for reasonable inertia relative to uniform rod
        uniform_rod_inertia = (1/3) * mass * length**2
        if inertia > 2 * uniform_rod_inertia:
            if self.warn_on_unusual:
                warnings.warn(
                    f"{pendulum_name} inertia ({inertia}) is large compared to "
                    f"uniform rod estimate ({uniform_rod_inertia:.6f})",
                    ConfigurationWarning
                )

        return True

    def validate_mass_distribution(
        self,
        cart_mass: float,
        pendulum_masses: List[float]
    ) -> bool:
        """Validate mass distribution for dynamic stability."""
        total_pendulum_mass = sum(pendulum_masses)

        # Check mass ratios for controllability
        mass_ratio = total_pendulum_mass / cart_mass

        if mass_ratio > 1.0:
            if self.warn_on_unusual:
                warnings.warn(
                    f"Total pendulum mass ({total_pendulum_mass:.3f}) exceeds "
                    f"cart mass ({cart_mass:.3f}), ratio = {mass_ratio:.3f}",
                    ConfigurationWarning
                )

        if mass_ratio < 0.01:
            if self.warn_on_unusual:
                warnings.warn(
                    f"Pendulum masses ({total_pendulum_mass:.3f}) very small compared to "
                    f"cart mass ({cart_mass:.3f}), ratio = {mass_ratio:.3f}",
                    ConfigurationWarning
                )

        return True

    def validate_system_parameters(self, params: Dict[str, Any]) -> List[str]:
        """
        Validate complete system parameter set.

        Args:
            params: Dictionary of system parameters

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []

        try:
            # Validate individual parameters
            for name, value in params.items():
                if 'mass' in name:
                    self.validate_mass(name, value)
                elif 'length' in name:
                    self.validate_length(name, value)
                elif 'inertia' in name:
                    self.validate_inertia(name, value)
                elif 'friction' in name:
                    self.validate_friction(name, value)
                elif name == 'gravity':
                    self.validate_gravity(value)

            # Validate geometric consistency
            if all(key in params for key in ['pendulum1_length', 'pendulum1_com']):
                self.validate_geometric_consistency(
                    params['pendulum1_length'],
                    params['pendulum1_com'],
                    'Pendulum 1'
                )

            if all(key in params for key in ['pendulum2_length', 'pendulum2_com']):
                self.validate_geometric_consistency(
                    params['pendulum2_length'],
                    params['pendulum2_com'],
                    'Pendulum 2'
                )

            # Validate inertia consistency
            if all(key in params for key in [
                'pendulum1_mass', 'pendulum1_length', 'pendulum1_com', 'pendulum1_inertia'
            ]):
                self.validate_inertia_consistency(
                    params['pendulum1_mass'],
                    params['pendulum1_length'],
                    params['pendulum1_com'],
                    params['pendulum1_inertia'],
                    'Pendulum 1'
                )

            if all(key in params for key in [
                'pendulum2_mass', 'pendulum2_length', 'pendulum2_com', 'pendulum2_inertia'
            ]):
                self.validate_inertia_consistency(
                    params['pendulum2_mass'],
                    params['pendulum2_length'],
                    params['pendulum2_com'],
                    params['pendulum2_inertia'],
                    'Pendulum 2'
                )

            # Validate mass distribution
            if all(key in params for key in ['cart_mass', 'pendulum1_mass', 'pendulum2_mass']):
                self.validate_mass_distribution(
                    params['cart_mass'],
                    [params['pendulum1_mass'], params['pendulum2_mass']]
                )

        except ConfigurationError as e:
            errors.append(str(e))
        except ConfigurationWarning as w:
            if self.strict_mode:
                errors.append(str(w))

        return errors

    def _setup_validation_rules(self) -> None:
        """Setup validation rules and bounds."""
        # Define reasonable parameter ranges
        self.parameter_bounds = {
            'mass': (1e-6, 1000),      # kg
            'length': (1e-4, 10),      # m
            'inertia': (1e-12, 100),   # kg⋅m²
            'friction': (0, 1000),     # N⋅s/m or N⋅m⋅s/rad
            'gravity': (0.1, 50),      # m/s²
            'regularization': (1e-15, 1e-3),
            'condition_number': (1, 1e20),
            'tolerance': (1e-15, 1e-3),
            'step_size': (1e-10, 1.0)
        }


def validate_physics_parameters(
    params: Dict[str, Any],
    strict_mode: bool = False
) -> Tuple[bool, List[str]]:
    """
    Convenience function for physics parameter validation.

    Args:
        params: Dictionary of parameters to validate
        strict_mode: Raise exceptions for warnings if True

    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = PhysicsParameterValidator(strict_mode=strict_mode)
    errors = validator.validate_system_parameters(params)

    return len(errors) == 0, errors