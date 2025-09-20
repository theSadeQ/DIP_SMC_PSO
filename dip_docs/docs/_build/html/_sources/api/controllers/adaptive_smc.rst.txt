========================
Adaptive SMC
========================
.. currentmodule:: src.controllers.adaptive_smc

Overview
--------
This module implements an adaptive sliding-mode controller that adjusts gains online to handle uncertainty in the double-inverted pendulum system. The controller combines conventional sliding-mode control with adaptive mechanisms that estimate unknown parameters and disturbances, providing robustness against model uncertainties.

Examples
--------
.. doctest::

   >>> from src.controllers.adaptive_smc import AdaptiveSMC
   >>> import numpy as np
   >>> # Create adaptive controller with default settings
   >>> controller = AdaptiveSMC()
   >>>
   >>> # Initialize with specific adaptation parameters
   >>> gains = np.array([10.0, 5.0, 2.0, 1.0, 50.0, 0.1, 0.5])  # Including adaptation rate
   >>> controller = AdaptiveSMC(gains)

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.controllers.adaptive_smc

Detailed API
------------
.. automodule:: src.controllers.adaptive_smc
   :members:
   :undoc-members:
   :show-inheritance: