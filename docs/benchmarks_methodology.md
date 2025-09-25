# Benchmarks & Methodology

This project includes comprehensive benchmarking capabilities for statistical analysis and performance comparison of sliding mode controllers. The benchmarking system provides standardized evaluation protocols and robust statistical metrics.

## Overview

The benchmarking framework evaluates controllers across multiple dimensions:

- **Performance metrics**: ISE, ITAE, RMS control effort, overshoot, constraint violations
- **Statistical validation**: 95% confidence intervals, Central Limit Theorem compliance
- **Robustness testing**: Physics parameter uncertainty, sensor noise, initial condition variations
- **Reproducibility**: Seeded random number generation for consistent results

## Core Metrics

### 1. State Error Metrics

**Integral of Squared Error (ISE)**
```
ISE = ∫₀ᵀ ||x(t)||² dt
```
- Measures cumulative tracking error across all state variables
- Lower values indicate better tracking performance
- Units: [position²·time] for position states, [angle²·time] for angular states

**Integral of Time-weighted Absolute Error (ITAE)**
```
ITAE = ∫₀ᵀ t·|x(t)| dt
```
- Emphasizes errors occurring later in the trajectory
- Penalizes sustained deviations more heavily than transient errors
- Preferred for evaluating settling characteristics

### 2. Control Effort Metrics

**RMS Control Effort**
```
RMS_u = √(1/T ∫₀ᵀ u(t)² dt)
```
- Measures average control energy consumption
- Important for actuator sizing and power requirements
- Units: [Force] for double pendulum system

**Control Rate (Slew Rate)**
```
du_RMS = √(1/T ∫₀ᵀ (du/dt)² dt)
```
- Measures control signal smoothness
- High values indicate chattering or aggressive switching
- Critical for actuator wear and implementation feasibility

### 3. Stability Metrics

**Maximum Overshoot**
```
Overshoot = max_{t∈[0,T]} |θᵢ(t)| for i ∈ {1,2}
```
- Maximum angular deviation from equilibrium
- Safety-critical for physical systems
- Units: [radians]

**Constraint Violations**
```
Violations = |{t : |u(t)| > u_max}|
```
- Number of time steps where control limits are exceeded
- Zero violations required for safe operation
- Configurable via `max_force` parameter

### 4. Sliding Mode Specific Metrics

**Sliding Variable Energy**
```
σ_energy = ∫₀ᵀ σ(t)² dt
```
- Measures sliding surface adherence
- Lower values indicate better sliding mode performance
- Defined by controller-specific sliding surface design

## Statistical Methodology

### Sample Size Requirements

The benchmarking system uses **n=30 trials** by default, based on Central Limit Theorem requirements:

- For approximately normal distributions: n ≥ 25-30 sufficient
- For skewed distributions: n ≥ 30 recommended
- Each trial uses independent random seeds for reproducibility

### Confidence Intervals

