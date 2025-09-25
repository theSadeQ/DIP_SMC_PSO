#==========================================================================================\\\
#============================= src/simulation/core/__init__.py =============================\\\
#==========================================================================================\\\

"""Core simulation framework interfaces and abstractions."""

from .interfaces import (
    SimulationEngine,
    Integrator,
    Orchestrator,
    SimulationStrategy,
    SafetyGuard,
    ResultContainer
)
from .simulation_context import SimulationContext
from .state_space import StateSpaceUtilities
from .time_domain import TimeManager

__all__ = [
    "SimulationEngine",
    "Integrator",
    "Orchestrator",
    "SimulationStrategy",
    "SafetyGuard",
    "ResultContainer",
    "SimulationContext",
    "StateSpaceUtilities",
    "TimeManager"
]