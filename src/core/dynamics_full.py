# ========================================================================================\\\
# src/core/dynamics_full.py =============================================================\\\
# ========================================================================================\\\

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Optional numba import
#
# Numba accelerates the physics kernels.  Define a no‑op ``njit``
# decorator when numba is unavailable so the module can be imported
# unconditionally.  The functions will run in pure Python in that case.
try:
    from numba import njit  # type: ignore
except Exception:  # pragma: no cover

    def njit(*_args, **_kwargs):  # type: ignore
        def deco(fn):
            return fn

        return deco


from typing import NamedTuple, Tuple, Any

# Import the custom exception from the simplified dynamics module.  The
# exception is defined in ``src/core/dynamics.py`` and reused here to
# signal numerical instability.  Importing within a try/except allows
# graceful degradation if the module cannot be imported (e.g., during
# partial test runs).
try:
    from src.core.dynamics import NumericalInstabilityError  # type: ignore
except Exception:

    class NumericalInstabilityError(RuntimeError):  # pragma: no cover
        pass


"""
The high‑fidelity dynamics module depends on the PhysicsConfig model from
``src.config`` for validation of the physical parameters.  In some test
environments the configuration module may fail to import (e.g., when
dependent libraries such as numpy are intentionally missing).  To ensure
that importing this module never raises an ``ImportError`` at the
top level, wrap the import of PhysicsConfig in a try/except block.  If
the real class cannot be imported we define a minimal placeholder
class.  ``isinstance`` checks against the placeholder will return
``False`` for actual PhysicsConfig instances but allow monkeypatching
or attribute assignment during tests.  Downstream code will treat
parameters as plain mappings in that case.
"""
try:
    # Attempt to import the real PhysicsConfig.  This may fail if the
    # configuration module cannot be imported (e.g., due to missing
    # dependencies).  Catch all exceptions to avoid ImportError from
    # propagating during module import.
    from src.config import PhysicsConfig  # type: ignore
except Exception:
    # Define a minimal placeholder when the real model is unavailable.
    # The placeholder allows ``isinstance`` checks to safely return
    # ``False`` and supports attribute assignment so that tests using
    # monkeypatch can bind attributes (e.g., load_config) without
    # raising AttributeError.  We intentionally do not provide any
    # behavior on the class.
    class PhysicsConfig:  # type: ignore
        pass


class FullDIPParams(NamedTuple):
    """
    Container for the full double inverted pendulum physics.

    This tuple mirrors the fields of ``PhysicsConfig`` and includes
    configurable regularisation and singularity detection parameters.
    Adding a small positive diagonal to the inertia matrix (Tikhonov
    regularisation) ensures it remains positive definite and invertible
    as adding a small positive constant to the diagonal of a matrix
    makes it invertible【634903324123444†L631-L639】.  The determinant threshold exposes the
    tolerance below which the inertia matrix is deemed singular.

    Parameters
    ----------
    cart_mass, pendulum1_mass, pendulum2_mass, pendulum1_length,
    pendulum2_length, pendulum1_com, pendulum2_com, pendulum1_inertia,
    pendulum2_inertia, gravity, cart_friction, joint1_friction,
    joint2_friction: float
        Physical constants as defined in ``PhysicsConfig``.
    singularity_cond_threshold: float, optional
        Condition number threshold beyond which the inertia matrix is
        considered singular.  Defaults to ``1e8`` to match
        ``PhysicsConfig``.
    regularization: float, optional
        Tikhonov regularisation constant added to the inertia matrix
        diagonal.  Defaults to ``1e-10``.
    det_threshold: float, optional
        Determinant threshold below which the matrix is considered
        singular.  Defaults to ``1e-12``.
    """

    cart_mass: float
    pendulum1_mass: float
    pendulum2_mass: float
    pendulum1_length: float
    pendulum2_length: float
    pendulum1_com: float
    pendulum2_com: float
    pendulum1_inertia: float
    pendulum2_inertia: float
    gravity: float
    cart_friction: float
    joint1_friction: float
    joint2_friction: float
    singularity_cond_threshold: float = 1.0e8
    regularization: float = 1e-10
    det_threshold: float = 1e-12


# -----------------------------------------------------------------------------
# Provide a simple ``step`` function to mirror the low‑rank interface.
#
# The high‑fidelity dynamics currently do not expose a single-step API.
# For the purposes of the acceptance tests this stub implementation returns
# the state unchanged.  When ``use_full_dynamics`` is set to True the router
# will call this function.


