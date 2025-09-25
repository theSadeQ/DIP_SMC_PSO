#========================================================================================\
#=========================src/plant/core/numerical_stability.py==========================\
#========================================================================================\

"""
Numerical Stability Utilities for Plant Dynamics.

Provides robust numerical methods for:
- Matrix conditioning and regularization
- Singular value analysis
- Adaptive regularization schemes
- Numerical instability detection

Extracted from monolithic dynamics for focused responsibility and testing.
"""

from __future__ import annotations
from typing import Tuple, Optional, Protocol
import numpy as np
import warnings

try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


class NumericalInstabilityError(RuntimeError):
    """
    Raised when numerical computation becomes unstable.

    This exception indicates that the system matrices are too ill-conditioned
    for reliable numerical computation, typically due to near-singular
    inertia matrices or extreme parameter values.
    """
    pass


class MatrixRegularizer(Protocol):
    """Protocol for matrix regularization strategies."""

    def regularize_matrix(self, matrix: np.ndarray) -> np.ndarray:
        """Apply regularization to improve matrix conditioning."""
        ...

    def check_conditioning(self, matrix: np.ndarray) -> bool:
        """Check if matrix conditioning is acceptable."""
        ...


class AdaptiveRegularizer:
    """
    Adaptive matrix regularization for improved numerical stability.

    Uses Tikhonov regularization with adaptive damping based on matrix
    conditioning. Provides robust matrix inversion for dynamics computation.

    Mathematical Background:
    - Adds λI to matrix diagonal where λ is adaptive damping parameter
    - λ scales with largest singular value and condition number
    - Prevents numerical instability while minimizing bias
    """

    def __init__(
        self,
        regularization_alpha: float = 1e-4,
        max_condition_number: float = 1e14,
        min_regularization: float = 1e-10,
        use_fixed_regularization: bool = False
    ):
        """
        Initialize adaptive regularizer.

        Args:
            regularization_alpha: Base regularization scaling factor
            max_condition_number: Maximum acceptable condition number
            min_regularization: Minimum regularization to ensure invertibility
            use_fixed_regularization: Use fixed rather than adaptive regularization
        """
        self.alpha = regularization_alpha
        self.max_cond = max_condition_number
        self.min_reg = min_regularization
        self.use_fixed = use_fixed_regularization

    def regularize_matrix(self, matrix: np.ndarray) -> np.ndarray:
        """
        Apply adaptive regularization to improve matrix conditioning.

        Args:
            matrix: Input matrix to regularize

        Returns:
            Regularized matrix with improved conditioning

        Raises:
            NumericalInstabilityError: If matrix cannot be adequately regularized
        """
        if self.use_fixed:
            return self._apply_fixed_regularization(matrix)
        else:
            return self._apply_adaptive_regularization(matrix)

    def check_conditioning(self, matrix: np.ndarray) -> bool:
        """
        Check if matrix conditioning is acceptable.

        Args:
            matrix: Matrix to check

        Returns:
            True if matrix is well-conditioned
        """
        try:
            cond_num = np.linalg.cond(matrix)
            return cond_num < self.max_cond and np.isfinite(cond_num)
        except (np.linalg.LinAlgError, ValueError):
            return False

    def _apply_fixed_regularization(self, matrix: np.ndarray) -> np.ndarray:
        """Apply fixed regularization with minimum damping."""
        regularized = matrix + self.min_reg * np.eye(matrix.shape[0])
        return regularized

    def _apply_adaptive_regularization(self, matrix: np.ndarray) -> np.ndarray:
        """Apply adaptive regularization based on matrix conditioning."""
        try:
            # Compute singular value decomposition
            U, s, Vt = np.linalg.svd(matrix)

            # Check for numerical issues
            if not np.all(np.isfinite(s)) or s.size == 0:
                raise NumericalInstabilityError("Invalid singular values in matrix")

            # Compute condition number
            if s[-1] <= 0:
                cond_num = np.inf
            else:
                cond_num = s[0] / s[-1]

            # Determine adaptive regularization
            if cond_num > self.max_cond:
                # Increase regularization for poor conditioning
                reg_scale = max(
                    self.alpha * s[0],
                    self.min_reg * (cond_num / self.max_cond)
                )
            else:
                # Use base regularization for good conditioning
                reg_scale = max(self.alpha * s[0], self.min_reg)

            # Apply regularization
            regularized = matrix + reg_scale * np.eye(matrix.shape[0])

            # Verify improved conditioning
            if not self.check_conditioning(regularized):
                warnings.warn(
                    f"Matrix conditioning remains poor after regularization "
                    f"(condition number: {cond_num:.2e})",
                    UserWarning
                )

            return regularized

        except np.linalg.LinAlgError as e:
            raise NumericalInstabilityError(f"SVD failed: {e}")


