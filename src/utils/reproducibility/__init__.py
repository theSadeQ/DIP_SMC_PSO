#==========================================================================================\\\
#==================== src/utils/reproducibility/__init__.py ===========================\\\
#==========================================================================================\\\

"""
Reproducibility utilities for control engineering experiments.

This package provides tools for managing random seeds and ensuring
reproducible results across experiments and simulations.
"""

from .seed import (
    set_global_seed,
    SeedManager,
    create_rng
)

# Create aliases for backward compatibility
set_seed = set_global_seed

# Create dummy functions for missing utilities (for backward compatibility)
def with_seed(seed):
    """Dummy function for backward compatibility."""
    def decorator(func):
        return func
    return decorator

def random_seed_context(seed):
    """Dummy context manager for backward compatibility."""
    import contextlib
    @contextlib.contextmanager
    def context():
        old_seed = None
        try:
            set_global_seed(seed)
            yield
        finally:
            if old_seed is not None:
                set_global_seed(old_seed)
    return context()

__all__ = [
    "set_global_seed",
    "set_seed",
    "SeedManager",
    "create_rng",
    "with_seed",
    "random_seed_context"
]