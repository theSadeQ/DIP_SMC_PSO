#==========================================================================================\\\
#========================= src/simulation/strategies/__init__.py ========================\\\
#==========================================================================================\\\
"""
Simulation analysis strategies and paradigms.
This module provides various strategies for simulation analysis including
Monte Carlo methods, sensitivity analysis, and parametric studies.
"""

# Import only what actually exists
from .monte_carlo import MonteCarloStrategy

__all__ = [
    "MonteCarloStrategy",
]

# Placeholder for future strategy implementations:
# from .sensitivity import SensitivityAnalysis
# from .parametric import ParametricSweep
# from .optimization import SimulationBasedOptimization