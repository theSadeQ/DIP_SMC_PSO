#==========================================================================================\\\
#=================================== src/config/schemas.py ==============================\\\
#==========================================================================================\\\
"""Configuration schemas and models for the DIP SMC PSO project."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def redact_value(value: Any) -> str:
    """Redact sensitive values for logging."""
    if isinstance(value, SecretStr):
        return "***"
    if isinstance(value, str) and any(
        keyword in str(value).lower() for keyword in ["password", "secret", "token", "key"]
    ):
        return "***"
    return str(value)

# ------------------------------------------------------------------------------
# Base strict model
# ------------------------------------------------------------------------------
class StrictModel(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        populate_by_name=True,
        validate_default=True,
        validate_assignment=True,
    )

# ------------------------------------------------------------------------------
# Physics
# ------------------------------------------------------------------------------
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
    # Physics effects for full dynamics model
    include_coriolis_effects: bool = Field(True)
    include_centrifugal_effects: bool = Field(True)
    include_gyroscopic_effects: bool = Field(True)

    @field_validator(
        "cart_mass", "pendulum1_mass", "pendulum2_mass",
        "pendulum1_length", "pendulum2_length",
        "pendulum1_inertia", "pendulum2_inertia",
        "pendulum1_com", "pendulum2_com",
        "gravity"
    )
    @classmethod
    def _must_be_strictly_positive(cls, v: float, info) -> float:
        if v is None or v <= 0.0:
            raise ValueError(f"{info.field_name} must be strictly positive, but got {v}")
        return v

    @model_validator(mode="after")
    def _validate_com_within_length(self) -> "PhysicsConfig":
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

# ------------------------------------------------------------------------------
# Simulation
# ------------------------------------------------------------------------------
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
            raise ValueError("initial_state must be a non-empty list of floats")
        if not all(isinstance(x, float) for x in v):
            raise ValueError("initial_state must contain float values (no implicit casts)")
        return v

# ------------------------------------------------------------------------------
# Legacy module-level namespace (best-effort)
# ------------------------------------------------------------------------------
try:
    if "config" not in globals():
        config = SimpleNamespace(
            simulation=SimpleNamespace(
                use_full_dynamics=False,
                safety=None,
            )
        )
except Exception:
    pass

# ------------------------------------------------------------------------------
# Controllers
# ------------------------------------------------------------------------------
class _BaseControllerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gains: List[float] = Field(default_factory=list, min_length=1)

    def __iter__(self):
        for k, v in self.model_dump(exclude_unset=True).items():
            yield k, v

class ControllerConfig(_BaseControllerConfig):
    pass

class ClassicalSMCConfig(_BaseControllerConfig):
    """Configuration for Classical Sliding Mode Controller."""
    max_force: Optional[float] = Field(None, gt=0.0)
    boundary_layer: Optional[float] = Field(None, gt=0.0)

class STASMCConfig(_BaseControllerConfig):
    """Configuration for Super-Twisting Algorithm Sliding Mode Controller."""
    max_force: Optional[float] = Field(None, gt=0.0)
    damping_gain: Optional[float] = Field(None, ge=0.0)
    dt: Optional[float] = Field(None, gt=0.0)

class AdaptiveSMCConfig(_BaseControllerConfig):
    """Configuration for Adaptive Sliding Mode Controller."""
    max_force: Optional[float] = Field(None, gt=0.0)
    leak_rate: Optional[float] = Field(None, ge=0.0)
    dead_zone: Optional[float] = Field(None, gt=0.0)
    adapt_rate_limit: Optional[float] = Field(None, gt=0.0)
    K_min: Optional[float] = Field(None, gt=0.0)
    K_max: Optional[float] = Field(None, gt=0.0)
    dt: Optional[float] = Field(None, gt=0.0)
    smooth_switch: Optional[bool] = None
    boundary_layer: Optional[float] = Field(None, gt=0.0)

    @model_validator(mode="after")
    def _validate_adaptive_bounds(self) -> "AdaptiveSMCConfig":
        if self.K_min is not None and self.K_max is not None:
            if self.K_min >= self.K_max:
                raise ValueError(f"K_min ({self.K_min}) must be less than K_max ({self.K_max})")
        return self

class SwingUpSMCConfig(_BaseControllerConfig):
    """Configuration for Swing-Up Sliding Mode Controller."""
    max_force: Optional[float] = Field(None, gt=0.0)
    stabilizing_controller: Optional[str] = None
    energy_gain: Optional[float] = Field(None, gt=0.0)
    switch_energy_factor: Optional[float] = Field(None, gt=0.0, le=1.0)
    switch_angle_tolerance: Optional[float] = Field(None, gt=0.0)
    exit_energy_factor: Optional[float] = Field(None, gt=0.0, le=1.0)
    reentry_angle_tolerance: Optional[float] = Field(None, gt=0.0)

class HybridAdaptiveSTASMCConfig(_BaseControllerConfig):
    """Configuration for Hybrid Adaptive Super-Twisting Sliding Mode Controller."""
    max_force: Optional[float] = Field(None, gt=0.0)
    dt: Optional[float] = Field(None, gt=0.0)
    k1_init: Optional[float] = Field(None, gt=0.0)
    k2_init: Optional[float] = Field(None, gt=0.0)
    gamma1: Optional[float] = Field(None, gt=0.0)
    gamma2: Optional[float] = Field(None, gt=0.0)
    dead_zone: Optional[float] = Field(None, gt=0.0)
    enable_equivalent: Optional[bool] = None
    damping_gain: Optional[float] = Field(None, ge=0.0)
    adapt_rate_limit: Optional[float] = Field(None, gt=0.0)
    sat_soft_width: Optional[float] = Field(None, gt=0.0)
    cart_gain: Optional[float] = Field(None, ge=0.0)
    cart_lambda: Optional[float] = Field(None, gt=0.0)
    cart_p_gain: Optional[float] = Field(None, ge=0.0)
    cart_p_lambda: Optional[float] = Field(None, gt=0.0)

    @model_validator(mode="after")
    def _validate_hybrid_constraints(self) -> "HybridAdaptiveSTASMCConfig":
        if self.sat_soft_width is not None and self.dead_zone is not None:
            if self.sat_soft_width < self.dead_zone:
                raise ValueError(
                    f"sat_soft_width ({self.sat_soft_width}) must be >= dead_zone ({self.dead_zone})"
                )
        return self

class PermissiveControllerConfig(_BaseControllerConfig):
    model_config = ConfigDict(extra="allow")
    unknown_params: Dict[str, Any] = Field(default_factory=dict)
    allow_unknown: bool = False

    @model_validator(mode="after")
    def _collect_unknown_params(self) -> "PermissiveControllerConfig":
        extra = getattr(self, "model_extra", None)
        if extra:
            unknown = dict(extra)
            object.__setattr__(self, "unknown_params", unknown)
            if not self.__class__.allow_unknown:
                unknown_keys = ", ".join(sorted(unknown.keys()))
                raise ValueError(
                    f"Unknown configuration keys: {unknown_keys}. "
                    "Set allow_unknown=True when calling load_config to accept unknown keys."
                )
        return self

def set_allow_unknown_config(_: bool) -> None:
    """Deprecated - use load_config(..., allow_unknown=True) instead."""
    raise RuntimeError(
        "set_allow_unknown_config() is deprecated; use load_config(..., allow_unknown=True) instead."
    )

class ControllersConfig(StrictModel):
    classical_smc: Optional[ClassicalSMCConfig] = None
    sta_smc: Optional[STASMCConfig] = None
    adaptive_smc: Optional[AdaptiveSMCConfig] = None
    swing_up_smc: Optional[SwingUpSMCConfig] = None
    hybrid_adaptive_sta_smc: Optional[HybridAdaptiveSTASMCConfig] = None
    mpc_controller: Optional[PermissiveControllerConfig] = None

    def keys(self) -> List[str]:
        return [
            name for name in (
                "classical_smc", "sta_smc", "adaptive_smc",
                "swing_up_smc", "hybrid_adaptive_sta_smc", "mpc_controller",
            ) if getattr(self, name) is not None
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

# ------------------------------------------------------------------------------
# PSO
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# Cost Function
# ------------------------------------------------------------------------------
class CostFunctionWeights(StrictModel):
    state_error: float = Field(50.0, ge=0.0)
    control_effort: float = Field(0.2, ge=0.0)
    control_rate: float = Field(0.1, ge=0.0)
    stability: float = Field(0.1, ge=0.0)

class CombineWeights(StrictModel):
    mean: float = Field(0.7, ge=0.0, le=1.0)
    max: float = Field(0.3, ge=0.0, le=1.0)

class CostFunctionConfig(StrictModel):
    weights: CostFunctionWeights
    baseline: Dict[str, Any]
    instability_penalty: float = Field(1000.0, ge=0.0)
    combine_weights: CombineWeights = CombineWeights()
    normalization_threshold: float = Field(1e-12, ge=0.0)

# ------------------------------------------------------------------------------
# Verification
# ------------------------------------------------------------------------------
class VerificationConfig(StrictModel):
    test_conditions: List[Dict[str, Any]]
    integrators: List[str]
    criteria: Dict[str, float]

# ------------------------------------------------------------------------------
# Sensors
# ------------------------------------------------------------------------------
class SensorsConfig(StrictModel):
    angle_noise_std: float = 0.0
    position_noise_std: float = 0.0
    quantization_angle: float = 0.0
    quantization_position: float = 0.0

# ------------------------------------------------------------------------------
# HIL
# ------------------------------------------------------------------------------
class HILConfig(StrictModel):
    plant_ip: str
    plant_port: int
    controller_ip: str
    controller_port: int
    extra_latency_ms: float = 0.0
    sensor_noise_std: float = 0.0

# ------------------------------------------------------------------------------
# FDI
# ------------------------------------------------------------------------------
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

    @field_validator("residual_states")
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
    def _validate_weights_length(self) -> "FDIConfig":
        w = getattr(self, "residual_weights", None)
        if w is not None:
            if len(w) != len(self.residual_states):
                raise ValueError(
                    f"residual_weights length {len(w)} does not match residual_states length"
                )
            if any((ww is None or ww < 0.0) for ww in w):
                raise ValueError("residual_weights must contain non-negative numbers")
        return self