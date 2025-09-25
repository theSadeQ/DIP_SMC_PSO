#==========================================================================================\\\
#==================================== src/optimizer/__init__.py ===========================\\\
#==========================================================================================\\\
"""
Optimizer compatibility layer.
This module provides backward compatibility by re-exporting optimizer classes
from their new modular locations, allowing legacy import paths to continue working.
"""

# Re-export PSO optimizer from new location
from ..optimization.algorithms.pso_optimizer import PSOTuner

__all__ = ['PSOTuner']