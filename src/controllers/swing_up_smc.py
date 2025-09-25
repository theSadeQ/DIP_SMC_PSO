#==========================================================================================\\\
#======================== src/controllers/swing_up_smc.py ========================\\\
#==========================================================================================\\\
"""
Swing-up SMC controller compatibility module.

This module provides backward compatibility for test modules that expect
swing-up SMC functionality at src.controllers.swing_up_smc. All functionality
is re-exported from the actual implementation location.
"""

# Import all swing-up SMC functionality from the actual location
from .specialized.swing_up_smc import *

__all__ = []