#==========================================================================================\\\
#====================== src/plant/models/simplified/__init__.py ========================\\\
#==========================================================================================\\\

"""
Simplified Double Inverted Pendulum Model.

Modular implementation of the simplified DIP dynamics with:
- Focused physics computation
- Type-safe configuration
- Numerical stability features
- Performance optimizations

Refactored from the monolithic 688-line dynamics.py file.
"""

from .config import SimplifiedDIPConfig
from .physics import SimplifiedPhysicsComputer
from .dynamics import SimplifiedDIPDynamics

__all__ = [
    "SimplifiedDIPConfig",
    "SimplifiedPhysicsComputer",
    "SimplifiedDIPDynamics"
]