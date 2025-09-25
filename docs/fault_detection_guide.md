# Fault Detection & Isolation (FDI) Guide

## Overview

The DIP_SMC_PSO system includes a comprehensive Fault Detection and Isolation (FDI) module that monitors system health in real-time. The FDI system compares model predictions with actual measurements to detect deviations that may indicate component failures, sensor faults, or unexpected disturbances.

## Architecture

The FDI system uses a **model-based residual approach**:

```
┌─────────────┐    ┌─────────────┐
│   Dynamics  │    │ Measurement │
│    Model    │    │   (Actual)  │
│   x̂(k+1)    │    │    x(k+1)   │
└──────┬──────┘    └──────┬──────┘
       │                  │
       └────────┬─────────┘
                │
        ┌───────▼────────┐
        │ Residual = r   │
        │ = x(k+1)-x̂(k+1)│
        └───────┬────────┘
                │
        ┌───────▼────────┐
        │ ||r|| > threshold │
        │ & persistence? │
        └────────────────┘
```

**Key Components:**

1. **Residual Generation**: Compares one-step predictions with measurements
2. **Threshold Testing**: Monitors residual norm against configurable limits
3. **Persistence Filter**: Requires sustained violations to avoid false alarms
4. **Adaptive Thresholds**: Dynamically adjusts limits based on operating conditions
5. **CUSUM Detection**: Detects slow parameter drifts over time

## Configuration

### Basic Configuration

Add FDI configuration to your `config.yaml`:

```yaml
fdi:
  enabled: true
  residual_threshold: 0.5      # Base threshold for residual norm
  persistence_counter: 10      # Consecutive violations required
  residual_states: [0, 1, 2]   # State indices to monitor (x, θ₁, θ₂)
  residual_weights: null       # Optional per-state weights
```

### Advanced Configuration

```yaml
fdi:
  enabled: true
  residual_threshold: 0.3
  persistence_counter: 5
  residual_states: [0, 1, 2, 3, 4, 5]  # Monitor all 6 states
  residual_weights: [1.0, 2.0, 2.0, 0.5, 1.5, 1.5]  # Weight angles more heavily

  # Adaptive thresholding
  adaptive: true
  window_size: 50              # Samples for threshold estimation
  threshold_factor: 3.0        # σ multiplier for adaptive threshold

  # CUSUM drift detection
  cusum_enabled: true
  cusum_threshold: 5.0         # Cumulative sum limit
```

## Usage Examples

### Basic FDI Monitoring

```bash
# Enable FDI in config.yaml and run simulation
python simulate.py --ctrl classical_smc --plot --plot-fdi
```

### Programmatic Usage

```python
from src.fault_detection.fdi import FDIsystem
from src.core.dynamics import DoublePendulum
import numpy as np

# Create FDI system
fdi = FDIsystem(
    residual_threshold=0.5,
    persistence_counter=10,
    residual_states=[0, 1, 2]  # Monitor position and angles
)

# Create dynamics model for predictions
dynamics = DoublePendulum()

# Simulation loop with FDI monitoring
for t in np.arange(0, 10, 0.001):
    # Get measurement (in practice, from sensors)
    x_measured = get_sensor_data()

    # Get control input
    u = controller.compute_control(x_measured, x_ref, t)

    # FDI check
    status, residual_norm = fdi.check(
        t=t,
        meas=x_measured,
        u=u,
        dt=0.001,
        dynamics_model=dynamics
    )

    if status == "FAULT":
        print(f"FAULT DETECTED at t={t:.3f}s, residual={residual_norm:.3f}")
        # Implement safety response
        break

    # Continue simulation
    x_next = dynamics.step(x_measured, u, 0.001)
```

## Threshold Configuration Guidelines

### Static Thresholds

**Position Residuals (x):**
- `threshold = 0.01-0.05` m for high-precision systems
- `threshold = 0.1-0.2` m for typical laboratory setups
- `threshold = 0.5-1.0` m for coarse monitoring

**Angular Residuals (θ₁, θ₂):**
- `threshold = 0.01-0.05` rad (0.6-3°) for precise control
- `threshold = 0.1-0.2` rad (6-11°) for standard operation
- `threshold = 0.5` rad (29°) for safety-critical detection

**Velocity Residuals (ẋ, θ̇₁, θ̇₂):**
- Often noisier than position measurements
- Use 2-5× larger thresholds than position equivalents
- Consider filtering or excluding from residual calculation

