#==========================================================================================\\\
#======================= src/plant/models/lowrank/dynamics.py ===========================\\\
#==========================================================================================\\\

"""
Low-rank DIP Dynamics Model.

Simplified implementation optimized for computational efficiency while
maintaining essential double inverted pendulum dynamics. Ideal for
fast prototyping, educational purposes, and real-time applications.
"""

from __future__ import annotations
from typing import Tuple, Optional, Dict, Any, Union
import numpy as np
import warnings

from ..base import BaseDynamicsModel, DynamicsResult
from ...core import (
    DIPStateValidator,
    NumericalInstabilityError,
    NumericalStabilityMonitor
)
from .config import LowRankDIPConfig
from .physics import LowRankPhysicsComputer


class LowRankDIPDynamics(BaseDynamicsModel):
    """
    Low-rank Double Inverted Pendulum Dynamics Model.

    Simplified implementation featuring:
    - Fast computation with reduced complexity
    - Essential dynamics preservation
    - Optional linearization for stability analysis
    - Small-angle approximations for efficiency
    - Educational clarity with simplified physics
    """

    def __init__(
        self,
        config: Union[LowRankDIPConfig, Dict[str, Any]],
        enable_monitoring: bool = False,
        enable_validation: bool = True
    ):
        """
        Initialize low-rank DIP dynamics.

        Args:
            config: Validated configuration for low-rank DIP model or dictionary
            enable_monitoring: Enable performance monitoring (optional for speed)
            enable_validation: Enable state validation
        """
        # Handle config parameter conversion
        if isinstance(config, dict):
            if config:
                self.config = LowRankDIPConfig.from_dict(config)
            else:
                self.config = LowRankDIPConfig.create_default()
        elif isinstance(config, LowRankDIPConfig):
            self.config = config
        else:
            raise ValueError(f"config must be LowRankDIPConfig or dict, got {type(config)}")

        self.enable_monitoring = enable_monitoring
        self.enable_validation = enable_validation

        # Initialize base class
        super().__init__(self.config)

        # Initialize physics computer
        self.physics = LowRankPhysicsComputer(self.config)

        # Setup simplified integration tracking
        self.computation_stats = {
            'total_computations': 0,
            'successful_computations': 0,
            'failed_computations': 0,
            'average_computation_time': 0.0
        }

        # Linearized system matrices (cached)
        self._linearized_matrices: Optional[Tuple[np.ndarray, np.ndarray]] = None
        self._linearization_point = None

    def compute_dynamics(
        self,
        state: np.ndarray,
        control_input: np.ndarray,
        time: float = 0.0,
        **kwargs: Any
    ) -> DynamicsResult:
        """
        Compute low-rank DIP dynamics.

        Args:
            state: State vector [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
            control_input: Control input [F] (force on cart)
            time: Current time
            **kwargs: Additional parameters (unused in low-rank model)

        Returns:
            Dynamics computation result
        """
        # Basic input validation
        if not self._validate_inputs(state, control_input):
            return self._create_failure_result(
                "Invalid inputs",
                state=state.copy(),
                control_input=control_input.copy(),
                time=time
            )

        try:
            # Optionally sanitize state
            if self.enable_validation:
                sanitized_state = self.sanitize_state(state)
                if not self._check_state_bounds(sanitized_state):
                    warnings.warn("State exceeds configured bounds", UserWarning)
            else:
                sanitized_state = state

            # Compute simplified dynamics
            state_derivative = self.physics.compute_simplified_dynamics_rhs(
                sanitized_state, control_input, time
            )

            # Validate result
            if not self.physics.validate_computation(sanitized_state, state_derivative):
                return self._create_failure_result(
                    "Invalid state derivative computed",
                    state=sanitized_state.copy(),
                    control_input=control_input.copy(),
                    time=time
                )

            # Compute diagnostics if needed
            diagnostics = {}
            if self.enable_monitoring:
                diagnostics = self._compute_diagnostics(sanitized_state, state_derivative, time)

            # Record successful computation
            self._record_successful_computation()

            return self._create_success_result(
                state_derivative,
                state=sanitized_state.copy(),
                control_input=control_input.copy(),
                time=time,
                **diagnostics
            )

        except NumericalInstabilityError as e:
            self._record_failed_computation()
            return self._create_failure_result(
                f"Numerical instability: {e}",
                state=state.copy(),
                control_input=control_input.copy(),
                time=time,
                error_type="numerical_instability"
            )

        except Exception as e:
            self._record_failed_computation()
            return self._create_failure_result(
                f"Dynamics computation failed: {e}",
                state=state.copy(),
                control_input=control_input.copy(),
                time=time,
                error_type="computation_error"
            )

    def get_physics_matrices(
        self,
        state: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get simplified physics matrices M, C, G at current state.

        Args:
            state: Current system state

        Returns:
            Tuple of (M, C, G) matrices (simplified)
        """
        return self.physics.compute_simplified_matrices(state)

    def get_linearized_system(
        self,
        equilibrium_point: str = "upright",
        force_recompute: bool = False
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get linearized system matrices around equilibrium point.

        Args:
            equilibrium_point: Equilibrium to linearize around
            force_recompute: Force recomputation even if cached

        Returns:
            Tuple of (A, B) matrices for linearized system
        """
        if (self._linearized_matrices is None or
            self._linearization_point != equilibrium_point or
            force_recompute):

            self._linearized_matrices = self.config.get_linearized_matrices(equilibrium_point)
            self._linearization_point = equilibrium_point

        return self._linearized_matrices

    def compute_linearized_dynamics(
        self,
        state: np.ndarray,
        control_input: np.ndarray,
        equilibrium_point: str = "upright"
    ) -> np.ndarray:
        """
        Compute dynamics using linearized model.

        Args:
            state: Current state
            control_input: Control input
            equilibrium_point: Linearization point

        Returns:
            State derivative from linearized model
        """
        A, B = self.get_linearized_system(equilibrium_point)

        # Compute deviation from equilibrium
        if equilibrium_point == "upright":
            equilibrium_state = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        elif equilibrium_point == "downward":
            equilibrium_state = np.array([0.0, np.pi, np.pi, 0.0, 0.0, 0.0])
        else:
            raise ValueError(f"Unknown equilibrium point: {equilibrium_point}")

        delta_state = state - equilibrium_state

        # Linear dynamics: ẋ = Ax + Bu
        state_derivative = A @ delta_state + B @ control_input.reshape(-1, 1).flatten()

        return state_derivative

    def compute_energy_analysis(self, state: np.ndarray) -> Dict[str, float]:
        """
        Compute simplified energy analysis.

        Args:
            state: Current system state

        Returns:
            Dictionary with energy breakdown
        """
        return self.physics.compute_energy(state)

    def compute_stability_metrics(self, state: np.ndarray) -> Dict[str, float]:
        """
        Compute simplified stability metrics.

        Args:
            state: Current system state

        Returns:
            Dictionary with stability metrics
        """
        return self.physics.compute_stability_metrics(state)

    def get_computation_statistics(self) -> Dict[str, Any]:
        """Get computation performance statistics."""
        stats = self.computation_stats.copy()
        if stats['total_computations'] > 0:
            stats['success_rate'] = stats['successful_computations'] / stats['total_computations']
            stats['failure_rate'] = stats['failed_computations'] / stats['total_computations']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0

        return stats

    def step(self, state: np.ndarray, control_input: np.ndarray, dt: float) -> np.ndarray:
        """
        Simplified single-step integration (for compatibility).

        Args:
            state: Current state
            control_input: Control input
            dt: Time step

        Returns:
            Next state using Euler integration
        """
        result = self.compute_dynamics(state, control_input)

        if not result.success:
            warnings.warn(f"Dynamics computation failed: {result.info.get('failure_reason', 'Unknown')}")
            return state  # Return current state if computation fails

        # Simple Euler integration
        return state + dt * result.state_derivative

    def _setup_validation(self) -> None:
        """Setup simplified state validation for low-rank DIP."""
        if self.enable_validation:
            self._state_validator = DIPStateValidator(
                position_bounds=self.config.cart_position_limits,
                angle_bounds=(-4*np.pi, 4*np.pi),  # Allow multiple rotations
                velocity_bounds=(-self.config.cart_velocity_limit, self.config.cart_velocity_limit),
                angular_velocity_bounds=(-self.config.joint_velocity_limits, self.config.joint_velocity_limits),
                wrap_angles=True,
                strict_validation=False  # Relaxed for low-rank model
            )

    def _validate_inputs(self, state: np.ndarray, control_input: np.ndarray) -> bool:
        """Basic input validation for low-rank model."""
        # State validation
        if not self.validate_state(state):
            return False

        # Control input validation
        if not self._validate_control_input(control_input):
            return False

        return True

    def _validate_control_input(self, control_input: np.ndarray) -> bool:
        """Validate control input."""
        return (
            isinstance(control_input, np.ndarray) and
            control_input.shape == (1,) and
            np.all(np.isfinite(control_input)) and
            abs(control_input[0]) <= self.config.force_limit
        )

    def _check_state_bounds(self, state: np.ndarray) -> bool:
        """Check if state is within configured bounds."""
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Check position bounds
        if self.config.cart_position_limits is not None:
            if not (self.config.cart_position_limits[0] <= x <= self.config.cart_position_limits[1]):
                return False

        # Check velocity bounds
        if abs(x_dot) > self.config.cart_velocity_limit:
            return False

        if abs(theta1_dot) > self.config.joint_velocity_limits or abs(theta2_dot) > self.config.joint_velocity_limits:
            return False

        return True

    def _compute_diagnostics(
        self,
        state: np.ndarray,
        state_derivative: np.ndarray,
        time: float
    ) -> Dict[str, Any]:
        """Compute simplified diagnostics."""
        diagnostics = {}

        # Energy analysis
        energy_analysis = self.compute_energy_analysis(state)
        diagnostics.update(energy_analysis)

        # Stability metrics
        stability_metrics = self.compute_stability_metrics(state)
        diagnostics.update(stability_metrics)

        # Basic quality metrics
        diagnostics['max_acceleration'] = np.max(np.abs(state_derivative[3:]))
        diagnostics['acceleration_norm'] = np.linalg.norm(state_derivative[3:])

        return diagnostics

    def _record_successful_computation(self) -> None:
        """Record successful computation."""
        self.computation_stats['total_computations'] += 1
        self.computation_stats['successful_computations'] += 1

    def _record_failed_computation(self) -> None:
        """Record failed computation."""
        self.computation_stats['total_computations'] += 1
        self.computation_stats['failed_computations'] += 1

    def _rhs_core(self, state: np.ndarray, u: float = 0.0) -> np.ndarray:
        """
        Compatibility method for legacy code expecting _rhs_core.

        This method provides backward compatibility for code that expects
        the '_rhs_core' method interface. Maps to the standard compute_dynamics
        interface.

        Args:
            state: System state vector [x, dx, theta1, dtheta1, theta2, dtheta2]
            u: Control input (scalar force)

        Returns:
            State derivative vector
        """
        control_input = np.array([u]) if np.isscalar(u) else u
        result = self.compute_dynamics(state, control_input)

        if result.success:
            return result.state_derivative
        else:
            # For compatibility, return zeros if computation fails
            return np.zeros_like(state)