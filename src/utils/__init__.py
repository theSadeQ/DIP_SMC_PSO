#==========================================================================================\\\
#=================================== src/utils/__init__.py ===========================\\\
#==========================================================================================\\\

"""
Comprehensive utilities package for control engineering.

This package provides a complete suite of utilities organized into focused modules:

Packages:
---------
validation : Parameter validation and range checking
control : Control primitives and saturation functions
monitoring : Real-time performance and latency monitoring
visualization : Animation, plotting, and movie generation
analysis : Statistical analysis and hypothesis testing

Legacy imports are maintained for backward compatibility.
"""

# New modular architecture (recommended)
from .validation import require_positive, require_finite, require_in_range, require_probability
from .control import saturate, smooth_sign, dead_zone
from .monitoring import LatencyMonitor
try:
    from .visualization import (
        DIPAnimator,
        MultiSystemAnimator,
        ControlPlotter,
        SystemVisualization,
        ProjectMovieGenerator,
        MovieScene,
        Visualizer as _Visualizer,
    )
except ImportError:
    DIPAnimator = MultiSystemAnimator = ControlPlotter = SystemVisualization = ProjectMovieGenerator = MovieScene = None  # type: ignore
    _Visualizer = None
from .analysis import (
    confidence_interval, bootstrap_confidence_interval,
    welch_t_test, one_way_anova, monte_carlo_analysis,
    performance_comparison_summary, sample_size_calculation
)

# Import from properly organized modular packages
try:
    from .types import (
        ClassicalSMCOutput, AdaptiveSMCOutput, STAOutput, HybridSTAOutput
    )
    from .reproducibility import (
        set_seed, set_global_seed, SeedManager, with_seed, random_seed_context
    )
except ImportError:
    # Handle case where some modules are not available
    pass

Visualizer = _Visualizer

__all__ = [
    # New modular architecture
    "require_positive",
    "require_finite",
    "require_in_range",
    "require_probability",
    "saturate",
    "smooth_sign",
    "dead_zone",
    "LatencyMonitor",
    "DIPAnimator",
    "MultiSystemAnimator",
    "ControlPlotter",
    "SystemVisualization",
    "ProjectMovieGenerator",
    "MovieScene",
    "confidence_interval",
    "bootstrap_confidence_interval",
    "welch_t_test",
    "one_way_anova",
    "monte_carlo_analysis",
    "performance_comparison_summary",
    "sample_size_calculation",

    # Legacy compatibility (if available)
    "ClassicalSMCOutput",
    "AdaptiveSMCOutput",
    "STAOutput",
    "HybridSTAOutput",
    "set_seed",
    "set_global_seed",
    "SeedManager",
    "with_seed",
    "random_seed_context",
    "Visualizer"  # Legacy Visualizer class
]