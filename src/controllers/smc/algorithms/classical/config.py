#==========================================================================================\\\
#============== src/controllers/smc/algorithms/classical/config.py =================\\\
#==========================================================================================\\\

"""
Configuration Schema for Classical SMC.

Type-safe configuration using Pydantic with validation rules based on SMC theory.
Replaces parameter validation scattered throughout the original 458-line controller.
"""

from typing import List, Optional, Literal
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator


@dataclass(frozen=True)
class ClassicalSMCConfig:
    """
    Type-safe configuration for Classical SMC controller.

    Based on SMC theory requirements:
    - Surface gains [k1, k2, λ1, λ2] must be positive for Hurwitz stability
    - Switching gain K must be positive for reaching condition
    - Derivative gain kd must be non-negative for damping
    """

    # Required parameters
    dt: float = field()                                    # Control timestep
    gains: List[float] = field()                           # [k1, k2, lam1, lam2, K, kd]
    max_force: float = field()                             # Control saturation limit

    # Boundary layer parameters
    boundary_layer: float = field()                        # Chattering reduction thickness
    boundary_layer_slope: float = field(default=0.0)      # Adaptive boundary layer slope

    # Switching function
    switch_method: Literal["tanh", "linear", "sign"] = field(default="tanh")

    # Numerical parameters
    regularization: float = field(default=1e-10)           # Matrix regularization
    controllability_threshold: Optional[float] = field(default=None)  # Equivalent control threshold

    # Optional dynamics model
    dynamics_model: Optional[object] = field(default=None, compare=False)

    def __post_init__(self):
        """Validate configuration after creation."""
        self._validate_gains()
        self._validate_parameters()

    def _validate_gains(self) -> None:
        """Validate gain vector according to SMC theory."""
        if len(self.gains) != 6:
            raise ValueError("Classical SMC requires exactly 6 gains: [k1, k2, lam1, lam2, K, kd]")

        k1, k2, lam1, lam2, K, kd = self.gains

        # Surface gains must be positive for Hurwitz stability
        if any(g <= 0 for g in [k1, k2, lam1, lam2]):
            raise ValueError("Surface gains [k1, k2, λ1, λ2] must be positive for stability")

        # Switching gain must be positive for reaching condition
        if K <= 0:
            raise ValueError("Switching gain K must be positive")

        # Derivative gain must be non-negative
        if kd < 0:
            raise ValueError("Derivative gain kd must be non-negative")

    def _validate_parameters(self) -> None:
        """Validate other configuration parameters."""
        if self.max_force <= 0:
            raise ValueError("max_force must be positive")

        if self.dt <= 0:
            raise ValueError("dt must be positive")

        if self.boundary_layer <= 0:
            raise ValueError("boundary_layer must be positive")

        if self.boundary_layer_slope < 0:
            raise ValueError("boundary_layer_slope must be non-negative")

        if self.regularization <= 0:
            raise ValueError("regularization must be positive")

        if self.controllability_threshold is not None and self.controllability_threshold <= 0:
            raise ValueError("controllability_threshold must be positive when specified")

    @property
    def k1(self) -> float:
        """Joint 1 position gain."""
        return self.gains[0]

    @property
    def k2(self) -> float:
        """Joint 2 position gain."""
        return self.gains[1]

    @property
    def lam1(self) -> float:
        """Joint 1 velocity gain (λ₁)."""
        return self.gains[2]

    @property
    def lam2(self) -> float:
        """Joint 2 velocity gain (λ₂)."""
        return self.gains[3]

    @property
    def K(self) -> float:
        """Switching gain."""
        return self.gains[4]

    @property
    def kd(self) -> float:
        """Derivative gain."""
        return self.gains[5]

    def get_surface_gains(self) -> List[float]:
        """Get sliding surface gains [k1, k2, λ1, λ2]."""
        return self.gains[:4]

    def get_effective_controllability_threshold(self) -> float:
        """Get effective controllability threshold."""
        if self.controllability_threshold is not None:
            return self.controllability_threshold
        # Default: scale with surface gains
        return 0.05 * (self.k1 + self.k2)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            'gains': list(self.gains),
            'max_force': self.max_force,
            'dt': self.dt,
            'boundary_layer': self.boundary_layer,
            'boundary_layer_slope': self.boundary_layer_slope,
            'switch_method': self.switch_method,
            'regularization': self.regularization,
            'controllability_threshold': self.controllability_threshold
        }

    @classmethod
    def from_dict(cls, config_dict: dict, dynamics_model=None) -> 'ClassicalSMCConfig':
        """Create configuration from dictionary."""
        config_dict = config_dict.copy()
        config_dict['dynamics_model'] = dynamics_model
        return cls(**config_dict)

    @classmethod
    def create_default(cls, gains: List[float], max_force: float = 100.0,
                      dt: float = 0.01, boundary_layer: float = 0.01, **kwargs) -> 'ClassicalSMCConfig':
        """Create configuration with sensible defaults."""
        return cls(
            gains=gains,
            max_force=max_force,
            dt=dt,
            boundary_layer=boundary_layer,
        )