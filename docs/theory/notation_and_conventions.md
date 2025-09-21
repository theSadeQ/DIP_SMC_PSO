# Notation and Conventions

This page establishes the mathematical notation and conventions used throughout the DIP_SMC_PSO documentation.

## General Notation

### Scalar Variables
- $t \in \mathbb{R}$ - Time variable
- $u \in \mathbb{R}$ - Control input (force applied to cart)
- $m_0, m_1, m_2$ - Masses of cart and pendulums
- $l_1, l_2$ - Lengths of pendulum links
- $g$ - Gravitational acceleration

### Vector Variables
- $\vec{q} = [x, \theta_1, \theta_2]^T \in \mathbb{R}^3$ - Generalized coordinates
- $\vec{x} = [\vec{q}^T, \dot{\vec{q}}^T]^T \in \mathbb{R}^6$ - State vector
- $\vec{e} \in \mathbb{R}^6$ - Tracking error vector
- $\vec{s} \in \mathbb{R}^6$ - Sliding surface vector

### Matrix Variables
- $\mat{M}(\vec{q}) \in \mathbb{R}^{3 \times 3}$ - Inertia matrix
- $\mat{C}(\vec{q}, \dot{\vec{q}}) \in \mathbb{R}^{3 \times 3}$ - Coriolis matrix
- $\vec{G}(\vec{q}) \in \mathbb{R}^3$ - Gravitational forces vector
- $\mat{B} \in \mathbb{R}^{3 \times 1}$ - Input matrix
- $\mat{S} \in \mathbb{R}^{3 \times 6}$ - Sliding surface design matrix

## Mathematical Operators

### Norms and Inner Products
- $\|\vec{x}\|$ - Euclidean norm of vector $\vec{x}$
- $\|\mat{A}\|_F$ - Frobenius norm of matrix $\mat{A}$
- $\langle \vec{x}, \vec{y} \rangle$ - Inner product of vectors $\vec{x}$ and $\vec{y}$

### Derivatives
- $\dot{(\cdot)} = \frac{d(\cdot)}{dt}$ - Time derivative
- $\ddot{(\cdot)} = \frac{d^2(\cdot)}{dt^2}$ - Second time derivative
- $\frac{\partial(\cdot)}{\partial x}$ - Partial derivative with respect to $x$

### Special Functions
- $\text{sign}(\cdot)$ - Sign function
- $\text{sat}(\cdot)$ - Saturation function
- $\text{tanh}(\cdot)$ - Hyperbolic tangent function

## Coordinate Systems

### Cart-Pendulum System
```{figure} ../visual/coordinate_system.png
:name: fig:coordinate_system
:width: 600px

Coordinate system for the double-inverted pendulum system.
```

- **Origin**: Fixed at the initial cart position
- **$x$-axis**: Horizontal, positive to the right
- **$\theta_1$**: Angle of first pendulum from vertical (positive counterclockwise)
- **$\theta_2$**: Angle of second pendulum from vertical (positive counterclockwise)

### State Space Representation
The complete state vector is defined as:

```{math}
:label: eq:state_definition
\vec{x} = \begin{bmatrix}
x \\
\theta_1 \\
\theta_2 \\
\dot{x} \\
\dot{\theta_1} \\
\dot{\theta_2}
\end{bmatrix} \in \mathbb{R}^6
```

## Control Theory Notation

### Sliding Mode Control
- $s(\vec{x}, t)$ - Sliding surface
- $u_{eq}$ - Equivalent control
- $u_{sw}$ - Switching control
- $\eta$ - Switching gain
- $\phi$ - Boundary layer thickness

### Lyapunov Analysis
- $V(\vec{x})$ - Lyapunov function candidate
- $\dot{V}(\vec{x})$ - Time derivative of Lyapunov function
- $\alpha, \beta$ - Class $\mathcal{K}$ function parameters

### Adaptive Control
- $\hat{\theta}$ - Parameter estimate
- $\tilde{\theta} = \theta - \hat{\theta}$ - Parameter estimation error
- $\Gamma$ - Adaptation gain matrix

## Optimization Notation

### PSO Parameters
- $N$ - Number of particles in swarm
- $\vec{x}_i^{(k)}$ - Position of particle $i$ at iteration $k$
- $\vec{v}_i^{(k)}$ - Velocity of particle $i$ at iteration $k$
- $\vec{p}_i$ - Personal best position of particle $i$
- $\vec{g}$ - Global best position of swarm
- $w$ - Inertia weight
- $c_1, c_2$ - Acceleration coefficients

### Cost Function
- $J(\theta)$ - Objective function to minimize
- $w_e, w_u, w_s$ - Weighting factors for error, control effort, and smoothness

## Physical Constants

```{list-table} System Parameters
:header-rows: 1
:name: table:system_parameters

* - Parameter
  - Symbol
  - Typical Value
  - Units
* - Cart mass
  - $m_0$
  - 1.0
  - kg
* - Pendulum 1 mass
  - $m_1$
  - 0.1
  - kg
* - Pendulum 2 mass
  - $m_2$
  - 0.1
  - kg
* - Pendulum 1 length
  - $l_1$
  - 0.5
  - m
* - Pendulum 2 length
  - $l_2$
  - 0.5
  - m
* - Gravitational acceleration
  - $g$
  - 9.81
  - m/s²
* - Cart friction coefficient
  - $b_0$
  - 0.1
  - N⋅s/m
* - Pendulum 1 friction
  - $b_1$
  - 0.01
  - N⋅m⋅s/rad
* - Pendulum 2 friction
  - $b_2$
  - 0.01
  - N⋅m⋅s/rad
```

## Sign Conventions

1. **Angles**: Measured counterclockwise from the upward vertical
2. **Forces**: Positive force moves cart to the right
3. **Velocities**: Consistent with position derivatives
4. **Control Input**: Positive input produces rightward acceleration

## References

For additional mathematical background, see:
- {doc}`mathematical_references` - Complete equation index
- {doc}`system_dynamics_complete` - Detailed dynamics derivation
- {doc}`smc_theory_complete` - Control theory foundations