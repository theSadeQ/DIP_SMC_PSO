#==========================================================================================\\\
#============================ src/core/safety_guards.py ================================\\\
#==========================================================================================\\\
"""
Safety guards compatibility layer.
This module re-exports the safety guard functions from their new modular location
for backward compatibility with legacy import paths.
"""

# Re-export safety guard functions from new location
from ..simulation.context.safety_guards import _guard_no_nan, _guard_energy, _guard_bounds

__all__ = ['_guard_no_nan', '_guard_energy', '_guard_bounds']