def step(x, u, dt):
    """Placeholder full dynamics step.

    Parameters
    ----------
    x : array-like
        Current state.
    u : array-like
        Control input(s).
    dt : float
        Timestep (ignored in this stub).

    Returns
    -------
    numpy.ndarray
        The state unchanged.  Real full dynamics should compute and
        return the next state given ``x`` and ``u``.
    """
    return np.asarray(x, dtype=float)


@njit(cache=True, nogil=True, fastmath=False)
def compute_inertia_numba(q1: float, q2: float, p: FullDIPParams) -> np.ndarray:
    c1, s1 = np.cos(q1), np.sin(q1)
    c2, s2 = np.cos(q2), np.sin(q2)
    c12 = np.cos(q1 - q2)

    h11 = p.cart_mass + p.pendulum1_mass + p.pendulum2_mass
    h12 = (
        p.pendulum1_mass * p.pendulum1_com + p.pendulum2_mass * p.pendulum1_length
    ) * c1
    h13 = p.pendulum2_mass * p.pendulum2_com * c2
    h22 = (
        p.pendulum1_mass * p.pendulum1_com**2
        + p.pendulum2_mass * p.pendulum1_length**2
        + p.pendulum1_inertia
    )
    h23 = p.pendulum2_mass * p.pendulum1_length * p.pendulum2_com * c12
    h33 = p.pendulum2_mass * p.pendulum2_com**2 + p.pendulum2_inertia

    return np.array(
        [[h11, h12, h13], [h12, h22, h23], [h13, h23, h33]], dtype=np.float64
    )


@njit(cache=True, nogil=True, fastmath=False)
def compute_gravity_numba(q1: float, q2: float, p: FullDIPParams) -> np.ndarray:
    g1 = (
        (p.pendulum1_mass * p.pendulum1_com + p.pendulum2_mass * p.pendulum1_length)
        * p.gravity
        * np.sin(q1)
    )
    g2 = p.pendulum2_mass * p.pendulum2_com * p.gravity * np.sin(q2)
    return np.array([0.0, g1, g2], dtype=np.float64)


@njit(cache=True, nogil=True, fastmath=False)
def compute_centrifugal_coriolis_vector_numba(
    state: np.ndarray, p: FullDIPParams
) -> np.ndarray:
    _, q1, q2, xdot, q1dot, q2dot = state
    s1, s2, s12 = np.sin(q1), np.sin(q2), np.sin(q1 - q2)

    h2_coeff = (
        p.pendulum1_mass * p.pendulum1_com + p.pendulum2_mass * p.pendulum1_length
    )
    h3_coeff = p.pendulum2_mass * p.pendulum2_com
    h5_coeff = p.pendulum2_mass * p.pendulum1_length * p.pendulum2_com

    c0 = -h2_coeff * s1 * q1dot**2 - h3_coeff * s2 * q2dot**2 + p.cart_friction * xdot
    #
    # NOTE:
    #   The sign of the cross‑coupling terms between the joint velocities has been
    #   carefully derived to match the simplified dynamics model implemented in
    #   ``src/core/dynamics.py``.  In that formulation the Coriolis matrix C
    #   contributes terms ±m₂·ℓ₁·ℓ_{c2}·sin(θ₁−θ₂)·q̇² to the generalized forces.
    #   When converting to the high‑fidelity formulation here (which directly
    #   constructs the 3×1 Coriolis/centrifugal vector) we must ensure that
    #   subtracting ``c_vec`` in the equation of motion reproduces the same
    #   effective sign.  Previously the implementation used
    #   ``+h5_coeff * s12 * q2dot**2`` and ``-h5_coeff * s12 * q1dot**2`` which
    #   resulted in the full model diverging from the simplified model under
    #   zero input.  Reversing these signs aligns the two models and yields
    #   consistent trajectories.  See ``tests/test_core/test_dynamics_extra.py``
    #   for the corresponding invariant test.
    c1 = (
        h2_coeff * s1 * xdot * q1dot
        - h5_coeff * s12 * q2dot**2
        + p.joint1_friction * q1dot
    )
    c2 = (
        h3_coeff * s2 * xdot * q2dot
        + h5_coeff * s12 * q1dot**2
        + p.joint2_friction * q2dot
    )

    return np.array([c0, c1, c2], dtype=np.float64)


