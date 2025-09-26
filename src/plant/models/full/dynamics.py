#========================================================================================\
#===========================src/plant/models/full/dynamics.py============================\
#========================================================================================\

"""
Full Fidelity DIP Dynamics Model.

Complete high-fidelity implementation of the double inverted pendulum
with all nonlinear effects, advanced numerical integration, and
comprehensive physics modeling.
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
from .config import FullDIPConfig
from .physics import FullFidelityPhysicsComputer


class FullDIPDynamics(BaseDynamicsModel):
    """
    Full Fidelity Double Inverted Pendulum Dynamics Model.

    High-fidelity implementation featuring:
    - Complete nonlinear dynamics with all coupling effects
    - Advanced friction models (viscous + Coulomb)
    - Aerodynamic forces and wind effects
    - High-precision adaptive integration
    - Comprehensive disturbance modeling
    - Research-grade numerical accuracy
    """

    def __init__(
        self,
        config: Union[FullDIPConfig, Dict[str, Any]],
        enable_monitoring: bool = True,
        enable_validation: bool = True
    ):
        """
        Initialize full-fidelity DIP dynamics.

        Args:
            config: Validated configuration for full DIP model or dictionary
            enable_monitoring: Enable comprehensive performance monitoring
            enable_validation: Enable detailed state validation
        """
        # Handle config parameter conversion
        if isinstance(config, dict):
            if config:
                self.config = FullDIPConfig.from_dict(config)
            else:
                self.config = FullDIPConfig.create_default()
        elif isinstance(config, FullDIPConfig):
            self.config = config
        else:
            raise ValueError(f"config must be FullDIPConfig or dict, got {type(config)}")

        self.enable_monitoring = enable_monitoring
        self.enable_validation = enable_validation

        # Initialize base class
        super().__init__(self.config)

        # Initialize physics computer
        self.physics = FullFidelityPhysicsComputer(self.config)

        # Setup integration state tracking
        self.integration_stats = {
            'total_steps': 0,
            'successful_steps': 0,
            'rejected_steps': 0,
            'average_step_size': 0.0,
            'min_step_size': float('inf'),
            'max_step_size': 0.0
        }

        # Wind model state (if enabled)
        self.wind_state = np.array([0.0, 0.0])  # [vx, vy]

    def compute_dynamics(
        self,
        state: np.ndarray,
        control_input: np.ndarray,
        time: float = 0.0,
        **kwargs: Any
    ) -> DynamicsResult:
        """
        Compute full-fidelity DIP dynamics.

        Args:
            state: State vector [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
            control_input: Control input [F] (force on cart)
            time: Current time for time-varying effects
            **kwargs: Additional parameters (wind_velocity, etc.)

        Returns:
            Dynamics computation result with comprehensive diagnostics
        """
        # Enhanced input validation
        if not self._validate_inputs(state, control_input):
            return self._create_failure_result(
                "Invalid inputs",
                state=state.copy(),
                control_input=control_input.copy(),
                time=time
            )

        try:
            # Sanitize and validate state
            if self.enable_validation:
                sanitized_state = self.sanitize_state(state)
                if not self._check_physical_constraints(sanitized_state):
                    return self._create_failure_result(
                        "Physical constraints violated",
                        state=state.copy(),
                        control_input=control_input.copy(),
                        time=time
                    )
            else:
                sanitized_state = state

            # Extract optional parameters
            wind_velocity = kwargs.get('wind_velocity', None)
            if self.config.wind_model_enabled and wind_velocity is None:
                wind_velocity = self._update_wind_model(time)

            # Compute high-fidelity dynamics
            state_derivative = self.physics.compute_complete_dynamics_rhs(
                sanitized_state, control_input, time, wind_velocity
            )

            # Validate result
            if not self._validate_state_derivative(state_derivative):
                return self._create_failure_result(
                    "Invalid state derivative computed",
                    state=sanitized_state.copy(),
                    control_input=control_input.copy(),
                    time=time
                )

            # Comprehensive diagnostics
            diagnostics = self._compute_diagnostics(sanitized_state, state_derivative, time)

            # Record successful computation
            if self.enable_monitoring:
                self._record_successful_computation(sanitized_state, diagnostics)

            return self._create_success_result(
                state_derivative,
                state=sanitized_state.copy(),
                control_input=control_input.copy(),
                time=time,
                wind_velocity=wind_velocity.copy() if wind_velocity is not None else None,
                **diagnostics
            )

        except NumericalInstabilityError as e:
            if self.enable_monitoring:
                self._record_numerical_instability(state, str(e))

            return self._create_failure_result(
                f"Numerical instability: {e}",
                state=state.copy(),
                control_input=control_input.copy(),
                time=time,
                error_type="numerical_instability"
            )

        except Exception as e:
            if self.enable_monitoring:
                self._record_computation_failure(state, str(e))

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
        Get complete physics matrices M, C, G at current state.

        Args:
            state: Current system state

        Returns:
            Tuple of (M, C, G) matrices with full nonlinear effects
        """
        M = self.physics._compute_full_inertia_matrix(state)
        C = self.physics._compute_full_coriolis_matrix(state)
        G = self.physics._compute_full_gravity_vector(state)
        return M, C, G

    def compute_energy_analysis(self, state: np.ndarray) -> Dict[str, float]:
        """
        Compute comprehensive energy analysis.

        Args:
            state: Current system state

        Returns:
            Dictionary with detailed energy breakdown
        """
        # Total energy components
        kinetic = self._compute_kinetic_energy(state)
        potential = self._compute_potential_energy(state)
        total = kinetic + potential

        # Detailed kinetic energy breakdown
        kinetic_cart = self._compute_cart_kinetic_energy(state)
        kinetic_pend1 = self._compute_pendulum_kinetic_energy(state, 1)
        kinetic_pend2 = self._compute_pendulum_kinetic_energy(state, 2)

        # Potential energy breakdown
        potential_pend1 = self._compute_pendulum_potential_energy(state, 1)
        potential_pend2 = self._compute_pendulum_potential_energy(state, 2)

        return {
            'total_energy': total,
            'kinetic_energy': kinetic,
            'potential_energy': potential,
            'kinetic_cart': kinetic_cart,
            'kinetic_pendulum1': kinetic_pend1,
            'kinetic_pendulum2': kinetic_pend2,
            'potential_pendulum1': potential_pend1,
            'potential_pendulum2': potential_pend2,
            'energy_ratio': kinetic / (total + 1e-12)  # Avoid division by zero
        }

    def compute_stability_metrics(self, state: np.ndarray) -> Dict[str, float]:
        """
        Compute stability and conditioning metrics.

        Args:
            state: Current system state

        Returns:
            Dictionary with stability metrics
        """
        M, C, G = self.get_physics_matrices(state)

        # Matrix conditioning
        cond_M = np.linalg.cond(M)
        det_M = np.linalg.det(M)

        # Eigenvalue analysis
        eigenvals_M = np.linalg.eigvals(M)
        min_eigenval = np.min(eigenvals_M)
        max_eigenval = np.max(eigenvals_M)

        # System energy
        energy_analysis = self.compute_energy_analysis(state)

        return {
            'inertia_condition_number': cond_M,
            'inertia_determinant': det_M,
            'min_eigenvalue': min_eigenval,
            'max_eigenvalue': max_eigenval,
            'eigenvalue_ratio': max_eigenval / (min_eigenval + 1e-12),
            'total_energy': energy_analysis['total_energy'],
            'kinetic_potential_ratio': (energy_analysis['kinetic_energy'] /
                                      (energy_analysis['potential_energy'] + 1e-12))
        }

    def set_wind_model(self, wind_function):
        """Set custom wind velocity function wind_function(time) -> [vx, vy]."""
        self._wind_function = wind_function

    def get_integration_statistics(self) -> Dict[str, Any]:
        """Get integration performance statistics."""
        stats = self.integration_stats.copy()
        if stats['total_steps'] > 0:
            stats['success_rate'] = stats['successful_steps'] / stats['total_steps']
            stats['rejection_rate'] = stats['rejected_steps'] / stats['total_steps']
        else:
            stats['success_rate'] = 0.0
            stats['rejection_rate'] = 0.0

        return stats

    def _setup_validation(self) -> None:
        """Setup enhanced state validation for full DIP."""
        if self.enable_validation:
            self._state_validator = DIPStateValidator(
                position_bounds=self.config.cart_position_limits,
                angle_bounds=(-8*np.pi, 8*np.pi),  # Allow more rotations for full model
                velocity_bounds=(-self.config.cart_velocity_limit, self.config.cart_velocity_limit),
                angular_velocity_bounds=(-self.config.joint_velocity_limits, self.config.joint_velocity_limits),
                wrap_angles=True,
                strict_validation=False
            )

    def _validate_inputs(self, state: np.ndarray, control_input: np.ndarray) -> bool:
        """Enhanced input validation for full model."""
        # Basic validation
        if not self.validate_state(state):
            return False

        if not self._validate_control_input(control_input):
            return False

        # Enhanced validations for full model
        if self.enable_validation:
            # Check for extreme values that might cause numerical issues
            if np.any(np.abs(state[3:]) > 100.0):  # Very high velocities
                warnings.warn("Extreme velocities detected", UserWarning)

            if np.abs(control_input[0]) > 10 * self.config.cart_mass * self.config.gravity:
                warnings.warn("Extreme control input detected", UserWarning)

        return True

    def _check_physical_constraints(self, state: np.ndarray) -> bool:
        """Check physical constraints specific to full model."""
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Cart position limits
        if self.config.cart_position_limits is not None:
            if not (self.config.cart_position_limits[0] <= x <= self.config.cart_position_limits[1]):
                return False

        # Joint angle limits
        if self.config.joint1_angle_limits is not None:
            if not (self.config.joint1_angle_limits[0] <= theta1 <= self.config.joint1_angle_limits[1]):
                return False

        if self.config.joint2_angle_limits is not None:
            if not (self.config.joint2_angle_limits[0] <= theta2 <= self.config.joint2_angle_limits[1]):
                return False

        # Velocity limits
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
        """Compute comprehensive diagnostics for full model."""
        diagnostics = {}

        # Energy analysis
        energy_analysis = self.compute_energy_analysis(state)
        diagnostics.update(energy_analysis)

        # Stability metrics
        stability_metrics = self.compute_stability_metrics(state)
        diagnostics.update(stability_metrics)

        # Physics forces breakdown
        forces = self._compute_force_breakdown(state)
        diagnostics.update(forces)

        # Integration quality metrics
        if hasattr(self, '_last_state') and hasattr(self, '_last_time'):
            dt = time - self._last_time
            if dt > 0:
                numerical_derivative = (state - self._last_state) / dt
                derivative_error = np.linalg.norm(numerical_derivative[3:] - state_derivative[3:])
                diagnostics['derivative_consistency_error'] = derivative_error

        # Store for next iteration
        self._last_state = state.copy()
        self._last_time = time

        return diagnostics

    def _compute_force_breakdown(self, state: np.ndarray) -> Dict[str, np.ndarray]:
        """Compute breakdown of all forces acting on the system."""
        # Get individual force components
        friction_forces = self.physics._compute_friction_forces(state)
        aero_forces = self.physics._compute_aerodynamic_forces(state, self.wind_state)
        disturbance_forces = self.physics._compute_disturbance_forces(state, 0.0)

        return {
            'friction_forces': friction_forces,
            'aerodynamic_forces': aero_forces,
            'disturbance_forces': disturbance_forces,
            'total_nonconservative_forces': friction_forces + aero_forces + disturbance_forces
        }

    def _update_wind_model(self, time: float) -> np.ndarray:
        """Update wind velocity model."""
        if hasattr(self, '_wind_function'):
            self.wind_state = np.array(self._wind_function(time))
        else:
            # Default: gentle sinusoidal wind
            wind_magnitude = 0.5  # m/s
            wind_frequency = 0.1  # Hz
            self.wind_state = np.array([
                wind_magnitude * np.sin(2 * np.pi * wind_frequency * time),
                0.0
            ])

        return self.wind_state

    def _compute_kinetic_energy(self, state: np.ndarray) -> float:
        """Compute total kinetic energy."""
        return (self._compute_cart_kinetic_energy(state) +
                self._compute_pendulum_kinetic_energy(state, 1) +
                self._compute_pendulum_kinetic_energy(state, 2))

    def _compute_potential_energy(self, state: np.ndarray) -> float:
        """Compute total potential energy."""
        return (self._compute_pendulum_potential_energy(state, 1) +
                self._compute_pendulum_potential_energy(state, 2))

    def _compute_cart_kinetic_energy(self, state: np.ndarray) -> float:
        """Compute kinetic energy of cart."""
        _, _, _, x_dot, _, _ = state
        return 0.5 * self.config.cart_mass * x_dot**2

    def _compute_pendulum_kinetic_energy(self, state: np.ndarray, pendulum_num: int) -> float:
        """Compute kinetic energy of specified pendulum."""
        if pendulum_num == 1:
            mass = self.config.pendulum1_mass
            length = self.config.pendulum1_com
            inertia = self.config.pendulum1_inertia
            theta_dot = state[4]
        else:
            mass = self.config.pendulum2_mass
            length = self.config.pendulum2_com
            inertia = self.config.pendulum2_inertia
            theta_dot = state[5]

        # Translational kinetic energy of COM
        com_velocity = self.physics._compute_pendulum_tip_velocity(pendulum_num, state, length)
        T_trans = 0.5 * mass * np.dot(com_velocity, com_velocity)

        # Rotational kinetic energy about COM
        T_rot = 0.5 * inertia * theta_dot**2

        return T_trans + T_rot

    def _compute_pendulum_potential_energy(self, state: np.ndarray, pendulum_num: int) -> float:
        """Compute potential energy of specified pendulum."""
        _, theta1, theta2, _, _, _ = state

        if pendulum_num == 1:
            mass = self.config.pendulum1_mass
            length = self.config.pendulum1_com
            height = length * (1 - np.cos(theta1))
        else:
            mass = self.config.pendulum2_mass
            length = self.config.pendulum2_com
            # Pendulum 2 height relative to its attachment point
            height = (self.config.pendulum1_length * (1 - np.cos(theta1)) +
                     length * (1 - np.cos(theta2)))

        return mass * self.config.gravity * height

    def _validate_control_input(self, control_input: np.ndarray) -> bool:
        """Validate control input for full model."""
        return (
            isinstance(control_input, np.ndarray) and
            control_input.shape == (1,) and
            np.all(np.isfinite(control_input))
        )

    def _validate_state_derivative(self, state_derivative: np.ndarray) -> bool:
        """Enhanced validation of computed state derivative."""
        is_valid = (
            isinstance(state_derivative, np.ndarray) and
            state_derivative.shape == (6,) and
            np.all(np.isfinite(state_derivative))
        )

        if is_valid and self.enable_validation:
            # Check for physically unreasonable accelerations
            max_reasonable_accel = 1000.0  # m/s² or rad/s²
            if np.any(np.abs(state_derivative[3:]) > max_reasonable_accel):
                warnings.warn("Extreme accelerations computed", UserWarning)

        return is_valid

    def _record_successful_computation(self, state: np.ndarray, diagnostics: Dict[str, Any]) -> None:
        """Record successful computation with full diagnostics."""
        if hasattr(self, '_stability_monitor'):
            cond_num = diagnostics.get('inertia_condition_number', np.inf)
            self._stability_monitor.record_inversion(
                condition_number=cond_num,
                was_regularized=cond_num > self.config.max_condition_number,
                failed=False
            )

        # Update integration statistics
        self.integration_stats['successful_steps'] += 1
        self.integration_stats['total_steps'] += 1

    def _record_numerical_instability(self, state: np.ndarray, error_msg: str) -> None:
        """Record numerical instability with context."""
        if hasattr(self, '_stability_monitor'):
            self._stability_monitor.record_inversion(
                condition_number=np.inf,
                was_regularized=True,
                failed=True
            )

        self.integration_stats['rejected_steps'] += 1
        self.integration_stats['total_steps'] += 1

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

    def _record_computation_failure(self, state: np.ndarray, error_msg: str) -> None:
        """Record general computation failure."""
        if hasattr(self, '_stability_monitor'):
            self._stability_monitor.record_inversion(
                condition_number=np.inf,
                was_regularized=False,
                failed=True
            )

        self.integration_stats['rejected_steps'] += 1
        self.integration_stats['total_steps'] += 1

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
