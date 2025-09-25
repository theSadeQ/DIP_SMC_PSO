#==========================================================================================\\\
#=============================== src/controllers/smc/__init__.py ===========================\\\
#==========================================================================================\\\

"""
Sliding Mode Controllers for the double inverted pendulum system.

This package provides both legacy monolithic controllers and new modular implementations:

Legacy Controllers (for backward compatibility):
- ClassicalSMC (from classic_smc.py)
- AdaptiveSMC (from adaptive_smc.py)
- SuperTwistingSMC (from sta_smc.py)
- HybridAdaptiveSTASMC (from hybrid_adaptive_sta_smc.py)

New Modular Controllers (recommended for new development):
- All controllers from algorithms package with focused, single-responsibility modules
- Improved maintainability, testing, and extensibility
- Type-safe configurations with mathematical validation
"""

# Legacy monolithic controllers (backward compatibility)
from .classic_smc import ClassicalSMC as LegacyClassicalSMC
from .adaptive_smc import AdaptiveSMC as LegacyAdaptiveSMC
from .sta_smc import SuperTwistingSMC as LegacySuperTwistingSMC
from .hybrid_adaptive_sta_smc import HybridAdaptiveSTASMC

# New modular controllers (recommended)
from .algorithms import (
    # Classical SMC
    ClassicalSMC, ModularClassicalSMC, ClassicalSMCConfig,

    # Adaptive SMC
    AdaptiveSMC, ModularAdaptiveSMC, AdaptiveSMCConfig,
    AdaptationLaw, ModifiedAdaptationLaw,
    UncertaintyEstimator, ParameterIdentifier, CombinedEstimator,

    # Super-Twisting SMC
    SuperTwistingSMC, ModularSuperTwistingSMC, SuperTwistingSMCConfig,
    SuperTwistingAlgorithm,

    # Hybrid SMC
    HybridSMC, ModularHybridSMC, HybridSMCConfig,
    HybridSwitchingLogic, SwitchingDecision, ControllerState,
    HybridMode, SwitchingCriterion
)

# Core shared components
from .core import (
    SlidingSurface, LinearSlidingSurface,
    SwitchingFunction,
    EquivalentControl,
    validate_smc_gains, SMCGainValidator
)

__all__ = [
    # Legacy controllers (backward compatibility)
    "LegacyClassicalSMC",
    "LegacyAdaptiveSMC",
    "LegacySuperTwistingSMC",
    "HybridAdaptiveSTASMC",

    # New modular controllers (recommended)
    # Classical SMC
    "ClassicalSMC",
    "ModularClassicalSMC",
    "ClassicalSMCConfig",

    # Adaptive SMC
    "AdaptiveSMC",
    "ModularAdaptiveSMC",
    "AdaptiveSMCConfig",
    "AdaptationLaw",
    "ModifiedAdaptationLaw",
    "UncertaintyEstimator",
    "ParameterIdentifier",
    "CombinedEstimator",

    # Super-Twisting SMC
    "SuperTwistingSMC",
    "ModularSuperTwistingSMC",
    "SuperTwistingSMCConfig",
    "SuperTwistingAlgorithm",

    # Hybrid SMC
    "HybridSMC",
    "ModularHybridSMC",
    "HybridSMCConfig",
    "HybridSwitchingLogic",
    "SwitchingDecision",
    "ControllerState",
    "HybridMode",
    "SwitchingCriterion",

    # Core components
    "SlidingSurface",
    "LinearSlidingSurface",
    "SwitchingFunction",
    "EquivalentControl",
    "validate_smc_gains",
    "SMCGainValidator"
]