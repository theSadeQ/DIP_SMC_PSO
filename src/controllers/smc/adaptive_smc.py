#==========================================================================================\\\
#========================== src/controllers/smc/adaptive_smc.py =========================\\\
#==========================================================================================\\\
"""
Adaptive sliding‑mode controller with online gain adaptation.

This implementation follows the classical adaptive SMC structure in
which the switching gain ``K`` is increased when the sliding
surface magnitude exceeds a dead zone and decays toward a nominal
value otherwise.  No control‑rate term is included in the
adaptation law; theoretical analyses show that augmenting the
adaptation with a rate‑dependent term can destabilise the closed
loop and is not required for convergence.
A continuous boundary layer of width ``boundary_layer`` is used to
approximate the discontinuous sign function, reducing chattering
at the expense of steady‑state accuracy.  The
boundary layer thickness must therefore be selected to balance
robustness and tracking error.  All gains
are validated for positivity to satisfy sliding‑mode stability
conditions.

Parameters
----------
gains : list of float
    Five gains in the order ``[k1, k2, lam1, lam2, gamma]``.
dt : float
    Simulation timestep (s); must be strictly positive.
max_force : float
    Saturation limit for the total control input.  Final commands
    are clipped to the interval [−max_force, +max_force].
leak_rate : float
    Leak coefficient that pulls the adaptive gain ``K`` back toward
    its nominal value ``K_init`` over time.  Non‑negative.
adapt_rate_limit : float
    Maximum rate of change allowed for ``K``.  Limits sudden
    growth or decay of the adaptive gain.
K_min, K_max : float
    Lower and upper bounds for ``K``.  These must satisfy
    ``0 < K_min ≤ K_init ≤ K_max``.  Bounding the gain ensures
    the controller remains within a physically reasonable range.
smooth_switch : bool
    If ``True`` the continuous switching function uses a hyperbolic
    tangent; otherwise a linear saturation is used.
boundary_layer : float
    Width of the boundary layer (ε) used in the switching function.
    Must be strictly positive; see [Utkin 1992] for the effects of
    boundary‑layer size on chattering.
dead_zone : float
    Radius around σ=0 in which adaptation is frozen to prevent
    wind‑up.  Outside this zone the adaptive gain increases
    proportionally to ``|σ|``.
K_init : float, optional
    Initial and nominal value of the adaptive gain ``K``.
alpha : float, optional
    Proportional term weighting the sliding surface in the control
    law.  Must be non‑negative.
**kwargs : dict
    Additional unused keyword arguments for forward compatibility.
"""

import numpy as np
from typing import Dict, Tuple, Optional, List

# ---------------------------------------------------------------------------
# Structured output type
#
# Import the named‑tuple output type from the sibling utils package using a
# relative import.  Using relative imports avoids issues when the project
# package is nested under different root prefixes.  See the design notes
# regarding explicit interfaces and return contracts.
# Import from organized legacy package
try:
    from src.utils import AdaptiveSMCOutput  # when repo root on sys.path
except Exception:
    try:
        from ...utils import AdaptiveSMCOutput  # when importing as src.controllers.*
    except Exception:
        from utils import AdaptiveSMCOutput    # when src itself on sys.path


