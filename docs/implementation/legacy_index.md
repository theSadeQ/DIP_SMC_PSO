# Implementation Documentation (Legacy)

```{toctree}
:maxdepth: 2
:hidden:

code_documentation_index
api/index
examples/index
```

Note: This section has moved. See Reference for the current structure.

This section provides comprehensive coverage of the DIP_SMC_PSO implementation, including detailed API documentation with mathematical context, code examples, and integration guides.

## Contents

::::{grid} 2
:::{grid-item-card} **Code Documentation Index**
:link: code_documentation_index
:link-type: doc

Central index of all modules with bidirectional links between theory and implementation.
:::

:::{grid-item-card} **API Reference**
:link: api/index
:link-type: doc

Complete API documentation with mathematical foundations, usage examples, and cross-references.
:::

:::{grid-item-card} **Examples & Tutorials**
:link: examples/index
:link-type: doc

Runnable code examples, tutorials, and integration guides for all components.
:::

:::{grid-item-card} **Configuration Guide**
:link: ../configuration
:link-type: doc

YAML configuration reference with parameter descriptions and validation rules.
:::
::::

## Architecture Overview

The DIP_SMC_PSO implementation follows a modular architecture with clear separation of concerns:

```{mermaid}
flowchart TB
    subgraph "Core Engine"
        Dynamics[dynamics.py<br/>System Models]
        SimRunner[simulation_runner.py<br/>Execution Engine]
        SimContext[simulation_context.py<br/>State Management]
        VectorSim[vector_sim.py<br/>Batch Processing]
    end

    subgraph "Controllers"
        ClassicSMC[classic_smc.py<br/>Classical SMC]
        STASMC[sta_smc.py<br/>Super-Twisting]
        AdaptiveSMC[adaptive_smc.py<br/>Adaptive Control]
        HybridSMC[hybrid_adaptive_sta_smc.py<br/>Hybrid Controller]
        Factory[factory.py<br/>Controller Factory]
    end

    subgraph "Optimization"
        PSOOpt[pso_optimizer.py<br/>PSO Implementation]
        CostFunc[Cost Functions<br/>Performance Metrics]
    end

    subgraph "Interfaces"
        CLI[simulate.py<br/>Command Line]
        Web[streamlit_app.py<br/>Web Interface]
        HIL[HIL Components<br/>Real-time Simulation]
    end

    Dynamics --> SimRunner
    SimContext --> SimRunner
    Controllers --> SimRunner
    SimRunner --> VectorSim
    Factory --> Controllers
    PSOOpt --> Controllers
    SimRunner --> CLI
    SimRunner --> Web
    SimRunner --> HIL
```

## Design Principles

### 1. Theory-Implementation Alignment

Every implementation component directly corresponds to theoretical concepts:

- **System Dynamics** ({doc}`../theory/system_dynamics_complete`) → `src/core/dynamics.py`
- **SMC Theory** ({doc}`../theory/smc_theory_complete`) → `src/controllers/`
- **PSO Theory** ({doc}`../theory/pso_optimization_complete`) → `src/optimizer/pso_optimizer.py`

### 2. Mathematical Traceability

Code implementations include explicit references to theoretical equations:

```python
def sliding_surface(self, x: np.ndarray) -> float:
    """
    Compute sliding surface value s(x) = Sx.

    Based on equation {eq}`eq:sliding_surface_design` from SMC theory.

    Parameters
    ----------
    x : np.ndarray, shape (6,)
        State vector [q, q_dot]

    Returns
    -------
    s : float
        Sliding surface value

    See Also
    --------
    theory.smc_theory_complete : Theoretical foundation
    """
    return self.S @ x  # Implements eq:sliding_surface_design
```

### 3. Performance Optimization

- **Numba JIT compilation** for computational kernels
- **Vectorized operations** for batch simulations
- **Efficient matrix operations** using NumPy/SciPy
- **Memory-efficient** state management

### 4. Comprehensive Testing

- **Unit tests** for individual components
- **Integration tests** for complete workflows
- **Property-based tests** for mathematical properties
- **Performance benchmarks** for regression detection

## Key Implementation Features

### Type Safety and Validation

All public APIs use comprehensive type hints and runtime validation:

```python
from typing import Protocol, TypeVar, Generic
from pydantic import BaseModel, validator

class ControllerProtocol(Protocol):
    """Protocol defining controller interface."""

    def compute_control(
        self,
        x: np.ndarray,
        x_ref: np.ndarray,
        t: float
    ) -> float:
        """Compute control input."""
        ...

class SimulationConfig(BaseModel):
    """Validated simulation configuration."""

    duration: float = Field(gt=0, description="Simulation duration")
    dt: float = Field(gt=0, lt=0.1, description="Time step")

    @validator('dt')
    def dt_stability(cls, v, values):
        if 'duration' in values and v > values['duration'] / 100:
            raise ValueError("Time step too large for stability")
        return v
```

### Configuration Management

Centralized YAML-based configuration with validation and documentation:

```yaml
# Complete configuration with inline documentation
controllers:
  classical_smc:
    # Sliding surface gain (see eq:sliding_surface_design)
    c: 5.0
    # Switching gain (see eq:reaching_condition)
    eta: 1.0
    # Boundary layer thickness (chattering reduction)
    epsilon: 0.1

pso:
  # Swarm size (computational vs. exploration tradeoff)
  n_particles: 20
  # Maximum iterations (convergence vs. time tradeoff)
  iters: 200
  # Objective weights (see eq:pso_objective)
  weights:
    error: 1.0      # Tracking performance
    control: 0.1    # Energy efficiency
    smoothness: 0.01 # Chattering reduction
```

### Error Handling and Diagnostics

Comprehensive error handling with domain-specific exceptions:

```python
class ControlSystemError(Exception):
    """Base exception for control system errors."""
    pass

class NumericalInstabilityError(ControlSystemError):
    """Raised when numerical instability detected."""

    def __init__(self, t: float, x: np.ndarray):
        super().__init__(
            f"Numerical instability at t={t:.3f}, "
            f"max(|x|)={np.max(np.abs(x)):.2e}"
        )
        self.time = t
        self.state = x.copy()

class ConvergenceError(ControlSystemError):
    """Raised when optimization fails to converge."""
    pass
```

## Module Documentation

### Core Modules

```{eval-rst}
.. autosummary::
   :toctree: api
   :recursive:

   src.core.dynamics
   src.core.simulation_runner
   src.core.simulation_context
   src.core.vector_sim
```

### Controller Modules

```{eval-rst}
.. autosummary::
   :toctree: api
   :recursive:

   src.controllers.classic_smc
   src.controllers.sta_smc
   src.controllers.adaptive_smc
   src.controllers.hybrid_adaptive_sta_smc
   src.controllers.factory
```

### Optimization Modules

```{eval-rst}
.. autosummary::
   :toctree: api
   :recursive:

   src.optimizer.pso_optimizer
```

### Utility Modules

```{eval-rst}
.. autosummary::
   :toctree: api
   :recursive:

   src.utils.control_analysis
   src.utils.visualization
   src.utils.statistics
```

## Getting Started

1. **Installation**: Follow {doc}`../guides/installation`
2. **Quick Start**: See {doc}`examples/quickstart_tutorial`
3. **Configuration**: Read {doc}`../configuration`
4. **API Usage**: Browse {doc}`api/index`

For theoretical background, see {doc}`../theory/index`.
