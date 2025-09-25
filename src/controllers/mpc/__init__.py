#==========================================================================================\\\
#=============================== src/controllers/mpc/__init__.py ===========================\\\
#==========================================================================================\\\

"""Model Predictive Controllers for the double inverted pendulum system."""

from .mpc_controller import MPCController, MPCWeights

__all__ = [
    "MPCController",
    "MPCWeights",
]