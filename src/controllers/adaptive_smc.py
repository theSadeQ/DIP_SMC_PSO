#==========================================================================================\\\
#========================== src/controllers/adaptive_smc.py =============================\\\
#==========================================================================================\\\

"""
Compatibility import for Adaptive SMC controller.

This module provides backward compatibility for old import paths.
The actual implementation is in src.controllers.smc.adaptive_smc.

Usage:
    from src.controllers.adaptive_smc import AdaptiveSMC  # Old style (works)
    from src.controllers import AdaptiveSMC               # New style (preferred)
"""

# Import from the actual location
from .smc.adaptive_smc import AdaptiveSMC

# Export for backward compatibility
__all__ = ["AdaptiveSMC"]