# ///=================================================================================================================\\\
# ///======================================== src/controllers/factory.py =============================================\\\
# ///=================================================================================================================\\\

# Changed: Added handling for deprecated `use_equivalent` key by mapping it to
# `enable_equivalent`; updated allowed keys accordingly and passed equivalent
# control flags only when provided (F‑1.ConfigurationFlow.1 / RC‑03 / A‑02).

"""Controller factory with tolerant-import policy, guarded numeric validation, key checks,
and polished MPC typing / boundary-layer handling.

New in this version:
- MPC horizon must be an *integer* (no silent floor-casts). Non-integer values raise ConfigValueError.
- Boundary-layer validation DRY'ed across SMC branches via helpers.
"""
from typing import Optional, List, Any, Dict, Iterable, Callable
import math
import logging

# ---------- custom exceptions ----------
class ConfigValueError(ValueError):
    """Raised when a config value is out of the accepted range."""

class UnknownConfigKeyError(ValueError):
    """Raised when unexpected/unknown keys appear in a controller config block."""


# ---------- DRY import helper ----------
def _try_import(primary_mod: str, fallback_mod: str, attr: str):
    """
    Try importing ``attr`` from ``primary_mod`` then ``fallback_mod``.

    If neither import succeeds raise ``ImportError``.  Returning ``None``
    on failure was a source of latent bugs: downstream code would
    attempt to call methods on ``None`` and raise obscure attribute
    errors.  Failing fast with an ImportError surfaces misconfigured
    controller names at the point of import and encourages users to
    correct typos.  This change aligns with software engineering
    guidance to avoid hiding errors behind sentinel values.
    """
    try:
        mod = __import__(primary_mod, fromlist=[attr])
        return getattr(mod, attr)
    except Exception:
        try:
            mod = __import__(fallback_mod, fromlist=[attr])
            return getattr(mod, attr)
        except Exception as e:
            raise ImportError(
                f"Could not import {attr} from either '{primary_mod}' or '{fallback_mod}': {e!s}"
            )

# ---- tolerant imports (controllers) ----
# Prefer imports from the shallow ``controllers`` namespace (added to sys.path by tests)
# and fall back to ``src.controllers`` when unavailable.  This ensures that
# instances returned by the factory have the same module identity as classes
# imported in tests (e.g., ``from controllers.classic_smc import ClassicalSMC``).
ClassicalSMC     = _try_import("controllers.classic_smc",  "src.controllers.classic_smc",  "ClassicalSMC")
SuperTwistingSMC = _try_import("controllers.sta_smc",      "src.controllers.sta_smc",      "SuperTwistingSMC")
AdaptiveSMC      = _try_import("controllers.adaptive_smc", "src.controllers.adaptive_smc", "AdaptiveSMC")
SwingUpSMC       = _try_import("controllers.swing_up_smc", "src.controllers.swing_up_smc", "SwingUpSMC")
MPCController    = _try_import("controllers.mpc_controller","src.controllers.mpc_controller","MPCController")
MPCWeights       = _try_import("controllers.mpc_controller","src.controllers.mpc_controller","MPCWeights")

# Hybrid adaptive super‑twisting controller.  Attempt to import from the
# shallow ``controllers`` namespace first to align with test imports,
# and fall back to the fully qualified ``src.controllers`` module.
HybridAdaptiveSTASMC = _try_import(
    "controllers.hybrid_adaptive_sta_smc", "src.controllers.hybrid_adaptive_sta_smc", "HybridAdaptiveSTASMC"
)

# ---- tolerant imports (config) ----
# Prefer top‑level ``config`` and fall back to ``src.config`` to align with test
# import semantics.  These shims avoid importing heavy modules at load time.
ConfigSchema     = _try_import("config", "src.config", "ConfigSchema")
load_config      = _try_import("config", "src.config", "load_config")
PhysicsConfig    = _try_import("config", "src.config", "PhysicsConfig")

# ---- tolerant imports (dynamics) ----
# Use the same import preference for dynamics modules.  Tests that prepend
# ``src`` to ``sys.path`` will import ``core.dynamics`` rather than
# ``src.core.dynamics``, so attempt the shallow variant first.
DoubleInvertedPendulum = _try_import("core.dynamics",      "src.core.dynamics",      "DoubleInvertedPendulum")
FullDIPDynamics        = _try_import("core.dynamics_full", "src.core.dynamics_full", "FullDIPDynamics")


