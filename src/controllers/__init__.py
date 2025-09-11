"""
Public controllers API.
Import from here in library/app code and tests:
    from src.controllers import (
        ClassicalSMC, SuperTwistingSMC, AdaptiveSMC, HybridAdaptiveSTASMC,
        SwingUpSMC, MPCController, create_controller,
    )
"""

# Re-exports (fail gracefully if a module is missing during partial refactors)
try:
    from .classic_smc import ClassicalSMC
except Exception:  # pragma: no cover
    ClassicalSMC = None  # type: ignore

try:
    from .sta_smc import SuperTwistingSMC
except Exception:  # pragma: no cover
    SuperTwistingSMC = None  # type: ignore

try:
    from .adaptive_smc import AdaptiveSMC
except Exception:  # pragma: no cover
    AdaptiveSMC = None  # type: ignore

try:
    from .hybrid_adaptive_sta_smc import HybridAdaptiveSTASMC
except Exception:  # pragma: no cover
    HybridAdaptiveSTASMC = None  # type: ignore

try:
    from .swing_up_smc import SwingUpSMC
except Exception:  # pragma: no cover
    SwingUpSMC = None  # type: ignore

try:
    from .mpc_controller import MPCController
except Exception:  # pragma: no cover
    MPCController = None  # type: ignore

try:
    from .factory import create_controller
except Exception:  # pragma: no cover
    create_controller = None  # type: ignore

__all__ = [
    "ClassicalSMC",
    "SuperTwistingSMC",
    "AdaptiveSMC",
    "HybridAdaptiveSTASMC",
    "SwingUpSMC",
    "MPCController",
    "create_controller",
]
