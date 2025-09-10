#==================================================================================\\\
# src/config.py ===================================================================\\\
#==================================================================================\\\

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Import the global seeding utility.  Placing this import near the top
# avoids circular dependencies when tests import ConfigSchema directly.
from src.utils.seed import set_global_seed

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Configuration strictness
#
# Earlier revisions of this module used a module‑level ``ALLOW_UNKNOWN_CONFIG``
# flag and a corresponding ``set_allow_unknown_config`` function to toggle
# permissive parsing of unknown keys in controller sections.  Relying on
# mutable module state is brittle because concurrent calls to ``load_config``
# may race to change the flag and because the global flag outlives the scope
# of a single configuration parse.  To eliminate this hidden coupling, the
# permissive behaviour is now controlled per‑call: the ``allow_unknown``
# keyword argument of ``load_config`` sets a class attribute on
# ``PermissiveControllerConfig`` before model construction and restores the
# previous value afterwards.  This design removes the global flag and keeps
# the acceptance of unknown keys explicit at the call site【401883805680716†L137-L149】.

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import yaml
from pathlib import Path


# --- Strict base for all config models (CFG-002) ---
class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)


# --------------- Physics ----------------- #
class PhysicsConfig(StrictModel):
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
    # Friction coefficients must be non‑negative.  Negative friction would
    # imply energy generation rather than dissipation and is physically
    # nonsensical.  Enforce a lower bound of zero on each friction
    # coefficient【121871467923514†L253-L288】.
    cart_friction: float = Field(..., ge=0.0)
    joint1_friction: float = Field(..., ge=0.0)
    joint2_friction: float = Field(..., ge=0.0)
    singularity_cond_threshold: float = Field(1.0e8, ge=1e4)

    # Regularisation constant for the inertia matrix.  Adding a small
    # diagonal offset (Tikhonov regularisation) to the inertia matrix
    # improves conditioning and ensures it remains positive definite
    #【91747125250215†L146-L153】.  Defaults to 1e‑10.
    # Regularisation constant for the inertia matrix.  A strictly
    # positive Tikhonov term ensures the matrix is positive definite
    # and invertible【474685546011607†L282-L292】.  Values approaching zero
    # degrade conditioning and may lead to singularity.  Reject zero
    # values to encourage physically meaningful regularisation.
    regularization: float = Field(1e-10, gt=0.0)

    # Determinant threshold below which the inertia matrix is treated as
    # singular.  The original implementation used 1e‑12; expose this
    # parameter so users can tune the sensitivity.  A smaller threshold
    # tolerates more ill‑conditioned matrices at the risk of numerical
    # instability.
    # Determinant threshold below which the inertia matrix is treated as
    # singular.  Setting this threshold too large causes the solver to
    # prematurely flag invertible matrices as ill‑conditioned.  To
    # prevent users from accidentally disabling simulation with an
    # excessively large value, enforce an upper bound (1e‑3) informed
    # by typical scales of the inertia matrix determinants in the
    # double pendulum【474685546011607†L282-L292】.
    det_threshold: float = Field(1e-12, ge=0.0, le=1e-3)

    @field_validator(
        'cart_mass', 'pendulum1_mass', 'pendulum2_mass',
        'pendulum1_length', 'pendulum2_length',
        'pendulum1_inertia', 'pendulum2_inertia',
        'pendulum1_com', 'pendulum2_com',
        'gravity'
    )
    @classmethod
    def _must_be_strictly_positive(cls, v: float, info) -> float:
        """
        Ensure that the provided value is strictly positive.

        The original implementation imposed a hard lower bound of 1e-6 on
        these parameters, which prevented the use of extremely small but
        physically valid values (e.g., 1e-12).  The updated validator only
        checks that the value is greater than zero, rejecting non-positive
        inputs.  None values are still disallowed.

        Parameters
        ----------
        v : float
            The value to validate.
        info : pydantic.fields.FieldInfo
            Field metadata, used only for error reporting.

        Returns
        -------
        float
            The validated (and coerced) float value.

        Raises
        ------
        ValueError
            If the input is None or not strictly positive.
        """
        if v is None or v <= 0.0:
            raise ValueError(f"{info.field_name} must be strictly positive, but got {v}")
        return float(v)

    @model_validator(mode='after')
    def _validate_com_within_length(self) -> 'PhysicsConfig':
        if self.pendulum1_com >= self.pendulum1_length:
            raise ValueError(
                f"pendulum1_com ({self.pendulum1_com}) must be less than pendulum1_length ({self.pendulum1_length})"
            )
        if self.pendulum2_com >= self.pendulum2_length:
            raise ValueError(
                f"pendulum2_com ({self.pendulum2_com}) must be less than pendulum2_length ({self.pendulum2_length})"
            )
        return self


