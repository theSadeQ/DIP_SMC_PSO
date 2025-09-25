#==========================================================================================\\\
#================================ src/controllers/factory.py ==============================\\\
#==========================================================================================\\\

"""Controller factory with Pydantic v2 config alignment and robust error handling."""

from typing import Optional, List, Any, Dict, Callable, Union, Type, Mapping

# Exported public API
__all__ = [
    "build_controller",
    "build_all",
    "create_controller",
    "_canonical",
    "normalize_controller_name",
    "apply_deprecation_mapping",
    "register_controller",
    "FactoryConfigurationError",
    "ConfigValueError",
    "UnknownConfigKeyError"
]
import numpy as np
import math
import logging
import warnings
import threading
from collections.abc import MutableMapping
# --- module logger (module-level; safe even if logging configured elsewhere) ---
logger = logging.getLogger("project.factory")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.INFO)
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

# ---------- custom exceptions ----------
class FactoryConfigurationError(Exception):
    """Raised when controller configuration or resolution fails."""
    pass

class ConfigValueError(ValueError):
    """Raised when a config value is out of the accepted range."""
    pass

class UnknownConfigKeyError(ValueError):
    """Raised when unexpected/unknown keys appear in a controller config block."""
    pass

# --- module logger (module-level; safe if configured elsewhere) ---
logger = logging.getLogger("project.factory")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.INFO)
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

# ---------- Controller Registry ----------
CONTROLLER_REGISTRY: Dict[str, Type[Any]] = {}
CONTROLLER_REGISTRY_LOCK = threading.Lock()

# ---------- Normalization Maps ----------
# Controller name aliases (normalized -> canonical)
ALIAS_MAP: Dict[str, str] = {
    "smc_v1": "classical_smc",
    "classic_smc": "classical_smc",  # Allow both forms
    "smc_classic": "classical_smc",
    "sta": "sta_smc",
    "super_twisting": "sta_smc",
    "adaptive": "adaptive_smc",
    "swing_up": "swing_up_smc",
    "hybrid": "hybrid_adaptive_sta_smc",
    "hybrid_sta": "hybrid_adaptive_sta_smc",
    "mpc": "mpc_controller",
}

# Deprecated parameter mappings per controller
DEPRECATED_PARAM_MAP: Dict[str, Dict[str, str]] = {
    "classical_smc": {
        "boundaryLayer": "boundary_layer",
        "boundary-layer": "boundary_layer",
        "maxForce": "max_force",
        "max-force": "max_force",
        "dampingGain": "damping_gain",
        "damping-gain": "damping_gain",
        "switchMethod": "switch_method",
        "switch-method": "switch_method",
    },
    "sta_smc": {
        "boundaryLayer": "boundary_layer",
        "boundary-layer": "boundary_layer",
        "maxForce": "max_force",
        "max-force": "max_force",
        "dampingGain": "damping_gain",
        "damping-gain": "damping_gain",
        "switchMethod": "switch_method",
        "switch-method": "switch_method",
        "antiWindupGain": "anti_windup_gain",
        "anti-windup-gain": "anti_windup_gain",
    },
    "adaptive_smc": {
        "maxForce": "max_force",
        "max-force": "max_force",
        "leakRate": "leak_rate",
        "leak-rate": "leak_rate",
        "deadZone": "dead_zone",
        "dead-zone": "dead_zone",
        "adaptRateLimit": "adapt_rate_limit",
        "adapt-rate-limit": "adapt_rate_limit",
        "smoothSwitch": "smooth_switch",
        "smooth-switch": "smooth_switch",
        "boundaryLayer": "boundary_layer",
        "boundary-layer": "boundary_layer",
        "k_min": "K_min",  # normalized lowercase to uppercase
        "k_max": "K_max",  # normalized lowercase to uppercase
        "k_init": "K_init",  # normalized lowercase to uppercase
    },
    "hybrid_adaptive_sta_smc": {
        "use_equivalent": "enable_equivalent",  # Special deprecated alias
        "useEquivalent": "enable_equivalent",
        "maxForce": "max_force",
        "max-force": "max_force",
        "dampingGain": "damping_gain",
        "damping-gain": "damping_gain",
        "adaptRateLimit": "adapt_rate_limit",
        "adapt-rate-limit": "adapt_rate_limit",
        "satSoftWidth": "sat_soft_width",
        "sat-soft-width": "sat_soft_width",
        "cartGain": "cart_gain",
        "cart-gain": "cart_gain",
        "cartLambda": "cart_lambda",
        "cart-lambda": "cart_lambda",
    },
    "mpc_controller": {
        "maxForce": "max_force",
        "max-force": "max_force",
        "maxCartPos": "max_cart_pos",
        "max-cart-pos": "max_cart_pos",
        "maxThetaDev": "max_theta_dev",
        "max-theta-dev": "max_theta_dev",
        "fallbackSmcGains": "fallback_smc_gains",
        "fallback-smc-gains": "fallback_smc_gains",
        "fallbackPdKp": "fallback_pd_kp",
        "fallback-pd-kp": "fallback_pd_kp",
        "fallbackPdKd": "fallback_pd_kd",
        "fallback-pd-kd": "fallback_pd_kd",
    },
    "swing_up_smc": {
        "stabilizingController": "stabilizing_controller",
        "stabilizing-controller": "stabilizing_controller",
        "energyGain": "energy_gain",
        "energy-gain": "energy_gain",
        "switchEnergyFactor": "switch_energy_factor",
        "switch-energy-factor": "switch_energy_factor",
        "exitEnergyFactor": "exit_energy_factor",
        "exit-energy-factor": "exit_energy_factor",
        "switchAngleTolerance": "switch_angle_tolerance",
        "switch-angle-tolerance": "switch_angle_tolerance",
        "reentryAngleTolerance": "reentry_angle_tolerance",
        "reentry-angle-tolerance": "reentry_angle_tolerance",
        "maxForce": "max_force",
        "max-force": "max_force",
    },
}

# ---------- DRY import helper ----------
def _try_import(primary_mod: str, fallback_mod: str, attr: str):
    """Try importing ``attr`` from ``primary_mod`` then ``fallback_mod``."""
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
ClassicalSMC = _try_import("src.controllers.smc.classic_smc", "controllers.smc.classic_smc", "ClassicalSMC")
SuperTwistingSMC = _try_import("src.controllers.smc.sta_smc", "controllers.smc.sta_smc", "SuperTwistingSMC")
AdaptiveSMC = _try_import("src.controllers.smc.adaptive_smc", "controllers.smc.adaptive_smc", "AdaptiveSMC")
SwingUpSMC = _try_import("src.controllers.specialized.swing_up_smc", "controllers.specialized.swing_up_smc", "SwingUpSMC")
MPCController = _try_import("src.controllers.mpc.mpc_controller", "controllers.mpc.mpc_controller", "MPCController")
MPCWeights = _try_import("src.controllers.mpc.mpc_controller", "controllers.mpc.mpc_controller", "MPCWeights")
HybridAdaptiveSTASMC = _try_import(
    "src.controllers.smc.hybrid_adaptive_sta_smc", "controllers.smc.hybrid_adaptive_sta_smc", "HybridAdaptiveSTASMC"
)

# ---- tolerant imports (config) ----
ConfigSchema = _try_import("config", "src.config", "ConfigSchema")
load_config = _try_import("config", "src.config", "load_config")
PhysicsConfig = _try_import("config", "src.config", "PhysicsConfig")

# ---- tolerant imports (dynamics) ----
DoubleInvertedPendulum = _try_import("src.core.dynamics", "core.dynamics", "DoubleInvertedPendulum")
FullDIPDynamics = _try_import("src.core.dynamics_full", "core.dynamics_full", "FullDIPDynamics")

# ---- utilities ----
try:
    from src.utils import set_global_seed
except ImportError:
    def set_global_seed(seed: int) -> None:
        """Fallback when seed utility is unavailable."""
        import random
        import numpy as np
        random.seed(seed)
        np.random.seed(seed)
        logger.debug(f"Set global seed to {seed}")

# ---------- Normalization Functions ----------
def normalize_controller_name(name: str) -> str:
    """
    Normalize controller name and apply aliases.
    
    Lowercase, trim, replace hyphens/spaces/dots with underscores,
    then check alias map.
    """
    if not name:
        return ""
    
    # Basic normalization
    normalized = name.lower().strip()
    for char in ["-", " ", "."]:
        normalized = normalized.replace(char, "_")
    
    # Apply alias mapping
    canonical = ALIAS_MAP.get(normalized, normalized)
    
    if normalized != canonical:
        logger.debug(f"Controller name '{name}' normalized to '{canonical}' via alias")
    elif name != normalized:
        logger.debug(f"Controller name '{name}' normalized to '{normalized}'")
    
    return canonical

def normalize_param_key(key: str) -> str:
    """Normalize parameter key: lowercase, replace hyphens/spaces with underscores."""
    if not key:
        return ""
    # Special case: preserve capitalization for K_ parameters
    if key.startswith('K_'):
        normalized = key.strip()
        for char in ["-", " "]:
            normalized = normalized.replace(char, "_")
        return normalized
    normalized = key.lower().strip()
    for char in ["-", " "]:
        normalized = normalized.replace(char, "_")
    return normalized

def apply_deprecation_mapping(
    controller_name: str, 
    params: Dict[str, Any], 
    allow_unknown: bool = False
) -> Dict[str, Any]:
    """
    Apply deprecation mapping for a controller's parameters.
    
    Returns normalized params dict with deprecated keys mapped to current ones.
    Emits DeprecationWarning for each deprecated key found.
    """
    deprecation_map = DEPRECATED_PARAM_MAP.get(controller_name, {})
    normalized_params = {}
    unknown_params = {}
    
    # Track which normalized keys we've seen to detect collisions
    seen_normalized = {}
    
    for original_key, value in params.items():
        # First normalize the key
        norm_key = normalize_param_key(original_key)
        
        # Check for deprecation (use original key for deprecation lookup)
        if original_key in deprecation_map:
            new_key = deprecation_map[original_key]
            # Only apply deprecation if the new key isn't already set
            if new_key not in params and new_key not in normalized_params:
                warnings.warn(
                    f"Parameter '{original_key}' is deprecated for {controller_name}. "
                    f"Please use '{new_key}' instead.",
                    DeprecationWarning,
                    stacklevel=3
                )
                logger.debug(f"Mapped deprecated param '{original_key}' -> '{new_key}' for {controller_name}")
                norm_key = new_key
            else:
                # New key already set, skip the deprecated one
                logger.debug(f"Skipping deprecated param '{original_key}' as '{new_key}' is already set")
                continue
        # Also check normalized form in deprecation map
        elif norm_key in deprecation_map:
            new_key = deprecation_map[norm_key]
            if new_key not in params and new_key not in normalized_params:
                warnings.warn(
                    f"Parameter '{original_key}' (normalized: '{norm_key}') is deprecated for {controller_name}. "
                    f"Please use '{new_key}' instead.",
                    DeprecationWarning,
                    stacklevel=3
                )
                logger.debug(f"Mapped deprecated param '{norm_key}' -> '{new_key}' for {controller_name}")
                norm_key = new_key
            else:
                continue
        
        # Check for key collision after normalization
        if norm_key in seen_normalized and seen_normalized[norm_key] != original_key:
            raise FactoryConfigurationError(
                f"controllers.{controller_name}: Parameter keys '{seen_normalized[norm_key]}' "
                f"and '{original_key}' both normalize to '{norm_key}'"
            )
        
        seen_normalized[norm_key] = original_key
        normalized_params[norm_key] = value
    
    return normalized_params

