#==========================================================================================\\\
#================== src/plant/models/base/dynamics_interface.py =======================\\\
#==========================================================================================\\\

"""
Common interface for plant dynamics models.

Defines abstract base classes and protocols that ensure consistency
across different dynamics implementations (simplified, full, low-rank).
"""

from __future__ import annotations
from typing import Protocol, Tuple, Optional, Dict, Any, NamedTuple
from abc import ABC, abstractmethod
from enum import Enum
import numpy as np


class IntegrationMethod(Enum):
    """Available integration methods for dynamics."""
    EULER = "euler"
    RK4 = "rk4"
    RK45 = "rk45"
    ADAPTIVE = "adaptive"


class DynamicsResult(NamedTuple):
    """
    Result of dynamics computation.

    Contains state derivatives and optional diagnostic information
    for debugging and analysis.
    """
    state_derivative: np.ndarray    # dx/dt vector
    success: bool                   # Whether computation succeeded
    info: Dict[str, Any]           # Additional information

    @classmethod
    def success_result(
        cls,
        state_derivative: np.ndarray,
        **info: Any
    ) -> 'DynamicsResult':
        """Create successful dynamics result."""
        return cls(
            state_derivative=state_derivative,
            success=True,
            info=info
        )

    @classmethod
    def failure_result(
        cls,
        reason: str,
        **info: Any
    ) -> 'DynamicsResult':
        """Create failed dynamics result."""
        return cls(
            state_derivative=np.array([]),
            success=False,
            info={"failure_reason": reason, **info}
        )


class DynamicsModel(Protocol):
    """
    Protocol for plant dynamics models.

    Defines the interface that all dynamics models must implement
    for consistent integration with controllers and simulators.
    """

    def compute_dynamics(
        self,
        state: np.ndarray,
        control_input: np.ndarray,
        time: float = 0.0,
        **kwargs: Any
    ) -> DynamicsResult:
        """
        Compute system dynamics at given state and input.

        Args:
            state: Current system state
            control_input: Applied control input
            time: Current time (for time-varying systems)
            **kwargs: Additional implementation-specific parameters

        Returns:
            Dynamics computation result
        """
        ...

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
        ...

    def validate_state(self, state: np.ndarray) -> bool:
        """
        Validate state vector format and bounds.

        Args:
            state: State vector to validate

        Returns:
            True if state is valid
        """
        ...

    def get_state_dimension(self) -> int:
        """Get the dimension of the state vector."""
        ...

    def get_control_dimension(self) -> int:
        """Get the dimension of the control input vector."""
        ...