### Adaptive Thresholds

When `adaptive = true`, the threshold becomes:
```
threshold(t) = μ + threshold_factor × σ
```
Where μ and σ are estimated from the last `window_size` residuals.

**Parameter Guidelines:**
- `window_size = 50-100`: Balance responsiveness vs. stability
- `threshold_factor = 2.0-4.0`: Corresponds to confidence levels
  - `factor = 2.0`: ~95% confidence (more sensitive)
  - `factor = 3.0`: ~99.7% confidence (balanced)
  - `factor = 4.0`: ~99.99% confidence (conservative)

## Persistence and False Alarm Management

### Persistence Counter

The `persistence_counter` requires sustained threshold violations:

```
FAULT declared if: violation_count ≥ persistence_counter
```

**Selection Guidelines:**
- `persistence = 1`: Immediate detection, higher false alarm rate
- `persistence = 5-10`: Balanced detection vs. false alarms
- `persistence = 20-50`: Conservative, slower detection

**Time-based Interpretation:**
- At 1000 Hz sampling: `persistence = 10` → 10ms sustained fault
- At 100 Hz sampling: `persistence = 10` → 100ms sustained fault

### State Weighting

Use `residual_weights` to emphasize critical states:

```yaml
# Example: Emphasize angular states for pendulum stability
residual_states: [0, 1, 2]        # x, θ₁, θ₂
residual_weights: [0.5, 2.0, 2.0] # Weight angles 4× more than position
```

The weighted residual norm becomes:
```
||r||_weighted = √(w₁r₁² + w₂r₂² + w₃r₃²)
```

## CUSUM Drift Detection

CUSUM (Cumulative Sum) detection complements threshold-based monitoring by accumulating small deviations over time.

### Algorithm

```
S(k) = max(0, S(k-1) + (r(k) - μ))
FAULT if S(k) > cusum_threshold
```

Where:
- `r(k)`: Current residual norm
- `μ`: Running average of residual norm
- `S(k)`: Cumulative sum statistic

### Configuration {#cusum-configuration}

```yaml
fdi:
  cusum_enabled: true
  cusum_threshold: 5.0    # Adjust based on expected drift magnitude
```

**Threshold Selection:**
- Lower values (1.0-3.0): Detect small parameter changes quickly
- Higher values (5.0-10.0): Reduce false alarms from noise
- Monitor CUSUM statistic during normal operation to calibrate

## Fault Types and Signatures

### Sensor Faults

**Bias Fault:**
- Constant offset in measurements
- **Signature**: Persistent residual in one direction
- **Detection**: Low threshold with moderate persistence

**Drift Fault:**
- Gradually changing sensor calibration
- **Signature**: Slowly increasing residual trend
- **Detection**: Enable CUSUM with moderate threshold

**Noise Fault:**
- Increased measurement noise
- **Signature**: Higher residual variance
- **Detection**: Adaptive thresholding automatically adjusts

**Stuck Sensor:**
- Sensor output frozen at constant value
- **Signature**: Residual tracks true motion
- **Detection**: Low threshold, immediate persistence

### Actuator Faults

**Reduced Effectiveness:**
- Actuator produces less force than commanded
- **Signature**: Tracking error increases over time
- **Detection**: Monitor position states with CUSUM

**Actuator Saturation:**
- Control input clipped beyond model assumptions
- **Signature**: Residuals during large control demands
- **Detection**: Condition-based thresholds

### Physical Parameter Changes

**Mass Changes:**
- Load added/removed from system
- **Signature**: Changes in acceleration response
- **Detection**: CUSUM on velocity residuals

**Friction Changes:**
- Wear, lubrication loss, contamination
- **Signature**: Velocity-dependent residual patterns
- **Detection**: Adaptive thresholding with long window

## Diagnostic Plots and Analysis

### FDI Visualization

```bash
# Generate FDI plots with simulation
python simulate.py --ctrl sta_smc --plot --plot-fdi
```

**Plot Elements:**
- **Residual Time Series**: Shows r(t) evolution
- **Threshold Lines**: Static and adaptive limits
- **Fault Markers**: Indicates detection times
- **CUSUM Trace**: Cumulative statistic (if enabled)

### Analysis Code

