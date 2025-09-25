#==========================================================================================\\\
#============ src/controllers/smc/algorithms/adaptive/adaptation_law.py =============\\\
#==========================================================================================\\\

"""
Adaptive Gain Update Laws for Adaptive SMC.

Implements online gain adaptation algorithms based on sliding mode theory.
The adaptation law adjusts switching gain K(t) to handle unknown uncertainties.

Mathematical Background:
- Adaptation law: K̇ = γ|s| - σK (with leakage)
- Lyapunov stability: V̇ = sṡ + (K̃/γ)K̇ ≤ 0
- Bounded adaptation: K_min ≤ K(t) ≤ K_max
"""

from typing import Optional, Union
import numpy as np


class AdaptationLaw:
    """
    Online gain adaptation for Adaptive SMC.

    Implements adaptive laws that adjust switching gains based on
    sliding surface behavior to handle uncertain disturbances.
    """

    def __init__(self,
                 adaptation_rate: float,
                 leak_rate: float = 0.1,
                 rate_limit: float = 100.0,
                 bounds: tuple[float, float] = (0.1, 100.0),
                 dead_zone: float = 0.01):
        """
        Initialize adaptation law.

        Args:
            adaptation_rate: γ > 0, adaptation speed
            leak_rate: σ ∈ [0,1], leakage to prevent drift
            rate_limit: Maximum |K̇| to prevent fast adaptation
            bounds: (K_min, K_max) gain bounds
            dead_zone: |s| threshold below which adaptation stops
        """
        if adaptation_rate <= 0:
            raise ValueError("Adaptation rate must be positive")
        if not (0 <= leak_rate <= 1):
            raise ValueError("Leak rate must be in [0, 1]")
        if rate_limit <= 0:
            raise ValueError("Rate limit must be positive")
        if bounds[1] <= bounds[0]:
            raise ValueError("K_max must be greater than K_min")
        if dead_zone < 0:
            raise ValueError("Dead zone must be non-negative")

        self.gamma = adaptation_rate
        self.sigma = leak_rate
        self.rate_limit = rate_limit
        self.K_min, self.K_max = bounds
        self.dead_zone = dead_zone

        # Internal state
        self._K_current = (self.K_min + self.K_max) / 2  # Initialize at midpoint
        self._adaptation_history = []

    def update_gain(self, surface_value: float, dt: float,
                   uncertainty_estimate: float = 0.0) -> float:
        """
        Update adaptive gain using adaptation law.

        Implements: K̇ = γ|s| - σK + γ*uncertainty_estimate

        Args:
            surface_value: Current sliding surface value s
            dt: Time step for integration
            uncertainty_estimate: Estimated uncertainty bound

        Returns:
            Updated gain value K(t+dt)
        """
        # Apply dead zone - no adaptation if |s| < dead_zone
        if abs(surface_value) < self.dead_zone:
            adaptation_term = 0.0
        else:
            adaptation_term = self.gamma * abs(surface_value)

        # Leakage term to prevent parameter drift
        leakage_term = self.sigma * self._K_current

        # Uncertainty compensation
        uncertainty_term = self.gamma * uncertainty_estimate

        # Adaptation law: K̇ = γ|s| - σK + γ*unc_est
        K_dot = adaptation_term - leakage_term + uncertainty_term

        # Apply rate limiting
        K_dot = np.clip(K_dot, -self.rate_limit, self.rate_limit)

        # Integrate (Euler method)
        K_new = self._K_current + K_dot * dt

        # Apply bounds
        K_new = np.clip(K_new, self.K_min, self.K_max)

        # Store adaptation history
        self._adaptation_history.append({
            'time_step': len(self._adaptation_history),
            'surface_value': surface_value,
            'K_old': self._K_current,
            'K_new': K_new,
            'K_dot': K_dot,
            'adaptation_term': adaptation_term,
            'leakage_term': leakage_term
        })

        # Update current gain
        self._K_current = K_new
        return K_new

    def get_current_gain(self) -> float:
        """Get current adaptive gain value."""
        return self._K_current

    def reset_gain(self, initial_gain: Optional[float] = None) -> None:
        """
        Reset adaptive gain to initial value.

        Args:
            initial_gain: Reset value (default: midpoint of bounds)
        """
        if initial_gain is None:
            self._K_current = (self.K_min + self.K_max) / 2
        else:
            self._K_current = np.clip(initial_gain, self.K_min, self.K_max)
        self._adaptation_history.clear()

    def is_adaptation_active(self, surface_value: float) -> bool:
        """Check if adaptation is currently active."""
        return abs(surface_value) >= self.dead_zone

    def get_adaptation_rate(self, surface_value: float) -> float:
        """
        Get current adaptation rate K̇.

        Args:
            surface_value: Current surface value

        Returns:
            Instantaneous adaptation rate
        """
        if not self.is_adaptation_active(surface_value):
            return -self.sigma * self._K_current  # Only leakage

        adaptation_term = self.gamma * abs(surface_value)
        leakage_term = self.sigma * self._K_current
        return adaptation_term - leakage_term

    def analyze_adaptation_performance(self) -> dict:
        """
        Analyze adaptation performance from history.

        Returns:
            Performance metrics dictionary
        """
        if len(self._adaptation_history) < 2:
            return {'error': 'Insufficient adaptation history'}

        history = np.array([
            [h['K_old'], h['K_new'], h['K_dot'], h['surface_value']]
            for h in self._adaptation_history
        ])

        K_values = history[:, 1]  # K_new column
        K_dots = history[:, 2]    # K_dot column
        surface_values = history[:, 3]  # surface_value column

        return {
            'gain_statistics': {
                'mean_gain': float(np.mean(K_values)),
                'std_gain': float(np.std(K_values)),
                'min_gain': float(np.min(K_values)),
                'max_gain': float(np.max(K_values)),
                'final_gain': float(K_values[-1])
            },
            'adaptation_statistics': {
                'mean_adaptation_rate': float(np.mean(np.abs(K_dots))),
                'max_adaptation_rate': float(np.max(np.abs(K_dots))),
                'adaptation_activity': float(np.mean(np.abs(K_dots) > 1e-6)),
                'convergence_indicator': float(np.std(K_values[-min(50, len(K_values)):])),
            },
            'performance_indicators': {
                'bounds_utilization': float((np.max(K_values) - np.min(K_values)) / (self.K_max - self.K_min)),
                'time_at_upper_bound': float(np.mean(K_values >= 0.95 * self.K_max)),
                'time_at_lower_bound': float(np.mean(K_values <= 1.05 * self.K_min)),
                'surface_correlation': float(np.corrcoef(np.abs(surface_values), K_values)[0, 1]) if len(K_values) > 1 else 0.0
            }
        }

    def set_adaptation_parameters(self, gamma: Optional[float] = None,
                                 sigma: Optional[float] = None,
                                 rate_limit: Optional[float] = None) -> None:
        """
        Update adaptation parameters during runtime.

        Args:
            gamma: New adaptation rate
            sigma: New leak rate
            rate_limit: New rate limit
        """
        if gamma is not None:
            if gamma <= 0:
                raise ValueError("Adaptation rate must be positive")
            self.gamma = gamma

        if sigma is not None:
            if not (0 <= sigma <= 1):
                raise ValueError("Leak rate must be in [0, 1]")
            self.sigma = sigma

        if rate_limit is not None:
            if rate_limit <= 0:
                raise ValueError("Rate limit must be positive")
            self.rate_limit = rate_limit

    def get_lyapunov_derivative(self, surface_value: float, surface_derivative: float) -> float:
        """
        Compute Lyapunov function derivative for stability analysis.

        For adaptive SMC: V̇ = sṡ + (K̃/γ)K̇
        Where K̃ = K - K* (gain error)

        Args:
            surface_value: Current surface value s
            surface_derivative: Surface derivative ṡ

        Returns:
            Lyapunov derivative (should be ≤ 0 for stability)
        """
        # Simplified analysis - assumes K* (optimal gain) is at upper bound
        K_star = self.K_max
        K_tilde = self._K_current - K_star

        # Surface contribution
        surface_term = surface_value * surface_derivative

        # Adaptation contribution
        K_dot = self.get_adaptation_rate(surface_value)
        adaptation_term = (K_tilde / self.gamma) * K_dot

        return surface_term + adaptation_term


