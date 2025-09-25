#========================================================================================\
#===========================src/plant/core/physics_matrices.py===========================\
#========================================================================================\

"""
Physics Matrix Computation for DIP Systems.

Provides focused components for computing the fundamental physics matrices:
- Inertia Matrix (M): Mass and inertial properties
- Coriolis Matrix (C): Velocity-dependent forces
- Gravity Vector (G): Gravitational forces

Split from monolithic dynamics for clarity, testability, and reusability.
"""

from __future__ import annotations
from typing import Tuple, Protocol, Any
import numpy as np

try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


class PhysicsMatrixComputer(Protocol):
    """Protocol for physics matrix computation."""

    def compute_inertia_matrix(self, state: np.ndarray) -> np.ndarray:
        """Compute inertia matrix M(q)."""
        ...

    def compute_coriolis_matrix(self, state: np.ndarray) -> np.ndarray:
        """Compute Coriolis matrix C(q, q̇)."""
        ...

    def compute_gravity_vector(self, state: np.ndarray) -> np.ndarray:
        """Compute gravity vector G(q)."""
        ...


class DIPPhysicsMatrices:
    """
    Double Inverted Pendulum physics matrix computation.

    Encapsulates the mathematical computation of fundamental physics matrices
    for the DIP system. Uses numerical optimizations (JIT compilation) for
    performance while maintaining clear mathematical structure.
    """

    def __init__(self, parameters: Any):
        """
        Initialize physics matrix computer.

        Args:
            parameters: Physical parameters for the DIP system
        """
        self.params = parameters

        # Extract commonly used parameters for performance
        self.m0 = parameters.cart_mass
        self.m1 = parameters.pendulum1_mass
        self.m2 = parameters.pendulum2_mass
        self.L1 = parameters.pendulum1_length
        self.L2 = parameters.pendulum2_length
        self.Lc1 = parameters.pendulum1_com
        self.Lc2 = parameters.pendulum2_com
        self.I1 = parameters.pendulum1_inertia
        self.I2 = parameters.pendulum2_inertia
        self.g = parameters.gravity

        # Friction coefficients
        self.c0 = parameters.cart_friction
        self.c1 = parameters.joint1_friction
        self.c2 = parameters.joint2_friction

    def compute_inertia_matrix(self, state: np.ndarray) -> np.ndarray:
        """
        Compute the inertia matrix M(q) for the DIP system.

        The inertia matrix represents the mass distribution and coupling
        between the degrees of freedom.

        Args:
            state: System state [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]

        Returns:
            3x3 inertia matrix M(q)
        """
        _, theta1, theta2, _, _, _ = state

        return self._compute_inertia_matrix_numba(
            theta1, theta2, self.m0, self.m1, self.m2,
            self.L1, self.L2, self.Lc1, self.Lc2, self.I1, self.I2
        )

    def compute_coriolis_matrix(self, state: np.ndarray) -> np.ndarray:
        """
        Compute the Coriolis matrix C(q, q̇) for the DIP system.

        The Coriolis matrix captures velocity-dependent forces including
        centripetal and Coriolis effects.

        Args:
            state: System state [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]

        Returns:
            3x3 Coriolis matrix C(q, q̇)
        """
        _, theta1, theta2, _, theta1_dot, theta2_dot = state

        return self._compute_coriolis_matrix_numba(
            theta1, theta2, theta1_dot, theta2_dot,
            self.m1, self.m2, self.L1, self.L2, self.Lc1, self.Lc2,
            self.c0, self.c1, self.c2
        )

    def compute_gravity_vector(self, state: np.ndarray) -> np.ndarray:
        """
        Compute the gravity vector G(q) for the DIP system.

        The gravity vector represents gravitational forces acting on
        the pendulum links.

        Args:
            state: System state [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]

        Returns:
            3x1 gravity vector G(q)
        """
        _, theta1, theta2, _, _, _ = state

        return self._compute_gravity_vector_numba(
            theta1, theta2, self.m1, self.m2,
            self.L1, self.Lc1, self.Lc2, self.g
        )

    def compute_all_matrices(self, state: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute all physics matrices in a single call for efficiency.

        Args:
            state: System state [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]

        Returns:
            Tuple of (M, C, G) matrices
        """
        M = self.compute_inertia_matrix(state)
        C = self.compute_coriolis_matrix(state)
        G = self.compute_gravity_vector(state)
        return M, C, G

    @staticmethod
    @njit
    def _compute_inertia_matrix_numba(
        theta1: float, theta2: float,
        m0: float, m1: float, m2: float,
        L1: float, L2: float, Lc1: float, Lc2: float,
        I1: float, I2: float
    ) -> np.ndarray:
        """JIT-compiled inertia matrix computation."""

        c1 = np.cos(theta1)
        c2 = np.cos(theta2)
        c12 = np.cos(theta1 - theta2)

        # Inertia matrix elements
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
    def _compute_coriolis_matrix_numba(
        theta1: float, theta2: float,
        theta1_dot: float, theta2_dot: float,
        m1: float, m2: float,
        L1: float, L2: float, Lc1: float, Lc2: float,
        c0: float, c1: float, c2: float
    ) -> np.ndarray:
        """JIT-compiled Coriolis matrix computation."""

        s1 = np.sin(theta1)
        s2 = np.sin(theta2)
        s12 = np.sin(theta1 - theta2)

        # Coriolis matrix elements
        C11 = c0
        C12 = -(m1 * Lc1 + m2 * L1) * s1 * theta1_dot - m2 * Lc2 * s2 * theta2_dot
        C13 = -m2 * Lc2 * s2 * theta2_dot

        C21 = 0.0
        C22 = c1 - m2 * L1 * Lc2 * s12 * theta2_dot
        C23 = -m2 * L1 * Lc2 * s12 * theta2_dot

        C31 = 0.0
        C32 = m2 * L1 * Lc2 * s12 * theta1_dot
        C33 = c2

        C = np.array([
            [C11, C12, C13],
            [C21, C22, C23],
            [C31, C32, C33]
        ])

        return C

    @staticmethod
    @njit
    def _compute_gravity_vector_numba(
        theta1: float, theta2: float,
        m1: float, m2: float,
        L1: float, Lc1: float, Lc2: float, g: float
    ) -> np.ndarray:
        """JIT-compiled gravity vector computation."""

        s1 = np.sin(theta1)
        s2 = np.sin(theta2)

        G1 = 0.0
        G2 = -(m1 * Lc1 + m2 * L1) * g * s1 - m2 * Lc2 * g * s2
        G3 = -m2 * Lc2 * g * s2

        G = np.array([G1, G2, G3])

        return G


class SimplifiedDIPPhysicsMatrices(DIPPhysicsMatrices):
    """
    Simplified physics matrices for computational efficiency.

    Uses approximations and simplifications suitable for control design
    while maintaining essential dynamics characteristics.
    """

    def compute_inertia_matrix(self, state: np.ndarray) -> np.ndarray:
        """Simplified inertia matrix with reduced coupling terms."""
        _, theta1, theta2, _, _, _ = state

        # Simplified computation with reduced cross-coupling
        return self._compute_simplified_inertia_matrix_numba(
            theta1, theta2, self.m0, self.m1, self.m2,
            self.L1, self.L2, self.Lc1, self.Lc2, self.I1, self.I2
        )

    @staticmethod
    @njit
    def _compute_simplified_inertia_matrix_numba(
        theta1: float, theta2: float,
        m0: float, m1: float, m2: float,
        L1: float, L2: float, Lc1: float, Lc2: float,
        I1: float, I2: float
    ) -> np.ndarray:
        """Simplified inertia matrix computation."""

        # Diagonal-dominant approximation for faster computation
        M11 = m0 + m1 + m2
        M22 = m1 * Lc1**2 + m2 * L1**2 + I1 + m2 * Lc2**2 + I2
        M33 = m2 * Lc2**2 + I2

        # Reduced off-diagonal terms
        c1 = np.cos(theta1)
        c2 = np.cos(theta2)

        M12 = 0.5 * (m1 * Lc1 + m2 * L1) * c1 + 0.5 * m2 * Lc2 * c2
        M13 = 0.5 * m2 * Lc2 * c2
        M23 = 0.8 * (m2 * Lc2**2 + I2)

        M = np.array([
            [M11, M12, M13],
            [M12, M22, M23],
            [M13, M23, M33]
        ])

        return M