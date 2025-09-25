#==========================================================================================\\\
#======================== src/plant/core/dynamics.py ========================\\\
#==========================================================================================\\\
"""
Plant core dynamics compatibility module.

This module provides backward compatibility for test modules that expect
plant dynamics components at src.plant.core.dynamics. All functionality
is re-exported from the actual implementation locations.
"""

# Import all dynamics functionality from existing locations
from ...core.dynamics import *
from ..models.dynamics import *

# Also import from specific model implementations
try:
    from ..models.full.dynamics import *
except ImportError:
    pass

try:
    from ..models.simplified.dynamics import *
except ImportError:
    pass

try:
    from ..models.lowrank.dynamics import *
except ImportError:
    pass

# Explicitly re-export key classes
from ...core.dynamics import DIPDynamics, DoubleInvertedPendulum, DIPParams

__all__ = [
    'DIPDynamics',
    'DoubleInvertedPendulum',
    'DIPParams',
]