class ModifiedAdaptationLaw(AdaptationLaw):
    """
    Modified adaptation law with additional robustness features.

    Includes projection operator and improved stability properties.
    """

    def __init__(self, *args, projection_margin: float = 0.1, **kwargs):
        """
        Initialize modified adaptation law.

        Args:
            projection_margin: Safety margin for projection operator
            *args, **kwargs: Standard adaptation law parameters
        """
        super().__init__(*args, **kwargs)
        self.projection_margin = projection_margin

    def update_gain(self, surface_value: float, dt: float,
                   uncertainty_estimate: float = 0.0) -> float:
        """Update gain with projection operator."""
        # Standard adaptation law
        adaptation_term = self.gamma * abs(surface_value) if abs(surface_value) >= self.dead_zone else 0.0
        leakage_term = self.sigma * self._K_current
        uncertainty_term = self.gamma * uncertainty_estimate

        K_dot = adaptation_term - leakage_term + uncertainty_term

        # Apply projection operator near bounds
        if self._K_current <= self.K_min + self.projection_margin and K_dot < 0:
            K_dot = max(0, K_dot)  # Project positive near lower bound
        elif self._K_current >= self.K_max - self.projection_margin and K_dot > 0:
            K_dot = min(0, K_dot)  # Project negative near upper bound

        # Apply rate limiting
        K_dot = np.clip(K_dot, -self.rate_limit, self.rate_limit)

        # Integrate and bound
        K_new = np.clip(self._K_current + K_dot * dt, self.K_min, self.K_max)

        # Update history and current value
        self._adaptation_history.append({
            'time_step': len(self._adaptation_history),
            'surface_value': surface_value,
            'K_old': self._K_current,
            'K_new': K_new,
            'K_dot': K_dot,
            'adaptation_term': adaptation_term,
            'leakage_term': leakage_term,
            'projection_active': self._is_projection_active(K_dot)
        })

        self._K_current = K_new
        return K_new

    def _is_projection_active(self, K_dot: float) -> bool:
        """Check if projection operator is currently active."""
        near_lower = self._K_current <= self.K_min + self.projection_margin and K_dot < 0
        near_upper = self._K_current >= self.K_max - self.projection_margin and K_dot > 0
        return near_lower or near_upper