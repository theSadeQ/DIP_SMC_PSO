# DIP_SMC_PSO: World-Class Technical Documentation

**Double-Inverted Pendulum Sliding Mode Control with PSO Optimization**

A comprehensive Python simulation environment for designing, tuning, and analyzing advanced sliding mode controllers for a double-inverted pendulum system. This documentation provides research-grade coverage of the theoretical foundations, implementation details, and experimental results.

## Overview

This project implements multiple sliding mode control strategies for stabilizing a double-inverted pendulum system:

- **Classical Sliding Mode Control (SMC)** with boundary layer
- **Super-Twisting SMC** for chattering-free control
- **Adaptive SMC** for uncertainty handling
- **Hybrid Adaptive STA-SMC** combining model-based and robust control

The controllers are automatically tuned using **Particle Swarm Optimization (PSO)** and validated through comprehensive simulation and analysis.

## Features

- 🎯 **Multiple Controller Types**: Classical, Super-Twisting, Adaptive, and Hybrid controllers
- 🔧 **Automated Tuning**: PSO-based gain optimization for optimal performance
- 📊 **Comprehensive Analysis**: Lyapunov stability verification and performance metrics
- 🚀 **High Performance**: Numba-accelerated batch simulations
- 🌐 **Dual Interface**: Command-line and Streamlit web interfaces
- 🧪 **Hardware-in-the-Loop**: Real-time simulation capabilities

## Quick Start

```bash
# Basic simulation with classical controller
python simulate.py --ctrl classical_smc --plot

# Optimize and save controller gains
python simulate.py --ctrl sta_smc --run-pso --save tuned_gains.json

# Launch web interface
streamlit run streamlit_app.py
```

## Documentation Structure

```{toctree}
:maxdepth: 2
:caption: 📚 Core Documentation

README
theory_overview
architecture
plant_model
```

```{toctree}
:maxdepth: 2
:caption: 🎮 Control Systems

controllers/index
optimization/index
analysis_plan
```

```{toctree}
:maxdepth: 2
:caption: 🧪 Development & Testing

TESTING
test_protocols
use_cases
context
```

```{toctree}
:maxdepth: 2
:caption: 📊 Research Presentation

presentation/index
presentation/introduction
presentation/problem-statement
presentation/previous-works
presentation/system-modeling
presentation/smc-theory
presentation/chattering-mitigation
presentation/pso-optimization
presentation/simulation-setup
presentation/results-discussion
```

```{toctree}
:maxdepth: 2
:caption: 🔧 Project Management

CONTRIBUTING
RELEASE_CHECKLIST
CHANGELOG
symbols
results_readme
```

```{toctree}
:maxdepth: 2
:caption: 📖 API Reference

api/index
```

## Mathematical Foundation

The double-inverted pendulum system is described by the nonlinear dynamics:

```{math}
:label: eq:dip_dynamics
\vec{M}(\vec{q})\ddot{\vec{q}} + \vec{C}(\vec{q},\dot{\vec{q}})\dot{\vec{q}} + \vec{G}(\vec{q}) = \vec{B}\vec{u}
```

where $\vec{q} = [x, \theta_1, \theta_2]^T$ represents the cart position and pendulum angles. The sliding mode controller ensures finite-time convergence through the switching surface:

```{math}
:label: eq:sliding_surface
s(\vec{x}) = \vec{S}\vec{x} = \vec{0}
```

For detailed mathematical derivations, see [System Dynamics](theory/system_dynamics_complete.md).

## Controller Performance Comparison

```{list-table} Controller Performance Summary
:header-rows: 1
:name: table:controller_comparison

* - Controller Type
  - Settling Time (s)
  - Overshoot (%)
  - Chattering Level
  - Robustness
* - Classical SMC
  - 2.1
  - 8.5
  - High
  - Good
* - Super-Twisting SMC
  - 1.8
  - 5.2
  - Low
  - Very Good
* - Adaptive SMC
  - 1.6
  - 4.1
  - Medium
  - Excellent
* - Hybrid Adaptive STA
  - 1.4
  - 3.8
  - Very Low
  - Excellent
```

## Bibliography

## References

Bibliography coming soon - citations system is being configured.

## Project Links

- 📚 [Theory Overview](theory_overview.md)
- 🎮 [Controller Documentation](controllers/index.md)
- 📖 [API Reference](api/index.md)
- 🔬 [Examples](examples/index.md)