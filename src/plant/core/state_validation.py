#==========================================================================================\\\
#======================= src/plant/core/state_validation.py ===========================\\\
#==========================================================================================\\\

"""
State Vector Validation for Plant Dynamics.

Provides comprehensive validation and sanitization of system states:
- State vector format validation
- Physical bounds checking
- Numerical validity verification
- Constraint enforcement

Ensures robust dynamics computation by catching invalid states early.
"""

from __future__ import annotations
from typing import Tuple, Optional, Protocol, Dict, Any
import numpy as np
import warnings


class StateValidationError(ValueError):
    """Raised when state vector validation fails."""
    pass


class StateValidator(Protocol):
    """Protocol for state validation strategies."""

    def validate_state(self, state: np.ndarray) -> bool:
        """Validate state vector."""
        ...

    def sanitize_state(self, state: np.ndarray) -> np.ndarray:
        """Sanitize and correct state vector if possible."""
        ...


class DIPStateValidator:
    """
    Double Inverted Pendulum state vector validation.

    Validates state vectors for the DIP system ensuring:
    - Correct dimensionality (6-element vectors)
    - Physical bounds on positions and velocities
    - Numerical validity (no NaN/inf values)
    - Angular wrapping and constraint enforcement
    """

    def __init__(
        self,
        position_bounds: Optional[Tuple[float, float]] = None,
        angle_bounds: Optional[Tuple[float, float]] = None,
        velocity_bounds: Optional[Tuple[float, float]] = None,
        angular_velocity_bounds: Optional[Tuple[float, float]] = None,
        wrap_angles: bool = True,
        strict_validation: bool = False
    ):
        """
        Initialize DIP state validator.

        Args:
            position_bounds: (min, max) cart position bounds in meters
            angle_bounds: (min, max) pendulum angle bounds in radians
            velocity_bounds: (min, max) cart velocity bounds in m/s
            angular_velocity_bounds: (min, max) angular velocity bounds in rad/s
            wrap_angles: Whether to wrap angles to [-π, π]
            strict_validation: Whether to raise exceptions for invalid states
        """
        # Default physical bounds for DIP system
        self.position_bounds = position_bounds or (-10.0, 10.0)
        self.angle_bounds = angle_bounds or (-4*np.pi, 4*np.pi)
        self.velocity_bounds = velocity_bounds or (-20.0, 20.0)
        self.angular_velocity_bounds = angular_velocity_bounds or (-50.0, 50.0)

        self.wrap_angles = wrap_angles
        self.strict_validation = strict_validation

        # Statistics tracking
        self.validation_count = 0
        self.sanitization_count = 0
        self.failure_count = 0

    def validate_state(self, state: np.ndarray) -> bool:
        """
        Validate complete state vector.

        Args:
            state: State vector [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]

        Returns:
            True if state is valid

        Raises:
            StateValidationError: If strict_validation=True and state is invalid
        """
        self.validation_count += 1

        try:
            # Check basic structure
            if not self._check_state_structure(state):
                if self.strict_validation:
                    raise StateValidationError("Invalid state vector structure")
                return False

            # Check numerical validity
            if not self._check_numerical_validity(state):
                if self.strict_validation:
                    raise StateValidationError("State contains invalid numerical values")
                return False

            # Check physical bounds
            if not self._check_physical_bounds(state):
                if self.strict_validation:
                    raise StateValidationError("State violates physical bounds")
                return False

            return True

        except Exception as e:
            self.failure_count += 1
            if self.strict_validation:
                raise StateValidationError(f"State validation failed: {e}")
            return False

    def sanitize_state(self, state: np.ndarray) -> np.ndarray:
        """
        Sanitize state vector to ensure validity.

        Args:
            state: Input state vector

        Returns:
            Sanitized state vector

        Raises:
            StateValidationError: If state cannot be sanitized
        """
        if not isinstance(state, np.ndarray):
            state = np.array(state, dtype=float)

        # Check structure
        if not self._check_state_structure(state):
            raise StateValidationError("Cannot sanitize: invalid state structure")

        sanitized = state.copy()
        was_modified = False

        # Handle numerical issues
        if not self._check_numerical_validity(sanitized):
            sanitized = self._fix_numerical_issues(sanitized)
            was_modified = True

        # Apply physical bounds
        original_sanitized = sanitized.copy()
        sanitized = self._apply_physical_bounds(sanitized)
        if not np.allclose(original_sanitized, sanitized):
            was_modified = True

        # Wrap angles if requested
        if self.wrap_angles:
            original_angles = sanitized[[1, 2]].copy()
            sanitized[[1, 2]] = self._wrap_angles(sanitized[[1, 2]])
            if not np.allclose(original_angles, sanitized[[1, 2]]):
                was_modified = True

        if was_modified:
            self.sanitization_count += 1
            if not self.strict_validation:
                warnings.warn("State vector was modified during sanitization", UserWarning)

        return sanitized

    def get_state_info(self, state: np.ndarray) -> Dict[str, Any]:
        """
        Get detailed information about state vector.

        Args:
            state: State vector to analyze

        Returns:
            Dictionary with state analysis
        """
        info = {
            "is_valid": self.validate_state(state),
            "structure_valid": self._check_state_structure(state),
            "numerically_valid": self._check_numerical_validity(state),
            "within_bounds": self._check_physical_bounds(state),
            "shape": state.shape if hasattr(state, 'shape') else None,
            "dtype": state.dtype if hasattr(state, 'dtype') else type(state)
        }

        if self._check_state_structure(state):
            x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

            info.update({
                "cart_position": x,
                "pendulum1_angle": theta1,
                "pendulum2_angle": theta2,
                "cart_velocity": x_dot,
                "pendulum1_angular_velocity": theta1_dot,
                "pendulum2_angular_velocity": theta2_dot,
                "total_energy_estimate": self._estimate_energy(state),
                "angular_momentum_estimate": self._estimate_angular_momentum(state)
            })

        return info

    def reset_statistics(self) -> None:
        """Reset validation statistics."""
        self.validation_count = 0
        self.sanitization_count = 0
        self.failure_count = 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        if self.validation_count == 0:
            return {
                "validation_count": 0,
                "sanitization_rate": 0.0,
                "failure_rate": 0.0
            }

        return {
            "validation_count": self.validation_count,
            "sanitization_rate": self.sanitization_count / self.validation_count,
            "failure_rate": self.failure_count / self.validation_count
        }

    def _check_state_structure(self, state: np.ndarray) -> bool:
        """Check if state has correct structure."""
        return (
            hasattr(state, 'shape') and
            len(state.shape) == 1 and
            state.shape[0] == 6
        )

    def _check_numerical_validity(self, state: np.ndarray) -> bool:
        """Check if state contains valid numerical values."""
        return np.all(np.isfinite(state))

    def _check_physical_bounds(self, state: np.ndarray) -> bool:
        """Check if state is within physical bounds."""
        if not self._check_state_structure(state):
            return False

        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Check position bounds
        if not (self.position_bounds[0] <= x <= self.position_bounds[1]):
            return False

        # Check angle bounds
        if not (self.angle_bounds[0] <= theta1 <= self.angle_bounds[1]):
            return False
        if not (self.angle_bounds[0] <= theta2 <= self.angle_bounds[1]):
            return False

        # Check velocity bounds
        if not (self.velocity_bounds[0] <= x_dot <= self.velocity_bounds[1]):
            return False

        # Check angular velocity bounds
        if not (self.angular_velocity_bounds[0] <= theta1_dot <= self.angular_velocity_bounds[1]):
            return False
        if not (self.angular_velocity_bounds[0] <= theta2_dot <= self.angular_velocity_bounds[1]):
            return False

        return True

    def _fix_numerical_issues(self, state: np.ndarray) -> np.ndarray:
        """Fix numerical issues in state vector."""
        fixed = state.copy()

        # Replace NaN with zeros
        nan_mask = np.isnan(fixed)
        if np.any(nan_mask):
            fixed[nan_mask] = 0.0
            warnings.warn("Replaced NaN values in state with zeros", UserWarning)

        # Clip infinite values
        inf_mask = np.isinf(fixed)
        if np.any(inf_mask):
            # Replace +inf with large finite values, -inf with large negative values
            fixed[np.isposinf(fixed)] = 1e6
            fixed[np.isneginf(fixed)] = -1e6
            warnings.warn("Clipped infinite values in state", UserWarning)

        return fixed

    def _apply_physical_bounds(self, state: np.ndarray) -> np.ndarray:
        """Apply physical bounds to state vector."""
        bounded = state.copy()

        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = bounded

        # Apply position bounds
        bounded[0] = np.clip(x, self.position_bounds[0], self.position_bounds[1])

        # Apply angle bounds
        bounded[1] = np.clip(theta1, self.angle_bounds[0], self.angle_bounds[1])
        bounded[2] = np.clip(theta2, self.angle_bounds[0], self.angle_bounds[1])

        # Apply velocity bounds
        bounded[3] = np.clip(x_dot, self.velocity_bounds[0], self.velocity_bounds[1])

        # Apply angular velocity bounds
        bounded[4] = np.clip(theta1_dot, self.angular_velocity_bounds[0], self.angular_velocity_bounds[1])
        bounded[5] = np.clip(theta2_dot, self.angular_velocity_bounds[0], self.angular_velocity_bounds[1])

        return bounded

    def _wrap_angles(self, angles: np.ndarray) -> np.ndarray:
        """Wrap angles to [-π, π] range."""
        return ((angles + np.pi) % (2 * np.pi)) - np.pi

    def _estimate_energy(self, state: np.ndarray) -> float:
        """Estimate total system energy (rough approximation)."""
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Kinetic energy (approximate)
        kinetic = 0.5 * (x_dot**2 + theta1_dot**2 + theta2_dot**2)

        # Potential energy (approximate, assuming unit masses and lengths)
        potential = 9.81 * (2 - np.cos(theta1) - np.cos(theta2))

        return kinetic + potential

    def _estimate_angular_momentum(self, state: np.ndarray) -> float:
        """Estimate total angular momentum (rough approximation)."""
        _, _, _, _, theta1_dot, theta2_dot = state

        # Approximate angular momentum
        return theta1_dot + theta2_dot


class MinimalStateValidator:
    """
    Minimal state validator for performance-critical applications.

    Provides only essential validation with minimal overhead.
    """

    def validate_state(self, state: np.ndarray) -> bool:
        """Fast basic validation."""
        return (
            hasattr(state, 'shape') and
            state.shape == (6,) and
            np.all(np.isfinite(state))
        )

    def sanitize_state(self, state: np.ndarray) -> np.ndarray:
        """Minimal sanitization."""
        if not isinstance(state, np.ndarray):
            state = np.array(state, dtype=float)

        if state.shape != (6,):
            raise StateValidationError("State must be 6-element vector")

        # Only fix numerical issues
        if not np.all(np.isfinite(state)):
            sanitized = state.copy()
            sanitized[~np.isfinite(sanitized)] = 0.0
            return sanitized

        return state