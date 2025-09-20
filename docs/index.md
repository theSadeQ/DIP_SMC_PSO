# DIP_SMC_PSO Documentation

**Double-Inverted Pendulum Sliding Mode Control with PSO Optimization**

A comprehensive Python simulation environment for designing, tuning, and analyzing advanced sliding mode controllers for a double-inverted pendulum system.

## Overview

This project implements multiple sliding mode control strategies for stabilizing a double-inverted pendulum system:

- **Classical Sliding Mode Control (SMC)** with boundary layer {cite}`slotine1991applied`
- **Super-Twisting SMC** for chattering-free control {cite}`moreno2012strict`
- **Adaptive SMC** for uncertainty handling
- **Hybrid Adaptive STA-SMC** combining model-based and robust control {cite}`levant2003higher`

The controllers are automatically tuned using **Particle Swarm Optimization (PSO)** {cite}`kennedy1995particle` and validated through comprehensive simulation and analysis.

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

installation
theory_overview
controllers/index
optimization
examples/index
api/index
```

## Mathematical Notation

The system dynamics are described by:

$$\ddot{q} = f(q, \dot{q}) + B(q)u$$

where $q \in \mathbb{R}^4$ represents the system states (cart position and pendulum angles), $u \in \mathbb{R}$ is the control input, and the control objective is to stabilize the system around the unstable equilibrium.

## Bibliography

```{bibliography}
:filter: docname in docnames
:style: author_year
```

## Project Links

- 📚 [Theory Overview](theory_overview.md)
- 🎮 [Controller Documentation](controllers/index.md)
- 📖 [API Reference](api/index.md)
- 🔬 [Examples](examples/index.md)