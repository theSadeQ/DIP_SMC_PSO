#==========================================================================================\\\
#=========================== src/plant/models/dynamics.py ==============================\\\
#==========================================================================================\\\
"""
Plant models dynamics compatibility layer.
This module re-exports the dynamics classes and parameters from their new locations
for backward compatibility with legacy import paths.
"""

# Re-export main dynamics classes from compatibility layers
from ...core.dynamics import DIPDynamics, DoubleInvertedPendulum, DIPParams

__all__ = ['DIPDynamics', 'DoubleInvertedPendulum', 'DIPParams']