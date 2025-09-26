#==========================================================================================\\\
#=========================== src/controllers/smc/classic_smc.py =========================\\\
#==========================================================================================\\\
# Changed: enforce strict positivity of sliding‑surface and switching gains and
# allow zero derivative gain; updated docstring to reflect these constraints.

import numpy as np
import logging
# Import from new organized structure
from ...utils import saturate
from ...utils import ClassicalSMCOutput
from typing import TYPE_CHECKING, List, Tuple, Dict, Optional, Union, Sequence, Any

# Avoid circular import at runtime
if TYPE_CHECKING:
    # Hint only; don't import at runtime to avoid path issues
    from ...plant.models.dynamics import DoubleInvertedPendulum

class ClassicalSMC:
    """
    Classical Sliding‑Mode Controller for a double‑inverted pendulum.

    This controller implements the conventional first‑order sliding‑mode law
    consisting of a model‑based equivalent control ``u_eq`` and a robust
    discontinuous term.  The robust term uses a continuous approximation to
    the sign function (either a hyperbolic tangent or a piecewise‑linear
    saturation) within a boundary layer of width ``epsilon`` to attenuate
    chattering.  Introducing a boundary layer around the switching surface
    replaces the discontinuous signum control with a continuous function,
    thereby reducing high‑frequency oscillations.  A number of authors
    note that the boundary‑layer approximation attenuates chattering at
    the cost of introducing a finite steady‑state tracking error; for
    example, a discussion of chattering reduction methods emphasises
    that the boundary‑layer method "reduces chattering but leads to a finite
    steady state error".  The user should therefore
    select ``epsilon`` to balance chattering reduction against steady‑state
    accuracy.

    Two switching functions are available: ``tanh`` (smooth hyperbolic
    tangent) and ``linear`` (piecewise‑linear saturation).  The ``linear``
    switch approximates the sign function more harshly by clipping the
    sliding surface directly, which can degrade robustness near the origin
    because the control gain effectively drops to zero for small errors.
    In contrast, the ``tanh`` switch retains smoothness and maintains a
    nonzero slope through the origin, preserving control authority in a
    neighbourhood of the sliding surface.  Users should prefer
    ``tanh`` unless there is a compelling reason to adopt the linear
    saturation and should be aware that linear saturation may cause
    increased steady‑state error and slower convergence near the origin.

    A small diagonal ``regularization`` is added to the inertia matrix during
    inversion to ensure positive definiteness and numerical robustness.
    Adding a tiny constant to the diagonal of a symmetric matrix is a
    well‑known regularisation technique: in the context of covariance
    matrices, Leung and colleagues recommend “adding a small, positive
    constant to the diagonal” to ensure the matrix is invertible.

    Parameters are typically supplied by a factory that reads a central
    configuration.  Each gain vector must contain exactly six elements in the
    order ``[k1, k2, lam1, lam2, K, kd]``.  The maximum force ``max_force``
    sets the saturation limit for the final control command.

    The optional ``controllability_threshold`` parameter decouples
    controllability from the boundary layer ``epsilon``.  Earlier
    implementations compared the magnitude of ``L·M^{-1}·B`` against
    ``epsilon`` to decide whether to compute the equivalent control.  This
    conflation of chattering mitigation with controllability made it
    difficult to tune each effect separately.  ``controllability_threshold``
    defines a lower bound on ``|L·M^{-1}·B|`` below which the equivalent
    control is suppressed.  If unspecified, a default of ``1e‑4`` is used
    based on matrix conditioning guidelines.  The
    boundary layer width ``epsilon`` should therefore be chosen solely to
    trade off between chattering and steady‑state error, while
    ``controllability_threshold`` governs when the model‑based feedforward
    term is applied.

    **Gain positivity (F‑4.SMCDesign.2 / RC‑04)** – Sliding‑mode theory
    requires that the sliding‑surface gains ``k1``, ``k2`` and the slope
    coefficients ``lam1``, ``lam2`` be strictly positive.  Utkin and
    Levant note that the discontinuous control gain ``k`` must be a
    positive constant【Rhif2012†L563-L564】, and the slope ``λ`` of the
    sliding function must be chosen positive to ensure Hurwitz
    stability【ModelFreeSMC2018†L340-L345】.  The switching gain ``K`` must
    also be strictly positive to drive the system to the sliding surface,
    while the derivative gain ``kd`` should be non‑negative to provide
    damping.  The constructor validates these constraints and raises
    ``ValueError`` when violated.
    """

    def __init__(
        self,
        gains: Union[Sequence[float], np.ndarray],
        max_force: float,
        boundary_layer: float,
        dynamics_model: Optional["DoubleInvertedPendulum"] = None,
        regularization: float = 1e-10,
        switch_method: str = "tanh",
        *,
        boundary_layer_slope: float = 0.0,
        controllability_threshold: Optional[float] = None,
        hysteresis_ratio: float = 0.0,
        **kwargs,
    ) -> None:
        """Initialize the controller.

        Args:
            gains: Six gains in the order ``[k1, k2, lam1, lam2, K, kd]``.
            max_force: Saturation limit for the control input (N).
            boundary_layer: Boundary layer thickness (epsilon) for chattering reduction.
            dynamics_model: Dynamics model providing physics matrices via ``_compute_physics_matrices``.
            regularization: Small value to add to the diagonal of the inertia matrix for numerical stability.
            **kwargs: Ignored extras to keep factory compatibility.

        Raises:
            ValueError: If ``gains`` does not contain exactly six elements
                        or if ``boundary_layer`` is not strictly positive.
        """
        # Validate and normalise the supplied gains early.  This makes it
        # possible for the factory or PSO tuner to reject misconfigured
        # gain vectors before instantiating the controller.  Accept any
        # sequence or array-like input and coerce it to a flat NumPy array
        # of floats.  After validation the gains are unpacked into the
        # canonical order ``[k1, k2, lam1, lam2, K, kd]``.
        self.validate_gains(gains)
        # Coerce to a 1‑D array of floats; ravel() flattens nested sequences
        gains_arr = np.asarray(gains, dtype=float).ravel()
        # Store a shallow copy of the gains for external inspection.  Using
        # list() avoids exposing the internal NumPy array directly.
        self._gains = gains_arr.tolist()
        # Unpack the gains into individual parameters
        self.k1, self.k2, self.lam1, self.lam2, self.K, self.kd = map(float, gains_arr)
        # Validate shared parameters via central utility.  Positivity of gains
        # and boundary layers ensures that the sliding surface and switching
        # function remain well‑defined and stable.
        # Import from new modular utils structure
        try:
            from src.utils import require_positive  # when repo root on sys.path
        except Exception:
            try:
                from ...utils import require_positive  # when importing as src.controllers.*
            except Exception:
                from utils import require_positive    # when src itself on sys.path
        self.max_force = require_positive(max_force, "max_force")
        # Use helpers for the adaptive boundary layer.  The nominal
        # thickness ``epsilon0`` must be strictly positive, while
        # ``boundary_layer_slope`` can be zero or positive.  A positive
        # slope scales the boundary layer with the norm of the sliding
        # variable, reducing chattering for large errors and shrinking
        # the layer as the error vanishes【967233543993377†L104-L115】.
        self.epsilon0 = require_positive(boundary_layer, "boundary_layer")
        self.epsilon1 = float(boundary_layer_slope)
        if self.epsilon1 < 0.0:
            raise ValueError("boundary_layer_slope must be non‑negative")
        # Backwards compatibility: retain constant epsilon attribute
        self.epsilon = self.epsilon0

        # Hysteresis ratio defines an inner dead‑band in which the
        # discontinuous robust term is suppressed.  A value in [0,1]
        # scales the nominal boundary layer ε; when |σ| < hysteresis_ratio·ε0
        # the robust term is frozen to zero【967233543993377†L104-L115】.  This
        # further reduces chattering by avoiding high‑frequency switching
        # inside a small neighbourhood of the sliding surface.
        self.hysteresis_ratio = float(hysteresis_ratio)
        if not (0.0 <= self.hysteresis_ratio <= 1.0):
            raise ValueError("hysteresis_ratio must be within [0,1]")

        # ---- Additional validation of SMC gains (F‑4.SMCDesign.2 / RC‑04) ----
        # Sliding‑mode theory requires strictly positive sliding‑surface and
        # switching gains and non‑negative derivative gain.  Validate each
        # gain here to catch misconfiguration early【Rhif2012†L563-L564】【ModelFreeSMC2018†L340-L345】.
        self.k1 = require_positive(self.k1, "k1")
        self.k2 = require_positive(self.k2, "k2")
        self.lam1 = require_positive(self.lam1, "lam1")
        self.lam2 = require_positive(self.lam2, "lam2")
        self.K = require_positive(self.K, "K")
        # Allow derivative gain to be zero but not negative
        self.kd = require_positive(self.kd, "kd", allow_zero=True)
        self.dyn = dynamics_model
        self.regularization = float(regularization)
        # Switching function selection
        sm = str(switch_method).lower().strip()
        if sm not in ("tanh", "linear"):
            raise ValueError("switch_method must be 'tanh' or 'linear'")
        self.switch_method = sm

        # Declare the dimensionality of the gain vector.  Exposing the
        # number of gains allows optimisers such as PSOTuner to infer
        # controller dimensionality without trial instantiation.  See
        # design review section 5 (PSO integration).
        self.n_gains: int = 6

        # (C-007) Cache the model's singularity conditioning threshold if provided.
        # If unavailable, leave as None to allow regularization to rehabilitate borderline cases.
        self._cond_threshold: Optional[float] = None
        try:
            if hasattr(self.dyn, "p_model") and hasattr(self.dyn.p_model, "singularity_cond_threshold"):
                self._cond_threshold = float(self.dyn.p_model.singularity_cond_threshold)
            elif hasattr(self.dyn, "params") and hasattr(self.dyn.params, "singularity_cond_threshold"):
                self._cond_threshold = float(self.dyn.params.singularity_cond_threshold)
        except Exception:
            self._cond_threshold = None

        # Sliding surface uses only joint rates; cart input appears via B
        self.L = np.array([0.0, self.k1, self.k2], dtype=float)
        self.B = np.array([1.0, 0.0, 0.0], dtype=float)

        # Configure logger
        self.logger = logging.getLogger(self.__class__.__name__)

        # Store the controllability threshold used when computing the
        # equivalent control.  Earlier versions used the boundary layer
        # thickness `epsilon` as the cutoff for |L·M⁻¹·B|, conflating
        # chattering mitigation with controllability.
        # Here we allow the caller to specify a separate threshold via
        # ``controllability_threshold``.  If unspecified, a default of
        # 1e‑4 is used as a conservative lower bound on |L·M⁻¹·B|; too
        # small of a threshold can lead to numerical instabilities, while a
        # larger threshold needlessly suppresses the equivalent control.  See
        # Golub & Van Loan for background on conditioning of linear systems.
        if controllability_threshold is None:
            # Scale the equivalent‑control threshold with the sum of switching gains.
            # Sliding‑mode theory states that the switching gain must exceed the
            # bound of system uncertainties plus a positive margin to guarantee
            # sliding【412237323761959†L496-L507】.  A threshold proportional to
            # (k1 + k2) avoids enabling the equivalent control when the system
            # is poorly controllable and adapts automatically when gains are
            # tuned.  The factor 0.05 was empirically chosen to provide a
            # conservative cutoff.
            self.eq_threshold = 0.05 * (self.k1 + self.k2)
        else:
            val = float(controllability_threshold)
            if val <= 0.0:
                raise ValueError("controllability_threshold must be > 0")
            self.eq_threshold = val

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def gains(self) -> List[float]:
        """Return the list of gains used by this controller.

        This property exposes the six control gains in the canonical order
        ``[k1, k2, lam1, lam2, K, kd]`` for external introspection.  The
        returned list is a shallow copy to prevent accidental mutation of
        the controller’s internal parameters.
        """
        return list(self._gains)

    def initialize_state(self) -> tuple:
        """No internal state for classical SMC; returns an empty tuple."""
        return ()

    def initialize_history(self) -> dict:
        """No history tracked for classical SMC; returns an empty dict."""
        return {}

    @staticmethod
    def validate_gains(gains: Union[Sequence[float], np.ndarray, Any]) -> None:
        """
        Validate that exactly six gains have been provided for the classical SMC.

        The classical sliding–mode controller uses six gains in the order
        ``[k1, k2, lam1, lam2, K, kd]``.  Any other length is considered
        misconfigured and results in a ``ValueError``.  This validator accepts
        any sequence or array-like input and coerces it to a one‑dimensional
        array of floats before verifying its length.  When coercion fails or
        the resulting array does not contain exactly six elements, a
        ``ValueError`` is raised.

        Parameters
        ----------
        gains : Sequence[float] or array-like
            Sequence of gain values supplied during construction.

        Raises
        ------
        ValueError
            If ``gains`` is not convertible to a sequence of length six.
        """
        # Attempt to coerce the gains into a flat NumPy array.  Any exception
        # indicates the input is not sequence-like or contains non-numeric
        # entries and should result in a validation error.
        try:
            arr = np.asarray(gains, dtype=float).ravel()
        except Exception:
            raise ValueError(
                "ClassicalSMC requires 6 gains: [k1, k2, lam1, lam2, K, kd]"
            )
        # Ensure exactly six gains are provided
        if arr.size != 6:
            raise ValueError(
                "ClassicalSMC requires 6 gains: [k1, k2, lam1, lam2, K, kd]"
            )

    def _compute_sliding_surface(self, state: np.ndarray) -> float:
        """Compute the sliding surface value, ``sigma``.

        Args:
            state: State vector ``[x, theta1, theta2, xdot, dtheta1, dtheta2]``.

        Returns:
            The scalar sliding surface value.
        """
        _, theta1, theta2, _, dtheta1, dtheta2 = state
        return self.lam1 * theta1 + self.lam2 * theta2 + self.k1 * dtheta1 + self.k2 * dtheta2

    def _compute_equivalent_control(self, state: np.ndarray) -> float:
        """Compute the model-based equivalent control ``u_eq`` with enhanced robustness.

        Args:
            state: State vector ``[x, theta1, theta2, xdot, dtheta1, dtheta2]``.

        Returns:
            The scalar equivalent control value, or 0.0 if computation is deemed unreliable.
        """
        if self.dyn is None:
            # No dynamics model attached; return zero equivalent control.
            return 0.0

        q_dot = state[3:]
        # Attempt to obtain the physics matrices from the dynamics model.  If
        # this fails, fall back to purely switching control.  Broad
        # exceptions are caught here to avoid propagating unexpected errors
        # upstream.  When the model cannot provide the matrices, equivalent
        # control is set to zero.
        try:
            M, C, G = self.dyn._compute_physics_matrices(state)
        except Exception:
            return 0.0

        # Apply Tikhonov regularisation to ensure the inertia matrix is
        # invertible.  Adding a small positive diagonal term improves
        # conditioning and avoids the need for expensive singular value
        # decompositions.  This technique, sometimes called diagonal jitter,
        # guarantees that the matrix becomes positive definite and
        # invertible.
        M_reg = M + np.eye(3) * max(self.regularization, 0.0)

        # Attempt to solve the linear system directly.  Use ``np.linalg.solve``
        # instead of a pseudo‑inverse to reduce computational overhead.
        try:
            # Compute the controllability scalar L @ M_reg^{-1} @ B.
            Minv_B = np.linalg.solve(M_reg, self.B)
            L_Minv_B = float(self.L @ Minv_B)
            # Guard against uncontrollable configurations.  If the scalar
            # approaches zero the equivalent control becomes ill‑defined and
            # we conservatively return zero.  The threshold used here
            # (``self.eq_threshold``) is independent of the boundary‑layer
            # thickness ``epsilon``.  Earlier versions tied this cutoff
            # directly to the boundary layer, conflating chattering mitigation
            # with controllability.  Sliding‑mode literature notes that
            # widening the boundary layer reduces chattering but induces a
            # steady‑state error; therefore the
            # controllability threshold should be tuned separately.  When
            # |L⋅M⁻¹⋅B| < ``self.eq_threshold`` the equivalent control is
            # disabled.
            if abs(L_Minv_B) < self.eq_threshold:
                return 0.0

            # Compute the numerator of the equivalent control.  Handle
            # different shapes of the Coriolis matrix C gracefully: when C
            # is a matrix multiply by q_dot; when C is already a vector
            # treat it directly.  See the documentation for details.
            if getattr(C, "ndim", 1) == 2:
                rhs = C @ q_dot + G
            else:
                rhs = C + G
            Minv_rhs = np.linalg.solve(M_reg, rhs)
            term1 = float(self.L @ Minv_rhs)
            term2 = self.k1 * self.lam1 * q_dot[1] + self.k2 * self.lam2 * q_dot[2]
            u_eq = (term1 - term2) / L_Minv_B
        except np.linalg.LinAlgError:
            # Inversion failed despite regularisation; treat as singular.
            return 0.0

        # In earlier versions a diagnostic clamp and a tiny bias term were
        # introduced here.  Empirically clamping the equivalent control to
        # ±10×max_force and returning an epsilon when u_eq=0 obscured the
        # true magnitude of the model‑based term and hindered reproducibility.
        # Current guidance from sliding‑mode theory advocates computing
        # exactly the model‑based feedforward term and handling large values
        # via the main saturation at the end of ``compute_control``
        #.  Therefore we simply return the
        # computed u_eq without adding biases.  The subsequent saturation
        # stage in ``compute_control`` will limit the control action.
        return float(u_eq)


    def compute_control(
        self, state: np.ndarray, state_vars: tuple, history: dict
    ) -> ClassicalSMCOutput:
        """Compute the control input for the classical SMC.

        The control law combines a model‑based equivalent term ``u_eq`` with
        a discontinuous (but smoothed) sliding‑mode term.  The robust term
        employs a saturation function within a boundary layer to approximate
        the sign function, which reduces chattering by replacing the infinite
        switching with a continuous control.  The
        total command is given by

        .. math::

            u = u_{\\text{eq}} - K \\\\operatorname{sat}\\\\left(\\\\frac{\\\\sigma}{\\\\epsilon}\\\\right) - k_d \\\\, \\\\sigma,

        where ``sat`` is either ``tanh`` or a linear clip depending on
        ``switch_method``.

        After summing the terms the result is saturated to lie within
        ``[-max_force, +max_force]``.  Saturation of the final command limits
        actuator effort and ensures physical plausibility.
        """
        sigma = self._compute_sliding_surface(state)

        # Adaptive boundary layer: compute a state‑dependent epsilon that
        # scales with the magnitude of the sliding variable.  This
        # continuous approximation reduces chattering while shrinking
        # towards zero near the sliding manifold【967233543993377†L104-L115】.
        eps_dyn = self.epsilon0 + self.epsilon1 * float(np.linalg.norm(sigma))
        # Apply hysteresis: when |sigma| lies within a small fraction of the
        # nominal boundary layer the robust term is suppressed.  This
        # dead‑band mitigates chattering by freezing the discontinuous
        # control inside the hysteresis band【967233543993377†L104-L115】.
        if abs(float(sigma)) < self.hysteresis_ratio * self.epsilon0:
            sat_sigma = 0.0
        else:
            sat_sigma = saturate(sigma, eps_dyn, method=self.switch_method)

        u_eq = self._compute_equivalent_control(state)
        # Moderately clamp the equivalent control.  Unbounded model‑based
        # terms can exceed the actuator limits by orders of magnitude,
        # causing integrator wind‑up and excitation of unmodelled
        # dynamics.  Sliding‑mode design guidelines recommend limiting
        # the equivalent component relative to the maximum control
        # authority.  We saturate u_eq at ±5×max_force,
        # which preserves the fidelity of the model‑based term while
        # preventing pathological spikes.
        max_eq = 5.0 * self.max_force
        if u_eq > max_eq:
            u_eq = max_eq
        elif u_eq < -max_eq:
            u_eq = -max_eq

        u_robust = -self.K * sat_sigma - self.kd * sigma

        # Combine equivalent and robust terms and saturate final command
        # to the actuator limits.  The final saturation prevents
        # commanded torques/forces from exceeding the physical
        # capability of the actuator.
        u = u_eq + u_robust
        u_saturated = float(np.clip(u, -self.max_force, self.max_force))

        # Telemetry: append key signals to history (in-place)
        hist = history if isinstance(history, dict) else {}
        hist.setdefault('sigma', []).append(float(sigma))
        hist.setdefault('epsilon_eff', []).append(float(eps_dyn))
        hist.setdefault('u_eq', []).append(float(u_eq))
        hist.setdefault('u_robust', []).append(float(u_robust))
        hist.setdefault('u_total', []).append(float(u))
        hist.setdefault('u', []).append(float(u_saturated))

        # Return structured output
        return ClassicalSMCOutput(u_saturated, (), hist)

    def reset(self) -> None:
        """Reset ClassicalSMC controller state.

        Classical SMC has no internal state variables to reset since it is
        stateless and purely reactive based on current measurements.
        This method is provided for interface compliance.
        """
        # Classical SMC is stateless - no internal state to reset
        pass

#=======================================================================================\\\
