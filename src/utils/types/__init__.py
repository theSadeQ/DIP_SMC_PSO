#==========================================================================================\\\
#========================== src/utils/types/__init__.py ================================\\\
#==========================================================================================\\\

"""
Type definitions and structured return types for control engineering.

This package provides type-safe structured return types for controllers
and other components, ensuring clear interfaces and reducing errors.
"""

from .control_outputs import (
    ClassicalSMCOutput,
    AdaptiveSMCOutput,
    STAOutput,
    HybridSTAOutput
)

__all__ = [
    "ClassicalSMCOutput",
    "AdaptiveSMCOutput",
    "STAOutput",
    "HybridSTAOutput"
]