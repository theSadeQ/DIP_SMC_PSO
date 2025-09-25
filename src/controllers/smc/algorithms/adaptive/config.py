#==========================================================================================\\\
#============== src/controllers/smc/algorithms/adaptive/config.py =================\\\
#==========================================================================================\\\

"""
Configuration Schema for Adaptive SMC.

Type-safe configuration for Adaptive Sliding Mode Control with online gain adaptation.
Replaces parameter validation from the original 427-line monolithic controller.
"""

from typing import List, Optional
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AdaptiveSMCConfig:
    """
    Type-safe configuration for Adaptive SMC controller.

    Based on adaptive SMC theory:
    - Surface gains [k1, k2, λ1, λ2] must be positive for Hurwitz stability
    - Adaptation rate γ must be positive but bounded for stability
    - Adaptation bounds [K_min, K_max] ensure bounded gains
    """

    # Required parameters
    gains: List[float] = field()                           # [k1, k2, lam1, lam2, gamma]
    max_force: float = field()                             # Control saturation limit
    dt: float = field()                                    # Control timestep

    # Adaptation parameters
    leak_rate: float = field(default=0.1)                  # Leakage for parameter drift
    adapt_rate_limit: float = field(default=100.0)        # Maximum adaptation rate
    K_min: float = field(default=0.1)                     # Minimum adaptive gain
    K_max: float = field(default=100.0)                   # Maximum adaptive gain
    K_init: float = field(default=10.0)                   # Initial adaptive gain
    alpha: float = field(default=0.5)                     # Adaptation law parameter

    # Boundary layer and switching
    boundary_layer: float = field(default=0.01)           # Chattering reduction
    smooth_switch: bool = field(default=True)             # Use smooth switching
    dead_zone: float = field(default=0.01)                # Dead zone for adaptation

    def __post_init__(self):
        """Validate configuration after creation."""
        self._validate_gains()
        self._validate_adaptation_parameters()
        self._validate_other_parameters()

    def _validate_gains(self) -> None:
        """Validate gain vector according to adaptive SMC theory."""
        if len(self.gains) != 5:
            raise ValueError("Adaptive SMC requires exactly 5 gains: [k1, k2, lam1, lam2, gamma]")

        k1, k2, lam1, lam2, gamma = self.gains

        # Surface gains must be positive for Hurwitz stability
        if any(g <= 0 for g in [k1, k2, lam1, lam2]):
            raise ValueError("Surface gains [k1, k2, λ1, λ2] must be positive for stability")

        # Adaptation rate must be positive
        if gamma <= 0:
            raise ValueError("Adaptation rate γ must be positive")

        # Warn if adaptation rate is too large
        if gamma > 1.0:
            import warnings
            warnings.warn("Large adaptation rate may cause instability", UserWarning)

    def _validate_adaptation_parameters(self) -> None:
        """Validate adaptation-specific parameters."""
        if self.leak_rate < 0 or self.leak_rate > 1:
            raise ValueError("leak_rate must be in [0, 1]")

        if self.adapt_rate_limit <= 0:
            raise ValueError("adapt_rate_limit must be positive")

        if self.K_min <= 0:
            raise ValueError("K_min must be positive")

        if self.K_max <= self.K_min:
            raise ValueError("K_max must be greater than K_min")

        if self.K_init < self.K_min or self.K_init > self.K_max:
            raise ValueError("K_init must be in [K_min, K_max]")

        if self.alpha <= 0 or self.alpha > 1:
            raise ValueError("alpha must be in (0, 1]")

        if self.dead_zone < 0:
            raise ValueError("dead_zone must be non-negative")

    def _validate_other_parameters(self) -> None:
        """Validate other configuration parameters."""
        if self.max_force <= 0:
            raise ValueError("max_force must be positive")

        if self.dt <= 0:
            raise ValueError("dt must be positive")

        if self.boundary_layer <= 0:
            raise ValueError("boundary_layer must be positive")

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
    def gamma(self) -> float:
        """Adaptation rate (γ)."""
        return self.gains[4]

    def get_surface_gains(self) -> List[float]:
        """Get sliding surface gains [k1, k2, λ1, λ2]."""
        return self.gains[:4]

    def get_adaptation_bounds(self) -> tuple[float, float]:
        """Get adaptation bounds (K_min, K_max)."""
        return (self.K_min, self.K_max)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            'gains': list(self.gains),
            'max_force': self.max_force,
            'dt': self.dt,
            'leak_rate': self.leak_rate,
            'adapt_rate_limit': self.adapt_rate_limit,
            'K_min': self.K_min,
            'K_max': self.K_max,
            'K_init': self.K_init,
            'alpha': self.alpha,
            'boundary_layer': self.boundary_layer,
            'smooth_switch': self.smooth_switch,
            'dead_zone': self.dead_zone
        }

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'AdaptiveSMCConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)

    @classmethod
    def create_default(cls, gains: List[float], max_force: float = 100.0,
                      dt: float = 0.01, **kwargs) -> 'AdaptiveSMCConfig':
        """Create configuration with sensible defaults."""
        return cls(
            gains=gains,
            max_force=max_force,
            dt=dt,
            **kwargs
        )