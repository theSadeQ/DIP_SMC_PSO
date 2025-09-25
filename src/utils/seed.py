#==========================================================================================\\\
#======================================= src/utils/seed.py ================================\\\
#==========================================================================================\\\
"""
Seed utilities compatibility layer.
This module re-exports the seed functions from their new modular location
for backward compatibility with legacy import paths.
"""

# Re-export seed functions from new location
from .reproducibility.seed import set_global_seed, create_rng

__all__ = ['set_global_seed', 'create_rng']