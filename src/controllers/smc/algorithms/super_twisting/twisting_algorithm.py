#==========================================================================================\\\
#======== src/controllers/smc/algorithms/super_twisting/twisting_algorithm.py ========\\\
#==========================================================================================\\\

"""
Super-Twisting Algorithm Implementation.

Implements the core Super-Twisting sliding mode algorithm for finite-time convergence.
The algorithm provides second-order sliding mode control with chattering reduction.

Mathematical Background:
- Control law: u = u₁ + u₂
- u₁ = -K₁|s|^α sign(s)
- u₂ = -K₂ ∫sign(s)dt
- Stability: K₁ > K₂ > 0 for finite-time convergence
"""

from typing import Optional, Dict, Any
import numpy as np
import math


class SuperTwistingAlgorithm:
    """
    Core Super-Twisting sliding mode algorithm.

    Implements second-order sliding mode control with finite-time convergence:
    - Continuous control component: u₁ = -K₁|s|^α sign(s)
    - Integral component: u₂ = -K₂ ∫sign(s)dt
    """

    def __init__(self,
                 K1: float,
                 K2: float,
                 alpha: float = 0.5,
                 anti_windup_limit: Optional[float] = None,
                 regularization: float = 1e-10):
        """
        Initialize Super-Twisting algorithm.

        Args:
            K1: First twisting gain (K1 > K2 > 0)
            K2: Second twisting gain
            alpha: Power exponent ∈ (0, 1] (standard = 0.5)
            anti_windup_limit: Limit for integral component
            regularization: Small value to prevent division by zero
        """
        if K2 >= K1 or K1 <= 0 or K2 <= 0:
            raise ValueError("Super-Twisting requires K1 > K2 > 0")
        if not (0 < alpha <= 1):
            raise ValueError("Power exponent must be in (0, 1]")
        if regularization <= 0:
            raise ValueError("Regularization must be positive")

        self.K1 = K1
        self.K2 = K2
        self.alpha = alpha
        self.anti_windup_limit = anti_windup_limit
        self.regularization = regularization

        # Internal state
        self._integral_state = 0.0
        self._previous_surface = 0.0

    def compute_control(self, surface_value: float, dt: float,
                       switching_function: str = "tanh",
                       boundary_layer: float = 0.01) -> Dict[str, float]:
        """
        Compute Super-Twisting control law.

        Args:
            surface_value: Current sliding surface value s
            dt: Time step for integration
            switching_function: Type of switching function ("tanh", "linear", "sign")
            boundary_layer: Boundary layer width for smooth switching

        Returns:
            Dictionary with control components and diagnostics
        """
        # Compute switching function
        switch_output = self._compute_switching_function(
            surface_value, switching_function, boundary_layer
        )

        # First component: u₁ = -K₁|s|^α sign(s)
        if abs(surface_value) > self.regularization:
            u1 = -self.K1 * (abs(surface_value) ** self.alpha) * switch_output
        else:
            # Regularized version near s = 0
            u1 = -self.K1 * (self.regularization ** self.alpha) * switch_output

        # Second component: u₂ = -K₂ ∫sign(s)dt
        # Update integral state
        integral_increment = switch_output * dt
        self._integral_state += integral_increment

        # Apply anti-windup if specified
        if self.anti_windup_limit is not None:
            self._integral_state = np.clip(
                self._integral_state, -self.anti_windup_limit, self.anti_windup_limit
            )

        u2 = -self.K2 * self._integral_state

        # Total control
        u_total = u1 + u2

        # Store previous surface for derivative estimation
        self._previous_surface = surface_value

        return {
            'u_total': float(u_total),
            'u1_continuous': float(u1),
            'u2_integral': float(u2),
            'integral_state': float(self._integral_state),
            'switch_output': float(switch_output),
            'surface_power': float(abs(surface_value) ** self.alpha),
            'regularization_active': abs(surface_value) <= self.regularization
        }

    def _compute_switching_function(self, s: float, method: str, epsilon: float) -> float:
        """
        Compute switching function sign(s) with smooth approximation.

        Args:
            s: Surface value
            method: Switching method ("tanh", "linear", "sign")
            epsilon: Boundary layer width

        Returns:
            Switching function output
        """
        if method == "sign":
            return np.sign(s)
        elif method == "tanh":
            if epsilon <= 0:
                return np.sign(s)
            return np.tanh(s / epsilon)
        elif method == "linear":
            if epsilon <= 0:
                return np.sign(s)
            return np.clip(s / epsilon, -1, 1)
        else:
            raise ValueError(f"Unknown switching method: {method}")

    def reset_state(self) -> None:
        """Reset algorithm internal state."""
        self._integral_state = 0.0
        self._previous_surface = 0.0

    def set_gains(self, K1: float, K2: float) -> None:
        """
        Update twisting gains.

        Args:
            K1, K2: New twisting gains (must satisfy K1 > K2 > 0)
        """
        if K2 >= K1 or K1 <= 0 or K2 <= 0:
            raise ValueError("Super-Twisting requires K1 > K2 > 0")
        self.K1 = K1
        self.K2 = K2

    def get_gains(self) -> tuple[float, float]:
        """Get current twisting gains (K1, K2)."""
        return (self.K1, self.K2)

    def check_stability_condition(self) -> bool:
        """Check if current gains satisfy stability condition."""
        return self.K1 > self.K2 > 0

    def estimate_convergence_time(self, initial_surface: float = 1.0) -> float:
        """
        Estimate finite-time convergence time.

        For standard Super-Twisting (α = 0.5):
        T_conv ≈ 2|s₀|^(1-α) / K₂^α

        Args:
            initial_surface: Initial surface value |s₀|

        Returns:
            Estimated convergence time
        """
        if not self.check_stability_condition():
            return float('inf')

        if self.alpha == 0.5:
            # Standard formula for α = 0.5
            return 2.0 * math.sqrt(abs(initial_surface)) / math.sqrt(self.K2)
        else:
            # General formula
            if self.K2 <= 0 or initial_surface <= 0:
                return float('inf')
            return ((1 - self.alpha) * (abs(initial_surface) ** (1 - self.alpha))) / (self.K2 ** self.alpha)

    def analyze_performance(self, surface_history: list) -> Dict[str, Any]:
        """
        Analyze Super-Twisting performance from surface history.

        Args:
            surface_history: List of historical surface values

        Returns:
            Performance analysis dictionary
        """
        if len(surface_history) < 2:
            return {'error': 'Insufficient history for analysis'}

        surface_array = np.array(surface_history)

        # Convergence analysis
        final_values = surface_array[-min(50, len(surface_array)):]
        convergence_rate = -np.polyfit(range(len(surface_array)), np.log(np.abs(surface_array) + 1e-10), 1)[0]

        # Finite-time convergence detection
        convergence_threshold = 0.01
        convergence_idx = None
        for i, val in enumerate(surface_array):
            if abs(val) < convergence_threshold:
                convergence_idx = i
                break

        return {
            'stability_metrics': {
                'gains_satisfy_condition': self.check_stability_condition(),
                'gain_ratio': self.K1 / self.K2 if self.K2 > 0 else float('inf'),
                'stability_margin': (self.K1 - self.K2) / self.K2 if self.K2 > 0 else float('inf')
            },
            'convergence_metrics': {
                'convergence_rate': float(convergence_rate),
                'final_surface_rms': float(np.sqrt(np.mean(final_values**2))),
                'convergence_detected': convergence_idx is not None,
                'convergence_time_steps': convergence_idx if convergence_idx is not None else len(surface_array),
                'theoretical_convergence_time': self.estimate_convergence_time(abs(surface_array[0]))
            },
            'control_characteristics': {
                'integral_state': self._integral_state,
                'anti_windup_active': self.anti_windup_limit is not None and abs(self._integral_state) >= 0.9 * self.anti_windup_limit,
                'power_exponent': self.alpha,
                'regularization_threshold': self.regularization
            }
        }

    def get_lyapunov_function(self, surface_value: float, surface_derivative: float) -> float:
        """
        Compute Lyapunov function for stability analysis.

        For Super-Twisting: V = K₂|s| + 0.5(u₂ + K₁|s|^α sign(s))²

        Args:
            surface_value: Current surface value s
            surface_derivative: Surface derivative ṡ

        Returns:
            Lyapunov function value
        """
        s = surface_value
        s_abs = abs(s)

        # First term: K₂|s|
        V1 = self.K2 * s_abs

        # Second term: 0.5(u₂ + K₁|s|^α sign(s))²
        u2 = -self.K2 * self._integral_state
        u1_equiv = -self.K1 * (s_abs ** self.alpha) * np.sign(s) if s_abs > self.regularization else 0

        V2 = 0.5 * (u2 + u1_equiv) ** 2

        return V1 + V2

    def get_state_dict(self) -> Dict[str, Any]:
        """Get current algorithm state for logging/debugging."""
        return {
            'gains': {'K1': self.K1, 'K2': self.K2},
            'parameters': {
                'alpha': self.alpha,
                'anti_windup_limit': self.anti_windup_limit,
                'regularization': self.regularization
            },
            'internal_state': {
                'integral_state': self._integral_state,
                'previous_surface': self._previous_surface
            },
            'stability': {
                'gains_valid': self.check_stability_condition(),
                'gain_ratio': self.K1 / self.K2 if self.K2 > 0 else float('inf')
            }
        }