========================
Simulation Runner
========================
.. currentmodule:: src.core.simulation_runner

Overview
--------
This module provides the main simulation orchestration for running single and batch simulations of the double-inverted pendulum system with various controllers. It handles integration stepping, data collection, and result formatting for analysis and visualization.

Examples
--------
.. doctest::

   >>> from src.core.simulation_runner import SimulationRunner
   >>> from src.controllers.classic_smc import ClassicalSMC
   >>> from src.core.dynamics import DoubleInvertedPendulum, DIPParams
   >>> import numpy as np
   >>>
   >>> # Create simulation components
   >>> controller = ClassicalSMC()
   >>> params = DIPParams()
   >>> dynamics = DoubleInvertedPendulum(params)
   >>>
   >>> # Initialize simulation runner
   >>> runner = SimulationRunner(dynamics, controller)
   >>> runner is not None
   True

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.core.simulation_runner

Detailed API
------------
.. automodule:: src.core.simulation_runner
   :members:
   :undoc-members:
   :show-inheritance: