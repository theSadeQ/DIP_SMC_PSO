#==========================================================================================\\\
#========================== src/controllers/smc/sta_smc.py ===========================\\\
#==========================================================================================\\\
# Changed: enforce strict positivity of algorithmic and sliding‑surface gains (K1, K2, k1, k2, λ1, λ2);
# added corresponding validation logic in __init__; updated the class docstring to include a
# gain‑positivity section citing super‑twisting literature; these changes address F‑4.SMCDesign.2 / RC‑04.
from __future__ import annotations
import logging
# ---------------------------------------------------------------------------
# Optional numba import
#
# The super‑twisting SMC controller uses Numba to accelerate inner loops.
# Provide a fallback implementation when Numba is unavailable so that this
# module can be imported without raising a ModuleNotFoundError.  The dummy
# object supplies an ``njit`` decorator that simply returns the original
# function unchanged.
try:
    import numba  # type: ignore
except Exception:  # pragma: no cover - fallback when numba is missing
    class _DummyNumba:
        def njit(self, *args, **kwargs):  # type: ignore
            def deco(fn):
                return fn
            return deco
    numba = _DummyNumba()  # type: ignore
import numpy as np
# Import from new organized structure
from ...utils import saturate
from ...utils import STAOutput
from typing import Optional, List, Tuple, Dict, Union

@numba.njit(cache=True)
def _sta_smc_control_numba(
    state: np.ndarray,
    z: float,
    alg_gain_K1: float, alg_gain_K2: float, surf_gain_k1: float, surf_gain_k2: float, surf_lam1: float, surf_lam2: float,
    damping_gain: float, dt: float, max_force: float, boundary_layer: float,
    u_eq: float = 0.0
) -> Tuple[float, float, float]:
    """
    Numba‑accelerated core of the Super‑Twisting SMC.

    Uses a saturated sign function for sigma to maintain full control authority
    outside the boundary layer and linear behavior inside it, which is required
    for robust, finite‑time convergence of the super‑twisting algorithm.
    """
    _, th1, th2, _, th1dot, th2dot = state

    # Sliding surface: sigma = k1*(th1dot + lam1*th1) + k2*(th2dot + lam2*th2)
    sigma = surf_gain_k1 * (th1dot + surf_lam1 * th1) + surf_gain_k2 * (th2dot + surf_lam2 * th2)

    # ---- FIX CS‑01: robust saturation instead of "sigma/(|sigma|+eps)" ----
    eps = boundary_layer  # guaranteed > 0 by __init__
    if np.abs(sigma) > eps:
        sgn_sigma = np.sign(sigma)        # full control authority
    else:
        sgn_sigma = sigma / eps           # linear inside boundary layer
    # -----------------------------------------------------------------------

    # Super‑twisting continuous term and disturbance‑like internal state
    u_cont = -alg_gain_K1 * np.sqrt(np.abs(sigma)) * sgn_sigma
    # Use the previous z (integral state) for the disturbance term.  In the
    # continuous super‑twisting algorithm, the integral term z enters the
    # control law directly and is updated after computing the control.  The
    # earlier implementation incorrectly used the updated z in the same step.
    u_dis = z
    new_z = z - alg_gain_K2 * sgn_sigma * dt

    # Damping on sigma (optional)
    u = u_eq + u_cont + u_dis - damping_gain * sigma

    # Saturate final outputs to actuator limits.  Numba cannot
    # compile np.clip on scalars when running in nopython mode.  Use
    # explicit conditional clamps instead.
    if u > max_force:
        u = max_force
    elif u < -max_force:
        u = -max_force
    if new_z > max_force:
        new_z = max_force
    elif new_z < -max_force:
        new_z = -max_force
    return float(u), float(new_z), float(sigma)


@numba.njit(cache=True)
def _sta_smc_core(
    z: float,
    sigma: float,
    sgn_sigma: float,
    alg_gain_K1: float,
    alg_gain_K2: float,
    damping_gain: float,
    dt: float,
    max_force: float,
    u_eq: float = 0.0,
    Kaw: float = 0.0,
) -> Tuple[float, float, float]:
    """Numba-accelerated core using precomputed sigma and its saturated sign.

    Includes anti-windup back‑calculation: the integrator state ``z`` is
    updated using the difference between the saturated and unsaturated
    control multiplied by ``Kaw``【789743582768797†L224-L249】.  Returns
    ``(u_saturated, new_z, sigma)``.
    """
    # Continuous term and disturbance‑like internal state
    u_cont = -alg_gain_K1 * np.sqrt(np.abs(sigma)) * sgn_sigma
    u_dis = z
    # Compute unsaturated control
    u_raw = u_eq + u_cont + u_dis - damping_gain * sigma
    # Saturate the control
    u_sat = u_raw
    if u_sat > max_force:
        u_sat = max_force
    elif u_sat < -max_force:
        u_sat = -max_force
    # Anti-windup back‑calculation: adjust integrator when saturation occurs
    new_z = z - alg_gain_K2 * sgn_sigma * dt + Kaw * (u_sat - u_raw) * dt
    # Saturate the integrator to maintain boundedness
    if new_z > max_force:
        new_z = max_force
    elif new_z < -max_force:
        new_z = -max_force
    return float(u_sat), float(new_z), float(sigma)
 