# -----------------------------------------------------------------------------
# Controller registry (Issue 8 resolution)
#
# A global registry allowing controllers to self‑register via a decorator.
# New controllers may register a constructor function without modifying
# this factory.  This pattern adheres to the open‑closed principle: the
# factory is open for extension (by adding new controllers via the
# decorator) but closed for modification.  The registry
# maps canonical controller names to callables that accept ``config``,
# ``gains`` and arbitrary keyword arguments and return a controller
# instance.  Registered builders are consulted before falling back to the
# built‑in if/elif ladder, preserving backward‑compatible behaviour.
import threading

# The registry itself and an accompanying lock to guard concurrent access.
# Without a lock, concurrent calls to register_controller could race,
# potentially overwriting or corrupting registry entries.  Using a lock
# ensures that only one thread can modify the registry at a time.  Read
# access (lookups) is unsynchronised as dictionary reads are atomic in
# CPython; however, acquiring the lock during registration prevents
# partial writes and upholds the interface contract of the factory.
# Treating the registry as a shared resource and enforcing mutual
# exclusion aligns with the general principle that shared data must be
# protected by locks to avoid race conditions; explicit contracts on
# shared data ensure deterministic behaviour.
CONTROLLER_REGISTRY: Dict[str, Callable[..., Any]] = {}
CONTROLLER_REGISTRY_LOCK = threading.Lock()

