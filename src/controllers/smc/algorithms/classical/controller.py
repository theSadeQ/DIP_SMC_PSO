#==========================================================================================\\\
#============= src/controllers/smc/algorithms/classical/controller.py ================\\\
#==========================================================================================\\\

"""
Modular Classical SMC Controller.

Clean implementation using focused components:
- SlidingSurface: Surface computation
- EquivalentControl: Model-based feedforward
- BoundaryLayer: Chattering reduction
- Configuration: Type-safe parameters

Replaces the monolithic 458-line controller with composition of 50-100 line modules.
"""

from typing import Dict, List, Union, Optional, Any
import numpy as np
import logging

from ...core.sliding_surface import LinearSlidingSurface
from ...core.equivalent_control import EquivalentControl
from .boundary_layer import BoundaryLayer
from .config import ClassicalSMCConfig


class ModularClassicalSMC:
    """
    Modular Classical SMC controller using composition of focused components.

    Components:
    - Sliding surface: Computes s = λ₁ė₁ + c₁e₁ + λ₂ė₂ + c₂e₂
    - Equivalent control: Model-based u_eq = -(LM⁻¹B)⁻¹LM⁻¹F
    - Boundary layer: Continuous switching with chattering reduction
    """

    # Required for PSO optimization integration
    n_gains = 6  # [k1, k2, lam1, lam2, K, kd]

    def __init__(self, config: ClassicalSMCConfig):
        """
        Initialize modular classical SMC.

        Args:
            config: Type-safe configuration object
        """
        self.config = config

        # Initialize components
        self._surface = LinearSlidingSurface(config.get_surface_gains())
        self._equivalent = EquivalentControl(
            dynamics_model=config.dynamics_model,
            regularization=config.regularization,
            controllability_threshold=config.get_effective_controllability_threshold()
        )
        self._boundary_layer = BoundaryLayer(
            thickness=config.boundary_layer,
            slope=config.boundary_layer_slope,
            switch_method=config.switch_method
        )

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)

    def compute_control(self, state: np.ndarray, state_vars: Any, history: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute classical SMC control law.

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

            # 2. Compute surface derivative (simplified)
            surface_derivative = self._estimate_surface_derivative(state)

            # 3. Compute equivalent control (model-based feedforward)
            u_equivalent = self._equivalent.compute(state, self._surface, surface_derivative)

            # 4. Compute switching control (robust feedback)
            u_switching = self._boundary_layer.compute_switching_control(
                surface_value, self.config.K, surface_derivative
            )

            # 5. Compute derivative control (damping)
            u_derivative = self.config.kd * surface_derivative

            # 6. Combine control components
            u_total = u_equivalent + u_switching + u_derivative

            # 7. Apply saturation
            u_saturated = np.clip(u_total, -self.config.max_force, self.config.max_force)

            # 8. Create result
            return self._create_control_result(
                u_saturated, surface_value, surface_derivative,
                u_equivalent, u_switching, u_derivative, u_total
            )

        except Exception as e:
            self.logger.error(f"Control computation failed: {e}")
            return self._create_error_result(str(e))

    def _estimate_surface_derivative(self, state: np.ndarray) -> float:
        """Estimate surface derivative for derivative control."""
        # Simplified derivative estimation
        # In full implementation, this would use dynamics model
        if len(state) >= 6:
            theta1_dot = state[3]
            theta2_dot = state[5]
            return self.config.lam1 * theta1_dot + self.config.lam2 * theta2_dot
        return 0.0

    def _create_control_result(self, u_final: float, surface_value: float,
                             surface_derivative: float, u_eq: float,
                             u_switch: float, u_deriv: float, u_total: float) -> Dict[str, Any]:
        """Create structured control result."""
        return {
            # Main output
            'u': float(u_final),

            # Component breakdown
            'surface_value': float(surface_value),
            'surface_derivative': float(surface_derivative),
            'equivalent_control': float(u_eq),
            'switching_control': float(u_switch),
            'derivative_control': float(u_deriv),
            'total_before_saturation': float(u_total),

            # Status indicators
            'saturation_active': abs(u_total) > self.config.max_force,
            'in_boundary_layer': self._boundary_layer.is_in_boundary_layer(surface_value, surface_derivative),
            'controller_type': 'classical_smc',

            # Performance metrics
            'control_effort': abs(u_final),
            'surface_magnitude': abs(surface_value)
        }

    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """Create error result with safe defaults."""
        return {
            'u': 0.0,
            'error': error_msg,
            'controller_type': 'classical_smc',
            'safe_mode': True
        }

    @property
    def gains(self) -> List[float]:
        """Return controller gains for interface compatibility."""
        return list(self.config.gains)

    def reset(self) -> None:
        """Reset controller to initial state."""
        # Reset any internal state variables if they exist
        # Classical SMC typically doesn't have internal state to reset
        # But we ensure any analysis components are reset
        if hasattr(self._boundary_layer, 'reset'):
            self._boundary_layer.reset()
        if hasattr(self._surface, 'reset'):
            self._surface.reset()

    def get_parameters(self) -> Dict[str, Any]:
        """Get all controller parameters."""
        return {
            'gains': self.gains,
            'config': self.config.to_dict(),
            'surface_params': self._surface.get_coefficients(),
            'boundary_layer_params': self._boundary_layer.get_parameters()
        }

    def analyze_performance(self, surface_history: List[float],
                          control_history: List[float], dt: float = 0.01) -> Dict[str, Any]:
        """Analyze controller performance."""
        return self._boundary_layer.analyze_performance(surface_history, control_history, dt)


# Backward compatibility facade
class ClassicalSMC:
    """Backward-compatible facade for the modular Classical SMC."""

    def __init__(self, gains: Union[List[float], np.ndarray], max_force: float,
                 boundary_layer: float, dynamics_model: Optional[Any] = None, **kwargs):
        """
        Initialize Classical SMC with legacy interface.

        Args:
            gains: [k1, k2, lam1, lam2, K, kd]
            max_force: Maximum control force
            boundary_layer: Boundary layer thickness
            dynamics_model: Optional dynamics model
            **kwargs: Additional parameters
        """
        # Create modular configuration
        config = ClassicalSMCConfig(
            gains=list(gains),
            max_force=max_force,
            boundary_layer=boundary_layer,
            dynamics_model=dynamics_model,
            **kwargs
        )

        # Initialize modular controller
        self._controller = ModularClassicalSMC(config)

    def compute_control(self, state: np.ndarray, state_vars: Any, history: Dict[str, Any]) -> Dict[str, Any]:
        """Compute control (delegates to modular controller)."""
        return self._controller.compute_control(state, state_vars, history)

    @property
    def gains(self) -> List[float]:
        """Return controller gains."""
        return self._controller.gains

    def reset(self) -> None:
        """Reset controller to initial state."""
        self._controller.reset()

    def get_parameters(self) -> Dict[str, Any]:
        """Get controller parameters."""
        return self._controller.get_parameters()