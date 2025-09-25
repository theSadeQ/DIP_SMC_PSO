# CLAUDE.md - Project Reference Guide

This document provides Claude with essential information about the DIP_SMC_PSO project structure, commands, and workflows.

## Project Overview

**Double-Inverted Pendulum Sliding Mode Control with PSO Optimization**

A comprehensive Python simulation environment for designing, tuning, and analyzing advanced sliding mode controllers for a double-inverted pendulum system. Features automated gain tuning via Particle Swarm Optimization and both CLI and web interfaces.

## Key Technologies
- **Python 3.9+** with NumPy, SciPy, Matplotlib
- **Control Systems**: Classical SMC, Super-Twisting SMC, Adaptive SMC, Hybrid Adaptive STA-SMC
- **Optimization**: PSO via PySwarms, Optuna
- **Performance**: Numba acceleration for batch simulations
- **Testing**: pytest with comprehensive test suite
- **Configuration**: YAML-based with Pydantic validation
- **UI**: Streamlit web interface

## Project Structure

```
├── src/                          # Main source code
│   ├── controllers/              # Controller implementations
│   │   ├── factory/             # Controller factory package
│   │   │   ├── __init__.py          # Factory public API
│   │   │   ├── smc_factory.py       # Clean SMC factory (PSO-optimized)
│   │   │   └── legacy_factory.py    # Legacy controller factory
│   │   ├── smc/                 # Core SMC controllers (4 types)
│   │   │   ├── classic_smc.py       # Classical sliding mode controller
│   │   │   ├── sta_smc.py           # Super-twisting sliding mode
│   │   │   ├── adaptive_smc.py      # Adaptive sliding mode
│   │   │   └── hybrid_adaptive_sta_smc.py  # Hybrid adaptive controller
│   │   ├── specialized/         # Specialized controllers
│   │   │   └── swing_up_smc.py      # Swing-up controller
│   │   ├── mpc/                 # Model predictive control
│   │   │   └── mpc_controller.py    # Model predictive controller
│   │   └── __init__.py          # Clean public API
│   ├── core/                    # Core simulation engine
│   │   ├── dynamics.py          # Simplified dynamics model
│   │   ├── dynamics_full.py     # Full nonlinear dynamics
│   │   ├── simulation_runner.py # Main simulation runner
│   │   ├── simulation_context.py # Unified simulation context
│   │   └── vector_sim.py        # Numba-accelerated batch simulator
│   ├── benchmarks/              # Modular benchmarking framework
│   │   ├── metrics/             # Performance metrics computation
│   │   │   ├── control_metrics.py     # ISE, ITAE, RMS calculations
│   │   │   ├── stability_metrics.py   # Overshoot, damping analysis
│   │   │   ├── constraint_metrics.py  # Violation counting & severity
│   │   │   └── __init__.py            # Unified metrics interface
│   │   ├── core/                # Trial execution engine
│   │   │   ├── trial_runner.py        # Multi-trial orchestration
│   │   │   └── __init__.py
│   │   ├── statistics/          # Statistical analysis
│   │   │   ├── confidence_intervals.py # CI computation & hypothesis testing
│   │   │   └── __init__.py
│   │   ├── config/              # Benchmarking configuration
│   │   └── statistical_benchmarks_v2.py # Refactored main interface
│   ├── optimizer/               # PSO optimization
│   │   └── pso_optimizer.py     # PSO tuner implementation
│   ├── hil/                     # Hardware-in-the-loop
│   │   ├── plant_server.py      # HIL plant server
│   │   └── controller_client.py # HIL controller client
│   └── config.py                # Configuration management
├── benchmarks/                  # Integration benchmarking framework
│   ├── integration/             # Numerical integration methods
│   │   ├── numerical_methods.py      # Euler, RK4, RK45 implementations
│   │   └── __init__.py
│   ├── analysis/                # Accuracy & performance analysis
│   │   ├── accuracy_metrics.py       # Energy conservation & convergence
│   │   └── __init__.py
│   ├── comparison/              # Method comparison framework
│   │   ├── method_comparison.py      # Systematic comparison engine
│   │   └── __init__.py
│   ├── benchmark/               # Benchmark orchestration
│   │   ├── integration_benchmark.py  # Main benchmark class
│   │   └── __init__.py
│   ├── examples/                # Usage demonstrations
│   │   ├── basic_comparison.py            # Fundamental usage examples
│   │   ├── advanced_analysis.py           # Research-grade analysis
│   │   └── __init__.py
│   └── __init__.py              # Clean main interface
├── tests/                       # Comprehensive test suite
│   ├── test_controllers/        # Controller unit tests
│   ├── test_core/               # Core simulation tests
│   ├── test_optimizer/          # PSO optimization tests
│   ├── test_benchmarks/         # Integration benchmarking tests
│   │   ├── test_integration_accuracy.py      # Accuracy and conservation tests
│   │   ├── test_modular_framework.py         # Framework functionality tests
│   │   └── conftest.py                       # Benchmarking test fixtures
│   └── conftest.py              # Test fixtures and configuration
├── simulate.py                  # Main CLI application
├── streamlit_app.py            # Web interface
├── run_tests.py                # Test runner script
├── config.yaml                 # Main configuration file
└── requirements.txt            # Python dependencies
```

