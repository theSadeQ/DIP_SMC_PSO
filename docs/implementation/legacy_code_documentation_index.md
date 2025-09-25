# Code Documentation Index (Legacy)
Note: This section has moved. See the Reference section for current API navigation.
This section provides a comprehensive mapping between the theoretical foundations and their concrete implementations in the DIP_SMC_PSO codebase, enabling seamless navigation from mathematical concepts to executable code.

## Theory-Implementation Mapping

### System Dynamics → Core Modules

The complete mathematical derivation in {doc}`../theory/system_dynamics_complete` is implemented across these core modules:

```{mermaid}
flowchart LR
    Theory[System Dynamics Theory<br/>{doc}'../theory/system_dynamics_complete']

    subgraph "Core Implementation"
        Dynamics[src.core.dynamics<br/>Simplified Model]
        DynamicsFull[src.core.dynamics_full<br/>Complete Nonlinear Model]
        SimRunner[src.core.simulation_runner<br/>Integration Engine]
        Context[src.core.simulation_context<br/>State Management]
    end

    Theory --> Dynamics
    Theory --> DynamicsFull
    Dynamics --> SimRunner
    DynamicsFull --> SimRunner
    SimRunner --> Context

    style Theory fill:#e8f5e8
    style Dynamics fill:#f3e5f5
    style DynamicsFull fill:#f3e5f5
```

**Key Equation Implementations:**

| Equation | Module | Function/Class |
|----------|--------|----------------|
| {eq}`mass_matrix_form` | `dynamics_full.py` | `DoublePendulumFull.compute_mass_matrix()` |
| {eq}`coriolis_matrix` | `dynamics_full.py` | `DoublePendulumFull.compute_coriolis_matrix()` |
| {eq}`nonlinear_state_space` | `dynamics.py` | `DoublePendulum.dynamics()` |
| {eq}`linear_state_space` | `dynamics.py` | `DoublePendulum.linearize()` |

### SMC Theory → Controller Modules

The sliding mode control theory from {doc}`../theory/smc_theory_complete` is implemented in specialized controller classes:

```{mermaid}
flowchart TB
    SMCTheory[SMC Theory<br/>{doc}'../theory/smc_theory_complete']

    subgraph "Controller Implementations"
        ClassicSMC[src.controllers.classic_smc<br/>Classical SMC]
        STASMC[src.controllers.sta_smc<br/>Super-Twisting SMC]
        AdaptiveSMC[src.controllers.adaptive_smc<br/>Adaptive SMC]
        HybridSMC[src.controllers.hybrid_adaptive_sta_smc<br/>Hybrid Controller]
        Factory[src.controllers.factory<br/>Controller Factory]
    end

    SMCTheory --> ClassicSMC
    SMCTheory --> STASMC
    SMCTheory --> AdaptiveSMC
    SMCTheory --> HybridSMC
    Factory --> ClassicSMC
    Factory --> STASMC
    Factory --> AdaptiveSMC
    Factory --> HybridSMC

    style SMCTheory fill:#e8f5e8
    style ClassicSMC fill:#fff3e0
    style STASMC fill:#fff3e0
    style AdaptiveSMC fill:#fff3e0
    style HybridSMC fill:#fff3e0
```

**Key Algorithm Implementations:**

| Algorithm | Module | Method | Theory Reference |
|-----------|--------|--------|------------------|
| Classical SMC | `classic_smc.py` | `compute_control()` | {eq}`classical_smc_structure` |
| Super-Twisting | `sta_smc.py` | `compute_control()` | {eq}`supertwisting_control` |
| Adaptive Law | `adaptive_smc.py` | `update_parameters()` | {eq}`adaptive_smc_law` |
| Lyapunov Function | `adaptive_smc.py` | `compute_lyapunov()` | {eq}`adaptive_lyapunov` |

### PSO Theory → Optimization Module

The particle swarm optimization theory from {doc}`../theory/pso_optimization_complete` is implemented in the optimization framework:

