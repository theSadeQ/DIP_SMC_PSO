========================
Numba Utils
========================
.. currentmodule:: src.core.numba_utils

Overview
--------
Utilities for configuring Numba at runtime.

Examples
--------
.. doctest::

   >>> import os, tempfile
   >>> from src.core.numba_utils import configure_numba
   >>> tmp = tempfile.mkdtemp()
   >>> configure_numba(cache_dir=tmp, threading_layer="workqueue")
   >>> os.environ.get("NUMBA_CACHE_DIR", "").startswith(tmp)
   True
   >>> os.environ.get("NUMBA_THREADING_LAYER")
   'workqueue'

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.core.numba_utils

Detailed API
------------
.. automodule:: src.core.numba_utils
   :members:
   :undoc-members:
   :show-inheritance:
