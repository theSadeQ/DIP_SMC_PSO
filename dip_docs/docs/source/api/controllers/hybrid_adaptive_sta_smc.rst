========================
Hybrid Adaptive STA SMC
========================
.. currentmodule:: src.controllers.hybrid_adaptive_sta_smc

Overview
--------
This module implements a hybrid adaptive super-twisting sliding-mode controller that combines the benefits of the Super-Twisting Algorithm with adaptive mechanisms. It provides finite-time convergence, continuous control, and online adaptation to uncertain parameters, making it highly robust for double-inverted pendulum control under varying conditions.

Examples
--------
.. doctest::

   >>> from src.controllers.hybrid_adaptive_sta_smc import HybridAdaptiveSTASMC
   >>> import numpy as np
   >>> # Create hybrid adaptive controller
   >>> controller = HybridAdaptiveSTASMC()
   >>>
   >>> # Initialize with hybrid gains including adaptation parameters
   >>> gains = np.array([10.0, 5.0, 2.0, 1.0, 25.0, 15.0, 0.5, 1.0])
   >>> controller = HybridAdaptiveSTASMC(gains)

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.controllers.hybrid_adaptive_sta_smc

Detailed API
------------
.. automodule:: src.controllers.hybrid_adaptive_sta_smc
   :members:
   :undoc-members:
   :show-inheritance: