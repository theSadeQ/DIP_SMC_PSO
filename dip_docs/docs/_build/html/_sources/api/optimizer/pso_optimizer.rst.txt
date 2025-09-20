========================
PSO Optimizer
========================
.. currentmodule:: src.optimizer.pso_optimizer

Overview
--------
This module provides the high-throughput, vectorised PSOTuner class that wraps a particle swarm optimisation algorithm around the vectorised simulation of a double inverted pendulum (DIP) system. It incorporates robust control theory practices with decoupled global state, explicit random number generation, dynamic instability penalties, and configurable cost normalisation.

Examples
--------
.. doctest::

   >>> from src.optimizer.pso_optimizer import PSOTuner
   >>> from src.config import load_config
   >>> # Create a simple controller factory
   >>> def controller_factory(gains):
   ...     from src.controllers.classic_smc import ClassicalSMC
   ...     return ClassicalSMC(gains)
   >>>
   >>> # Load configuration and create tuner
   >>> config = load_config('config.yaml')
   >>> tuner = PSOTuner(controller_factory, config, seed=42)
   >>>
   >>> # Run PSO optimization
   >>> result = tuner.optimise(iters_override=10, n_particles_override=20)
   >>> result['best_cost'] > 0  # Should find a valid cost
   True

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.optimizer.pso_optimizer

Detailed API
------------
.. automodule:: src.optimizer.pso_optimizer
   :members:
   :undoc-members:
   :show-inheritance: