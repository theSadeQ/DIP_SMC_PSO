#==========================================================================================\\\
#=================== src/plant/models/simplified/config.py ===========================\\\
#==========================================================================================\\\

"""
Configuration for Simplified DIP Dynamics.

Type-safe configuration with validation for the simplified double
inverted pendulum model. Ensures physical consistency and provides
mathematical constraints based on mechanical engineering principles.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import numpy as np


@dataclass(frozen=True)
class SimplifiedDIPConfig:
    """
    Type-safe configuration for simplified DIP dynamics.

    Physical Parameters:
    - All masses must be positive (physical requirement)
    - All lengths must be positive (geometric requirement)
    - Friction coefficients must be non-negative (energy dissipation)
    - Inertias must be positive (rotational mass distribution)

    Numerical Parameters:
    - Regularization ensures matrix invertibility
    - Condition number bounds prevent numerical instability
    """

    # Physical parameters - masses (kg)
    cart_mass: float = field()
    pendulum1_mass: float = field()
    pendulum2_mass: float = field()

    # Physical parameters - lengths (m)
    pendulum1_length: float = field()
    pendulum2_length: float = field()
    pendulum1_com: float = field()    # Center of mass distance
    pendulum2_com: float = field()    # Center of mass distance

    # Physical parameters - inertias (kg⋅m²)
    pendulum1_inertia: float = field()
    pendulum2_inertia: float = field()

    # Environmental parameters
    gravity: float = field(default=9.81)

    # Friction parameters (N⋅s/m or N⋅m⋅s/rad)
    cart_friction: float = field(default=0.1)
    joint1_friction: float = field(default=0.01)
    joint2_friction: float = field(default=0.01)

    # Numerical stability parameters
    regularization_alpha: float = field(default=1e-4)
    max_condition_number: float = field(default=1e14)
    min_regularization: float = field(default=1e-10)
    singularity_threshold: float = field(default=1e8)
    use_fixed_regularization: bool = field(default=False)

    # Integration parameters
    max_step_size: float = field(default=0.01)
    min_step_size: float = field(default=1e-6)
    relative_tolerance: float = field(default=1e-6)
    absolute_tolerance: float = field(default=1e-9)

    def __post_init__(self):
        """Validate configuration after creation."""
        self._validate_physical_parameters()
        self._validate_numerical_parameters()
        self._validate_geometric_constraints()

    def _validate_physical_parameters(self) -> None:
        """Validate physical parameters for consistency."""
        # Mass validation
        if self.cart_mass <= 0:
            raise ValueError(f"Cart mass must be positive, got {self.cart_mass}")
        if self.pendulum1_mass <= 0:
            raise ValueError(f"Pendulum 1 mass must be positive, got {self.pendulum1_mass}")
        if self.pendulum2_mass <= 0:
            raise ValueError(f"Pendulum 2 mass must be positive, got {self.pendulum2_mass}")

        # Length validation
        if self.pendulum1_length <= 0:
            raise ValueError(f"Pendulum 1 length must be positive, got {self.pendulum1_length}")
        if self.pendulum2_length <= 0:
            raise ValueError(f"Pendulum 2 length must be positive, got {self.pendulum2_length}")
        if self.pendulum1_com <= 0:
            raise ValueError(f"Pendulum 1 COM must be positive, got {self.pendulum1_com}")
        if self.pendulum2_com <= 0:
            raise ValueError(f"Pendulum 2 COM must be positive, got {self.pendulum2_com}")

        # Inertia validation
        if self.pendulum1_inertia <= 0:
            raise ValueError(f"Pendulum 1 inertia must be positive, got {self.pendulum1_inertia}")
        if self.pendulum2_inertia <= 0:
            raise ValueError(f"Pendulum 2 inertia must be positive, got {self.pendulum2_inertia}")

        # Friction validation (must be non-negative)
        if self.cart_friction < 0:
            raise ValueError(f"Cart friction must be non-negative, got {self.cart_friction}")
        if self.joint1_friction < 0:
            raise ValueError(f"Joint 1 friction must be non-negative, got {self.joint1_friction}")
        if self.joint2_friction < 0:
            raise ValueError(f"Joint 2 friction must be non-negative, got {self.joint2_friction}")

        # Gravity validation
        if abs(self.gravity) < 1e-3:
            raise ValueError(f"Gravity magnitude too small, got {self.gravity}")

    def _validate_numerical_parameters(self) -> None:
        """Validate numerical parameters for stability."""
        if self.regularization_alpha <= 0:
            raise ValueError(f"Regularization alpha must be positive, got {self.regularization_alpha}")

        if self.max_condition_number <= 1:
            raise ValueError(f"Max condition number must be > 1, got {self.max_condition_number}")

        if self.min_regularization <= 0:
            raise ValueError(f"Min regularization must be positive, got {self.min_regularization}")

        if self.singularity_threshold <= 1:
            raise ValueError(f"Singularity threshold must be > 1, got {self.singularity_threshold}")

        # Integration parameter validation
        if self.max_step_size <= 0:
            raise ValueError(f"Max step size must be positive, got {self.max_step_size}")

        if self.min_step_size <= 0:
            raise ValueError(f"Min step size must be positive, got {self.min_step_size}")

        if self.min_step_size >= self.max_step_size:
            raise ValueError("Min step size must be less than max step size")

        if self.relative_tolerance <= 0:
            raise ValueError(f"Relative tolerance must be positive, got {self.relative_tolerance}")

        if self.absolute_tolerance <= 0:
            raise ValueError(f"Absolute tolerance must be positive, got {self.absolute_tolerance}")

    def _validate_geometric_constraints(self) -> None:
        """Validate geometric constraints between parameters."""
        # Center of mass must be within pendulum length
        if self.pendulum1_com > self.pendulum1_length:
            raise ValueError(
                f"Pendulum 1 COM ({self.pendulum1_com}) cannot exceed length ({self.pendulum1_length})"
            )

        if self.pendulum2_com > self.pendulum2_length:
            raise ValueError(
                f"Pendulum 2 COM ({self.pendulum2_com}) cannot exceed length ({self.pendulum2_length})"
            )

        # Reasonable inertia bounds based on geometry
        # For a uniform rod: I = (1/3) * m * L²
        max_inertia_1 = self.pendulum1_mass * self.pendulum1_length**2
        if self.pendulum1_inertia > max_inertia_1:
            raise ValueError(
                f"Pendulum 1 inertia ({self.pendulum1_inertia}) exceeds physical bound ({max_inertia_1:.3f})"
            )

        max_inertia_2 = self.pendulum2_mass * self.pendulum2_length**2
        if self.pendulum2_inertia > max_inertia_2:
            raise ValueError(
                f"Pendulum 2 inertia ({self.pendulum2_inertia}) exceeds physical bound ({max_inertia_2:.3f})"
            )

        # Minimum inertia bounds (point mass at COM)
        min_inertia_1 = self.pendulum1_mass * self.pendulum1_com**2
        if self.pendulum1_inertia < min_inertia_1:
            raise ValueError(
                f"Pendulum 1 inertia ({self.pendulum1_inertia}) below physical bound ({min_inertia_1:.3f})"
            )

        min_inertia_2 = self.pendulum2_mass * self.pendulum2_com**2
        if self.pendulum2_inertia < min_inertia_2:
            raise ValueError(
                f"Pendulum 2 inertia ({self.pendulum2_inertia}) below physical bound ({min_inertia_2:.3f})"
            )

    @classmethod
    def create_default(cls) -> 'SimplifiedDIPConfig':
        """Create configuration with sensible default parameters."""
        return cls(
            # Masses (kg)
            cart_mass=1.0,
            pendulum1_mass=0.1,
            pendulum2_mass=0.1,

            # Lengths (m)
            pendulum1_length=0.5,
            pendulum2_length=0.5,
            pendulum1_com=0.25,  # Half of length for uniform rod
            pendulum2_com=0.25,  # Half of length for uniform rod

            # Inertias (kg⋅m²) - uniform rod approximation
            pendulum1_inertia=0.1 * (0.5**2) / 3,  # (1/3) * m * L²
            pendulum2_inertia=0.1 * (0.5**2) / 3,  # (1/3) * m * L²

            # Environmental
            gravity=9.81,

            # Friction
            cart_friction=0.1,
            joint1_friction=0.01,
            joint2_friction=0.01
        )

    @classmethod
    def create_benchmark(cls) -> 'SimplifiedDIPConfig':
        """Create configuration for benchmark/comparison studies."""
        return cls(
            # Standard benchmark parameters
            cart_mass=1.0,
            pendulum1_mass=0.2,
            pendulum2_mass=0.2,
            pendulum1_length=0.6,
            pendulum2_length=0.6,
            pendulum1_com=0.3,
            pendulum2_com=0.3,
            pendulum1_inertia=0.024,  # More realistic inertia
            pendulum2_inertia=0.024,
            gravity=9.81,
            cart_friction=0.05,
            joint1_friction=0.005,
            joint2_friction=0.005
        )

    @classmethod
    def create_lightweight(cls) -> 'SimplifiedDIPConfig':
        """Create configuration optimized for computational speed."""
        return cls(
            # Lightweight parameters for fast simulation
            cart_mass=0.5,
            pendulum1_mass=0.05,
            pendulum2_mass=0.05,
            pendulum1_length=0.3,
            pendulum2_length=0.3,
            pendulum1_com=0.15,
            pendulum2_com=0.15,
            pendulum1_inertia=0.05 * (0.3**2) / 3,
            pendulum2_inertia=0.05 * (0.3**2) / 3,
            gravity=9.81,
            cart_friction=0.02,
            joint1_friction=0.002,
            joint2_friction=0.002,

            # Relaxed numerical parameters for speed
            use_fixed_regularization=True,
            max_step_size=0.02,
            relative_tolerance=1e-4,
            absolute_tolerance=1e-6
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            # Physical parameters
            'cart_mass': self.cart_mass,
            'pendulum1_mass': self.pendulum1_mass,
            'pendulum2_mass': self.pendulum2_mass,
            'pendulum1_length': self.pendulum1_length,
            'pendulum2_length': self.pendulum2_length,
            'pendulum1_com': self.pendulum1_com,
            'pendulum2_com': self.pendulum2_com,
            'pendulum1_inertia': self.pendulum1_inertia,
            'pendulum2_inertia': self.pendulum2_inertia,
            'gravity': self.gravity,
            'cart_friction': self.cart_friction,
            'joint1_friction': self.joint1_friction,
            'joint2_friction': self.joint2_friction,

            # Numerical parameters
            'regularization_alpha': self.regularization_alpha,
            'max_condition_number': self.max_condition_number,
            'min_regularization': self.min_regularization,
            'singularity_threshold': self.singularity_threshold,
            'use_fixed_regularization': self.use_fixed_regularization,

            # Integration parameters
            'max_step_size': self.max_step_size,
            'min_step_size': self.min_step_size,
            'relative_tolerance': self.relative_tolerance,
            'absolute_tolerance': self.absolute_tolerance
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'SimplifiedDIPConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)

    def get_total_mass(self) -> float:
        """Get total system mass."""
        return self.cart_mass + self.pendulum1_mass + self.pendulum2_mass

    def get_characteristic_length(self) -> float:
        """Get characteristic length scale of the system."""
        return max(self.pendulum1_length, self.pendulum2_length)

    def get_characteristic_time(self) -> float:
        """Get characteristic time scale for oscillations."""
        L_char = self.get_characteristic_length()
        return np.sqrt(L_char / self.gravity)

    def estimate_natural_frequency(self) -> float:
        """Estimate natural frequency for small oscillations."""
        return 1.0 / self.get_characteristic_time()