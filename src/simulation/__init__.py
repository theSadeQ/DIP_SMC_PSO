#==========================================================================================\\\
#================================== src/simulation/__init__.py ==============================\\\
#==========================================================================================\\\

"""Professional simulation framework for control engineering applications.

This module provides a comprehensive simulation framework with:
- Multiple execution strategies (sequential, batch, parallel, real-time)
- Advanced numerical integration methods (adaptive and fixed-step)
- Comprehensive safety monitoring and constraint enforcement
- Professional result processing and analysis
- Extensible architecture for research and production use

For backward compatibility, legacy interfaces are maintained.
"""

# =============================================================================
# NEW FRAMEWORK INTERFACES
# =============================================================================

# Core framework components
from .core import (
    SimulationEngine, Integrator, Orchestrator, SimulationStrategy,
    SafetyGuard, ResultContainer, SimulationContext, StateSpaceUtilities, TimeManager
)

# Orchestrators for different execution strategies
from .orchestrators import (
    SequentialOrchestrator, BatchOrchestrator, ParallelOrchestrator, RealTimeOrchestrator
)

# Integration methods
from .integrators import (
    ForwardEuler, RungeKutta4, DormandPrince45, ZeroOrderHold
)

# Safety and monitoring
from .safety import (
    apply_safety_guards, SafetyViolationError, SafetyMonitor, PerformanceMonitor
)

# Result management
from .results import (
    StandardResultContainer, BatchResultContainer, ResultProcessor
)

# Analysis strategies
from .strategies import (
    MonteCarloStrategy,
)

# =============================================================================
# BACKWARD COMPATIBILITY INTERFACES
# =============================================================================

# Legacy imports from old structure (maintaining exact same interface)
from .orchestrators.sequential import get_step_fn, step, run_simulation
from .core.simulation_context import SimulationContext

# Legacy vector simulation interface
from .orchestrators.batch import simulate_batch as simulate

# Legacy adaptive integration
from .integrators.adaptive.runge_kutta import rk45_step

# Legacy safety guards (exact original interface)
from .safety.guards import (
    guard_no_nan as _guard_no_nan,
    guard_energy as _guard_energy,
    guard_bounds as _guard_bounds
)

# =============================================================================
# EXPORTS
# =============================================================================

# New framework exports
__all__ = [
    # Core interfaces
    "SimulationEngine", "Integrator", "Orchestrator", "SimulationStrategy",
    "SafetyGuard", "ResultContainer", "SimulationContext",
    "StateSpaceUtilities", "TimeManager",

    # Orchestrators
    "SequentialOrchestrator", "BatchOrchestrator", "ParallelOrchestrator", "RealTimeOrchestrator",

    # Integrators
    "ForwardEuler", "RungeKutta4", "DormandPrince45", "ZeroOrderHold",

    # Safety
    "apply_safety_guards", "SafetyViolationError", "SafetyMonitor", "PerformanceMonitor",

    # Results
    "StandardResultContainer", "BatchResultContainer", "ResultProcessor",

    # Strategies
    "MonteCarloStrategy",

    # Legacy compatibility (IMPORTANT: maintain exact same names)
    "get_step_fn",           # Original function from simulation_runner
    "step",                  # Original step function
    "run_simulation",        # Original simulation runner
    "simulate",              # Original vector simulation function
    "rk45_step",             # Original adaptive integration function
]

# =============================================================================
# CONVENIENCE FACTORY FUNCTIONS
# =============================================================================

def create_simulation_engine(engine_type: str = "sequential", config_path: str = "config.yaml"):
    """Create a simulation engine of specified type.

    Parameters
    ----------
    engine_type : str, optional
        Type of engine: 'sequential', 'batch', 'parallel', 'real_time'
    config_path : str, optional
        Path to configuration file

    Returns
    -------
    SimulationEngine
        Configured simulation engine
    """
    context = SimulationContext(config_path)
    return context.create_simulation_engine(engine_type)


def run_monte_carlo_analysis(simulation_fn, n_samples: int = 1000, **kwargs):
    """Run Monte Carlo analysis on simulation function.

    Parameters
    ----------
    simulation_fn : callable
        Simulation function to analyze
    n_samples : int, optional
        Number of Monte Carlo samples
    **kwargs
        Additional parameters for analysis

    Returns
    -------
    dict
        Monte Carlo analysis results
    """
    strategy = MonteCarloStrategy(n_samples=n_samples)
    return strategy.analyze(simulation_fn, kwargs)


# Add convenience functions to exports
__all__.extend([
    "create_simulation_engine",
    "run_monte_carlo_analysis"
])