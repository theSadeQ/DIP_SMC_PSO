#==========================================================================================\\\
#======================= src/plant/models/lowrank/__init__.py ===========================\\\
#==========================================================================================\\\

"""
Low-rank Double Inverted Pendulum (DIP) Model Package.

Simplified implementation optimized for computational efficiency and fast prototyping.
Provides reduced-order dynamics while maintaining essential system behavior.
"""

from .config import LowRankDIPConfig
from .physics import LowRankPhysicsComputer
from .dynamics import LowRankDIPDynamics

__all__ = [
    "LowRankDIPConfig",
    "LowRankPhysicsComputer",
    "LowRankDIPDynamics"
]