## Modular Benchmarking Architecture

### Statistical Benchmarking Framework (`src/benchmarks/`)

The statistical benchmarking system uses a modular architecture for enhanced maintainability and extensibility:

#### **Metrics Module** (`src/benchmarks/metrics/`)
Specialized performance metric calculations:
```python
# Use individual metric modules
from src.benchmarks.metrics.control_metrics import compute_ise, compute_itae
from src.benchmarks.metrics.stability_metrics import compute_overshoot
from src.benchmarks.metrics.constraint_metrics import count_control_violations

# Or use unified interface
from src.benchmarks.metrics import compute_all_metrics
metrics = compute_all_metrics(t, x, u, max_force, include_advanced=True)
```

#### **Core Module** (`src/benchmarks/core/`)
Trial execution and orchestration:
```python
from src.benchmarks.core import run_multiple_trials, validate_trial_configuration

# Execute trials with enhanced error handling and progress tracking
metrics_list = run_multiple_trials(
    controller_factory, cfg, n_trials=30,
    progress_callback=lambda current, total: print(f"Trial {current}/{total}")
)
```

#### **Statistics Module** (`src/benchmarks/statistics/`)
Advanced statistical analysis:
```python
from src.benchmarks.statistics import (
    compute_t_confidence_intervals,
    compute_bootstrap_confidence_intervals,
    compare_metric_distributions
)

# Non-parametric confidence intervals
ci_results = compute_bootstrap_confidence_intervals(metrics_list, confidence_level=0.99)

# Statistical hypothesis testing
comparison = compare_metric_distributions(metrics_a, metrics_b)
```

#### **Main Interface** (`src/benchmarks/statistical_benchmarks_v2.py`)
Backward-compatible interface with enhanced capabilities:
```python
from src.benchmarks.statistical_benchmarks_v2 import (
    run_trials,  # Original API preserved
    run_trials_with_advanced_statistics,  # Enhanced analysis
    compare_controllers  # Controller comparison
)

# Original usage still works
metrics_list, ci_results = run_trials(controller_factory, cfg)

# Enhanced statistical analysis
metrics_list, analysis = run_trials_with_advanced_statistics(
    controller_factory, cfg,
    confidence_level=0.99,
    use_bootstrap=True
)
```

### Integration Benchmarking Framework (`benchmarks/`)

Modular numerical integration comparison system:

#### **Benchmark Module** (`benchmarks/benchmark/`)
Main benchmark orchestration with backward compatibility:
```python
from benchmarks import IntegrationBenchmark

# Initialize benchmark (original API preserved)
benchmark = IntegrationBenchmark()

# Legacy methods work unchanged
euler_result = benchmark.euler_integrate(sim_time=5.0, dt=0.01)
rk4_result = benchmark.rk4_integrate(sim_time=5.0, dt=0.01)
rk45_result = benchmark.rk45_integrate(sim_time=5.0, rtol=1e-8)

# Enhanced capabilities
comparison_results = benchmark.comprehensive_comparison()
performance_profile = benchmark.profile_performance()
conservation_analysis = benchmark.validate_conservation_laws()
```

#### **Integration Module** (`benchmarks/integration/`)
High-performance integration methods:
```python
from benchmarks.integration import EulerIntegrator, RK4Integrator, AdaptiveRK45Integrator

# Direct use of integration methods
integrator = RK4Integrator(dynamics)
result = integrator.integrate(x0, sim_time, dt, controller)
```

#### **Analysis Module** (`benchmarks/analysis/`)
Comprehensive accuracy and performance analysis:
```python
from benchmarks.analysis import EnergyAnalyzer, ConvergenceAnalyzer, PerformanceProfiler

# Energy conservation analysis
energy_analyzer = EnergyAnalyzer(physics_params)
accuracy_analysis = energy_analyzer.analyze_energy_conservation(result)

# Convergence order estimation
convergence_analysis = convergence_analyzer.estimate_convergence_order(
    integration_method, x0, sim_time, dt_values
)
```

#### **Comparison Module** (`benchmarks/comparison/`)
Systematic method comparison framework:
```python
from benchmarks.comparison import IntegrationMethodComparator, ComparisonScenario

# Comprehensive comparison across scenarios
comparator = IntegrationMethodComparator(physics_params)
results = comparator.run_comprehensive_comparison()

# Custom scenario testing
scenario = ComparisonScenario(
    name="high_energy", x0=initial_state, sim_time=5.0,
    dt_values=[0.01, 0.005, 0.001]
)
comparison_result = comparator.run_single_comparison(scenario)
```

#### **Tests Module** (`tests/test_benchmarks/`)
Comprehensive test suite for framework validation integrated with project tests:
```python
# Run integration accuracy tests
pytest tests/test_benchmarks/test_integration_accuracy.py -v

# Run modular framework tests
pytest tests/test_benchmarks/test_modular_framework.py -v

# Run all benchmark tests
pytest tests/test_benchmarks/ -v

# Run all project tests including benchmarks
pytest tests/ -v
```

#### **Examples Module** (`benchmarks/examples/`)
Ready-to-run usage demonstrations:
```python
# Run basic demonstration
python benchmarks/examples/basic_comparison.py

# Run advanced analysis demonstration
python benchmarks/examples/advanced_analysis.py
```

### Benefits of Modular Architecture

1. **Single Responsibility**: Each module has one clear purpose
2. **Parallel Development**: Multiple developers can work on different metrics
3. **Easy Testing**: Unit test individual components in isolation
4. **Flexible Deployment**: Use only needed components
5. **Scientific Rigor**: Domain-specific validation built into each module
6. **Performance Optimization**: Targeted optimization of computational bottlenecks

## Essential Commands

### Running Simulations
```bash
# Basic simulation with classical controller
python simulate.py --ctrl classical_smc --plot

# Use super-twisting controller with full dynamics
python simulate.py --ctrl sta_smc --plot

# Load pre-tuned gains and run simulation
python simulate.py --load tuned_gains.json --plot

# Print current configuration
python simulate.py --print-config
```

### PSO Optimization
```bash
# Optimize classical SMC gains
python simulate.py --ctrl classical_smc --run-pso --save gains_classical.json

# Optimize adaptive SMC with specific seed
python simulate.py --ctrl adaptive_smc --run-pso --seed 42 --save gains_adaptive.json

# Optimize hybrid adaptive controller
python simulate.py --ctrl hybrid_adaptive_sta_smc --run-pso --save gains_hybrid.json
```

### Hardware-in-the-Loop (HIL)
```bash
# Run HIL simulation (spawns server and client)
python simulate.py --run-hil --plot

# HIL with custom configuration
python simulate.py --config custom_config.yaml --run-hil
```

### Testing
```bash
# Run full test suite
python run_tests.py

# Run specific test module
python -m pytest tests/test_controllers/test_classical_smc.py -v

# Run modular benchmark tests
python -m pytest tests/test_benchmarks/test_statistical_benchmarks.py -v

# Run performance benchmarks only
python -m pytest tests/test_benchmarks/ --benchmark-only

# Test integration benchmarking framework
python -m pytest tests/test_benchmarks/ -v

# Test specific accuracy features
python -m pytest tests/test_benchmarks/test_integration_accuracy.py -v

# Test modular framework capabilities
python -m pytest tests/test_benchmarks/test_modular_framework.py -v

# Run tests with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Web Interface
```bash
# Launch Streamlit dashboard
streamlit run streamlit_app.py
```

### Integration Benchmarking Examples
```bash
# Run basic integration method comparison
python benchmarks/examples/basic_comparison.py

# Run advanced research-grade analysis
python benchmarks/examples/advanced_analysis.py

# Quick framework demonstration
python -c "from benchmarks import demo; demo()"
```

## Controller Types

1. **classical_smc**: Classical sliding mode with boundary layer for chattering reduction
2. **sta_smc**: Super-twisting sliding mode for continuous control and finite-time convergence
3. **adaptive_smc**: Adaptive controller that adjusts gains online for uncertainty handling
4. **hybrid_adaptive_sta_smc**: Hybrid adaptive super-twisting with model-based equivalent control
5. **swing_up_smc**: Energy-based swing-up controller for large angle stabilization
6. **mpc_controller**: Model predictive controller (experimental)

## Configuration System

The project uses `config.yaml` for centralized configuration with Pydantic validation:

- **Physics parameters**: Masses, lengths, inertias, friction coefficients
- **Controller settings**: Gains, saturation limits, adaptation rates
- **PSO parameters**: Swarm size, bounds, iterations, cognitive/social coefficients
- **Simulation settings**: Duration, timestep, initial conditions
- **HIL configuration**: Network settings, sensor noise, latency simulation

## Key Development Patterns

### Adding New Controllers
1. Implement controller class in `src/controllers/`
2. Add factory method in `src/controllers/factory.py`
3. Add configuration section to `config.yaml`
4. Create unit tests in `tests/test_controllers/`

### Running Batch Simulations
Use `src/core/vector_sim.py` for Numba-accelerated parallel simulations:
```python
from src.core.vector_sim import run_batch_simulation
results = run_batch_simulation(controller, dynamics, initial_conditions, sim_params)
```

### Configuration Loading
```python
from src.config import load_config
config = load_config("config.yaml", allow_unknown=False)
```

## Testing Architecture

- **Unit tests**: Individual component testing
- **Integration tests**: End-to-end simulation workflows
- **Property-based tests**: Hypothesis-driven randomized testing
- **Performance benchmarks**: pytest-benchmark for regression detection
- **Scientific validation**: Lyapunov stability, chattering analysis

### Test Execution Patterns
```bash
# Fast unit tests only
pytest tests/test_controllers/ -k "not integration"