def redact_value(value: Any) -> str:
    """Redact sensitive values for logging."""
    if value is None:
        return "None"
    value_str = str(value).lower()
    if any(keyword in value_str for keyword in ["password", "secret", "token", "key", "api"]):
        return "***"
    # Also redact if the key name suggests sensitivity
    return str(value)[:50] + "..." if len(str(value)) > 50 else str(value)

# ---------- Registry Functions ----------
def register_controller(name: str) -> Callable[[Type[Any]], Type[Any]]:
    """
    Decorator for registering controller constructors.
    
    Registration is idempotent - re-registering the same name overwrites.
    """
    def decorator(cls: Type[Any]) -> Type[Any]:
        normalized_name = normalize_controller_name(name)
        with CONTROLLER_REGISTRY_LOCK:
            CONTROLLER_REGISTRY[normalized_name] = cls
            logger.info(f"Registered controller '{normalized_name}' -> {cls.__name__}")
        return cls
    return decorator

# ---------- Helper Functions ----------
def _as_dict(obj: Any) -> Dict[str, Any]:
    """Robustly convert an arbitrary object into a plain dict."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(exclude_unset=True)
        except Exception:
            pass
    if hasattr(obj, "dict"):
        try:
            return obj.dict(exclude_unset=True)
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    try:
        return dict(obj)
    except Exception:
        return {}

def _get_default_gains(controller_name: str, config: Any, gains_override: Optional[List[float]]) -> List[float]:
    """Get gains from override, defaults, or raise error."""
    if gains_override is not None:
        return list(gains_override)
    
    try:
        defaults_all = _as_dict(getattr(config, "controller_defaults", {}))
        defaults = defaults_all.get(controller_name, None)
        if isinstance(defaults, dict) and "gains" in defaults:
            return list(defaults["gains"])
        if hasattr(defaults, "gains"):
            return list(defaults.gains)
    except Exception:
        pass
    
    raise FactoryConfigurationError(
        f"controllers.{controller_name}.gains: No gains provided and no defaults found. "
        f"Please specify 'controller_defaults.{controller_name}.gains' in config or pass gains explicitly."
    )

def _ensure_dynamics_available(use_full: bool) -> None:
    """Ensure required dynamics model is available."""
    if use_full and FullDIPDynamics is None:
        raise ImportError(
            "FullDIPDynamics is unavailable. Ensure 'src/core/dynamics_full.py' is importable."
        )
    if (not use_full) and DoubleInvertedPendulum is None:
        raise ImportError(
            "DoubleInvertedPendulum is unavailable. Ensure 'src/core/dynamics.py' is importable."
        )

import numbers
def _validate_shared_params(controller_name: str, dt: float, max_force: float) -> None:
    """Validate common parameters shared by controllers."""
    if not (isinstance(dt, numbers.Real) and math.isfinite(float(dt)) and dt > 0):
        raise ConfigValueError(f"controllers.{controller_name}.dt must be > 0 (got {dt})")
    if not (isinstance(max_force, numbers.Real) and math.isfinite(float(max_force)) and max_force > 0):
        raise ConfigValueError(f"controllers.{controller_name}.max_force must be finite and > 0 (got {max_force})")

# ---------- Main Factory Functions ----------
def build_controller(
    name: str,
    cfg: Union[Dict[str, Any], Mapping[str, Any], Any],
    *,
    allow_unknown: bool = False,
    config: Optional[Any] = None,  # For backward compat with create_controller
    gains: Optional[List[float]] = None
) -> Any:
    """
    Build a single controller from configuration.
    
    Parameters
    ----------
    name : str
        Controller name (will be normalized and aliased).
    cfg : dict or Mapping or ControllerConfig
        Controller-specific configuration.
    allow_unknown : bool
        If True, unknown parameters are stored as unknown_params on the instance.
        If False, unknown parameters raise FactoryConfigurationError.
    config : optional
        Full configuration object (for backward compatibility).
    gains : optional
        Explicit gains override.
    
    Returns
    -------
    Controller instance
    
    Raises
    ------
    FactoryConfigurationError
        If controller name is unknown or configuration is invalid.
    """
    # Normalize controller name
    controller_name = normalize_controller_name(name)
    
    # Check registry first
    with CONTROLLER_REGISTRY_LOCK:
        if controller_name in CONTROLLER_REGISTRY:
            controller_class = CONTROLLER_REGISTRY[controller_name]
            logger.info(f"Building controller '{controller_name}' from registry")
            
            # Convert config to dict
            cfg_dict = _as_dict(cfg)
            
            # Apply normalization and deprecation
            normalized_cfg = apply_deprecation_mapping(controller_name, cfg_dict, allow_unknown)
            
            # Handle gains
            if gains is not None:
                normalized_cfg["gains"] = gains
            elif "gains" not in normalized_cfg and config is not None:
                try:
                    normalized_cfg["gains"] = _get_default_gains(controller_name, config, None)
                except Exception:
                    pass  # Let the controller handle missing gains
            
            # Try from_config method first, then constructor
            try:
                if hasattr(controller_class, "from_config"):
                    # If permissive, pass through as-is; from_config should decide.
                    instance = controller_class.from_config(normalized_cfg)
                else:
                    # In permissive mode, filter kwargs by the constructor signature.
                    if allow_unknown:
                        import inspect
                        sig = inspect.signature(controller_class)
                        valid = {p.name for p in sig.parameters.values()
                                 if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)}
                        filtered = {k: v for k, v in normalized_cfg.items() if k in valid}
                        unknown = {k: v for k, v in normalized_cfg.items() if k not in valid}
                        instance = controller_class(**filtered)
                        if unknown:
                            instance.unknown_params = {**getattr(instance, "unknown_params", {}), **unknown}
                    else:
                        instance = controller_class(**normalized_cfg)
                
                # Store unknown params if in permissive mode
                if allow_unknown and hasattr(cfg, "unknown_params"):
                    instance.unknown_params = cfg.unknown_params
                
                logger.info(f"Successfully built controller '{controller_name}'")
                return instance
                
            except (TypeError, ValueError) as e:
                # Wrap with dot-path
                error_msg = str(e)
                if "unexpected keyword argument" in error_msg:
                    import re
                    match = re.search(r"'(\w+)'", error_msg)
                    if match:
                        unknown_key = match.group(1)
                        raise FactoryConfigurationError(
                            f"controllers.{controller_name}.{unknown_key}: Unknown parameter. "
                            f"Error: {error_msg}"
                        )
                raise FactoryConfigurationError(
                    f"controllers.{controller_name}: Failed to construct. Error: {error_msg}"
                )
    
    # Fall back to legacy create_controller for backward compatibility
    logger.debug(f"Controller '{controller_name}' not in registry, trying legacy construction")
    return _legacy_create_controller(name, cfg, config, gains, allow_unknown)

def build_all(
    controllers_cfg: Union[Dict[str, Any], Any],
    *,
    allow_unknown: bool = False,
    config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Build all controllers from a ControllersConfig.
    
    Parameters
    ----------
    controllers_cfg : ControllersConfig or dict
        Configuration for all controllers.
    allow_unknown : bool
        If True, unknown parameters are stored on instances.
        If False, unknown parameters raise errors.
    config : optional
        Full configuration object for defaults.
    
    Returns
    -------
    dict[str, Controller]
        Mapping of controller names to instances.
    
    Raises
    ------
    FactoryConfigurationError
        If any controller fails to build (aggregates all errors).
    """
    built_controllers = {}
    errors = []
    
    # Handle different config types
    if hasattr(controllers_cfg, "items"):
        items = controllers_cfg.items()
    elif hasattr(controllers_cfg, "keys"):
        items = [(k, getattr(controllers_cfg, k)) for k in controllers_cfg.keys()]
    else:
        items = _as_dict(controllers_cfg).items()
    
    for name, controller_cfg in items:
        try:
            controller = build_controller(
                name, 
                controller_cfg, 
                allow_unknown=allow_unknown,
                config=config
            )
            built_controllers[name] = controller
        except Exception as e:
            errors.append(f"controllers.{name}: {str(e)}")
    
    if errors:
        raise FactoryConfigurationError(
            "Failed to build controllers:\n" + "\n".join(errors)
        )
    
    logger.info(f"Successfully built {len(built_controllers)} controllers: {list(built_controllers.keys())}")
    return built_controllers

# ---------- Legacy Support ----------
def _legacy_create_controller(
    ctrl_name: str,
    ctrl_cfg: Any,
    config: Optional[Any],
    gains: Optional[List[float]],
    allow_unknown: bool
) -> Any:
    """Legacy controller creation for backward compatibility."""
    # Load config if needed
    if config is None:
        if load_config is None:
            raise RuntimeError("No configuration loader available. Provide 'config' explicitly.")
        config = load_config("config.yaml")
    
    # Handle global seed if present
    try:
        if hasattr(config, "global_seed") and config.global_seed is not None:
            set_global_seed(config.global_seed)
            logger.debug(f"Set global seed to {config.global_seed}")
    except Exception as e:
        logger.debug(f"Could not set global seed: {e}")
    
    key = normalize_controller_name(ctrl_name)
    
    # Get controllers from config
    controllers_map = _as_dict(getattr(config, "controllers", {}))
    
    # Legacy classical_smc aliasing
    if key not in controllers_map and key == "classical_smc" and "classic_smc" in controllers_map:
        key = "classic_smc"
    
    if key not in controllers_map:
        available = "none configured" if len(controllers_map) == 0 else ", ".join(sorted(controllers_map.keys()))
        raise FactoryConfigurationError(
            f"Controller '{ctrl_name}' not found in config.controllers. Available: {available}"
        )
    
    # Get dynamics model preference
    use_full = False
    try:
        sim_cfg = getattr(config, "simulation", None)
        if sim_cfg is not None:
            use_full = bool(getattr(sim_cfg, "use_full_dynamics", False))
    except Exception:
        use_full = False
    
    _ensure_dynamics_available(use_full)
    
    # Get controller config and merge with overrides
    ctrl_cfg_obj = controllers_map.get(key, {})
    ctrl_cfg_dict = _as_dict(ctrl_cfg_obj)
    
    # Merge any provided cfg
    if ctrl_cfg is not None:
        override_dict = _as_dict(ctrl_cfg)
        ctrl_cfg_dict.update(override_dict)
    
    # Apply normalization and deprecation
    ctrl_cfg_dict = apply_deprecation_mapping(key, ctrl_cfg_dict, allow_unknown)
    
    # Build dynamics model
    dynamics_model = None
    try:
        phys = getattr(config, "physics", None)
        if phys is not None:
            if use_full:
                dynamics_model = FullDIPDynamics(phys)
            else:
                dynamics_model = DoubleInvertedPendulum(phys)
    except Exception:
        dynamics_model = None
    
    # Get shared parameters
    try:
        sim_cfg = getattr(config, "simulation", None)
        sim_dt = getattr(sim_cfg, "dt", None) if sim_cfg is not None else None
    except Exception:
        sim_dt = None
    
    dt_in_cfg = "dt" in ctrl_cfg_dict
    mf_in_cfg = "max_force" in ctrl_cfg_dict
    
    if dt_in_cfg:
        shared_dt = float(ctrl_cfg_dict.get("dt"))
    else:
        shared_dt = float(sim_dt if sim_dt is not None else 0.01)
        logger.warning(
            f"controllers.{key}: no 'dt' specified; inheriting dt={shared_dt} from simulation configuration."
        )
    
    if mf_in_cfg:
        shared_max_force = float(ctrl_cfg_dict.get("max_force"))
    else:
        shared_max_force = 20.0
        logger.warning(
            f"controllers.{key}: no 'max_force' specified; using default max_force={shared_max_force}."
        )
    
    _validate_shared_params(key, shared_dt, shared_max_force)
    
    # Delegate to specific controller construction
    # This is the legacy if/elif chain from the original factory
    # We keep it for backward compatibility
    
    if key == "classical_smc":
        return _build_classical_smc(key, ctrl_cfg_dict, config, gains, dynamics_model, shared_dt, shared_max_force, allow_unknown)
    elif key == "sta_smc":
        return _build_sta_smc(key, ctrl_cfg_dict, config, gains, dynamics_model, shared_dt, shared_max_force, allow_unknown)
    elif key == "adaptive_smc":
        return _build_adaptive_smc(key, ctrl_cfg_dict, config, gains, shared_dt, shared_max_force, allow_unknown)
    elif key == "swing_up_smc":
        return _build_swing_up_smc(key, ctrl_cfg_dict, config, gains, dynamics_model, shared_dt, shared_max_force, allow_unknown)
    elif key == "hybrid_adaptive_sta_smc":
        return _build_hybrid_adaptive_sta_smc(key, ctrl_cfg_dict, config, gains, dynamics_model, shared_dt, shared_max_force, allow_unknown)
    elif key == "mpc_controller":
        return _build_mpc_controller(key, ctrl_cfg_dict, config, gains, shared_dt, shared_max_force, allow_unknown)
    else:
        raise FactoryConfigurationError(f"Controller '{ctrl_name}' is not a recognized type.")

# Individual controller builders (legacy)
def _build_classical_smc(key, ctrl_cfg_dict, config, gains, dynamics_model, shared_dt, shared_max_force, allow_unknown):
    if ClassicalSMC is None:
        raise ImportError(
            "Controller 'classical_smc' is unavailable (import error). Ensure required modules are importable."
        )
    
    allowed = {
        "dt", "max_force", "damping_gain", "boundary_layer", 
        "switch_method", "regularization", "gains"
    }
    unknown_keys = set(ctrl_cfg_dict.keys()) - allowed
    
    if unknown_keys and not allow_unknown:
        raise FactoryConfigurationError(
            f"controllers.{key}: Unknown configuration keys: {', '.join(sorted(unknown_keys))}. "
            f"Allowed keys: {', '.join(sorted(allowed))}"
        )
    
    boundary_layer = float(ctrl_cfg_dict.get("boundary_layer", 0.01))
    if boundary_layer <= 0:
        raise ConfigValueError(f"controllers.{key}.boundary_layer must be > 0 (got {boundary_layer})")
    
    switch_method = ctrl_cfg_dict.get("switch_method")
    if switch_method is not None:
        switch_method = str(switch_method).lower().strip()
        if switch_method not in ("tanh", "linear"):
            raise ConfigValueError(
                f"controllers.{key}.switch_method must be one of ['tanh','linear'] (got {switch_method!r})"
            )
    
    regularization = float(ctrl_cfg_dict.get("regularization", 1e-10))
    gains_to_use = _get_default_gains(key, config, gains)
    
    instance = ClassicalSMC(
        gains=gains_to_use,
        dynamics_model=dynamics_model,
        max_force=shared_max_force,
        boundary_layer=boundary_layer,
        regularization=regularization,
        **({"switch_method": switch_method} if switch_method else {}),
    )
    
    if allow_unknown and unknown_keys:
        instance.unknown_params = {k: ctrl_cfg_dict[k] for k in unknown_keys}
    
    return instance

