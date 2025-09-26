#==========================================================================================\\\
#======================== src/plant/models/lowrank/config.py ============================\\\
#==========================================================================================\\\

"""
Low-rank DIP Configuration.

Simplified configuration with reduced parameters optimized for computational
efficiency while maintaining essential system characteristics.
"""

from __future__ import annotations
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
import numpy as np

from ...configurations.base_config import BaseDIPConfig


@dataclass(frozen=True)
class LowRankDIPConfig(BaseDIPConfig):
    """
    Configuration for Low-rank Double Inverted Pendulum Model.

    Simplified configuration that captures essential dynamics while reducing
    computational complexity. Uses representative parameters rather than
    full nonlinear effects.
    """

    # Basic physical parameters (simplified)
    cart_mass: float = 1.0
    pendulum1_mass: float = 0.1
    pendulum2_mass: float = 0.1
    pendulum1_length: float = 0.5
    pendulum2_length: float = 0.5
    gravity: float = 9.81

    # Simplified friction model
    friction_coefficient: float = 0.1
    damping_coefficient: float = 0.01

    # Control limits
    force_limit: float = 150.0

    # State bounds (relaxed for low-rank model)
    cart_position_limits: Optional[Tuple[float, float]] = (-2.0, 2.0)
    cart_velocity_limit: float = 5.0
    joint_velocity_limits: float = 10.0

    # Integration parameters
    max_timestep: float = 0.01
    min_timestep: float = 1e-6
    integration_tolerance: float = 1e-4

    # Numerical stability
    regularization_epsilon: float = 1e-6
    max_condition_number: float = 1e6

    # Simplified model flags
    enable_linearization: bool = True
    enable_small_angle_approximation: bool = True
    enable_decoupled_dynamics: bool = False

    # Performance optimization
    enable_fast_math: bool = True
    use_simplified_matrices: bool = True

    def __post_init__(self) -> None:
        """Post-initialization validation and derived parameter computation."""
        super().__post_init__()

        # Validate basic parameters
        self._validate_physical_parameters()

        # Compute derived parameters for low-rank model
        self._compute_derived_parameters()

        # Setup simplified physics constants
        self._setup_physics_constants()

    def _validate_physical_parameters(self) -> None:
        """Validate simplified physical parameters."""
        if self.cart_mass <= 0:
            raise ValueError("Cart mass must be positive")

        if self.pendulum1_mass <= 0 or self.pendulum2_mass <= 0:
            raise ValueError("Pendulum masses must be positive")

        if self.pendulum1_length <= 0 or self.pendulum2_length <= 0:
            raise ValueError("Pendulum lengths must be positive")

        if self.gravity <= 0:
            raise ValueError("Gravity must be positive")

        if self.friction_coefficient < 0:
            raise ValueError("Friction coefficient must be non-negative")

        if self.damping_coefficient < 0:
            raise ValueError("Damping coefficient must be non-negative")

    def _compute_derived_parameters(self) -> None:
        """Compute derived parameters for low-rank dynamics."""
        # Total system mass
        object.__setattr__(self, 'total_mass', self.cart_mass + self.pendulum1_mass + self.pendulum2_mass)

        # Effective lengths for simplified dynamics
        object.__setattr__(self, 'effective_length1', self.pendulum1_length)
        object.__setattr__(self, 'effective_length2', self.pendulum2_length)

        # Simplified inertial parameters
        object.__setattr__(self, 'effective_inertia1', self.pendulum1_mass * self.pendulum1_length**2)
        object.__setattr__(self, 'effective_inertia2', self.pendulum2_mass * self.pendulum2_length**2)

        # Natural frequencies (for linearized analysis)
        object.__setattr__(self, 'natural_freq1', np.sqrt(self.gravity / self.pendulum1_length))
        object.__setattr__(self, 'natural_freq2', np.sqrt(self.gravity / self.pendulum2_length))

        # Coupling strength parameter
        coupling_strength = (self.pendulum1_mass * self.pendulum1_length +
                                 self.pendulum2_mass * self.pendulum2_length) / self.total_mass
        object.__setattr__(self, 'coupling_strength', coupling_strength)

    def _setup_physics_constants(self) -> None:
        """Setup simplified physics constants for efficient computation."""
        # Gravitational terms
        object.__setattr__(self, 'g1', self.pendulum1_mass * self.gravity * self.pendulum1_length)
        object.__setattr__(self, 'g2', self.pendulum2_mass * self.gravity * self.pendulum2_length)

        # Mass-length products
        object.__setattr__(self, 'm1l1', self.pendulum1_mass * self.pendulum1_length)
        object.__setattr__(self, 'm2l2', self.pendulum2_mass * self.pendulum2_length)

        # Simplified friction terms
        object.__setattr__(self, 'friction_force_max', self.friction_coefficient * self.total_mass * self.gravity)

    def get_linearized_matrices(
        self,
        equilibrium_point: str = "upright"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get linearized system matrices around equilibrium point.

        Args:
            equilibrium_point: Equilibrium to linearize around ("upright" or "downward")

        Returns:
            Tuple of (A, B) matrices for linearized dynamics
        """
        if equilibrium_point == "upright":
            return self._get_upright_linearization()
        elif equilibrium_point == "downward":
            return self._get_downward_linearization()
        else:
            raise ValueError(f"Unknown equilibrium point: {equilibrium_point}")

    def _get_upright_linearization(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get linearization around upright equilibrium."""
        # State: [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
        A = np.zeros((6, 6))
        B = np.zeros((6, 1))

        # Position derivatives
        A[0, 3] = 1.0  # x_dot
        A[1, 4] = 1.0  # theta1_dot
        A[2, 5] = 1.0  # theta2_dot

        # Simplified acceleration terms (small angle approximation)
        # Cart acceleration
        A[3, 1] = -self.g1 / self.cart_mass  # theta1 effect
        A[3, 2] = -self.g2 / self.cart_mass  # theta2 effect
        A[3, 3] = -self.friction_coefficient  # velocity damping

        # Pendulum 1 acceleration
        A[4, 1] = -self.natural_freq1**2  # restoring force
        A[4, 3] = self.g1 / (self.effective_inertia1 * self.pendulum1_length)  # cart coupling
        A[4, 4] = -self.damping_coefficient  # angular damping

        # Pendulum 2 acceleration
        A[5, 2] = -self.natural_freq2**2  # restoring force
        A[5, 3] = self.g2 / (self.effective_inertia2 * self.pendulum2_length)  # cart coupling
        A[5, 5] = -self.damping_coefficient  # angular damping

        # Control input effect
        B[3, 0] = 1.0 / self.cart_mass  # Force on cart

        return A, B

    def _get_downward_linearization(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get linearization around downward equilibrium (stable)."""
        # State: [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
        A = np.zeros((6, 6))
        B = np.zeros((6, 1))

        # Position derivatives
        A[0, 3] = 1.0  # x_dot
        A[1, 4] = 1.0  # theta1_dot
        A[2, 5] = 1.0  # theta2_dot

        # For downward equilibrium, pendulums are stable
        # Cart acceleration
        A[3, 3] = -self.friction_coefficient  # velocity damping

        # Pendulum 1 acceleration (stable pendulum)
        A[4, 1] = self.natural_freq1**2  # negative restoring force (stable)
        A[4, 4] = -self.damping_coefficient  # angular damping

        # Pendulum 2 acceleration (stable pendulum)
        A[5, 2] = self.natural_freq2**2  # negative restoring force (stable)
        A[5, 5] = -self.damping_coefficient  # angular damping

        # Control input effect
        B[3, 0] = 1.0 / self.cart_mass  # Force on cart

        return A, B

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'cart_mass': self.cart_mass,
            'pendulum1_mass': self.pendulum1_mass,
            'pendulum2_mass': self.pendulum2_mass,
            'pendulum1_length': self.pendulum1_length,
            'pendulum2_length': self.pendulum2_length,
            'gravity': self.gravity,
            'friction_coefficient': self.friction_coefficient,
            'damping_coefficient': self.damping_coefficient,
            'force_limit': self.force_limit,
            'cart_position_limits': self.cart_position_limits,
            'cart_velocity_limit': self.cart_velocity_limit,
            'joint_velocity_limits': self.joint_velocity_limits,
            'enable_linearization': self.enable_linearization,
            'enable_small_angle_approximation': self.enable_small_angle_approximation,
            'enable_decoupled_dynamics': self.enable_decoupled_dynamics,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LowRankDIPConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)

    @classmethod
    def create_default(cls) -> 'LowRankDIPConfig':
        """Create default configuration."""
        return cls()

    @classmethod
    def create_fast_prototype(cls) -> 'LowRankDIPConfig':
        """Create configuration optimized for fast prototyping."""
        return cls(
            cart_mass=1.0,
            pendulum1_mass=0.1,
            pendulum2_mass=0.1,
            pendulum1_length=0.5,
            pendulum2_length=0.5,
            friction_coefficient=0.05,
            damping_coefficient=0.01,
            enable_linearization=True,
            enable_small_angle_approximation=True,
            enable_fast_math=True,
            use_simplified_matrices=True,
        )

    @classmethod
    def create_educational(cls) -> 'LowRankDIPConfig':
        """Create configuration for educational purposes."""
        return cls(
            cart_mass=1.0,
            pendulum1_mass=0.2,
            pendulum2_mass=0.1,
            pendulum1_length=1.0,
            pendulum2_length=0.8,
            friction_coefficient=0.1,
            damping_coefficient=0.02,
            enable_linearization=False,
            enable_small_angle_approximation=False,
            enable_decoupled_dynamics=False,
        )