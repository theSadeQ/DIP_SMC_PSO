#==========================================================================================\\\
#==================================== src/utils/seed.py ===================================\\\
#==========================================================================================\\\
"""
Global seeding utilities for reproducible simulations.

This module centralises the handling of pseudo‑random number generators used
throughout the project.  Reproducibility is a cornerstone of computational
experiments; when models include stochastic elements, the random seeds used
must be recorded and shared so that results can be replicated on different
machines and numbers of processors【675644021986605†L385-L388】.  Failing to set
a consistent seed can lead to subtle nondeterministic behaviour when code
implicitly calls Python’s ``random`` module or NumPy’s global generator.

The ``set_global_seed`` function below initializes both Python’s built‑in
``random`` module and NumPy’s global random number generator with the same
integer seed.  If additional pseudo‑random number generators (PRNGs) are
introduced (e.g., in Numba kernels), this function can be extended to
configure them as well.

Usage
-----
Call ``set_global_seed(seed)`` once at the start of your program or in
``load_config`` to ensure that all subsequent stochastic operations
produce deterministic results.  Note that individual components of the
project, such as the PSO tuner, may still instantiate their own local
``numpy.random.Generator`` instances for thread safety; those generators
should be seeded explicitly using the same or a derived seed.
"""

from __future__ import annotations

import random
import numpy as np
from typing import Optional

# ==============================================================================
# SeedManager utility
#
# Reproducibility requires explicit management of pseudo‑random number
# generators.  A common practice is to set a single master seed and
# derive independent seeds for sub‑components such as the PSO optimiser
# or simulation workers.  The SeedManager encapsulates this pattern
# using NumPy's Generator and records the assigned seeds.  See
# reproducibility guidelines【858334346726481†L302-L305】 for further
# discussion.


class SeedManager:
    """Manage deterministic seed generation for reproducibility.

    A ``SeedManager`` creates a master :class:`numpy.random.Generator`
    initialised with a given seed.  Each call to :meth:`spawn` returns
    a fresh 32‑bit integer seed that can be used to initialise
    independent RNGs in other modules.  All generated seeds are stored
    in the ``history`` attribute for logging and provenance.

    Parameters
    ----------
    master_seed : int
        Seed used to initialise the internal generator.  If ``None`` the
        generator is seeded nondeterministically.

    Examples
    --------
    >>> mgr = SeedManager(42)
    >>> rng = np.random.default_rng(mgr.spawn())
    """

    def __init__(self, master_seed: Optional[int]) -> None:
        self.master_seed = master_seed
        if master_seed is not None:
            self._gen = np.random.default_rng(master_seed)
        else:
            self._gen = np.random.default_rng()
        self.history = []  # type: list[int]

    def spawn(self) -> int:
        """Return a new integer seed derived from the master generator."""
        seed = int(self._gen.integers(0, 2**32 - 1))
        self.history.append(seed)
        return seed


def set_global_seed(seed: Optional[int]) -> None:
    """Seed Python and NumPy global PRNGs for reproducibility.

    Parameters
    ----------
    seed : int or None
        The integer seed to use.  If ``None``, no seeding is performed.

    Notes
    -----
    A simulation or optimisation routine that relies on random numbers
    should be seeded to ensure that repeated runs yield identical
    trajectories and results.  According to reproducibility guidelines in
    computational science, when random number generation is part of a
    model, the seeds form part of the model description and must be
    recorded and shared to allow replicability【675644021986605†L385-L388】.

    Examples
    --------
    >>> from src.utils.seed import set_global_seed
    >>> set_global_seed(123)
    >>> import random
    >>> import numpy as np
    >>> random.random(), np.random.rand()
    (0.052363598850944326, 0.6964691855978616)

    Calling ``set_global_seed`` again with the same seed resets both
    generators to their initial state:

    >>> set_global_seed(123)
    >>> random.random(), np.random.rand()
    (0.052363598850944326, 0.6964691855978616)
    """
    if seed is None:
        return
    try:
        # Seed Python's global random module
        random.seed(int(seed))
    except Exception:
        # Fall back silently if the seed is not an integer
        pass
    try:
        # Seed NumPy's legacy RandomState.  NumPy's global RNG is
        # implicitly used in many functions (e.g., np.random.normal).
        np.random.seed(int(seed))
    except Exception:
        pass


def create_rng(seed: Optional[int] = None) -> np.random.Generator:
    """Create a local NumPy random number generator.

    Parameters
    ----------
    seed : int or None, optional
        Seed for the generator.  If None, NumPy will choose a random
        seed.  Passing an integer ensures deterministic behaviour of
        subsequent random draws.

    Returns
    -------
    numpy.random.Generator
        A new random number generator instance seeded with ``seed``.

    Notes
    -----
    Creating local PRNGs instead of seeding the global RNG allows
    different components to use independent random streams without
    interfering with each other.  This is particularly important when
    running concurrent simulations or optimisation algorithms【675644021986605†L385-L388】.
    """
    if seed is None:
        return np.random.default_rng()
    try:
        return np.random.default_rng(int(seed))
    except Exception:
        # Fall back to an unseeded generator if the seed is invalid
        return np.random.default_rng()
