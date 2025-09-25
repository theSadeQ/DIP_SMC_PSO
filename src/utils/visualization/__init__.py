#==========================================================================================\\\
#==================== src/utils/visualization/__init__.py =============================\\\
#==========================================================================================\\\

"""
Comprehensive visualization package for control engineering.

This package provides complete visualization capabilities including:
- Real-time and recorded animations
- Static analysis plots
- Controller comparison visualizations
- Complete project documentation movies
- Professional presentation materials
"""

from .animation import DIPAnimator, MultiSystemAnimator
from .static_plots import ControlPlotter, SystemVisualization
from .movie_generator import ProjectMovieGenerator, MovieScene
from .legacy_visualizer import Visualizer  # Legacy compatibility

__all__ = [
    "DIPAnimator",
    "MultiSystemAnimator",
    "ControlPlotter",
    "SystemVisualization",
    "ProjectMovieGenerator",
    "MovieScene",
    "Visualizer"  # Legacy visualizer
]