# Integration tests with full dynamics
pytest tests/ -k "full_dynamics"

# Performance regression testing
pytest --benchmark-only --benchmark-compare --benchmark-compare-fail=mean:5%
```

## Common Debugging

### Import Issues
- Ensure working directory is project root
- Check `PYTHONPATH` includes `src/`
- Verify all dependencies in `requirements.txt` are installed

### Simulation Failures
- Check configuration validation errors in logs
- Verify physics parameters are positive
- Ensure simulation duration ≥ timestep
- Monitor for numerical instabilities (`NumericalInstabilityError`)

### PSO Not Converging
- Increase `pso.iters` or `pso.n_particles`
- Adjust parameter bounds in `pso.bounds`
- Check cost function weights in `cost_function.weights`
- Verify controller constraints (saturation limits, adaptation rates)

## Performance Optimization

- Use `simulation.use_full_dynamics: false` for faster iterations
- Reduce `simulation.duration` for development
- Leverage `src/core/vector_sim.py` for batch processing
- Monitor benchmark results to catch performance regressions

## Development Workflow

1. **Configuration First**: Define controller parameters in `config.yaml`
2. **Test-Driven**: Write tests before implementation
3. **Validate Early**: Use configuration validation and type hints
4. **Benchmark**: Measure performance impact of changes
5. **Scientific Rigor**: Verify control-theoretic properties

This project emphasizes scientific reproducibility, performance, and robust engineering practices for control systems research and development.

## Modular Code Organization Principles

### Domain-Driven Architecture

The project follows domain-driven design principles with clear separation of concerns:

#### **1. Functional Decomposition**
- **Single Responsibility**: Each module handles one specific domain concept
- **Clear Interfaces**: Well-defined APIs between modules
- **Dependency Inversion**: High-level modules don't depend on low-level implementation details

#### **2. Scientific Code Structure**
```python
# Example: Metrics module organization
metrics/
├── control_metrics.py      # Control engineering specific metrics (ISE, ITAE, RMS)
├── stability_metrics.py    # Stability analysis metrics (overshoot, damping)
├── constraint_metrics.py   # Physical constraint validation
└── __init__.py            # Unified interface with compute_all_metrics()
```

#### **3. Physics-Aware Separation**
- **Physics Models**: Separate from numerical methods
- **Control Theory**: Independent from implementation details
- **Analysis Tools**: Domain-specific but method-agnostic

### Module Design Patterns

#### **Factory Pattern for Extensibility**
```python
# Easy addition of new integration methods
def create_integrator(method_name: str, dynamics: DynamicsModel):
    integrators = {
        'euler': EulerIntegrator,
        'rk4': RK4Integrator,
        'rk45': AdaptiveRK45Integrator
    }
    return integrators[method_name](dynamics)
```

#### **Strategy Pattern for Algorithms**
```python
# Interchangeable analysis strategies
class PerformanceAnalyzer:
    def __init__(self, strategy: AnalysisStrategy):
        self.strategy = strategy

    def analyze(self, data):
        return self.strategy.compute_metrics(data)
```

#### **Template Method for Scientific Validation**
```python
# Consistent validation across all metric computations
class MetricValidator:
    def validate_and_compute(self, data):
        self.validate_inputs(data)
        result = self.compute_metric(data)
        self.validate_outputs(result)
        return result
```

### Scientific Code Documentation

#### **Mathematical Foundations in Docstrings**
```python
def compute_ise(t: np.ndarray, x: np.ndarray) -> float:
    """Compute Integral of Squared Error (ISE) for state tracking.

    Mathematical Definition:
    ISE = ∫₀ᵀ ||x(t)||² dt

    Physical Interpretation:
    Measures cumulative deviation from desired trajectory.
    Lower values indicate better tracking performance.

    Control Engineering Context:
    - Quadratic cost function component in optimal control
    - Related to H₂ norm of closed-loop system
    - Emphasizes large deviations more than small ones

    Parameters
    ----------
    t : np.ndarray
        Time vector, shape (N+1,)
    x : np.ndarray
        State trajectories, shape (B, N+1, S) for B batches, S states

    Returns
    -------
    float
        ISE value averaged across batch dimension

    References
    ----------
    [1] Franklin, G.F. "Feedback Control of Dynamic Systems", Ch. 7
    [2] Åström, K.J. "Control System Design", Section 4.3
    """
```

#### **Theory-Implementation Bridge**
- **Executable Documentation**: Code examples in docstrings that actually run
- **Mathematical Validation**: Assert theoretical properties in implementation
- **Reference Linking**: Connect code to scientific literature

### Code Splitting Guidelines

#### **When to Split a Module**

**Split if module exhibits any of:**
1. **Multiple Responsibilities**: Handles >1 distinct domain concept
2. **Size Threshold**: >500 lines or >10 classes/functions
3. **Import Complexity**: Imports from >5 different domains
4. **Test Complexity**: Requires >20 test cases for adequate coverage
5. **Collaboration Conflicts**: Multiple developers editing simultaneously

#### **How to Split Effectively**

**1. Domain Boundaries**
```python
# Before: Mixed responsibilities
performance_analysis.py  # 800 lines, handles metrics + statistics + visualization

# After: Clear domain separation
metrics/
├── control_metrics.py     # ISE, ITAE, RMS computations
├── stability_metrics.py   # Overshoot, damping analysis
└── constraint_metrics.py  # Violation detection
statistics/
├── confidence_intervals.py  # Statistical analysis
└── hypothesis_testing.py    # Comparative analysis
visualization/
├── time_series_plots.py     # State/control trajectories
└── performance_charts.py    # Metric comparison plots
```

**2. Dependency Management**
```python
# Use __init__.py for clean interfaces
from .control_metrics import compute_ise, compute_itae
from .stability_metrics import compute_overshoot
from .constraint_metrics import count_violations

__all__ = ['compute_all_metrics', 'compute_basic_metrics']

def compute_all_metrics(...):
    """Unified interface hiding internal module structure."""
    pass
```

**3. Backward Compatibility**
```python
# Maintain APIs during refactoring
# old_module.py -> new_modular_structure/
def old_function(*args, **kwargs):
    """Legacy function preserved for backward compatibility."""
    from .new_structure import enhanced_function
    return enhanced_function(*args, **kwargs)
```

#### **Module Interaction Patterns**

**1. Layered Architecture**
```
Application Layer    # CLI, Web interfaces
Domain Layer        # Controllers, metrics, analysis
Infrastructure      # Dynamics, simulation, I/O
```

**2. Clean Dependency Flow**
- **Inward Dependencies**: Lower layers don't know about higher layers
- **Interface Segregation**: Modules depend only on interfaces they use
- **Dependency Injection**: Configuration-driven component assembly

### Code Quality Enforcement

#### **1. Type Safety**
```python
# Strict typing for scientific computing
from typing import Protocol, runtime_checkable

@runtime_checkable
class IntegrationMethod(Protocol):
    def integrate(self, x0: np.ndarray, t_span: tuple,
                 controller: Optional[Controller]) -> IntegrationResult:
        ...
```

#### **2. Scientific Validation**
```python
# Built-in theoretical property checking
def validate_energy_conservation(result: IntegrationResult,
                               tolerance: float = 1e-3) -> bool:
    """Verify energy conservation for Hamiltonian systems."""
    energy_drift = compute_energy_drift(result)
    max_relative_drift = np.max(np.abs(energy_drift)) / initial_energy
    return max_relative_drift < tolerance
```

#### **3. Performance Monitoring**
```python
# Automatic performance regression detection
@benchmark_critical
def compute_control_metrics(t, x, u):
    """Critical path function - monitor for performance regressions."""
    pass
```

## Code Style Guidelines

### ASCII Header Style
All Python files should include a distinctive ASCII art header for visual identification and professionalism:

```python
#==========================================================================================\\\
#========================================= filename.py ===================================\\\
#==========================================================================================\\\
```

**Header Rules:**
- Use exactly 90 characters wide (`=` characters)
- Center the file path (relative to project root) with padding `=` characters
- Include `.py` extension in the filename
- For root-level files, use just the filename (e.g., `simulate.py`)
- For files in subdirectories, use the full path (e.g., `src/controllers/factory.py`)
- End each line with `\\\`
- Place at the very top of each Python file
- Use 3 lines total (top border, file path, bottom border)

**Example Implementation:**
```python
#==========================================================================================\\\
#======================================== simulate.py ===================================\\\
#==========================================================================================\\\

"""Main CLI application for double-inverted pendulum simulation."""

import argparse
# ... rest of file
```

This creates a banner-style header that makes files visually distinctive and easier to identify in editors and version control diffs.

### **IMPORTANT: Cleanup After Changes**

**Always clean up after making changes:**
1. **Remove temporary files**: Delete any test files, examples, or temporary artifacts created during development
2. **Remove redundant files**: Delete old files when restructuring (e.g., when splitting monolithic classes)
3. **Update imports**: Ensure all import paths are correct after moving files
4. **Test thoroughly**: Verify functionality still works after changes
5. **Update documentation**: Keep CLAUDE.md current with actual project structure
6. **Commit clean state**: Only commit the final, clean version without temporary artifacts

**Example cleanup checklist:**
- ✅ Remove `*_example.py`, `test_*.py`, `*_proposal.md` files
- ✅ Delete old monolithic files after successful modularization
- ✅ Update all `__init__.py` files with correct imports
- ✅ Verify factory and public APIs still work
- ✅ Update CLAUDE.md with new structure
- ✅ Test import paths from different contexts

## Clean SMC Factory System (September 2024)

### Overview

A **focused, type-safe factory system** for the 4 core SMC controllers, optimized specifically for PSO parameter tuning and research workflows. Replaces the complex legacy factory with a clean, single-responsibility implementation.

### Architecture

```
src/controllers/
├── factory/               # Controller factory package
│   ├── __init__.py           # Clean factory public API
│   ├── smc_factory.py        # Clean SMC factory (400 lines vs 1,179 legacy)
│   └── legacy_factory.py     # Legacy factory (backward compatibility)
├── __init__.py            # Clean public API with PSO conveniences
├── smc/                   # 4 core SMC controllers (unchanged)
│   ├── classic_smc.py
│   ├── adaptive_smc.py
│   ├── sta_smc.py
│   └── hybrid_adaptive_sta_smc.py
├── specialized/           # Optional specialized controllers
│   └── swing_up_smc.py
└── mpc/                   # Optional MPC controllers
    └── mpc_controller.py
```

### Design Principles

1. **Single Responsibility**: Only SMC controllers (no MPC, swing-up mixing)
2. **Type Safety**: Enums, protocols, dataclasses for all interfaces
3. **PSO Optimization**: Built-in functions for parameter tuning workflows
4. **Research Focus**: Gain bounds, validation, comparison utilities
5. **Clean Separation**: Core SMC vs specialized controllers
6. **Organized Structure**: Factory package with clean public API

### Core Components

#### **SMC Types Enum**
```python
from controllers import SMCType

SMCType.CLASSICAL           # Classical SMC
SMCType.ADAPTIVE           # Adaptive SMC
SMCType.SUPER_TWISTING     # Super-Twisting (STA) SMC
SMCType.HYBRID             # Hybrid Adaptive-STA SMC
```

#### **Configuration System**
```python
from controllers import SMCConfig

config = SMCConfig(
    gains=[10.0, 8.0, 15.0, 12.0, 50.0, 5.0],
    max_force=100.0,
    dt=0.01,
    boundary_layer=0.01
    # ... controller-specific parameters with smart defaults
)
```

#### **Clean Factory Interface**
```python
from controllers import SMCFactory

# Type-safe controller creation
controller = SMCFactory.create_controller(SMCType.CLASSICAL, config)

# Get controller specifications
spec = SMCFactory.get_gain_specification(SMCType.CLASSICAL)
print(f"Requires {spec.n_gains} gains: {spec.gain_names}")
```

### PSO Integration (Primary Use Case)

#### **One-Liner Controller Creation**
```python
from controllers import create_smc_for_pso

# PSO fitness function integration
def fitness_function(gains_array):
    controller = create_smc_for_pso(SMCType.CLASSICAL, gains_array)
    performance = evaluate_controller(controller, test_scenarios)
    return performance
```

#### **Automatic Gain Bounds**
```python
from controllers import get_gain_bounds_for_pso

# Get PSO optimization bounds for any controller type
bounds = get_gain_bounds_for_pso(SMCType.CLASSICAL)
# Returns: [(0.1, 50.0), (0.1, 50.0), (0.1, 50.0), (0.1, 50.0), (1.0, 200.0), (0.0, 50.0)]
```

#### **Gain Validation**
```python
from controllers import validate_smc_gains

# Pre-validate gains before expensive simulation
is_valid = validate_smc_gains(SMCType.CLASSICAL, candidate_gains)
if not is_valid:
    return float('inf')  # Invalid gains get worst fitness
```

### Research Convenience Functions

#### **Batch Controller Creation**
```python
from controllers import create_all_smc_controllers

gains_dict = {
    "classical": [10, 8, 15, 12, 50, 5],
    "adaptive": [10, 8, 15, 12, 0.5],
    "sta": [25, 10, 15, 12, 20, 15],
    "hybrid": [15, 12, 18, 15]
}

# Create all 4 controllers for comparison study
controllers = create_all_smc_controllers(gains_dict, max_force=100.0)
```

#### **Complete Gain Bounds**
```python
from controllers import get_all_gain_bounds

# Get bounds for all SMC types (useful for multi-objective PSO)
all_bounds = get_all_gain_bounds()
```

### Migration from Legacy Factory

#### **Before (Legacy Factory)**
```python
# Complex, mixed-concern factory
from controllers.factory import create_controller

controller = create_controller(
    "classical_smc",
    gains=[10, 8, 15, 12, 50, 5],
    max_force=100.0,
    boundary_layer=0.01,
    dynamics_model=dynamics,
    config=full_config  # Required complex config object
)
```

#### **After (Clean SMC Factory)**
```python
# Simple, focused factory
from controllers import create_smc_for_pso, SMCType

controller = create_smc_for_pso(
    SMCType.CLASSICAL,
    gains=[10, 8, 15, 12, 50, 5],
    max_force=100.0
)
```

### Backward Compatibility

The legacy factory remains available as `create_controller_legacy` for existing code:

```python
from controllers import create_controller_legacy

# Existing code continues to work
controller = create_controller_legacy("classical_smc", gains=[...])
```

### Benefits Summary

1. **90% Code Reduction**: 400 lines vs 1,179 in legacy factory
2. **Type Safety**: Compile-time error detection with mypy
3. **PSO Optimized**: Built-in functions eliminate boilerplate
4. **Research Ready**: Gain bounds and validation included
5. **Clear Separation**: SMC focus, no mixed concerns
6. **Performance**: Faster imports, reduced complexity
7. **Maintainable**: Single responsibility, easier testing

### Usage Examples

See `examples/clean_smc_usage.py` for comprehensive usage demonstrations including:
- PSO integration patterns
- Comparison study workflows
- Type-safe configuration
- Performance optimization tips

### Testing

```bash
# Test the clean SMC factory
python examples/clean_smc_usage.py

# Run example PSO workflow
python -c "from examples.clean_smc_usage import demonstrate_pso_workflow; demonstrate_pso_workflow()"
```

This clean factory system is specifically designed for serious SMC research with PSO optimization, eliminating the complexity and mixed concerns of the legacy system while providing a more powerful and focused interface.

## Modular SMC Controller Architecture (Future Enhancement)

### Current State vs. Proposed Modular Design

Your current SMC controllers are well-implemented but monolithic (400-650 lines each). A modular architecture would provide significant benefits for maintainability, testing, and scientific clarity.

#### **Current Structure Issues:**
- **Large files**: 400-650 lines per controller
- **Mixed responsibilities**: Validation + computation + output + logging in single classes
- **Code duplication**: Similar sliding surface logic across controllers
- **Testing difficulty**: Monolithic classes with multiple responsibilities
- **Maintenance overhead**: Changes require touching large files

#### **Proposed Modular Structure:**
```
src/controllers/smc/
├── core/                          # Shared SMC components (reusable)
│   ├── sliding_surface.py            # Unified sliding surface calculations
│   ├── equivalent_control.py         # Model-based equivalent control
│   ├── switching_functions.py        # tanh, linear, sign functions
│   ├── gain_validation.py            # Parameter validation logic
│   └── control_outputs.py            # Structured output data classes
├── algorithms/                    # Algorithm-specific implementations
│   ├── classical/                    # Classical SMC (458 lines → 6 modules)
│   │   ├── controller.py (100 lines)    # Main classical SMC orchestration
│   │   ├── boundary_layer.py (50 lines) # Boundary layer logic
│   │   └── chattering_reduction.py      # Chattering mitigation strategies
│   ├── adaptive/                     # Adaptive SMC (427 lines → 5 modules)
│   │   ├── controller.py (120 lines)    # Main adaptive SMC orchestration
│   │   ├── adaptation_law.py (80 lines) # Online gain adaptation algorithms
│   │   ├── parameter_estimation.py      # Uncertainty estimation methods
│   │   └── stability_monitor.py         # Real-time stability analysis
│   ├── super_twisting/               # Super-Twisting SMC (505 lines → 6 modules)
│   │   ├── controller.py (120 lines)    # Main STA SMC orchestration
│   │   ├── twisting_algorithm.py        # 2nd order sliding mode logic
│   │   ├── higher_order_surface.py      # Higher-order sliding surfaces
│   │   └── convergence_analysis.py      # Finite-time convergence monitoring
│   └── hybrid/                       # Hybrid SMC (643 lines → 7 modules)
│       ├── controller.py (150 lines)    # Main hybrid controller orchestration
│       ├── mode_switching.py            # Adaptive/STA mode switching logic
│       ├── performance_monitor.py       # Performance-based switching decisions
│       └── unified_adaptation.py        # Combined adaptation laws
├── utils/                         # SMC-specific utilities
│   ├── matrix_operations.py           # Matrix regularization, inversion helpers
│   ├── numerical_stability.py        # Conditioning checks, stability analysis
│   └── performance_metrics.py         # SMC-specific metrics (chattering index)
└── interfaces/                    # Clean type-safe interfaces
    ├── base_controller.py             # Abstract SMC base class
    ├── controller_protocol.py         # SMC controller protocol
    └── config_schemas.py              # Pydantic configuration schemas
```

### **Modular Benefits for Research**

#### **1. Scientific Clarity**
```python
# Current: Mixed concerns in 458-line file
class ClassicalSMC:
    def __init__(self, ...):  # 100 lines of validation + setup
    def compute_control(self, ...):  # 200 lines of mixed logic
    def _validate_params(self, ...):  # 50 lines
    # ... more mixed responsibilities

