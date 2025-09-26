#==========================================================================================\\\
#=============== src/controllers/smc/algorithms/hybrid/config.py ====================\\\
#==========================================================================================\\\

"""
Configuration Schema for Hybrid SMC.

Type-safe configuration for Hybrid Sliding Mode Control that combines
multiple SMC algorithms with intelligent switching logic.

Mathematical Requirements:
- Individual controller gains must satisfy their respective stability conditions
- Switching thresholds must prevent chattering between controllers
- Hysteresis parameters must ensure stable mode transitions
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from ..classical.config import ClassicalSMCConfig
from ..adaptive.config import AdaptiveSMCConfig
from ..super_twisting.config import SuperTwistingSMCConfig


class HybridMode(Enum):
    """Available hybrid controller modes."""
    CLASSICAL_ADAPTIVE = "classical_adaptive"
    ADAPTIVE_SUPERTWISTING = "adaptive_supertwisting"
    CLASSICAL_SUPERTWISTING = "classical_supertwisting"
    TRIPLE_HYBRID = "triple_hybrid"


class SwitchingCriterion(Enum):
    """Switching criteria for hybrid control."""
    SURFACE_MAGNITUDE = "surface_magnitude"
    CONTROL_EFFORT = "control_effort"
    TRACKING_ERROR = "tracking_error"
    ADAPTATION_RATE = "adaptation_rate"
    PERFORMANCE_INDEX = "performance_index"
    TIME_BASED = "time_based"


@dataclass(frozen=True)
class HybridSMCConfig:
    """
    Type-safe configuration for Hybrid SMC controller.

    Combines multiple SMC controllers with intelligent switching logic
    for improved performance across different operating conditions.
    """

    # Required parameters
    hybrid_mode: HybridMode = field()                          # Which controllers to combine
    dt: float = field()                                        # Control timestep
    max_force: float = field()                                 # Control saturation limit

    # Controller configurations
    classical_config: Optional[ClassicalSMCConfig] = field(default=None)
    adaptive_config: Optional[AdaptiveSMCConfig] = field(default=None)
    supertwisting_config: Optional[SuperTwistingSMCConfig] = field(default=None)

    # Switching logic parameters
    switching_criterion: SwitchingCriterion = field(default=SwitchingCriterion.SURFACE_MAGNITUDE)
    switching_thresholds: List[float] = field(default_factory=lambda: [0.1, 1.0])  # [low, high]
    hysteresis_margin: float = field(default=0.02)            # Prevents chattering
    min_switching_time: float = field(default=0.1)            # Minimum time between switches

    # Performance monitoring
    performance_window: int = field(default=50)               # Window for performance evaluation
    performance_weights: Dict[str, float] = field(default_factory=lambda: {
        'tracking_error': 0.4,
        'control_effort': 0.3,
        'surface_magnitude': 0.3
    })

    # Advanced switching features
    enable_predictive_switching: bool = field(default=False)  # Look-ahead switching
    prediction_horizon: int = field(default=10)               # Steps ahead for prediction
    enable_learning: bool = field(default=False)              # Adaptive switching thresholds
    learning_rate: float = field(default=0.01)                # Threshold adaptation rate

    # Transition smoothing
    transition_smoothing: bool = field(default=True)          # Smooth control transitions
    smoothing_time_constant: float = field(default=0.05)     # Smoothing filter time constant

    # Optional dynamics model
    dynamics_model: Optional[object] = field(default=None, compare=False)

    def __post_init__(self):
        """Validate configuration after creation."""
        self._validate_hybrid_mode()
        self._validate_switching_parameters()
        self._validate_controller_configs()
        self._validate_performance_parameters()

    def _validate_hybrid_mode(self) -> None:
        """Validate hybrid mode and required controller configurations."""
        mode_requirements = {
            HybridMode.CLASSICAL_ADAPTIVE: ['classical_config', 'adaptive_config'],
            HybridMode.ADAPTIVE_SUPERTWISTING: ['adaptive_config', 'supertwisting_config'],
            HybridMode.CLASSICAL_SUPERTWISTING: ['classical_config', 'supertwisting_config'],
            HybridMode.TRIPLE_HYBRID: ['classical_config', 'adaptive_config', 'supertwisting_config']
        }

        required_configs = mode_requirements[self.hybrid_mode]

        for config_name in required_configs:
            config_value = getattr(self, config_name)
            if config_value is None:
                raise ValueError(f"Hybrid mode {self.hybrid_mode.value} requires {config_name}")

    def _validate_switching_parameters(self) -> None:
        """Validate switching logic parameters."""
        if len(self.switching_thresholds) < 2:
            raise ValueError("At least 2 switching thresholds required")

        thresholds = sorted(self.switching_thresholds)
        if thresholds != self.switching_thresholds:
            raise ValueError("Switching thresholds must be in ascending order")

        if self.hysteresis_margin < 0:
            raise ValueError("Hysteresis margin must be non-negative")

        if self.min_switching_time <= 0:
            raise ValueError("Minimum switching time must be positive")

        if self.hysteresis_margin >= min(abs(t2 - t1) for t1, t2 in zip(thresholds[:-1], thresholds[1:])):
            raise ValueError("Hysteresis margin too large compared to threshold differences")

    def _validate_controller_configs(self) -> None:
        """Validate individual controller configurations."""
        configs_to_check = []

        if self.classical_config is not None:
            configs_to_check.append(('classical', self.classical_config))
        if self.adaptive_config is not None:
            configs_to_check.append(('adaptive', self.adaptive_config))
        if self.supertwisting_config is not None:
            configs_to_check.append(('supertwisting', self.supertwisting_config))

        # Check dt consistency
        for name, config in configs_to_check:
            if abs(config.dt - self.dt) > 1e-6:
                raise ValueError(f"{name} config dt={config.dt} inconsistent with hybrid dt={self.dt}")

        # Check max_force consistency
        for name, config in configs_to_check:
            if abs(config.max_force - self.max_force) > 1e-6:
                raise ValueError(f"{name} config max_force={config.max_force} inconsistent with hybrid max_force={self.max_force}")

    def _validate_performance_parameters(self) -> None:
        """Validate performance monitoring parameters."""
        if self.performance_window <= 0:
            raise ValueError("Performance window must be positive")

        weight_sum = sum(self.performance_weights.values())
        if abs(weight_sum - 1.0) > 1e-6:
            raise ValueError(f"Performance weights must sum to 1.0, got {weight_sum}")

        for weight in self.performance_weights.values():
            if weight < 0:
                raise ValueError("Performance weights must be non-negative")

        if self.enable_predictive_switching and self.prediction_horizon <= 0:
            raise ValueError("Prediction horizon must be positive when predictive switching enabled")

        if self.enable_learning and not (0 < self.learning_rate <= 1):
            raise ValueError("Learning rate must be in (0, 1]")

        if self.transition_smoothing and self.smoothing_time_constant <= 0:
            raise ValueError("Smoothing time constant must be positive")

    def get_active_controllers(self) -> List[str]:
        """Get list of active controller types based on hybrid mode."""
        mode_mapping = {
            HybridMode.CLASSICAL_ADAPTIVE: ['classical', 'adaptive'],
            HybridMode.ADAPTIVE_SUPERTWISTING: ['adaptive', 'supertwisting'],
            HybridMode.CLASSICAL_SUPERTWISTING: ['classical', 'supertwisting'],
            HybridMode.TRIPLE_HYBRID: ['classical', 'adaptive', 'supertwisting']
        }
        return mode_mapping[self.hybrid_mode]

    def get_controller_config(self, controller_type: str) -> Union[ClassicalSMCConfig, AdaptiveSMCConfig, SuperTwistingSMCConfig]:
        """Get configuration for specific controller type."""
        config_mapping = {
            'classical': self.classical_config,
            'adaptive': self.adaptive_config,
            'supertwisting': self.supertwisting_config
        }

        config = config_mapping.get(controller_type)
        if config is None:
            raise ValueError(f"Controller type '{controller_type}' not configured for this hybrid mode")

        return config

    def get_switching_thresholds_with_hysteresis(self) -> List[tuple[float, float]]:
        """
        Get switching thresholds with hysteresis bands.

        Returns:
            List of (lower_threshold, upper_threshold) tuples
        """
        thresholds_with_hysteresis = []
        for threshold in self.switching_thresholds:
            lower = threshold - self.hysteresis_margin / 2
            upper = threshold + self.hysteresis_margin / 2
            thresholds_with_hysteresis.append((lower, upper))

        return thresholds_with_hysteresis

    def is_switching_allowed(self, last_switch_time: float, current_time: float) -> bool:
        """Check if switching is allowed based on minimum switching time."""
        return (current_time - last_switch_time) >= self.min_switching_time

    def get_performance_metric_names(self) -> List[str]:
        """Get list of performance metric names."""
        return list(self.performance_weights.keys())

    def compute_weighted_performance(self, metrics: Dict[str, float]) -> float:
        """
        Compute weighted performance index.

        Args:
            metrics: Dictionary of performance metrics

        Returns:
            Weighted performance index (lower is better)
        """
        weighted_sum = 0.0
        for metric_name, weight in self.performance_weights.items():
            if metric_name in metrics:
                weighted_sum += weight * metrics[metric_name]
            else:
                raise ValueError(f"Missing performance metric: {metric_name}")

        return weighted_sum

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        result = {
            'hybrid_mode': self.hybrid_mode.value,
            'dt': self.dt,
            'max_force': self.max_force,
            'switching_criterion': self.switching_criterion.value,
            'switching_thresholds': list(self.switching_thresholds),
            'hysteresis_margin': self.hysteresis_margin,
            'min_switching_time': self.min_switching_time,
            'performance_window': self.performance_window,
            'performance_weights': dict(self.performance_weights),
            'enable_predictive_switching': self.enable_predictive_switching,
            'prediction_horizon': self.prediction_horizon,
            'enable_learning': self.enable_learning,
            'learning_rate': self.learning_rate,
            'transition_smoothing': self.transition_smoothing,
            'smoothing_time_constant': self.smoothing_time_constant
        }

        # Add individual controller configs
        if self.classical_config is not None:
            result['classical_config'] = self.classical_config.to_dict()
        if self.adaptive_config is not None:
            result['adaptive_config'] = self.adaptive_config.to_dict()
        if self.supertwisting_config is not None:
            result['supertwisting_config'] = self.supertwisting_config.to_dict()

        return result

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any], dynamics_model=None) -> 'HybridSMCConfig':
        """Create configuration from dictionary."""
        config_dict = config_dict.copy()

        # Convert enum strings back to enums
        config_dict['hybrid_mode'] = HybridMode(config_dict['hybrid_mode'])
        config_dict['switching_criterion'] = SwitchingCriterion(config_dict['switching_criterion'])

        # Reconstruct individual controller configs
        if 'classical_config' in config_dict:
            config_dict['classical_config'] = ClassicalSMCConfig.from_dict(
                config_dict['classical_config'], dynamics_model
            )
        if 'adaptive_config' in config_dict:
            config_dict['adaptive_config'] = AdaptiveSMCConfig.from_dict(
                config_dict['adaptive_config'], dynamics_model
            )
        if 'supertwisting_config' in config_dict:
            config_dict['supertwisting_config'] = SuperTwistingSMCConfig.from_dict(
                config_dict['supertwisting_config'], dynamics_model
            )

        config_dict['dynamics_model'] = dynamics_model
        return cls(**config_dict)

    @classmethod
    def create_classical_adaptive_hybrid(cls, classical_gains: List[float], adaptive_gains: List[float],
                                        dt: float = 0.01, max_force: float = 100.0, **kwargs) -> 'HybridSMCConfig':
        """Create Classical-Adaptive hybrid configuration."""
        classical_config = ClassicalSMCConfig(
            gains=classical_gains, dt=dt, max_force=max_force, boundary_layer=0.01
        )
        adaptive_config = AdaptiveSMCConfig(
            gains=adaptive_gains, dt=dt, max_force=max_force
        )

        return cls(
            hybrid_mode=HybridMode.CLASSICAL_ADAPTIVE,
            dt=dt,
            max_force=max_force,
            classical_config=classical_config,
            adaptive_config=adaptive_config,
            **kwargs
        )

    @classmethod
    def create_adaptive_supertwisting_hybrid(cls, adaptive_gains: List[float],
                                           supertwisting_gains: List[float],
                                           dt: float = 0.01, max_force: float = 100.0, **kwargs) -> 'HybridSMCConfig':
        """Create Adaptive-SuperTwisting hybrid configuration."""
        adaptive_config = AdaptiveSMCConfig(
            gains=adaptive_gains, dt=dt, max_force=max_force
        )
        supertwisting_config = SuperTwistingSMCConfig(
            gains=supertwisting_gains, dt=dt, max_force=max_force
        )

        return cls(
            hybrid_mode=HybridMode.ADAPTIVE_SUPERTWISTING,
            dt=dt,
            max_force=max_force,
            adaptive_config=adaptive_config,
            supertwisting_config=supertwisting_config,
            **kwargs
        )