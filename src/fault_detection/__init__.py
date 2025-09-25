#==========================================================================================\\\
#======================== src/fault_detection/__init__.py ===============================\\\
#==========================================================================================\\\

"""
Compatibility import for fault detection system.

This module provides backward compatibility for old import paths.
The actual implementation is in src.analysis.fault_detection.

Usage:
    from src.fault_detection.fdi import FDIsystem      # Old style (works)
    from src.analysis.fault_detection import FDIsystem # New style (preferred)
"""

# Re-export everything from the actual location
from ..analysis.fault_detection import *