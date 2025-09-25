#==========================================================================================\\\
#==================== src/controllers/smc/algorithms/__init__.py ====================\\\
#==========================================================================================\\\

"""
SMC Algorithms Package.

Comprehensive collection of Sliding Mode Control algorithms implemented
with modular architecture for clarity and best practices:

- Classical SMC: Traditional sliding mode control with boundary layer
- Adaptive SMC: Online gain adaptation for unknown uncertainties
- Super-Twisting SMC: Second-order sliding mode for finite-time convergence
- Hybrid SMC: Intelligent switching between multiple SMC algorithms

Each algorithm is split into focused components following single-responsibility principle.
"""

# Classical SMC
from .classical import ClassicalSMC, ModularClassicalSMC, ClassicalSMCConfig

# Adaptive SMC
from .adaptive import (
    AdaptiveSMC, ModularAdaptiveSMC, AdaptiveSMCConfig,
    AdaptationLaw, ModifiedAdaptationLaw,
    UncertaintyEstimator, ParameterIdentifier, CombinedEstimator
)

# Super-Twisting SMC
from .super_twisting import (
    SuperTwistingSMC, ModularSuperTwistingSMC, SuperTwistingSMCConfig,
    SuperTwistingAlgorithm
)

# Hybrid SMC
from .hybrid import (
    HybridSMC, ModularHybridSMC, HybridSMCConfig,
    HybridSwitchingLogic, SwitchingDecision, ControllerState,
    HybridMode, SwitchingCriterion
)

__all__ = [
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
    "SwitchingCriterion"
]