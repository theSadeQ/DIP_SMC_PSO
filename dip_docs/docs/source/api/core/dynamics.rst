========================
Dynamics
========================
.. currentmodule:: src.core.dynamics

Overview
--------
This module provides the simplified dynamics model for the double-inverted pendulum system with numerical stability enhancements. It implements linearized equations of motion suitable for control design and rapid simulation, with built-in safeguards against numerical instabilities and singular configurations.

Examples
--------
.. doctest::

   >>> from src.core.dynamics import DoubleInvertedPendulum, DIPParams
   >>> import numpy as np
   >>> # Create dynamics model with default parameters
   >>> params = DIPParams()
   >>> model = DoubleInvertedPendulum(params)
   >>>
   >>> # Compute dynamics for a given state and control
   >>> state = np.array([0.1, 0.0, 0.1, 0.0])  # [theta1, omega1, theta2, omega2]
   >>> u = 1.0  # control input
   >>> x_dot = model.dynamics(0.0, state, u)
   >>> len(x_dot) == 4
   True

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.core.dynamics

Detailed API
------------
.. automodule:: src.core.dynamics
   :members:
   :undoc-members:
   :show-inheritance: