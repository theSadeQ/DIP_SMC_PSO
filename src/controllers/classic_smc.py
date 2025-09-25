#==========================================================================================\\\
#============================ src/controllers/classic_smc.py ============================\\\
#==========================================================================================\\\
"""
Classical SMC compatibility layer.
This module re-exports the ClassicalSMC class from its new modular location
for backward compatibility with legacy import paths.
"""

# Re-export ClassicalSMC from new location
from .smc.classic_smc import ClassicalSMC

__all__ = ['ClassicalSMC']