```{mermaid}
flowchart LR
    PSOTheory[PSO Theory<br/>{doc}'../theory/pso_optimization_complete']

    subgraph "Optimization Implementation"
        PSOOpt[src.optimizer.pso_optimizer<br/>PSO Implementation]
        CostFunc[Cost Function Evaluation<br/>Multi-objective]
        Constraints[Constraint Handling<br/>Parameter Bounds]
    end

    PSOTheory --> PSOOpt
    PSOOpt --> CostFunc
    PSOOpt --> Constraints

    style PSOTheory fill:#e8f5e8
    style PSOOpt fill:#e1f5fe
```

**Key Optimization Implementations:**

| Component | Module | Method | Theory Reference |
|-----------|--------|--------|------------------|
| Particle Updates | `pso_optimizer.py` | `pyswarms.single.GlobalBestPSO` (wrapped in `optimise()`) | {eq}`pso_velocity_update` |
| Fitness Evaluation | `pso_optimizer.py` | `_fitness()` | {eq}`multiobjective_problem` |
| Cost Computation | `pso_optimizer.py` | `_compute_cost_from_traj()` | {eq}`parameter_constraints` |

**Implementation Note:** This project uses **PySwarms (GlobalBestPSO)** as the underlying PSO engine. Inertia scheduling and velocity clamping are applied via `w_schedule` and `velocity_clamp` configuration parameters.

## Module Architecture

### Core System (`src/core/`)

The core modules implement the fundamental mathematical models and simulation infrastructure:

**Core Modules Documentation:**
- `src.core.dynamics` - Simplified dynamics model implementation
- `src.core.dynamics_full` - Complete nonlinear dynamics with full derivation
- `src.core.simulation_runner` - Main simulation execution engine
- `src.core.simulation_context` - Unified state management and context
- `src.core.vector_sim` - Numba-accelerated batch simulation processing
- `src.core.protocols` - Type protocols and interface definitions

**Mathematical Foundations Implemented:**
- Lagrangian dynamics derivation → `dynamics_full.py`
- State-space representation → `dynamics.py`
- Numerical integration → `simulation_runner.py`
- Batch processing → `vector_sim.py`

### Controller Framework (`src/controllers/`)

Each controller implements specific SMC algorithms with rigorous mathematical foundations:

**Controller Modules Documentation:**
- `src.controllers.classic_smc` - Classical sliding mode controller with boundary layer
- `src.controllers.sta_smc` - Super-twisting algorithm for chattering-free control
- `src.controllers.adaptive_smc` - Adaptive SMC with parameter estimation
- `src.controllers.hybrid_adaptive_sta_smc` - Hybrid adaptive super-twisting controller
- `src.controllers.factory` - Controller factory for dynamic instantiation

**Control Theory Implementations:**
- Sliding surface design → All controllers implement {eq}`linear_sliding_surface`
- Equivalent control → {eq}`equivalent_control` in base classes
- Switching control → Algorithm-specific implementations
- Lyapunov analysis → Validation methods in each controller

### Optimization Engine (`src/optimizer/`)

**Optimization Modules Documentation:**
- `src.optimizer.pso_optimizer` - Complete PSO implementation with multi-objective support

**Optimization Theory Implementations:**
- Particle dynamics → {eq}`pso_velocity_update` and {eq}`pso_position_update`
- Convergence analysis → Built-in monitoring and stopping criteria
- Multi-objective handling → Weighted sum approach {eq}`weighted_sum`

## Cross-Reference System

### Equation-to-Code Mapping

Every significant mathematical equation has a corresponding implementation:

```{list-table} Complete Equation-Code Cross-Reference
:header-rows: 1
:name: table:equation_code_mapping

* - Theory Section
  - Equation
  - Implementation Module
  - Function/Method
  - Line Reference
* - System Dynamics
  - {eq}`mass_matrix_form`
  - `dynamics_full.py`
  - `compute_mass_matrix()`
  - ~150
* - System Dynamics
  - {eq}`coriolis_matrix`
  - `dynamics_full.py`
  - `compute_coriolis_matrix()`
  - ~200
* - SMC Theory
  - {eq}`classical_smc_structure`
  - `classic_smc.py`
  - `compute_control()`
  - ~80
* - SMC Theory
  - {eq}`supertwisting_control`
  - `sta_smc.py`
  - `compute_control()`
  - ~95
* - SMC Theory
  - {eq}`adaptive_smc_law`
  - `adaptive_smc.py`
  - `update_parameters()`
  - ~120
* - PSO Theory
  - {eq}`pso_velocity_update`
  - `pso_optimizer.py`
  - `optimise()` (via PySwarms)
  - ~596
* - PSO Theory
  - {eq}`multiobjective_problem`
  - `pso_optimizer.py`
  - `_fitness()`
  - ~500
```