# Proposed: Clear separation of scientific concepts
class ModularClassicalSMC:
    def __init__(self, config: ClassicalSMCConfig):
        self._surface = SlidingSurface(config.surface_gains)
        self._equivalent = EquivalentControl(config.dynamics_model)
        self._switching = SwitchingFunction(config.switch_method)
        self._boundary = BoundaryLayer(config.boundary_layer)

    def compute_control(self, state, state_vars, history):
        surface = self._surface.compute(state)      # Clear responsibility
        u_eq = self._equivalent.compute(state)      # Model-based component
        u_switch = self._switching.apply(surface)   # Robust component
        return self._combine_controls(u_eq, u_switch)
```

#### **2. Component Reusability**
```python
# Shared sliding surface across all SMC types
from controllers.smc.core import SlidingSurface

# Classical SMC uses linear sliding surface
classical_surface = SlidingSurface.linear(gains=[10, 8, 15, 12])

# Adaptive SMC uses the same sliding surface with different gains
adaptive_surface = SlidingSurface.linear(gains=adaptive_gains)

# Super-Twisting uses higher-order sliding surface
sta_surface = SlidingSurface.higher_order(gains=[25, 10, 15, 12, 20, 15])
```

#### **3. Easy Unit Testing**
```python
# Test sliding surface in isolation
def test_sliding_surface_computation():
    surface = LinearSlidingSurface(gains=[1, 2, 3, 4])
    state = np.array([0.1, 0.2, -0.1, 0.05, 0.0, 0.0])
    result = surface.compute(state)
    assert isinstance(result, float)
    assert abs(result - expected_value) < 1e-6

# Test adaptation law independently
def test_adaptation_law_stability():
    adaptation = AdaptationLaw(leak_rate=0.1, rate_limit=10.0)
    gains = adaptation.update_gains(uncertainty=5.0, state=test_state)
    assert all(0.1 <= g <= 100.0 for g in gains)  # Bounded adaptation

# Test switching function properties
def test_tanh_switching_continuity():
    switching = SwitchingFunction("tanh")
    # Test smoothness and monotonicity
    for s in np.linspace(-1, 1, 100):
        result = switching.compute(s, boundary_layer=0.01)
        assert -1 <= result <= 1  # Bounded output
```

#### **4. Performance Optimization**
```python
# Optimized imports - only load what you need
from controllers.smc.core import SlidingSurface
from controllers.smc.algorithms.classical import ClassicalSMC

# vs. importing entire 458-line monolithic class
# Faster startup, reduced memory usage
```

#### **5. Configuration-Driven Design**
```python
# Type-safe configuration with validation
@dataclass(frozen=True)
class ClassicalSMCConfig:
    gains: List[float] = Field(..., min_items=6, max_items=6)
    max_force: float = Field(..., gt=0)
    boundary_layer: float = Field(..., gt=0)
    switch_method: Literal["tanh", "linear", "sign"] = "tanh"

    def __post_init__(self):
        # Scientific constraints validation
        if any(g <= 0 for g in self.gains[:5]):  # k1,k2,λ1,λ2,K > 0
            raise ValueError("SMC stability requires positive surface gains")
```

### **Migration Strategy**

#### **Phase 1: Extract Shared Components** (Week 1-2)
1. Create `core/sliding_surface.py` with unified surface calculations
2. Create `core/switching_functions.py` with chattering reduction methods
3. Create `core/equivalent_control.py` with model-based control logic
4. Extensive testing of shared components

#### **Phase 2: Modularize Classical SMC** (Week 3-4)
1. Split `classic_smc.py` into focused modules
2. Create `algorithms/classical/` package
3. Maintain backward compatibility with facade pattern
4. Comprehensive testing and performance validation

#### **Phase 3: Advanced Controllers** (Week 5-8)
1. Modularize Adaptive SMC (adaptation laws, parameter estimation)
2. Modularize Super-Twisting SMC (higher-order surfaces, twisting algorithms)
3. Modularize Hybrid SMC (mode switching, unified adaptation)
4. Optimize shared component usage across all controllers

#### **Phase 4: Integration and Optimization** (Week 9-10)
1. Update factory to support both modular and legacy interfaces
2. Performance benchmarking and optimization
3. Update documentation and examples
4. Final testing and validation

### **Backward Compatibility Guarantee**

```python
# Existing code continues to work unchanged
from controllers import ClassicalSMC

controller = ClassicalSMC(
    gains=[10, 8, 15, 12, 50, 5],
    max_force=100.0,
    boundary_layer=0.01
)

# New modular API provides enhanced capabilities
from controllers.smc.algorithms.classical import ModularClassicalSMC
from controllers.smc.interfaces import ClassicalSMCConfig

config = ClassicalSMCConfig(
    gains=[10, 8, 15, 12, 50, 5],
    max_force=100.0,
    boundary_layer=0.01
)
modular_controller = ModularClassicalSMC(config)
```

This modular architecture would transform your controllers from monolithic 400-650 line files into focused, testable, reusable components while maintaining scientific rigor and backward compatibility. Each component would have a single responsibility, making the codebase more maintainable and suitable for serious research applications.