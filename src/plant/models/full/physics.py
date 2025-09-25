#========================================================================================\
#============================src/plant/models/full/physics.py============================\
#========================================================================================\

"""
Full Fidelity Physics Computation for DIP.

Complete high-fidelity physics computation including all nonlinear effects,
advanced friction models, aerodynamic forces, and coupling terms for the
double inverted pendulum system.
"""

from __future__ import annotations
from typing import Tuple, Any, Optional
import numpy as np

try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from ...core import (
    DIPPhysicsMatrices,
    AdaptiveRegularizer,
    MatrixInverter,
    NumericalInstabilityError
)
from .config import FullDIPConfig


class FullFidelityPhysicsComputer:
    """
    Full-fidelity physics computation for DIP dynamics.

    Implements complete nonlinear dynamics with:
    - All coupling terms and nonlinear effects
    - Advanced friction modeling (viscous + Coulomb)
    - Aerodynamic forces and drag
    - Gyroscopic and Coriolis effects
    - High-precision matrix computation
    """

    def __init__(self, config: FullDIPConfig):
        """
        Initialize full-fidelity physics computer.

        Args:
            config: Validated configuration for full DIP model
        """
        self.config = config

        # Setup base physics matrices
        self.base_matrices = DIPPhysicsMatrices(config)

        # Setup high-precision numerical stability
        self.regularizer = AdaptiveRegularizer(
            regularization_alpha=config.regularization_alpha,
            max_condition_number=config.max_condition_number,
            min_regularization=config.min_regularization,
            use_fixed_regularization=False  # Always use adaptive for full model
        )
        self.matrix_inverter = MatrixInverter(self.regularizer)

        # Precompute commonly used constants
        self._setup_cached_parameters()

    def compute_complete_dynamics_rhs(
        self,
        state: np.ndarray,
        control_input: np.ndarray,
        time: float = 0.0,
        wind_velocity: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compute complete right-hand side of dynamics equation.

        Implements the full nonlinear dynamics:
        M(q)q̈ + C(q,q̇)q̇ + G(q) + F_friction + F_aero + F_disturbance = u

        Args:
            state: State vector [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
            control_input: Control input [F] (force on cart)
            time: Current time for time-varying effects
            wind_velocity: Wind velocity vector [vx, vy] if aerodynamics enabled

        Returns:
            State derivative vector
        """
        # Extract state components
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state
        position = np.array([x, theta1, theta2])
        velocity = np.array([x_dot, theta1_dot, theta2_dot])

        try:
            # Compute base physics matrices
            M = self._compute_full_inertia_matrix(state)
            C = self._compute_full_coriolis_matrix(state)
            G = self._compute_full_gravity_vector(state)

            # Prepare control vector
            u = np.array([control_input[0], 0.0, 0.0])

            # Compute additional force terms
            F_friction = self._compute_friction_forces(state)
            F_aero = self._compute_aerodynamic_forces(state, wind_velocity)
            F_disturbance = self._compute_disturbance_forces(state, time)

            # Total forcing: u - C·q̇ - G - F_friction - F_aero - F_disturbance
            forcing = u - C @ velocity - G - F_friction - F_aero - F_disturbance

            # Solve for accelerations with high precision
            if self.config.use_iterative_refinement:
                accelerations = self._solve_with_refinement(M, forcing)
            else:
                accelerations = self.matrix_inverter.solve_linear_system(M, forcing)

            # Construct state derivative
            state_derivative = np.concatenate([velocity, accelerations])

            return state_derivative

        except (np.linalg.LinAlgError, NumericalInstabilityError) as e:
            raise NumericalInstabilityError(f"Full dynamics computation failed: {e}")

    def _compute_full_inertia_matrix(self, state: np.ndarray) -> np.ndarray:
        """Compute full inertia matrix with all coupling terms."""
        _, theta1, theta2, _, _, _ = state

        return self._compute_full_inertia_matrix_numba(
            theta1, theta2,
            self.config.cart_mass,
            self.config.pendulum1_mass,
            self.config.pendulum2_mass,
            self.config.pendulum1_length,
            self.config.pendulum2_length,
            self.config.pendulum1_com,
            self.config.pendulum2_com,
            self.config.pendulum1_inertia,
            self.config.pendulum2_inertia
        )

    def _compute_full_coriolis_matrix(self, state: np.ndarray) -> np.ndarray:
        """Compute full Coriolis matrix with all nonlinear terms."""
        _, theta1, theta2, _, theta1_dot, theta2_dot = state

        return self._compute_full_coriolis_matrix_numba(
            theta1, theta2, theta1_dot, theta2_dot,
            self.config.pendulum1_mass,
            self.config.pendulum2_mass,
            self.config.pendulum1_length,
            self.config.pendulum2_length,
            self.config.pendulum1_com,
            self.config.pendulum2_com,
            self.config.include_coriolis_effects,
            self.config.include_centrifugal_effects,
            self.config.include_gyroscopic_effects
        )

    def _compute_full_gravity_vector(self, state: np.ndarray) -> np.ndarray:
        """Compute full gravity vector."""
        return self.base_matrices.compute_gravity_vector(state)

    def _compute_friction_forces(self, state: np.ndarray) -> np.ndarray:
        """
        Compute advanced friction forces.

        Combines viscous and Coulomb friction models:
        F_friction = F_viscous + F_coulomb
        """
        _, _, _, x_dot, theta1_dot, theta2_dot = state

        # Viscous friction (linear in velocity)
        F_viscous = np.array([
            -self.config.cart_viscous_friction * x_dot,
            -self.config.joint1_viscous_friction * theta1_dot,
            -self.config.joint2_viscous_friction * theta2_dot
        ])

        # Coulomb friction (constant magnitude, opposite to velocity direction)
        F_coulomb = np.array([
            -self.config.cart_coulomb_friction * np.sign(x_dot) if abs(x_dot) > 1e-6 else 0.0,
            -self.config.joint1_coulomb_friction * np.sign(theta1_dot) if abs(theta1_dot) > 1e-6 else 0.0,
            -self.config.joint2_coulomb_friction * np.sign(theta2_dot) if abs(theta2_dot) > 1e-6 else 0.0
        ])

        return F_viscous + F_coulomb

    def _compute_aerodynamic_forces(
        self,
        state: np.ndarray,
        wind_velocity: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compute aerodynamic drag forces on pendulums.

        F_drag = 0.5 * ρ * Cd * A * v_rel² * sign(v_rel)
        """
        if not self.config.include_aerodynamic_forces:
            return np.zeros(3)

        _, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Default wind velocity
        if wind_velocity is None:
            wind_velocity = np.array([0.0, 0.0])

        # Compute pendulum tip velocities in world frame
        v1_tip = self._compute_pendulum_tip_velocity(
            1, state, self.config.pendulum1_length
        )
        v2_tip = self._compute_pendulum_tip_velocity(
            2, state, self.config.pendulum2_length
        )

        # Relative velocities (pendulum velocity - wind velocity)
        v1_rel = v1_tip - wind_velocity
        v2_rel = v2_tip - wind_velocity

        # Drag forces
        rho = self.config.air_density

        F1_drag = (0.5 * rho * self.config.pendulum1_drag_coefficient *
                   self.config.pendulum1_cross_section *
                   np.linalg.norm(v1_rel) * v1_rel)

        F2_drag = (0.5 * rho * self.config.pendulum2_drag_coefficient *
                   self.config.pendulum2_cross_section *
                   np.linalg.norm(v2_rel) * v2_rel)

        # Transform drag forces to generalized coordinates
        # (This is a simplified transformation - full implementation would
        # require Jacobian matrices for proper force transformation)
        F_aero = np.array([
            -(F1_drag[0] + F2_drag[0]) * 0.1,  # Approximate coupling to cart
            -F1_drag[1] * self.config.pendulum1_length * 0.5,  # Torque on pendulum 1
            -F2_drag[1] * self.config.pendulum2_length * 0.5   # Torque on pendulum 2
        ])

        return F_aero

    def _compute_disturbance_forces(self, state: np.ndarray, time: float) -> np.ndarray:
        """Compute external disturbance forces."""
        F_disturbance = np.zeros(3)

        # Base excitation (sinusoidal ground motion)
        if self.config.base_excitation_enabled:
            # Example: sinusoidal base excitation
            excitation_freq = 1.0  # Hz
            excitation_amplitude = 0.1  # m/s²
            base_accel = excitation_amplitude * np.sin(2 * np.pi * excitation_freq * time)

            # Base excitation affects all masses
            total_mass = (self.config.cart_mass +
                         self.config.pendulum1_mass +
                         self.config.pendulum2_mass)
            F_disturbance[0] += total_mass * base_accel

        return F_disturbance

    def _compute_pendulum_tip_velocity(
        self,
        pendulum_num: int,
        state: np.ndarray,
        length: float
    ) -> np.ndarray:
        """Compute velocity of pendulum tip in world coordinates."""
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        if pendulum_num == 1:
            # Pendulum 1 tip position: (x + L1*sin(θ1), L1*cos(θ1))
            tip_vx = x_dot + length * np.cos(theta1) * theta1_dot
            tip_vy = -length * np.sin(theta1) * theta1_dot
        else:
            # Pendulum 2 tip position relative to pendulum 1 tip
            # Chain rule for velocities
            tip_vx = (x_dot +
                     self.config.pendulum1_length * np.cos(theta1) * theta1_dot +
                     length * np.cos(theta2) * theta2_dot)
            tip_vy = (-self.config.pendulum1_length * np.sin(theta1) * theta1_dot -
                     length * np.sin(theta2) * theta2_dot)

        return np.array([tip_vx, tip_vy])

    def _solve_with_refinement(self, A: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Solve linear system with iterative refinement for higher accuracy."""
        # Initial solution
        x = self.matrix_inverter.solve_linear_system(A, b)

        # Iterative refinement
        for _ in range(2):  # Usually 1-2 iterations sufficient
            residual = b - A @ x
            correction = self.matrix_inverter.solve_linear_system(A, residual)
            x += correction

            # Check convergence
            if np.linalg.norm(correction) / np.linalg.norm(x) < 1e-12:
                break

        return x

    def _setup_cached_parameters(self) -> None:
        """Setup frequently used parameters for efficiency."""
        self.total_mass = (self.config.cart_mass +
                          self.config.pendulum1_mass +
                          self.config.pendulum2_mass)

    @staticmethod
    @njit
    def _compute_full_inertia_matrix_numba(
        theta1: float, theta2: float,
        m0: float, m1: float, m2: float,
        L1: float, L2: float, Lc1: float, Lc2: float,
        I1: float, I2: float
    ) -> np.ndarray:
        """JIT-compiled full inertia matrix computation."""
        c1 = np.cos(theta1)
        c2 = np.cos(theta2)
        c12 = np.cos(theta1 - theta2)

        # Full inertia matrix with all coupling terms
        M11 = m0 + m1 + m2
        M12 = (m1 * Lc1 + m2 * L1) * c1 + m2 * Lc2 * c2
        M13 = m2 * Lc2 * c2

        M21 = M12
        M22 = (m1 * Lc1**2 + m2 * L1**2) + I1 + m2 * Lc2**2 + I2 + 2 * m2 * L1 * Lc2 * c12
        M23 = m2 * Lc2**2 + I2 + m2 * L1 * Lc2 * c12

        M31 = M13
        M32 = M23
        M33 = m2 * Lc2**2 + I2

        M = np.array([
            [M11, M12, M13],
            [M21, M22, M23],
            [M31, M32, M33]
        ])

        return M

    @staticmethod
    @njit
    def _compute_full_coriolis_matrix_numba(
        theta1: float, theta2: float,
        theta1_dot: float, theta2_dot: float,
        m1: float, m2: float,
        L1: float, L2: float, Lc1: float, Lc2: float,
        include_coriolis: bool, include_centrifugal: bool, include_gyroscopic: bool
    ) -> np.ndarray:
        """JIT-compiled full Coriolis matrix computation."""
        s1 = np.sin(theta1)
        s2 = np.sin(theta2)
        s12 = np.sin(theta1 - theta2)

        # Initialize matrix
        C = np.zeros((3, 3))

        # Standard Coriolis/centrifugal terms
        if include_coriolis and include_centrifugal:
            C[0, 1] = -(m1 * Lc1 + m2 * L1) * s1 * theta1_dot - m2 * Lc2 * s2 * theta2_dot
            C[0, 2] = -m2 * Lc2 * s2 * theta2_dot

            C[1, 1] = -m2 * L1 * Lc2 * s12 * theta2_dot
            C[1, 2] = -m2 * L1 * Lc2 * s12 * theta2_dot

            C[2, 1] = m2 * L1 * Lc2 * s12 * theta1_dot
            C[2, 2] = 0.0

        # Gyroscopic effects (additional coupling terms)
        if include_gyroscopic:
            # Additional small gyroscopic terms for high-fidelity model
            gyro_coupling = 0.01  # Small coupling coefficient
            C[0, 1] += gyro_coupling * (theta1_dot + theta2_dot)
            C[1, 0] -= gyro_coupling * (theta1_dot + theta2_dot)

        return C