def _build_sta_smc(key, ctrl_cfg_dict, config, gains, dynamics_model, shared_dt, shared_max_force, allow_unknown):
    if SuperTwistingSMC is None:
        raise ImportError(
            "Controller 'sta_smc' is unavailable (import error). Ensure required modules are importable."
        )
    
    allowed = {
        "dt", "max_force", "damping_gain", "boundary_layer", 
        "switch_method", "regularization", "anti_windup_gain", "gains"
    }
    unknown_keys = set(ctrl_cfg_dict.keys()) - allowed
    
    if unknown_keys and not allow_unknown:
        raise FactoryConfigurationError(
            f"controllers.{key}: Unknown configuration keys: {', '.join(sorted(unknown_keys))}. "
            f"Allowed keys: {', '.join(sorted(allowed))}"
        )
    
    boundary_layer = float(ctrl_cfg_dict.get("boundary_layer", 0.01))
    if boundary_layer <= 0:
        raise ConfigValueError(f"controllers.{key}.boundary_layer must be > 0 (got {boundary_layer})")
    
    switch_method = ctrl_cfg_dict.get("switch_method")
    if switch_method is not None:
        switch_method = str(switch_method).lower().strip()
        if switch_method not in ("tanh", "linear"):
            raise ConfigValueError(
                f"controllers.{key}.switch_method must be one of ['tanh','linear'] (got {switch_method!r})"
            )
    
    regularization = float(ctrl_cfg_dict.get("regularization", 1e-10))
    gains_to_use = _get_default_gains(key, config, gains)
    
    instance = SuperTwistingSMC(
        gains=gains_to_use,
        dynamics_model=dynamics_model,
        max_force=shared_max_force,
        damping_gain=float(ctrl_cfg_dict.get("damping_gain", 0.0)),
        boundary_layer=boundary_layer,
        dt=shared_dt,
        regularization=regularization,
        **({"switch_method": switch_method} if switch_method else {}),
        **({"anti_windup_gain": float(ctrl_cfg_dict["anti_windup_gain"])} if "anti_windup_gain" in ctrl_cfg_dict else {}),
    )
    
    if allow_unknown and unknown_keys:
        instance.unknown_params = {k: ctrl_cfg_dict[k] for k in unknown_keys}
    
    return instance

def _build_adaptive_smc(key, ctrl_cfg_dict, config, gains, shared_dt, shared_max_force, allow_unknown):
    if AdaptiveSMC is None:
        raise ImportError(
            "Controller 'adaptive_smc' is unavailable (import error). Ensure required modules are importable."
        )
    
    allowed = {
        "dt", "max_force", "leak_rate", "dead_zone", "adapt_rate_limit",
        "K_min", "K_max", "smooth_switch", "boundary_layer", "K_init", "alpha", "gains"
    }
    unknown_keys = set(ctrl_cfg_dict.keys()) - allowed
    
    if unknown_keys and not allow_unknown:
        raise FactoryConfigurationError(
            f"controllers.{key}: Unknown configuration keys: {', '.join(sorted(unknown_keys))}. "
            f"Allowed keys: {', '.join(sorted(allowed))}"
        )
    
    gains_to_use = _get_default_gains(key, config, gains)
    filtered = {k: v for k, v in ctrl_cfg_dict.items() if k in allowed}
    filtered.setdefault("dt", shared_dt)
    filtered.setdefault("max_force", shared_max_force)
    
    if "boundary_layer" in filtered:
        bl = float(filtered["boundary_layer"])
        if bl <= 0:
            raise ConfigValueError(f"controllers.{key}.boundary_layer must be > 0 (got {bl})")
    
    instance = AdaptiveSMC(gains=gains_to_use, **filtered)
    
    if allow_unknown and unknown_keys:
        instance.unknown_params = {k: ctrl_cfg_dict[k] for k in unknown_keys}
    
    return instance

