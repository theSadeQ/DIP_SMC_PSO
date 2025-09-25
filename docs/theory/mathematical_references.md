# Mathematical References

This page serves as a central index of all numbered equations used throughout the DIP_SMC_PSO documentation, providing quick access to mathematical results and their context.

## System Dynamics Equations

### Fundamental Dynamics

```{math}
:label: eq:lagrangian_dynamics
\frac{d}{dt}\left(\frac{\partial L}{\partial \dot{q}_i}\right) - \frac{\partial L}{\partial q_i} = Q_i
```
**Context**: Lagrangian formulation of the double-inverted pendulum system.
**Location**: {doc}`system_dynamics_complete`

```{math}
:label: eq:mass_matrix
\mat{M}(\vec{q}) = \begin{bmatrix}
m_{total} & m_1 l_1 c_1 + m_2(l_1 c_1 + l_2 c_{12}) & m_2 l_2 c_{12} \\
m_1 l_1 c_1 + m_2(l_1 c_1 + l_2 c_{12}) & I_1 + m_1 l_1^2 + m_2 l_1^2 & m_2 l_1 l_2 c_2 \\
m_2 l_2 c_{12} & m_2 l_1 l_2 c_2 & I_2 + m_2 l_2^2
\end{bmatrix}
```
**Context**: Inertia matrix for the three-degree-of-freedom system.
**Location**: {doc}`system_dynamics_complete`

```{math}
:label: eq:coriolis_matrix_ref
\mat{C}(\vec{q}, \dot{\vec{q}}) = \begin{bmatrix}
0 & -m_1 l_1 s_1 \dot{\theta_1} - m_2(l_1 s_1 \dot{\theta_1} + l_2 s_{12}(\dot{\theta_1} + \dot{\theta_2})) & -m_2 l_2 s_{12}(\dot{\theta_1} + \dot{\theta_2}) \\
0 & 0 & -m_2 l_1 l_2 s_2 \dot{\theta_2} \\
0 & m_2 l_1 l_2 s_2 \dot{\theta_1} & 0
\end{bmatrix}
```
**Context**: Coriolis and centripetal forces matrix.
**Location**: {doc}`system_dynamics_complete`

### State-Space Representation

```{math}
:label: eq:state_space_form
\dot{\vec{x}} = \begin{bmatrix}
\dot{\vec{q}} \\
\mat{M}^{-1}(\vec{q})[\vec{B}u - \mat{C}(\vec{q}, \dot{\vec{q}})\dot{\vec{q}} - \vec{G}(\vec{q})]
\end{bmatrix}
```
**Context**: Complete state-space representation of the nonlinear system.
**Location**: {doc}`system_dynamics_complete`

## Sliding Mode Control Equations

### Sliding Surface Design

```{math}
:label: eq:sliding_surface_design
s(\vec{x}) = \mat{S}\vec{x} = \vec{c}^T \vec{e} + \dot{\vec{e}}
```
**Context**: Linear sliding surface with tracking error dynamics.
**Location**: {doc}`smc_theory_complete`

```{math}
:label: eq:reaching_condition_ref
s \dot{s} \leq -\eta |s|
```
**Context**: Reaching condition for finite-time convergence to sliding surface.
**Location**: {doc}`smc_theory_complete`

### Control Laws

```{math}
:label: eq:classical_smc
u = u_{eq} + u_{sw} = -(\mat{S}\mat{B})^{-1}\mat{S}f(\vec{x}) - \eta \frac{s}{|s| + \epsilon}
```
**Context**: Classical sliding mode control with boundary layer.
**Location**: {doc}`smc_theory_complete`

```{math}
:label: eq:supertwisting_law
\begin{aligned}
u &= u_1 + u_2 \\
\dot{u_1} &= -\alpha |s|^{1/2} \text{sign}(s) \\
u_2 &= -\beta \text{sign}(s)
\end{aligned}
```
**Context**: Super-twisting algorithm for chattering-free control.
**Location**: {doc}`smc_theory_complete`

```{math}
:label: eq:adaptive_law
\dot{\hat{\theta}} = \Gamma s \sigma(\vec{x})
```
**Context**: Adaptive parameter estimation for uncertain systems.
**Location**: {doc}`smc_theory_complete`