### API Documentation Links

Each API page includes:
- **Mathematical Context**: Links to relevant theory sections
- **Implementation Details**: Step-by-step algorithm breakdown
- **Usage Examples**: Practical code examples with expected outputs
- **Performance Notes**: Computational complexity and optimization tips
- **Validation**: Unit tests and theoretical property verification

## Code Quality Assurance

### Documentation Standards

All public APIs follow NumPy docstring conventions with mathematical enhancement:

```python
def compute_control(self, x: np.ndarray, x_ref: np.ndarray, t: float) -> float:
    """
    Compute sliding mode control input.

    Implements the classical SMC law from {eq}`classical_smc_structure`:

    .. math::
        u(t) = u_{eq}(t) + u_{sw}(t)

    where equivalent control ensures sliding surface convergence.

    Parameters
    ----------
    x : np.ndarray, shape (6,)
        Current state vector [x, θ₁, θ₂, ẋ, θ̇₁, θ̇₂]
    x_ref : np.ndarray, shape (6,)
        Reference trajectory
    t : float
        Current time

    Returns
    -------
    u : float
        Control force (N)

    Notes
    -----
    The sliding surface is defined as in {eq}`linear_sliding_surface`.
    Stability is guaranteed by Theorem 3 in {doc}`../theory/smc_theory_complete`.

    Examples
    --------
    >>> controller = ClassicalSMC(c=[5, 8, 7], eta=2.0, epsilon=0.1)
    >>> x = np.array([0.1, 0.05, 0.02, 0, 0, 0])
    >>> x_ref = np.zeros(6)
    >>> u = controller.compute_control(x, x_ref, 0.0)
    >>> print(f"Control input: {u:.3f} N")
    Control input: -1.234 N

    See Also
    --------
    theory.smc_theory_complete : Mathematical foundations
    sta_smc.SuperTwistingSMC : Alternative SMC implementation
    """
```

### Type Safety and Validation

All implementations include comprehensive type hints and runtime validation:

```python
from typing import Protocol, Optional, Tuple
from pydantic import BaseModel, validator, Field
import numpy as np

class ControllerProtocol(Protocol):
    """Protocol defining the controller interface."""

    def compute_control(
        self,
        x: np.ndarray,
        x_ref: np.ndarray,
        t: float
    ) -> float:
        """Compute control input with guaranteed interface."""
        ...

class SMCParameters(BaseModel):
    """Validated SMC parameters with mathematical constraints."""

    c: List[float] = Field(..., description="Sliding surface gains")
    eta: float = Field(gt=0, description="Switching gain")
    epsilon: float = Field(gt=0, lt=1, description="Boundary layer")

    @validator('c')
    def validate_sliding_gains(cls, v):
        if not all(ci > 0 for ci in v):
            raise ValueError("All sliding gains must be positive")
        return v

    @validator('eta')
    def validate_switching_gain(cls, v, values):
        # Theoretical lower bound from uncertainty analysis
        if v < 0.1:
            raise ValueError("Switching gain too small for robustness")
        return v
```

### Unit Test Integration

Every algorithm implementation includes unit tests that verify theoretical properties:

```python
def test_sliding_surface_stability():
    """Verify that sliding surface has stable dynamics."""
    controller = ClassicalSMC(c=[1, 2, 3], eta=1.0, epsilon=0.1)

    # Test eigenvalues of sliding surface dynamics
    A_slide = controller.get_sliding_dynamics_matrix()
    eigenvals = np.linalg.eigvals(A_slide)

    # Theorem 1: All eigenvalues should be negative
    assert all(np.real(eig) < 0 for eig in eigenvals)

def test_lyapunov_decrease():
    """Verify Lyapunov function decreases along trajectories."""
    controller = AdaptiveSMC(c=[2, 3, 4], gamma=1.0)

    # Test Lyapunov function derivative
    x = np.random.rand(6)
    V_dot = controller.compute_lyapunov_derivative(x)

    # Theorem 5: Lyapunov derivative should be negative
    assert V_dot <= 0
```