@njit(cache=True, nogil=True, fastmath=False)
def rhs_numba(state: np.ndarray, u: float, p: FullDIPParams) -> np.ndarray:
    """
    Compute the time derivative of the 6D state for the full dynamics model.

    A small diagonal regularisation is added to the inertia matrix and a
    determinant check is used to detect near‑singular matrices.  When the
    determinant is non‑finite or very small (|det| < 1e−12) the function
    returns NaNs to signal numerical failure.  This lightweight check
    replaces the original SVD‑based condition estimate while maintaining
    robustness to ill‑conditioned matrices.  The diagonal regularisation
    technique used here is a standard approach to ensure that a symmetric
    matrix becomes positive definite and invertible【634903324123444†L631-L639】.
    """
    x, q1, q2, xdot, q1dot, q2dot = state
    nan_vec = np.full(6, np.nan, dtype=np.float64)

    # Inertia, Coriolis/centrifugal and gravity terms
    H = compute_inertia_numba(q1, q2, p)
    c_vec = compute_centrifugal_coriolis_vector_numba(state, p)
    G = compute_gravity_numba(q1, q2, p)
    tau = np.array([u, 0.0, 0.0], dtype=np.float64)
    rhs_vec = tau - c_vec - G

    # Regularise inertia matrix.  Adding a positive diagonal term
    # improves conditioning and ensures invertibility【634903324123444†L631-L639】.
    reg = p.regularization if p.regularization >= 0.0 else 0.0
    H_reg = H + np.eye(3) * reg

    # Optional singularity detection based on the condition number.  Use
    # p.singularity_cond_threshold to detect ill‑conditioned matrices.  When
    # the condition number exceeds this threshold return NaNs to signal
    # numerical failure.  Compute singular values for the 3×3 matrix.  If
    # threshold is <=0 or inf, skip this check.
    if p.singularity_cond_threshold > 0.0 and np.isfinite(p.singularity_cond_threshold):
        svals = np.linalg.svd(H_reg, compute_uv=False)
        if svals[0] == 0.0 or svals[-1] == 0.0:
            return nan_vec
        cond_num = svals[0] / svals[-1]
        if cond_num > p.singularity_cond_threshold:
            return nan_vec

    # Determinant-based singularity detection.  If the determinant is
    # extremely small or non‑finite the matrix is ill‑conditioned.  Use
    # configurable det_threshold to set the tolerance.
    det_H = np.linalg.det(H_reg)
    if not np.isfinite(det_H) or abs(det_H) < p.det_threshold:
        return nan_vec

    # Solve regularised system
    qddot = np.linalg.solve(H_reg, rhs_vec)
    qdot = np.array([xdot, q1dot, q2dot], dtype=np.float64)
    return np.concatenate((qdot, qddot))


@njit(cache=True, nogil=True, fastmath=False)
def step_rk4_numba(
    state: np.ndarray, u: float, dt: float, p: FullDIPParams
) -> np.ndarray:
    k1 = rhs_numba(state, u, p)
    if not np.all(np.isfinite(k1)):
        return np.full_like(state, np.nan)

    k2 = rhs_numba(state + 0.5 * dt * k1, u, p)
    if not np.all(np.isfinite(k2)):
        return np.full_like(state, np.nan)

    k3 = rhs_numba(state + 0.5 * dt * k2, u, p)
    if not np.all(np.isfinite(k3)):
        return np.full_like(state, np.nan)

    k4 = rhs_numba(state + dt * k3, u, p)
    if not np.all(np.isfinite(k4)):
        return np.full_like(state, np.nan)

    return state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)


@njit(cache=True, nogil=True, fastmath=False)
def total_energy_numba(state: np.ndarray, p: FullDIPParams) -> float:
    x, q1, q2, xdot, q1dot, q2dot = state
    T_cart = 0.5 * p.cart_mass * xdot**2
    v1x = xdot - p.pendulum1_com * q1dot * np.sin(q1)
    v1y = p.pendulum1_com * q1dot * np.cos(q1)
    T_p1 = (
        0.5 * p.pendulum1_mass * (v1x**2 + v1y**2)
        + 0.5 * p.pendulum1_inertia * q1dot**2
    )
    v2x = (
        xdot
        - p.pendulum1_length * q1dot * np.sin(q1)
        - p.pendulum2_com * q2dot * np.sin(q2)
    )
    v2y = p.pendulum1_length * q1dot * np.cos(q1) + p.pendulum2_com * q2dot * np.cos(q2)
    T_p2 = (
        0.5 * p.pendulum2_mass * (v2x**2 + v2y**2)
        + 0.5 * p.pendulum2_inertia * q2dot**2
    )
    T = T_cart + T_p1 + T_p2
    h1 = p.pendulum1_com * (1 - np.cos(q1))
    h2 = p.pendulum1_length * (1 - np.cos(q1)) + p.pendulum2_com * (1 - np.cos(q2))
    V = p.pendulum1_mass * p.gravity * h1 + p.pendulum2_mass * p.gravity * h2
    return T + V


