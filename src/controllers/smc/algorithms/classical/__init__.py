#==========================================================================================\\\
#================ src/controllers/smc/algorithms/classical/__init__.py ================\\\
#==========================================================================================\\\

"""
Classical SMC Algorithm Package.

Modular implementation of Classical Sliding Mode Control split into focused components:
- Controller: Main orchestration and control computation
- Boundary Layer: Chattering reduction through boundary layer method
- Configuration: Type-safe parameter configuration

This replaces the monolithic 458-line classical SMC with focused modules.
"""

from .controller import ModularClassicalSMC
from .boundary_layer import BoundaryLayer
from .config import ClassicalSMCConfig

# Backward compatibility facade
from .controller import ClassicalSMC

__all__ = [
    # Modular components
    "ModularClassicalSMC",
    "BoundaryLayer",
    "ClassicalSMCConfig",

    # Backward compatibility
    "ClassicalSMC"
]