def register_controller(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for registering controller constructors.

    Parameters
    ----------
    name : str
        The canonical name of the controller.  Names are normalised to
        lower‑case and spaces/hyphens are replaced with underscores via
        ``_canonical``.

    Returns
    -------
    Callable
        A decorator that registers the decorated function in the
        ``CONTROLLER_REGISTRY``.

    Notes
    -----
    When a controller is registered, calls to :func:`create_controller`
    with the given name will dispatch to the registered builder instead
    of using the hard‑coded if/elif ladder.  This allows new controllers
    to be added without editing this factory, satisfying the
    open‑closed principle.  Existing controllers remain
    functional because the registry is checked before the legacy
    dispatch logic.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        key = _canonical(name)
        # Acquire the lock to ensure thread‑safe updates
        with CONTROLLER_REGISTRY_LOCK:
            CONTROLLER_REGISTRY[key] = func
        return func
    return decorator


# ---------- helpers ----------
def _canonical(name: str) -> str:
    return name.lower().strip().replace("-", "_").replace(" ", "_")


def _as_dict(obj) -> dict:
    """
    Robustly convert an arbitrary object into a plain ``dict``.

    This helper supports several types of inputs:

    * ``None`` returns an empty dictionary.
    * Instances of ``dict`` or mapping subclasses pass through unchanged.
    * Pydantic v2 models (with ``model_dump``) are dumped using
      ``model_dump(exclude_unset=True)``.
    * Pydantic v1 models (with ``dict``) are dumped using
      ``dict(exclude_unset=True)``.
    * Objects with a ``__dict__`` attribute are converted via ``dict(obj.__dict__)``.
    * As a last resort, ``dict(obj)`` is attempted, though this may still
      raise a ``TypeError`` if the object is not iterable.  In that case,
      an empty dictionary is returned.

    Parameters
    ----------
    obj : Any
        The object to convert.

    Returns
    -------
    dict
        A dictionary representation of ``obj``.
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(exclude_unset=True)  # type: ignore[attr-defined]
        except Exception:
            pass
    if hasattr(obj, "dict"):
        try:
            return obj.dict(exclude_unset=True)  # type: ignore[attr-defined]
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    try:
        return dict(obj)
    except Exception:
        return {}


def _get_default_gains(key: str, cfg, gains_override: Optional[List[float]]) -> List[float]:
    if gains_override is not None:
        return list(gains_override)
    # Only look up defaults from the top‑level controller_defaults section.
    # Do not attempt to infer gains from the controllers section, as this
    # can hide configuration mistakes and lead to inconsistent default
    # behaviour (see verification report issue #24).  If no defaults are
    # specified for the given controller and no override is provided,
    # raise a ConfigValueError instructing the user to supply gains.
    try:
        defaults_all = _as_dict(getattr(cfg, "controller_defaults", {}))
        defaults = defaults_all.get(key, None)
        if isinstance(defaults, dict) and "gains" in defaults:
            return list(defaults["gains"])
        if hasattr(defaults, "gains"):
            return list(defaults.gains)
    except Exception:
        pass
    raise ConfigValueError(
        f"No gains provided and no defaults found for '{key}'. "
        f"Please specify 'controller_defaults.{key}.gains' in config.yaml or pass gains explicitly."
    )


def _ensure_dynamics_available(use_full: bool):
    if use_full and FullDIPDynamics is None:
        raise ImportError(
            "FullDIPDynamics is unavailable. Ensure 'src/core/dynamics_full.py' is importable."
        )
    if (not use_full) and DoubleInvertedPendulum is None:
        raise ImportError(
            "DoubleInvertedPendulum is unavailable. Ensure 'src/core/dynamics.py' is importable."
        )


def _validate_shared_params(key: str, dt: float, max_force: float):
    if not (isinstance(dt, (int, float)) and math.isfinite(dt) and dt > 0):
        raise ConfigValueError(f"controllers.{key}.dt must be > 0 (got {dt})")
    if not (isinstance(max_force, (int, float)) and math.isfinite(max_force) and max_force > 0):
        raise ConfigValueError(f"controllers.{key}.max_force must be finite and > 0 (got {max_force})")


def _validate_boundary_layer(ctrl_key: str, value: float) -> float:
    bl = float(value)
    if bl <= 0.0:
        raise ConfigValueError(f"controllers.{ctrl_key}.boundary_layer must be > 0 (got {bl})")
    return bl


def _validate_switch_method(ctrl_key: str, val: object):
    """
    Accepts None|'tanh'|'linear'. Returns normalized method string or None.
    """
    if val is None:
        return None
    m = str(val).lower().strip()
    if m not in ("tanh", "linear"):
        raise ConfigValueError(
            f"controllers.{ctrl_key}.switch_method must be one of ['tanh','linear'] (got {val!r})"
        )
    return m


def _get_boundary_layer_or_default(ctrl_key: str, cfg: Dict, default_if_absent: float) -> float:
    if "boundary_layer" in cfg:
        return _validate_boundary_layer(ctrl_key, cfg["boundary_layer"])
    return float(default_if_absent)


def _validate_mpc_params(key: str, ctrl: Dict):
    # horizon: must be integer and >= 1
    if "horizon" in ctrl:
        hv = ctrl["horizon"]
        if not isinstance(hv, int):
            raise ConfigValueError(f"controllers.{key}.horizon must be an integer ≥ 1 (got {hv!r})")
        horizon = hv
        if horizon < 1:
            raise ConfigValueError(f"controllers.{key}.horizon must be ≥ 1 (got {horizon})")
    # geometry
    max_cart_pos = float(ctrl.get("max_cart_pos", 1.5))
    if not (math.isfinite(max_cart_pos) and max_cart_pos > 0):
        raise ConfigValueError(f"controllers.{key}.max_cart_pos must be > 0 (got {max_cart_pos})")
    # optional angle bound
    if "max_theta_dev" in ctrl:
        mtd = float(ctrl["max_theta_dev"])
        if not (math.isfinite(mtd) and mtd > 0):
            raise ConfigValueError(f"controllers.{key}.max_theta_dev must be > 0 when provided (got {mtd})")
    # weights if provided
    for wkey in ("q_x", "q_theta", "r_u"):
        if wkey in ctrl:
            val = float(ctrl[wkey])
            if val < 0:
                raise ConfigValueError(f"controllers.{key}.{wkey} must be ≥ 0 (got {val})")


def _validate_allowed_keys(key: str, provided: Dict, allowed: Iterable[str]):
    allowed_set = set(allowed)
    # gains are handled by _get_default_gains but permitted in block
    allowed_set.add("gains")
    unknown = sorted(k for k in provided.keys() if k not in allowed_set)
    if unknown:
        allowed_list = ", ".join(sorted(allowed_set))
        unknown_list = ", ".join(unknown)
        raise UnknownConfigKeyError(
            f"controllers.{key} has unknown config keys: {unknown_list}. Allowed keys: {allowed_list}"
        )


# ---------- factory ----------
def create_controller(
    ctrl_name: str,
    config: Optional[object] = None,
    gains: Optional[List[float]] = None,
    **override: Any,
) -> Any:
    # Load configuration on demand.  Tests may call this factory without
    # providing a full configuration object.  When a loader is available,
    # use it; otherwise default to ``None``.  The override parameters
    # supplied via **override take precedence over values in the config.
    if config is None:
        if load_config is None:
            raise RuntimeError("No configuration loader available. Provide 'config' explicitly.")
        config = load_config("config.yaml")

    key = _canonical(ctrl_name)

    # ------------------------------------------------------------------
    # Registry dispatch
    #
    # Before executing the legacy if/elif ladder we consult the global
    # CONTROLLER_REGISTRY for a matching builder.  This enables new
    # controllers to be added without modifying this function.  If a
    # builder is found it is called with the configuration object,
    # optional gains and any overrides.  Errors are propagated
    # naturally.  If no builder exists the legacy dispatch logic
    # continues below.
    # Acquire the registry lock before reading to avoid racing with registration
    with CONTROLLER_REGISTRY_LOCK:
        builder = CONTROLLER_REGISTRY.get(key)
    if builder is not None:
        return builder(config=config, gains=gains, **override)

    controllers_map: Dict[str, Any] = _as_dict(getattr(config, "controllers", {}))
    # Support legacy naming by aliasing ``classical_smc`` to ``classic_smc``.
    # When the canonicalised name ``classical_smc`` does not appear in the
    # controllers map but ``classic_smc`` does, reinterpret the key to
    # preserve backward compatibility.  This prevents a hard failure when
    # older configuration files or tests request ``classical_smc`` while
    # the configuration uses the shortened form.  See verification report
    # new issue detection for details.
    if key not in controllers_map and key == "classical_smc" and "classic_smc" in controllers_map:
        key = "classic_smc"
    # If the controller name is still unknown, raise a ValueError listing available keys.
    # Per test expectations, this branch must not import or touch heavy dependencies; it
    # simply introspects the configuration.  Note: do *not* call
    # ``_ensure_dynamics_available`` here because unknown names should not trigger
    # any dynamics checks.  See tests in ``test_factory_dynamics_consolidated.py``.
    if key not in controllers_map:
        available = "none configured" if len(controllers_map) == 0 else ", ".join(sorted(controllers_map.keys()))
        raise ValueError(
            f"Controller '{ctrl_name}' not found in config.controllers. Available: {available}"
        )

    # Determine whether full dynamics are requested from the simulation section of the
    # configuration.  Tests pass config objects with a nested ``simulation`` attribute
    # containing ``use_full_dynamics``.  When absent, default to False.  Perform this
    # lookup lazily so that unknown controller names (above) are handled before any
    # optional dependency checks.  Only after confirming a valid controller name do we
    # validate that the appropriate dynamics are available.  This ensures that heavy
    # imports do not occur when not needed.
    use_full = False
    try:
        sim_cfg = getattr(config, "simulation", None)
        if sim_cfg is not None:
            use_full = bool(getattr(sim_cfg, "use_full_dynamics", False))
    except Exception:
        # Default to lightweight dynamics when simulation config is malformed
        use_full = False

    # Check that the requested dynamics (full or lightweight) are available.  Raise
    # ImportError if the corresponding module could not be imported.  This guard
    # prevents tests from silently executing with missing dependencies.  See
    # ``test_factory_dynamics_consolidated.py``.
    _ensure_dynamics_available(use_full)

    # Start with the controller's configuration dictionary if present; otherwise
    # use an empty dict.  Convert via _as_dict to ensure plain dict.
    ctrl_cfg_obj = controllers_map.get(key, {})
    ctrl_cfg_dict: Dict[str, Any] = _as_dict(ctrl_cfg_obj)

    # Apply any overrides provided directly to this factory.  These
    # overrides (e.g., dt=0.01, max_force=10) take precedence over
    # values in the configuration file.  All override keys are treated
    # as part of the controller configuration for subsequent validation.
    for _k, _v in override.items():
        ctrl_cfg_dict[_k] = _v

    # Instantiate a dynamics model when controllers support equivalent control
    # or require physics.  Respect the ``use_full_dynamics`` flag from the
    # simulation configuration by selecting the appropriate model.  When
    # ``use_full`` is True, instantiate the high‑fidelity dynamics;
    # otherwise instantiate the simplified model.  Defer instantiation
    # until after key validation to avoid expensive imports on unknown
    # controller names.  See design review finding #13.
    dynamics_model: Any = None
    try:
        # Only attempt to build a dynamics model if the physics is available on
        # the configuration.  Some tests omit the physics attribute entirely.
        phys = getattr(config, "physics", None)
        if phys is not None:
            if use_full:
                # FullDIPDynamics may be unavailable; _ensure_dynamics_available
                # has already checked availability.  Instantiate with the
                # validated physics config to enforce Pydantic validation.
                dynamics_model = FullDIPDynamics(phys)
            else:
                dynamics_model = DoubleInvertedPendulum(phys)
    except Exception:
        # If instantiation fails (e.g., missing physics or invalid params),
        # fall back to None.  Controllers that rely on dynamics will
        # gracefully disable equivalent control when the model is absent.
        dynamics_model = None

    # Coerce YAML-ish numerics to float
    # Determine the shared time step and maximum force.  Prefer values from
    # overrides or the controller configuration; if absent, fall back to the
    # simulation configuration (dt) and a modest default for max_force.  This
    # behaviour is required by ``test_factory_dynamics_consolidated.py``, which
    # expects that ``simulation.dt`` propagates to controllers when no per‑
    # controller ``dt`` is specified.
    try:
        sim_cfg = getattr(config, "simulation", None)
        sim_dt = getattr(sim_cfg, "dt", None) if sim_cfg is not None else None
    except Exception:
        sim_dt = None
    # Compute shared dt and max_force.  When these values are not provided
    # explicitly in the controller configuration (or via overrides), fall
    # back to the simulation configuration or conservative defaults.  Emit
    # a warning to inform users that implicit inheritance has occurred
    # (design review issue #23).
    dt_in_cfg = "dt" in ctrl_cfg_dict
    mf_in_cfg = "max_force" in ctrl_cfg_dict
    if dt_in_cfg:
        shared_dt = float(ctrl_cfg_dict.get("dt"))
    else:
        # Use simulation dt if available, otherwise a conservative default
        shared_dt = float(sim_dt if sim_dt is not None else 0.01)
        logging.warning(
            f"controllers.{key}: no 'dt' specified; inheriting dt={shared_dt} from simulation configuration."
        )
    if mf_in_cfg:
        shared_max_force = float(ctrl_cfg_dict.get("max_force"))
    else:
        shared_max_force = 20.0
        logging.warning(
            f"controllers.{key}: no 'max_force' specified; using default max_force={shared_max_force}."
        )

    # Validate shared params early
    _validate_shared_params(key, shared_dt, shared_max_force)

    # -------- classical_smc --------
    if key == "classical_smc":
        if ClassicalSMC is None:
            raise ImportError(
                "Controller 'classical_smc' is unavailable (import error). Ensure required modules (and utils/control_primitives.py) are importable."
            )
        # Validate supplied keys.  Allow dt and max_force in the override; permit
        # 'use_adaptive_boundary' for backward compatibility even though it is
        # ignored by ClassicalSMC.
        _validate_allowed_keys(
            "classical_smc",
            ctrl_cfg_dict,
            allowed=(
                "dt",
                "max_force",
                "damping_gain",
                "boundary_layer",
                "switch_method",
                "regularization",
            ),
        )
        # Determine the boundary layer.  Use the value from the configuration if
        # provided; otherwise fall back to a conservative default of 0.01.  The
        # default aligns with sliding‑mode design guidelines and is used to
        # mitigate chattering when users do not specify an explicit
        # boundary‑layer thickness.
        boundary_layer = _get_boundary_layer_or_default("classical_smc", ctrl_cfg_dict, 0.01)
        switch_method = _validate_switch_method(
            "classical_smc", ctrl_cfg_dict.get("switch_method")
        )
        regularization = float(ctrl_cfg_dict.get("regularization", 1e-10))
        gains_to_use = _get_default_gains(key, config, gains)
        return ClassicalSMC(
            gains=gains_to_use,
            dynamics_model=dynamics_model,
            max_force=shared_max_force,
            boundary_layer=boundary_layer,
            regularization=regularization,
            **({"switch_method": switch_method} if switch_method else {}),
        )

    # -------- sta_smc --------
    if key == "sta_smc":
        if SuperTwistingSMC is None:
            raise ImportError(
                "Controller 'sta_smc' is unavailable (import error). Ensure required modules (and utils/control_primitives.py) are importable."
            )
        _validate_allowed_keys(
            key,
            ctrl_cfg_dict,
            allowed=(
                "dt",
                "max_force",
                "damping_gain",
                "boundary_layer",
                "switch_method",
                "regularization",
            ),
        )
        boundary_layer = _get_boundary_layer_or_default("sta_smc", ctrl_cfg_dict, 0.01)
        switch_method = _validate_switch_method(
            "sta_smc", ctrl_cfg_dict.get("switch_method")
        )
        regularization = float(ctrl_cfg_dict.get("regularization", 1e-10))
        gains_to_use = _get_default_gains(key, config, gains)
        return SuperTwistingSMC(
            gains=gains_to_use,
            dynamics_model=dynamics_model,
            max_force=shared_max_force,
            damping_gain=float(ctrl_cfg_dict.get("damping_gain", 0.0)),
            boundary_layer=boundary_layer,
            dt=shared_dt,
            regularization=regularization,
            **({"switch_method": switch_method} if switch_method else {}),
        )

    # -------- adaptive_smc --------
    if key == "adaptive_smc":
        if AdaptiveSMC is None:
            raise ImportError(
                "Controller 'adaptive_smc' is unavailable (import error). Ensure required modules (and utils/control_primitives.py) are importable."
            )
        allowed = {
            "dt",
            "max_force",
            "leak_rate",
            "dead_zone",
            "adapt_rate_limit",
            "K_min",
            "K_max",
            "smooth_switch",
            "boundary_layer",
            "K_init",
            "alpha",
        }
        _validate_allowed_keys(key, ctrl_cfg_dict, allowed=allowed)
        gains_to_use = _get_default_gains(key, config, gains)
        filtered: Dict[str, Any] = {k: v for k, v in ctrl_cfg_dict.items() if k in allowed}
        filtered.setdefault("dt", shared_dt)
        filtered.setdefault("max_force", shared_max_force)
        if "boundary_layer" in filtered:
            filtered["boundary_layer"] = _validate_boundary_layer(
                "adaptive_smc", filtered["boundary_layer"]
            )
        return AdaptiveSMC(gains=gains_to_use, **filtered)

    # -------- swing_up_smc --------
    if key == "swing_up_smc":
        if SwingUpSMC is None:
            raise ImportError(
                "Controller 'swing_up_smc' is unavailable (import error). Ensure required modules (and utils/control_primitives.py) are importable."
            )
        _validate_allowed_keys(
            key,
            ctrl_cfg_dict,
            allowed=(
                "dt",
                "max_force",
                "stabilizing_controller",
                "energy_gain",
                "switch_energy_factor",
                "exit_energy_factor",
                "switch_angle_tolerance",
                "reentry_angle_tolerance",
            ),
        )
        inner_name = ctrl_cfg_dict.get("stabilizing_controller", "classical_smc")
        if _canonical(inner_name) == "swing_up_smc":
            raise ConfigValueError(
                "swing_up_smc cannot use itself as stabilizing_controller."
            )
        # Recursively construct the stabilizer using the same overrides
        stabilizer = create_controller(inner_name, config=config, gains=None)
        max_force = float(
            ctrl_cfg_dict.get(
                "max_force", getattr(stabilizer, "max_force", shared_max_force)
            )
        )
        return SwingUpSMC(
            dynamics_model=dynamics_model,
            stabilizing_controller=stabilizer,
            energy_gain=float(ctrl_cfg_dict.get("energy_gain", 50.0)),
            switch_energy_factor=float(ctrl_cfg_dict.get("switch_energy_factor", 0.95)),
            exit_energy_factor=float(ctrl_cfg_dict.get("exit_energy_factor", 0.90)),
            switch_angle_tolerance=float(ctrl_cfg_dict.get("switch_angle_tolerance", 0.35)),
            reentry_angle_tolerance=float(
                ctrl_cfg_dict.get(
                    "reentry_angle_tolerance",
                    ctrl_cfg_dict.get("switch_angle_tolerance", 0.35),
                )
            ),
            dt=shared_dt,
            max_force=max_force,
        )

    # -------- hybrid_adaptive_sta_smc --------
    if key == "hybrid_adaptive_sta_smc":
        # Ensure the hybrid adaptive controller is importable.  When
        # optional dependencies are missing the import helper returns
        # None, prompting an informative ImportError.
        if HybridAdaptiveSTASMC is None:
            raise ImportError(
                "Controller 'hybrid_adaptive_sta_smc' is unavailable (import error)."
                " Ensure that 'src/controllers/hybrid_adaptive_sta_smc.py' exists and is importable."
            )
        # Validate allowed keys.  Gains are handled separately via
        # _get_default_gains; the remaining parameters correspond to
        # the controller's constructor arguments.  Unknown keys will
        # produce a clear error message.
        _validate_allowed_keys(
            key,
            ctrl_cfg_dict,
            allowed=(
                "dt",
                "max_force",
                "k1_init",
                "k2_init",
                "gamma1",
                "gamma2",
                "dead_zone",
                # expose optional knobs for tuning
                "use_equivalent",
                "enable_equivalent",
                "damping_gain",
                "adapt_rate_limit",
                "sat_soft_width",
                "cart_gain",
                "cart_lambda",
                "cart_p_gain",
                "cart_p_lambda",
            ),
        )
        # Retrieve sliding surface gains from defaults or overrides.
        gains_to_use = _get_default_gains(key, config, gains)
        # Pull configuration values for the controller.  Use defaults
        # when values are omitted; dt and max_force fall back to
        # shared_dt and shared_max_force computed earlier.
        filtered: Dict[str, Any] = {
            k: v
            for k, v in ctrl_cfg_dict.items()
            if k in {
                "dt",
                "max_force",
                "k1_init",
                "k2_init",
                "gamma1",
                "gamma2",
                "dead_zone",
                "use_equivalent",
                "enable_equivalent",
                "damping_gain",
                "adapt_rate_limit",
                "sat_soft_width",
                "cart_gain",
                "cart_lambda",
                "cart_p_gain",
                "cart_p_lambda",
            }
        }
        filtered.setdefault("dt", shared_dt)
        filtered.setdefault("max_force", shared_max_force)
        # Instantiate the controller with all provided parameters, casting
        # numerics to float.  Missing adaptation parameters default to
        # sensible values (e.g., 0.0 for k1_init).
        # Determine which flag controls the equivalent control term.  The
        # preferred key ``enable_equivalent`` takes precedence; the legacy
        # alias ``use_equivalent`` is still accepted for backward
        # compatibility.  Pass only the keys provided to avoid confusion.
        eq_kwargs: Dict[str, Any] = {}
        if "enable_equivalent" in filtered:
            eq_kwargs["enable_equivalent"] = bool(filtered["enable_equivalent"])
        if "use_equivalent" in filtered:
            eq_kwargs["use_equivalent"] = bool(filtered["use_equivalent"])
        return HybridAdaptiveSTASMC(
            gains=gains_to_use,
            dt=float(filtered.get("dt", shared_dt)),
            max_force=float(filtered.get("max_force", shared_max_force)),
            k1_init=float(filtered.get("k1_init", 0.0)),
            k2_init=float(filtered.get("k2_init", 0.0)),
            gamma1=float(filtered.get("gamma1", 0.0)),
            gamma2=float(filtered.get("gamma2", 0.0)),
            dead_zone=float(filtered.get("dead_zone", 0.0)),
            damping_gain=float(filtered.get("damping_gain", 3.0)),
            adapt_rate_limit=float(filtered.get("adapt_rate_limit", 5.0)),
            sat_soft_width=float(filtered.get("sat_soft_width", 0.03)),
            cart_gain=float(filtered.get("cart_gain", 0.5)),
            cart_lambda=float(filtered.get("cart_lambda", 1.0)),
            cart_p_gain=float(filtered.get("cart_p_gain", 80.0)),
            cart_p_lambda=float(filtered.get("cart_p_lambda", 2.0)),
            dynamics_model=dynamics_model,
            **eq_kwargs,
        )

    # -------- mpc_controller --------
    if key == "mpc_controller":
        if MPCController is None:
            raise ImportError(
                "Controller 'mpc_controller' is unavailable (missing optional dependency)."
            )
        _validate_allowed_keys(
            key,
            ctrl_cfg_dict,
            allowed=(
                "dt",
                "max_force",
                "horizon",
                "q_x",
                "q_theta",
                "r_u",
                "max_theta_dev",
                "max_cart_pos",
                # Expose fallback controller parameters.  Users can
                # specify fallback gains for the SMC or PD controllers
                # used when the MPC solver fails.  See design review
                # issue #38.
                "fallback_smc_gains",
                "fallback_pd_kp",
                "fallback_pd_kd",
            ),
        )
        _validate_mpc_params(key, ctrl_cfg_dict)
        # Build a minimal dummy dynamics model for prediction.  When cvxpy is
        # unavailable the MPC controller will fall back to a linear policy
        # that does not depend on the dynamics.  This dummy supplies the
        # attributes expected by the fallback but otherwise does nothing.
        class _DummyDyn:
            def __init__(self):
                self.state_dim = 6
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                return np.asarray(state, dtype=float)
            def f(self, x: np.ndarray, u: float) -> np.ndarray:
                return np.zeros_like(x)
            continuous_dynamics = f

        prediction_model = _DummyDyn()
        q_x = ctrl_cfg_dict.get("q_x")
        q_theta = ctrl_cfg_dict.get("q_theta")
        r_u = ctrl_cfg_dict.get("r_u")
        if any(v is not None for v in (q_x, q_theta, r_u)):
            weight_kwargs: Dict[str, float] = {}
            if q_x is not None:
                weight_kwargs["q_x"] = float(q_x)
            if q_theta is not None:
                weight_kwargs["q_theta"] = float(q_theta)
            if r_u is not None:
                weight_kwargs["r_u"] = float(r_u)
            weights = MPCWeights(**weight_kwargs)
        else:
            weights = None
        theta_dev = ctrl_cfg_dict.get("max_theta_dev", None)
        mpc_kwargs: Dict[str, Any] = {
            "dynamics_model": prediction_model,
            "horizon": int(ctrl_cfg_dict.get("horizon", 20)),
            "dt": float(shared_dt),
            "max_force": float(shared_max_force),
            "weights": weights,
            "max_cart_pos": float(ctrl_cfg_dict.get("max_cart_pos", 1.5)),
        }
        if theta_dev is not None:
            mpc_kwargs["max_theta_dev"] = float(theta_dev)
        # Pass fallback controller gains to MPCController.  When
        # provided these values override the internal defaults used
        # when the QP solver fails.  The SMC fallback expects a list
        # of six gains.  The PD fallback expects scalar gains kp and
        # kd.  Non‑numeric entries are ignored and default values are
        # used instead.
        fb_smc = ctrl_cfg_dict.get("fallback_smc_gains", None)
        if fb_smc is not None:
            try:
                mpc_kwargs["fallback_smc_gains"] = [float(x) for x in fb_smc]
            except Exception:
                logging.warning(
                    f"controllers.{key}: fallback_smc_gains must be a sequence of floats; ignoring provided value {fb_smc!r}."
                )
        fb_kp = ctrl_cfg_dict.get("fallback_pd_kp", None)
        fb_kd = ctrl_cfg_dict.get("fallback_pd_kd", None)
        if fb_kp is not None and fb_kd is not None:
            try:
                mpc_kwargs["fallback_pd_gains"] = (float(fb_kp), float(fb_kd))
            except Exception:
                logging.warning(
                    f"controllers.{key}: fallback_pd_kp/kd must be numeric; using default PD gains."
                )
        return MPCController(**mpc_kwargs)

    raise ValueError(f"Controller '{ctrl_name}' is not a recognized type.")