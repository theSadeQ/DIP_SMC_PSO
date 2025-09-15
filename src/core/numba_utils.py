#==========================================================================================\\
#=============================== src/core/numba_utils.py ===============================\\
#==========================================================================================\\
"""Utilities for configuring Numba at runtime.

This module exposes a helper to set Numba cache and threading
configuration in a controlled manner.  Previously the batch simulator
(`vector_sim.py`) unconditionally set environment variables
``NUMBA_CACHE_DIR`` and ``NUMBA_THREADING_LAYER`` at import time.  This
practice can interfere with other components in the same Python process
and lead to non‑deterministic behaviour.  Following reproducibility
guidelines, configuration should be performed explicitly by the caller
rather than globally at import.

Callers may invoke :func:`configure_numba` early in the program to
establish a preferred cache directory and threading layer.  If no
threading layer is specified, Numba's default selection is used.  When
``cache_dir`` is provided, the function ensures that the directory
exists before assigning it to the ``NUMBA_CACHE_DIR`` environment
variable.
"""

from __future__ import annotations

import os
from typing import Optional


def configure_numba(cache_dir: Optional[str] = None, threading_layer: Optional[str] = None) -> None:
    """Configure Numba's cache directory and threading layer.

    Parameters
    ----------
    cache_dir : str or None, optional
        The directory to use for caching compiled Numba functions.  When
        ``None`` the existing ``NUMBA_CACHE_DIR`` environment variable is
        left unchanged.  If a non‑empty string is provided, the
        directory is created if it does not already exist, and the
        environment variable ``NUMBA_CACHE_DIR`` is set to this path.

    threading_layer : str or None, optional
        The threading backend to use (e.g., ``"tbb"``, ``"omp"`` or
        ``"workqueue"``).  When ``None`` the existing
        ``NUMBA_THREADING_LAYER`` environment variable is left unchanged.
        When a value is provided, it is assigned to
        ``NUMBA_THREADING_LAYER``.  Invalid threading layers will be
        detected and raise a ``ValueError`` when Numba subsequently
        selects a backend.

    Notes
    -----
    Numba selects its threading backend at the time of the first
    compilation.  Therefore, callers should invoke this function before
    importing modules that compile Numba functions (such as
    :mod:`src.core.vector_sim`).  The configuration is stored in the
    environment, so it persists for the duration of the process.
    """
    if cache_dir:
        # Ensure the cache directory exists before assigning
        os.makedirs(cache_dir, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = cache_dir
    if threading_layer:
        os.environ["NUMBA_THREADING_LAYER"] = threading_layer