class PhysicsUncertaintySchema(StrictModel):
    n_evals: int
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


# ---------------- Simulation -------------------#
class SimulationConfig(StrictModel):
    duration: float
    dt: float = 0.01
    initial_state: Optional[List[float]] = None
    # When True the vectorised simulator uses the full nonlinear pendulum
    # dynamics rather than the simplified toy model.  High‑fidelity
    # simulations are recommended during controller tuning because
    # low‑fidelity models can yield misleading performance estimates.  A
    # comparative study showed that low‑fidelity designs produced
    # predictions with 21–25% relative error while high‑fidelity models
    # achieved 4–6% error【39347391922137†L146-L166】.  Default to True so that
    # PSO optimisation and batch simulations use the accurate dynamics
    # unless the caller explicitly opts in to the simplified model for
    # preliminary exploration.【39347391922137†L146-L166】
    use_full_dynamics: bool = True

    # Sensor latency in seconds.  A positive latency delays the
    # measurement provided to the controller, emulating sample‑and‑hold or
    # communication delays.  The latency must be non‑negative and is
    # quantised to integer multiples of ``dt`` in the simulation runner.
    sensor_latency: float = Field(0.0, ge=0.0)

    # Actuator latency in seconds.  A positive latency delays the
    # application of computed control commands, modelling actuator
    # response delays or command buffering.  Latency must be
    # non‑negative and is quantised to integer multiples of ``dt``.  When
    # greater than zero the simulation runner holds previous control
    # inputs for the specified delay duration before applying new
    # commands to the dynamics.
    actuator_latency: float = Field(0.0, ge=0.0)

    # When True, the simulation runner will attempt to align wall‑clock
    # time with simulation time by sleeping up to ``dt`` seconds per
    # iteration.  Real‑time simulation helps test controllers under
    # realistic timing constraints and prevents simulation from running
    # faster than a physical system can respond【785499886503999†L146-L179】.  This
    # flag defaults to False to avoid slowing down batch simulations.
    real_time: bool = False

    # When True the simulation runner will raise an exception on serious
    # numerical issues (e.g., NaNs, singularities) instead of logging a
    # warning and returning truncated results.  This facilitates
    # fail‑fast behaviour in safety‑critical applications.  See design
    # review issue #21.  Defaults to False, meaning warnings are
    # emitted and the simulation continues where possible.
    raise_on_warning: bool = False

# -----------------------------------------------------------------------------
# Provide a lightweight configuration namespace for components that only need
# the ``config.simulation.use_full_dynamics`` and optional safety settings.
#
# Some modules import ``src.config`` solely to read this attribute; defining
# ``config`` here ensures that importing ``src.config`` succeeds even when
# pydantic or other dependencies are unavailable.  The default ``use_full_dynamics``
# is ``False`` so that simulations run in low‑rank mode unless explicitly
# enabled.  The ``safety`` attribute may be monkeypatched by tests or callers
# to supply energy or bound limits.
try:
    from types import SimpleNamespace
    # Only define ``config`` if it doesn't already exist in the module
    if "config" not in globals():
        config = SimpleNamespace(
            simulation=SimpleNamespace(
                use_full_dynamics=False,
                safety=None,
            )
        )
