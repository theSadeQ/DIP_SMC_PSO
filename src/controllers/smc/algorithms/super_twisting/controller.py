#==========================================================================================\\\
#========= src/controllers/smc/algorithms/super_twisting/controller.py ===============\\\
#==========================================================================================\\\

"""
Modular Super-Twisting SMC Controller.

Implements Super-Twisting Sliding Mode Control using composed components:
- LinearSlidingSurface: Surface computation
- SuperTwistingAlgorithm: Second-order sliding mode control
- SwitchingFunction: Smooth chattering reduction

Provides finite-time convergence with chattering reduction through
second-order sliding mode dynamics.
"""

from typing import Dict, List, Union, Optional, Any
import numpy as np
import logging

from ...core.sliding_surface import LinearSlidingSurface
from ...core.switching_functions import SwitchingFunction
from .twisting_algorithm import SuperTwistingAlgorithm
from .config import SuperTwistingSMCConfig


class ModularSuperTwistingSMC:
    """
    Modular Super-Twisting SMC using composition of focused components.

    Super-Twisting control law:
    u = u₁ + u₂
    u₁ = -K₁|s|^α sign(s)
    u₂ = -K₂ ∫sign(s)dt

    Provides finite-time convergence when K₁ > K₂ > 0.
    """

    # Required for PSO optimization integration
    n_gains = 6  # [c1, lambda1, c2, lambda2, K1, K2]

    def __init__(self, config: SuperTwistingSMCConfig):
        """
        Initialize modular Super-Twisting SMC.

        Args:
            config: Type-safe configuration object
        """
        self.config = config

        # Initialize components
        self._surface = LinearSlidingSurface(config.get_surface_gains())
        self._switching = SwitchingFunction(config.switch_method)
        self._twisting_algorithm = SuperTwistingAlgorithm(
            K1=config.K1,
            K2=config.K2,
            alpha=config.power_exponent,
            anti_windup_limit=config.get_effective_anti_windup_gain(),
            regularization=config.regularization
        )

        # Internal state
        self._previous_surface = 0.0
        self._control_history = []

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)

    def compute_control(self, state: np.ndarray, state_vars: Any, history: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute Super-Twisting SMC control law.

        Args:
            state: System state [x, x_dot, theta1, theta1_dot, theta2, theta2_dot]
            state_vars: Controller internal state (for interface compatibility)
            history: Controller history (for interface compatibility)

        Returns:
            Control result dictionary
        """
        try:
            # 1. Compute sliding surface
            surface_value = self._surface.compute(state)

            # 2. Estimate surface derivative
            surface_derivative = self._estimate_surface_derivative(state, surface_value)

            # 3. Compute Super-Twisting control using algorithm
            twisting_result = self._twisting_algorithm.compute_control(
                surface_value=surface_value,
                dt=self.config.dt,
                switching_function=self.config.switch_method,
                boundary_layer=self.config.boundary_layer
            )

            # 4. Add damping if specified
            u_twisting = twisting_result['u_total']
            if self.config.damping_gain > 0:
                damping_control = -self.config.damping_gain * surface_derivative
                u_with_damping = u_twisting + damping_control
            else:
                u_with_damping = u_twisting
                damping_control = 0.0

            # 5. Apply saturation
            u_saturated = np.clip(u_with_damping, -self.config.max_force, self.config.max_force)

            # 6. Store control history
            self._control_history.append(u_saturated)
            if len(self._control_history) > 100:  # Limit history size
                self._control_history.pop(0)

            # 7. Update previous surface
            self._previous_surface = surface_value

            # 8. Create comprehensive result
            return self._create_control_result(
                u_saturated, surface_value, surface_derivative,
                twisting_result, damping_control, u_with_damping
            )

        except Exception as e:
            self.logger.error(f"Super-Twisting control computation failed: {e}")
            return self._create_error_result(str(e))

    def _estimate_surface_derivative(self, state: np.ndarray, current_surface: float) -> float:
        """Estimate surface derivative using finite differences."""
        if self.config.dt > 0:
            surface_derivative = (current_surface - self._previous_surface) / self.config.dt
        else:
            # Fallback: simplified derivative from joint velocities
            if len(state) >= 6:
                theta1_dot = state[3]
                theta2_dot = state[5]
                surface_derivative = self.config.lam1 * theta1_dot + self.config.lam2 * theta2_dot
            else:
                surface_derivative = 0.0

        return surface_derivative

    def _create_control_result(self, u_final: float, surface_value: float,
                             surface_derivative: float, twisting_result: Dict[str, float],
                             damping_control: float, u_before_sat: float) -> Dict[str, Any]:
        """Create structured control result."""
        return {
            # Main output
            'u': float(u_final),

            # Surface information
            'surface_value': float(surface_value),
            'surface_derivative': float(surface_derivative),

            # Super-Twisting components
            'u1_continuous': twisting_result['u1_continuous'],
            'u2_integral': twisting_result['u2_integral'],
            'integral_state': twisting_result['integral_state'],
            'switch_output': twisting_result['switch_output'],
            'surface_power': twisting_result['surface_power'],

            # Additional control components
            'damping_control': float(damping_control),
            'control_before_saturation': float(u_before_sat),

            # Twisting gains
            'K1': self.config.K1,
            'K2': self.config.K2,
            'gain_ratio': self.config.K1 / self.config.K2,

            # Status indicators
            'saturation_active': abs(u_before_sat) > self.config.max_force,
            'regularization_active': twisting_result['regularization_active'],
            'anti_windup_active': self._is_anti_windup_active(),
            'controller_type': 'super_twisting_smc',

            # Performance metrics
            'control_effort': abs(u_final),
            'surface_magnitude': abs(surface_value),
            'finite_time_convergence': self._twisting_algorithm.check_stability_condition(),

            # Stability analysis
            'stability_condition_satisfied': self.config.K1 > self.config.K2 > 0,
            'convergence_time_estimate': self._twisting_algorithm.estimate_convergence_time(abs(surface_value)),
            'lyapunov_function': self._twisting_algorithm.get_lyapunov_function(surface_value, surface_derivative),

            # Configuration info
            'power_exponent': self.config.power_exponent,
            'boundary_layer': self.config.boundary_layer,
            'switch_method': self.config.switch_method
        }

    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """Create error result with safe defaults."""
        return {
            'u': 0.0,
            'error': error_msg,
            'controller_type': 'super_twisting_smc',
            'safe_mode': True,
            'K1': self.config.K1,
            'K2': self.config.K2
        }

    def _is_anti_windup_active(self) -> bool:
        """Check if anti-windup is currently active."""
        if self.config.anti_windup_gain is None:
            return False

        twisting_state = self._twisting_algorithm.get_state_dict()
        integral_state = abs(twisting_state['internal_state']['integral_state'])
        limit = self.config.get_effective_anti_windup_gain()

        return integral_state >= 0.9 * limit

    @property
    def gains(self) -> List[float]:
        """Return controller gains [K1, K2, k1, k2, λ1, λ2]."""
        return list(self.config.gains)

    def get_twisting_gains(self) -> tuple[float, float]:
        """Get Super-Twisting gains (K1, K2)."""
        return self.config.get_twisting_gains()

    def set_twisting_gains(self, K1: float, K2: float) -> None:
        """
        Update Super-Twisting gains.

        Args:
            K1, K2: New twisting gains (must satisfy K1 > K2 > 0)
        """
        if K2 >= K1 or K1 <= 0 or K2 <= 0:
            raise ValueError("Super-Twisting requires K1 > K2 > 0")

        # Update algorithm gains
        self._twisting_algorithm.set_gains(K1, K2)

        # Update config (note: config is frozen, so this will need a new instance)
        # For now, just update the algorithm - config update would require reconstruction
        self.logger.info(f"Updated twisting gains: K1={K1}, K2={K2}")

    def reset_controller(self) -> None:
        """Reset controller to initial state."""
        self._twisting_algorithm.reset_state()
        self._previous_surface = 0.0
        self._control_history.clear()

    def reset(self) -> None:
        """Reset controller state (interface compliance).

        Provides standard reset() method interface for compatibility with
        other controllers and test frameworks.
        """
        self.reset_controller()

    def get_stability_analysis(self) -> Dict[str, Any]:
        """Get comprehensive stability analysis."""
        stability_info = self.config.check_stability_conditions()

        # Add algorithm-specific analysis
        if len(self._control_history) > 10:
            surface_history = [abs(self._previous_surface)] * len(self._control_history)  # Simplified
            performance_analysis = self._twisting_algorithm.analyze_performance(surface_history)
        else:
            performance_analysis = {'error': 'Insufficient control history'}

        return {
            'config_stability': stability_info,
            'algorithm_performance': performance_analysis,
            'current_state': self._twisting_algorithm.get_state_dict(),
            'theoretical_properties': {
                'finite_time_convergence': self.config.K1 > self.config.K2 > 0,
                'chattering_reduction': self.config.switch_method != "sign",
                'second_order_sliding': True,
                'power_exponent_standard': abs(self.config.power_exponent - 0.5) < 1e-6
            }
        }

    def tune_gains(self, K1: Optional[float] = None, K2: Optional[float] = None,
                   boundary_layer: Optional[float] = None) -> None:
        """
        Tune controller parameters during runtime.

        Args:
            K1, K2: New twisting gains
            boundary_layer: New boundary layer width
        """
        if K1 is not None and K2 is not None:
            self.set_twisting_gains(K1, K2)

        if boundary_layer is not None:
            if boundary_layer <= 0:
                raise ValueError("Boundary layer must be positive")
            # Update switching function (would need config reconstruction for full update)
            self.logger.info(f"Boundary layer tuning to {boundary_layer} (requires config update)")

    def get_parameters(self) -> Dict[str, Any]:
        """Get all controller parameters."""
        return {
            'twisting_gains': self.get_twisting_gains(),
            'surface_gains': self.config.get_surface_gains(),
            'config': self.config.to_dict(),
            'algorithm_state': self._twisting_algorithm.get_state_dict(),
            'surface_params': self._surface.get_coefficients(),
            'control_history_length': len(self._control_history)
        }

    def get_convergence_estimate(self, current_surface: Optional[float] = None) -> Dict[str, Any]:
        """
        Estimate convergence properties.

        Args:
            current_surface: Current surface value (uses last known if None)

        Returns:
            Convergence analysis
        """
        if current_surface is None:
            current_surface = abs(self._previous_surface)

        convergence_time = self._twisting_algorithm.estimate_convergence_time(current_surface)

        return {
            'estimated_convergence_time': convergence_time,
            'finite_time_convergence': convergence_time < float('inf'),
            'current_surface_magnitude': current_surface,
            'stability_margin': (self.config.K1 - self.config.K2) / self.config.K2,
            'convergence_rate_factor': self.config.K2 ** self.config.power_exponent
        }


# Backward compatibility facade
class SuperTwistingSMC:
    """Backward-compatible facade for the modular Super-Twisting SMC."""

    def __init__(self, gains: Union[List[float], np.ndarray], dt: float,
                 max_force: float, **kwargs):
        """
        Initialize Super-Twisting SMC with legacy interface.

        Args:
            gains: [K1, K2, k1, k2, lam1, lam2]
            dt: Control timestep
            max_force: Maximum control force
            **kwargs: Additional parameters
        """
        # Create modular configuration
        config = SuperTwistingSMCConfig(
            gains=list(gains),
            dt=dt,
            max_force=max_force,
            **kwargs
        )

        # Initialize modular controller
        self._controller = ModularSuperTwistingSMC(config)

    def compute_control(self, state: np.ndarray, state_vars: Any, history: Dict[str, Any]) -> Dict[str, Any]:
        """Compute control (delegates to modular controller)."""
        return self._controller.compute_control(state, state_vars, history)

    @property
    def gains(self) -> List[float]:
        """Return controller gains."""
        return self._controller.gains

    def get_twisting_gains(self) -> tuple[float, float]:
        """Get Super-Twisting gains."""
        return self._controller.get_twisting_gains()

    def reset_controller(self) -> None:
        """Reset controller state."""
        self._controller.reset_controller()

    def get_parameters(self) -> Dict[str, Any]:
        """Get controller parameters."""
        return self._controller.get_parameters()