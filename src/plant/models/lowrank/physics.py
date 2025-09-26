#==========================================================================================\\\
#======================== src/plant/models/lowrank/physics.py ===========================\\\
#==========================================================================================\\\

"""
Low-rank DIP Physics Computer.

Simplified physics computation optimized for speed and efficiency.
Uses approximations and reduced-order models to maintain essential
dynamics while minimizing computational overhead.
"""

from __future__ import annotations
from typing import Optional, Tuple
import numpy as np

from .config import LowRankDIPConfig


class LowRankPhysicsComputer:
    """
    Low-rank Physics Computer for Double Inverted Pendulum.

    Implements simplified physics calculations optimized for:
    - Fast computation
    - Essential dynamics preservation
    - Educational clarity
    - Prototyping efficiency
    """

    def __init__(self, config: LowRankDIPConfig):
        """
        Initialize low-rank physics computer.

        Args:
            config: Validated low-rank DIP configuration
        """
        self.config = config
        self._precompute_constants()

    def _precompute_constants(self) -> None:
        """Precompute frequently used constants for efficiency."""
        # Mass and inertia terms
        self.m0 = self.config.cart_mass
        self.m1 = self.config.pendulum1_mass
        self.m2 = self.config.pendulum2_mass
        self.l1 = self.config.pendulum1_length
        self.l2 = self.config.pendulum2_length
        self.g = self.config.gravity

        # Precomputed products
        self.m1l1 = self.m1 * self.l1
        self.m2l2 = self.m2 * self.l2
        self.m1l1_sq = self.m1 * self.l1**2
        self.m2l2_sq = self.m2 * self.l2**2

        # Total mass
        self.total_mass = self.m0 + self.m1 + self.m2

        # Gravitational terms
        self.m1gl1 = self.m1 * self.g * self.l1
        self.m2gl2 = self.m2 * self.g * self.l2

        # Friction and damping
        self.friction_coeff = self.config.friction_coefficient
        self.damping_coeff = self.config.damping_coefficient

    def compute_simplified_dynamics_rhs(
        self,
        state: np.ndarray,
        control_input: np.ndarray,
        time: float = 0.0
    ) -> np.ndarray:
        """
        Compute simplified dynamics right-hand side.

        Args:
            state: State vector [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
            control_input: Control input [F]
            time: Current time (unused in basic model)

        Returns:
            State derivative vector
        """
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state
        F = control_input[0]

        if self.config.enable_linearization and self.config.enable_small_angle_approximation:
            return self._compute_linearized_dynamics(state, F)
        elif self.config.enable_small_angle_approximation:
            return self._compute_small_angle_dynamics(state, F)
        else:
            return self._compute_simplified_nonlinear_dynamics(state, F)

    def _compute_linearized_dynamics(self, state: np.ndarray, F: float) -> np.ndarray:
        """Compute linearized dynamics (fastest)."""
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # State derivative
        state_dot = np.zeros(6)

        # Position derivatives
        state_dot[0] = x_dot
        state_dot[1] = theta1_dot
        state_dot[2] = theta2_dot

        # Small angle approximation: sin(θ) ≈ θ, cos(θ) ≈ 1
        # Simplified linear dynamics
        state_dot[3] = (F - self.friction_coeff * x_dot -
                       self.m1gl1 * theta1 - self.m2gl2 * theta2) / self.total_mass

        state_dot[4] = (self.m1gl1 * theta1 + self.m1l1 * state_dot[3] -
                       self.damping_coeff * theta1_dot) / self.m1l1_sq

        state_dot[5] = (self.m2gl2 * theta2 + self.m2l2 * state_dot[3] -
                       self.damping_coeff * theta2_dot) / self.m2l2_sq

        return state_dot

    def _compute_small_angle_dynamics(self, state: np.ndarray, F: float) -> np.ndarray:
        """Compute dynamics with small angle approximation."""
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Small angle: sin(θ) ≈ θ, cos(θ) ≈ 1
        sin_theta1, cos_theta1 = theta1, 1.0
        sin_theta2, cos_theta2 = theta2, 1.0

        return self._compute_dynamics_with_trig(
            state, F, sin_theta1, cos_theta1, sin_theta2, cos_theta2
        )

    def _compute_simplified_nonlinear_dynamics(self, state: np.ndarray, F: float) -> np.ndarray:
        """Compute simplified nonlinear dynamics."""
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Full trigonometric functions
        sin_theta1, cos_theta1 = np.sin(theta1), np.cos(theta1)
        sin_theta2, cos_theta2 = np.sin(theta2), np.cos(theta2)

        return self._compute_dynamics_with_trig(
            state, F, sin_theta1, cos_theta1, sin_theta2, cos_theta2
        )

    def _compute_dynamics_with_trig(
        self,
        state: np.ndarray,
        F: float,
        sin_theta1: float, cos_theta1: float,
        sin_theta2: float, cos_theta2: float
    ) -> np.ndarray:
        """Compute dynamics with given trigonometric values."""
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # State derivative
        state_dot = np.zeros(6)

        # Position derivatives
        state_dot[0] = x_dot
        state_dot[1] = theta1_dot
        state_dot[2] = theta2_dot

        # Simplified force calculations
        # Cart forces
        F_gravity1 = -self.m1l1 * sin_theta1 * theta1_dot**2
        F_gravity2 = -self.m2l2 * sin_theta2 * theta2_dot**2
        F_friction = -self.friction_coeff * x_dot

        # Pendulum coupling forces
        F_coupling1 = self.m1l1 * cos_theta1
        F_coupling2 = self.m2l2 * cos_theta2

        # Simplified mass matrix (diagonal approximation for speed)
        M_cart = self.total_mass
        M_pend1 = self.m1l1_sq
        M_pend2 = self.m2l2_sq

        # Cart acceleration
        numerator_cart = F + F_gravity1 + F_gravity2 + F_friction
        state_dot[3] = numerator_cart / M_cart

        # Pendulum accelerations (simplified coupling)
        # Pendulum 1
        tau_gravity1 = -self.m1gl1 * sin_theta1
        tau_coupling1 = F_coupling1 * state_dot[3]
        tau_damping1 = -self.damping_coeff * theta1_dot

        state_dot[4] = (tau_gravity1 + tau_coupling1 + tau_damping1) / M_pend1

        # Pendulum 2
        tau_gravity2 = -self.m2gl2 * sin_theta2
        tau_coupling2 = F_coupling2 * state_dot[3]
        tau_damping2 = -self.damping_coeff * theta2_dot

        state_dot[5] = (tau_gravity2 + tau_coupling2 + tau_damping2) / M_pend2

        return state_dot

    def compute_simplified_matrices(
        self,
        state: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute simplified physics matrices M, C, G.

        Args:
            state: Current system state

        Returns:
            Tuple of (M, C, G) matrices (simplified)
        """
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        if self.config.use_simplified_matrices:
            return self._compute_diagonal_matrices(state)
        else:
            return self._compute_coupled_matrices(state)

    def _compute_diagonal_matrices(
        self,
        state: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute diagonal approximation of physics matrices."""
        # Simplified diagonal mass matrix
        M = np.diag([
            1.0,  # x equation (normalized)
            1.0,  # theta1 equation (normalized)
            1.0,  # theta2 equation (normalized)
        ])

        # Simplified damping matrix
        C = np.diag([
            self.friction_coeff / self.total_mass,
            self.damping_coeff / self.m1l1_sq,
            self.damping_coeff / self.m2l2_sq
        ])

        # Simplified gravity vector
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        if self.config.enable_small_angle_approximation:
            sin_theta1, sin_theta2 = theta1, theta2
        else:
            sin_theta1, sin_theta2 = np.sin(theta1), np.sin(theta2)

        G = np.array([
            0.0,  # No gravity on cart directly
            self.m1gl1 * sin_theta1 / self.m1l1_sq,
            self.m2gl2 * sin_theta2 / self.m2l2_sq
        ])

        return M, C, G

    def _compute_coupled_matrices(
        self,
        state: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute coupled physics matrices (more accurate)."""
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        if self.config.enable_small_angle_approximation:
            cos_theta1, cos_theta2 = 1.0, 1.0
            sin_theta1, sin_theta2 = theta1, theta2
        else:
            cos_theta1, cos_theta2 = np.cos(theta1), np.cos(theta2)
            sin_theta1, sin_theta2 = np.sin(theta1), np.sin(theta2)

        # Simplified mass matrix with coupling
        M = np.array([
            [self.total_mass, self.m1l1*cos_theta1, self.m2l2*cos_theta2],
            [self.m1l1*cos_theta1, self.m1l1_sq, 0.0],
            [self.m2l2*cos_theta2, 0.0, self.m2l2_sq]
        ])

        # Simplified Coriolis matrix
        C = np.array([
            [self.friction_coeff, -self.m1l1*sin_theta1*theta1_dot, -self.m2l2*sin_theta2*theta2_dot],
            [0.0, self.damping_coeff, 0.0],
            [0.0, 0.0, self.damping_coeff]
        ])

        # Gravity vector
        G = np.array([
            0.0,
            self.m1gl1 * sin_theta1,
            self.m2gl2 * sin_theta2
        ])

        return M, C, G

    def compute_energy(self, state: np.ndarray) -> dict:
        """Compute simplified energy analysis."""
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Kinetic energy (simplified)
        T_cart = 0.5 * self.m0 * x_dot**2
        T_pend1 = 0.5 * self.m1l1_sq * theta1_dot**2
        T_pend2 = 0.5 * self.m2l2_sq * theta2_dot**2
        kinetic_energy = T_cart + T_pend1 + T_pend2

        # Potential energy
        if self.config.enable_small_angle_approximation:
            # Small angle: 1 - cos(θ) ≈ θ²/2
            V_pend1 = self.m1gl1 * (theta1**2 / 2)
            V_pend2 = self.m2gl2 * (theta2**2 / 2)
        else:
            V_pend1 = self.m1gl1 * (1 - np.cos(theta1))
            V_pend2 = self.m2gl2 * (1 - np.cos(theta2))

        potential_energy = V_pend1 + V_pend2
        total_energy = kinetic_energy + potential_energy

        return {
            'kinetic_energy': kinetic_energy,
            'potential_energy': potential_energy,
            'total_energy': total_energy,
            'kinetic_cart': T_cart,
            'kinetic_pendulum1': T_pend1,
            'kinetic_pendulum2': T_pend2,
            'potential_pendulum1': V_pend1,
            'potential_pendulum2': V_pend2
        }

    def compute_stability_metrics(self, state: np.ndarray) -> dict:
        """Compute simplified stability metrics."""
        M, C, G = self.compute_simplified_matrices(state)

        # Basic conditioning
        cond_M = np.linalg.cond(M)
        det_M = np.linalg.det(M)

        # Energy metrics
        energy = self.compute_energy(state)

        return {
            'condition_number': cond_M,
            'determinant': det_M,
            'total_energy': energy['total_energy'],
            'kinetic_potential_ratio': energy['kinetic_energy'] / (energy['potential_energy'] + 1e-12)
        }

    def validate_computation(self, state: np.ndarray, state_derivative: np.ndarray) -> bool:
        """Validate physics computation results."""
        # Basic sanity checks
        if not np.all(np.isfinite(state_derivative)):
            return False

        # Check for reasonable acceleration magnitudes
        max_accel = 1000.0  # m/s² or rad/s² - relaxed for high control inputs
        if np.any(np.abs(state_derivative[3:]) > max_accel):
            return False

        return True