class MatrixInverter:
    """
    Robust matrix inversion with numerical stability checks.

    Provides multiple inversion strategies with fallback mechanisms
    for reliable computation of matrix inverses in dynamics.
    """

    def __init__(self, regularizer: Optional[AdaptiveRegularizer] = None):
        """
        Initialize matrix inverter.

        Args:
            regularizer: Optional regularizer for improving conditioning
        """
        self.regularizer = regularizer or AdaptiveRegularizer()

    def invert_matrix(self, matrix: np.ndarray) -> np.ndarray:
        """
        Robustly invert matrix with regularization if needed.

        Args:
            matrix: Matrix to invert

        Returns:
            Matrix inverse

        Raises:
            NumericalInstabilityError: If matrix cannot be reliably inverted
        """
        # Check for obvious issues
        if matrix.size == 0 or not np.all(np.isfinite(matrix)):
            raise NumericalInstabilityError("Matrix contains invalid values")

        # Try direct inversion first
        if self.regularizer.check_conditioning(matrix):
            try:
                return np.linalg.inv(matrix)
            except np.linalg.LinAlgError:
                pass  # Fall back to regularized inversion

        # Apply regularization and retry
        regularized_matrix = self.regularizer.regularize_matrix(matrix)

        try:
            return np.linalg.inv(regularized_matrix)
        except np.linalg.LinAlgError as e:
            raise NumericalInstabilityError(f"Matrix inversion failed: {e}")

    def solve_linear_system(self, A: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        Solve linear system Ax = b with numerical stability.

        Args:
            A: Coefficient matrix
            b: Right-hand side vector

        Returns:
            Solution vector x

        Raises:
            NumericalInstabilityError: If system cannot be reliably solved
        """
        # Try direct solve first
        if self.regularizer.check_conditioning(A):
            try:
                return np.linalg.solve(A, b)
            except np.linalg.LinAlgError:
                pass  # Fall back to regularized solve

        # Apply regularization and retry
        regularized_A = self.regularizer.regularize_matrix(A)

        try:
            return np.linalg.solve(regularized_A, b)
        except np.linalg.LinAlgError as e:
            raise NumericalInstabilityError(f"Linear system solve failed: {e}")


@njit
def fast_condition_estimate(matrix: np.ndarray) -> float:
    """
    Fast condition number estimation using determinant ratio.

    Provides a lightweight alternative to full SVD for condition checking
    in performance-critical code paths.

    Args:
        matrix: Matrix to analyze

    Returns:
        Approximate condition number estimate
    """
    n = matrix.shape[0]

    # Compute determinant
    det = np.linalg.det(matrix)

    if abs(det) < 1e-15:
        return np.inf

    # Estimate using Frobenius norm and determinant
    frobenius_norm = np.sqrt(np.sum(matrix * matrix))
    trace = np.trace(matrix)

    # Rough condition estimate
    cond_estimate = (frobenius_norm / abs(det)**(1.0/n)) * n

    return cond_estimate


class NumericalStabilityMonitor:
    """
    Monitor numerical stability during dynamics computation.

    Tracks conditioning, regularization frequency, and stability metrics
    for debugging and performance optimization.
    """

    def __init__(self):
        """Initialize stability monitor."""
        self.reset_statistics()

    def reset_statistics(self) -> None:
        """Reset monitoring statistics."""
        self.total_inversions = 0
        self.regularized_inversions = 0
        self.failed_inversions = 0
        self.worst_condition_number = 0.0
        self.average_condition_number = 0.0

    def record_inversion(
        self,
        condition_number: float,
        was_regularized: bool,
        failed: bool = False
    ) -> None:
        """
        Record matrix inversion statistics.

        Args:
            condition_number: Condition number of the matrix
            was_regularized: Whether regularization was applied
            failed: Whether the inversion failed
        """
        self.total_inversions += 1

        if failed:
            self.failed_inversions += 1
        elif was_regularized:
            self.regularized_inversions += 1

        if np.isfinite(condition_number):
            self.worst_condition_number = max(
                self.worst_condition_number,
                condition_number
            )

            # Update running average
            alpha = 1.0 / self.total_inversions
            self.average_condition_number = (
                (1 - alpha) * self.average_condition_number +
                alpha * condition_number
            )

    def get_statistics(self) -> dict:
        """
        Get numerical stability statistics.

        Returns:
            Dictionary of stability metrics
        """
        if self.total_inversions == 0:
            return {
                "total_inversions": 0,
                "regularization_rate": 0.0,
                "failure_rate": 0.0,
                "worst_condition_number": 0.0,
                "average_condition_number": 0.0
            }

        return {
            "total_inversions": self.total_inversions,
            "regularization_rate": self.regularized_inversions / self.total_inversions,
            "failure_rate": self.failed_inversions / self.total_inversions,
            "worst_condition_number": self.worst_condition_number,
            "average_condition_number": self.average_condition_number
        }