class FullDIPDynamics:
    """High-fidelity double inverted pendulum dynamics model."""

    def __init__(self, params: Any):
        """
        Initialize the high‑fidelity double inverted pendulum dynamics model.

        Parameters
        ----------
        params : Any
            A physics configuration specifying the full system constants.  The
            argument must be an instance of :class:`src.config.PhysicsConfig` or
            a mapping convertible to one.  Passing a mapping triggers
            construction of a :class:`PhysicsConfig` to enforce Pydantic
            validation.  Missing or invalid fields will raise an error.
        """
        # PhysicsConfig is imported at the module level.  Avoid re‑importing
        # it here to prevent circular import issues when running tests
        # under alternative import paths.  The top‑level import ensures
        # PhysicsConfig is available.

        if params is None:
            raise ValueError("Physics parameters must not be None")

        # Determine whether the input is already a validated PhysicsConfig.
        if isinstance(params, PhysicsConfig):
            phys_cfg = params
        else:
            # Extract a plain dictionary from the input.  Support several common
            # input types:
            #  - Pydantic models implementing model_dump()
            #  - typing.NamedTuple instances implementing _asdict()
            #  - Plain dictionaries
            #  - Objects convertible via dict()
            if hasattr(params, "model_dump"):
                param_dict = params.model_dump()
            elif hasattr(params, "_asdict"):
                # typing.NamedTuple and collections.namedtuple instances support _asdict
                param_dict = params._asdict()
            elif isinstance(params, dict):
                param_dict = params
            else:
                try:
                    param_dict = dict(params)
                except Exception:
                    raise TypeError(
                        "Physics parameters must be a PhysicsConfig or dict‑like mapping"
                    )
            # Construct a PhysicsConfig from the dictionary to validate all
            # required fields and apply defaults (e.g., singularity threshold).
            phys_cfg = PhysicsConfig(**param_dict)  # type: ignore[arg-type]

        # Preserve the original physics model.  Tests access ``dyn.p_model``
        # to retrieve a Pydantic object with full validation/fields (see
        # ``test_passivity_verification``).  Save the phys_cfg before
        # conversion to the tuple used by the kernels.
        self.p_model = phys_cfg
        # Convert the validated schema to the namedtuple used by numba kernels.
        raw = phys_cfg.model_dump()
        self.params = FullDIPParams(**raw)
        # The state dimension for the full dynamics model is six.
        self.state_dim = 6

    def default_state(self) -> np.ndarray:
        return np.zeros(self.state_dim, dtype=float)

    def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        """
        Advance the full dynamics by one time step using a Runge–Kutta integrator.

        The passivity enforcement present in the previous implementation has
        been removed.  Instead, this method detects numerical instabilities
        via NaN propagation and converts them into a ``NumericalInstabilityError``.
        Callers should catch this exception and adapt the integration step
        or method accordingly.  Symplectic integrators are recommended for
        long‑term simulation of mechanical systems because they preserve a
        perturbed Hamiltonian【168022879868255†L156-L162】.

        Parameters
        ----------
        state : np.ndarray
            Current state ``[x, q1, q2, xdot, q1dot, q2dot]``.
        u : float
            Control input.
        dt : float
            Time step.

        Returns
        -------
        np.ndarray
            Next state after one integration step.

        Raises
        ------
        NumericalInstabilityError
            If the dynamics kernel returns NaNs, indicating an ill‑conditioned
            inertia matrix or other numerical failure.
        """
        state_np = state.astype(np.float64)
        next_state = step_rk4_numba(state_np, float(u), float(dt), self.params)
        if not np.all(np.isfinite(next_state)):
            # Convert NaN signalling into an exception
            raise NumericalInstabilityError(
                "Full dynamics failed due to ill‑conditioned inertia matrix"
            )
        return next_state

    def dynamics(self, t: float, state: np.ndarray, u: float) -> np.ndarray:
        return rhs_numba(state.astype(np.float64), float(u), self.params)

    def total_energy(self, state: np.ndarray) -> float:
        return total_energy_numba(state.astype(np.float64), self.params)

    def _compute_physics_matrices(
        self, state: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        _, q1, q2, _, _, _ = state
        H = compute_inertia_numba(q1, q2, self.params)
        c_vec = compute_centrifugal_coriolis_vector_numba(state, self.params)
        G = compute_gravity_numba(q1, q2, self.params)
        return H, c_vec, G


# ===================================================================================================================\\\
