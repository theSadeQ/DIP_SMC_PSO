# Complete Sliding Mode Control Theory

This section provides comprehensive coverage of sliding mode control theory as applied to the double-inverted pendulum system, including mathematical foundations, stability analysis, and chattering mitigation strategies.

## Introduction to Sliding Mode Control

Sliding Mode Control (SMC) is a robust control methodology that provides finite-time convergence and inherent disturbance rejection capabilities {cite}`utkin1999sliding`. The fundamental principle is to constrain the system trajectory to evolve on a lower-dimensional sliding surface where desired dynamics are enforced.

### Fundamental Concepts

**Definition 1 (Sliding Surface)**: A sliding surface $\mathcal{S}$ is a subset of the state space defined by:

```{math}
:label: eq:sliding_surface_definition
\mathcal{S} = \{\vec{x} \in \mathbb{R}^n : s(\vec{x}, t) = 0\}
```

where $s(\vec{x}, t): \mathbb{R}^n \times \mathbb{R}^+ \rightarrow \mathbb{R}$ is the sliding function.

```{note}
**Implementation Note**: The sliding surface calculation is implemented in {py:obj}`src.controllers.classic_smc.ClassicalSMC.compute_sliding_surface` using the equations defined above.
```

**Definition 2 (Sliding Mode)**: The system is said to be in sliding mode when:
1. The trajectory reaches the sliding surface: $s(\vec{x}, t) = 0$
2. The trajectory remains on the surface: $\dot{s}(\vec{x}, t) = 0$

## Sliding Surface Design for DIP System

### Error Dynamics

For the double-inverted pendulum system with reference trajectory $\vec{x}_r(t)$, we define the tracking error:

```{math}
:label: eq:tracking_error
\vec{e}(t) = \vec{x}(t) - \vec{x}_r(t) = \begin{bmatrix} e_x \\ e_{\theta_1} \\ e_{\theta_2} \\ \dot{e}_x \\ \dot{e}_{\theta_1} \\ \dot{e}_{\theta_2} \end{bmatrix}
```

### Linear Sliding Surface

The sliding surface is designed using a linear combination of position and velocity errors:

```{math}
:label: eq:linear_sliding_surface
s(\vec{x}, t) = \mat{S}\vec{e}(t) = \vec{c}^T\vec{e}_p + \dot{\vec{e}}_p
```

where:
- $\vec{e}_p = [e_x, e_{\theta_1}, e_{\theta_2}]^T$ - position errors
- $\dot{\vec{e}}_p = [\dot{e}_x, \dot{e}_{\theta_1}, \dot{e}_{\theta_2}]^T$ - velocity errors
- $\vec{c} = [c_x, c_{\theta_1}, c_{\theta_2}]^T$ - sliding surface parameters

The sliding surface matrix is defined in equation {eq}`eq:linear_sliding_surface` and implemented in {py:obj}`src.controllers.classic_smc.ClassicalSMC.sliding_surface_matrix`:

```{math}
:label: eq:sliding_surface_matrix
\mat{S} = \begin{bmatrix} c_x & 0 & 0 & 1 & 0 & 0 \\ 0 & c_{\theta_1} & 0 & 0 & 1 & 0 \\ 0 & 0 & c_{\theta_2} & 0 & 0 & 1 \end{bmatrix}
```

### Surface Dynamics Analysis

When the system is constrained to the sliding surface $s = 0$, the reduced-order dynamics become:

```{math}
:label: eq:sliding_surface_dynamics
\dot{\vec{e}}_p + \mat{C}\vec{e}_p = 0
```

where $\mat{C} = \text{diag}(c_x, c_{\theta_1}, c_{\theta_2})$.

**Theorem 1 (Surface Stability)**: If all sliding surface parameters $c_i > 0$, then the sliding surface dynamics are exponentially stable with convergence rates determined by $c_i$.

*Proof*: The characteristic polynomial of each error component is $s + c_i = 0$, yielding eigenvalues $\lambda_i = -c_i < 0$ for $c_i > 0$. □

## Classical Sliding Mode Control

### Control Law Structure

The classical SMC law consists of two components:

```{math}
:label: eq:classical_smc_structure
u(t) = u_{eq}(t) + u_{sw}(t)
```

where:
- $u_{eq}(t)$ - equivalent control (continuous component)
- $u_{sw}(t)$ - switching control (discontinuous component)

### Equivalent Control Design

The equivalent control ensures $\dot{s} = 0$ in the absence of disturbances and model uncertainties. From the system dynamics {eq}`eq:nonlinear_state_space`:

