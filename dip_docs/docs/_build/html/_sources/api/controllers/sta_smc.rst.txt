========================
STA SMC
========================
.. currentmodule:: src.controllers.sta_smc

Overview
--------
This module implements the Super-Twisting Algorithm (STA) sliding-mode controller, which provides finite-time convergence and continuous control signals without chattering. The STA is a second-order sliding-mode algorithm that maintains robustness while eliminating the high-frequency switching characteristic of traditional sliding-mode controllers.

Examples
--------
.. doctest::

   >>> from src.controllers.sta_smc import STASMC
   >>> import numpy as np
   >>> # Create STA controller with default parameters
   >>> controller = STASMC()
   >>>
   >>> # Initialize with specific STA gains
   >>> gains = np.array([10.0, 5.0, 2.0, 1.0, 25.0, 15.0])  # [k1, k2, k3, k4, alpha, beta]
   >>> controller = STASMC(gains)

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.controllers.sta_smc

Detailed API
------------
.. automodule:: src.controllers.sta_smc
   :members:
   :undoc-members:
   :show-inheritance: