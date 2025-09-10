from pydantic_settings import BaseSettings, SettingsConfigDict
#==================================================================================\\\
# src/config.py ===================================================================\\\
#==================================================================================\\\

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, Type

import yaml

  param($m)
  $lead = $m.Groups[1].Value
  $rest = $m.Groups[2].Value
  $rest = $rest -replace '\bBaseSettings\b,\s*', '' -replace ',\s*\bBaseSettings\b', '' -replace '\bBaseSettings\b', ''
  $lead + $rest

from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings as PydanticBaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from dotenv import load_dotenv

# Import the global seeding utility
from src.utils.seed import set_global_seed

# Configure module logger
logger = logging.getLogger("project.config")
logger.setLevel(logging.INFO)

# Custom exception for configuration errors
class InvalidConfigurationError(Exception):
    """Raised when configuration validation fails with aggregated error messages."""
    pass


# --- Helper for redacting secrets in logs ---
def redact_value(value: Any) -> str:
    """Redact sensitive values for logging."""
    if isinstance(value, SecretStr):
        return "***"
    if isinstance(value, str) and any(
        keyword in str(value).lower() for keyword in ["password", "secret", "token", "key"]
    ):
        return "***"
    return str(value)


# --- Strict base for nested config models ---
class StrictModel(BaseModel):
    # Enforce no implicit coercions across all nested models
    model_config = ConfigDict(
        strict=True,
        extra='forbid',
        populate_by_name=True,
        validate_default=True,
        validate_assignment=True,
    )


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
    cart_friction: float = Field(..., ge=0.0)
    joint1_friction: float = Field(..., ge=0.0)
    joint2_friction: float = Field(..., ge=0.0)
    singularity_cond_threshold: float = Field(1.0e8, ge=1e4)
    regularization: float = Field(1e-10, gt=0.0)
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
        if v is None or v <= 0.0:
            raise ValueError(f"{info.field_name} must be strictly positive, but got {v}")
        # No casting: keep strict typing
        return v

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
    use_full_dynamics: bool = True
    sensor_latency: float = Field(0.0, ge=0.0)
    actuator_latency: float = Field(0.0, ge=0.0)
    real_time: bool = False
    raise_on_warning: bool = False

    @field_validator("dt", "duration")
    @classmethod
    def _must_be_positive(cls, v: float, info):
        if v is None or v <= 0.0:
            raise ValueError(f"{info.field_name} must be > 0")
        return v

    @model_validator(mode="after")
    def _duration_at_least_dt(self):
        if self.duration < self.dt:
            raise ValueError("simulation.duration must be >= simulation.dt")
        return self

    @field_validator("initial_state")
    @classmethod
    def _initial_state_valid(cls, v):
        if v is None:
            return v
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError(
                "initial_state must be a non-empty list of floats"
            )
        # Enforce strict floats (no implicit coercion)
        if not all(isinstance(x, float) for x in v):
            raise ValueError("initial_state must contain float values (no implicit casts)")
        return v


# Module-level fallback namespace for backward compatibility
try:
    from types import SimpleNamespace
    if "config" not in globals():
        config = SimpleNamespace(
            simulation=SimpleNamespace(
                use_full_dynamics=False,
                safety=None,
            )
        )
except Exception:
    pass


# ---------------- Controllers -------------------#
class _BaseControllerConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    gains: List[float] = Field(default_factory=list, min_length=1)

    def __iter__(self):
        for k, v in self.model_dump(exclude_unset=True).items():
            yield k, v


class ControllerConfig(_BaseControllerConfig):
    pass


class PermissiveControllerConfig(_BaseControllerConfig):
    model_config = ConfigDict(extra='allow')
    unknown_params: Dict[str, Any] = Field(default_factory=dict)
    allow_unknown: bool = False

    @model_validator(mode="after")
    def _collect_unknown_params(self) -> 'PermissiveControllerConfig':
        extra = getattr(self, 'model_extra', None)
        if extra:
            unknown = dict(extra)
            object.__setattr__(self, 'unknown_params', unknown)
            if not self.__class__.allow_unknown:
                unknown_keys = ", ".join(sorted(unknown.keys()))
                raise ValueError(
                    f"Unknown configuration keys: {unknown_keys}. "
                    "Set allow_unknown=True when calling load_config to accept unknown keys."
                )
        return self


def set_allow_unknown_config(flag: bool) -> None:
    """Deprecated - use load_config(..., allow_unknown=True) instead."""
    raise RuntimeError(
        "set_allow_unknown_config() is deprecated; "
        "use load_config(..., allow_unknown=True) instead."
    )


class ControllersConfig(StrictModel):
    classical_smc: Optional[PermissiveControllerConfig] = None
    sta_smc: Optional[PermissiveControllerConfig] = None
    adaptive_smc: Optional[PermissiveControllerConfig] = None
    swing_up_smc: Optional[PermissiveControllerConfig] = None
    hybrid_adaptive_sta_smc: Optional[PermissiveControllerConfig] = None
    mpc_controller: Optional[PermissiveControllerConfig] = None

    def keys(self) -> List[str]:
        return [
            name for name in (
                "classical_smc", "sta_smc", "adaptive_smc",
                "swing_up_smc", "hybrid_adaptive_sta_smc", "mpc_controller"
            )
            if getattr(self, name) is not None
        ]

    def __iter__(self):
        for name in self.keys():
            yield name

    def items(self):
        for name in self:
            yield (name, getattr(self, name))

    def __getitem__(self, key: str) -> Any:
        canonical = str(key).lower().strip().replace("-", "_").replace(" ", "_")
        if canonical in self.keys():
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
    n_particles: int = Field(100, ge=1)
    bounds: PSOBounds
    w: float = Field(0.5, ge=0.0)
    c1: float = Field(1.5, ge=0.0)
    c2: float = Field(1.5, ge=0.0)
    iters: int = Field(200, ge=1)
    w_schedule: Optional[Tuple[float, float]] = None
    velocity_clamp: Optional[Tuple[float, float]] = None
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
        if any(idx >= 6 for idx in v):
            raise ValueError(
                f"residual_states contains invalid indices {v}; valid state indices are 0-5"
            )
        return v

    @model_validator(mode="after")
    def _validate_weights_length(self) -> 'FDIConfig':
        w = getattr(self, 'residual_weights', None)
        if w is not None:
            if len(w) != len(self.residual_states):
                raise ValueError(
                    f"residual_weights length {len(w)} does not match residual_states length"
                )
            if any((ww is None or ww < 0.0) for ww in w):
                raise ValueError("residual_weights must contain non-negative numbers")
        return self


# ---------------- Custom File Source for Settings -------------------#
class FileSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source for loading from YAML or JSON files."""
    
    def __init__(self, settings_cls: Type[BaseSettings], file_path: Optional[Path] = None):
        super().__init__(settings_cls)
        self.file_path = file_path
        
    def _read_file(self, file_path: Path) -> Dict[str, Any]:
        """Read configuration from YAML or JSON file."""
        if not file_path or not file_path.exists():
            return {}
            
        try:
            content = file_path.read_text(encoding='utf-8')
            
            if file_path.suffix.lower() in ('.yaml', '.yml'):
                return yaml.safe_load(content) or {}
            elif file_path.suffix.lower() == '.json':
                return json.loads(content) or {}
            else:
                logger.warning(f"Unknown file type: {file_path.suffix}")
                return {}
        except Exception as e:
            logger.error(f"Failed to read config file {file_path}: {e}")
            return {}
    
    def get_field_value(self, field: FieldInfo, field_name: str) -> Tuple[Any, str, bool]:
        """Get field value from file."""
        return None, field_name, False
    
    def __call__(self) -> Dict[str, Any]:
        """Load the configuration from file."""
        if self.file_path:
            return self._read_file(self.file_path)
        return {}


# ---------------- Main Schema using BaseSettings -------------------#
class ConfigSchema(PydanticBaseSettings):
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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="C04__",
        env_nested_delimiter="__",
        extra="forbid",
        validate_default=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "env_parse_none_str": "null",
        }
    )
    
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize settings sources to achieve precedence:
        ENV > .env > FILE > defaults
        
        We inject our custom file source between dotenv and init_settings.
        """
        file_path = getattr(settings_cls, '_file_path', None)
        file_source = FileSettingsSource(settings_cls, file_path)
        
        # Order determines precedence (first wins)
        return (
            env_settings,      # Environment variables (highest)
            dotenv_settings,   # .env file
            file_source,       # YAML/JSON file
            init_settings,     # Defaults (lowest)
        )


# ---------------- Loader Function -------------------#
def load_config(
    path: str | Path = "config.yaml",
    *,
    allow_unknown: bool = False,
) -> ConfigSchema:
    """Load, parse, and validate configuration from multiple sources.
    
    Precedence (highest to lowest):
    1. Environment variables (C04__ prefix)
    2. .env file
    3. External file (YAML/JSON) specified by path
    4. Model defaults
    
    Parameters
    ----------
    path : str or Path, optional
        Path to YAML or JSON configuration file. Defaults to "config.yaml".
    allow_unknown : bool, optional
        When True, unrecognized keys in controller configs are accepted.
        When False (default), unknown keys raise ValueError.
        
    Returns
    -------
    ConfigSchema
        The validated configuration object.
        
    Raises
    ------
    InvalidConfigurationError
        If configuration validation fails.
    """
    # Store previous permissive state
    try:
        previous_allow = PermissiveControllerConfig.allow_unknown
    except Exception:
        previous_allow = False
    
    # Set permissive mode for this call
    PermissiveControllerConfig.allow_unknown = bool(allow_unknown)
    
    try:
        # Convert path to Path object
        file_path = Path(path) if path else None
        
        # Check if file exists (optional - file source handles missing files)
        if file_path and not file_path.exists():
            logger.warning(f"Configuration file not found: {file_path.absolute()}")
            # Continue anyway - will use env/defaults
        
        # Load .env file if it exists
        if Path(".env").exists():
            load_dotenv(".env", override=False)
            logger.debug("Loaded .env file")
        
        # Attach file path to class for source customization
        ConfigSchema._file_path = file_path
        
        try:
            # Create settings instance - this will use all sources
            cfg = ConfigSchema()
            
            # Log configuration sources used
            logger.info(f"Configuration loaded from sources: ENV > .env > {file_path or 'defaults'}")
            
            # Set global seed if specified
            try:
                if hasattr(cfg, "global_seed") and cfg.global_seed is not None:
                    set_global_seed(cfg.global_seed)
                    logger.debug(f"Set global seed to {cfg.global_seed}")
            except Exception as e:
                logger.warning(f"Failed to set global seed: {e}")
            
            return cfg
            
        except Exception as e:
            # Aggregate validation errors
            error_messages = []
            if hasattr(e, 'errors'):
                for err in e.errors():
                    loc = '.'.join(str(x) for x in err.get('loc', []))
                    msg = err.get('msg', 'Unknown error')
                    # Redact sensitive values
                    if 'input' in err:
                        err['input'] = redact_value(err['input'])
                    error_messages.append(f"  - {loc}: {msg}")
                    logger.error(f"Validation error at {loc}: {msg}")
            else:
                error_messages.append(str(e))
                logger.error(f"Configuration error: {e}")
            
            # Raise aggregated error
            error_text = "Configuration validation failed:\n" + "\n".join(error_messages)
            raise InvalidConfigurationError(error_text) from e
            
    finally:
        # Restore previous permissive state
        try:
            PermissiveControllerConfig.allow_unknown = bool(previous_allow)
        except Exception:
            pass
        
        # Clean up temporary attribute
        if hasattr(ConfigSchema, '_file_path'):
            delattr(ConfigSchema, '_file_path')


#====================================================================================\\\
