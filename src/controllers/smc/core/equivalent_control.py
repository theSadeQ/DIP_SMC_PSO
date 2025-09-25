#==========================================================================================\\\
#=================== src/controllers/smc/core/equivalent_control.py ====================\\\
#==========================================================================================\\\

"""
Equivalent Control Computation for SMC Controllers.

Implements model-based equivalent control (u_eq) that drives the system along
the sliding surface. This is the feedforward component of SMC that provides
nominal performance when the model is accurate.

Mathematical Background:
- Equivalent control: u_eq = -(LM^{-1}B)^{-1} * LM^{-1}F
- Where: M = inertia matrix, F = nonlinear forces, L = surface gradient, B = input matrix
- Requires dynamics model and assumes controllability: |LM^{-1}B| > threshold
"""

from typing import Optional, Any, Tuple
import numpy as np
import logging
from abc import ABC, abstractmethod


class EquivalentControl:
    """
    Model-based equivalent control computation for SMC.

    Computes the control input that would maintain the system exactly on the
    sliding surface if the model were perfect and no disturbances were present.
    """

    def __init__(self,
                 dynamics_model: Optional[Any] = None,
                 regularization: float = 1e-10,
                 controllability_threshold: float = 1e-4):
        """
        Initialize equivalent control computation.

        Args:
            dynamics_model: System dynamics model with get_dynamics() method
            regularization: Matrix regularization for numerical stability
            controllability_threshold: Minimum |LM^{-1}B| for equivalent control
        """
        self.dynamics_model = dynamics_model
        self.regularization = regularization
        self.controllability_threshold = controllability_threshold

        # Control input matrix for cart force [force affects cart position only]
        self.B = np.array([1.0, 0.0, 0.0], dtype=float)

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)

    def compute(self, state: np.ndarray, sliding_surface,
                surface_derivative: Optional[float] = None) -> float:
        """
        Compute equivalent control input.

        Args:
            state: Current system state [x, x_dot, theta1, theta1_dot, theta2, theta2_dot]
            sliding_surface: SlidingSurface object with L matrix
            surface_derivative: Pre-computed surface derivative (optional)

        Returns:
            Equivalent control input u_eq
        """
        # If no dynamics model, return zero equivalent control
        if self.dynamics_model is None:
            return 0.0

        try:
            # Get system dynamics matrices
            M, F = self._extract_dynamics_matrices(state)
            if M is None or F is None:
                return 0.0

            # Get surface gradient L from sliding surface
            L = self._get_surface_gradient(sliding_surface)

            # Compute controllability matrix LM^{-1}B
            M_reg = self._regularize_matrix(M)
            M_inv = np.linalg.inv(M_reg)
            LM_inv_B = L @ M_inv @ self.B

            # Check controllability
            if abs(LM_inv_B) < self.controllability_threshold:
                self.logger.debug(f"Poor controllability: |LM^{{-1}}B| = {abs(LM_inv_B):.2e}")
                return 0.0

            # Compute equivalent control: u_eq = -(LM^{-1}B)^{-1} * LM^{-1}F
            LM_inv_F = L @ M_inv @ F
            u_eq = -LM_inv_F / LM_inv_B

            # Validate result
            if not np.isfinite(u_eq):
                self.logger.warning("Non-finite equivalent control computed")
                return 0.0

            return float(u_eq)

        except (np.linalg.LinAlgError, ValueError, AttributeError) as e:
            self.logger.debug(f"Equivalent control computation failed: {e}")
            return 0.0

    def _extract_dynamics_matrices(self, state: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Extract inertia matrix M and force vector F from dynamics model.

        Args:
            state: System state vector

        Returns:
            Tuple of (M, F) matrices or (None, None) if extraction fails
        """
        try:
            # Try different common interfaces for dynamics models
            if hasattr(self.dynamics_model, 'get_dynamics'):
                # Standard interface: get_dynamics(state) -> (M, F)
                result = self.dynamics_model.get_dynamics(state)
                if isinstance(result, tuple) and len(result) == 2:
                    return result[0], result[1]

            elif hasattr(self.dynamics_model, 'M') and hasattr(self.dynamics_model, 'F'):
                # Direct matrix access
                M = self.dynamics_model.M(state) if callable(self.dynamics_model.M) else self.dynamics_model.M
                F = self.dynamics_model.F(state) if callable(self.dynamics_model.F) else self.dynamics_model.F
                return M, F

            elif hasattr(self.dynamics_model, 'compute_dynamics'):
                # Alternative interface
                return self.dynamics_model.compute_dynamics(state)

            else:
                self.logger.debug("Dynamics model does not have recognized interface")
                return None, None

        except Exception as e:
            self.logger.debug(f"Failed to extract dynamics matrices: {e}")
            return None, None

    def _get_surface_gradient(self, sliding_surface) -> np.ndarray:
        """
        Get surface gradient L from sliding surface object.

        Args:
            sliding_surface: SlidingSurface object

        Returns:
            Surface gradient vector L
        """
        # Try to get L matrix from sliding surface
        if hasattr(sliding_surface, 'L'):
            return sliding_surface.L
        elif hasattr(sliding_surface, 'get_gradient'):
            return sliding_surface.get_gradient()
        else:
            # Default for double-inverted pendulum (affects joint dynamics only)
            # L = [0, k1, k2] for reduced state [theta1_dot, theta1, theta2]
            if hasattr(sliding_surface, 'k1') and hasattr(sliding_surface, 'k2'):
                return np.array([0.0, sliding_surface.k1, sliding_surface.k2], dtype=float)
            else:
                # Fallback: assume unit gains
                return np.array([0.0, 1.0, 1.0], dtype=float)

    def _regularize_matrix(self, M: np.ndarray) -> np.ndarray:
        """
        Add regularization to matrix for numerical stability.

        Args:
            M: Matrix to regularize

        Returns:
            Regularized matrix M + ε*I
        """
        if M.ndim != 2 or M.shape[0] != M.shape[1]:
            raise ValueError("Matrix must be square for regularization")

        return M + self.regularization * np.eye(M.shape[0])

    def check_controllability(self, state: np.ndarray, sliding_surface) -> dict:
        """
        Analyze system controllability at current state.

        Args:
            state: Current system state
            sliding_surface: SlidingSurface object

        Returns:
            Dictionary with controllability analysis
        """
        result = {
            'controllable': False,
            'LM_inv_B': 0.0,
            'condition_number': np.inf,
            'rank_deficient': True
        }

        if self.dynamics_model is None:
            return result

        try:
            M, F = self._extract_dynamics_matrices(state)
            if M is None:
                return result

            L = self._get_surface_gradient(sliding_surface)
            M_reg = self._regularize_matrix(M)

            # Compute condition number
            result['condition_number'] = np.linalg.cond(M_reg)

            # Check rank
            rank = np.linalg.matrix_rank(M_reg)
            result['rank_deficient'] = rank < M_reg.shape[0]

            # Compute controllability measure
            M_inv = np.linalg.inv(M_reg)
            LM_inv_B = L @ M_inv @ self.B
            result['LM_inv_B'] = float(LM_inv_B)

            # Check controllability threshold
            result['controllable'] = abs(LM_inv_B) >= self.controllability_threshold

            return result

        except Exception as e:
            self.logger.debug(f"Controllability analysis failed: {e}")
            return result

    def set_controllability_threshold(self, threshold: float) -> None:
        """
        Update controllability threshold.

        Args:
            threshold: New threshold value (must be > 0)
        """
        if threshold <= 0:
            raise ValueError("Controllability threshold must be positive")
        self.controllability_threshold = threshold

    def get_dynamics_info(self, state: np.ndarray) -> dict:
        """
        Get information about dynamics matrices at current state.

        Args:
            state: Current system state

        Returns:
            Dictionary with dynamics information
        """
        info = {
            'has_model': self.dynamics_model is not None,
            'M_shape': None,
            'F_shape': None,
            'M_condition': np.inf,
            'M_determinant': 0.0
        }

        if self.dynamics_model is None:
            return info

        try:
            M, F = self._extract_dynamics_matrices(state)
            if M is not None:
                info['M_shape'] = M.shape
                info['M_condition'] = np.linalg.cond(M)
                info['M_determinant'] = np.linalg.det(M)

            if F is not None:
                info['F_shape'] = F.shape

        except Exception as e:
            self.logger.debug(f"Failed to get dynamics info: {e}")

        return info