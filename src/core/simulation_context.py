#==========================================================================================\\\
#============================ src/core/simulation_context.py ==============================\\\
#==========================================================================================\\\
"""
Simulation context compatibility layer.
This module re-exports the simulation context from its new modular location
for backward compatibility with legacy import paths.
"""

# Re-export simulation context from new location
from ..simulation.core.simulation_context import SimulationContext

__all__ = ['SimulationContext']