========================
Control Primitives
========================
.. currentmodule:: src.utils.control_primitives

Overview
--------
This module provides utilities for control primitives, including the require_positive, require_in_range, saturate functions.

Examples
--------
.. doctest::

   >>> from src.utils.control_primitives import require_positive, saturate
   >>> import numpy as np
   >>> # Validate positive control gains
   >>> gain = require_positive(5.0, "controller_gain")
   >>> gain
   5.0
   >>> # Saturate sliding surface for boundary layer
   >>> sigma = np.array([-2.0, 0.5, 3.0])
   >>> saturated = saturate(sigma, epsilon=1.0, method="tanh")
   >>> saturated
   array([-0.96402758,  0.46211716,  0.99505475])

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.utils.control_primitives

Detailed API
------------
.. automodule:: src.utils.control_primitives
   :members:
   :undoc-members:
   :show-inheritance:
