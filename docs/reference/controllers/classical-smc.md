# Classical Sliding Mode Control

## Overview

Classical Sliding Mode Control (SMC) represents the foundational approach to sliding mode control theory. It provides robust control through discontinuous switching based on a sliding surface design.

## Mathematical Foundation

The classical SMC law is defined as:

```{math}
:label: eq:classical_smc_control
u = u_{eq} + u_{sw}
```

where:
- $u_{eq}$: Equivalent control term
- $u_{sw}$: Switching control term

### Sliding Surface

The linear sliding surface is designed as:

```{math}
:label: eq:classical_sliding_surface
s = c_1 \dot{\theta_1} + c_2 \dot{\theta_2} + \lambda_1 \theta_1 + \lambda_2 \theta_2
```

### Control Law Components

**Equivalent Control:**
```{math}
u_{eq} = -\frac{1}{g}(f + \dot{s}_{ref})
```

**Switching Control:**
```{math}
u_{sw} = -K \cdot \text{sat}(s/\phi)
```

where $\text{sat}(\cdot)$ is the saturation function used to reduce chattering.

## Implementation Details

### Source Code
- **File**: `src/controllers/classic_smc.py`
- **Class**: `ClassicalSMCController`
- **Key Methods**:
  - `compute_control()`: Main control computation
  - `compute_sliding_surface()`: Sliding surface calculation
  - `update_state()`: State tracking

### Configuration Parameters

```yaml
controllers:
  classical_smc:
    c: [5.0, 8.0, 7.0]          # Sliding surface coefficients
    eta: 2.0                    # Reaching law parameter
    boundary_layer: 0.1         # Boundary layer thickness
    max_control: 150.0          # Control saturation limit
```

### PSO-Optimized Parameters

The following parameters have been optimized using PSO:

**Solution A:**
- $c = [36.65, 28.21, 17.89]$
- $\lambda = [13.05, 20.75]$
- $K = 4.21$
- **Cost**: 517.17

**Solution B:**
- $c = [92.80, 74.10, 6.36]$
- $\lambda = [14.47, 30.33]$
- $K = 0.72$
- **Cost**: 491.76

## Performance Characteristics

### Strengths
- **Robust**: Insensitive to matched uncertainties
- **Finite-time convergence**: Reaches sliding surface in finite time
- **Simple design**: Straightforward implementation

### Limitations
- **Chattering**: High-frequency switching causes control oscillations
- **Control effort**: May require high control energy
- **Sensitivity**: Performance depends on boundary layer tuning

## Simulation Results

### Tracking Performance
- **RMSE**: 1.76 rad (combined θ₁, θ₂)
- **Control effort**: 1.55 × 10⁵ J
- **Chattering index**: 3.2 × 10²

### Typical Response
The classical SMC quickly drives the pendulum angles to zero but exhibits moderate chattering due to the discontinuous switching term. The PSO-optimized gains balance tracking performance with control effort.

## Usage Example

```python
from src.controllers.factory import create_controller
from src.config import load_config

# Load configuration
config = load_config('config.yaml')

# Create controller
controller = create_controller('classical_smc', config)

# Compute control (in simulation loop)
u = controller.compute_control(state, reference, time)
```

## References

1. Utkin, V.I. (1992). *Sliding Modes in Control and Optimization*
2. Edwards, C. & Spurgeon, S. (1998). *Sliding Mode Control: Theory and Applications*
3. Levant, A. (2003). Higher-order sliding modes, differentiation and output-feedback control

## Related Documentation

- [SMC Theory Complete](../theory/smc_theory_complete.md) - Mathematical foundations
- [Implementation Guide](../implementation/code_documentation_index.md) - Code documentation
- [PSO Optimization](../theory/pso_optimization_complete.md) - Parameter tuning details