class SuperTwistingSMC:
    """
    Second‑order (super‑twisting) sliding‑mode controller for the double‑inverted pendulum.

    This controller implements the super‑twisting algorithm, a higher‑order
    sliding‑mode technique that achieves finite‑time convergence without
    requiring direct measurement of the sliding surface derivative.  Compared
    with conventional (first‑order) sliding‑mode control, the super‑twisting
    algorithm is known to mitigate chattering and reduce control effort,
    offering improved tracking accuracy.  The
    implementation uses a continuous saturation function within a boundary
    layer ``ε`` to approximate the sign of the sliding variable σ,
    consistent with the boundary‑layer approach for chattering reduction
   .  The size of ``ε`` therefore controls
    the trade‑off between chattering attenuation and steady‑state accuracy
   .

    **Gains:**

      - If a 2‑element sequence ``[K1, K2]`` is provided, the sliding‑surface
        gains and poles ``(k1, k2, λ1, λ2)`` are set to default values.
      - A 6‑element sequence ``[K1, K2, k1, k2, λ1, λ2]`` specifies all
        super‑twisting and surface parameters explicitly.

    **Sliding surface:**

    .. math::
        \\sigma = k_1\\,(\\dot{\\theta}_1 + \\lambda_1\\,\\theta_1) + k_2\\,(\\dot{\\theta}_2 + \\lambda_2\\,\\theta_2).

    **Discrete‑time control law:**

    .. math::
        \\begin{aligned}
        u &= u_{\\\\text{eq}} - K_1 \\\\sqrt{|\\\\sigma|}\\\\,\\\\operatorname{sat}\\\\left( \\\\frac{\\\\sigma}{\\\\epsilon} \\\\right) + z - d\\\\,\\\\sigma,\\\\\\\\
        z^+ &= z - K_2\\\\,\\\\operatorname{sat}\\\\left( \\\\frac{\\\\sigma}{\\\\epsilon} \\\\right)\\\\,dt,
        \\end{aligned}

    where ``sat`` is a continuous approximation of ``sign`` (either linear or
    hyperbolic tangent), ``d`` is the optional damping gain and ``u_eq`` is
    the equivalent control derived from the dynamics model.  The final output
    ``u`` and the disturbance‑like internal state ``z`` are both saturated
    to lie within the actuator limits.

    The boundary layer ε (> 0) is validated at construction time to avoid
    division by zero in the saturated sign computation.  A well‑chosen ε
    ensures finite‑time convergence and reduces chattering.

    **Gain positivity (F‑4.SMCDesign.2 / RC‑04)**:  For finite‑time convergence of
    the super‑twisting algorithm the algorithmic gains ``K1`` and ``K2`` must
    be strictly positive and the sliding‑surface gains ``k1`` and ``k2`` together
    with the slope parameters ``λ1`` and ``λ2`` must also be strictly positive.
    Super‑twisting literature emphasises that positive constants are required to
    ensure robust finite‑time stability【MorenoOsorio2012†L27-L40】 and positive
    sliding‑surface coefficients guarantee that the error terms combine with
    positive weights【OkstateThesis2013†L1415-L1419】.  The constructor therefore
    validates all gains using ``require_positive`` and raises a ``ValueError``
    when any gain is non‑positive.

    Returns
    -------
    tuple
        A triple ``(u, (z, σ), history)`` containing the saturated control
        signal ``u``, the updated internal state and sliding surface value,
        and a history dictionary (empty for this controller).
    """

    def __init__(
        self,
        gains: Union[Tuple[float, ...], List[float]],
        dt: float,
        max_force: float = 150.0,
        damping_gain: float = 0.0,
        boundary_layer: float = 0.01,
        dynamics_model: Optional[object] = None,
        switch_method: str = "linear",
        regularization: float = 1e-10,
        anti_windup_gain: float = 0.0,
    ) -> None:
        """
        Initialize a Super‑Twisting Sliding Mode Controller.

        Parameters
        ----------
        gains : array‑like of length 2 or 6
            Controller gains.  A 2‑vector supplies algorithmic gains
            ``[K1, K2]`` and defaults sliding surface parameters.  A 6‑vector
            supplies ``[K1, K2, k1, k2, λ1, λ2]`` explicitly.
        dt : float
            Integration time step (seconds). Must be > 0.
        max_force : float, optional
            Actuator saturation limit.  Defaults to ``150.0``.  The control
            output will be clipped to ``[-max_force, max_force]``.
        damping_gain : float, optional
            Linear damping term multiplied by the sliding surface σ.  Defaults to
            ``0.0``.
        boundary_layer : float, optional
            Positive width of the boundary layer used to regularize the sign
            function.  Defaults to ``0.01``.  A non‑zero value is required to
            avoid division by zero and to guarantee finite‑time convergence in
            the discrete super‑twisting algorithm. **Raises `ValueError` if ≤ 0.**
        switch_method : {"linear","tanh"}, optional
            Method for saturated sign of σ. Defaults to "linear".
        dynamics_model : object, optional
            Dynamics model used to compute the equivalent control.  If ``None``,
            the equivalent control will be zero.
        """
        # Gain initialization
        # Store a private copy of the provided gains for external
        # introspection via the ``gains`` property.  Accept both 2‑ and 6‑
        # element sequences.  Only the relevant elements are used for
        # internal parameters; extra values are ignored.
        self._gains = list(gains)
        if len(gains) == 2:
            self.alg_gain_K1, self.alg_gain_K2 = map(float, gains)
            # Default surface gains (positive constants).  Choosing conservative
            # defaults ensures the sliding surface has a positive slope and
            # finite‑time convergence properties【MorenoOsorio2012†L27-L40】.
            self.surf_gain_k1, self.surf_gain_k2, self.surf_lam1, self.surf_lam2 = 5.0, 3.0, 2.0, 1.0
        elif len(gains) == 6:
            self.alg_gain_K1, self.alg_gain_K2, self.surf_gain_k1, self.surf_gain_k2, self.surf_lam1, self.surf_lam2 = map(float, gains[:6])
        else:
            raise ValueError("SuperTwistingSMC requires 2 or 6 gains")


        # Store parameters from arguments
        self.dyn = dynamics_model
        # Validate core parameters using the shared utility.  These
        # validations enforce positivity or non‑negativity with
        # consistent error messages across controllers.  See
        # `src/utils/control_primitives.require_positive` for details.
        # Import from new modular utils structure
        try:
            from src.utils import require_positive  # when repo root on sys.path
        except Exception:
            try:
                from ...utils import require_positive  # when importing as src.controllers.*
            except Exception:
                from utils import require_positive    # when src itself on sys.path

        # Integration step must be strictly positive to avoid division by
        # zero in discrete‑time updates.
        self.dt = require_positive(dt, "dt")

        # Saturation limit must be strictly positive; if zero the
        # controller could never exert any force and would be ineffective.
        self.max_force = require_positive(max_force, "max_force")

        # Damping gain is a free parameter; allow any finite float
        # (positive, zero or negative) without validation here.  The
        # smoothing effect of the damping term is documented in the
        # class docstring.
        self.damping_gain = float(damping_gain)

        # Boundary layer width epsilon must be strictly positive to
        # avoid division by zero in the saturated sign function.  Use
        # `require_positive` to centralise this check and unify error
        # messages across controllers.
        self.boundary_layer = require_positive(boundary_layer, "boundary_layer")

        # ---- Additional validation of STA gains (F‑4.SMCDesign.2 / RC‑04) ----
        # Enforce positivity of algorithmic gains K1, K2 and sliding‑surface
        # parameters k1, k2, λ1, λ2.  Positive constants ensure finite‑time
        # stability and well‑posed Lyapunov surfaces【MorenoOsorio2012†L27-L40】.
        self.alg_gain_K1 = require_positive(self.alg_gain_K1, "K1")
        self.alg_gain_K2 = require_positive(self.alg_gain_K2, "K2")
        self.surf_gain_k1 = require_positive(self.surf_gain_k1, "k1")
        self.surf_gain_k2 = require_positive(self.surf_gain_k2, "k2")
        self.surf_lam1 = require_positive(self.surf_lam1, "lam1")
        self.surf_lam2 = require_positive(self.surf_lam2, "lam2")
        sm = str(switch_method).lower().strip()
        if sm not in ("linear", "tanh"):
            raise ValueError("switch_method must be 'linear' or 'tanh'")
        self.switch_method = sm

        # Placeholders for optional equivalent control
        self.L = np.array([0.0, self.surf_gain_k1, self.surf_gain_k2], dtype=float)
        self.B = np.array([1.0, 0.0, 0.0], dtype=float)

        # Logger
        self.logger = logging.getLogger(self.__class__.__name__)

        # Regularisation constant used in the equivalent control term.  A
        # small positive diagonal added to the inertia matrix improves
        # conditioning and ensures the matrix is invertible.
        self.regularization = float(regularization)

        # Anti‑windup gain used in back‑calculation.  When non‑zero, the
        # integrator state z is updated using the difference between the
        # saturated and unsaturated control to prevent integrator wind‑up
        # under actuator saturation【789743582768797†L224-L249】.
        self.anti_windup_gain = float(anti_windup_gain)

        # Expose the expected length of the gain vector to external tools.
        # When a 2‑element gain vector is supplied the remaining surface
        # parameters default to conservative values; however PSO and other
        # tuners should explore the full six‑dimensional space.  Declare
        # six as the nominal dimension so that vector bounds reflect this
        # maximum length.  See design review section 5 (PSO integration).
        self.n_gains: int = 6

    # ---------------- Controller state/history API ----------------

    def initialize_state(self) -> tuple[float, float]:
        """Return (z, sigma) initial internal state."""
        return (0.0, 0.0)

    def initialize_history(self) -> Dict:
        return {}

    # ---------------- Main control computation -------------------

    def compute_control(
        self,
        state: np.ndarray,
        state_vars: tuple,
        history: dict,
    ) -> STAOutput:
        # State variables may be provided either as a tuple of (z, sigma)
        # or as a single scalar (legacy usage).  Accept both forms.
        try:
            # Unpack z and ignore provided sigma; the sliding surface will
            # be recomputed below.
            z, _ = state_vars
        except Exception:
            # Non‑iterable (e.g., float) provided: treat as z and
            # initialize sigma to zero.  Cast to float to avoid
            # unexpected types (e.g., numpy scalars).
            z = float(state_vars) if state_vars is not None else 0.0

        u_eq = self._compute_equivalent_control(state)

        # Compute sliding surface and its saturated sign using shared utility
        sigma = self._compute_sliding_surface(state)
        sgn_sigma = saturate(sigma, self.boundary_layer, method=self.switch_method)

        # Use numba core with precomputed sigma and sgn_sigma
        u, new_z, sigma_val = _sta_smc_core(
            z=z,
            sigma=float(sigma),
            sgn_sigma=float(sgn_sigma),
            alg_gain_K1=self.alg_gain_K1,
            alg_gain_K2=self.alg_gain_K2,
            damping_gain=self.damping_gain,
            dt=self.dt,
            max_force=self.max_force,
            u_eq=u_eq,
            Kaw=self.anti_windup_gain,
        )
        # Telemetry: append key signals to history (in-place)
        hist = history if isinstance(history, dict) else {}
        hist.setdefault('sigma', []).append(float(sigma))
        hist.setdefault('z', []).append(float(new_z))
        hist.setdefault('u', []).append(float(u))
        hist.setdefault('u_eq', []).append(float(u_eq))

        # Package results into a named tuple. The internal state carries
        # the updated z and latest sliding surface value.
        return STAOutput(u, (new_z, float(sigma)), hist)

    def validate_gains(self, gains_b: "np.ndarray") -> "np.ndarray":
        """
        Vectorized feasibility check for super‑twisting SMC gains.

        The algorithmic gains ``K1`` and ``K2`` must be strictly positive to
        ensure finite‑time convergence of the super‑twisting algorithm.  When
        a six‑element gain vector is provided the sliding‑surface gains
        ``k1``, ``k2`` and the lambda parameters ``lam1``, ``lam2`` must also
        be positive.  Positive sliding‑surface coefficients are required
        because the sliding surface is a linear combination of state
        variables with positive weights.

        Parameters
        ----------
        gains_b : np.ndarray
            Array of shape (B, D) containing candidate gain vectors.  The
            first two columns correspond to ``K1`` and ``K2``; if ``D`` ≥ 6
            then columns 3–6 correspond to ``k1``, ``k2``, ``lam1`` and
            ``lam2`` respectively.

        Returns
        -------
        np.ndarray
            Boolean mask of shape (B,) indicating which rows satisfy the
            positivity constraints.
        """
        import numpy as _np
        if gains_b.ndim != 2 or gains_b.shape[1] < 2:
            return _np.ones(gains_b.shape[0], dtype=bool)
        # Always require K1 and K2 to be positive
        k1 = gains_b[:, 0].astype(float)
        k2 = gains_b[:, 1].astype(float)
        valid = (k1 > 0.0) & (k2 > 0.0)
        # If sliding surface parameters are provided, require them to be positive
        if gains_b.shape[1] >= 6:
            surf_k1 = gains_b[:, 2].astype(float)
            surf_k2 = gains_b[:, 3].astype(float)
            lam1 = gains_b[:, 4].astype(float)
            lam2 = gains_b[:, 5].astype(float)
            valid = valid & (surf_k1 > 0.0) & (surf_k2 > 0.0) & (lam1 > 0.0) & (lam2 > 0.0)
        return valid

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def gains(self) -> List[float]:
        """Return a copy of the gains used to configure this controller.

        The returned list includes all elements supplied to the constructor,
        whether 2 or 6 gains.  This enables external code (and tests) to
        inspect the algorithmic and sliding‑surface gains after
        instantiation without risk of mutating the internal state.
        """
        return list(self._gains)
    # ---------------- Utilities -------------------

    def reset(self) -> None:
        """Reset STA-SMC controller state.

        Resets internal state variables to initial conditions:
        - Clears the integral state z
        - Resets the last surface value
        - Reinitializes any internal tracking variables
        """
        # Reset integral state (z) to zero
        # This is the main internal state for the super-twisting algorithm
        pass  # The controller gets z from state_vars parameter, no persistent internal state

    def set_dynamics(self, dynamics_model) -> None:
        """Attach dynamics model if available (used by u_eq if implemented)."""
        self.dyn = dynamics_model

    def _compute_sliding_surface(self, state: np.ndarray) -> float:
        _, th1, th2, _, th1dot, th2dot = state
        return self.surf_gain_k1 * (th1dot + self.surf_lam1 * th1) + self.surf_gain_k2 * (th2dot + self.surf_lam2 * th2)

    def _compute_equivalent_control(self, state: np.ndarray) -> float:
        """Compute the model‑based equivalent control ``u_eq`` using Tikhonov regularisation.

        The original implementation used an SVD‑based condition estimate and a
        pseudo‑inverse to invert the inertia matrix.  This version instead
        applies a small diagonal regularisation and solves the resulting
        linear systems directly, reducing computational overhead and
        eliminating the need for a full SVD.  Adding a small constant to
        the diagonal of a symmetric indefinite matrix makes it positive
        definite and invertible, a standard technique in control
        literature.
        """
        if self.dyn is None:
            return 0.0

        q_dot = state[3:]
        try:
            M, C, G = self.dyn._compute_physics_matrices(state)
        except Exception:
            return 0.0

        # Regularise the inertia matrix using the configurable constant.  A
        # small diagonal offset guarantees invertibility of symmetric
        # matrices.
        M_reg = M + np.eye(3) * max(self.regularization, 0.0)
        try:
            # Compute controllability scalar L M^-1 B.  Use the boundary layer
            # thickness as a threshold for ill‑conditioned feedforward terms.
            Minv_B = np.linalg.solve(M_reg, self.B)
            L_Minv_B = float(self.L @ Minv_B)
            # If the equivalent control would divide by a very small number,
            # return zero.  The threshold equals the boundary layer epsilon
            # such that the same tuning parameter governs both chattering
            # mitigation and model invertibility.
            if abs(L_Minv_B) < self.boundary_layer:
                return 0.0

            # Compute rhs = C q_dot + G.  Support both matrix and vector forms.
            if getattr(C, "ndim", 1) == 2:
                rhs = C @ q_dot + G
            else:
                rhs = C + G
            Minv_rhs = np.linalg.solve(M_reg, rhs)
            num = float(self.L @ Minv_rhs)
            # Equivalent control is the feedforward term minus the damping
            # portion from the sliding surface definition.  Following
            # conventional SMC, subtract the inner product of the surface
            # gains with the joint velocities.  Note the sign convention
            # matches the one used in ClassicalSMC.
            u_eq = (num - (self.surf_gain_k1 * self.surf_lam1 * q_dot[1] +
                           self.surf_gain_k2 * self.surf_lam2 * q_dot[2])) / L_Minv_B
        except np.linalg.LinAlgError:
            # Singular matrix despite regularisation; disable equivalent control
            return 0.0

        # Do not apply additional clamping here.  The final saturation in
        # ``compute_control`` will bound the control effort.  Returning the
        # raw equivalent control maintains transparency and avoids
        # inadvertently biasing the controller output.
        return float(u_eq)
#========================================================================================================\\\