```{math}
:label: eq:sliding_surface_derivative
\dot{s} = \mat{S}\dot{\vec{e}} = \mat{S}[\vec{f}(\vec{x}) + \vec{g}(\vec{x})u - \dot{\vec{x}}_r]
```

Setting $\dot{s} = 0$ and solving for $u_{eq}$:

```{math}
:label: eq:equivalent_control
u_{eq} = (\mat{S}\vec{g}(\vec{x}))^{-1}[\dot{\vec{x}}_r - \mat{S}\vec{f}(\vec{x})]
```

**Assumption 1**: The matrix $\mat{S}\vec{g}(\vec{x})$ is invertible for all $\vec{x}$ in the domain of interest.

### Switching Control Design

The switching control provides robustness against uncertainties and disturbances:

```{math}
:label: eq:switching_control
u_{sw} = -\eta \frac{s}{|s| + \epsilon}
```

where:
- $\eta > 0$ - switching gain
- $\epsilon > 0$ - boundary layer thickness (chattering reduction)

### Reaching Condition

**Definition 3 (Reaching Condition)**: The system trajectory reaches the sliding surface in finite time if:

```{math}
:label: eq:reaching_condition
s \cdot \dot{s} \leq -\alpha |s|
```

for some $\alpha > 0$.

**Theorem 2 (Finite-Time Reaching)**: Under the reaching condition {eq}`eq:reaching_condition`, the system reaches the sliding surface in finite time bounded by:

```{math}
:label: eq:reaching_time_bound
t_{reach} \leq \frac{|s(0)|}{\alpha}
```

*Proof*: From the reaching condition:
$$\frac{d}{dt}(|s|) = \text{sign}(s) \cdot \dot{s} \leq -\alpha$$

Integrating from $0$ to $t_{reach}$:
$$|s(t_{reach})| - |s(0)| \leq -\alpha t_{reach}$$

Setting $|s(t_{reach})| = 0$ yields the bound. □

## Lyapunov Stability Analysis

### Lyapunov Function Candidate

For stability analysis, we consider the Lyapunov function:

```{math}
:label: eq:lyapunov_candidate
V(s) = \frac{1}{2}s^2
```

### Stability Proof

**Theorem 3 (Classical SMC Stability)**: The classical SMC law {eq}`eq:classical_smc_structure` with switching gain $\eta > \rho$ (where $\rho$ is the uncertainty bound) ensures global finite-time convergence to the sliding surface.

*Proof*: Consider the Lyapunov function derivative:

```{math}
:label: eq:lyapunov_derivative
\dot{V} = s \cdot \dot{s} = s[\mat{S}\vec{f}(\vec{x}) + \mat{S}\vec{g}(\vec{x})u - \mat{S}\dot{\vec{x}}_r]
```

Substituting the control law:
```{math}
:label: eq:lyapunov_with_control
\dot{V} = s[\mat{S}\vec{f}(\vec{x}) + \mat{S}\vec{g}(\vec{x})(u_{eq} + u_{sw}) - \mat{S}\dot{\vec{x}}_r]
```

With perfect equivalent control, the first and third terms cancel. The switching term yields:
```{math}
:label: eq:lyapunov_switching_term
\dot{V} = s \cdot \mat{S}\vec{g}(\vec{x}) \cdot (-\eta \frac{s}{|s| + \epsilon}) = -\eta \frac{s^2}{|s| + \epsilon} \leq -\eta \frac{|s|}{1 + \epsilon} < 0
```

This establishes finite-time convergence. □

## Super-Twisting Algorithm

### Motivation for Higher-Order SMC

Classical SMC suffers from chattering due to the discontinuous switching control. The super-twisting algorithm {cite}`levant2003higher` provides continuous control while maintaining finite-time convergence.

### Super-Twisting Control Law

The super-twisting algorithm is a second-order sliding mode controller:

```{math}
:label: eq:supertwisting_control
\begin{aligned}
u &= u_1 + u_2 \\
\dot{u_1} &= -\alpha |s|^{1/2} \text{sign}(s) \\
u_2 &= -\beta \text{sign}(s)
\end{aligned}
```

where $\alpha > 0$ and $\beta > 0$ are tuning parameters.

### Lyapunov Analysis for Super-Twisting

**Theorem 4 (Super-Twisting Stability)**: The super-twisting algorithm ensures finite-time convergence to the second-order sliding set $\{s = 0, \dot{s} = 0\}$ if the parameters satisfy:

```{math}
:label: eq:supertwisting_conditions
\alpha > \frac{2\sqrt{2\rho}}{\sqrt{\gamma}}, \quad \beta > \frac{\rho}{\gamma}
```