class BaseDynamicsModel(ABC):
    """
    Abstract base class for dynamics models.

    Provides common functionality and enforces interface compliance
    for concrete dynamics implementations.
    """

    def __init__(self, parameters: Any):
        """
        Initialize dynamics model.

        Args:
            parameters: Physical parameters for the system
        """
        self.parameters = parameters
        self._setup_validation()
        self._setup_monitoring()

    @abstractmethod
    def compute_dynamics(
        self,
        state: np.ndarray,
        control_input: np.ndarray,
        time: float = 0.0,
        **kwargs: Any
    ) -> DynamicsResult:
        """Compute system dynamics (must be implemented by subclasses)."""
        pass

    @abstractmethod
    def get_physics_matrices(
        self,
        state: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Get physics matrices (must be implemented by subclasses)."""
        pass

    @abstractmethod
    def _setup_validation(self) -> None:
        """Setup state validation (must be implemented by subclasses)."""
        pass

    def validate_state(self, state: np.ndarray) -> bool:
        """Validate state vector using configured validator."""
        if hasattr(self, '_state_validator'):
            return self._state_validator.validate_state(state)
        return self._basic_state_validation(state)

    def sanitize_state(self, state: np.ndarray) -> np.ndarray:
        """Sanitize state vector if validator supports it."""
        if hasattr(self, '_state_validator') and hasattr(self._state_validator, 'sanitize_state'):
            return self._state_validator.sanitize_state(state)
        return state

    def get_state_dimension(self) -> int:
        """Get state vector dimension (default: 6 for DIP)."""
        return 6

    def get_control_dimension(self) -> int:
        """Get control input dimension (default: 1 for DIP)."""
        return 1

    def reset_monitoring(self) -> None:
        """Reset monitoring statistics."""
        if hasattr(self, '_stability_monitor'):
            self._stability_monitor.reset_statistics()
        if hasattr(self, '_state_validator') and hasattr(self._state_validator, 'reset_statistics'):
            self._state_validator.reset_statistics()

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        stats = {}

        if hasattr(self, '_stability_monitor'):
            stats['numerical_stability'] = self._stability_monitor.get_statistics()

        if hasattr(self, '_state_validator') and hasattr(self._state_validator, 'get_statistics'):
            stats['state_validation'] = self._state_validator.get_statistics()

        return stats

    def _setup_monitoring(self) -> None:
        """Setup default monitoring (can be overridden)."""
        from ...core import NumericalStabilityMonitor
        self._stability_monitor = NumericalStabilityMonitor()

    def _basic_state_validation(self, state: np.ndarray) -> bool:
        """Basic state validation fallback."""
        return (
            isinstance(state, np.ndarray) and
            state.shape == (self.get_state_dimension(),) and
            np.all(np.isfinite(state))
        )

    def _create_success_result(
        self,
        state_derivative: np.ndarray,
        **info: Any
    ) -> DynamicsResult:
        """Helper to create successful dynamics result."""
        return DynamicsResult.success_result(state_derivative, **info)

    def _create_failure_result(
        self,
        reason: str,
        **info: Any
    ) -> DynamicsResult:
        """Helper to create failed dynamics result."""
        return DynamicsResult.failure_result(reason, **info)


class LinearDynamicsModel(BaseDynamicsModel):
    """
    Base class for linear dynamics models.

    Provides structure for linear systems of the form:
    ẋ = Ax + Bu + f(t)

    Where A is the system matrix, B is the input matrix,
    and f(t) is an optional time-varying disturbance.
    """

    def __init__(self, A: np.ndarray, B: np.ndarray, parameters: Any):
        """
        Initialize linear dynamics model.

        Args:
            A: System matrix
            B: Input matrix
            parameters: Physical parameters
        """
        super().__init__(parameters)
        self.A = A
        self.B = B

        # Validate matrix dimensions
        self._validate_matrices()

    def compute_dynamics(
        self,
        state: np.ndarray,
        control_input: np.ndarray,
        time: float = 0.0,
        **kwargs: Any
    ) -> DynamicsResult:
        """Compute linear dynamics."""
        if not self.validate_state(state):
            return self._create_failure_result("Invalid state vector")

        if not self._validate_control_input(control_input):
            return self._create_failure_result("Invalid control input")

        try:
            # Linear dynamics: ẋ = Ax + Bu
            state_derivative = self.A @ state + self.B @ control_input

            # Add time-varying terms if available
            if hasattr(self, '_compute_time_varying_terms'):
                disturbance = self._compute_time_varying_terms(time, state)
                state_derivative += disturbance

            return self._create_success_result(
                state_derivative,
                time=time,
                control_input=control_input.copy(),
                **kwargs
            )

        except Exception as e:
            return self._create_failure_result(f"Linear dynamics computation failed: {e}")

    def get_physics_matrices(
        self,
        state: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Get linear system matrices as M, C, G equivalent."""
        n = len(state)

        # For linear systems: M = I, C = -A, G = 0
        M = np.eye(n)
        C = -self.A
        G = np.zeros(n)

        return M, C, G

    def _setup_validation(self) -> None:
        """Setup validation for linear systems."""
        from ...core import MinimalStateValidator
        self._state_validator = MinimalStateValidator()

    def _validate_matrices(self) -> None:
        """Validate system matrices."""
        if self.A.shape[0] != self.A.shape[1]:
            raise ValueError("System matrix A must be square")

        if self.B.shape[0] != self.A.shape[0]:
            raise ValueError("Input matrix B must have same number of rows as A")

        if not np.all(np.isfinite(self.A)):
            raise ValueError("System matrix A contains invalid values")

        if not np.all(np.isfinite(self.B)):
            raise ValueError("Input matrix B contains invalid values")

    def _validate_control_input(self, control_input: np.ndarray) -> bool:
        """Validate control input vector."""
        return (
            isinstance(control_input, np.ndarray) and
            len(control_input.shape) == 1 and
            control_input.shape[0] == self.B.shape[1] and
            np.all(np.isfinite(control_input))
        )