```python
# Access FDI history for custom analysis
import matplotlib.pyplot as plt

# After simulation with FDI enabled
times = fdi.times
residuals = fdi.residuals

# Plot residual statistics
plt.figure(figsize=(12, 8))

# Residual time series
plt.subplot(2, 2, 1)
plt.plot(times, residuals)
plt.axhline(fdi.residual_threshold, color='r', linestyle='--')
plt.ylabel('Residual Norm')
plt.title('FDI Residual History')

# Residual histogram
plt.subplot(2, 2, 2)
plt.hist(residuals, bins=50, alpha=0.7)
plt.xlabel('Residual Norm')
plt.ylabel('Frequency')
plt.title('Residual Distribution')

# Moving statistics
window = 50
if len(residuals) > window:
    moving_mean = np.convolve(residuals, np.ones(window)/window, mode='valid')
    moving_std = [np.std(residuals[i:i+window]) for i in range(len(residuals)-window+1)]

    plt.subplot(2, 2, 3)
    plt.plot(times[window-1:], moving_mean, label='Moving Mean')
    plt.plot(times[window-1:], np.array(moving_mean) + 3*np.array(moving_std),
             'r--', label='μ + 3σ')
    plt.ylabel('Residual Statistics')
    plt.legend()
    plt.title('Adaptive Threshold Evolution')

plt.tight_layout()
plt.show()
```

## Integration with Control System

### Safe State Responses

When a fault is detected, implement appropriate safety measures:

```python
if status == "FAULT":
    # Log fault information
    logging.critical(f"FAULT at t={t:.3f}s: residual={residual_norm:.3f}")

    # Safety responses (choose appropriate action)

    # Option 1: Emergency stop
    u = 0.0

    # Option 2: Switch to safe controller
    controller = safe_mode_controller

    # Option 3: Graceful shutdown
    target_state = safe_equilibrium

    # Option 4: Reduce performance
    controller.reduce_gains(factor=0.5)
```

### Controller Reconfiguration

```python
# Fault-tolerant control example
class FaultTolerantController:
    def __init__(self, primary_controller, backup_controller, fdi_system):
        self.primary = primary_controller
        self.backup = backup_controller
        self.fdi = fdi_system
        self.active_controller = primary_controller

    def compute_control(self, x, x_ref, t, u_prev, dt, dynamics):
        # FDI check
        status, residual = self.fdi.check(t, x, u_prev, dt, dynamics)

        # Switch controllers if fault detected
        if status == "FAULT" and self.active_controller == self.primary:
            logging.warning("Switching to backup controller due to fault")
            self.active_controller = self.backup

        return self.active_controller.compute_control(x, x_ref, t)
```

## Performance Considerations

### Computational Cost

FDI adds minimal overhead:
- Model prediction: ~10 μs (for simplified dynamics)
- Residual computation: ~1 μs
- Threshold checking: ~0.1 μs

**Total overhead**: <1% of 1 kHz control loop

### Memory Usage

- History storage: `O(simulation_length / dt)` for plotting
- Adaptive window: `O(window_size)` floating-point values
- Total memory: Negligible for typical simulations

### Real-time Considerations

- Use simplified dynamics model for FDI predictions
- Limit history storage in embedded implementations
- Consider downsampling FDI rate if computational resources are constrained

## Troubleshooting

### High False Alarm Rate

**Symptoms**: Frequent fault detections during normal operation

**Solutions**:
1. Increase `residual_threshold`
2. Increase `persistence_counter`
3. Enable adaptive thresholding
4. Check model accuracy
5. Verify sensor noise levels

### Missed Fault Detection

**Symptoms**: Known faults not detected by FDI

**Solutions**:
1. Decrease `residual_threshold`
2. Decrease `persistence_counter`
3. Enable CUSUM for slow faults
4. Check `residual_states` selection
5. Tune `residual_weights` for critical states

### Noisy Residuals

**Symptoms**: High-frequency oscillations in residual signal

**Solutions**:
1. Filter measurements before FDI
2. Use adaptive thresholding
3. Increase `window_size`
4. Check integration timestep
5. Verify model-plant match

## Related Documentation

- [System Architecture](architecture.md) - Overall system design
- [Configuration Reference](api/index.md) - Complete FDI configuration options
- [Testing Guide](TESTING.md) - How to test FDI functionality
- [FDI Source Code](../src/fault_detection/fdi.py) - FDI implementation details