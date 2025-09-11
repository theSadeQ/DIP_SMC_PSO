"""
Public controllers API.
Usage:
    from src.controllers import (
        ClassicalSMC, SuperTwistingSMC, AdaptiveSMC, HybridAdaptiveSTASMC,
        SwingUpSMC, MPCController, create_controller,
    )
"""

from .classic_smc import ClassicalSMC
from .sta_smc import SuperTwistingSMC
from .adaptive_smc import AdaptiveSMC

try:
    from .hybrid_adaptive_sta_smc import HybridAdaptiveSTASMC
except Exception:  # optional
    HybridAdaptiveSTASMC = None  # type: ignore
try:
    from .swing_up_smc import SwingUpSMC
except Exception:
    SwingUpSMC = None  # type: ignore
try:
    from .mpc_controller import MPCController
except Exception:
    MPCController = None  # type: ignore
from .factory import create_controller

__all__ = [
    "ClassicalSMC",
    "SuperTwistingSMC",
    "AdaptiveSMC",
    "HybridAdaptiveSTASMC",
    "SwingUpSMC",
    "MPCController",
    "create_controller",
]
