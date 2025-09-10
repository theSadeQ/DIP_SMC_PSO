"""
Linearisation and controllability/observability analysis utilities.

This module exposes helper functions to linearise the double inverted
pendulum dynamics at an equilibrium point and to construct the
controllability and observability matrices for a linear time‑invariant
(LTI) system.  The Kalman rank criterion states that an LTI system is
controllable if and only if its controllability matrix has full rank
equal to the number of state variables【920100172589331†L79-L84】.  An
analogous condition holds for observability.  These functions aid in
assessing whether a given linearised model is suitable for state‐space
control or estimation design.
"""

from __future__ import annotations

from typing import Tuple
import numpy as np

from src.controllers.mpc_controller import _numeric_linearize_continuous


def linearize_dip(dyn: callable, x_eq: np.ndarray, u_eq: float) -> Tuple[np.ndarray, np.ndarray]:
    """Linearise the nonlinear dynamics around an equilibrium point.

    Parameters
    ----------
    dyn : callable
        A function implementing the continuous‑time dynamics ``f(x, u)``.
    x_eq : np.ndarray
        Equilibrium state vector at which to linearise.
    u_eq : float
        Equilibrium control input.

    Returns
    -------
    (A, B) : tuple of np.ndarray
        Continuous‑time state matrix ``A`` and input matrix ``B`` obtained
        via numerical differentiation of the dynamics.
    """
    A, B = _numeric_linearize_continuous(dyn, x_eq, u_eq)
    return A, B


def controllability_matrix(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Construct the controllability matrix of an LTI system.

    For an ``n``‑state system described by matrices ``A`` and ``B``, the
    controllability matrix is defined as ``[B, AB, A^2B, …, A^{n-1}B]``.
    The system is controllable if this matrix has full row rank equal to ``n``【920100172589331†L79-L84】.

    Parameters
    ----------
    A : np.ndarray
        State transition matrix of shape ``(n, n)``.
    B : np.ndarray
        Input matrix of shape ``(n, m)``.

    Returns
    -------
    np.ndarray
        The controllability matrix of shape ``(n, n*m)``.
    """
    n = A.shape[0]
    mats = [B]
    # Successively multiply by A
    for _ in range(1, n):
        mats.append(A @ mats[-1])
    return np.hstack(mats)


def observability_matrix(A: np.ndarray, C: np.ndarray) -> np.ndarray:
    """Construct the observability matrix of an LTI system.

    Given output matrix ``C`` of shape ``(p, n)``, the observability
    matrix is ``[C; CA; CA^2; …; CA^{n-1}]``.  The system is observable
    when this matrix has full column rank equal to ``n``【920100172589331†L79-L84】.

    Parameters
    ----------
    A : np.ndarray
        State transition matrix of shape ``(n, n)``.
    C : np.ndarray
        Output matrix of shape ``(p, n)``.

    Returns
    -------
    np.ndarray
        Observability matrix of shape ``(p*n, n)``.
    """
    n = A.shape[0]
    mats = [C]
    for _ in range(1, n):
        mats.append(mats[-1] @ A)
    return np.vstack(mats)


def check_controllability_observability(A: np.ndarray, B: np.ndarray, C: np.ndarray) -> Tuple[bool, bool]:
    """Check controllability and observability of an LTI system.

    Parameters
    ----------
    A : np.ndarray
        State transition matrix ``(n, n)``.
    B : np.ndarray
        Input matrix ``(n, m)``.
    C : np.ndarray
        Output matrix ``(p, n)``.

    Returns
    -------
    (bool, bool)
        Tuple ``(is_controllable, is_observable)``.  ``True`` when the
        corresponding rank test passes【920100172589331†L79-L84】.
    """
    n = A.shape[0]
    # Build controllability and observability matrices
    ctrb = controllability_matrix(A, B)
    obsv = observability_matrix(A, C)
    # Evaluate rank conditions
    is_ctrl = np.linalg.matrix_rank(ctrb) == n
    is_obsv = np.linalg.matrix_rank(obsv) == n
    return is_ctrl, is_obsv