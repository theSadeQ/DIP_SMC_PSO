# Theoretical Foundations

```{toctree}
:maxdepth: 2
:hidden:

notation_and_conventions
mathematical_references
system_dynamics_complete
smc_theory_complete
pso_optimization_complete
```

This section provides comprehensive theoretical coverage of the double-inverted pendulum control system, including mathematical foundations, control theory, and optimization algorithms.

## Contents

::::{grid} 2
:::{grid-item-card} **Notation & Conventions**
:link: notation_and_conventions
:link-type: doc

Mathematical notation, symbols, coordinate systems, and conventions used throughout the documentation.
:::

:::{grid-item-card} **Mathematical References**
:link: mathematical_references
:link-type: doc

Central index of all numbered equations with cross-references and derivation context.
:::

:::{grid-item-card} **System Dynamics**
:link: system_dynamics_complete
:link-type: doc

Complete derivation of double-inverted pendulum dynamics from first principles to state-space form.
:::

:::{grid-item-card} **SMC Theory**
:link: smc_theory_complete
:link-type: doc

Sliding mode control theory, Lyapunov stability analysis, and chattering mitigation strategies.
:::
::::

## Overview

The theoretical foundation of this work rests on three pillars:

1. **Nonlinear System Modeling**: First-principles derivation of the double-inverted pendulum dynamics
2. **Robust Control Theory**: Sliding mode control with finite-time convergence guarantees
3. **Optimization Theory**: Particle swarm optimization for automated parameter tuning

The mathematical framework ensures that all control designs have rigorous stability guarantees while maintaining practical implementability.

## Key Mathematical Results

The main theoretical contributions include:

- Complete nonlinear dynamics model with $n=3$ degrees of freedom
- Lyapunov-based stability proof for finite-time convergence in {eq}`eq:lyapunov_stability`
- Chattering-free control via super-twisting algorithms in {eq}`eq:supertwisting_law`
- Optimal gain selection through constrained PSO optimization in {eq}`eq:pso_objective`

For implementation details, see {doc}`../implementation/index`.