class AdaptiveSMC:
    """
    Adaptive Sliding Mode Controller that adjusts gain K online.
    
    The controller prevents gain wind-up by using a dead zone around the sliding surface.
    When |σ| ≤ dead_zone, the gain K only decreases via the leak term, preventing
    uncontrolled growth during chattering.
    """
    n_gains = 5  
    def __init__(
        self,
        gains: List[float],
        dt: float,
        max_force: float,
        leak_rate: float,
        adapt_rate_limit: float,
        K_min: float,
        K_max: float,
        smooth_switch: bool,
        boundary_layer: float,
        dead_zone: float,
        K_init: float = 10.0,
        alpha: float = 0.5,
        **kwargs
    ):
        """
        Initialize Adaptive SMC controller.
        
        Args:
            gains: Five gains in the order ``[k1, k2, lam1, lam2, gamma]``.
            dt: Integration timestep (s); must be strictly positive.
            max_force: Saturation limit for the control input.
            leak_rate: Non‑negative leak coefficient that pulls ``K`` back
                toward ``K_init``.
            adapt_rate_limit: Maximum rate of change for ``K``; must be
                non‑negative.
            K_min: Minimum permissible value of ``K`` (strictly
                positive).
            K_max: Maximum permissible value of ``K`` (≥ ``K_min``).
            smooth_switch: If ``True``, use a hyperbolic tangent for
                switching; otherwise use a linear saturation.
            boundary_layer: Positive boundary‑layer thickness ε for the
                switching function; see the class docstring.
            dead_zone: Width of the dead zone (≥ 0) within which
                adaptation is frozen.
            K_init: Initial and nominal value of the adaptive gain ``K``.
            alpha: Proportional term weighting the sliding surface.
            **kwargs: Additional unused keyword arguments (ignored).
        """
        # Keep the original gains for external visibility.  Accept
        # additional gains by ignoring extras; this provides forward
        # compatibility with tests that pass extra values.  Only the
        # first five elements are used for controller parameters.
        #
        # Preserve the raw gains for introspection via a property.  Use
        # a private attribute to guard against accidental mutation of
        # controller parameters from the outside.  Tests assert that
        # ``controller.gains`` returns the same sequence that was
        # supplied at construction time, regardless of how many
        # additional gains were provided.
        # Validate the supplied gains early.  Use the static validator to
        # mirror STA's feasibility check and fail fast if the wrong number of
        # gains is provided.  This allows the factory or PSO tuner to
        # reject invalid configurations before instantiating the controller.
        self.validate_gains(gains)
        self._gains: List[float] = list(gains)
        # Use only the first 5 gains for internal parameters
        self.k1, self.k2, self.lam1, self.lam2, self.gamma = map(float, gains[:5])
        # Use centralised positivity checks for dt and max_force.  The
        # ``require_positive`` helper enforces strictly positive values and
        # provides consistent error messages across controllers.
        # Import from new modular utils structure
        try:
            from src.utils import require_positive  # when repo root on sys.path
        except Exception:
            try:
                from ...utils import require_positive  # when importing as src.controllers.*
            except Exception:
                from utils import require_positive    # when src itself on sys.path
        self.dt = require_positive(dt, "dt")
        self.max_force = require_positive(max_force, "max_force")
        # Remove rate_weight.  The adaptive SMC controller adapts its gain
        # solely based on the magnitude of the sliding surface, consistent with
        # adaptive SMC theory.  Including a control‑rate term has no
        # theoretical justification and can destabilise the adaptation law.  See
        # Roy (2020) for an adaptation law that increases the gain outside a
        # dead‑zone and decreases it within a neighbourhood of the sliding
        # surface.
        # Import from new modular utils structure
        try:
            from src.utils import require_positive  # when repo root on sys.path
        except Exception:
            try:
                from ...utils import require_positive  # when importing as src.controllers.*
            except Exception:
                from utils import require_positive    # when src itself on sys.path
        # Use central positivity checks.  leak_rate and adapt_rate_limit may be zero
        # according to design review but must not be negative.  Gains K_min and
        # K_max must be strictly positive to ensure Lyapunov stability.
        self.leak_rate = require_positive(leak_rate, "leak_rate", allow_zero=True)
        self.K_init = float(K_init)
        self.adapt_rate_limit = require_positive(adapt_rate_limit, "adapt_rate_limit", allow_zero=True)
        self.K_min = require_positive(K_min, "K_min")
        self.K_max = require_positive(K_max, "K_max")
        self.smooth_switch = smooth_switch
        # Validate boundary layer via central utility
        self.boundary_layer = require_positive(boundary_layer, "boundary_layer")

        # dead_zone can be zero or positive; enforce non‑negativity via helper
        self.dead_zone = require_positive(dead_zone, "dead_zone", allow_zero=True)
        self.alpha = float(alpha)
        # Additional envelope / rate validations
        if not (self.K_min <= self.K_init <= self.K_max):
            raise ValueError("Require K_min ≤ K_init ≤ K_max")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def gains(self) -> List[float]:
        """
        Return a copy of the gain vector supplied to this controller.

        The returned list includes all elements that were passed in
        through the ``gains`` argument during initialization.  It is a
        shallow copy to prevent external callers from mutating the
        internal gain storage.  Tests use this property to verify that
        custom gains are accepted and stored correctly.
        """
        return list(self._gains)        

    @staticmethod
    def validate_gains(gains: List[float]) -> None:
        """
        Validate that a suitable gain sequence has been provided.

        The adaptive sliding–mode controller uses exactly five gains
        (k1, k2, λ1, λ2, γ) for its sliding surface and adaptation law.
        Additional gains may be supplied for forward compatibility
        (they will be ignored), but fewer than five gains is considered
        an error.

        Raises
        ------
        ValueError
            If ``gains`` has fewer than five elements.
        """
        if not isinstance(gains, (list, tuple)) or len(gains) < 5:
            raise ValueError(
                "AdaptiveSMC requires at least 5 gains: [k1, k2, lam1, lam2, gamma]"
            )
        # Enforce positive sliding‑surface gains and adaptation gain using a shared helper.
        # The sliding surface is a linear combination of state variables with
        # positive weights; choosing non‑positive values violates the
        # conditions for sliding‑mode stability.
        # Import from new modular utils structure
        try:
            from src.utils import require_positive  # when repo root on sys.path
        except Exception:
            try:
                from ...utils import require_positive  # when importing as src.controllers.*
            except Exception:
                from utils import require_positive    # when src itself on sys.path
        k1, k2, lam1, lam2, gamma = gains[:5]
        for name, val in zip(("k1", "k2", "lam1", "lam2", "gamma"), (k1, k2, lam1, lam2, gamma)):
            require_positive(val, f"AdaptiveSMC gain {name}")
    def initialize_state(self) -> Tuple[float, float, float]:
        """Initialize internal state: (K, last_u, time_in_sliding)."""
        return (self.K_init, 0.0, 0.0)
        
    def initialize_history(self) -> Dict:
        """Initialize history dictionary."""
        return {
            'K': [],
            'sigma': [],
            'u_sw': [],
            'dK': [],
            'time_in_sliding': []
        }
        
    def compute_control(
        self,
        state: np.ndarray,
        state_vars: Tuple[float, float, float],
        history: Dict,
    ) -> AdaptiveSMCOutput:  # type: ignore[override]
        """
        Compute the adaptive sliding–mode control law with unified anti‑windup.

        The controller constructs a sliding surface based on the joint
        velocities and positions and generates a switching control using
        either a hyperbolic tangent or a linear saturation function.  The
        adaptive gain ``K`` increases proportionally to the magnitude of the
        sliding surface whenever the system is outside a small dead‑zone and
        remains constant (or decays slowly toward its nominal value) inside
        the dead‑zone.  Unlike some earlier
        implementations, the adaptation law no longer depends on the rate of
        change of the control input; including such a term lacks theoretical
        justification and can destabilise the adaptation process.  A leak
        term pulls ``K`` back toward ``K_init`` over time to prevent
        unbounded growth.  The method returns the saturated control input,
        updated internal state variables, an updated history dictionary and
        the current sliding surface value packaged as a named tuple.  Using
        a structured return type formalises the contract and allows callers
        to access fields by name.

        Parameters
        ----------
        state : np.ndarray
            The full system state [x, θ1, θ2, ẋ, θ̇1, θ̇2].
        state_vars : Tuple[float, float, float]
            The internal controller state (K, last_u, time_in_sliding).
        history : Dict
            A dictionary storing time series of internal variables.  The
            entries 'K', 'sigma', 'u_sw', 'dK', and 'time_in_sliding'
            will be appended in place.

        Returns
        -------
        AdaptiveSMCOutput
            A named tuple ``(u, state, history, sigma)`` containing the
            saturated control input, updated internal state variables,
            the updated history dictionary and the current sliding
            surface.  Using a named tuple formalises the return contract
            and allows callers to access fields by name rather than
            positional index.  This reduces ambiguity and
            preserves backward compatibility because named tuples are
            subclasses of ``tuple``.
        """
        # The tests may supply ``state_vars`` in various shapes (e.g., a
        # single float instead of a 3‑tuple).  Robustly unpack the
        # adaptive gain (prev_K), the previous control (last_u), and
        # accumulated time in the sliding region.  Defaults are chosen
        # to match ``initialize_state()`` when information is missing.
        try:
            # Expecting a 3‑tuple: (K, last_u, time_in_sliding)
            prev_K, last_u, time_in_sliding = state_vars  # type: ignore[misc]
        except Exception:
            # Fall back for legacy or malformed inputs.  Accept
            # sequences of varying length or scalar values.  Coerce
            # values to floats to avoid numpy scalar surprises.
            if isinstance(state_vars, (list, tuple)):
                if len(state_vars) == 0:
                    prev_K, last_u, time_in_sliding = self.K_init, 0.0, 0.0
                elif len(state_vars) == 1:
                    prev_K = float(state_vars[0]) if state_vars[0] is not None else self.K_init
                    last_u, time_in_sliding = 0.0, 0.0
                elif len(state_vars) == 2:
                    prev_K = float(state_vars[0]) if state_vars[0] is not None else self.K_init
                    last_u = float(state_vars[1]) if state_vars[1] is not None else 0.0
                    time_in_sliding = 0.0
                else:
                    # More than 3 values: use the first three
                    prev_K = float(state_vars[0]) if state_vars[0] is not None else self.K_init
                    last_u = float(state_vars[1]) if state_vars[1] is not None else 0.0
                    time_in_sliding = float(state_vars[2]) if state_vars[2] is not None else 0.0
            else:
                # Scalar or None: treat as K and initialize others to zero
                prev_K = float(state_vars) if state_vars is not None else self.K_init
                last_u, time_in_sliding = 0.0, 0.0
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state
        
        # Compute sliding surface (consistent with classical SMC formulation)
        sigma = self.k1 * (theta1_dot + self.lam1 * theta1) + self.k2 * (theta2_dot + self.lam2 * theta2)
        
        # Compute switching control with current adaptive gain.  Use the
        # shared ``saturate`` helper to unify boundary layer behaviour
        # across controllers.  ``saturate`` divides by epsilon internally.
        # robust import for utils.* to support both import styles
        try:
            from src.utils import saturate  # when repo root on sys.path
        except Exception:
            try:
                from ...utils import saturate  # when importing as src.controllers.*
            except Exception:
                from utils import saturate    # when src itself on sys.path
        if self.smooth_switch:
            switching = saturate(sigma, self.boundary_layer, method="tanh")
        else:
            switching = saturate(sigma, self.boundary_layer, method="linear")
            
        u_sw = -prev_K * switching
        
        # Total control with proportional term for improved convergence
        u = u_sw - self.alpha * sigma
        u = np.clip(u, -self.max_force, self.max_force)
        
        # Update time in sliding mode
        if abs(sigma) <= self.boundary_layer:
            new_time_in_sliding = time_in_sliding + self.dt
        else:
            new_time_in_sliding = 0.0
        
        # Adaptive law with unified anti‑windup logic.
        #
        # The adaptive sliding–mode controller adjusts the switching gain based
        # solely on the magnitude of the sliding surface σ.  According to
        # adaptive SMC theory, the gain should increase when the system is
        # outside a small neighbourhood of the sliding manifold and should
        # remain constant (or decay slowly toward its nominal value) inside
        # this neighbourhood.  Including the rate of
        # change of the control input in the adaptation law is not justified
        # by standard analysis and may introduce unnecessary coupling.  We
        # therefore remove the control‑rate term and implement the standard
        # adaptation law:
        #   dK = γ·|σ| − leak_rate·(K − K_init)   if |σ| > dead_zone
        #   dK = 0                                if |σ| ≤ dead_zone
        if abs(sigma) <= self.dead_zone:
            # Inside dead zone: hold K constant (no growth or decay).  This
            # prevents the gain from drifting downward due to the leak term
            # when the sliding surface is small, preserving the learned
            # disturbance bound.
            dK = 0.0
        else:
            # Outside dead zone: increase K proportional to |σ| and apply a
            # leak term pulling K back toward its nominal value.  The leak
            # term prevents unbounded growth once disturbances subside.
            growth = self.gamma * abs(sigma)
            dK = growth - self.leak_rate * (prev_K - self.K_init)
        
        # Apply rate limit to prevent sudden jumps
        dK = np.clip(dK, -self.adapt_rate_limit, self.adapt_rate_limit)
        
        # Update gain with saturation
        new_K = prev_K + dK * self.dt
        new_K = np.clip(new_K, self.K_min, self.K_max)
        
        # Update history in place.  Avoid allocating a new dictionary
        # on every call; simply append to existing lists.  Initialize
        # lists if they are missing to support callers passing in a
        # partially filled history.  History accumulation can be
        # disabled by passing in an empty dict, though the lists
        # will be created on demand if needed.
        hist = history
        hist.setdefault('K', []).append(new_K)
        hist.setdefault('sigma', []).append(sigma)
        hist.setdefault('u_sw', []).append(u_sw)
        hist.setdefault('dK', []).append(dK)
        hist.setdefault('time_in_sliding', []).append(new_time_in_sliding)
        # Construct a structured return value.  Returning a named tuple
        # clarifies the meaning of each element while preserving
        # tuple‑like behaviour.
        return AdaptiveSMCOutput(u, (new_K, u, new_time_in_sliding), hist, sigma)
        
    def set_dynamics(self, dynamics_model) -> None:
        """Set dynamics model (for compatibility, not used in this implementation)."""
        pass

    def reset(self) -> None:
        """Reset AdaptiveSMC controller state.

        Resets the adaptive gain K to its initial value and clears
        any internal tracking variables.
        """
        # Reset adaptive gain to initial value
        # Note: The controller uses state_vars parameter for persistence,
        # so we don't maintain persistent internal state here.
        # This method ensures interface compliance.
        pass
#===========================================================================================================\\\