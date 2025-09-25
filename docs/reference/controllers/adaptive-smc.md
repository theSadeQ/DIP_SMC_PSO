# Adaptive Sliding Mode Control

## Overview

Adaptive Sliding Mode Control automatically adjusts controller gains online to handle system uncertainties without requiring a priori knowledge of uncertainty bounds. This approach combines the robustness of sliding mode control with adaptive control techniques.

## Mathematical Foundation

The adaptive SMC consists of a sliding mode controller with adaptive gain adjustment:

```{math}
:label: eq:adaptive_smc_structure
u = u_{eq} + u_{sw} + u_{adaptive}
```

### Adaptive Control Law

```{math}
:label: eq:adaptive_control_law
\begin{align}
u_{sw} &= -K(t) \cdot \text{sign}(s) \\
\dot{K} &= \gamma |s| - \sigma (K - K_0)
\end{align}
```

where:
- $K(t)$: Time-varying switching gain
- $\gamma > 0$: Adaptation rate
- $\sigma > 0$: Leakage coefficient
- $K_0$: Nominal gain value

### Lyapunov-Based Design

The adaptation law is designed using the Lyapunov function:

```{math}
:label: eq:adaptive_lyapunov_function
V = \frac{1}{2}s^2 + \frac{1}{2\gamma}\tilde{K}^2
```

where $\tilde{K} = K - K^*$ is the gain estimation error.

## Implementation Details

### Source Code
- **File**: `src/controllers/adaptive_smc.py`
- **Class**: `AdaptiveSMCController`
- **Key Methods**:
  - `compute_control()`: Main control computation
  - `update_adaptive_gains()`: Online gain adaptation
  - `compute_lyapunov()`: Lyapunov function evaluation

### Configuration Parameters

```yaml
controllers:
  adaptive_smc:
    c: [5.0, 8.0, 7.0]          # Sliding surface coefficients
    adaptation_rate: 1.0         # Adaptation rate γ
    leakage_coefficient: 0.1     # Leakage coefficient σ
    initial_gain: 1.0           # Initial switching gain K₀
    alpha: 0.5                  # Proportional damping
    boundary_layer: 0.1         # Boundary layer thickness
```

### Default vs. Optimal Parameters

**Current Status**: This controller uses baseline default parameters and has **not yet been PSO-optimized**.

**Default Parameters:**
- $c = [5.0, 8.0, 7.0]$
- $\gamma = 1.0$
- $\sigma = 0.1$
- $K_0 = 1.0$
- $\alpha = 0.5$

## Adaptive Mechanism

### Online Gain Adjustment
The switching gain $K(t)$ adapts according to:

1. **Increase**: When $|s|$ is large (far from sliding surface)
2. **Decrease**: Through leakage term to prevent gain drift
3. **Equilibrium**: Balances adaptation and leakage

### Chattering Reduction
- Boundary layer approach: $\text{sat}(s/\phi)$ instead of $\text{sign}(s)$
- Proportional damping: $\alpha s$ term for smooth control
- Adaptive gain prevents excessive switching

## Performance Characteristics

### Strengths
- **Self-tuning**: Automatically adjusts to uncertainties
- **No prior knowledge**: Doesn't require uncertainty bounds
- **Chattering reduction**: Adaptive nature reduces switching amplitude
- **Stability**: Lyapunov-based design ensures stability

### Limitations
- **Complexity**: More complex than classical SMC
- **Parameter sensitivity**: Multiple parameters to tune
- **Convergence time**: May require longer settling time
- **Gain drift**: Requires leakage to prevent parameter drift

## Current Simulation Results

**⚠️ Note**: Results shown are for **default parameters only** (not PSO-optimized):

### Performance Metrics
- **RMSE**: 24.30 rad (combined θ₁, θ₂)
- **Control effort**: 2.07 × 10⁵ J
- **Chattering index**: 1.63 × 10³

### Analysis
The high RMSE with default parameters suggests the adaptation mechanism is not properly tuned. The moderate chattering index indicates some improvement over classical SMC, but overall performance is poor without optimization.

## Adaptation Dynamics

### Typical Behavior
1. **Initial phase**: High adaptation rate due to large sliding surface error
2. **Convergence phase**: Gain stabilizes as system approaches sliding surface
3. **Steady state**: Small oscillations around optimal gain value

### Gain Evolution
The adaptive gain typically exhibits:
- Rapid increase when disturbances occur
- Gradual decrease through leakage when system is stable
- Bounded growth due to leakage mechanism

## Future Work

### PSO Optimization Required
Complete PSO optimization should be performed with search bounds:
- $\gamma \in [0.1, 10.0]$: Adaptation rate
- $\sigma \in [0.01, 1.0]$: Leakage coefficient
- $K_0 \in [0.1, 10.0]$: Initial gain
- $\alpha \in [0.1, 2.0]$: Damping coefficient
- $c \in [1.0, 20.0]$: Sliding surface coefficients

### Expected Improvements
- Dramatic reduction in RMSE through proper parameter tuning
- Better balance between adaptation and stability
- Improved transient response
- Reduced control effort through optimal gain selection

## Usage Example

```python
from src.controllers.factory import create_controller
from src.config import load_config

# Load configuration
config = load_config('config.yaml')

# Create controller
controller = create_controller('adaptive_smc', config)

# Simulation loop
for t, state in simulation:
    u = controller.compute_control(state, reference, t)

    # Monitor adaptive gains
    current_gain = controller.get_adaptive_gain()
    print(f"Adaptive gain: {current_gain:.3f}")
```

## Theoretical Analysis

### Stability Proof
The Lyapunov function derivative is:

```{math}
\dot{V} = s\dot{s} + \frac{1}{\gamma}\tilde{K}\dot{\tilde{K}} \leq -\eta|s|
```

ensuring finite-time convergence to the sliding surface.

### Adaptation Convergence
Under persistent excitation conditions, the adaptive gain converges to the optimal value that minimizes the sliding surface error.

## References

1. Ioannou, P.A. & Sun, J. (1996). *Robust Adaptive Control*
2. Slotine, J.J. & Li, W. (1991). *Applied Nonlinear Control*
3. Narendra, K.S. & Annaswamy, A.M. (2005). *Stable Adaptive Systems*
4. Utkin, V. (1992). *Sliding Modes in Control and Optimization*

## Related Documentation

- [SMC Theory Complete](../theory/smc_theory_complete.md) - Mathematical foundations
- [Classical SMC](classical-smc.md) - Non-adaptive comparison
- [Hybrid Adaptive STA](hybrid-adaptive-smc.md) - Advanced adaptive approach
