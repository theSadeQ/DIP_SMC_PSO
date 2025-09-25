#==========================================================================================\\\
#============================== src/optimizer/pso_optimizer.py ============================\\\
#==========================================================================================\\\
"""
PSO optimizer compatibility layer.
This module re-exports the PSO optimizer from its new modular location
for backward compatibility with legacy import paths.
"""

# Re-export PSO optimizer from new location
from ..optimization.algorithms.pso_optimizer import PSOTuner

__all__ = ['PSOTuner']