#==========================================================================================\\\
#========================= src/utils/control_analysis.py =========================\\\
#==========================================================================================\\\
"""
Control analysis utilities compatibility module.

This module provides backward compatibility for test modules that expect
control analysis utilities at src.utils.control_analysis. All functionality
is re-exported from the actual implementation location.
"""

# Import all control analysis functionality
from ..analysis.performance.control_analysis import *

# Explicitly import key classes for clarity
from ..analysis.performance.control_analysis import ControlAnalyzer

__all__ = [
    'ControlAnalyzer',
]