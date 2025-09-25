#==========================================================================================\\\
#============== src/controllers/smc/algorithms/super_twisting/__init__.py ==============\\\
#==========================================================================================\\\

"""
Super-Twisting SMC Algorithm Package.

Modular implementation of Super-Twisting Sliding Mode Control split into focused components:
- Controller: Main orchestration and Super-Twisting control computation
- SuperTwistingAlgorithm: Core second-order sliding mode algorithm
- Configuration: Type-safe parameter configuration with stability validation

This implements finite-time convergent sliding mode control with chattering reduction
through second-order sliding mode dynamics.
"""

from .controller import ModularSuperTwistingSMC, SuperTwistingSMC
from .twisting_algorithm import SuperTwistingAlgorithm
from .config import SuperTwistingSMCConfig

__all__ = [
    # Main controller
    "ModularSuperTwistingSMC",
    "SuperTwistingSMC",  # Backward compatibility

    # Components
    "SuperTwistingAlgorithm",

    # Configuration
    "SuperTwistingSMCConfig"
]