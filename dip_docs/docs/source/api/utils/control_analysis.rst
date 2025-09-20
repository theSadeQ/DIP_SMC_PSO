========================
Control Analysis
========================
.. currentmodule:: src.utils.control_analysis

Overview
--------
Linearisation and controllability/observability analysis utilities.

Examples
--------
.. doctest::

   >>> import numpy as np
   >>> from src.utils.control_analysis import controllability_matrix, observability_matrix, check_controllability_observability
   >>> # Simple 2-state double integrator: x' = [0 1; 0 0] x + [0; 1] u, y = [1 0] x
   >>> A = np.array([[0.0, 1.0],
   ...               [0.0, 0.0]])
   >>> B = np.array([[0.0],
   ...               [1.0]])
   >>> C = np.array([[1.0, 0.0]])
   >>> # Controllability/observability matrices and rank checks
   >>> Ctrb = controllability_matrix(A, B)
   >>> Obsv = observability_matrix(A, C)
   >>> Ctrb.shape, Obsv.shape
   ((2, 2), (2, 2))
   >>> check_controllability_observability(A, B, C)
   (True, True)

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.utils.control_analysis

Detailed API
------------
.. automodule:: src.utils.control_analysis
   :members:
   :undoc-members:
   :show-inheritance:
