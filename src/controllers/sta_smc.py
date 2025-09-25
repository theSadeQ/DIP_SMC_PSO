#==========================================================================================\\\
#============================ src/controllers/sta_smc.py ===============================\\\
#==========================================================================================\\\

"""
Compatibility import for Super-Twisting SMC controller.

This module provides backward compatibility for old import paths.
The actual implementation is in src.controllers.smc.sta_smc.

Usage:
    from src.controllers.sta_smc import SuperTwistingSMC  # Old style (works)
    from src.controllers import SuperTwistingSMC         # New style (preferred)
"""

# Import from the actual location
from .smc.sta_smc import SuperTwistingSMC

# Export for backward compatibility
__all__ = ["SuperTwistingSMC"]