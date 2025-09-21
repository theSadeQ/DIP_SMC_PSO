# DIP_SMC_PSO Project Reference

This document provides Claude with essential project-specific information for the DIP_SMC_PSO project.

## Project Overview

**Double-Inverted Pendulum Sliding Mode Control with PSO Optimization**

A comprehensive Python simulation environment for designing, tuning, and analyzing advanced sliding mode controllers for a double-inverted pendulum system. Features automated gain tuning via Particle Swarm Optimization and both CLI and web interfaces.

## Key Technologies
- **Python 3.9+** with NumPy, SciPy, Matplotlib
- **Control Systems**: Classical SMC, Super-Twisting SMC, Adaptive SMC, Hybrid Adaptive STA-SMC
- **Optimization**: PSO via PySwarms, Optuna
- **Performance**: Numba acceleration for batch simulations
- **Testing**: pytest with comprehensive test suite
- **Configuration**: YAML-based with Pydantic validation
- **UI**: Streamlit web interface

## Project Structure

```
├── src/                          # Main source code
│   ├── controllers/              # Controller implementations
│   │   ├── classic_smc.py       # Classical sliding mode controller
│   │   ├── sta_smc.py           # Super-twisting sliding mode
│   │   ├── adaptive_smc.py      # Adaptive sliding mode
│   │   ├── hybrid_adaptive_sta_smc.py  # Hybrid adaptive controller
│   │   ├── swing_up_smc.py      # Swing-up controller
│   │   ├── mpc_controller.py    # Model predictive controller
│   │   └── factory.py           # Controller factory
│   ├── core/                    # Core simulation engine
│   │   ├── dynamics.py          # Simplified dynamics model
│   │   ├── dynamics_full.py     # Full nonlinear dynamics
│   │   ├── simulation_runner.py # Main simulation runner
│   │   ├── simulation_context.py # Unified simulation context
│   │   └── vector_sim.py        # Numba-accelerated batch simulator
│   ├── optimizer/               # PSO optimization
│   │   └── pso_optimizer.py     # PSO tuner implementation
│   ├── hil/                     # Hardware-in-the-loop
│   │   ├── plant_server.py      # HIL plant server
│   │   └── controller_client.py # HIL controller client
│   └── config.py                # Configuration management
├── tests/                       # Comprehensive test suite
│   ├── test_controllers/        # Controller unit tests
│   ├── test_core/               # Core simulation tests
│   ├── test_optimizer/          # PSO optimization tests
│   ├── test_benchmarks/         # Performance benchmarks
│   └── conftest.py              # Test fixtures and configuration
├── simulate.py                  # Main CLI application
├── streamlit_app.py            # Web interface
├── run_tests.py                # Test runner script
├── config.yaml                 # Main configuration file
└── requirements.txt            # Python dependencies
```

## Essential Commands

### Running Simulations
```bash
# Basic simulation with classical controller
python simulate.py --ctrl classical_smc --plot

# Use super-twisting controller with full dynamics
python simulate.py --ctrl sta_smc --plot

# Load pre-tuned gains and run simulation
python simulate.py --load tuned_gains.json --plot

# Print current configuration
python simulate.py --print-config
```

### PSO Optimization
```bash
# Optimize classical SMC gains
python simulate.py --ctrl classical_smc --run-pso --save gains_classical.json

# Optimize adaptive SMC with specific seed
python simulate.py --ctrl adaptive_smc --run-pso --seed 42 --save gains_adaptive.json

# Optimize hybrid adaptive controller
python simulate.py --ctrl hybrid_adaptive_sta_smc --run-pso --save gains_hybrid.json
```

### Hardware-in-the-Loop (HIL)
```bash
# Run HIL simulation (spawns server and client)
python simulate.py --run-hil --plot

# HIL with custom configuration
python simulate.py --config custom_config.yaml --run-hil
```

### Testing
```bash
# Run full test suite
python run_tests.py

# Run specific test module
python -m pytest tests/test_controllers/test_classical_smc.py -v

# Run performance benchmarks only
python -m pytest tests/test_benchmarks/ --benchmark-only

# Run tests with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Web Interface
```bash
# Launch Streamlit dashboard
streamlit run streamlit_app.py
```

## Controller Types

1. **classical_smc**: Classical sliding mode with boundary layer for chattering reduction
2. **sta_smc**: Super-twisting sliding mode for continuous control and finite-time convergence
3. **adaptive_smc**: Adaptive controller that adjusts gains online for uncertainty handling
4. **hybrid_adaptive_sta_smc**: Hybrid adaptive super-twisting with model-based equivalent control
5. **swing_up_smc**: Energy-based swing-up controller for large angle stabilization
6. **mpc_controller**: Model predictive controller (experimental)

## Configuration System

The project uses `config.yaml` for centralized configuration with Pydantic validation:

- **Physics parameters**: Masses, lengths, inertias, friction coefficients
- **Controller settings**: Gains, saturation limits, adaptation rates
- **PSO parameters**: Swarm size, bounds, iterations, cognitive/social coefficients
- **Simulation settings**: Duration, timestep, initial conditions
- **HIL configuration**: Network settings, sensor noise, latency simulation

## Key Development Patterns

### Adding New Controllers
1. Implement controller class in `src/controllers/`
2. Add factory method in `src/controllers/factory.py`
3. Add configuration section to `config.yaml`
4. Create unit tests in `tests/test_controllers/`

### Running Batch Simulations
Use `src/core/vector_sim.py` for Numba-accelerated parallel simulations:
```python
from src.core.vector_sim import run_batch_simulation
results = run_batch_simulation(controller, dynamics, initial_conditions, sim_params)
```

### Configuration Loading
```python
from src.config import load_config
config = load_config("config.yaml", allow_unknown=False)
```

## Testing Architecture

- **Unit tests**: Individual component testing
- **Integration tests**: End-to-end simulation workflows
- **Property-based tests**: Hypothesis-driven randomized testing
- **Performance benchmarks**: pytest-benchmark for regression detection
- **Scientific validation**: Lyapunov stability, chattering analysis

### Test Execution Patterns
```bash
# Fast unit tests only
pytest tests/test_controllers/ -k "not integration"

# Integration tests with full dynamics
pytest tests/ -k "full_dynamics"

# Performance regression testing
pytest --benchmark-only --benchmark-compare --benchmark-compare-fail=mean:5%
```

## Common Debugging

### Import Issues
- Ensure working directory is project root
- Check `PYTHONPATH` includes `src/`
- Verify all dependencies in `requirements.txt` are installed

### Simulation Failures
- Check configuration validation errors in logs
- Verify physics parameters are positive
- Ensure simulation duration ≥ timestep
- Monitor for numerical instabilities (`NumericalInstabilityError`)

### PSO Not Converging
- Increase `pso.iters` or `pso.n_particles`
- Adjust parameter bounds in `pso.bounds`
- Check cost function weights in `cost_function.weights`
- Verify controller constraints (saturation limits, adaptation rates)

## Performance Optimization

- Use `simulation.use_full_dynamics: false` for faster iterations
- Reduce `simulation.duration` for development
- Leverage `src/core/vector_sim.py` for batch processing
- Monitor benchmark results to catch performance regressions

## Development Workflow

1. **Configuration First**: Define controller parameters in `config.yaml`
2. **Test-Driven**: Write tests before implementation
3. **Validate Early**: Use configuration validation and type hints
4. **Benchmark**: Measure performance impact of changes
5. **Scientific Rigor**: Verify control-theoretic properties

This project emphasizes scientific reproducibility, performance, and robust engineering practices for control systems research and development.