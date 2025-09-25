#==========================================================================================\\\
#============ src/controllers/smc/algorithms/super_twisting/config.py ===============\\\
#==========================================================================================\\\

"""
Configuration Schema for Super-Twisting SMC.

Type-safe configuration for Super-Twisting Sliding Mode Control (STA-SMC).
Implements second-order sliding mode control for finite-time convergence.

Mathematical Requirements:
- Twisting gains: K1 > K2 > 0 for stability and finite-time convergence
- Surface gains: [k1, k2, λ1, λ2] must be positive for Hurwitz stability
- Anti-windup: Prevents integrator windup in the twisting algorithm
"""

from typing import List, Optional
from dataclasses import dataclass, field
import math


@dataclass(frozen=True)
class SuperTwistingSMCConfig:
    """
    Type-safe configuration for Super-Twisting SMC controller.

    Based on Super-Twisting algorithm theory:
    - Twisting gains K1, K2 must satisfy K1 > K2 > 0 for finite-time stability
    - Surface gains [k1, k2, λ1, λ2] must be positive for Hurwitz stability
    - Power exponent α ∈ (0, 1) determines convergence rate
    """

    # Required parameters
    gains: List[float] = field()                           # [K1, K2, k1, k2, lam1, lam2]
    max_force: float = field()                             # Control saturation limit
    dt: float = field()                                    # Control timestep

    # Super-Twisting specific parameters
    damping_gain: float = field(default=0.0)               # Additional damping
    anti_windup_gain: Optional[float] = field(default=None) # Anti-windup for integrator
    power_exponent: float = field(default=0.5)             # α for |s|^α term

    # Boundary layer and switching
    boundary_layer: float = field(default=0.01)            # Chattering reduction
    switch_method: str = field(default="tanh")             # Switching function type
    regularization: float = field(default=1e-10)           # Numerical regularization

    # Optional dynamics model
    dynamics_model: Optional[object] = field(default=None, compare=False)

    def __post_init__(self):
        """Validate configuration after creation."""
        self._validate_gains()
        self._validate_twisting_parameters()
        self._validate_other_parameters()

    def _validate_gains(self) -> None:
        """Validate gain vector according to Super-Twisting theory."""
        if len(self.gains) != 6:
            raise ValueError("Super-Twisting SMC requires exactly 6 gains: [K1, K2, k1, k2, lam1, lam2]")

        K1, K2, k1, k2, lam1, lam2 = self.gains

        # Twisting gains stability condition: K1 > K2 > 0
        if K1 <= 0 or K2 <= 0:
            raise ValueError("Twisting gains K1, K2 must be positive")

        if K2 >= K1:
            raise ValueError("Super-Twisting stability requires K1 > K2 > 0")

        # Surface gains must be positive for Hurwitz stability
        if any(g <= 0 for g in [k1, k2, lam1, lam2]):
            raise ValueError("Surface gains [k1, k2, λ1, λ2] must be positive for stability")

    def _validate_twisting_parameters(self) -> None:
        """Validate Super-Twisting specific parameters."""
        if self.damping_gain < 0:
            raise ValueError("Damping gain must be non-negative")

        if self.anti_windup_gain is not None and self.anti_windup_gain <= 0:
            raise ValueError("Anti-windup gain must be positive when specified")

        if not (0 < self.power_exponent <= 1):
            raise ValueError("Power exponent must be in (0, 1] for convergence")

        # Warn if power exponent is not 0.5 (standard Super-Twisting)
        if abs(self.power_exponent - 0.5) > 1e-6:
            import warnings
            warnings.warn(f"Non-standard power exponent {self.power_exponent}. "
                         "Standard Super-Twisting uses α = 0.5", UserWarning)

    def _validate_other_parameters(self) -> None:
        """Validate other configuration parameters."""
        if self.max_force <= 0:
            raise ValueError("max_force must be positive")

        if self.dt <= 0:
            raise ValueError("dt must be positive")

        if self.boundary_layer <= 0:
            raise ValueError("boundary_layer must be positive")

        if self.regularization <= 0:
            raise ValueError("regularization must be positive")

        if self.switch_method not in ("tanh", "linear", "sign"):
            raise ValueError("switch_method must be 'tanh', 'linear', or 'sign'")

    @property
    def K1(self) -> float:
        """First twisting gain."""
        return self.gains[0]

    @property
    def K2(self) -> float:
        """Second twisting gain."""
        return self.gains[1]

    @property
    def k1(self) -> float:
        """Joint 1 position gain."""
        return self.gains[2]

    @property
    def k2(self) -> float:
        """Joint 2 position gain."""
        return self.gains[3]

    @property
    def lam1(self) -> float:
        """Joint 1 velocity gain (λ₁)."""
        return self.gains[4]

    @property
    def lam2(self) -> float:
        """Joint 2 velocity gain (λ₂)."""
        return self.gains[5]

    def get_twisting_gains(self) -> tuple[float, float]:
        """Get Super-Twisting gains (K1, K2)."""
        return (self.K1, self.K2)

    def get_surface_gains(self) -> List[float]:
        """Get sliding surface gains [k1, k2, λ1, λ2]."""
        return self.gains[2:]

    def check_stability_conditions(self) -> dict:
        """
        Check Super-Twisting stability conditions.

        Returns:
            Dictionary with stability analysis
        """
        K1, K2 = self.get_twisting_gains()

        # Basic stability: K1 > K2 > 0
        basic_stable = K1 > K2 > 0

        # Enhanced stability condition (sufficient for finite-time convergence)
        # Requires specific relationship between K1 and K2
        ratio = K1 / K2 if K2 > 0 else float('inf')
        enhanced_stable = ratio > 1.1  # Margin for robustness

        # Convergence time estimate (approximate)
        if basic_stable and self.power_exponent == 0.5:
            # T_conv ≈ 2 / (K2^0.5) for standard Super-Twisting
            convergence_time_est = 2.0 / math.sqrt(K2) if K2 > 0 else float('inf')
        else:
            convergence_time_est = float('inf')

        return {
            'basic_stability': basic_stable,
            'enhanced_stability': enhanced_stable,
            'gain_ratio': ratio,
            'convergence_time_estimate': convergence_time_est,
            'power_exponent_standard': abs(self.power_exponent - 0.5) < 1e-6
        }

    def get_effective_anti_windup_gain(self) -> float:
        """Get effective anti-windup gain."""
        if self.anti_windup_gain is not None:
            return self.anti_windup_gain
        # Default: proportional to twisting gains
        return 0.1 * (self.K1 + self.K2)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            'gains': list(self.gains),
            'max_force': self.max_force,
            'dt': self.dt,
            'damping_gain': self.damping_gain,
            'anti_windup_gain': self.anti_windup_gain,
            'power_exponent': self.power_exponent,
            'boundary_layer': self.boundary_layer,
            'switch_method': self.switch_method,
            'regularization': self.regularization
        }

    @classmethod
    def from_dict(cls, config_dict: dict, dynamics_model=None) -> 'SuperTwistingSMCConfig':
        """Create configuration from dictionary."""
        config_dict = config_dict.copy()
        config_dict['dynamics_model'] = dynamics_model
        return cls(**config_dict)

    @classmethod
    def create_default(cls, gains: List[float], max_force: float = 100.0,
                      dt: float = 0.01, **kwargs) -> 'SuperTwistingSMCConfig':
        """Create configuration with sensible defaults."""
        return cls(
            gains=gains,
            max_force=max_force,
            dt=dt,
            **kwargs
        )

    @classmethod
    def create_from_classical_gains(cls, classical_gains: List[float],
                                   K1: float, K2: float, **kwargs) -> 'SuperTwistingSMCConfig':
        """
        Create Super-Twisting config from classical SMC gains.

        Args:
            classical_gains: [k1, k2, lam1, lam2] from classical SMC
            K1, K2: Super-Twisting gains (K1 > K2 > 0)
            **kwargs: Additional parameters

        Returns:
            Super-Twisting configuration
        """
        if len(classical_gains) < 4:
            raise ValueError("Classical gains must have at least 4 elements")

        if K2 >= K1 or K1 <= 0 or K2 <= 0:
            raise ValueError("Super-Twisting requires K1 > K2 > 0")

        sta_gains = [K1, K2] + list(classical_gains[:4])

        return cls(gains=sta_gains, **kwargs)