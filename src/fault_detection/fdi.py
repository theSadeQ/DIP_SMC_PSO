#==========================================================================================\\\
#============================ src/fault_detection/fdi.py ===============================\\\
#==========================================================================================\\\

"""
Compatibility import for fault detection and isolation system.

This module provides backward compatibility for old import paths.
The actual implementation is in src.analysis.fault_detection.fdi.

Usage:
    from src.fault_detection.fdi import FDIsystem      # Old style (works)
    from src.analysis.fault_detection.fdi import FDIsystem # New style (preferred)
"""

# Import from the actual location
from ..analysis.fault_detection.fdi import *