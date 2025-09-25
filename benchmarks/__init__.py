#==========================================================================================\\\
#========================== benchmarks/__init__.py ======================================\\\
#==========================================================================================\\\
"""
Modular Integration Benchmarking Framework.

This package provides a comprehensive, modular framework for benchmarking
and analyzing numerical integration methods for dynamic systems. The
architecture emphasizes:

* **Modularity**: Clear separation of concerns across specialized modules
* **Extensibility**: Easy addition of new methods and analysis techniques
* **Performance**: Optimized implementations with comprehensive profiling
* **Scientific Rigor**: Physics-based validation and theoretical grounding
* **Usability**: Clean APIs with backward compatibility

Framework Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                    Integration Benchmarking                     │
├─────────────────────────────────────────────────────────────────┤
│  benchmark/          │  Main orchestration classes             │
│  ├─ IntegrationBenchmark  Enhanced benchmark with legacy API   │
│  └─ ...                                                         │
├─────────────────────────────────────────────────────────────────┤
│  integration/        │  Numerical integration methods          │
│  ├─ EulerIntegrator       Fast Euler implementation            │
│  ├─ RK4Integrator         Fourth-order Runge-Kutta            │
│  └─ AdaptiveRK45Integrator  Adaptive Runge-Kutta-Fehlberg     │
├─────────────────────────────────────────────────────────────────┤
│  analysis/           │  Accuracy and performance analysis      │
│  ├─ EnergyAnalyzer        Energy conservation analysis         │
│  ├─ ConvergenceAnalyzer   Convergence order estimation         │
│  └─ PerformanceProfiler   Computational efficiency analysis    │
├─────────────────────────────────────────────────────────────────┤
│  comparison/         │  Systematic method comparison           │
│  ├─ IntegrationMethodComparator  Multi-scenario comparison     │
│  └─ ComparisonScenario           Test scenario specification    │
├─────────────────────────────────────────────────────────────────┤
│  tests/              │  Comprehensive test suite               │
│  ├─ test_integration_accuracy    Accuracy and conservation     │
│  ├─ test_modular_framework       Framework functionality       │
│  └─ conftest                     Shared fixtures               │
└─────────────────────────────────────────────────────────────────┘

Quick Start:
    # Basic usage (backward compatible)
    from benchmarks import IntegrationBenchmark
    benchmark = IntegrationBenchmark()
    result = benchmark.euler_integrate(sim_time=5.0, dt=0.01)

    # Advanced analysis
    comparison_results = benchmark.comprehensive_comparison()
    performance_profile = benchmark.profile_performance()

    # Direct module access
    from benchmarks.integration import RK4Integrator
    from benchmarks.analysis import EnergyAnalyzer
    from benchmarks.comparison import ComparisonScenario
"""

from __future__ import annotations

# Main interface - backward compatible
from .benchmark import IntegrationBenchmark

# Core modules for advanced usage
from .integration import (
    EulerIntegrator,
    RK4Integrator,
    AdaptiveRK45Integrator,
    IntegrationResult
)

from .analysis import (
    EnergyAnalyzer,
    ConvergenceAnalyzer,
    PerformanceProfiler,
    AccuracyAnalysis
)

from .comparison import (
    IntegrationMethodComparator,
    ComparisonScenario,
    MethodComparisonResult
)

# Version and metadata
__version__ = "2.0.0"
__author__ = "DIP_SMC_PSO Project"
__description__ = "Modular Integration Benchmarking Framework"

# Public API
__all__ = [
    # Main interface
    'IntegrationBenchmark',

    # Integration methods
    'EulerIntegrator',
    'RK4Integrator',
    'AdaptiveRK45Integrator',
    'IntegrationResult',

    # Analysis tools
    'EnergyAnalyzer',
    'ConvergenceAnalyzer',
    'PerformanceProfiler',
    'AccuracyAnalysis',

    # Comparison framework
    'IntegrationMethodComparator',
    'ComparisonScenario',
    'MethodComparisonResult',

    # Metadata
    '__version__',
    '__author__',
    '__description__'
]


def get_framework_info() -> dict:
    """Get comprehensive framework information.

    Returns
    -------
    dict
        Framework metadata including version, available methods, etc.
    """
    return {
        'version': __version__,
        'description': __description__,
        'integration_methods': ['Euler', 'RK4', 'RK45'],
        'analysis_capabilities': [
            'Energy conservation analysis',
            'Convergence order estimation',
            'Performance profiling',
            'Hamiltonian structure validation'
        ],
        'comparison_features': [
            'Multi-scenario testing',
            'Method ranking',
            'Statistical analysis',
            'Custom scenario support'
        ],
        'architecture': 'Modular with clean interfaces',
        'backward_compatibility': True
    }


def run_quick_demo() -> None:
    """Run a quick demonstration of framework capabilities.

    This function provides a fast overview of the framework functionality
    suitable for initial testing or documentation purposes.
    """
    print("Integration Benchmarking Framework Quick Demo")
    print("=" * 50)

    # Initialize benchmark
    benchmark = IntegrationBenchmark()
    print("OK Framework initialized")

    # Run quick comparison
    methods = ['Euler', 'RK4']
    results = {}

    for method in methods:
        if method == 'Euler':
            result = benchmark.euler_integrate(sim_time=1.0, dt=0.01, use_controller=False)
        else:
            result = benchmark.rk4_integrate(sim_time=1.0, dt=0.01, use_controller=False)

        energy_drift = benchmark.calculate_energy_drift(result)
        max_drift = float(max(abs(energy_drift)))

        results[method] = {
            'execution_time': result['time'],
            'max_energy_drift': max_drift
        }

        print(f"OK {method}: {result['time']:.4f}s, drift: {max_drift:.2e}")

    # Show basic comparison
    faster = min(results.items(), key=lambda x: x[1]['execution_time'])
    more_accurate = min(results.items(), key=lambda x: x[1]['max_energy_drift'])

    print(f"\nQuick Analysis:")
    print(f"  Fastest: {faster[0]} ({faster[1]['execution_time']:.4f}s)")
    print(f"  Most accurate: {more_accurate[0]} (drift: {more_accurate[1]['max_energy_drift']:.2e})")
    print(f"\nOK Demo complete! Framework is operational.")


# Convenience function for interactive use
demo = run_quick_demo