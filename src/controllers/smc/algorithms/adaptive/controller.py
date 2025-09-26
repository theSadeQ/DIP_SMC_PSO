#==========================================================================================\\\
#============= src/controllers/smc/algorithms/adaptive/controller.py ================\\\
#==========================================================================================\\\

"""
Modular Adaptive SMC Controller.

Implements Adaptive Sliding Mode Control using composed components:
- LinearSlidingSurface: Surface computation
- AdaptationLaw: Online gain adjustment
- UncertaintyEstimator: Disturbance bound estimation
- SwitchingFunction: Smooth chattering reduction

Replaces the monolithic 427-line controller with composition of focused modules.
"""

from typing import Dict, List, Union, Optional, Any
import numpy as np
import logging

from ...core.sliding_surface import LinearSlidingSurface
from ...core.switching_functions import SwitchingFunction
from .adaptation_law import AdaptationLaw
from .parameter_estimation import UncertaintyEstimator
from .config import AdaptiveSMCConfig


class ModularAdaptiveSMC:
    """
    Modular Adaptive SMC using composition of focused components.

    Adaptive SMC law: u = -K(t) * sign(s)
    Where K(t) adapts online: K̇ = γ|s| - σK
    """

    # Required for PSO optimization integration
    n_gains = 5  # [c1, lambda1, c2, lambda2, adaptation_rate]

    def __init__(self, config: AdaptiveSMCConfig):
        """
        Initialize modular adaptive SMC.

        Args:
            config: Type-safe configuration object
        """
        self.config = config

        # Initialize components
        self._surface = LinearSlidingSurface(config.get_surface_gains())
        self._switching = SwitchingFunction("tanh" if config.smooth_switch else "linear")
        self._adaptation = AdaptationLaw(
            adaptation_rate=config.gamma,
            leak_rate=config.leak_rate,
            rate_limit=config.adapt_rate_limit,
            bounds=config.get_adaptation_bounds(),
            dead_zone=config.dead_zone
        )
        self._uncertainty_estimator = UncertaintyEstimator(
            window_size=50,
            forgetting_factor=0.95,
            initial_estimate=1.0
        )

        # Initialize adaptive gain
        self._adaptation.reset_gain(config.K_init)

        # Internal state
        self._previous_surface = 0.0
        self._control_history = []

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)

    def compute_control(self, state: np.ndarray, state_vars: Any, history: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute adaptive SMC control law.

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

            # 3. Update uncertainty estimate
            if len(self._control_history) > 0:
                last_control = self._control_history[-1]
                uncertainty_bound = self._uncertainty_estimator.update_estimate(
                    surface_value, surface_derivative, last_control, self.config.dt
                )
            else:
                uncertainty_bound = self._uncertainty_estimator.get_uncertainty_bound()

            # 4. Update adaptive gain
            adaptive_gain = self._adaptation.update_gain(
                surface_value, self.config.dt, uncertainty_bound
            )

            # 5. Compute switching control
            switching_output = self._switching.compute(surface_value, self.config.boundary_layer)
            u_adaptive = -adaptive_gain * switching_output

            # 6. Apply saturation
            u_saturated = np.clip(u_adaptive, -self.config.max_force, self.config.max_force)

            # 7. Store control history
            self._control_history.append(u_saturated)
            if len(self._control_history) > 100:  # Limit history size
                self._control_history.pop(0)

            # 8. Update previous surface
            self._previous_surface = surface_value

            # 9. Create result
            return self._create_control_result(
                u_saturated, surface_value, surface_derivative,
                adaptive_gain, uncertainty_bound, switching_output, u_adaptive
            )

        except Exception as e:
            self.logger.error(f"Adaptive control computation failed: {e}")
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
                             surface_derivative: float, adaptive_gain: float,
                             uncertainty_bound: float, switching_output: float,
                             u_before_sat: float) -> Dict[str, Any]:
        """Create structured control result."""
        return {
            # Main output
            'u': float(u_final),

            # Surface information
            'surface_value': float(surface_value),
            'surface_derivative': float(surface_derivative),

            # Adaptive components
            'adaptive_gain': float(adaptive_gain),
            'uncertainty_bound': float(uncertainty_bound),
            'switching_output': float(switching_output),
            'control_before_saturation': float(u_before_sat),

            # Status indicators
            'saturation_active': abs(u_before_sat) > self.config.max_force,
            'adaptation_active': self._adaptation.is_adaptation_active(surface_value),
            'controller_type': 'adaptive_smc',

            # Performance metrics
            'control_effort': abs(u_final),
            'surface_magnitude': abs(surface_value),
            'adaptation_rate': self._adaptation.get_adaptation_rate(surface_value),

            # Bounds information
            'gain_bounds': self.config.get_adaptation_bounds(),
            'gain_utilization': (adaptive_gain - self.config.K_min) / (self.config.K_max - self.config.K_min)
        }

    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """Create error result with safe defaults."""
        return {
            'u': 0.0,
            'error': error_msg,
            'controller_type': 'adaptive_smc',
            'safe_mode': True,
            'adaptive_gain': self._adaptation.get_current_gain()
        }

    @property
    def gains(self) -> List[float]:
        """Return controller gains (including current adaptive gain)."""
        static_gains = list(self.config.gains)
        current_adaptive_gain = self._adaptation.get_current_gain()
        return static_gains + [current_adaptive_gain]

    def get_adaptive_gain(self) -> float:
        """Get current adaptive gain value."""
        return self._adaptation.get_current_gain()

    def reset(self) -> None:
        """Reset controller to initial state (standard interface)."""
        self.reset_adaptation()

    def reset_adaptation(self, initial_gain: Optional[float] = None) -> None:
        """Reset adaptive components to initial state."""
        self._adaptation.reset_gain(initial_gain or self.config.K_init)
        self._previous_surface = 0.0
        self._control_history.clear()

    def get_adaptation_analysis(self) -> Dict[str, Any]:
        """Get comprehensive adaptation analysis."""
        adaptation_analysis = self._adaptation.analyze_adaptation_performance()
        uncertainty_analysis = self._uncertainty_estimator.analyze_estimation_quality()

        return {
            'adaptation_performance': adaptation_analysis,
            'uncertainty_estimation': uncertainty_analysis,
            'current_state': {
                'adaptive_gain': self._adaptation.get_current_gain(),
                'uncertainty_bound': self._uncertainty_estimator.get_uncertainty_bound(),
                'control_history_length': len(self._control_history)
            },
            'configuration': self.config.to_dict()
        }

    def tune_adaptation_parameters(self, gamma: Optional[float] = None,
                                  sigma: Optional[float] = None,
                                  rate_limit: Optional[float] = None) -> None:
        """Tune adaptation parameters during runtime."""
        self._adaptation.set_adaptation_parameters(gamma, sigma, rate_limit)

    def get_parameters(self) -> Dict[str, Any]:
        """Get all controller parameters."""
        return {
            'static_gains': self.config.gains,
            'current_adaptive_gain': self._adaptation.get_current_gain(),
            'config': self.config.to_dict(),
            'surface_params': self._surface.get_coefficients(),
            'adaptation_bounds': self.config.get_adaptation_bounds()
        }


