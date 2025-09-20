========================
Visualization
========================
.. currentmodule:: src.utils.visualization

Overview
--------
Utility for visualising a double–inverted-pendulum simulation.

Examples
--------
.. doctest::

   >>> import numpy as np
   >>> from math import pi
   >>> from src.utils.visualization import Visualizer
   >>> # Minimal pendulum model (lengths used by Visualizer for link endpoints)
   >>> class DummyPendulum:
   ...     l1 = 0.5
   ...     l2 = 0.5
   ...     L1 = 0.5
   >>> N, dt = 5, 0.1
   >>> t = np.linspace(0.0, N*dt, N+1)
   >>> # State: [x, th1, th2, xdot, th1dot, th2dot]
   >>> x = np.zeros((N+1, 6), dtype=float)
   >>> x[:, 1] = np.linspace(0, 5*pi/180, N+1)   # small motion in θ1
   >>> x[:, 2] = np.linspace(0, -5*pi/180, N+1)  # small motion in θ2
   >>> u = np.zeros(N, dtype=float)
   >>> vis = Visualizer(DummyPendulum())
   >>> ani = vis.animate(t, x, u, dt=dt)
   >>> hasattr(ani, "save") and hasattr(ani, "event_source")
   True

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.utils.visualization

Detailed API
------------
.. automodule:: src.utils.visualization
   :members:
   :undoc-members:
   :show-inheritance:
