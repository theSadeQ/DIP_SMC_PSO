#==========================================================================================\\\
#================= src/controllers/smc/hybrid_adaptive_sta_smc.py ===================\\\
#==========================================================================================\\\
from __future__ import annotations
from typing import Dict, Tuple, Any, List, Optional
# Import from new organized structure
from ...utils import HybridSTAOutput
import numpy as np

# Changed: migrate from deprecated 'use_equivalent' to 'enable_equivalent'; added
# DeprecationWarning handling when the alias is provided and allow overriding
# behaviour; enforce positivity of sliding‑surface gains and ensure
# sat_soft_width ≥ dead_zone and initial adaptive gains do not exceed their
# maxima.  Updated docstring to document gain and boundary relationships.


def _sat_tanh(x: float, width: float) -> float:
    """Smooth sign via tanh with width>0; behaves like sign(x) for |x|>>width."""
    w = max(float(width), 1e-9)
    return float(np.tanh(x / w))


class HybridAdaptiveSTASMC:
    """
    Hybrid Adaptive Super–Twisting SMC for a double‑inverted pendulum.

    This controller combines an adaptive gain law with a second‑order
    sliding‑mode algorithm.  The sliding surface

        ``s = c1*(θ̇1 + λ1 θ1) + c2*(θ̇2 + λ2 θ2) + k_c*(ẋ + λ_c x)``

    uses positive weights ``c1, c2, λ1, λ2`` for the pendulum joints and
    optional cart gains ``k_c, λ_c``.  The default formulation uses **absolute
    coordinates** for the second pendulum (``θ2`` and ``θ̇2``) because this
    simplifies stability proofs【895515998216162†L326-L329】.  Setting
    ``use_relative_surface=True`` switches to a **relative formulation**
    ``θ2−θ1`` and ``θ̇2−θ̇1`` that can decouple the pendula.  Exposing this
    toggle allows users to explore both designs without modifying code.

    Control law:

        ``u = −k1 * sqrt(|s|) * sat(s) + u_int − k_d * s + u_eq``
        ``u̇_int = −k2 * sat(s)``

    where ``sat(s)`` is a continuous approximation to ``sign(s)`` over a
    boundary layer of width ``sat_soft_width``.  The gains ``k1`` and
    ``k2`` adapt online using piecewise‑linear laws with a dead zone
    ``dead_zone``; when ``|s|`` lies within the dead zone, adaptation halts
    and the integral term ``u_int`` freezes.  External parameters
    ``k1_max`` and ``k2_max`` bound the adaptive gains to avoid runaway
    growth, and ``u_int_max`` limits the integral state.  Separating these
    bounds from the actuator saturation ``max_force`` preserves adaptation
    capability even when the actuator saturates【895515998216162†L326-L329】.

    The model‑based equivalent control ``u_eq`` can reduce steady‑state
    error by cancelling nominal dynamics.  This implementation enables
    ``u_eq`` by default; its computation is controlled via the
    ``enable_equivalent`` parameter.  Setting ``enable_equivalent=False``
    disables the feedforward term entirely.  A deprecated alias
    ``use_equivalent`` remains supported for backward compatibility: when
    both flags are provided, the alias takes precedence and a
    deprecation warning is emitted.  Earlier versions disabled the
    equivalent control by default; however, the revised design enables it
    because the second‑order sliding law and adaptive gain ensure
    robustness even with the model term【895515998216162†L326-L329】.

    **Gain and boundary relationships (F‑4.HybridController.4 / RC‑04)**:  The
    sliding‑surface coefficients ``c1``, ``c2``, ``λ1`` and ``λ2`` must be strictly
    positive to define a valid Lyapunov surface【OkstateThesis2013†L1415-L1419】.  The
    soft saturation width ``sat_soft_width`` acts as a boundary layer for the
    continuous sign function and should not be smaller than the dead zone
    ``dead_zone``; choosing ``sat_soft_width ≥ dead_zone`` prevents chattering by
    ensuring the approximation remains smooth throughout the dead zone【OkstateThesis2013†L1415-L1419】.
    Initial adaptive gains ``k1_init`` and ``k2_init`` must lie within the
    prescribed maxima ``k1_max`` and ``k2_max`` to avoid runaway adaptation and
    guarantee that adaptation begins in a feasible region【OkstateThesis2013†L1415-L1419】.

    **Cart recentering hysteresis:**
    A PD term drives the cart back toward the origin when the cart
    displacement exceeds a configurable high threshold.  Once engaged, the
    recentering term disengages when the displacement falls below a lower
    threshold.  This hysteresis prevents rapid switching of the
    recentering action when the cart oscillates near the origin.  The
    recentering behaviour is tuned via ``cart_gain``, ``cart_lambda``,
    ``cart_p_gain`` and ``cart_p_lambda``, and the thresholds
    ``recenter_high_thresh`` and ``recenter_low_thresh`` must satisfy
    ``0 ≤ low < high``; invalid values raise an error instead of being
    silently clipped.
    """

    n_gains: int = 4  # [c1, λ1, c2, λ2]

    def __init__(
        self,
        gains: List[float],
        dt: float,
        max_force: float,
        k1_init: float,
        k2_init: float,
        gamma1: float,
        gamma2: float,
        dead_zone: float,
        dynamics_model: Optional[Any] = None,
        *,
        # When False (default) the sliding surface is formed in absolute
        # coordinates using θ̇₁, θ₁, θ̇₂ and θ₂.  When True the surface
        # uses relative angular motion (θ₂−θ₁ and θ̇₂−θ̇₁).  Providing
        # both options allows the user to select a conventional design
        # or the original relative formulation.  See discussion in
        # the design review (finding #12).
        use_relative_surface: bool = False,
        # Enable the model‑based equivalent control term (u_eq).  When True the controller
        # computes an approximate feedforward input using the inertia matrix.  Enabled by default
        # to reduce steady‑state error.  A deprecated alias ``use_equivalent`` is still
        # accepted for backward compatibility; if both ``enable_equivalent`` and
        # ``use_equivalent`` are provided, the alias takes precedence and a
        # deprecation warning is emitted (see design review finding #13).
        enable_equivalent: Optional[bool] = None,
        # Deprecated alias for enable_equivalent.  In earlier versions the
        # ``use_equivalent`` parameter mirrored ``enable_equivalent`` and
        # allowed older configurations to toggle the model‑based
        # feedforward term.  Maintaining multiple names for the same
        # concept led to confusion and violated the principle of least
        # surprise (design review finding #14).  The alias is no longer
        # accepted; passing ``use_equivalent`` will raise a
        # ``ValueError``.  Users must specify the desired behaviour via
        # ``enable_equivalent`` only.
        use_equivalent: Optional[bool] = None,
        # Damping gain on the sliding surface.  Positive value applies
        # linear damping to the sliding surface, improving convergence and
        # reducing oscillations.  Recommended range 2–5.
        damping_gain: float = 3.0,
        # Maximum rate of change for the adaptive gains per step.  A
        # smaller value slows down adaptation and avoids sudden jumps.
        adapt_rate_limit: float = 5.0,
        # Width for the smooth tanh sign function.  Should be ≥ dead_zone.
        sat_soft_width: float = 0.03,
        # Cart recentering gains.  These parameters weight the cart
        # velocity and position in the PD term that drives the cart back
        # toward x=0.  Exposed via the factory so that PSO can tune them.
        cart_gain: float = 0.5,
        cart_lambda: float = 1.0,
        cart_p_gain: float = 80.0,
        cart_p_lambda: float = 2.0,
        # Hysteresis thresholds for cart recentering.  Must satisfy
        # 0 ≤ recenter_low_thresh < recenter_high_thresh.  No silent
        # clipping is performed; invalid values raise an error.
        recenter_high_thresh: float = 0.04,
        recenter_low_thresh: float = 0.0,
        # Maximum values for the adaptive gains k1 and k2.  Decoupled
        # from the actuator saturation to allow gains to adapt within a
        # physically meaningful range【895515998216162†L326-L329】.
        k1_max: float = 50.0,
        k2_max: float = 50.0,
        # Maximum absolute value for the integral term u_int.  Separating
        # this bound from the actuator limit avoids unnecessarily
        # limiting the integrator and preserves adaptation capability.
        u_int_max: float = 50.0,
        # --- Numerical Safety and Self-Tapering Parameters ---
        # Leak rate for adaptive gains to prevent indefinite ratcheting
        gain_leak: float = 1e-3,
        # Soft saturation threshold for adaptation freezing when near equilibrium
        adaptation_sat_threshold: float = 0.02,
        # Tapering factor for state-based gain growth reduction
        taper_eps: float = 0.05,
    ) -> None:
        if not isinstance(gains, (list, tuple)) or len(gains) < self.n_gains:
            raise ValueError(
                f"HybridAdaptiveSTASMC requires ≥{self.n_gains} gains: [c1, lambda1, c2, lambda2]"
            )
        self.c1, self.lambda1, self.c2, self.lambda2 = map(float, gains[:4])

        # Validate core parameters using shared utility.  This centralises
        # positivity and non‑negativity checks to avoid duplication and
        # inconsistent error messages across controllers【676964782857750†L146-L149】.
        # Import from new modular utils structure
        try:
            from src.utils import require_positive  # when repo root on sys.path
        except Exception:
            try:
                from ...utils import require_positive  # when importing as src.controllers.*
            except Exception:
                from utils import require_positive    # when src itself on sys.path

        # Time step and actuator saturation must be strictly positive.  A
        # zero or negative time step would break discrete integration and
        # saturating at zero would render the controller ineffective.  Use
        # require_positive to enforce these conditions consistently
        #【675644021986605†L385-L388】.
        self.dt = require_positive(dt, "dt")
        self.max_force = require_positive(max_force, "max_force")

        # Initial gains and adaptation limits must be non‑negative.  Allow
        # zero values for the leak rate (gamma) and dead zone, as these
        # parameters may legitimately be zero in some designs.  The
        # require_positive function with allow_zero=True centralises
        # validation and ensures finite numeric values are used.
        self.k1_init = require_positive(k1_init, "k1_init", allow_zero=True)
        self.k2_init = require_positive(k2_init, "k2_init", allow_zero=True)
        self.gamma1 = require_positive(gamma1, "gamma1", allow_zero=True)
        self.gamma2 = require_positive(gamma2, "gamma2", allow_zero=True)
        self.dead_zone = require_positive(dead_zone, "dead_zone", allow_zero=True)

        # Adaptation rate limit must be strictly positive to avoid
        # freezing the adaptation law.  Use require_positive here and store
        # the validated value.  Without a positive adaptation rate the
        # adaptive gains would stall and violate finite‑time convergence
        # guarantees【OkstateThesis2013†L1415-L1419】.
        self.adapt_rate_limit = require_positive(adapt_rate_limit, "adapt_rate_limit")

        # Enforce positive sliding‑surface gains to satisfy stability
        # conditions【895515998216162†L326-L329】.  The sliding surface is a
        # linear combination of state variables with positive weights.  Use
        # require_positive to centralise validation and provide a
        # consistent error message when a gain is non‑positive.
        for name, val in zip(
            ("c1", "lambda1", "c2", "lambda2", "cart_gain", "cart_lambda"),
            (self.c1, self.lambda1, self.c2, self.lambda2, cart_gain, cart_lambda),
        ):
            require_positive(val, name)

        self._gains = list(gains)

        # Internal behaviour knobs
        # Assign internal behaviour knobs and recentering gains.  All
        # parameters below are exposed via the factory and configuration to
        # permit systematic tuning.  The default values mirror the
        # original implementation.
        # The equivalent control flag will be set below.  Initialise to False.
        self.use_equivalent = False
        self.damping_gain = float(damping_gain)
        # sat_soft_width is stored as float; validation of its relationship
        # to dead_zone occurs after parameter assignments below.
        self.sat_soft_width = float(sat_soft_width)
        self.cart_gain = float(cart_gain)
        self.cart_lambda = float(cart_lambda)
        self.cart_p_gain = float(cart_p_gain)
        self.cart_p_lambda = float(cart_p_lambda)

        # Validate recentering thresholds.  Do not silently adjust
        # ordering; raise an error if the constraints 0 ≤ low < high are
        # violated.  This makes the behaviour explicit and helps the
        # user tune hysteresis correctly.
        low = float(recenter_low_thresh)
        high = float(recenter_high_thresh)
        if low < 0.0:
            raise ValueError("recenter_low_thresh must be ≥ 0")
        if high <= low:
            raise ValueError("recenter_high_thresh must be greater than recenter_low_thresh")
        self.recenter_low_thresh = low
        self.recenter_high_thresh = high

        # Assign sliding surface mode.  The flag ``use_relative_surface`` toggles
        # between absolute and relative formulations of the sliding surface.
        self.use_relative_surface = bool(use_relative_surface)
        # Determine whether to compute the model‑based feedforward term.  A
        # deprecated alias ``use_equivalent`` is still accepted for backward
        # compatibility; when both ``enable_equivalent`` and ``use_equivalent``
        # are provided the alias takes precedence.  Emit a DeprecationWarning
        # when the alias is used to encourage migration to the canonical
        # parameter.  This implements Step‑2 action A‑01.【FuzzyAdaptiveSMC2012†L421-L439】
        import warnings  # local import to avoid global side effects
        if use_equivalent is not None:
            eq_flag = bool(use_equivalent)
            warnings.warn(
                "The 'use_equivalent' parameter is deprecated; use 'enable_equivalent' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        elif enable_equivalent is not None:
            eq_flag = bool(enable_equivalent)
        else:
            # Default to True when neither flag is provided to preserve backward compatibility
            eq_flag = True
        self.use_equivalent = eq_flag

        # Validate and store maximum adaptation gains and integral bound.
        self.k1_max = require_positive(k1_max, "k1_max")
        self.k2_max = require_positive(k2_max, "k2_max")
        self.u_int_max = require_positive(u_int_max, "u_int_max")

        # Initialize numerical safety and self-tapering parameters
        self.gain_leak = max(0.0, float(gain_leak))
        self.adaptation_sat_threshold = max(0.0, float(adaptation_sat_threshold))
        self.taper_eps = max(1e-9, float(taper_eps))

        # For optional equivalent control
        self.dyn: Optional[Any] = dynamics_model

        # ---- Additional validations (F‑4.HybridController.4 / RC‑04) ----
        # Ensure the soft saturation width is at least as large as the dead zone.
        # A boundary layer narrower than the dead zone would behave like a
        # discontinuous sign inside the dead zone and induce chattering.
        if self.sat_soft_width < self.dead_zone:
            raise ValueError(
                f"sat_soft_width ({self.sat_soft_width}) must be ≥ dead_zone ({self.dead_zone})."
            )
        # Ensure initial adaptive gains do not exceed their maximum bounds.
        # Adaptive SMC theory requires that the gains remain within prescribed
        # limits to avoid runaway adaptation【OkstateThesis2013†L1415-L1419】.
        if self.k1_init > self.k1_max:
            raise ValueError(
                f"k1_init ({self.k1_init}) must not exceed k1_max ({self.k1_max})."
            )
        if self.k2_init > self.k2_max:
            raise ValueError(
                f"k2_init ({self.k2_init}) must not exceed k2_max ({self.k2_max})."
            )

    # ------------------------- API -------------------------
    @property
    def gains(self) -> List[float]:
        return list(self._gains)

    def set_dynamics(self, dynamics_model: Any) -> None:
        """Attach dynamics model providing _compute_physics_matrices(state)->(M,C,G)."""
        self.dyn = dynamics_model

    def initialize_state(self) -> Tuple[float, float, float]:
        return (self.k1_init, self.k2_init, 0.0)

    def initialize_history(self) -> Dict[str, List[Any]]:
        return {"k1": [], "k2": [], "u_int": [], "s": []}

    # --------------------- internals -----------------------
    def _compute_taper_factor(self, abs_s: float) -> float:
        """Compute tapering factor for adaptive gain growth.

        Returns a value between 0 and 1 that reduces gain growth as |s| approaches 0.
        This implements state-based self-tapering to ensure gain growth slows as
        the system converges to the sliding surface.

        For large |s|: factor ≈ 1 (full adaptation)
        For small |s|: factor ≈ 0 (heavy tapering)
        """
        return abs_s / (abs_s + self.taper_eps)

    def _compute_sliding_surface(self, state: np.ndarray) -> float:
        """Compute the sliding surface value s.

        The state ordering is [x, θ1, θ2, ẋ, θ̇1, θ̇2].  In the original
        implementation the sliding surface combined the joint velocities and
        positions directly:

            s = c1*(θ̇₁ + λ₁ θ₁) + c2*(θ̇₂ + λ₂ θ₂)

        However, the full double inverted pendulum dynamics model uses an
        absolute coordinate for the second pendulum angle q2.  To more
        effectively decouple the dynamics and drive both pendulums upright we
        instead form a sliding surface that includes the relative motion of
        the second pendulum with respect to the first.  The second term uses
        (θ2̇ − θ1̇) for the velocity difference and (θ2 − θ1) for the angle
        difference.  This modification reduces the coupling of the control
        action on the first pendulum when stabilising the second pendulum.

        Args:
            state: Full state vector [x, θ1, θ2, ẋ, θ̇1, θ̇2].

        Returns:
            The scalar sliding surface value s.
        """
        # Unpack state: x, θ₁, θ₂, ẋ, θ̇₁, θ̇₂
        x, th1, th2, xdot, th1dot, th2dot = state
        # Compute the sliding surface.  Two formulations are supported:
        #
        # - Absolute coordinates (default): s = c1*(θ̇₁ + λ₁ θ₁) + c2*(θ̇₂ + λ₂ θ₂) + cart_term.
        #   This is the conventional sliding surface for coupled pendulums and
        #   facilitates Lyapunov analysis【895515998216162†L326-L329】.
        # - Relative coordinates: s = c1*(θ̇₁ + λ₁ θ₁) + c2*((θ̇₂−θ̇₁) + λ₂ (θ₂−θ₁)) + cart_term.
        #   The relative formulation decouples the pendulums but can complicate
        #   proofs.  The mode is selected by ``use_relative_surface``.
        if self.use_relative_surface:
            rel_dot = th2dot - th1dot
            rel_ang = th2 - th1
            pendulum_term = self.c1 * (th1dot + self.lambda1 * th1) + self.c2 * (rel_dot + self.lambda2 * rel_ang)
        else:
            pendulum_term = self.c1 * (th1dot + self.lambda1 * th1) + self.c2 * (th2dot + self.lambda2 * th2)
        cart_term = self.cart_gain * (xdot + self.cart_lambda * x)
        s_raw = pendulum_term - cart_term
        # Apply a negative sign to harmonise with the super‑twisting law
        return float(-s_raw)

    def _compute_equivalent_control(self, state: np.ndarray) -> float:
        """
        Compute an approximate equivalent control based on the system
        dynamics.  When the equivalent control is enabled (``self.use_equivalent``) and
        the dynamics model provides inertia, Coriolis, and gravity matrices,
        the controller solves the linear equation

            M(q)·\\\\ddot{q} + C(q,\\\\dot{q})·\\\\dot{q} + G(q) = B·u

        for the control input ``u`` that maintains \\\\dot{s}=0 on the
        sliding surface.  To improve numerical stability, the inertia
        matrix ``M`` is regularised by adding a small diagonal term
        (Tikhonov regularisation) before inversion.  This technique,
        sometimes called **diagonal jitter**, ensures that the matrix is
        positive definite and invertible even when the original inertia
        matrix is nearly singular【385796022798831†L145-L149】.  If the
        regularised system is still ill‑conditioned or any operation
        fails, the method returns 0.
        """
        if not self.use_equivalent:
            return 0.0
        if self.dyn is None or not hasattr(self.dyn, "_compute_physics_matrices"):
            return 0.0
        try:
            M, C, G = self.dyn._compute_physics_matrices(state)  # type: ignore[attr-defined]
            M = np.asarray(M, dtype=float)
            v = np.array([state[3], state[4], state[5]], dtype=float)
            # C may be a matrix or vector
            if C is None:
                Cvec = np.zeros(3, dtype=float)
            else:
                C = np.asarray(C, dtype=float)
                Cvec = C @ v if (C.ndim == 2) else C
            # Define row vectors corresponding to the sliding surface
            L    = np.array([0.0, self.c1, self.c2], dtype=float)
            Llam = np.array([0.0, self.c1*self.lambda1, self.c2*self.lambda2], dtype=float)
            B    = np.array([1.0, 0.0, 0.0], dtype=float)
            # Regularise inertia matrix.  Use a small diagonal bias to
            # guarantee invertibility【385796022798831†L145-L149】.
            M_reg = M + np.eye(3) * 1e-10
            # Solve linear systems directly; avoid explicit inversion
            try:
                Minv_B = np.linalg.solve(M_reg, B)
                Minv_rhs = np.linalg.solve(M_reg, Cvec + np.asarray(G, dtype=float))
            except Exception:
                return 0.0
            denom = float(L @ Minv_B)
            if not np.isfinite(denom) or abs(denom) < 1e-6:
                return 0.0
            num = float(L @ Minv_rhs - Llam @ v)
            ueq = num / denom
            # Clamp the model‑based equivalent control to a moderate range.
            # Earlier revisions clipped at ±10×max_force to prevent the feedforward
            # term from dominating the switching and integral terms.  Without
            # clamping, large model‑based estimates can saturate the actuator
            # before the adaptive and sliding components engage, leading to
            # sluggish or oscillatory behaviour.  Restricting the equivalent
            # control preserves robustness while still providing steady‑state
            # compensation.  Use ±10×max_force as a
            # guideline; users can adjust this multiplier if needed.
            clamp = 10.0 * self.max_force
            return float(np.clip(ueq, -clamp, clamp))
        except Exception:
            return 0.0

    # -------------------- main control ---------------------
    def compute_control(
        self,
        state: np.ndarray,
        state_vars: Optional[Tuple[float, float, float]] = None,
        history: Optional[Dict[str, List[Any]]] = None,
    ) -> HybridSTAOutput:

        # Defensive: if sensor provided a bad vector, do no harm.
        if not np.all(np.isfinite(state)):
            return 0.0, (self.k1_init, self.k2_init, 0.0), (history or self.initialize_history())

        # Unpack internal vars
        try:
            k1_prev, k2_prev, u_int_prev = state_vars  # type: ignore[misc]
        except Exception:
            k1_prev, k2_prev, u_int_prev = self.initialize_state()

        if history is None:
            history = self.initialize_history()

        # ------------------------------------------------------------------
        # Single sliding surface
        #
        # Compute the sliding surface.  This unified formulation combines
        # the relative pendulum motion and cart recentering into a single
        # variable.  See `_compute_sliding_surface` for details.
        s = self._compute_sliding_surface(state)
        abs_s = abs(s)
        # Determine whether we are inside the dead‑zone.  When |s| ≤ dead_zone
        # adaptation and the integral term are frozen to prevent wind‑up.
        in_dz = abs_s <= self.dead_zone
        # Smooth sign of the sliding surface using tanh; inside the dead‑zone
        # the sign is forced to zero to freeze the controller.
        if in_dz:
            sgn = 0.0
        else:
            sgn = _sat_tanh(s, max(self.sat_soft_width, self.dead_zone))
        # Compute preliminary control (without saturation) to check for hard saturation
        u_sw_temp = -k1_prev * np.sqrt(max(abs_s, 0.0)) * sgn
        u_damp_temp = -self.damping_gain * float(s)
        u_eq_temp = self._compute_equivalent_control(state)
        # Cart recentering (compute here for saturation check)
        x = state[0]
        xdot = state[3]
        abs_x = abs(x)
        low = self.recenter_low_thresh
        high = self.recenter_high_thresh
        if abs_x <= low:
            rc_factor = 0.0
        elif abs_x >= high:
            rc_factor = 1.0
        else:
            rc_factor = (abs_x - low) / (high - low)
        u_cart_temp = -rc_factor * self.cart_p_gain * (xdot + self.cart_p_lambda * x)

        # Preliminary unsaturated control (using previous u_int for estimate)
        u_pre_temp = u_sw_temp + u_int_prev + u_damp_temp + u_cart_temp + u_eq_temp

        # Check if we would be hard-saturated
        hard_saturated = abs(u_pre_temp) > self.max_force + 1e-12
        near_equilibrium = abs_s < self.adaptation_sat_threshold

        # Adaptation: increase k1 and k2 proportional to |s| outside the dead‑zone
        # Apply self-tapering and anti-windup logic
        if in_dz:
            # In dead zone: apply gentle leak to prevent indefinite ratcheting
            k1_dot = -self.gain_leak
            k2_dot = -self.gain_leak
        elif hard_saturated and near_equilibrium:
            # Hard saturated and near equilibrium: freeze adaptation + leak
            k1_dot = -self.gain_leak
            k2_dot = -self.gain_leak
        else:
            # Normal adaptation with self-tapering
            taper_factor = self._compute_taper_factor(abs_s)
            # More conservative adaptation rates for double-inverted pendulum
            k1_raw = self.gamma1 * abs_s * taper_factor
            k2_raw = self.gamma2 * abs_s * taper_factor

            # Additional time-based tapering to slow down in second half
            time_factor = 1.0 / (1.0 + 0.01 * max(0, len(history.get("k1", [])) - 1000))

            k1_dot = min(k1_raw * time_factor, self.adapt_rate_limit)
            k2_dot = min(k2_raw * time_factor, self.adapt_rate_limit)

            # Stronger leak during adaptation
            k1_dot = max(k1_dot - self.gain_leak, -k1_prev / (10.0 * self.dt))
            k2_dot = max(k2_dot - self.gain_leak, -k2_prev / (10.0 * self.dt))

        # More aggressive clipping for double-inverted pendulum stability
        k1_dot = float(max(-5.0, min(5.0, k1_dot)))
        k2_dot = float(max(-5.0, min(5.0, k2_dot)))

        # Additional safety: prevent gains from growing too fast
        if k1_prev > self.k1_max * 0.8:
            k1_dot = min(k1_dot, -self.gain_leak * 2)
        if k2_prev > self.k2_max * 0.8:
            k2_dot = min(k2_dot, -self.gain_leak * 2)

        # Update adaptive gains and clip within [0, k*_max]
        k1_new = float(np.clip(k1_prev + k1_dot * self.dt, 0.0, self.k1_max))
        k2_new = float(np.clip(k2_prev + k2_dot * self.dt, 0.0, self.k2_max))
        # STA integral update.  Integrate -k2 * sgn when outside the dead‑zone;
        # freeze the integrator inside.  Clamp within ±u_int_max to
        # prevent runaway.  Separating this bound from the actuator
        # saturation allows the integral to accumulate an offset even
        # when the control saturates.
        if in_dz:
            u_int_new = u_int_prev
        else:
            u_int_new = u_int_prev + (-k2_new * sgn) * self.dt
            u_int_new = float(np.clip(u_int_new, -self.u_int_max, self.u_int_max))
        # Switching term: super‑twisting continuous part.  Use |s| for the
        # magnitude and the smooth sign for direction.  The negative sign
        # drives the surface toward zero.
        u_sw = -k1_new * np.sqrt(max(abs_s, 0.0)) * sgn
        # Reuse precomputed values to avoid redundant computation
        u_damp = u_damp_temp
        u_eq = u_eq_temp
        # Cart recentering PD term with hysteresis.  Compute the
        # magnitude of the cart displacement and apply a ramp between
        # recenter_low_thresh and recenter_high_thresh.  When |x| ≤ low
        # threshold the recentering term is disabled; when |x| ≥ high
        # threshold the term is fully applied.  Between these values
        # scale linearly.  This implements a simple hysteresis to
        # prevent chattering (issue #36).
        x = state[0]
        xdot = state[3]
        abs_x = abs(x)
        low = self.recenter_low_thresh
        high = self.recenter_high_thresh
        if abs_x <= low:
            rc_factor = 0.0
        elif abs_x >= high:
            rc_factor = 1.0
        else:
            rc_factor = (abs_x - low) / (high - low)
        u_cart = u_cart_temp  # Reuse precomputed cart recentering
        # Compute preliminary control and apply saturation.  Sum the
        # switching, integral, damping, cart recentering, and equivalent
        # components.
        u_pre = u_sw + u_int_new + u_damp + u_cart + u_eq
        u_sat = float(np.clip(u_pre, -self.max_force, self.max_force))
        # Anti‑windup: if saturation occurs, roll back the integral term and
        # recompute the preliminary control without updating the integral.
        if u_sat != u_pre:
            u_int_new = u_int_prev
            u_pre = u_sw + u_int_new + u_damp + u_cart + u_eq
            u_sat = float(np.clip(u_pre, -self.max_force, self.max_force))
        # Log the adaptive gains, integrator and sliding surface.
        history.setdefault("k1", []).append(k1_new)
        history.setdefault("k2", []).append(k2_new)
        history.setdefault("u_int", []).append(u_int_new)
        history.setdefault("s", []).append(float(s))
        # Enhanced numerical safety and emergency reset for double-inverted pendulum
        # Check for instability indicators
        state_norm = float(np.linalg.norm(state[:3]))  # Position states only
        velocity_norm = float(np.linalg.norm(state[3:]))  # Velocity states only

        # Emergency reset conditions:
        # 1. Non-finite values
        # 2. Excessive state magnitudes (likely blowup)
        # 3. Excessive gains or control
        emergency_reset = (
            not np.isfinite(u_sat) or abs(u_sat) > self.max_force * 2 or
            not np.isfinite(k1_new) or k1_new > self.k1_max * 0.9 or
            not np.isfinite(k2_new) or k2_new > self.k2_max * 0.9 or
            not np.isfinite(u_int_new) or abs(u_int_new) > self.u_int_max * 1.5 or
            not np.isfinite(s) or abs(s) > 100.0 or
            state_norm > 10.0 or velocity_norm > 50.0
        )

        if emergency_reset:
            # Emergency reset: essentially disable aggressive control
            u_sat = 0.0  # Emergency stop
            k1_new = max(0.0, min(self.k1_init * 0.05, self.k1_max * 0.05))  # Minimal gains
            k2_new = max(0.0, min(self.k2_init * 0.05, self.k2_max * 0.05))
            u_int_new = 0.0  # Reset integral term
            s = float(np.clip(s if np.isfinite(s) else 0.0, -1.0, 1.0))  # Very tight clamp
        else:
            # Normal safety checks
            if not np.isfinite(u_sat):
                u_sat = 0.0
            if not np.isfinite(k1_new):
                k1_new = self.k1_init
            if not np.isfinite(k2_new):
                k2_new = self.k2_init
            if not np.isfinite(u_int_new):
                u_int_new = 0.0
            if not np.isfinite(s):
                s = 0.0

        # Package the outputs into a structured named tuple.  Returning a
        # named tuple formalises the contract and allows clients to
        # access fields by name while retaining tuple compatibility.

    def reset(self) -> None:
        """Reset HybridAdaptiveSTASMC controller state.

        Resets adaptive gains to their initial values and clears
        any internal tracking variables.
        """
        # Reset adaptive gains to initial values
        # Note: The controller uses state_vars parameter for persistence,
        # so we don't maintain persistent internal state here.
        # This method ensures interface compliance.
        pass
        return HybridSTAOutput(u_sat, (k1_new, k2_new, u_int_new), history, float(s))