where $\rho$ is the uncertainty bound and $\gamma$ is the lower bound on the control effectiveness.

*Proof*: The proof uses a strict Lyapunov function from {cite}`moreno2012strict`:

```{math}
:label: eq:supertwisting_lyapunov
V = \zeta^T \mat{P} \zeta
```

where $\zeta = [|s|^{1/2}\text{sign}(s), \dot{s}]^T$ and $\mat{P}$ is a positive definite matrix. The detailed proof shows $\dot{V} < 0$ outside the origin. □

## Adaptive Sliding Mode Control

### Parameter Uncertainty Model

Consider the DIP system with parametric uncertainties:

```{math}
:label: eq:uncertain_system
\mat{M}(\vec{q}, \vec{\theta})\ddot{\vec{q}} + \mat{C}(\vec{q}, \dot{\vec{q}}, \vec{\theta})\dot{\vec{q}} + \mat{G}(\vec{q}, \vec{\theta}) = \mat{B}u + \vec{d}(t)
```

where:
- $\vec{\theta}$ - unknown parameter vector
- $\vec{d}(t)$ - external disturbances

### Linear Parameterization

The system can be linearly parameterized as:

```{math}
:label: eq:linear_parameterization
\mat{M}(\vec{q})\ddot{\vec{q}} + \mat{C}(\vec{q}, \dot{\vec{q}})\dot{\vec{q}} + \mat{G}(\vec{q}) = \mat{Y}(\vec{q}, \dot{\vec{q}}, \ddot{\vec{q}})\vec{\theta}
```

where $\mat{Y}(\vec{q}, \dot{\vec{q}}, \ddot{\vec{q}})$ is the regression matrix.

### Adaptive Control Law

The adaptive SMC combines equivalent control with parameter adaptation:

```{math}
:label: eq:adaptive_smc_law
\begin{aligned}
u &= u_{eq} + u_{sw} \\
u_{eq} &= (\mat{S}\mat{B})^{-1}[\mat{S}\mat{Y}\hat{\vec{\theta}} - \mat{S}\dot{\vec{x}}_r] \\
u_{sw} &= -\eta \text{sign}(s) \\
\dot{\hat{\vec{\theta}}} &= -\Gamma \mat{Y}^T \mat{S}^T s
\end{aligned}
```

where:
- $\hat{\vec{\theta}}$ - parameter estimates
- $\Gamma > 0$ - adaptation gain matrix

### Adaptive Stability Analysis

**Theorem 5 (Adaptive SMC Stability)**: The adaptive control law {eq}`eq:adaptive_smc_law` ensures:
1. Global boundedness of all signals
2. Convergence of the sliding variable: $\lim_{t \rightarrow \infty} s(t) = 0$
3. Parameter convergence under persistence of excitation

*Proof*: Consider the composite Lyapunov function:

```{math}
:label: eq:adaptive_lyapunov
V = \frac{1}{2}s^2 + \frac{1}{2}\tilde{\vec{\theta}}^T \Gamma^{-1} \tilde{\vec{\theta}}
```

where $\tilde{\vec{\theta}} = \vec{\theta} - \hat{\vec{\theta}}$ is the parameter error.

The derivative becomes:
```{math}
:label: eq:adaptive_lyapunov_derivative
\dot{V} = s\dot{s} + \tilde{\vec{\theta}}^T \Gamma^{-1} \dot{\tilde{\vec{\theta}}} = -\eta |s| \leq 0
```

This establishes Lyapunov stability and convergence of $s(t)$ to zero. □

## Chattering Analysis and Mitigation

### Chattering Phenomenon

Chattering occurs due to:
1. **Finite switching frequency** of digital implementations
2. **Unmodeled dynamics** (actuator dynamics, sensor delays)
3. **Measurement noise** affecting the sliding variable

### Quantitative Chattering Measure

Define the chattering index as:

```{math}
:label: eq:chattering_index
\mathcal{I}_{chat} = \frac{1}{T} \int_0^T |\dot{u}(t)| dt
```

### Boundary Layer Method

Replace the discontinuous sign function with a continuous approximation:

```{math}
:label: eq:boundary_layer
\text{sign}(s) \rightarrow \text{sat}(s/\epsilon) = \begin{cases}
s/\epsilon & \text{if } |s| \leq \epsilon \\
\text{sign}(s) & \text{if } |s| > \epsilon
\end{cases}
```

**Theorem 6 (Boundary Layer Convergence)**: With the boundary layer method, the tracking error is ultimately bounded by:

