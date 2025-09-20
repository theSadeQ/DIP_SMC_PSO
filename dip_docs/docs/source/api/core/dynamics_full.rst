========================
Full Nonlinear Dynamics
========================
.. currentmodule:: src.core.dynamics_full

Overview
--------
Complete nonlinear dynamics model for the double-inverted pendulum system including all coupling terms, friction effects, and system constraints. Provides high-fidelity simulation with Numba acceleration for performance-critical applications and control algorithm validation.

Examples
--------
.. doctest::

   >>> from src.core.dynamics_full import DPDynamicsFull
   >>> import numpy as np
   >>> # Create full dynamics model with physical parameters
   >>> dynamics = DPDynamicsFull(
   ...     m1=0.5, m2=0.5, l1=0.5, l2=0.5,
   ...     dt=0.001, use_friction=True
   ... )
   >>> # Simulate one step with state and control input
   >>> state = np.array([0.1, 0.0, 0.1, 0.0])  # [theta1, omega1, theta2, omega2]
   >>> u = np.array([1.0])  # Control force
   >>> next_state = dynamics.step(state, u)

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.core.dynamics_full

Detailed API
------------
.. automodule:: src.core.dynamics_full
   :members:
   :undoc-members:
   :show-inheritance: