#==========================================================================================\\\
#========================== src/controllers/mpc_controller.py ===========================\\\
#==========================================================================================\\\

"""
Compatibility import for MPC controller.

This module provides backward compatibility for old import paths.
The actual implementation is in src.controllers.mpc.mpc_controller.

Usage:
    from src.controllers.mpc_controller import MPCController  # Old style (works)
    from src.controllers import MPCController                 # New style (preferred)
"""

# Import from the actual location
from .mpc.mpc_controller import MPCController, MPCWeights, _numeric_linearize_continuous

# Export for backward compatibility
__all__ = ["MPCController", "MPCWeights", "_numeric_linearize_continuous"]