## Usage Patterns

### Basic Controller Usage

```python
from src.controllers.factory import create_controller
from src.core.dynamics import DoublePendulum
from src.core.simulation_runner import SimulationRunner

# Create system and controller using theory-based parameters
system = DoublePendulum()
controller = create_controller(
    'classical_smc',
    c=[5.0, 8.0, 7.0],     # From {eq}`linear_sliding_surface`
    eta=2.0,               # Satisfies {eq}`reaching_condition`
    epsilon=0.05           # Boundary layer for chattering reduction
)

# Run simulation with automatic validation
runner = SimulationRunner(system, controller)
results = runner.simulate(duration=10.0, dt=0.01)
```

### PSO Optimization Workflow

```python
from src.optimizer.pso_optimizer import PSOOptimizer
from src.core.simulation_context import SimulationContext

# Set up optimization problem from theory
optimizer = PSOOptimizer(
    n_particles=30,        # From {eq}`swarm_size_rule`
    bounds=[[0.1, 20]] * 3 + [[0.1, 10], [0.001, 0.5]],  # Physical constraints
    objectives=['tracking', 'control_effort', 'smoothness']  # {eq}`multiobjective_problem`
)

# Run optimization with theoretical convergence monitoring
context = SimulationContext('classical_smc')
best_params = optimizer.optimize(context, max_generations=50)
```

## Integration Examples

### Complete Workflow Example

```python
"""
Complete DIP-SMC-PSO workflow demonstrating theory-implementation integration.
"""
import numpy as np
from src.config import load_config
from src.controllers.factory import create_controller
from src.core.dynamics_full import DoublePendulumFull
from src.optimizer.pso_optimizer import PSOOptimizer
from src.utils.visualization import plot_results

def main():
    # Load validated configuration
    config = load_config('config.yaml')

    # Create system using complete dynamics {eq}`mass_matrix_form`
    system = DoublePendulumFull(
        m0=config.physics.m0, m1=config.physics.m1, m2=config.physics.m2,
        l1=config.physics.l1, l2=config.physics.l2, g=config.physics.g
    )

    # Optimize controller parameters using PSO theory
    optimizer = PSOOptimizer(config.pso)
    best_params = optimizer.optimize_controller(
        system=system,
        controller_type='hybrid_adaptive_sta_smc',
        objectives={
            'tracking': 1.0,      # {eq}`tracking_objective`
            'effort': 0.1,        # {eq}`control_effort_objective`
            'smoothness': 0.01    # {eq}`smoothness_objective`
        }
    )

    # Create optimized controller
    controller = create_controller('hybrid_adaptive_sta_smc', **best_params)

    # Validate theoretical properties
    assert controller.verify_stability_conditions()  # Theorem 5
    assert controller.verify_convergence_properties()  # Theorem 4

    # Run final simulation
    runner = SimulationRunner(system, controller)
    results = runner.simulate(duration=10.0)

    # Visualize and analyze results
    plot_results(results)
    print(f"Performance metrics: {results.compute_metrics()}")

if __name__ == "__main__":
    main()
```

## Contributing Guidelines

### Adding New Controllers

1. **Theory Development**: Document mathematical foundations in `docs/theory/`
2. **Implementation**: Follow the `ControllerProtocol` interface
3. **Documentation**: Include equation cross-references and examples
4. **Testing**: Verify theoretical properties with unit tests
5. **Integration**: Add to factory and configuration system

### Code Style Requirements

- **Type Hints**: All public methods must include comprehensive type hints
- **Docstrings**: NumPy style with mathematical context and equation references
- **Validation**: Use Pydantic for parameter validation with theoretical constraints
- **Testing**: Property-based tests that verify mathematical guarantees

---

**Next Steps:**
- Browse individual module documentation in {doc}`api/index`
- See practical examples in {doc}`examples/index`
- Review theoretical foundations in {doc}`../theory/index`