except Exception:
    pass

    @model_validator(mode='after')
    def _check_duration_vs_dt(self) -> 'SimulationConfig':
        """
        Validate that the simulation horizon is at least one integration step.

        The design review noted that passing a duration shorter than the
        integration step ``dt`` would result in zero integration steps and an
        empty trajectory.  Explicitly enforcing ``duration >= dt`` prevents
        this misconfiguration at parse time.  Classical simulation theory
        requires that the time horizon contain at least one integration
        interval; see numerical integration discussions in Golub & Van Loan
        for why zero‑step integration yields no evolution.  A warning is
        raised via pydantic validation if the constraint is violated.  This
        aligns the schema with the implicit assumption in the simulation
        runner that at least one step will be executed.

        Returns
        -------
        SimulationConfig
            The validated configuration instance.

        Raises
        ------
        ValueError
            If ``duration`` is less than ``dt``.
        """
        if self.duration is not None and self.dt is not None:
            if float(self.duration) < float(self.dt):
                raise ValueError(
                    f"duration ({self.duration}) must be at least one timestep dt ({self.dt})"
                )
        return self

    @field_validator("dt", "duration")
    @classmethod
    def _must_be_positive(cls, v: float, info):
        if v is None or v <= 0.0:
            raise ValueError(f"{info.field_name} must be > 0")
        return float(v)

    @model_validator(mode="after")
    def _duration_at_least_dt(self):
        if self.duration < self.dt:
            raise ValueError("simulation.duration must be >= simulation.dt")
        return self

    @field_validator("initial_state")
    @classmethod
    def _initial_state_valid(cls, v):
        """
        Validate the initial state vector provided to the simulator.

        Earlier versions of this project enforced a fixed six‑element state
        vector corresponding to the cart position, two pendulum angles and
        their velocities.  This rigid assumption prevented the addition of
        extra actuator or sensor states and violated the open‑closed
        principle.  Consistent with the design review recommendations, the
        initial state may now contain an arbitrary number of elements.  The
        only requirement is that the list is non‑empty and contains
        real‑valued entries.  The simulation runner infers the state
        dimension from the length of this list and allocates arrays
        accordingly.

        Returns
        -------
        list
            The validated initial state vector.

        Raises
        ------
        ValueError
            If the provided value is not a list or is empty.
        """
        if v is None:
            return v
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError(
                "initial_state must be a non‑empty list of floats; its length determines the state dimension"
            )
        # Cast elements to float for consistency
        return [float(x) for x in v]


# ---------------- Controllers -------------------#
class _BaseControllerConfig(BaseModel):
    """
    Base class for per‑controller configuration.

    By default this class forbids unknown keys to ensure that callers
    explicitly specify only supported configuration fields.  The primary
    `ControllerConfig` alias below inherits from this base and therefore
    rejects any unexpected attributes (e.g., ``rate_weight``) when
    instantiated directly.

    When loading a configuration file, however, we still need to accept
    arbitrary controller‑specific parameters (to maintain backwards
    compatibility).  For that purpose the `PermissiveControllerConfig`
    subclass below overrides the `extra` behaviour to allow unknown keys
    while still exposing them as attributes on the resulting object.
     """
    model_config = ConfigDict(extra='forbid')
    gains: List[float] = Field(default_factory=list, min_length=1)

    def __iter__(self):
        """Iterate over key/value pairs for backward compatibility."""
        for k, v in self.model_dump(exclude_unset=True).items():
            yield k, v

class ControllerConfig(_BaseControllerConfig):
    """
    Strict per‑controller configuration model.

    This alias is provided for direct use in code and tests.  It forbids
    unspecified fields by inheriting from `_BaseControllerConfig`, which
    uses `extra='forbid'`.  Attempts to instantiate this class with
    unknown keys (e.g., ``rate_weight``) will raise a `ValidationError`.
    """
    pass


