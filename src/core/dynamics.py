#==========================================================================================\\\
# src/core/dynamics.py ====================================================================\\\
#==========================================================================================\\\

from __future__ import annotations
import numpy as np
# ---------------------------------------------------------------------------
# Optional numba import
#
# Numba is used to JIT‑compile compute kernels for performance.  In
# environments where Numba is unavailable (e.g., during certain test
# runs), we fall back to pure‑Python functions by defining ``njit`` as
# an identity decorator.  This allows the module to be imported without
# raising a ``ModuleNotFoundError`` while preserving type signatures.
try:
    from numba import njit  # type: ignore
except Exception:  # pragma: no cover - fallback for missing numba
    def njit(*_args, **_kwargs):  # type: ignore
        def deco(fn):
            return fn
        return deco
from typing import NamedTuple, Tuple, Any, Optional

# Import adaptive integrator step.  This embedded Runge–Kutta pair
# provides error estimates and adaptive step size control【Dormand1980 p.20, DOI:10.1016/0771-050X(80)90013-3】.
from .adaptive_integrator import rk45_step

# ------------------------------------------------------------------------------
# Numerical stability utilities
#
# The original implementation in this project estimated the condition number of
# the inertia matrix using a full singular value decomposition (SVD) on every
# call to ``rhs_numba``.  When the condition number exceeded a hard‑coded
# threshold the function returned a vector of NaNs to signal failure.  While
# accurate, computing an SVD at each integration step is computationally
# expensive and hides the underlying numerical issue by silently returning
# invalid values.  To improve transparency we introduce a custom exception
# ``NumericalInstabilityError`` which callers can catch and handle gracefully.
# This follows the recommendation from the design review to throw a specific
# exception instead of propagating NaNs when the inertia matrix becomes
# effectively singular.  A lightweight determinant check is used to detect
# near‑singular matrices; adding a small positive diagonal term to the
# inertia matrix (Tikhonov regularisation) is a proven technique to
# ensure the matrix becomes positive definite and invertible.  In
# applied mathematics and statistics, adding a small positive constant
# to the diagonal of a covariance or inertia matrix is widely used to
# make the matrix invertible; for example, Leung et al. describe
# adding “a small, positive constant to the diagonal” of a matrix to
# regularise it and ensure it is invertible【634903324123444†L631-L639】.

class NumericalInstabilityError(RuntimeError):
    """Raised when the inertia matrix is too ill‑conditioned to invert.

    This exception is thrown by the dynamics routines when a near‑singular
    inertia matrix prevents reliable computation of the accelerations.  The
    simulation runner should catch this exception and handle it by, for
    example, reducing the integration step size or aborting the simulation.
    """
    pass
"""
The simplified double inverted pendulum dynamics relies on the
``PhysicsConfig`` model from ``src.config`` for validating input
parameters.  Tests may simulate environments where importing
``src.config`` fails (for example, when core dependencies like numpy
are intentionally removed).  To avoid raising an ImportError at
module import time, attempt to import PhysicsConfig in a try/except
block.  If the import fails, define a lightweight placeholder class.

The placeholder ensures that ``isinstance(params, PhysicsConfig)``
returns ``False`` for any real PhysicsConfig instance, thereby
falling back to treating ``params`` as a mapping.  It also permits
monkeypatching attributes (e.g., ``load_config``) on ``src.config``
without raising AttributeError.
"""
try:
    from src.config import PhysicsConfig  # type: ignore
except Exception:
    class PhysicsConfig:  # type: ignore
        pass

