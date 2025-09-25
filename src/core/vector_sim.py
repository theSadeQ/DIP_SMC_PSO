#==========================================================================================\\\
#============================ src/core/vector_sim.py ============================\\\
#==========================================================================================\\\
"""
Compatibility import module for vector simulation functionality.

This module provides backward compatibility for test modules that expect
vector simulation components at src.core.vector_sim. All functionality
is re-exported from the actual implementation location.
"""

# Import all components from the actual vector_sim location
from src.simulation.engines.vector_sim import *

# Explicitly import key functions that actually exist
from src.simulation.engines.vector_sim import (
    simulate,
    simulate_system_batch,
)

# Keep compatibility with old import patterns
__all__ = [
    'simulate',
    'simulate_system_batch',
]