**95% Confidence Interval Calculation:**
```
CI = x̄ ± 1.96 × (s/√n)
```
Where:
- `x̄`: sample mean
- `s`: sample standard deviation (Bessel's correction)
- `n`: number of trials (30)
- `1.96`: z-score for 95% confidence level

### Random Seed Management

```python
# Base seed for reproducibility
base_seed = 1234

# Each trial gets independent seed
trial_seeds = rng.integers(0, 2**32-1, size=n_trials)
```

## Robustness Testing Scenarios

### 1. Nominal Conditions

- Standard physics parameters from `config.yaml`
- No sensor noise or parameter uncertainty
- Baseline for controller comparison

### 2. Parameter Uncertainty

Physics parameters perturbed within realistic bounds:

```yaml
physics_uncertainty:
  n_evals: 10                    # Number of uncertainty scenarios
  cart_mass: 0.05               # ±5% variation
  pendulum1_mass: 0.10          # ±10% variation
  pendulum2_mass: 0.10          # ±10% variation
  pendulum1_length: 0.05        # ±5% variation
  pendulum2_length: 0.05        # ±5% variation
  friction_cart: 0.20           # ±20% variation
```

### 3. Sensor Noise

Additive Gaussian noise applied to state measurements:

```python
# Configurable noise standard deviation
noise_std = 0.001  # 1mm position noise
x_noisy = x_true + N(0, noise_std)
```

### 4. Initial Condition Variations

Random perturbations around equilibrium:

```python
# Example: ±5 degree initial angle variation
θ1_init = np.random.uniform(-π/36, π/36)
θ2_init = np.random.uniform(-π/36, π/36)
```

## Usage Examples

### Basic Benchmark Run

```python
from src.benchmarks.statistical_benchmarks_v2 import run_trials
from src.controllers.factory import create_controller_factory
from src.config import load_config

# Load configuration
config = load_config('config.yaml')

# Create controller factory
factory = create_controller_factory('classical_smc', config.controllers.classical_smc)

# Run benchmark
metrics_per_trial, ci_results = run_trials(
    controller_factory=factory,
    cfg=config,
    n_trials=30,
    seed=1234
)

# Display results with confidence intervals
for metric, (mean, ci_width) in ci_results.items():
    print(f"{metric}: {mean:.4f} ± {ci_width:.4f}")
```

### Robustness Evaluation

```python
# Test with physics uncertainty and sensor noise
metrics_robust, ci_robust = run_trials(
    controller_factory=factory,
    cfg=config,
    n_trials=50,              # More trials for robustness testing
    randomise_physics=True,   # Enable parameter variations
    noise_std=0.001          # Add sensor noise
)
```

### Controller Comparison

```python
controllers = ['classical_smc', 'sta_smc', 'adaptive_smc']
results = {}

for ctrl_name in controllers:
    factory = create_controller_factory(ctrl_name, getattr(config.controllers, ctrl_name))
    _, ci_results = run_trials(factory, config, n_trials=30)
    results[ctrl_name] = ci_results

# Compare ISE performance
for ctrl, metrics in results.items():
    ise_mean, ise_ci = metrics['ise']
    print(f"{ctrl}: ISE = {ise_mean:.3f} ± {ise_ci:.3f}")
```

## Performance Acceptance Criteria

### Tracking Performance

- **ISE < 0.1**: Excellent tracking
- **ISE < 0.5**: Good tracking
- **ISE > 1.0**: Poor tracking, investigate controller tuning

### Control Effort

- **RMS_u < 10 N**: Low energy consumption
- **RMS_u < 50 N**: Moderate energy consumption
- **RMS_u > 100 N**: High energy, check actuator specifications

### Stability Requirements

- **Violations = 0**: Required for all controllers
- **Overshoot < π/4**: Safety limit for pendulum angles
- **Overshoot < π/6**: Preferred for smooth operation

### Control Quality

- **Control rate < 1000 N/s**: Smooth control, low chattering
- **Control rate > 5000 N/s**: Excessive chattering, tune boundary layer

## Integration with PSO Optimization

The benchmarking metrics form the basis for PSO cost function design:

```yaml
cost_function:
  weights:
    state_error: 50.0      # Emphasize tracking performance
    control_effort: 0.2    # Minimize energy consumption
    control_rate: 0.1      # Penalize chattering
    stability: 0.1         # Sliding variable penalty
```

**Multi-objective Optimization:**
```
J = w₁·ISE_norm + w₂·RMS_u_norm + w₃·du_norm + w₄·σ_norm + penalties
```

Where normalization prevents metric dominance and penalties handle constraint violations.

## Reproducibility Guidelines

### Configuration Management

1. **Version Control**: Store exact `config.yaml` with benchmark results
2. **Seed Documentation**: Record random seeds for each benchmark run
3. **Environment Info**: Log Python version, NumPy version, hardware specs
4. **Parameter Tracking**: Save optimized controller gains with benchmark data

### Result Documentation

```python
benchmark_metadata = {
    'timestamp': datetime.now().isoformat(),
    'config_hash': hashlib.md5(config_content).hexdigest(),
    'random_seed': 1234,
    'n_trials': 30,
    'environment': {
        'python_version': sys.version,
        'numpy_version': np.__version__,
        'platform': platform.platform()
    }
}
```

### Statistical Reporting

Always report confidence intervals alongside point estimates:

```
Classical SMC Performance:
- ISE: 0.045 ± 0.003 [dimensionless]
- RMS Control: 12.3 ± 1.2 [N]
- Max Overshoot: 0.087 ± 0.012 [rad]
- Violations: 0 ± 0 [count]
```

## Advanced Analysis

### Performance Sensitivity

Evaluate controller robustness by varying uncertainty levels:

```python
uncertainty_levels = [0.0, 0.05, 0.10, 0.15, 0.20]
sensitivity_results = {}

for uncertainty in uncertainty_levels:
    # Update config with uncertainty level
    config.physics_uncertainty.cart_mass = uncertainty

    # Run benchmark
    _, ci_results = run_trials(factory, config, n_trials=30)
    sensitivity_results[uncertainty] = ci_results['ise'][0]  # Mean ISE
```

### Statistical Significance Testing

Compare controllers using t-tests or non-parametric methods:

```python
from scipy import stats

# Compare two controllers
ctrl1_ise = [trial['ise'] for trial in metrics_ctrl1]
ctrl2_ise = [trial['ise'] for trial in metrics_ctrl2]

# Welch's t-test (unequal variances)
t_stat, p_value = stats.ttest_ind(ctrl1_ise, ctrl2_ise, equal_var=False)

# Significant difference if p < 0.05
if p_value < 0.05:
    print(f"Controllers significantly different (p={p_value:.4f})")
```

## Related Documentation

- [PSO Optimization Theory](theory/pso_optimization_complete.md) - Cost function design
- [Statistical Benchmarks Source](../src/benchmarks/statistical_benchmarks.py) - Implementation details
- [Configuration Reference](api/index.md) - Benchmark configuration options
- [Controller Comparison Results](results/index.md) - Benchmark result examples