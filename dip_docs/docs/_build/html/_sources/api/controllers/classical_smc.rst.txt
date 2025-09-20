========================
Classical SMC
========================
.. currentmodule:: src.controllers.classic_smc

Overview
--------
This module implements the conventional first-order sliding-mode controller for a double-inverted pendulum, consisting of a model-based equivalent control and a robust discontinuous term. The controller uses a continuous approximation to the sign function within a boundary layer to attenuate chattering while maintaining robust tracking performance.

Examples
--------
.. doctest::

   >>> from src.controllers.classic_smc import ClassicalSMC
   >>> import numpy as np
   >>> # Create controller with default gains
   >>> controller = ClassicalSMC()
   >>>
   >>> # Set specific gains: [k1, k2, k3, k4, ksw, epsilon]
   >>> gains = np.array([10.0, 5.0, 2.0, 1.0, 50.0, 0.1])
   >>> controller = ClassicalSMC(gains)
   >>>
   >>> # Check controller properties
   >>> controller.n_gains
   6

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.controllers.classic_smc

Detailed API
------------
.. automodule:: src.controllers.classic_smc
   :members:
   :undoc-members:
   :show-inheritance: