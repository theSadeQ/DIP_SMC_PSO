#==========================================================================================\\\
#=================== src/optimization/objectives/control/__init__.py ==================\\\
#==========================================================================================\\\

"""Control performance objective functions."""

from .tracking import TrackingErrorObjective
from .energy import EnergyConsumptionObjective, ControlEffortObjective
from .stability import StabilityMarginObjective
from .robustness import RobustnessObjective

__all__ = [
    "TrackingErrorObjective",
    "EnergyConsumptionObjective",
    "ControlEffortObjective",
    "StabilityMarginObjective",
    "RobustnessObjective"
]