#========================================================================================\
#==============================src/plant/models/full/config.py==============================\
#========================================================================================\

"""
Configuration for Full Fidelity DIP Dynamics.

Type-safe configuration for the high-fidelity double inverted pendulum model
with complete nonlinear dynamics, coupling effects, and advanced numerical
integration features.
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import numpy as np


@dataclass(frozen=True)
class FullDIPConfig:
    """
    Type-safe configuration for full-fidelity DIP dynamics.

    High-Fidelity Features:
    - Complete nonlinear dynamics with all coupling terms
    - Advanced friction models (viscous + Coulomb)
    - Flexible joint constraints and limits
    - High-precision numerical integration
    - Wind/disturbance modeling capability
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
    air_density: float = field(default=1.225)     # kg/m³ for air resistance

    # Advanced friction modeling
    cart_viscous_friction: float = field(default=0.1)      # Linear velocity friction
    cart_coulomb_friction: float = field(default=0.05)     # Static/kinetic friction
    joint1_viscous_friction: float = field(default=0.01)   # Angular velocity friction
    joint1_coulomb_friction: float = field(default=0.005)  # Joint static friction
    joint2_viscous_friction: float = field(default=0.01)   # Angular velocity friction
    joint2_coulomb_friction: float = field(default=0.005)  # Joint static friction

    # Joint limits and constraints
    cart_position_limits: Optional[tuple] = field(default=(-5.0, 5.0))
    joint1_angle_limits: Optional[tuple] = field(default=None)  # No limits = free rotation
    joint2_angle_limits: Optional[tuple] = field(default=None)  # No limits = free rotation
    cart_velocity_limit: float = field(default=10.0)            # m/s
    joint_velocity_limits: float = field(default=50.0)          # rad/s

    # Aerodynamic parameters (for high-speed motion)
    pendulum1_drag_coefficient: float = field(default=0.0)    # Cd for pendulum 1
    pendulum2_drag_coefficient: float = field(default=0.0)    # Cd for pendulum 2
    pendulum1_cross_section: float = field(default=0.0)       # Cross-sectional area
    pendulum2_cross_section: float = field(default=0.0)       # Cross-sectional area

    # Advanced numerical parameters
    use_adaptive_integration: bool = field(default=True)
    integration_method: str = field(default="DOPRI5")         # Dormand-Prince 5th order
    relative_tolerance: float = field(default=1e-8)
    absolute_tolerance: float = field(default=1e-10)
    max_step_size: float = field(default=0.001)               # Smaller for high fidelity
    min_step_size: float = field(default=1e-8)

    # Matrix conditioning and regularization
    regularization_alpha: float = field(default=1e-6)         # Smaller for high precision
    max_condition_number: float = field(default=1e12)         # Tighter for full model
    min_regularization: float = field(default=1e-12)          # Higher precision
    use_iterative_refinement: bool = field(default=True)      # For better accuracy

    # Advanced features
    include_coriolis_effects: bool = field(default=True)
    include_centrifugal_effects: bool = field(default=True)
    include_gyroscopic_effects: bool = field(default=True)
    include_aerodynamic_forces: bool = field(default=False)
    include_joint_flexibility: bool = field(default=False)

    # Disturbance modeling
    wind_model_enabled: bool = field(default=False)
    base_excitation_enabled: bool = field(default=False)

    def __post_init__(self):
        """Validate configuration after creation."""
        self._validate_physical_parameters()
        self._validate_numerical_parameters()
        self._validate_advanced_features()

    def _validate_physical_parameters(self) -> None:
        """Validate physical parameters for high-fidelity model."""
        # Basic validations (same as simplified)
        if self.cart_mass <= 0:
            raise ValueError(f"Cart mass must be positive, got {self.cart_mass}")
        if self.pendulum1_mass <= 0:
            raise ValueError(f"Pendulum 1 mass must be positive, got {self.pendulum1_mass}")
        if self.pendulum2_mass <= 0:
            raise ValueError(f"Pendulum 2 mass must be positive, got {self.pendulum2_mass}")

        # Length validations
        if self.pendulum1_length <= 0:
            raise ValueError(f"Pendulum 1 length must be positive, got {self.pendulum1_length}")
        if self.pendulum2_length <= 0:
            raise ValueError(f"Pendulum 2 length must be positive, got {self.pendulum2_length}")

        # COM validations
        if self.pendulum1_com <= 0 or self.pendulum1_com > self.pendulum1_length:
            raise ValueError(f"Pendulum 1 COM must be in (0, {self.pendulum1_length}]")
        if self.pendulum2_com <= 0 or self.pendulum2_com > self.pendulum2_length:
            raise ValueError(f"Pendulum 2 COM must be in (0, {self.pendulum2_length}]")

        # Inertia validations
        if self.pendulum1_inertia <= 0:
            raise ValueError(f"Pendulum 1 inertia must be positive, got {self.pendulum1_inertia}")
        if self.pendulum2_inertia <= 0:
            raise ValueError(f"Pendulum 2 inertia must be positive, got {self.pendulum2_inertia}")

        # Friction validations (all must be non-negative)
        friction_params = [
            ("cart_viscous_friction", self.cart_viscous_friction),
            ("cart_coulomb_friction", self.cart_coulomb_friction),
            ("joint1_viscous_friction", self.joint1_viscous_friction),
            ("joint1_coulomb_friction", self.joint1_coulomb_friction),
            ("joint2_viscous_friction", self.joint2_viscous_friction),
            ("joint2_coulomb_friction", self.joint2_coulomb_friction)
        ]

        for name, value in friction_params:
            if value < 0:
                raise ValueError(f"{name} must be non-negative, got {value}")

    def _validate_numerical_parameters(self) -> None:
        """Validate numerical parameters for high-fidelity integration."""
        if self.relative_tolerance <= 0 or self.relative_tolerance >= 1e-3:
            raise ValueError(f"Relative tolerance must be in (0, 1e-3), got {self.relative_tolerance}")

        if self.absolute_tolerance <= 0 or self.absolute_tolerance >= 1e-6:
            raise ValueError(f"Absolute tolerance must be in (0, 1e-6), got {self.absolute_tolerance}")

        if self.max_step_size <= 0 or self.max_step_size > 0.01:
            raise ValueError(f"Max step size must be in (0, 0.01], got {self.max_step_size}")

        if self.min_step_size <= 0 or self.min_step_size >= self.max_step_size:
            raise ValueError("Min step size must be positive and less than max step size")

        # Integration method validation
        valid_methods = ["DOPRI5", "DOPRI853", "RADAU", "BDF", "LSODA"]
        if self.integration_method not in valid_methods:
            raise ValueError(f"Integration method must be one of {valid_methods}")

    def _validate_advanced_features(self) -> None:
        """Validate advanced feature combinations."""
        # Aerodynamic forces require drag coefficients and cross-sections
        if self.include_aerodynamic_forces:
            if (self.pendulum1_drag_coefficient == 0 and self.pendulum1_cross_section == 0 and
                self.pendulum2_drag_coefficient == 0 and self.pendulum2_cross_section == 0):
                raise ValueError("Aerodynamic forces enabled but no drag parameters specified")

        # Joint limits validation
        if self.cart_position_limits is not None:
            if len(self.cart_position_limits) != 2 or self.cart_position_limits[0] >= self.cart_position_limits[1]:
                raise ValueError("Cart position limits must be (min, max) with min < max")

    @classmethod
    def create_high_fidelity(cls) -> 'FullDIPConfig':
        """Create high-fidelity configuration with realistic parameters."""
        return cls(
            # Realistic laboratory DIP parameters
            cart_mass=2.5,
            pendulum1_mass=0.3,
            pendulum2_mass=0.3,
            pendulum1_length=0.8,
            pendulum2_length=0.8,
            pendulum1_com=0.4,
            pendulum2_com=0.4,
            pendulum1_inertia=0.032,  # More realistic for actual pendulum
            pendulum2_inertia=0.032,

            # Advanced friction modeling
            cart_viscous_friction=0.2,
            cart_coulomb_friction=0.1,
            joint1_viscous_friction=0.02,
            joint1_coulomb_friction=0.01,
            joint2_viscous_friction=0.02,
            joint2_coulomb_friction=0.01,

            # High-precision integration
            relative_tolerance=1e-8,
            absolute_tolerance=1e-10,
            max_step_size=0.001,
            use_adaptive_integration=True,
            integration_method="DOPRI5",

            # All advanced effects enabled
            include_coriolis_effects=True,
            include_centrifugal_effects=True,
            include_gyroscopic_effects=True,
            use_iterative_refinement=True
        )

    @classmethod
    def create_research_grade(cls) -> 'FullDIPConfig':
        """Create research-grade configuration with aerodynamics and disturbances."""
        config = cls.create_high_fidelity()

        # Enable advanced features for research
        return cls(
            **config.to_dict(),
            include_aerodynamic_forces=True,
            pendulum1_drag_coefficient=0.5,
            pendulum2_drag_coefficient=0.5,
            pendulum1_cross_section=0.02,  # 20 cm² cross-section
            pendulum2_cross_section=0.02,
            wind_model_enabled=True,
            base_excitation_enabled=True,
            relative_tolerance=1e-10,
            absolute_tolerance=1e-12
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
            'air_density': self.air_density,

            # Friction parameters
            'cart_viscous_friction': self.cart_viscous_friction,
            'cart_coulomb_friction': self.cart_coulomb_friction,
            'joint1_viscous_friction': self.joint1_viscous_friction,
            'joint1_coulomb_friction': self.joint1_coulomb_friction,
            'joint2_viscous_friction': self.joint2_viscous_friction,
            'joint2_coulomb_friction': self.joint2_coulomb_friction,

            # Constraints
            'cart_position_limits': self.cart_position_limits,
            'joint1_angle_limits': self.joint1_angle_limits,
            'joint2_angle_limits': self.joint2_angle_limits,
            'cart_velocity_limit': self.cart_velocity_limit,
            'joint_velocity_limits': self.joint_velocity_limits,

            # Aerodynamics
            'pendulum1_drag_coefficient': self.pendulum1_drag_coefficient,
            'pendulum2_drag_coefficient': self.pendulum2_drag_coefficient,
            'pendulum1_cross_section': self.pendulum1_cross_section,
            'pendulum2_cross_section': self.pendulum2_cross_section,

            # Numerical parameters
            'use_adaptive_integration': self.use_adaptive_integration,
            'integration_method': self.integration_method,
            'relative_tolerance': self.relative_tolerance,
            'absolute_tolerance': self.absolute_tolerance,
            'max_step_size': self.max_step_size,
            'min_step_size': self.min_step_size,
            'regularization_alpha': self.regularization_alpha,
            'max_condition_number': self.max_condition_number,
            'min_regularization': self.min_regularization,
            'use_iterative_refinement': self.use_iterative_refinement,

            # Advanced features
            'include_coriolis_effects': self.include_coriolis_effects,
            'include_centrifugal_effects': self.include_centrifugal_effects,
            'include_gyroscopic_effects': self.include_gyroscopic_effects,
            'include_aerodynamic_forces': self.include_aerodynamic_forces,
            'include_joint_flexibility': self.include_joint_flexibility,
            'wind_model_enabled': self.wind_model_enabled,
            'base_excitation_enabled': self.base_excitation_enabled
        }

    def get_complexity_level(self) -> str:
        """Get complexity level description."""
        complexity_score = 0

        if self.include_coriolis_effects: complexity_score += 1
        if self.include_centrifugal_effects: complexity_score += 1
        if self.include_gyroscopic_effects: complexity_score += 1
        if self.include_aerodynamic_forces: complexity_score += 2
        if self.include_joint_flexibility: complexity_score += 2
        if self.wind_model_enabled: complexity_score += 1
        if self.base_excitation_enabled: complexity_score += 1

        if complexity_score <= 2:
            return "Basic Full Model"
        elif complexity_score <= 5:
            return "Advanced Full Model"
        else:
            return "Research-Grade Full Model"

    @property
    def cart_friction(self) -> float:
        """Get cart friction coefficient (alias for viscous friction)."""
        return self.cart_viscous_friction

    @property
    def joint1_friction(self) -> float:
        """Get joint 1 friction coefficient (alias for viscous friction)."""
        return self.joint1_viscous_friction

    @property
    def joint2_friction(self) -> float:
        """Get joint 2 friction coefficient (alias for viscous friction)."""
        return self.joint2_viscous_friction

    @classmethod
    def create_default(cls) -> 'FullDIPConfig':
        """Create default full DIP configuration."""
        return cls(
            cart_mass=1.0,
            pendulum1_mass=0.1,
            pendulum2_mass=0.1,
            pendulum1_length=0.5,
            pendulum2_length=0.5,
            pendulum1_com=0.25,
            pendulum2_com=0.25,
            pendulum1_inertia=0.01,
            pendulum2_inertia=0.01
        )

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'FullDIPConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)