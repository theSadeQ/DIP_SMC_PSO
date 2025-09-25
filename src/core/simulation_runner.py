#==========================================================================================\\\
#=========================== src/core/simulation_runner.py =================================\\\
#==========================================================================================\\\
"""
Simulation runner compatibility layer.
This module re-exports the simulation runner from its new modular location
for backward compatibility with legacy import paths.
"""

# Re-export simulation runner function from new location
from ..simulation.engines.simulation_runner import run_simulation

__all__ = ['run_simulation']