## Lyapunov Stability Analysis

```{math}
:label: eq:lyapunov_candidate_ref
V(\vec{x}) = \frac{1}{2}s^T s + \frac{1}{2}\tilde{\theta}^T \Gamma^{-1} \tilde{\theta}
```
**Context**: Lyapunov function candidate for adaptive sliding mode control.
**Location**: {doc}`smc_theory_complete`

```{math}
:label: eq:lyapunov_stability
\dot{V}(\vec{x}) = -\eta |s| \leq 0
```
**Context**: Lyapunov stability condition ensuring finite-time convergence.
**Location**: {doc}`smc_theory_complete`

```{math}
:label: eq:finite_time_convergence
t_{reach} \leq \frac{V(0)}{\eta}
```
**Context**: Upper bound on reaching time to sliding surface.
**Location**: {doc}`smc_theory_complete`

## PSO Optimization Equations

### Particle Dynamics

```{math}
:label: eq:pso_velocity_update_ref
\vec{v}_i^{(k+1)} = w\vec{v}_i^{(k)} + c_1 r_1(\vec{p}_i - \vec{x}_i^{(k)}) + c_2 r_2(\vec{g} - \vec{x}_i^{(k)})
```
**Context**: Velocity update equation for PSO particle motion.
**Location**: {doc}`pso_optimization_complete`

```{math}
:label: eq:pso_position_update_ref
\vec{x}_i^{(k+1)} = \vec{x}_i^{(k)} + \vec{v}_i^{(k+1)}
```
**Context**: Position update equation for PSO particles.
**Location**: {doc}`pso_optimization_complete`

### Cost Function

```{math}
:label: eq:pso_objective
J(\theta) = w_e \int_0^T \|\vec{e}(t)\|^2 dt + w_u \int_0^T u(t)^2 dt + w_s \int_0^T \dot{u}(t)^2 dt
```
**Context**: Multi-objective cost function for controller optimization.
**Location**: {doc}`pso_optimization_complete`

## Convergence and Stability Theorems

### Theorem 1: Finite-Time Convergence

**Statement**: Under the control law {eq}`eq:classical_smc` with reaching condition {eq}`eq:reaching_condition`, the system state reaches the sliding surface in finite time bounded by {eq}`eq:finite_time_convergence`.

**Proof**: See {doc}`smc_theory_complete`, Section 3.2.

### Theorem 2: Asymptotic Stability on Sliding Surface

**Statement**: Once on the sliding surface $s = 0$, the tracking error converges exponentially to zero with rate determined by the sliding surface parameters.

**Proof**: See {doc}`smc_theory_complete`, Section 3.3.

### Theorem 3: Adaptive Parameter Convergence

**Statement**: The adaptive law {eq}`eq:adaptive_law` ensures bounded parameter estimates and asymptotic tracking under persistence of excitation conditions.

**Proof**: See {doc}`smc_theory_complete`, Section 4.2.

## Implementation Constants

```{list-table} Typical Control Parameters
:header-rows: 1
:name: table:control_parameters

* - Parameter
  - Symbol
  - Typical Range
  - Units
* - Sliding surface gain
  - $c$
  - [1, 10]
  - 1/s
* - Switching gain
  - $\eta$
  - [0.1, 5]
  - N
* - Boundary layer
  - $\epsilon$
  - [0.01, 0.1]
  - -
* - Super-twisting $\alpha$
  - $\alpha$
  - [0.5, 2]
  - N/√s
* - Super-twisting $\beta$
  - $\beta$
  - [0.1, 1]
  - N
* - Adaptation gain
  - $\gamma$
  - [0.1, 10]
  - various
```

## Quick Reference

### Most Important Equations
- System dynamics: {eq}`eq:state_space_form`
- Sliding surface: {eq}`eq:sliding_surface_design`
- Control law: {eq}`eq:classical_smc`
- Stability condition: {eq}`eq:lyapunov_stability`
- PSO update: {eq}`eq:pso_velocity_update`

### Cross-References
- {doc}`notation_and_conventions` - Symbol definitions
- {doc}`system_dynamics_complete` - Detailed derivations
- {doc}`smc_theory_complete` - Control theory proofs
- {doc}`pso_optimization_complete` - Optimization algorithms