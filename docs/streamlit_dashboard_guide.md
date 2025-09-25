# Streamlit Dashboard User Guide

## Overview

The DIP_SMC_PSO project includes an interactive web dashboard built with Streamlit that provides a user-friendly interface for exploring sliding mode control systems. The dashboard allows you to configure controllers, run simulations, optimize parameters with PSO, and visualize results in real-time.

## Quick Start

### Installation Requirements

Ensure Streamlit is installed:
```bash
pip install streamlit
```

### Launching the Dashboard

```bash
# From project root directory
streamlit run streamlit_app.py
```

The dashboard will open in your default web browser at `http://localhost:8501`.

## Dashboard Overview

### Main Interface

The dashboard is organized into two main areas:

- **Sidebar (Left)**: Control panels for configuration
- **Main Panel (Right)**: Simulation results, plots, and metrics

### Language Support

The dashboard supports multiple languages:
- **English**: Default interface language
- **فارسی (Farsi)**: Persian language support

Use the language selector in the top-left sidebar to switch between languages.

## Configuration Panels

### 1. Dynamics Model Selection

**Purpose**: Choose between simplified and full nonlinear dynamics models.

**Options**:
- ☐ **Simplified Dynamics** (Default): Faster computation, suitable for controller design
- ☑ **Use Full Nonlinear Dynamics**: Complete model with all nonlinearities, more accurate

**When to Use**:
- **Simplified**: Initial controller tuning, parameter exploration, educational purposes
- **Full**: Final validation, accurate performance assessment, research results

### 2. Controller Selection

**Available Controllers**:
- `classical_smc`: Classical sliding mode with boundary layer
- `sta_smc`: Super-twisting sliding mode algorithm
- `adaptive_smc`: Adaptive sliding mode with online gain adjustment
- `hybrid_adaptive_sta_smc`: Hybrid adaptive super-twisting controller
- `swing_up_smc`: Energy-based swing-up controller
- `mpc_controller`: Model predictive controller (experimental)

**Controller Information**:
Each controller displays its current parameter values below the selection dropdown.

### 3. PSO Optimization

**Purpose**: Automatically tune controller parameters for optimal performance.

**Usage**:
1. Select desired controller type
2. Click **"Run PSO"** button
3. Wait for optimization to complete (typically 30-60 seconds)
4. Optimized parameters are automatically applied

**PSO Configuration**:
The optimization uses settings from `config.yaml`:
```yaml
pso:
  n_particles: 30
  iters: 100
  bounds: [...]  # Controller-specific parameter bounds
```

**Results Display**:
- **Success Message**: Confirms optimization completion
- **Best Cost**: Final optimization objective value
- **Updated Parameters**: New controller gains displayed

### 4. Simulation Settings

**Duration Control**:
- **Range**: 1.0 - 60.0 seconds
- **Default**: From `config.yaml` (typically 10s)
- **Step Size**: 0.5s increments

**Time Step (dt)**:
- **Range**: 0.001 - 0.1 seconds
- **Default**: 0.001s (1000 Hz)
- **Considerations**:
  - Smaller dt: More accurate but slower
  - Larger dt: Faster but may miss dynamics

**Initial State Configuration**:
- **Format**: Comma-separated values
- **States**: `[x, θ₁, θ₂, ẋ, θ̇₁, θ̇₂]`
- **Units**: Position (m), Angles (rad), Velocities (m/s, rad/s)
- **Example**: `0.1, 0.05, -0.02, 0, 0, 0`

**Common Initial Conditions**:
```
Equilibrium:     0, 0, 0, 0, 0, 0
Small Displacement: 0.1, 0.05, -0.05, 0, 0, 0
Large Disturbance:  0.5, 0.2, -0.3, 0, 0, 0
```

### 5. Disturbance Injection

**Purpose**: Test controller robustness against external forces.

**Configuration**:
- **Enable**: Check "Add Disturbance" checkbox
- **Magnitude**: 0.0 - 10.0 N force applied to cart
- **Start Time**: When disturbance begins (0 to sim_duration-0.1)
- **Duration**: How long disturbance is applied

**Disturbance Types**:
The dashboard currently supports step disturbances. The force profile is:
```
d(t) = { 0           if t < start_time
       { magnitude   if start_time ≤ t < start_time + duration
       { 0           if t ≥ start_time + duration
```

**Testing Scenarios**:
- **Mild Test**: 1-2N for 0.5s
- **Moderate Test**: 3-5N for 1.0s
- **Stress Test**: 8-10N for 2.0s

## Main Panel Features

### Simulation Execution

**Run Button**: Located prominently in the main panel
- Executes simulation with current settings
- Shows progress spinner during computation
- Automatically updates results when complete