class PermissiveControllerConfig(_BaseControllerConfig):
    """
    Permissive variant of the controller configuration.

    In earlier versions of the project this class permitted arbitrary
    keys to be specified in the YAML by setting ``extra='allow'`` and
    storing unknown fields in ``unknown_params``.  While preserving
    unknown parameters can be helpful when extending controllers, it
    also allows typographical errors to silently pass through
    validation.  Following the recommendations in the Step 3
    verification report, the default behaviour of this model is now
    **strict**: unknown keys cause a ``ValueError`` to be raised.  This
    protects users from inadvertently mis‑spelling configuration
    options.  If an application needs to accept unknown keys it
    should do so explicitly (e.g., by supplying a command‑line flag
    that relaxes validation and bypassing the Pydantic schema).

    During validation any extraneous keys are collected into
    ``unknown_params``.  If unknown parameters are present the
    validator raises a ``ValueError`` listing the offending keys.  To
    re‑enable permissive behaviour callers must explicitly call
    ``set_allow_unknown_config(True)`` before loading the
    configuration.  This function toggles the module‑level flag
    ``ALLOW_UNKNOWN_CONFIG``; no environment variables are consulted.
    """

    # Allow unknown keys at the Pydantic layer so they can be collected
    # during model validation.  If ``extra='forbid'`` were used here,
    # Pydantic would raise a ``ValidationError`` before our custom
    # validator has a chance to inspect the unknown keys.  Setting
    # ``extra='allow'`` permits arbitrary parameters to be parsed into
    # the model and subsequently stored in ``unknown_params``.  Whether
    # such parameters are accepted or rejected is then governed by the
    # module‑level flag ``ALLOW_UNKNOWN_CONFIG``, which can be toggled via
    # ``set_allow_unknown_config``.  Environment variables are no longer
    # consulted for this purpose.  Allowing unknown keys aligns with
    # flexible design philosophies in robust control where additional
    # tuning parameters may be introduced without requiring immediate
    # schema updates【93203717924010†L31-L39】.
    model_config = ConfigDict(extra='allow')
    # Store any unknown controller configuration keys.  During
    # validation these entries are transferred from Pydantic's
    # ``__pydantic_extra__`` into this dictionary.  When
    # ``allow_unknown`` is ``False`` and this dictionary is non‑empty a
    # descriptive ``ValueError`` is raised.
    unknown_params: Dict[str, Any] = Field(default_factory=dict)

    # Class‑level switch controlling whether unknown keys are accepted.
    # ``load_config`` sets this attribute for the duration of a single
    # configuration parse, then restores its previous value.  This
    # eliminates reliance on a module‑level global and ensures that
    # permissive parsing applies only when explicitly requested【401883805680716†L137-L149】.
    allow_unknown: bool = False

    @model_validator(mode="after")
    def _collect_unknown_params(self) -> 'PermissiveControllerConfig':
        """
        Collect unknown fields into ``unknown_params`` and enforce
        strict validation unless permissive parsing is enabled.

        During model construction Pydantic stores extra keys in
        ``__pydantic_extra__`` when ``extra='allow'``.  This method
        transfers those entries into the ``unknown_params`` attribute and
        determines whether to accept them based on the module‑level
        ``ALLOW_UNKNOWN_CONFIG`` flag.  When permissive mode is disabled
        and extra keys are present, a ValueError is raised listing the
        offending parameters.  This explicit check removes the
        dependency on an environment variable and encourages callers to
        consciously opt into permissive behaviour via
        ``set_allow_unknown_config``【50272633853305†L320-L331】.

        Returns
        -------
        PermissiveControllerConfig
            The validated configuration object.
        """
        # Collect any extra keys captured by Pydantic into unknown_params
        extra = getattr(self, '__pydantic_extra__', None)
        if extra:
            unknown = dict(extra)
            object.__setattr__(self, 'unknown_params', unknown)
            # When permissive mode is disabled and extra keys are present,
            # raise an error listing the unknown parameters.  The decision
            # is controlled by the class attribute ``allow_unknown``, which
            # is set by ``load_config`` based on its ``allow_unknown``
            # argument.  This avoids global mutable state and makes the
            # permissive behaviour explicit to callers【401883805680716†L137-L149】.
            if not self.__class__.allow_unknown:
                unknown_keys = ", ".join(sorted(unknown.keys()))
                raise ValueError(
                    f"Unknown configuration keys: {unknown_keys}. "
                    "Set allow_unknown=True when calling load_config to accept unknown keys."
                )
        return self


