#==========================================================================================\\\
#=================== src/plant/models/simplified/physics.py ===========================\\\
#==========================================================================================\\\

"""
Simplified Physics Computation for DIP.

Focused physics computation module extracted from the monolithic
dynamics implementation. Provides optimized matrix computation
with numerical stability features.
"""

from __future__ import annotations
from typing import Tuple, Any
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
    SimplifiedDIPPhysicsMatrices,
    AdaptiveRegularizer,
    MatrixInverter,
    NumericalInstabilityError
)
from .config import SimplifiedDIPConfig


class SimplifiedPhysicsComputer:
    """
    Simplified physics computation for DIP dynamics.

    Optimized for computational efficiency while maintaining essential
    dynamics characteristics. Uses adaptive regularization for numerical
    stability and supports both full and simplified matrix computation.
    """

    def __init__(self, config: SimplifiedDIPConfig):
        """
        Initialize simplified physics computer.

        Args:
            config: Validated configuration for simplified DIP
        """
        self.config = config

        # Setup physics matrix computers
        self.full_matrices = DIPPhysicsMatrices(config)
        self.simplified_matrices = SimplifiedDIPPhysicsMatrices(config)

        # Setup numerical stability components
        self.regularizer = AdaptiveRegularizer(
            regularization_alpha=config.regularization_alpha,
            max_condition_number=config.max_condition_number,
            min_regularization=config.min_regularization,
            use_fixed_regularization=config.use_fixed_regularization
        )
        self.matrix_inverter = MatrixInverter(self.regularizer)

        # Performance optimization flags
        self.use_simplified_inertia = True
        self.cache_matrices = False
        self._matrix_cache = {}

    def compute_dynamics_rhs(
        self,
        state: np.ndarray,
        control_input: np.ndarray
    ) -> np.ndarray:
        """
        Compute right-hand side of dynamics equation.

        Computes ẍ = M⁻¹(u - C·ẋ - G) for the simplified DIP system.

        Args:
            state: State vector [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
            control_input: Control input [F] (force on cart)

        Returns:
            State derivative vector [x_dot, theta1_dot, theta2_dot, x_ddot, theta1_ddot, theta2_ddot]

        Raises:
            NumericalInstabilityError: If matrix inversion fails
        """
        # Extract state components
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state
        position = np.array([x, theta1, theta2])
        velocity = np.array([x_dot, theta1_dot, theta2_dot])

        # Compute physics matrices
        M, C, G = self.get_physics_matrices(state)

        # Prepare control vector (applied only to cart)
        u = np.array([control_input[0], 0.0, 0.0])

        # Compute dynamics: M·q̈ + C·q̇ + G = u
        # Rearranged: q̈ = M⁻¹(u - C·q̇ - G)
        try:
            # Compute forcing terms
            forcing = u - C @ velocity - G

            # Solve for accelerations
            accelerations = self.matrix_inverter.solve_linear_system(M, forcing)

            # Construct state derivative
            state_derivative = np.concatenate([velocity, accelerations])

            return state_derivative

        except (np.linalg.LinAlgError, NumericalInstabilityError) as e:
            raise NumericalInstabilityError(f"Dynamics computation failed: {e}")

    def get_physics_matrices(
        self,
        state: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get physics matrices M, C, G for current state.

        Args:
            state: Current system state

        Returns:
            Tuple of (M, C, G) matrices
        """
        # Use cache if enabled
        if self.cache_matrices:
            cache_key = tuple(state[:3])  # Only position-dependent
            if cache_key in self._matrix_cache:
                return self._matrix_cache[cache_key]

        # Compute matrices
        if self.use_simplified_inertia:
            matrices = self.simplified_matrices.compute_all_matrices(state)
        else:
            matrices = self.full_matrices.compute_all_matrices(state)

        # Store in cache if enabled
        if self.cache_matrices:
            self._matrix_cache[cache_key] = matrices

        return matrices

    def compute_inertia_matrix(self, state: np.ndarray) -> np.ndarray:
        """Compute inertia matrix M(q)."""
        if self.use_simplified_inertia:
            return self.simplified_matrices.compute_inertia_matrix(state)
        else:
            return self.full_matrices.compute_inertia_matrix(state)

    def compute_coriolis_matrix(self, state: np.ndarray) -> np.ndarray:
        """Compute Coriolis matrix C(q, q̇)."""
        return self.full_matrices.compute_coriolis_matrix(state)

    def compute_gravity_vector(self, state: np.ndarray) -> np.ndarray:
        """Compute gravity vector G(q)."""
        return self.full_matrices.compute_gravity_vector(state)

    def compute_total_energy(self, state: np.ndarray) -> float:
        """
        Compute total energy of the system.

        Args:
            state: Current system state

        Returns:
            Total energy (kinetic + potential)
        """
        return self._compute_kinetic_energy(state) + self._compute_potential_energy(state)

    def compute_kinetic_energy(self, state: np.ndarray) -> float:
        """Compute kinetic energy T = (1/2) q̇ᵀ M q̇."""
        return self._compute_kinetic_energy(state)

    def compute_potential_energy(self, state: np.ndarray) -> float:
        """Compute potential energy V."""
        return self._compute_potential_energy(state)

    def _compute_kinetic_energy(self, state: np.ndarray) -> float:
        """Internal kinetic energy computation."""
        velocity = state[3:6]
        M = self.compute_inertia_matrix(state)
        return 0.5 * velocity.T @ M @ velocity

    def _compute_potential_energy(self, state: np.ndarray) -> float:
        """Internal potential energy computation."""
        _, theta1, theta2, _, _, _ = state

        # Gravitational potential energy
        m1, m2 = self.config.pendulum1_mass, self.config.pendulum2_mass
        Lc1, Lc2 = self.config.pendulum1_com, self.config.pendulum2_com
        g = self.config.gravity

        # Heights of centers of mass (measured from equilibrium)
        h1 = Lc1 * (1 - np.cos(theta1))
        h2 = self.config.pendulum1_length * (1 - np.cos(theta1)) + Lc2 * (1 - np.cos(theta2))

        V = m1 * g * h1 + m2 * g * h2
        return V

    def enable_matrix_caching(self, enable: bool = True) -> None:
        """Enable/disable matrix caching for repeated calculations."""
        self.cache_matrices = enable
        if not enable:
            self._matrix_cache.clear()

    def clear_matrix_cache(self) -> None:
        """Clear matrix cache."""
        self._matrix_cache.clear()

    def set_simplified_inertia(self, use_simplified: bool = True) -> None:
        """Enable/disable simplified inertia matrix computation."""
        self.use_simplified_inertia = use_simplified

    def get_matrix_conditioning(self, state: np.ndarray) -> float:
        """Get condition number of inertia matrix."""
        M = self.compute_inertia_matrix(state)
        return np.linalg.cond(M)

    def check_numerical_stability(self, state: np.ndarray) -> bool:
        """Check if current state leads to numerically stable computation."""
        try:
            M = self.compute_inertia_matrix(state)
            return self.regularizer.check_conditioning(M)
        except (np.linalg.LinAlgError, ValueError):
            return False


@njit
def compute_simplified_dynamics_numba(
    state: np.ndarray,
    control_force: float,
    m0: float, m1: float, m2: float,
    L1: float, L2: float, Lc1: float, Lc2: float,
    I1: float, I2: float, g: float,
    c0: float, c1: float, c2: float,
    reg_alpha: float, min_reg: float
) -> np.ndarray:
    """
    JIT-compiled simplified dynamics computation.

    Ultra-fast dynamics computation for performance-critical applications.
    Uses simplified physics with minimal overhead.

    Args:
        state: System state vector
        control_force: Applied control force
        m0, m1, m2: Masses
        L1, L2, Lc1, Lc2: Lengths and COM distances
        I1, I2: Inertias
        g: Gravity
        c0, c1, c2: Friction coefficients
        reg_alpha, min_reg: Regularization parameters

    Returns:
        State derivative vector
    """
    x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

    # Trigonometric terms
    c1_val = np.cos(theta1)
    c2_val = np.cos(theta2)
    s1 = np.sin(theta1)
    s2 = np.sin(theta2)
    c12 = np.cos(theta1 - theta2)
    s12 = np.sin(theta1 - theta2)

    # Simplified inertia matrix (diagonal-dominant)
    M11 = m0 + m1 + m2
    M22 = m1 * Lc1**2 + m2 * L1**2 + I1 + m2 * Lc2**2 + I2
    M33 = m2 * Lc2**2 + I2

    # Reduced coupling terms
    M12 = 0.7 * ((m1 * Lc1 + m2 * L1) * c1_val + m2 * Lc2 * c2_val)
    M13 = 0.7 * m2 * Lc2 * c2_val
    M23 = 0.8 * (m2 * Lc2**2 + I2 + m2 * L1 * Lc2 * c12)

    # Apply minimal regularization
    reg = max(reg_alpha * max(M11, M22, M33), min_reg)
    M11 += reg
    M22 += reg
    M33 += reg

    # Coriolis and gravity terms (simplified)
    C1 = -c0 * x_dot - 0.5 * (m1 * Lc1 + m2 * L1) * s1 * theta1_dot**2 - 0.5 * m2 * Lc2 * s2 * theta2_dot**2
    C2 = -c1 * theta1_dot - 0.5 * m2 * L1 * Lc2 * s12 * (theta1_dot - theta2_dot)**2
    C3 = -c2 * theta2_dot + 0.5 * m2 * L1 * Lc2 * s12 * (theta1_dot - theta2_dot)**2

    G1 = 0.0
    G2 = -(m1 * Lc1 + m2 * L1) * g * s1 - 0.5 * m2 * Lc2 * g * s2
    G3 = -m2 * Lc2 * g * s2

    # Forcing terms
    F1 = control_force - C1 - G1
    F2 = -C2 - G2
    F3 = -C3 - G3

    # Solve 3x3 system using explicit inversion (simplified)
    det = (M11 * (M22 * M33 - M23**2) -
           M12 * (M12 * M33 - M13 * M23) +
           M13 * (M12 * M23 - M13 * M22))

    if abs(det) < 1e-12:
        # Fallback for near-singular matrix
        det = 1e-12

    # Inverse elements (symmetric matrix)
    inv_M11 = (M22 * M33 - M23**2) / det
    inv_M12 = (M13 * M23 - M12 * M33) / det
    inv_M13 = (M12 * M23 - M13 * M22) / det
    inv_M22 = (M11 * M33 - M13**2) / det
    inv_M23 = (M12 * M13 - M11 * M23) / det
    inv_M33 = (M11 * M22 - M12**2) / det

    # Compute accelerations
    x_ddot = inv_M11 * F1 + inv_M12 * F2 + inv_M13 * F3
    theta1_ddot = inv_M12 * F1 + inv_M22 * F2 + inv_M23 * F3
    theta2_ddot = inv_M13 * F1 + inv_M23 * F2 + inv_M33 * F3

    # Return state derivative
    return np.array([x_dot, theta1_dot, theta2_dot, x_ddot, theta1_ddot, theta2_ddot])