#==========================================================================================\\\
#============== src/simulation/integrators/discrete/zero_order_hold.py =================\\\
#==========================================================================================\\\

"""Zero-order hold discretization for discrete-time simulation."""

from __future__ import annotations

from typing import Callable, Optional
import numpy as np
from scipy.linalg import expm

from ..base import BaseIntegrator


class ZeroOrderHold(BaseIntegrator):
    """Zero-order hold discretization for linear and linearized systems."""

    def __init__(self,
                 A: Optional[np.ndarray] = None,
                 B: Optional[np.ndarray] = None,
                 dt: Optional[float] = None):
        """Initialize ZOH discretization.

        Parameters
        ----------
        A : np.ndarray, optional
            State matrix for linear system dx/dt = Ax + Bu
        B : np.ndarray, optional
            Input matrix for linear system dx/dt = Ax + Bu
        dt : float, optional
            Discretization time step (can be set later)
        """
        super().__init__()
        self.A = A
        self.B = B
        self.dt_discrete = dt
        self._discrete_matrices = None

    @property
    def order(self) -> int:
        """Integration method order (exact for linear systems)."""
        return float('inf')  # Exact for linear systems

    @property
    def adaptive(self) -> bool:
        """Whether integrator supports adaptive step size."""
        return False

    def set_linear_system(self, A: np.ndarray, B: np.ndarray, dt: float) -> None:
        """Set linear system matrices and compute discrete-time equivalent.

        Parameters
        ----------
        A : np.ndarray
            Continuous-time state matrix
        B : np.ndarray
            Continuous-time input matrix
        dt : float
            Discretization time step
        """
        self.A = A
        self.B = B
        self.dt_discrete = dt
        self._compute_discrete_matrices()

    def _compute_discrete_matrices(self) -> None:
        """Compute discrete-time matrices using matrix exponential."""
        if self.A is None or self.B is None or self.dt_discrete is None:
            raise ValueError("Linear system matrices and dt must be set")

        n = self.A.shape[0]
        m = self.B.shape[1]

        # Construct augmented matrix for matrix exponential method
        # [A  B]
        # [0  0]
        augmented = np.zeros((n + m, n + m))
        augmented[:n, :n] = self.A * self.dt_discrete
        augmented[:n, n:] = self.B * self.dt_discrete

        # Compute matrix exponential
        exp_aug = expm(augmented)

        # Extract discrete-time matrices
        Ad = exp_aug[:n, :n]
        Bd = exp_aug[:n, n:]

        self._discrete_matrices = (Ad, Bd)

    def integrate(self,
                 dynamics_fn: Callable,
                 state: np.ndarray,
                 control: np.ndarray,
                 dt: float,
                 t: float = 0.0,
                 **kwargs) -> np.ndarray:
        """Integrate using zero-order hold discretization.

        Parameters
        ----------
        dynamics_fn : callable
            Dynamics function (used for nonlinear systems)
        state : np.ndarray
            Current state
        control : np.ndarray
            Control input (held constant over interval)
        dt : float
            Time step
        t : float, optional
            Current time

        Returns
        -------
        np.ndarray
            Integrated state
        """
        self._validate_inputs(dynamics_fn, state, control, dt)

        if self._discrete_matrices is not None and np.isclose(dt, self.dt_discrete):
            # Use precomputed discrete-time matrices for linear system
            Ad, Bd = self._discrete_matrices
            new_state = Ad @ state + Bd @ control
            self._update_stats(True, 0)  # No function evaluations for linear case
        else:
            # For nonlinear systems or different dt, use approximation
            # Assume control is held constant over interval
            new_state = self._integrate_nonlinear(dynamics_fn, state, control, dt, t)

        return new_state

    def _integrate_nonlinear(self,
                           dynamics_fn: Callable,
                           state: np.ndarray,
                           control: np.ndarray,
                           dt: float,
                           t: float) -> np.ndarray:
        """Integrate nonlinear system with ZOH control approximation.

        For nonlinear systems, we approximate by holding control constant
        and using a higher-order integration method.
        """
        # Use RK4 with constant control as approximation to ZOH
        k1 = dynamics_fn(t, state, control)
        k2 = dynamics_fn(t + dt/2, state + dt*k1/2, control)
        k3 = dynamics_fn(t + dt/2, state + dt*k2/2, control)
        k4 = dynamics_fn(t + dt, state + dt*k3, control)

        new_state = state + dt * (k1 + 2*k2 + 2*k3 + k4) / 6
        self._update_stats(True, 4)
        return new_state

    def get_discrete_matrices(self) -> Optional[tuple]:
        """Get computed discrete-time matrices.

        Returns
        -------
        tuple or None
            (Ad, Bd) discrete-time matrices if available
        """
        return self._discrete_matrices

    def simulate_discrete_sequence(self,
                                 initial_state: np.ndarray,
                                 control_sequence: np.ndarray,
                                 horizon: int) -> np.ndarray:
        """Simulate discrete-time system for multiple steps.

        Parameters
        ----------
        initial_state : np.ndarray
            Initial state
        control_sequence : np.ndarray
            Control sequence (horizon x m)
        horizon : int
            Number of time steps

        Returns
        -------
        np.ndarray
            State trajectory (horizon+1 x n)
        """
        if self._discrete_matrices is None:
            raise ValueError("Discrete matrices must be computed first")

        Ad, Bd = self._discrete_matrices
        n = len(initial_state)

        # Initialize trajectory
        states = np.zeros((horizon + 1, n))
        states[0] = initial_state

        # Simulate forward
        for k in range(horizon):
            control = control_sequence[k] if control_sequence.ndim > 1 else control_sequence
            states[k + 1] = Ad @ states[k] + Bd @ control

        return states