#==========================================================================================\\\
#==================== benchmarks/integration/__init__.py ================================\\\
#==========================================================================================\\\
"""
Numerical integration methods package for dynamic system simulation.

This package provides high-performance implementations of various integration
schemes optimized for control system applications.
"""

from __future__ import annotations

from .numerical_methods import (
    IntegrationResult,
    EulerIntegrator,
    RK4Integrator,
    AdaptiveRK45Integrator
)

__all__ = [
    'IntegrationResult',
    'EulerIntegrator',
    'RK4Integrator',
    'AdaptiveRK45Integrator'
]