```{math}
:label: eq:boundary_layer_bound
\limsup_{t \rightarrow \infty} |\vec{e}(t)| \leq \frac{\epsilon}{\lambda_{\min}(\mat{C})}
```

where $\lambda_{\min}(\mat{C})$ is the minimum eigenvalue of the sliding surface parameter matrix.

## Implementation Considerations

### Digital Implementation

For discrete-time implementation with sampling period $T_s$:

```{math}
:label: eq:discrete_smc
u[k] = u_{eq}[k] + u_{sw}[k]
```

where:
```{math}
:label: eq:discrete_components
\begin{aligned}
u_{eq}[k] &= (\mat{S}\mat{B})^{-1}[\dot{\vec{x}}_r[k] - \mat{S}\vec{f}(\vec{x}[k])] \\
u_{sw}[k] &= -\eta \text{sat}(s[k]/\epsilon)
\end{aligned}
```

### Parameter Tuning Guidelines

1. **Sliding surface parameters** $c_i$:
   - Start with $c_i = 2\zeta_i\omega_{ni}$ where $\zeta_i$ and $\omega_{ni}$ are desired damping and natural frequency
   - Increase for faster convergence, decrease for smoother response

2. **Switching gain** $\eta$:
   - Must exceed uncertainty bound: $\eta > \rho$
   - Larger values improve robustness but increase chattering

3. **Boundary layer** $\epsilon$:
   - Trade-off between chattering reduction and tracking accuracy
   - Typical range: $\epsilon \in [0.01, 0.1]$

### Computational Complexity

The SMC algorithms have the following computational requirements:

```{list-table} Computational Complexity
:header-rows: 1
:name: table:computational_complexity

* - Algorithm
  - Matrix Operations
  - Trigonometric Functions
  - Real-time Feasibility
* - Classical SMC
  - 1 matrix inversion (3×3)
  - 6 sin/cos evaluations
  - Excellent
* - Super-Twisting
  - 1 matrix inversion (3×3)
  - 6 sin/cos evaluations
  - Excellent
* - Adaptive SMC
  - 1 matrix inversion (3×3)
  - 6 sin/cos evaluations
  - Good
* - Hybrid STA
  - 2 matrix inversions (3×3)
  - 6 sin/cos evaluations
  - Good
```

## Performance Analysis

### Convergence Properties

**Classical SMC**:
- Finite-time convergence to sliding surface
- Exponential convergence on sliding surface
- Chattering in control signal

**Super-Twisting**:
- Finite-time convergence to second-order sliding set
- Continuous control signal
- Reduced chattering

**Adaptive SMC**:
- Asymptotic convergence with parameter adaptation
- Handles parametric uncertainties
- Requires persistence of excitation for parameter convergence

### Robustness Characteristics

All SMC variants provide inherent robustness to:
- **Matched disturbances** (entering through control channel)
- **Parametric uncertainties** (with appropriate adaptation)
- **Unmodeled dynamics** (within sliding mode bandwidth)

### Design Trade-offs

```{mermaid}
flowchart TD
    Performance[Performance Requirements]
    Performance --> FastResponse[Fast Response]
    Performance --> LowChattering[Low Chattering]
    Performance --> Robustness[High Robustness]

    FastResponse --> ClassicalSMC[Classical SMC<br/>High gains]
    LowChattering --> SuperTwisting[Super-Twisting SMC<br/>Continuous control]
    Robustness --> AdaptiveSMC[Adaptive SMC<br/>Parameter estimation]

    ClassicalSMC --> TradeOff[Design Trade-offs]
    SuperTwisting --> TradeOff
    AdaptiveSMC --> TradeOff

    TradeOff --> OptimalDesign[Optimal Design<br/>Multi-objective optimization]
```

## Conclusions

This comprehensive analysis of sliding mode control theory provides the mathematical foundation for the controller implementations in the DIP_SMC_PSO project. The theoretical results guarantee:

1. **Finite-time convergence** for classical and super-twisting algorithms
2. **Robust performance** under uncertainties and disturbances
3. **Adaptive capabilities** for unknown system parameters
4. **Practical implementability** with bounded control signals

The next step is to apply these theoretical results to automated parameter optimization using PSO techniques, covered in {doc}`pso_optimization_complete`.

## References

The theoretical development follows {cite}`utkin1999sliding`, {cite}`edwards1998sliding`, and {cite}`shtessel2014sliding`, with super-twisting analysis from {cite}`levant2003higher` and {cite}`moreno2012strict`. Adaptive extensions are based on {cite}`slotine1991applied` and {cite}`krstic1995nonlinear`.