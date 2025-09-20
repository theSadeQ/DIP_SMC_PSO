========================
Statistics
========================
.. currentmodule:: src.utils.statistics

Overview
--------
Statistical utilities for performance analysis.

Examples
--------
.. doctest::

   >>> import numpy as np
   >>> from src.utils.statistics import confidence_interval
   >>> rng = np.random.default_rng(0)
   >>> # 200 noisy samples of a zero-mean metric (e.g., RMS tracking error)
   >>> samples = rng.normal(loc=0.0, scale=1.0, size=200)
   >>> mean, half = confidence_interval(samples, confidence=0.95)
   >>> # Mean is near 0 and the 95% half-width is suitably small for n=200
   >>> (abs(mean) < 0.2) and (0.0 < half < 0.2)
   True

   >>> # Edge case: fewer than two samples → half-width is NaN
   >>> m1, h1 = confidence_interval(np.array([1.0]))
   >>> (np.isfinite(m1), np.isnan(h1))
   (True, True)

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.utils.statistics

Detailed API
------------
.. automodule:: src.utils.statistics
   :members:
   :undoc-members:
   :show-inheritance:
