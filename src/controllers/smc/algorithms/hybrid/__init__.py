#==========================================================================================\\\
#================= src/controllers/smc/algorithms/hybrid/__init__.py =================\\\
#==========================================================================================\\\

"""
Hybrid SMC Algorithm Package.

Modular implementation of Hybrid Sliding Mode Control that intelligently
switches between multiple SMC algorithms based on system conditions:

- Controller: Main orchestration with intelligent switching
- SwitchingLogic: Decision-making logic for controller selection
- Configuration: Type-safe parameter configuration for hybrid operation

This provides optimal performance by selecting the most appropriate SMC algorithm
for current operating conditions, with smooth transitions and performance monitoring.
"""

from .controller import ModularHybridSMC, HybridSMC
from .switching_logic import HybridSwitchingLogic, SwitchingDecision, ControllerState
from .config import HybridSMCConfig, HybridMode, SwitchingCriterion

__all__ = [
    # Main controller
    "ModularHybridSMC",
    "HybridSMC",  # Backward compatibility

    # Components
    "HybridSwitchingLogic",
    "SwitchingDecision",
    "ControllerState",

    # Configuration
    "HybridSMCConfig",
    "HybridMode",
    "SwitchingCriterion"
]