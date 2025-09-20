========================
Seed
========================
.. currentmodule:: src.utils.seed

Overview
--------
Global seeding utilities for reproducible simulations.

Examples
--------
.. doctest::

   >>> from src.utils.seed import set_global_seed
   >>> # Set reproducible random seed for simulation
   >>> set_global_seed(42)
   >>> import numpy as np
   >>> # Verify reproducible random numbers
   >>> np.random.rand(3)  # doctest: +SKIP
   array([0.37454012, 0.95071431, 0.73199394])

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.utils.seed

Detailed API
------------
.. automodule:: src.utils.seed
   :members:
   :undoc-members:
   :show-inheritance:
