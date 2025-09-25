#==========================================================================================\\\
#======================================= src/core/__init__.py ===============================\\\
#==========================================================================================\\\
"""
Core module compatibility layer.
This module provides backward compatibility by re-exporting classes and functions
from their new modular locations, allowing legacy import paths to continue working
while maintaining the improved project structure.
"""

# Re-export dynamics models from their new locations
from ..plant.models.simplified.dynamics import SimplifiedDIPDynamics as DIPDynamics
from ..plant.models.full.dynamics import FullDIPDynamics
from ..plant.models.lowrank.dynamics import LowRankDIPDynamics

# Re-export simulation components - only what actually exists
from ..simulation.core.simulation_context import SimulationContext
from ..simulation.engines.simulation_runner import run_simulation

# Legacy aliases for backward compatibility
DoubleInvertedPendulum = DIPDynamics  # Common legacy alias

__all__ = [
    # Main dynamics classes
    'DIPDynamics',
    'FullDIPDynamics',
    'LowRankDIPDynamics',

    # Simulation components
    'SimulationContext',
    'run_simulation',

    # Legacy aliases
    'DoubleInvertedPendulum',
]