# Backward compatibility facade
class AdaptiveSMC:
    """Backward-compatible facade for the modular Adaptive SMC."""

    def __init__(self, gains: Union[List[float], np.ndarray], dt: float,
                 max_force: float, **kwargs):
        """
        Initialize Adaptive SMC with legacy interface.

        Args:
            gains: [k1, k2, lam1, lam2, gamma]
            dt: Control timestep
            max_force: Maximum control force
            **kwargs: Additional parameters
        """
        # Create modular configuration
        config = AdaptiveSMCConfig(
            gains=list(gains),
            dt=dt,
            max_force=max_force,
            **kwargs
        )

        # Initialize modular controller
        self._controller = ModularAdaptiveSMC(config)

    def compute_control(self, state: np.ndarray, state_vars: Any, history: Dict[str, Any]) -> Dict[str, Any]:
        """Compute control (delegates to modular controller)."""
        return self._controller.compute_control(state, state_vars, history)

    @property
    def gains(self) -> List[float]:
        """Return controller gains."""
        return self._controller.gains

    def get_adaptive_gain(self) -> float:
        """Get current adaptive gain."""
        return self._controller.get_adaptive_gain()

    def reset(self) -> None:
        """Reset controller to initial state."""
        self._controller.reset()

    def reset_adaptation(self) -> None:
        """Reset adaptation state."""
        self._controller.reset_adaptation()

    def get_parameters(self) -> Dict[str, Any]:
        """Get controller parameters."""
        return self._controller.get_parameters()