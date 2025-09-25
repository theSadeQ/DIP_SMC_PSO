#==========================================================================================\\\
#======================== src/plant/models/full/__init__.py ============================\\\
#==========================================================================================\\\

"""
Full Fidelity Double Inverted Pendulum Model.

High-fidelity implementation with complete nonlinear dynamics,
advanced numerical integration, and comprehensive physics modeling.
"""

from .config import FullDIPConfig
from .physics import FullFidelityPhysicsComputer
from .dynamics import FullDIPDynamics

__all__ = [
    "FullDIPConfig",
    "FullFidelityPhysicsComputer",
    "FullDIPDynamics"
]