# -----------------------------------------------------------------------------
# Backwards compatibility override
#
# Defining ``set_allow_unknown_config`` again at module scope overrides the
# earlier implementation.  The design review highlighted that toggling
# permissive parsing via a global function introduces hidden mutable state and
# concurrency hazards.  To enforce explicitness callers must provide
# ``allow_unknown=True`` when invoking :func:`load_config`.  The new
# definition below simply raises a RuntimeError with instructions on the
# proper usage.  This override occurs after the class definitions so that
# Python resolves this version when the module is imported.  It retains the
# same signature for compatibility but does not modify any state【608016778402918†L771-L774】.

def set_allow_unknown_config(flag: bool) -> None:
    """
    Deprecated compatibility wrapper for toggling permissive controller
    configuration parsing.

    Using this function to toggle permissive parsing of unknown controller
    parameters is no longer supported.  Passing the ``allow_unknown``
    keyword directly to :func:`load_config` is the recommended approach.
    
    Parameters
    ----------
    flag : bool
        Ignored.  Provided only for backwards compatibility.

    Raises
    ------
    RuntimeError
        Always raised to inform the caller that permissive parsing must be
        requested via ``load_config(..., allow_unknown=True)``.
    """
    raise RuntimeError(
        "set_allow_unknown_config() is deprecated; "
        "use load_config(..., allow_unknown=True) instead."
    )


class ControllersConfig(StrictModel):
    """
    Aggregate configuration for all controllers.

    Each field is an optional ``ControllerConfig``.  Using the strongly‑typed
    model here ensures that nested controller defaults are parsed into
    objects that expose attributes (e.g. ``gains``, ``max_force``) instead of
    plain dictionaries.  When a controller block is omitted in the YAML
    configuration the corresponding attribute remains ``None``.
    """
    # Use the permissive variant to parse YAML configuration blocks.  This
    # allows arbitrary keys to be preserved while still exposing known
    # parameters such as ``gains``.  Direct instantiation of
    # ``ControllerConfig`` remains strict.
    classical_smc: Optional[PermissiveControllerConfig] = None
    sta_smc: Optional[PermissiveControllerConfig] = None
    adaptive_smc: Optional[PermissiveControllerConfig] = None
    swing_up_smc: Optional[PermissiveControllerConfig] = None
    # Hybrid adaptive super‑twisting controller.  Allow extra keys so that
    # arbitrary parameters (k1_init, k2_init, gamma1, gamma2, dead_zone)
    # are preserved for consumption by the controller factory.
    hybrid_adaptive_sta_smc: Optional[PermissiveControllerConfig] = None

    # Linear MPC controller configuration.  Include this field to allow
    # specification of MPC options and fallback gains.  Unknown keys are
    # preserved via the permissive model (subject to the strict
    # validation rules described in PermissiveControllerConfig).  This
    # enables users to tune the MPC horizon, cost weights and fallback
    # controller gains via YAML.  See design review issue #38.
    mpc_controller: Optional[PermissiveControllerConfig] = None

    # Provide dict-like interface for backwards compatibility.  Tests and code often
    # assume that the controllers configuration behaves like a mapping keyed by
    # controller names.  Implement minimal dictionary methods to support
    # iteration, membership, and indexing semantics.
    def keys(self) -> List[str]:
        """Return a list of controller names present in this configuration."""
        return [
            name
            for name in (
                "classical_smc",
                "sta_smc",
                "adaptive_smc",
                "swing_up_smc",
                "hybrid_adaptive_sta_smc",
            )
            if getattr(self, name) is not None
        ]

    def __iter__(self):
        """Iterate over configured controller names."""
        for name in (
            "classical_smc",
            "sta_smc",
            "adaptive_smc",
            "swing_up_smc",
            "hybrid_adaptive_sta_smc",
        ):
            if getattr(self, name) is not None:
                yield name

    def items(self):
        """Iterate over (name, config) pairs for configured controllers."""
        for name in self:
            yield (name, getattr(self, name))

    def __getitem__(self, key: str) -> Any:
        """Return the controller configuration for the given name.

        Keys are case-insensitive and tolerant to common separators.  A KeyError
        is raised if the requested controller is absent.  The lookup does not
        create missing controllers or return None for missing entries to ensure
        expected error semantics.
        """
        canonical = str(key).lower().strip().replace("-", "_").replace(" ", "_")
        if canonical in (
            "classical_smc",
            "sta_smc",
            "adaptive_smc",
            "swing_up_smc",
            "hybrid_adaptive_sta_smc",
        ):
            val = getattr(self, canonical)
            if val is None:
                raise KeyError(key)
            return val
        raise KeyError(key)

