#==========================================================================================\\\
#========================= src/controllers/smc/core/__init__.py ========================\\\
#==========================================================================================\\\

"""
SMC Core Components - Shared logic across all SMC controllers.

Provides reusable components that implement fundamental SMC concepts:
- Sliding surface calculations
- Switching functions for chattering reduction
- Equivalent control computation
- Parameter validation
"""

from .sliding_surface import SlidingSurface, LinearSlidingSurface
from .switching_functions import SwitchingFunction, tanh_switching, linear_switching
from .equivalent_control import EquivalentControl
from .gain_validation import validate_smc_gains, SMCGainValidator

__all__ = [
    # Sliding surface components
    "SlidingSurface",
    "LinearSlidingSurface",

    # Switching functions
    "SwitchingFunction",
    "tanh_switching",
    "linear_switching",

    # Equivalent control
    "EquivalentControl",

    # Validation
    "validate_smc_gains",
    "SMCGainValidator"
]