**Caching**: Results are cached for identical parameter sets to improve performance.

### Visualization

**State Trajectory Plots**:
- **Position (x)**: Cart position over time
- **Angles (θ₁, θ₂)**: Both pendulum angles
- **Velocities**: All velocity components
- **Control Input (u)**: Applied force over time

**Plot Features**:
- Interactive zooming and panning
- Hover tooltips with exact values
- Grid lines for easier reading
- Automatic scaling

**Animation**:
- Real-time pendulum animation showing system motion
- Synchronized with state plots
- Cart and pendulum visualization

### Performance Metrics

**Automatically Computed**:
- **Settling Time**: Time to reach and stay within tolerance
- **RMS Control Effort**: Root-mean-square control force
- **Peak Deviations**: Maximum position and angle excursions
- **Control Authority**: Maximum control force used

**Metric Tolerances**:
- Position: ±2 cm
- Angles: ±3° (±0.05 rad)

**Interpretation**:
- **Lower settling time**: Faster response
- **Lower RMS control**: More energy efficient
- **Lower peak deviations**: Better tracking
- **Lower max control**: Less demanding on actuators

## Advanced Features

### Configuration Export/Import

**Export Current Settings**:
```python
# Settings are saved automatically in browser session
# Manual export via JSON download (if implemented)
```

**Reproducible Results**:
The dashboard uses deterministic seeding for PSO optimization, ensuring reproducible results when the same parameters are used.

### Custom Parameter Tuning

**Manual Parameter Adjustment**:
While the dashboard doesn't currently support manual gain sliders, you can:
1. Modify `config.yaml` for custom default values
2. Use PSO optimization as starting point
3. Run CLI with custom parameters: `python simulate.py --ctrl custom_gains.json`

### Performance Optimization

**For Faster Simulations**:
- Use simplified dynamics model
- Reduce simulation duration
- Increase time step (with caution)
- Disable animations during parameter sweeps

**For More Accuracy**:
- Use full nonlinear dynamics
- Decrease time step to 0.0005s
- Extend simulation duration
- Enable disturbance testing

## Troubleshooting

### Common Issues

**Dashboard Won't Start**:
```bash
# Check Streamlit installation
pip install streamlit

# Verify working directory
cd /path/to/DIP_SMC_PSO
streamlit run streamlit_app.py
```

**Simulation Errors**:
- **"Configuration not found"**: Ensure `config.yaml` exists in project root
- **"Module not found"**: Install requirements: `pip install -r requirements.txt`
- **"Numerical instability"**: Reduce time step or initial conditions

**PSO Optimization Fails**:
- Check parameter bounds in `config.yaml`
- Verify controller type is properly configured
- Try different initial conditions
- Reduce optimization complexity

**Performance Issues**:
```bash
# Clear Streamlit cache
streamlit cache clear

# Check available memory
# Large simulations may require more RAM
```

### Browser Compatibility

**Recommended Browsers**:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Known Issues**:
- Internet Explorer: Not supported
- Very old browsers: May have rendering issues

## Integration with CLI Tools

### Workflow Integration

**Dashboard → CLI**:
1. Use dashboard for interactive parameter exploration
2. Export optimized parameters
3. Run production simulations via CLI
4. Generate publication-quality plots

**CLI → Dashboard**:
1. Develop parameters via CLI scripts
2. Visualize results in dashboard
3. Share interactive results with stakeholders

### Configuration Consistency

Both dashboard and CLI use the same `config.yaml` file, ensuring consistent behavior across interfaces.

## Educational Use

### Teaching Applications

**Controller Comparison**:
1. Select different controllers
2. Use identical initial conditions
3. Compare performance metrics
4. Discuss trade-offs

**Parameter Sensitivity**:
1. Run PSO to find optimal parameters
2. Manually adjust one parameter via config
3. Observe performance degradation
4. Understand parameter importance

**Disturbance Rejection**:
1. Optimize controller without disturbance
2. Apply various disturbance magnitudes
3. Compare controller robustness
4. Motivate adaptive control needs

### Research Applications

**Parameter Studies**:
- Systematic evaluation of controller variants
- Statistical analysis of optimization results
- Sensitivity analysis for uncertain parameters

**Algorithm Development**:
- Rapid prototyping of new controllers
- Interactive debugging of control algorithms
- Real-time visualization of control behavior

## Related Documentation

- [Main README](README.md) - Project overview and installation
- [CLI Guide](simulate.py --help) - Command-line interface
- [Configuration Reference](api/index.md) - Complete configuration options
- [Controller Theory](theory/smc_theory_complete.md) - Mathematical foundations
- [PSO Optimization](theory/pso_optimization_complete.md) - Optimization theory