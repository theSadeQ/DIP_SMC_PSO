# Super-Twisting Sliding Mode Control

## Overview

Super-Twisting Algorithm (STA) is a second-order sliding mode controller that eliminates chattering while preserving the robust properties of sliding mode control. It achieves continuous control through an internal integrator mechanism.

## Mathematical Foundation

The super-twisting control law is defined as:

```{math}
:label: eq:sta_control_law
\begin{align}
u &= u_1 + u_2 \\
\dot{u_1} &= -k_1 \text{sign}(s) \\
u_2 &= -k_2 |s|^{1/2} \text{sign}(s)
\end{align}
```

where:
- $k_1, k_2 > 0$: Super-twisting gains
- $s$: Sliding surface
- $u_1$: Integral component
- $u_2$: Proportional component

## Key Properties

### Finite-Time Convergence
The super-twisting algorithm ensures finite-time convergence to the sliding surface with the convergence condition:

```{math}
k_2 > \sqrt{2k_1} \cdot L
```

where $L$ is the Lipschitz constant of the uncertainty.

### Continuous Control
Unlike classical SMC, the super-twisting algorithm produces a continuous control signal, eliminating chattering while maintaining robustness.

## Implementation Details

### Source Code
- **File**: `src/controllers/sta_smc.py`
- **Class**: `SuperTwistingSMCController`
- **Key Methods**:
  - `compute_control()`: Main control computation
  - `update_integral()`: Integral state update
  - `compute_sliding_surface()`: Sliding surface calculation

### Configuration Parameters

```yaml
controllers:
  sta_smc:
    c: [5.0, 8.0, 7.0]          # Sliding surface coefficients
    k_st: 10.0                  # Super-twisting gain k1
    k_int: 5.0                  # Super-twisting gain k2
    max_control: 150.0          # Control saturation limit
```

### Default vs. Optimal Parameters

**Current Status**: This controller uses baseline default parameters and has **not yet been PSO-optimized**.

**Default Parameters:**
- $c = [5.0, 8.0, 7.0]$
- $k_1 = 10.0$ (`k_st`)
- $k_2 = 5.0$ (`k_int`)

**Expected Improvements with PSO**: The poor performance with default parameters (RMSE: 20.61) suggests significant improvement potential through proper optimization.

## Performance Characteristics

### Strengths
- **Chattering-free**: Continuous control signal eliminates high-frequency switching
- **Finite-time convergence**: Guaranteed convergence in finite time
- **Robust**: Maintains robustness to matched uncertainties
- **Smooth control**: Better actuator compatibility

### Limitations
- **Parameter sensitivity**: Requires careful tuning of $k_1$ and $k_2$
- **Complexity**: More complex than classical SMC
- **Initialization**: Integral state requires proper initialization

## Current Simulation Results

**⚠️ Note**: Results shown are for **default parameters only** (not PSO-optimized):

### Performance Metrics
- **RMSE**: 20.61 rad (combined θ₁, θ₂)
- **Control effort**: 9.53 × 10⁴ J
- **Chattering index**: 4.38 × 10⁴

### Analysis
The high RMSE and chattering index with default parameters indicate suboptimal tuning. The algorithm shows potential but requires PSO optimization to achieve competitive performance.

## Future Work

### PSO Optimization Required
Complete PSO optimization should be performed with search bounds:
- $k_1 \in [1.0, 50.0]$
- $k_2 \in [1.0, 30.0]$
- $c \in [1.0, 20.0]$ (for each component)

### Expected Outcomes
- Significant reduction in RMSE
- Lower chattering index
- Improved control effort efficiency
- Better convergence properties

## Usage Example

```python
from src.controllers.factory import create_controller
from src.config import load_config

# Load configuration
config = load_config('config.yaml')

# Create controller
controller = create_controller('sta_smc', config)

# Compute control (in simulation loop)
u = controller.compute_control(state, reference, time)
```

## Mathematical Background

### Lyapunov Analysis
The super-twisting algorithm can be analyzed using the Lyapunov function:

```{math}
V = |s| + \frac{1}{2k_1}u_1^2
```

### Convergence Properties
Under proper gain selection, the algorithm achieves:
1. Finite-time convergence to $s = 0$
2. Continuous control signal
3. Robustness to bounded uncertainties

## References

1. Levant, A. (2003). Higher-order sliding modes, differentiation and output-feedback control
2. Moreno, J.A. & Osorio, M. (2008). A Lyapunov approach to second-order sliding mode controllers
3. Utkin, V. & Poznyak, A. (2013). Adaptive sliding mode control with application to super-twist algorithm

## Related Documentation

- [SMC Theory Complete](../theory/smc_theory_complete.md) - Mathematical foundations
- [Classical SMC](classical-smc.md) - Comparison with traditional approach
- [Results Discussion](../presentation/results-discussion.md) - Performance analysis
