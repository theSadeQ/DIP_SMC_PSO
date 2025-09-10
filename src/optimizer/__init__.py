# src/optimizer/__init__.py

# Expose the public API from the consolidated optimizer module
from .pso_optimizer import PSOTuner

__all__ = ["PSOTuner"]