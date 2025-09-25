#==========================================================================================\\\
#======================== src/optimization/objectives/__init__.py ======================\\\
#==========================================================================================\\\

"""Optimization objective functions for control engineering applications."""

# Control Performance Objectives
from .control.tracking import TrackingErrorObjective
from .control.energy import EnergyConsumptionObjective, ControlEffortObjective
from .control.stability import StabilityMarginObjective
from .control.robustness import RobustnessObjective

# System Performance Objectives
from .system.settling_time import SettlingTimeObjective, RiseTimeObjective
from .system.overshoot import OvershootObjective, UndershootObjective
from .system.steady_state import SteadyStateErrorObjective

# Multi-Objective Combinations
from .multi.weighted_sum import WeightedSumObjective, AdaptiveWeightedSumObjective
from .multi.pareto import ParetoObjective

# Base Classes
from .base import (
    SimulationBasedObjective,
    AnalyticalObjective,
    CompositeObjective
)

__all__ = [
    # Control objectives
    "TrackingErrorObjective",
    "EnergyConsumptionObjective",
    "ControlEffortObjective",
    "StabilityMarginObjective",
    "RobustnessObjective",

    # System objectives
    "SettlingTimeObjective",
    "RiseTimeObjective",
    "OvershootObjective",
    "UndershootObjective",
    "SteadyStateErrorObjective",

    # Multi-objective
    "WeightedSumObjective",
    "AdaptiveWeightedSumObjective",
    "ParetoObjective",

    # Base classes
    "SimulationBasedObjective",
    "AnalyticalObjective",
    "CompositeObjective"
]