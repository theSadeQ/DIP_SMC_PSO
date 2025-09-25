#==========================================================================================\\\
#=================== src/optimization/objectives/multi/__init__.py =====================\\\
#==========================================================================================\\\
"""
Multi-objective optimization functions for control systems.
This module provides multi-objective cost functions that balance
competing control objectives like tracking performance, control effort,
robustness, and stability margins in control parameter tuning.
"""

from .weighted_sum import WeightedSumObjective, AdaptiveWeightedSumObjective
from .pareto import ParetoObjective

__all__ = [
    "WeightedSumObjective",
    "AdaptiveWeightedSumObjective",
    "ParetoObjective"
]