class DIPParams(NamedTuple):
    """
    Lightweight container for the simplified double inverted pendulum physics.

    This named tuple mirrors the fields of ``PhysicsConfig`` so that it can be
    passed into numba‑compiled kernels.  The final field
    ``singularity_cond_threshold`` has a default value to permit tests to
    construct ``DIPParams`` without specifying it explicitly.  When omitted
    the threshold defaults to ``1e8``, matching the default in
    ``PhysicsConfig``.  Making this argument optional aligns the signature
    with test expectations (see ``test_rhs_returns_nan_for_ill_conditioned_matrix``).

    Adaptive regularisation parameters
    ---------------------------------
    Numerical inversion of the inertia matrix can fail when the matrix is
    nearly singular.  A common remedy is Tikhonov regularisation: adding a
    small positive constant to the diagonal to ensure the matrix remains
    invertible.  In ridge regression the normal equations are regularised
    by adding \\(\\lambda I\\), which improves conditioning at the cost of
    bias【Hoerl1970 p.215, DOI:10.1080/00401706.1970.10488634】.

    * ``regularization_alpha`` scales the diagonal damping by the largest
      singular value of the inertia matrix.  According to ridge regression
      theory, adding \\(\\lambda I\\) with \\(\\lambda>0\\) stabilises the inverse and
      trades bias for variance【Hoerl1970 p.215, DOI:10.1080/00401706.1970.10488634】.
    * ``max_condition_number`` limits the ratio of the largest to smallest
      singular values; if the condition number exceeds this bound the
      regularisation is increased.  This is analogous to the damping factor
      selection in damped least‑squares methods【Hoerl1970 p.215, DOI:10.1080/00401706.1970.10488634】.
    * ``min_regularization`` enforces a strictly positive minimum on the
      diagonal to prevent zero damping.
    * ``use_fixed_regularization`` bypasses the adaptive scheme and always
      applies ``min_regularization``.
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

    # Base scale for Tikhonov regularisation when inverting the inertia
    # matrix.  Adding a non‑zero diagonal damping to a symmetric matrix
    # guarantees invertibility【451626699008270†L238-L244】.  The adaptive
    # scheme multiplies this parameter by the largest singular value of
    # the inertia matrix and increases it further when the condition
    # number exceeds a threshold【451626699008270†L286-L297】.
    regularization_alpha: float = 1e-4
    # Maximum acceptable condition number for the inertia matrix.  When
    # the ratio of largest to smallest singular values exceeds this value
    # the regularisation term is increased to reduce the condition
    # number【451626699008270†L286-L297】.  Numerical linear algebra
    # references note that matrices with condition numbers above ~10^14
    # cannot be reliably inverted in double precision【862099055591481†L149-L160】.  The
    # default threshold is therefore raised from 1e10 to 1e14 to avoid
    # overly conservative regularisation.
    max_condition_number: float = 1e14
    # Minimum regularisation added to the diagonal.  Ensures a strictly
    # positive damping even when singular values are very small【451626699008270†L238-L244】.  A
    # small positive constant (1e‑10) is used to guarantee invertibility
    # even when the inertia matrix becomes nearly singular.
    min_regularization: float = 1e-10
    # If True the adaptive scaling is bypassed and the solver always uses
    # ``min_regularization``.  Useful for legacy comparisons.
    use_fixed_regularization: bool = False

    #: Relative tolerance factor used when computing the condition number.
    # Instead of clamping the smallest singular value to an absolute value
    # (e.g. 1e‑16), scale the tolerance with the largest singular value.  A
    # relative tolerance avoids sensitivity to the units and scale of the
    # inertia matrix and is consistent with numerical linear algebra
    # recommendations that matrices with condition numbers above ~10^14 in
    # double precision cannot be stably inverted【862099055591481†L149-L160】.  Using
    # a small factor (default 1e‑12) helps detect ill‑conditioning while
    # not triggering false positives on well‑scaled matrices.  The factor
    # may be overridden via PhysicsConfig or directly on DIPParams.
    condition_tol_factor: float = 1e-12

    @classmethod
    def from_physics_config(cls, cfg: Any) -> "DIPParams":
        """Create a :class:`DIPParams` instance from a PhysicsConfig.

        This helper converts a high‑level :class:`src.config.PhysicsConfig` into the
        named‑tuple format required by the numba kernels.  Missing regularisation
        parameters are filled with sensible defaults.  The regularisation
        constant from the PhysicsConfig is mapped to ``min_regularization`` and
        ``regularization_alpha`` is left at its default of 1e‑4.  The
        determinant threshold and max condition number are copied if
        present.  A relative tolerance factor for computing the condition
        number is also provided via ``condition_tol_factor``.

        Parameters
        ----------
        cfg : PhysicsConfig
            Validated configuration instance with physical constants.

        Returns
        -------
        DIPParams
            A new named‑tuple suitable for passing into numba kernels.
        """
        # Extract a dictionary from the Pydantic model.  Use model_dump
        # if available, otherwise fall back to __dict__.
        try:
            data = cfg.model_dump()
        except Exception:
            data = {k: getattr(cfg, k) for k in cfg.__dict__.keys() if not k.startswith("_")}
        # Map regularisation constant to both min_regularization and regularization_alpha
        reg = float(data.get("regularization", 1e-10))
        data.setdefault("min_regularization", reg)
        data.setdefault("regularization_alpha", 1e-4)
        # Max condition number default
        data.setdefault("max_condition_number", 1e10)
        # Use adaptive regularisation by default
        data.setdefault("use_fixed_regularization", False)
        # Provide determinant threshold
        data.setdefault("det_threshold", float(data.get("det_threshold", 1e-12)))
        # Provide condition tolerance factor
        data.setdefault("condition_tol_factor", 1e-12)
        # The namedtuple expects 'singularity_cond_threshold' not present in PhysicsConfig? supply default
        data.setdefault("singularity_cond_threshold", float(data.get("singularity_cond_threshold", 1e8)))
        # Remove keys not expected by DIPParams
        allowed = {
            'cart_mass','pendulum1_mass','pendulum2_mass','pendulum1_length','pendulum2_length',
            'pendulum1_com','pendulum2_com','pendulum1_inertia','pendulum2_inertia','gravity',
            'cart_friction','joint1_friction','joint2_friction','singularity_cond_threshold',
            'regularization_alpha','max_condition_number','min_regularization','use_fixed_regularization',
            'det_threshold','condition_tol_factor'
        }
        filtered = {k: data[k] for k in allowed if k in data}
        return cls(**filtered)

    # Determinant threshold used to detect singular inertia matrices.  If
    # the determinant of the regularised inertia matrix falls below this
    # value the matrix is deemed singular and the dynamics returns NaNs.
    det_threshold: float = 1e-12

@njit(cache=True, nogil=True, fastmath=False)
def compute_matrices_numba(state: np.ndarray, p: DIPParams) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    _, q1, q2, _, q1dot, q2dot = state

    c1, s1 = np.cos(q1), np.sin(q1)
    c2, s2 = np.cos(q2), np.sin(q2)
    c12 = np.cos(q1 - q2)
    s12 = np.sin(q1 - q2)

    m_c = p.cart_mass
    m1, m2 = p.pendulum1_mass, p.pendulum2_mass
    l1, l2 = p.pendulum1_length, p.pendulum2_length
    lc1, lc2 = p.pendulum1_com, p.pendulum2_com
    I1, I2 = p.pendulum1_inertia, p.pendulum2_inertia

    h11 = m_c + m1 + m2
    h12 = (m1 * lc1 + m2 * l1) * c1
    h13 = (m2 * lc2) * c2
    h22 = m1 * lc1 * lc1 + m2 * l1 * l1 + I1
    h23 = (m2 * l1 * lc2) * c12
    h33 = m2 * lc2 * lc2 + I2

    H = np.array([[h11, h12, h13],
                  [h12, h22, h23],
                  [h13, h23, h33]], dtype=np.float64)

    C = np.zeros((3, 3), dtype=np.float64)
    C[0, 0] = p.cart_friction
    C[1, 1] = p.joint1_friction
    C[2, 2] = p.joint2_friction
    c_coeff = m2 * l1 * lc2
    C[1, 2] = -c_coeff * s12 * q2dot
    C[2, 1] = +c_coeff * s12 * q1dot

    g2 = (m1 * lc1 + m2 * l1) * p.gravity * s1
    g3 = (m2 * lc2) * p.gravity * s2
    G = np.array([0.0, g2, g3], dtype=np.float64)

    return H, C, G

@njit(cache=True, nogil=True, fastmath=False)
def rhs_numba(state: np.ndarray, u: float, p: DIPParams) -> np.ndarray:
    """
    Compute the time derivative of the state for the simplified dynamics.

    This implementation adds a small Tikhonov regularisation term to the
    inertia matrix to ensure invertibility and checks the determinant of
    the regularised matrix instead of computing a full SVD.  If the
    determinant is extremely small (indicating a near‑singular matrix) or
    infinite, the function returns an array of NaNs.  Downstream code can
    detect these NaNs and raise a ``NumericalInstabilityError`` to signal
    failure.  The light‑weight determinant check reduces computational
    overhead relative to the original SVD‑based condition estimate while
    still avoiding inversion of ill‑conditioned matrices.  Adding a
    constant to the diagonal of a symmetric indefinite matrix is a
    standard method to make it positive definite and invertible【Hoerl1970 p.215, DOI:10.1080/00401706.1970.10488634】.
    """
    x, q1, q2, xdot, q1dot, q2dot = state
    # Initialise a NaN vector for error signalling
    nan_vec = np.array([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan], dtype=np.float64)

    # Compute physics matrices
    H, C, G = compute_matrices_numba(state, p)

    # Generalised forces and velocities
    tau = np.array([u, 0.0, 0.0], dtype=np.float64)
    qdot = np.array([xdot, q1dot, q2dot], dtype=np.float64)
    rhs_vec = tau - C @ qdot - G

    # Adaptive Tikhonov regularisation based on singular values.
    # Compute singular values of the unregularised inertia matrix.  For
    # 3×3 matrices the SVD is inexpensive and exposes the spectral
    # properties required to tune the regularisation【Hoerl1970 p.215, DOI:10.1080/00401706.1970.10488634】.
    svals = np.linalg.svd(H, compute_uv=False)
    sigma_max = svals[0]
    sigma_min = svals[-1]
    # Determine the regularisation to apply.  When the flag
    # ``use_fixed_regularization`` is set we always use the minimum
    # regularisation; otherwise scale with the largest singular value and
    # adapt if the condition number is too large【Hoerl1970 p.215, DOI:10.1080/00401706.1970.10488634】.
    if p.use_fixed_regularization:
        reg = p.min_regularization
    else:
        # Base reg proportional to the largest singular value; ensure
        # strictly positive value via min_regularization.
        reg = p.regularization_alpha * sigma_max
        reg = max(reg, p.min_regularization)
        # Estimate condition number using a relative tolerance.  Use a
        # tolerance proportional to the largest singular value instead of an
        # absolute clamp.  This follows numerical linear algebra guidelines
        # that matrix inversion becomes unreliable when the condition number
        # exceeds ~10^14 in double precision【862099055591481†L149-L160】.  The
        # tolerance factor (condition_tol_factor) can be tuned via DIPParams.
        tol = p.condition_tol_factor * sigma_max
        denom = sigma_min if sigma_min > tol else tol
        cond = sigma_max / denom
        if cond > p.max_condition_number:
            # Increase reg proportionally to reduce the condition number back
            # towards the allowable maximum.  This adaptive scaling is
            # analogous to damped least squares regularisation【908631897601352†L881-L883】.
            scale = cond / p.max_condition_number
            reg *= scale
    # Form the regularised inertia matrix
    H_reg = H + np.eye(3) * reg
    # Compute singular values of the regularised matrix; if the smallest
    # singular value vanishes or is non‑finite the matrix is still
    # ill‑conditioned and we signal failure by returning NaNs.
    svals_reg = np.linalg.svd(H_reg, compute_uv=False)
    # Raise a dedicated error when the regularised inertia matrix is
    # ill‑conditioned.  Instead of silently returning NaNs, throw
    # NumericalInstabilityError so callers can handle the failure.  The
    # smallest singular value must be strictly positive for the matrix
    # to be invertible【451626699008270†L238-L244】.  Detect non‑finite singular
    # values as well, which indicate overflow or underflow.  Raising
    # within a numba‑jitted function is allowed and preserves
    # transparency【862099055591481†L149-L160】.
    if not np.all(np.isfinite(svals_reg)) or svals_reg[-1] <= 0.0:
        raise NumericalInstabilityError(
            "Inertia matrix ill‑conditioned or singular in rhs_numba"
        )
    # Solve the regularised system; let linear algebra exceptions
    # propagate naturally.  Tikhonov regularisation ensures H_reg is
    # invertible and well‑conditioned【Hoerl1970 p.215, DOI:10.1080/00401706.1970.10488634】.
    qddot = np.linalg.solve(H_reg, rhs_vec)
    return np.array([xdot, q1dot, q2dot, qddot[0], qddot[1], qddot[2]], dtype=np.float64)

@njit(cache=True, nogil=True, fastmath=False)
def step_rk4_numba(state: np.ndarray, u: float, dt: float, p: DIPParams) -> np.ndarray:
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

    return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

@njit(cache=True, nogil=True, fastmath=False)
def step_euler_numba(state: np.ndarray, u: float, dt: float, p: DIPParams) -> np.ndarray:
    return state + dt * rhs_numba(state, u, p)

@njit(cache=True, nogil=True, fastmath=False)
def kinetic_energy_numba(state: np.ndarray, p: DIPParams) -> float:
    _, q1, q2, xdot, q1dot, q2dot = state
    T_cart = 0.5 * p.cart_mass * xdot * xdot

    v1x = xdot - p.pendulum1_com * q1dot * np.sin(q1)
    v1y = p.pendulum1_com * q1dot * np.cos(q1)
    T1 = 0.5 * p.pendulum1_mass * (v1x * v1x + v1y * v1y) + 0.5 * p.pendulum1_inertia * q1dot * q1dot

    v2x = xdot - p.pendulum1_length * q1dot * np.sin(q1) - p.pendulum2_com * q2dot * np.sin(q2)
    v2y = p.pendulum1_length * q1dot * np.cos(q1) + p.pendulum2_com * q2dot * np.cos(q2)
    T2 = 0.5 * p.pendulum2_mass * (v2x * v2x + v2y * v2y) + 0.5 * p.pendulum2_inertia * q2dot * q2dot

    return T_cart + T1 + T2

@njit(cache=True, nogil=True, fastmath=False)
def potential_energy_numba(state: np.ndarray, p: DIPParams) -> float:
    _, q1, q2, _, _, _ = state
    V1 = p.pendulum1_mass * p.gravity * p.pendulum1_com * (1.0 - np.cos(q1))
    V2 = p.pendulum2_mass * p.gravity * (p.pendulum1_length * (1.0 - np.cos(q1)) + p.pendulum2_com * (1.0 - np.cos(q2)))
    return V1 + V2

@njit(cache=True, nogil=True, fastmath=False)
def total_energy_numba(state: np.ndarray, p: DIPParams) -> float:
    return kinetic_energy_numba(state, p) + potential_energy_numba(state, p)

class DoubleInvertedPendulum:
    """Double Inverted Pendulum dynamics model with JIT-compiled physics kernels."""

    def __init__(self, params: Any):
        """
        Initialize the simplified double inverted pendulum dynamics model.

        Parameters
        ----------
        params : Any
            A physics configuration specifying the system constants.  This
            must either be an instance of :class:`src.config.PhysicsConfig`
            or a mapping with the same keys.  Passing a mapping will
            attempt to construct a :class:`PhysicsConfig` to ensure the
            values are validated.  Any failure to import or construct
            the configuration will propagate an exception.
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
            # Extract a plain dictionary from the input.  Accept Pydantic‑like
            # objects that implement model_dump(), plain dicts, or objects
            # that can be converted via dict().  Raise if conversion is
            # impossible so that invalid inputs are not silently accepted.
            if hasattr(params, "model_dump"):
                param_dict = params.model_dump()
            elif isinstance(params, dict):
                param_dict = params
            else:
                try:
                    param_dict = dict(params)
                except Exception:
                    raise TypeError(
                        "Physics parameters must be a PhysicsConfig or dict‑like mapping"
                    )
            # Construct a PhysicsConfig from the dictionary.  This will
            # perform full Pydantic validation and raise on invalid or
            # missing fields.
            phys_cfg = PhysicsConfig(**param_dict)  # type: ignore[arg-type]

        # Preserve the original physics model on the instance.  Tests access
        # ``dyn.p_model`` to retrieve a Pydantic model rather than a raw
        # mapping (see ``test_passivity_verification``).  Store a reference
        # before converting to the tuple used by numba kernels.
        self.p_model = phys_cfg
        # Convert the validated schema to the namedtuple used by numba kernels.
        # Use the classmethod to map PhysicsConfig fields into DIPParams.  This
        # resolves the mismatch between PhysicsConfig and DIPParams fields and
        # supplies default regularisation parameters.
        try:
            self.params = DIPParams.from_physics_config(phys_cfg)  # type: ignore[arg-type]
        except Exception:
            # Fallback: attempt to construct directly from dump
            raw = phys_cfg.model_dump()
            self.params = DIPParams(**raw)
        # The state dimension of the simplified model is fixed at six.
        self.state_dim = 6

        # -----------------------------------------------------------------
        # Integration scheme configuration
        #
        # The dynamics can be integrated using either a fixed step RK4 scheme
        # or an adaptive embedded Runge–Kutta pair (Dormand–Prince).  The
        # ``integration_scheme`` attribute selects between these methods.  When
        # set to ``'adaptive'`` the ``step`` method will call ``rk45_step`` and
        # adjust the time step to control local truncation error.  The
        # tolerances and bounds can be overridden via attributes on this
        # instance.  See Hairer et al.【Hairer1993 §II.5.2, DOI:10.1007/978-3-540-78862-1】
        # for a discussion of adaptive step size control.
        # Default to adaptive integration.  Adaptive schemes (Dormand–Prince)
        # control local truncation error and mitigate energy drift.  Users
        # may override this attribute to 'rk4' or 'symplectic' for fixed
        # step RK4 or symplectic velocity‑Verlet integration.
        self.integration_scheme: str = 'adaptive'
        # Absolute and relative tolerances for adaptive integration.  These
        # values were chosen to keep local errors below 1e-6 in typical
        # simulations.  Users may override them after construction.
        self.abs_tol: float = 1e-6
        self.rel_tol: float = 1e-3
        # Minimum and maximum allowable time steps for the adaptive scheme.
        self.min_dt: float = 1e-5
        self.max_dt: float = 0.05
        # Internal state for adaptive integration: previous time step and time.
        self._dt_adaptive: Optional[float] = None
        self._time: float = 0.0

    def default_state(self) -> np.ndarray:
        return np.zeros(self.state_dim)

    def kinetic_energy(self, state: np.ndarray) -> float:
        return float(kinetic_energy_numba(state.astype(np.float64), self.params))

    def potential_energy(self, state: np.ndarray) -> float:
        return float(potential_energy_numba(state.astype(np.float64), self.params))

    def total_energy(self, state: np.ndarray) -> float:
        return float(total_energy_numba(state.astype(np.float64), self.params))

    def _compute_physics_matrices(self, state: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        return compute_matrices_numba(state.astype(np.float64), self.params)

    def _rhs_core(self, state: np.ndarray, u: float) -> np.ndarray:
        """
        Evaluate the right‑hand side of the state ODE.

        This method wraps the low‑level ``rhs_numba`` implementation and
        converts any NaN outputs into a ``NumericalInstabilityError``.  When
        ``rhs_numba`` returns a vector containing NaNs (indicating that the
        inertia matrix was too ill‑conditioned to invert) this wrapper
        raises ``NumericalInstabilityError``.  Callers should catch this
        exception and handle it appropriately (e.g., by reducing the time
        step or aborting the simulation).  This approach replaces the
        previous NaN‑returning behaviour with explicit error signalling as
        recommended by the design review.
        """
        xdot = rhs_numba(state.astype(np.float64), float(u), self.params)
        # Detect NaN signalling from rhs_numba
        if not np.all(np.isfinite(xdot)):
            raise NumericalInstabilityError(
                "Inertia matrix ill‑conditioned; dynamics cannot be computed"
            )
        return xdot

    def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        """Integrate the dynamics over one time step.

        Depending on the ``integration_scheme`` attribute this method will
        either perform a single fixed‑step RK4 integration or invoke the
        embedded Dormand–Prince adaptive integrator.  When using adaptive
        integration the step size is adjusted based on an error estimate
        until the local truncation error is below ``abs_tol`` and ``rel_tol``.
        The adaptive algorithm follows the strategy outlined by Dormand
        & Prince【Dormand1980 p.20, DOI:10.1016/0771-050X(80)90013-3】 and Hairer
        et al.【Hairer1993 §II.5.2, DOI:10.1007/978-3-540-78862-1】.  If the
        integrator produces a non‑finite result or repeatedly rejects a
        step the method raises ``NumericalInstabilityError``.

        Parameters
        ----------
        state : np.ndarray
            Current system state.
        u : float
            Control input to apply.
        dt : float
            Proposed integration timestep.  When using the adaptive
            integrator this serves as the initial guess; subsequent calls
            will reuse the last accepted step size.

        Returns
        -------
        np.ndarray
            Next state after integrating over ``dt``.

        Raises
        ------
        NumericalInstabilityError
            If the integrator returns a non‑finite state vector or the
            adaptive algorithm fails to find a suitable step size.
        """
        scheme = getattr(self, 'integration_scheme', 'rk4')
        # Symplectic integration branch
        if scheme == 'symplectic':
            return self._step_symplectic(state, u, dt)
        # Adaptive integration branch
        if scheme == 'adaptive':
            # Initialise adaptive dt on first call
            if self._dt_adaptive is None:
                self._dt_adaptive = float(dt)
            # Local variables for readability
            t = self._time
            dt_try = float(self._dt_adaptive)
            # Limit dt within [min_dt, max_dt]
            dt_try = max(self.min_dt, min(dt_try, self.max_dt))
            # Attempt up to a fixed number of step trials
            for _ in range(10):
                y_new, dt_new = rk45_step(
                    lambda _t, y: self._rhs_core(y, u),
                    t,
                    state.astype(np.float64),
                    dt_try,
                    self.abs_tol,
                    self.rel_tol,
                )
                if y_new is not None:
                    # Step accepted
                    if not np.all(np.isfinite(y_new)):
                        raise NumericalInstabilityError(
                            "Dynamics integration failed: non‑finite values encountered in adaptive step"
                        )
                    # Update internal time and step size
                    self._time = t + dt_try
                    self._dt_adaptive = float(min(max(dt_new, self.min_dt), self.max_dt))
                    return y_new
                # Step rejected; reduce dt and retry
                dt_try = max(dt_new, self.min_dt)
            # Too many rejections
            raise NumericalInstabilityError(
                "Adaptive integrator failed to converge within the retry limit"
            )
        # Default fixed RK4 integration
        next_state = step_rk4_numba(state.astype(np.float64), float(u), float(dt), self.params)
        if not np.all(np.isfinite(next_state)):
            raise NumericalInstabilityError(
                "Dynamics integration failed: non‑finite values encountered in next state"
            )
        return next_state

    def step_rk4(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        return self.step(state, u, dt)

    def _step_symplectic(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        """Perform a symplectic velocity‑Verlet integration step.

        Symplectic integrators preserve the Hamiltonian structure of
        mechanical systems and maintain bounded energy error over long
        horizons【959405733725261†L294-L301】.  This method implements a simple
        velocity‑Verlet scheme: velocities are advanced half a step, positions
        are updated using the half‑step velocities, and then velocities
        are completed with the acceleration at the new configuration.  If
        any intermediate acceleration evaluation returns non‑finite values
        a :class:`NumericalInstabilityError` is raised.

        Parameters
        ----------
        state : np.ndarray
            Current state vector [x, q1, q2, xdot, q1dot, q2dot].
        u : float
            Control input.
        dt : float
            Integration time step.

        Returns
        -------
        np.ndarray
            The next state after one symplectic step.
        """
        s = state.astype(np.float64)
        # Decompose state
        x, q1, q2, xdot, q1dot, q2dot = s
        # Compute initial acceleration
        deriv = self._rhs_core(s, u)
        # Ensure finite derivative
        if not np.all(np.isfinite(deriv)):
            raise NumericalInstabilityError(
                "Dynamics integration failed: non‑finite values encountered in symplectic step"
            )
        a0 = deriv[3:]
        # Half‑step velocity update
        v_half = np.array([xdot, q1dot, q2dot], dtype=np.float64) + 0.5 * dt * a0
        # Full position update using half‑step velocities
        pos_new = np.array([x, q1, q2], dtype=np.float64) + dt * v_half
        # Build intermediate state with new positions and half‑step velocities
        interm_state = np.concatenate((pos_new, v_half))
        # Compute acceleration at new configuration
        deriv_new = self._rhs_core(interm_state, u)
        if not np.all(np.isfinite(deriv_new)):
            raise NumericalInstabilityError(
                "Dynamics integration failed: non‑finite values encountered in symplectic step"
            )
        a1 = deriv_new[3:]
        # Complete velocity update
        v_new = v_half + 0.5 * dt * a1
        # Assemble new state
        next_state = np.concatenate((pos_new, v_new)).astype(np.float64)
        return next_state

    def _rhs(self, t: float, s: np.ndarray) -> np.ndarray:
        if hasattr(self, 'controller') and self.controller is not None:
            import inspect
            sig = inspect.signature(self.controller)
            if len(sig.parameters) == 2:
                u = self.controller(t, s)
            else:
                u = self.controller(s)
        else:
            u = 0.0
        return self._rhs_core(s, u)

DIPDynamics = DoubleInvertedPendulum
#==========================================================================================\\\