#==========================================================================================\\\
#================= src/simulation/integrators/adaptive/error_control.py ================\\\
#==========================================================================================\\\

"""Error control and step size adaptation for adaptive integration."""

from __future__ import annotations

from typing import Tuple
import numpy as np


class ErrorController:
    """Basic error controller for adaptive step size methods."""

    def __init__(self, safety_factor: float = 0.9):
        """Initialize error controller.

        Parameters
        ----------
        safety_factor : float, optional
            Safety factor for step size adjustments
        """
        self.safety_factor = safety_factor

    def update_step_size(self,
                        error_norm: float,
                        current_dt: float,
                        min_dt: float,
                        max_dt: float,
                        order: int) -> Tuple[float, bool]:
        """Update step size based on error estimate.

        Parameters
        ----------
        error_norm : float
            Normalized error estimate
        current_dt : float
            Current step size
        min_dt : float
            Minimum allowed step size
        max_dt : float
            Maximum allowed step size
        order : int
            Method order for exponent calculation

        Returns
        -------
        tuple
            (new_dt, accept_step)
        """
        tolerance = 1.0  # Standard tolerance for normalized error

        if error_norm <= tolerance:
            # Accept step
            accept = True
            if error_norm == 0.0:
                # Perfect accuracy, grow step moderately
                factor = 2.0
            else:
                # Standard PI controller formula
                factor = self.safety_factor * (tolerance / error_norm) ** (1.0 / order)
                factor = min(factor, 5.0)  # Limit growth
        else:
            # Reject step
            accept = False
            factor = self.safety_factor * (tolerance / error_norm) ** (1.0 / (order + 1))
            factor = max(factor, 0.1)  # Limit shrinkage

        new_dt = np.clip(current_dt * factor, min_dt, max_dt)
        return new_dt, accept


class PIController(ErrorController):
    """PI (Proportional-Integral) controller for step size adaptation."""

    def __init__(self,
                 safety_factor: float = 0.9,
                 alpha: float = 0.7,
                 beta: float = 0.4):
        """Initialize PI controller.

        Parameters
        ----------
        safety_factor : float, optional
            Safety factor for step size adjustments
        alpha : float, optional
            Proportional gain parameter
        beta : float, optional
            Integral gain parameter
        """
        super().__init__(safety_factor)
        self.alpha = alpha
        self.beta = beta
        self._previous_error = None

    def update_step_size(self,
                        error_norm: float,
                        current_dt: float,
                        min_dt: float,
                        max_dt: float,
                        order: int) -> Tuple[float, bool]:
        """Update step size using PI control.

        Parameters
        ----------
        error_norm : float
            Normalized error estimate
        current_dt : float
            Current step size
        min_dt : float
            Minimum allowed step size
        max_dt : float
            Maximum allowed step size
        order : int
            Method order

        Returns
        -------
        tuple
            (new_dt, accept_step)
        """
        tolerance = 1.0

        if error_norm <= tolerance:
            accept = True
        else:
            accept = False

        # PI controller formula
        if self._previous_error is None:
            # First step, use basic controller
            if error_norm == 0.0:
                factor = 2.0
            else:
                factor = self.safety_factor * (tolerance / error_norm) ** (1.0 / order)
        else:
            # PI controller with error history
            if error_norm == 0.0:
                factor = 2.0
            else:
                # PI formula: safety * (tol/err)^alpha * (prev_err/err)^beta
                proportional = (tolerance / error_norm) ** self.alpha
                integral = (self._previous_error / error_norm) ** self.beta
                factor = self.safety_factor * proportional * integral

        # Limit factor to reasonable bounds
        factor = np.clip(factor, 0.1, 5.0)
        new_dt = np.clip(current_dt * factor, min_dt, max_dt)

        self._previous_error = error_norm
        return new_dt, accept

    def reset(self) -> None:
        """Reset controller state."""
        self._previous_error = None


class DeadBeatController(ErrorController):
    """Dead-beat controller for aggressive step size adaptation."""

    def __init__(self, safety_factor: float = 0.9, target_error: float = 0.1):
        """Initialize dead-beat controller.

        Parameters
        ----------
        safety_factor : float, optional
            Safety factor for step size adjustments
        target_error : float, optional
            Target error level for step size prediction
        """
        super().__init__(safety_factor)
        self.target_error = target_error

    def update_step_size(self,
                        error_norm: float,
                        current_dt: float,
                        min_dt: float,
                        max_dt: float,
                        order: int) -> Tuple[float, bool]:
        """Update step size using dead-beat control.

        This controller attempts to predict the optimal step size
        to achieve the target error level.

        Parameters
        ----------
        error_norm : float
            Normalized error estimate
        current_dt : float
            Current step size
        min_dt : float
            Minimum allowed step size
        max_dt : float
            Maximum allowed step size
        order : int
            Method order

        Returns
        -------
        tuple
            (new_dt, accept_step)
        """
        tolerance = 1.0

        if error_norm <= tolerance:
            accept = True
        else:
            accept = False

        # Dead-beat prediction to target error
        if error_norm == 0.0:
            factor = 2.0
        else:
            factor = self.safety_factor * (self.target_error / error_norm) ** (1.0 / order)

        # More aggressive bounds for dead-beat control
        factor = np.clip(factor, 0.05, 10.0)
        new_dt = np.clip(current_dt * factor, min_dt, max_dt)

        return new_dt, accept