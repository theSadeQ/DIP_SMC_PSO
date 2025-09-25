#==========================================================================================\\\
#======================== src/utils/control/__init__.py ================================\\\
#==========================================================================================\\\

"""
Control engineering utilities.

This package provides fundamental control system utilities including
saturation functions, output structures, and control primitives.
"""

from .saturation import saturate, smooth_sign, dead_zone

__all__ = [
    "saturate",
    "smooth_sign",
    "dead_zone"
]