def _build_swing_up_smc(key, ctrl_cfg_dict, config, gains, dynamics_model, shared_dt, shared_max_force, allow_unknown):
    if SwingUpSMC is None:
        raise ImportError(
            "Controller 'swing_up_smc' is unavailable (import error). Ensure required modules are importable."
        )
    
    allowed = {
        "dt", "max_force", "stabilizing_controller", "energy_gain",
        "switch_energy_factor", "exit_energy_factor", "switch_angle_tolerance",
        "reentry_angle_tolerance", "gains"
    }
    unknown_keys = set(ctrl_cfg_dict.keys()) - allowed
    
    if unknown_keys and not allow_unknown:
        raise FactoryConfigurationError(
            f"controllers.{key}: Unknown configuration keys: {', '.join(sorted(unknown_keys))}. "
            f"Allowed keys: {', '.join(sorted(allowed))}"
        )
    
    inner_name = ctrl_cfg_dict.get("stabilizing_controller", "classical_smc")
    normalized_inner = normalize_controller_name(inner_name)
    if normalized_inner == "swing_up_smc":
        raise ConfigValueError("swing_up_smc cannot use itself as stabilizing_controller.")
    
    # Recursively build stabilizer
    stabilizer = build_controller(inner_name, {}, config=config, gains=None)
    
    max_force = float(
        ctrl_cfg_dict.get("max_force", getattr(stabilizer, "max_force", shared_max_force))
    )
    
    instance = SwingUpSMC(
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
    
    if allow_unknown and unknown_keys:
        instance.unknown_params = {k: ctrl_cfg_dict[k] for k in unknown_keys}
    
    return instance

def _build_hybrid_adaptive_sta_smc(key, ctrl_cfg_dict, config, gains, dynamics_model, shared_dt, shared_max_force, allow_unknown):
    if HybridAdaptiveSTASMC is None:
        raise ImportError(
            "Controller 'hybrid_adaptive_sta_smc' is unavailable (import error)."
        )
    
    allowed = {
        "dt", "max_force", "k1_init", "k2_init", "gamma1", "gamma2", "dead_zone",
        "use_equivalent", "enable_equivalent", "damping_gain", "adapt_rate_limit",
        "sat_soft_width", "cart_gain", "cart_lambda", "cart_p_gain", "cart_p_lambda", "gains"
    }
    unknown_keys = set(ctrl_cfg_dict.keys()) - allowed
    
    if unknown_keys and not allow_unknown:
        raise FactoryConfigurationError(
            f"controllers.{key}: Unknown configuration keys: {', '.join(sorted(unknown_keys))}. "
            f"Allowed keys: {', '.join(sorted(allowed))}"
        )
    
    gains_to_use = _get_default_gains(key, config, gains)
    
    filtered = {
        k: v for k, v in ctrl_cfg_dict.items()
        if k in allowed
    }
    filtered.setdefault("dt", shared_dt)
    filtered.setdefault("max_force", shared_max_force)
    
    # Handle equivalent control flags
    eq_kwargs = {}
    if "enable_equivalent" in filtered:
        eq_kwargs["enable_equivalent"] = bool(filtered.pop("enable_equivalent"))
    if "use_equivalent" in filtered:
        eq_kwargs["use_equivalent"] = bool(filtered.pop("use_equivalent"))
    
    instance = HybridAdaptiveSTASMC(
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
    
    if allow_unknown and unknown_keys:
        instance.unknown_params = {k: ctrl_cfg_dict[k] for k in unknown_keys}
    
    return instance

def _build_mpc_controller(key, ctrl_cfg_dict, config, gains, shared_dt, shared_max_force, allow_unknown):
    if MPCController is None:
        raise ImportError(
            "Controller 'mpc_controller' is unavailable (missing optional dependency)."
        )
    
    allowed = {
        "dt", "max_force", "horizon", "q_x", "q_theta", "r_u",
        "max_theta_dev", "max_cart_pos", "fallback_smc_gains",
        "fallback_pd_kp", "fallback_pd_kd", "gains"
    }
    unknown_keys = set(ctrl_cfg_dict.keys()) - allowed
    
    if unknown_keys and not allow_unknown:
        raise FactoryConfigurationError(
            f"controllers.{key}: Unknown configuration keys: {', '.join(sorted(unknown_keys))}. "
            f"Allowed keys: {', '.join(sorted(allowed))}"
        )
    
    # Validate MPC params
    if "horizon" in ctrl_cfg_dict:
        hv = ctrl_cfg_dict["horizon"]
        if not isinstance(hv, int):
            raise ConfigValueError(f"controllers.{key}.horizon must be an integer â‰¥ 1 (got {hv!r})")
        horizon = hv
        if horizon < 1:
            raise ConfigValueError(f"controllers.{key}.horizon must be â‰¥ 1 (got {horizon})")
    
    max_cart_pos = float(ctrl_cfg_dict.get("max_cart_pos", 1.5))
    if not (math.isfinite(max_cart_pos) and max_cart_pos > 0):
        raise ConfigValueError(f"controllers.{key}.max_cart_pos must be > 0 (got {max_cart_pos})")
    
    if "max_theta_dev" in ctrl_cfg_dict:
        mtd = float(ctrl_cfg_dict["max_theta_dev"])
        if not (math.isfinite(mtd) and mtd > 0):
            raise ConfigValueError(f"controllers.{key}.max_theta_dev must be > 0 when provided (got {mtd})")
    
    for wkey in ("q_x", "q_theta", "r_u"):
        if wkey in ctrl_cfg_dict:
            val = float(ctrl_cfg_dict[wkey])
            if val < 0:
                raise ConfigValueError(f"controllers.{key}.{wkey} must be â‰¥ 0 (got {val})")
    
    # Build dummy dynamics
    class _DummyDyn:
        def __init__(self):
            self.state_dim = 6
        def step(self, state, u, dt):
            return np.asarray(state, dtype=float)
        def f(self, x, u):
            return np.zeros_like(x)
        continuous_dynamics = f
    
    prediction_model = _DummyDyn()
    
    # Build weights
    q_x = ctrl_cfg_dict.get("q_x")
    q_theta = ctrl_cfg_dict.get("q_theta")
    r_u = ctrl_cfg_dict.get("r_u")
    if any(v is not None for v in (q_x, q_theta, r_u)):
        weight_kwargs = {}
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
    mpc_kwargs = {
        "dynamics_model": prediction_model,
        "horizon": int(ctrl_cfg_dict.get("horizon", 20)),
        "dt": float(shared_dt),
        "max_force": float(shared_max_force),
        "weights": weights,
        "max_cart_pos": float(ctrl_cfg_dict.get("max_cart_pos", 1.5)),
    }
    if theta_dev is not None:
        mpc_kwargs["max_theta_dev"] = float(theta_dev)
    
    # Handle fallback gains
    fb_smc = ctrl_cfg_dict.get("fallback_smc_gains", None)
    if fb_smc is not None:
        try:
            mpc_kwargs["fallback_smc_gains"] = [float(x) for x in fb_smc]
        except Exception:
            logger.warning(
                f"controllers.{key}: fallback_smc_gains must be a sequence of floats; ignoring provided value {fb_smc!r}."
            )
    
    fb_kp = ctrl_cfg_dict.get("fallback_pd_kp", None)
    fb_kd = ctrl_cfg_dict.get("fallback_pd_kd", None)
    if fb_kp is not None and fb_kd is not None:
        try:
            mpc_kwargs["fallback_pd_gains"] = (float(fb_kp), float(fb_kd))
        except Exception:
            logger.warning(
                f"controllers.{key}: fallback_pd_kp/kd must be numeric; using default PD gains."
            )
    
    instance = MPCController(**mpc_kwargs)
    
    if allow_unknown and unknown_keys:
        instance.unknown_params = {k: ctrl_cfg_dict[k] for k in unknown_keys}
    
    return instance

# ---------- Backward Compatibility ----------
# Keep create_controller for backward compatibility
def create_controller(name: str, /, **kwargs: Any) -> Any:
    """
    Backwards-compatible convenience wrapper used by tests and the CLI.
    Delegates to build_controller() so mapping/validation stays centralized.

    Parameters
    ----------
    name : str
        Controller name (aliases allowed).
    **kwargs :
        Per-controller constructor args (e.g., gains, dt, max_force).
    """
    # Unknown *controller names* must still raise.
    # allow_unknown=True relaxes parameter filtering only.

    # Normalize controller name
    controller_name = normalize_controller_name(name)

    # Check registry first
    with CONTROLLER_REGISTRY_LOCK:
        if controller_name in CONTROLLER_REGISTRY:
            return build_controller(name, kwargs, allow_unknown=True)

    # For tests and direct usage, try to create directly without config.yaml
    # Apply deprecation mapping first
    normalized_kwargs = apply_deprecation_mapping(controller_name, kwargs, allow_unknown=True)

    # Handle direct controller construction for common cases
    if controller_name == "classical_smc" and ClassicalSMC is not None:
        # Extract required parameters
        gains = normalized_kwargs.get('gains')
        if gains is None:
            raise ValueError(f"Controller '{name}': gains parameter is required")

        max_force = normalized_kwargs.get('max_force', 20.0)
        boundary_layer = normalized_kwargs.get('boundary_layer', 0.01)

        # Filter known parameters
        known_params = {
            'gains': gains,
            'max_force': max_force,
            'boundary_layer': boundary_layer,
            'dynamics_model': normalized_kwargs.get('dynamics_model'),
            'regularization': normalized_kwargs.get('regularization', 1e-10),
            'switch_method': normalized_kwargs.get('switch_method', 'tanh'),
        }

        # Remove None values
        filtered_params = {k: v for k, v in known_params.items() if v is not None}

        return ClassicalSMC(**filtered_params)

    elif controller_name == "sta_smc" and SuperTwistingSMC is not None:
        # Similar handling for SuperTwistingSMC
        gains = normalized_kwargs.get('gains')
        if gains is None:
            raise ValueError(f"Controller '{name}': gains parameter is required")

        max_force = normalized_kwargs.get('max_force', 20.0)
        boundary_layer = normalized_kwargs.get('boundary_layer', 0.01)
        dt = normalized_kwargs.get('dt', 0.01)

        known_params = {
            'gains': gains,
            'max_force': max_force,
            'boundary_layer': boundary_layer,
            'dt': dt,
            'dynamics_model': normalized_kwargs.get('dynamics_model'),
            'damping_gain': normalized_kwargs.get('damping_gain', 0.0),
            'regularization': normalized_kwargs.get('regularization', 1e-10),
            'switch_method': normalized_kwargs.get('switch_method', 'tanh'),
        }

        # Handle optional anti_windup_gain
        if 'anti_windup_gain' in normalized_kwargs:
            known_params['anti_windup_gain'] = normalized_kwargs['anti_windup_gain']

        filtered_params = {k: v for k, v in known_params.items() if v is not None}

        return SuperTwistingSMC(**filtered_params)

    elif controller_name == "adaptive_smc" and AdaptiveSMC is not None:
        # Similar handling for AdaptiveSMC with required defaults
        gains = normalized_kwargs.get('gains')
        if gains is None:
            raise ValueError(f"Controller '{name}': gains parameter is required")

        known_params = {
            'gains': gains,
            'dt': normalized_kwargs.get('dt', 0.01),
            'max_force': normalized_kwargs.get('max_force', 20.0),
            'leak_rate': normalized_kwargs.get('leak_rate', 0.1),
            'dead_zone': normalized_kwargs.get('dead_zone', 0.01),
            'adapt_rate_limit': normalized_kwargs.get('adapt_rate_limit', 100.0),
            'K_min': normalized_kwargs.get('K_min', 0.1),
            'K_max': normalized_kwargs.get('K_max', 100.0),
            'smooth_switch': normalized_kwargs.get('smooth_switch', True),
            'boundary_layer': normalized_kwargs.get('boundary_layer', 0.01),
            'K_init': normalized_kwargs.get('K_init', 10.0),
            'alpha': normalized_kwargs.get('alpha', 0.5),
        }

        # All parameters have defaults, so just pass them all
        return AdaptiveSMC(**known_params)

    # For unknown controller names or when direct construction fails,
    # fall back to full build_controller with config loading
    try:
        config = kwargs.pop('config', None)
        gains = kwargs.pop('gains', None)

        return build_controller(
            name,
            kwargs,
            config=config,
            gains=gains,
            allow_unknown=True
        )
    except Exception:
        # If all else fails, raise error for unknown controller
        raise ValueError(f"Controller '{name}' is not a recognized type")

# Expose the canonical name helper for backward compat
def _canonical(name: str) -> str:
    """
    Legacy/compat alias for tests. Mirrors normalize_controller_name().
    """
    return normalize_controller_name(name)
