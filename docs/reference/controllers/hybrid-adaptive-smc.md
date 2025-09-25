# Hybrid Adaptive STA-SMC

## Overview

The Hybrid Adaptive Super-Twisting SMC combines the continuous control properties of the Super-Twisting Algorithm with online adaptive parameter adjustment. This approach aims to achieve the best of both worlds: chattering-free control and automatic adaptation to system uncertainties.

## Mathematical Foundation

The hybrid controller integrates three components:

```{math}
:label: eq:hybrid_control_structure
u = u_{eq} + u_{sta} + u_{adaptive}
```

### Super-Twisting Component

```{math}
:label: eq:hybrid_sta_component
\begin{align}
u_{sta} &= u_1 + u_2 \\
\dot{u_1} &= -k_1(t) \cdot \text{sign}(s) \\
u_2 &= -k_2(t) |s|^{1/2} \text{sign}(s)
\end{align}
```

### Adaptive Mechanism

```{math}
:label: eq:hybrid_adaptation_laws
\begin{align}
\dot{k_1} &= \gamma_1 |s| - \sigma_1 (k_1 - k_{1,0}) \\
\dot{k_2} &= \gamma_2 |s|^{1/2} - \sigma_2 (k_2 - k_{2,0})
\end{align}
```

where both super-twisting gains adapt online based on sliding surface magnitude.

## Key Innovations

### Continuous Adaptive Control
Unlike classical adaptive SMC, the hybrid approach maintains continuous control through the super-twisting mechanism while adapting parameters online.

### Dual-Rate Adaptation
The adaptation rates for $k_1$ and $k_2$ are designed with different scaling factors to match the super-twisting algorithm structure.

### Model-Based Equivalent Control
Incorporates model knowledge through the equivalent control term while maintaining robustness through adaptive super-twisting.

## Implementation Details

### Source Code
- **File**: `src/controllers/hybrid_adaptive_sta_smc.py`
- **Class**: `HybridAdaptiveSTASMCController`
- **Key Methods**:
  - `compute_control()`: Main control computation
  - `update_adaptive_gains()`: Dual gain adaptation
  - `compute_equivalent_control()`: Model-based component

### Configuration Parameters

```yaml
controllers:
  hybrid_adaptive_sta_smc:
    c: [5.0, 8.0, 7.0]          # Sliding surface coefficients
    k1_initial: 1.0             # Initial super-twisting gain k₁
    k2_initial: 0.5             # Initial super-twisting gain k₂
    gamma1: 0.5                 # Adaptation rate for k₁
    gamma2: 0.3                 # Adaptation rate for k₂
    sigma1: 0.1                 # Leakage coefficient for k₁
    sigma2: 0.1                 # Leakage coefficient for k₂
    alpha: 0.2                  # Proportional damping
```

## Performance Characteristics

### Strengths
- **Chattering-free**: Inherits super-twisting continuous control
- **Self-tuning**: Adapts to system uncertainties automatically
- **Fast convergence**: Combines finite-time convergence with adaptation
- **Robust**: Maintains robustness under parameter variations
- **Smooth control**: Excellent actuator compatibility

### Limitations
- **Complexity**: Most complex controller in the suite
- **Parameter tuning**: Multiple adaptation parameters to configure
- **Computational cost**: Higher computational requirements
- **Initialization**: Requires proper initialization of adaptive gains

## Current Simulation Results

**⚠️ Note**: Results shown are for **default parameters only** (not PSO-optimized):

### Exceptional Performance with Defaults
- **RMSE**: 0.0083 rad (combined θ₁, θ₂)
- **Control effort**: 2.83 J
- **Chattering index**: 3.42 × 10³

### Analysis
Remarkably, this controller achieves excellent performance even with default parameters:
- **Lowest RMSE**: By far the best tracking performance
- **Minimal control effort**: Only 2.83 J compared to 10⁵ J for other controllers
- **Good smoothness**: Moderate chattering index indicates acceptable control quality

This exceptional performance with default parameters suggests the controller is either:
1. Well-designed with good default parameter choices
2. Robust to parameter variations due to adaptive mechanism
3. Has significant potential for even better performance when PSO-optimized

## Adaptation Dynamics

### Dual-Gain Evolution
The controller adapts two gains simultaneously:

**k₁ Adaptation:**
- Responds to sliding surface magnitude $|s|$
- Controls the integral component strength
- Balances convergence speed vs. stability

**k₂ Adaptation:**
- Responds to $|s|^{1/2}$ for super-twisting compatibility
- Controls the proportional component strength
- Ensures finite-time convergence properties

### Convergence Properties
The hybrid approach maintains the finite-time convergence of super-twisting while achieving:
- Automatic gain adjustment
- Uncertainty compensation
- Chattering elimination

## Future Work

### PSO Optimization Potential
Despite good default performance, PSO optimization could further improve:

**Optimization Parameters:**
- $\gamma_1, \gamma_2 \in [0.1, 5.0]$: Adaptation rates
- $\sigma_1, \sigma_2 \in [0.01, 0.5]$: Leakage coefficients
- $k_{1,0}, k_{2,0} \in [0.1, 10.0]$: Initial gains
- $c \in [1.0, 20.0]$: Sliding surface coefficients

**Expected Improvements:**
- Even lower RMSE (potentially < 0.005)
- Further reduced control effort
- Improved transient response
- Better adaptation convergence

## Usage Example

```python
from src.controllers.factory import create_controller
from src.config import load_config

# Load configuration
config = load_config('config.yaml')

# Create controller
controller = create_controller('hybrid_adaptive_sta_smc', config)

# Simulation loop
for t, state in simulation:
    u = controller.compute_control(state, reference, t)

    # Monitor adaptive gains
    k1, k2 = controller.get_adaptive_gains()
    print(f"Adaptive gains: k1={k1:.3f}, k2={k2:.3f}")
```

## Theoretical Foundation

### Lyapunov Stability
The hybrid controller uses the Lyapunov function:

```{math}
V = V_{sta} + \frac{1}{2\gamma_1}\tilde{k_1}^2 + \frac{1}{2\gamma_2}\tilde{k_2}^2
```

where $V_{sta}$ is the super-twisting Lyapunov function.

### Convergence Analysis
The controller ensures:
1. Finite-time convergence to sliding surface
2. Bounded adaptive gain evolution
3. Continuous control signal
4. Robust performance under uncertainties

## Comparison with Other Controllers

| Aspect | Classical SMC | Super-Twisting | Adaptive SMC | **Hybrid Adaptive** |
|--------|---------------|----------------|--------------|-------------------|
| Chattering | High | Low | Medium | **Lowest** |
| RMSE | 1.76 | 20.61 | 24.30 | **0.0083** |
| Control Effort | High | Medium | High | **Lowest** |
| Complexity | Low | Medium | High | **Highest** |
| Robustness | Good | Good | Excellent | **Excellent** |

## References

1. Levant, A. (2003). Higher-order sliding modes, differentiation and output-feedback control
2. Moreno, J.A. & Osorio, M. (2008). Strict Lyapunov functions for the super-twisting algorithm
3. Shtessel, Y. et al. (2014). *Sliding Mode Control and Observation*
4. Fridman, L. & Levant, A. (2002). Higher order sliding modes

## Related Documentation

- [Super-Twisting SMC](super-twisting-smc.md) - Base algorithm
- [Adaptive SMC](adaptive-smc.md) - Adaptation principles
- [SMC Theory Complete](../theory/smc_theory_complete.md) - Mathematical foundations
- [Results Analysis](../presentation/results-discussion.md) - Performance comparison
