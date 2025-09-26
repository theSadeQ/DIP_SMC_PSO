#==========================================================================================\\\
#================== src/plant/models/simplified/dynamics.py ===========================\\\
#==========================================================================================\\\

"""
Simplified DIP Dynamics Model.

Main dynamics model implementation combining all simplified DIP components.
Provides a clean, modular interface for the simplified double inverted
pendulum dynamics with numerical stability and performance optimizations.
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
from .config import SimplifiedDIPConfig
from .physics import SimplifiedPhysicsComputer, compute_simplified_dynamics_numba


class SimplifiedDIPDynamics(BaseDynamicsModel):
    """
    Simplified Double Inverted Pendulum Dynamics Model.

    Modular implementation of simplified DIP dynamics featuring:
    - Type-safe configuration with validation
    - Numerical stability monitoring and recovery
    - Performance optimizations with JIT compilation
    - Clean separation of physics computation
    - Comprehensive state validation
    """

    def __init__(
        self,
        config: Union[SimplifiedDIPConfig, Dict[str, Any]],
        enable_fast_mode: bool = False,
        enable_monitoring: bool = True
    ):
        """
        Initialize simplified DIP dynamics.

        Args:
            config: Validated configuration for simplified DIP or dictionary
            enable_fast_mode: Use JIT-compiled fast dynamics computation
            enable_monitoring: Enable performance and stability monitoring
        """
        # Handle config parameter conversion
        if isinstance(config, dict):
            if config:
                self.config = SimplifiedDIPConfig.from_dict(config)
            else:
                self.config = SimplifiedDIPConfig.create_default()
        elif isinstance(config, SimplifiedDIPConfig):
            self.config = config
        else:
            raise ValueError(f"config must be SimplifiedDIPConfig or dict, got {type(config)}")

        # Initialize base class
        super().__init__(self.config)

        self.enable_fast_mode = enable_fast_mode
        self.enable_monitoring = enable_monitoring

        # Initialize physics computer
        self.physics = SimplifiedPhysicsComputer(self.config)

        # Performance optimizations for fast mode
        if enable_fast_mode:
            self.physics.set_simplified_inertia(True)
            self.physics.enable_matrix_caching(True)

    def compute_dynamics(
        self,
        state: np.ndarray,
        control_input: np.ndarray,
        time: float = 0.0,
        **kwargs: Any
    ) -> DynamicsResult:
        """
        Compute simplified DIP dynamics.

        Args:
            state: State vector [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
            control_input: Control input [F] (force on cart)
            time: Current time (unused in this model)

        Returns:
            Dynamics computation result with state derivative
        """
        # Validate inputs
        if not self.validate_state(state):
            return self._create_failure_result(
                "Invalid state vector",
                state=state.copy(),
                time=time
            )

        if not self._validate_control_input(control_input):
            return self._create_failure_result(
                "Invalid control input",
                control_input=control_input.copy(),
                time=time
            )

        try:
            # Sanitize state if needed
            sanitized_state = self.sanitize_state(state)

            # Compute dynamics
            if self.enable_fast_mode:
                state_derivative = self._compute_fast_dynamics(sanitized_state, control_input)
            else:
                state_derivative = self._compute_standard_dynamics(sanitized_state, control_input)

            # Validate result
            if not self._validate_state_derivative(state_derivative):
                return self._create_failure_result(
                    "Invalid state derivative computed",
                    state=state.copy(),
                    control_input=control_input.copy(),
                    time=time
                )

            # Record monitoring statistics
            if self.enable_monitoring:
                self._record_successful_computation(sanitized_state)

            return self._create_success_result(
                state_derivative,
                state=sanitized_state.copy(),
                control_input=control_input.copy(),
                time=time,
                total_energy=self.physics.compute_total_energy(sanitized_state),
                kinetic_energy=self.physics.compute_kinetic_energy(sanitized_state),
                potential_energy=self.physics.compute_potential_energy(sanitized_state)
            )

        except NumericalInstabilityError as e:
            # Record instability for monitoring
            if self.enable_monitoring:
                self._record_numerical_instability(state)

            return self._create_failure_result(
                f"Numerical instability: {e}",
                state=state.copy(),
                control_input=control_input.copy(),
                time=time,
                error_type="numerical_instability"
            )

        except Exception as e:
            # Record general failure
            if self.enable_monitoring:
                self._record_computation_failure(state)

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
        Get physics matrices M, C, G at current state.

        Args:
            state: Current system state

        Returns:
            Tuple of (M, C, G) matrices
        """
        return self.physics.get_physics_matrices(state)

    def compute_total_energy(self, state: np.ndarray) -> float:
        """Compute total system energy."""
        return self.physics.compute_total_energy(state)

    def compute_linearization(
        self,
        equilibrium_state: np.ndarray,
        equilibrium_input: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute linearization around equilibrium point.

        Args:
            equilibrium_state: Equilibrium state (typically upright position)
            equilibrium_input: Equilibrium control input (typically zero)

        Returns:
            Tuple of (A, B) matrices for linear system ẋ = Ax + Bu
        """
        return self._compute_linearization_matrices(equilibrium_state, equilibrium_input)

    def get_equilibrium_states(self) -> Dict[str, np.ndarray]:
        """Get standard equilibrium states for the DIP system."""
        return {
            "upright": np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            "downward": np.array([0.0, np.pi, np.pi, 0.0, 0.0, 0.0]),
            "mixed_1": np.array([0.0, 0.0, np.pi, 0.0, 0.0, 0.0]),
            "mixed_2": np.array([0.0, np.pi, 0.0, 0.0, 0.0, 0.0])
        }

    def _setup_validation(self) -> None:
        """Setup state validation for simplified DIP."""
        self._state_validator = DIPStateValidator(
            position_bounds=(-10.0, 10.0),
            angle_bounds=(-4*np.pi, 4*np.pi),
            velocity_bounds=(-50.0, 50.0),
            angular_velocity_bounds=(-100.0, 100.0),
            wrap_angles=True,
            strict_validation=False
        )

    def _compute_standard_dynamics(
        self,
        state: np.ndarray,
        control_input: np.ndarray
    ) -> np.ndarray:
        """Compute dynamics using standard (modular) approach."""
        return self.physics.compute_dynamics_rhs(state, control_input)

    def _compute_fast_dynamics(
        self,
        state: np.ndarray,
        control_input: np.ndarray
    ) -> np.ndarray:
        """Compute dynamics using fast JIT-compiled approach."""
        return compute_simplified_dynamics_numba(
            state,
            control_input[0],
            self.config.cart_mass,
            self.config.pendulum1_mass,
            self.config.pendulum2_mass,
            self.config.pendulum1_length,
            self.config.pendulum2_length,
            self.config.pendulum1_com,
            self.config.pendulum2_com,
            self.config.pendulum1_inertia,
            self.config.pendulum2_inertia,
            self.config.gravity,
            self.config.cart_friction,
            self.config.joint1_friction,
            self.config.joint2_friction,
            self.config.regularization_alpha,
            self.config.min_regularization
        )

    def _validate_control_input(self, control_input: np.ndarray) -> bool:
        """Validate control input vector."""
        return (
            isinstance(control_input, np.ndarray) and
            control_input.shape == (1,) and
            np.all(np.isfinite(control_input)) and
            abs(control_input[0]) < 1000.0  # Reasonable force bound
        )

    def _validate_state_derivative(self, state_derivative: np.ndarray) -> bool:
        """Validate computed state derivative."""
        return (
            isinstance(state_derivative, np.ndarray) and
            state_derivative.shape == (6,) and
            np.all(np.isfinite(state_derivative))
        )

    def _compute_linearization_matrices(
        self,
        eq_state: np.ndarray,
        eq_input: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute linearization matrices A, B."""
        eps = 1e-8  # Finite difference step

        # Get reference dynamics
        dynamics_result = self.compute_dynamics(eq_state, eq_input)
        if not dynamics_result.success:
            raise ValueError("Cannot linearize: equilibrium point is unstable")

        f0 = dynamics_result.state_derivative

        # Compute A matrix (∂f/∂x)
        n = len(eq_state)
        A = np.zeros((n, n))
        for i in range(n):
            state_plus = eq_state.copy()
            state_plus[i] += eps

            dynamics_plus = self.compute_dynamics(state_plus, eq_input)
            if dynamics_plus.success:
                A[:, i] = (dynamics_plus.state_derivative - f0) / eps
            else:
                warnings.warn(f"Linearization: failed to compute derivative w.r.t. state[{i}]")

        # Compute B matrix (∂f/∂u)
        m = len(eq_input)
        B = np.zeros((n, m))
        for j in range(m):
            input_plus = eq_input.copy()
            input_plus[j] += eps

            dynamics_plus = self.compute_dynamics(eq_state, input_plus)
            if dynamics_plus.success:
                B[:, j] = (dynamics_plus.state_derivative - f0) / eps
            else:
                warnings.warn(f"Linearization: failed to compute derivative w.r.t. input[{j}]")

        return A, B

    def _record_successful_computation(self, state: np.ndarray) -> None:
        """Record successful computation for monitoring."""
        if hasattr(self, '_stability_monitor'):
            cond_num = self.physics.get_matrix_conditioning(state)
            self._stability_monitor.record_inversion(
                condition_number=cond_num,
                was_regularized=cond_num > self.config.max_condition_number,
                failed=False
            )

    def _record_numerical_instability(self, state: np.ndarray) -> None:
        """Record numerical instability for monitoring."""
        if hasattr(self, '_stability_monitor'):
            try:
                cond_num = self.physics.get_matrix_conditioning(state)
            except:
                cond_num = np.inf

            self._stability_monitor.record_inversion(
                condition_number=cond_num,
                was_regularized=True,
                failed=True
            )

    def _record_computation_failure(self, state: np.ndarray) -> None:
        """Record general computation failure for monitoring."""
        if hasattr(self, '_stability_monitor'):
            self._stability_monitor.record_inversion(
                condition_number=np.inf,
                was_regularized=False,
                failed=True
            )

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