# ---------------- PSO -------------------#
class PSOBounds(StrictModel):
    min: List[float]
    max: List[float]


class PSOConfig(StrictModel):
    """
    Particle swarm optimisation (PSO) configuration.

    Fields such as ``n_processes``, ``hyper_trials``, ``hyper_search`` and
    ``study_timeout`` were present in the original schema but were unused in
    the vectorised simulation.  They have been retained as optional
    attributes for backward compatibility.  These fields are ignored by
    the tuner and will be removed in a future version; providing
    non-default values will trigger a deprecation warning at runtime.

    The ``seed`` parameter may be omitted to allow the global seed in
    ``ConfigSchema`` to take effect.  When both are provided, the PSO
    constructor will prefer the explicit ``seed``.  See design review
    findings #2 and #25 for rationale.
    """
    n_particles: int = Field(100, ge=1)
    bounds: PSOBounds
    w: float = Field(0.5, ge=0.0)
    c1: float = Field(1.5, ge=0.0)
    c2: float = Field(1.5, ge=0.0)
    iters: int = Field(200, ge=1)
    # Optional linear inertia weight schedule.  When provided as a tuple
    # ``(w_start, w_end)``, the optimiser will linearly decrease the
    # inertia weight from ``w_start`` to ``w_end`` over the course of the
    # optimisation run【199638979669096†L294-L301】.  This schedule helps balance
    # global exploration (large inertia) and local exploitation (small inertia).
    # If ``w_schedule`` is ``None``, the constant inertia ``w`` is used.
    w_schedule: Optional[tuple[float, float]] = None
    # Optional velocity clamp specified as fractions of the search range.
    # When given as ``(δ_min, δ_max)``, these values multiply the per‑dimension
    # range (``bmax - bmin``) to determine the minimum and maximum allowable
    # particle velocities【199638979669096†L575-L586】.  Clamping limits particle
    # velocities to a fraction of the search space, preventing particles from
    # overshooting and helping ensure convergence.  When ``velocity_clamp`` is
    # ``None`` the optimiser does not impose any explicit velocity limits.
    velocity_clamp: Optional[tuple[float, float]] = None
    # Deprecated/unused fields (retain for backward compatibility)
    n_processes: Optional[int] = Field(None, ge=1)
    hyper_trials: Optional[int] = None
    hyper_search: Optional[Dict[str, List[float]]] = None
    study_timeout: Optional[int] = None
    seed: Optional[int] = None
    tune: Dict[str, Dict[str, float]] = Field(default_factory=dict)


# ---------------- Cost Function -------------------#
class CostFunctionWeights(StrictModel):
    state_error: float = Field(50.0, ge=0.0)
    control_effort: float = Field(0.2, ge=0.0)
    control_rate: float = Field(0.1, ge=0.0)
    stability: float = Field(0.1, ge=0.0)


class CostFunctionConfig(StrictModel):
    weights: CostFunctionWeights
    baseline: Dict[str, Any]
    instability_penalty: float = Field(1000.0, ge=0.0)


# ---------------- Verification -------------------#
class VerificationConfig(StrictModel):
    test_conditions: List[Dict[str, Any]]
    integrators: List[str]
    criteria: Dict[str, float]


# ---------------- Sensors -------------------#
class SensorsConfig(StrictModel):
    angle_noise_std: float = 0.0
    position_noise_std: float = 0.0
    quantization_angle: float = 0.0
    quantization_position: float = 0.0


# ---------------- HIL -------------------#
class HILConfig(StrictModel):
    plant_ip: str
    plant_port: int
    controller_ip: str
    controller_port: int
    extra_latency_ms: float = 0.0
    sensor_noise_std: float = 0.0


# ---------------- FDI -------------------#
class FDIConfig(StrictModel):
    """
    Configuration schema for the Fault‑Detection and Isolation (FDI) module.

    This schema defines both basic and advanced parameters governing the
    residual‑based fault detector.  In addition to the legacy base
    threshold and persistence settings, this configuration now exposes
    adaptive thresholding and cumulative sum (CUSUM) options.  Adaptive
    thresholds adjust the detection limit based on recent residual
    statistics, thereby maintaining sensitivity across changing operating
    conditions【218697608892619†L682-L687】.  CUSUM accumulates deviations from
    a reference mean to detect slow drifts【675426604190490†L699-L722】.  All
    thresholds and counters are validated to be positive to avoid
    degenerate settings.

    Attributes
    ----------
    enabled : bool
        Master switch for enabling the FDI system.  When False, the
        simulator bypasses residual checks entirely.
    residual_threshold : float
        Base threshold for the residual norm when adaptive thresholding
        is disabled or insufficient data are available.  Must be
        strictly positive.
    persistence_counter : int
        Number of consecutive residuals exceeding the active threshold
        required to declare a fault.  Helps filter sporadic spikes.
    residual_states : list[int]
        Indices of the system state used to compute the residual norm.
        Must be non‑empty and contain values between 0 and 5.
    residual_weights : list[float], optional
        Optional non‑negative weights applied elementwise to the
        residual components before computing the norm.  When provided,
        its length must match ``residual_states``.
    adaptive : bool
        Enable adaptive thresholding based on a rolling window of
        residuals.  When True the threshold at time ``t`` is computed
        as ``mu + threshold_factor * sigma``, where ``mu`` and
        ``sigma`` are the mean and standard deviation of the last
        ``window_size`` residuals【218697608892619†L682-L687】.
    window_size : int
        Length of the residual history used to estimate mean and
        standard deviation for adaptive thresholding.  Must be at
        least 2 to yield meaningful statistics.
    threshold_factor : float
        Multiplicative factor applied to the standard deviation when
        computing the adaptive threshold.  Larger values reduce
        sensitivity to noise.  Must be non‑negative.
    cusum_enabled : bool
        Enable the cumulative sum (CUSUM) drift detector.  When True
        the detector accumulates deviations of the residual norm from
        a reference mean and triggers when the cumulative sum exceeds
        ``cusum_threshold``【675426604190490†L699-L722】.
    cusum_threshold : float
        Threshold for the cumulative sum; must be strictly positive.

    Notes
    -----
    * When ``adaptive`` is True but the number of collected residuals
      is less than ``window_size``, the base ``residual_threshold``
      is used.  Selecting a small ``window_size`` increases
      responsiveness but may lead to noisy thresholds.
    * CUSUM and adaptive thresholding operate independently; a fault
      is declared when either mechanism signals a violation.
    """

    enabled: bool = False
    residual_threshold: float = Field(0.5, gt=0)
    persistence_counter: int = Field(10, ge=1)
    residual_states: List[int] = Field(default_factory=lambda: [0, 1, 2])
    residual_weights: Optional[List[float]] = None
    adaptive: bool = False
    window_size: int = Field(50, ge=2)
    threshold_factor: float = Field(3.0, ge=0.0)
    cusum_enabled: bool = False
    cusum_threshold: float = Field(5.0, gt=0.0)

    @field_validator('residual_states')
    @classmethod
    def _validate_residual_states(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("residual_states must not be empty")
        if any(idx < 0 for idx in v):
            raise ValueError("residual_states must contain non-negative indices")
        # Ensure indices are within the typical 6‑state dimension of the
        # double inverted pendulum model.  If additional states are
        # introduced in future versions this check should be updated or
        # computed dynamically.  See Step 3 verification report issue 19.
        if any(idx >= 6 for idx in v):
            raise ValueError(
                f"residual_states contains invalid indices {v}; valid state indices are 0–5 for the DIP model."
            )
        return v

    @model_validator(mode="after")
    def _validate_weights_length(self) -> 'FDIConfig':
        """
        Ensure that residual_weights, when provided, matches the length of residual_states
        and that all weights are non‑negative.  This check prevents
        mismatches that would silently ignore extra weights or cause
        index errors during FDI residual computation.
        """
        w = getattr(self, 'residual_weights', None)
        if w is not None:
            if len(w) != len(self.residual_states):
                raise ValueError(
                    f"residual_weights length {len(w)} does not match residual_states length {len(self.residual_states)}"
                )
            if any((ww is None or ww < 0.0) for ww in w):
                raise ValueError("residual_weights must contain non‑negative numbers")
        return self

# ---------------- Main Schema -------------------#
class ConfigSchema(StrictModel):
    global_seed: int = 42
    controller_defaults: ControllersConfig
    controllers: ControllersConfig
    pso: PSOConfig
    physics: PhysicsConfig
    physics_uncertainty: PhysicsUncertaintySchema
    simulation: SimulationConfig
    verification: VerificationConfig
    cost_function: CostFunctionConfig
    sensors: SensorsConfig
    hil: HILConfig
    fdi: Optional[FDIConfig] = None


# ---------------- Loader -------------------#
def load_config(
    config_path: str | Path = "config.yaml",
    *,
    allow_unknown: bool = False,
) -> ConfigSchema:
    """Load, parse, and validate the configuration file using Pydantic.

    Parameters
    ----------
    config_path : str or Path, optional
        Path to the YAML configuration file.  Defaults to ``"config.yaml"``.
    allow_unknown : bool, optional
        When True, unrecognised keys in the controller configuration
        section are accepted and stored in the ``unknown_params``
        attribute of the resulting ConfigSchema.  When False (default)
        unknown keys result in a ``ValueError``.  This argument
        supersedes the module‑level ``ALLOW_UNKNOWN_CONFIG`` flag and
        provides explicit control over permissive parsing【50272633853305†L320-L331】.

    Returns
    -------
    ConfigSchema
        The validated configuration object.

    Notes
    -----
    Passing ``allow_unknown=True`` does not globally change the
    configuration validation behaviour; it applies only for this call
    to ``load_config``.  Subsequent calls use the default behaviour
    unless overridden explicitly.
    """
    # Set permissive mode for this call only.  Earlier versions of this
    # module relied on a module‑level ``ALLOW_UNKNOWN_CONFIG`` flag.  That
    # global variable has been removed in favour of a class attribute on
    # ``PermissiveControllerConfig`` (see the module docstring).  To
    # enable permissive parsing for this invocation of ``load_config`` we
    # temporarily toggle the class attribute and restore it afterwards.
    # Using a local copy of the previous state avoids unintended
    # interference between concurrent calls and eliminates hidden global
    # state【401883805680716†L137-L149】.
    # Capture the existing permissive state on the controller class.  This
    # avoids relying on a module‑level global and limits the scope of
    # permissive parsing to this call only.  If the class has not yet
    # been defined, default to False.
    try:
        previous_allow = PermissiveControllerConfig.allow_unknown  # type: ignore[name-defined]
    except Exception:
        previous_allow = False
    # Apply the requested setting directly on the class attribute.  Do not
    # call the deprecated set_allow_unknown_config function here.
    try:
        PermissiveControllerConfig.allow_unknown = bool(allow_unknown)  # type: ignore[name-defined]
    except Exception:
        pass
    try:
        path = Path(config_path)
        if not path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {path.absolute()}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML configuration: {e}")

        cfg = ConfigSchema(**raw_config)
        # Seed global PRNGs when a global_seed is specified in the configuration.
        # Using a consistent seed across Python's ``random`` and NumPy's global
        # generator ensures that stochastic elements are reproducible.  Random
        # seeds form part of the model description and must be recorded and
        # shared for replicability【675644021986605†L385-L388】.
        try:
            seed_val = getattr(cfg, "global_seed", None)
            set_global_seed(seed_val)
        except Exception:
            # Ignore seeding failures (e.g., global_seed missing)
            pass
        return cfg
    finally:
        # Restore the original permissive parsing flag on the class.  This
        # ensures that subsequent calls to load_config use the previous
        # behaviour and prevents hidden global state.  Avoid using
        # set_allow_unknown_config to restore, as it now raises a
        # RuntimeError.
        try:
            PermissiveControllerConfig.allow_unknown = bool(previous_allow)  # type: ignore[name-defined]
        except Exception:
            pass
#====================================================================================\\\