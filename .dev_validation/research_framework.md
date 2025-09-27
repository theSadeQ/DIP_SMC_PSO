# SMC Controllers Comparison Research Framework

## Research Objectives

### Primary Objective
Compare four Sliding Mode Control variants for double inverted pendulum:
1. **Classical SMC** - Traditional sliding mode with sign function
2. **Adaptive SMC** - Self-tuning gains without disturbance bounds knowledge
3. **STA SMC** - Super-Twisting Algorithm for chattering reduction
4. **Hybrid Adaptive-STA SMC** - Combined adaptive and super-twisting benefits

## Research Hypotheses

### H1: Chattering Reduction
**Hypothesis**: STA SMC and Hybrid SMC will demonstrate significantly lower chattering compared to Classical and Adaptive SMC.
- **Metric**: Control signal variance, high-frequency content analysis
- **Expected Outcome**: 60-80% chattering reduction based on literature

### H2: Convergence Performance
**Hypothesis**: Adaptive-based controllers will achieve faster stabilization times.
- **Metric**: Settling time, rise time, steady-state error
- **Expected Outcome**: 30-45% improvement in convergence speed

### H3: Robustness Analysis
**Hypothesis**: Hybrid Adaptive-STA will show superior performance under uncertainties.
- **Test Conditions**: ±20% mass variation, ±15% length uncertainty, external disturbances
- **Metric**: Performance degradation under uncertainty

### H4: Energy Efficiency
**Hypothesis**: STA-based controllers will require lower control energy.
- **Metric**: Integrated absolute control effort (IACE), RMS control signal
- **Expected Outcome**: 20-30% energy reduction

## Experimental Design

### Test Scenarios
1. **Nominal Performance**: Standard swing-up and stabilization
2. **Disturbance Rejection**: Step and sinusoidal disturbances
3. **Parameter Uncertainty**: Monte Carlo with random parameters
4. **Noise Sensitivity**: Measurement noise robustness
5. **Initial Condition Variation**: Different starting positions

### Performance Metrics
- **Time Domain**: Settling time, overshoot, steady-state error
- **Frequency Domain**: Bandwidth, phase/gain margins
- **Control Quality**: Chattering index, energy consumption
- **Robustness**: Sensitivity functions, uncertainty bounds

### Statistical Analysis
- **Sample Size**: 100 trials per scenario per controller
- **Significance Testing**: ANOVA, Tukey HSD post-hoc tests
- **Effect Size**: Cohen's d for practical significance
- **Confidence Level**: 95% confidence intervals

## Success Criteria
1. Identify best-performing controller for each scenario
2. Quantify trade-offs between performance metrics
3. Provide design guidelines for controller selection
4. Publish comparative analysis with statistical significance

## Timeline
- **Weeks 1-2**: Literature review completion ✓
- **Weeks 3-4**: Experimental framework implementation
- **Weeks 5-8**: Data collection and analysis
- **Weeks 9-10**: Statistical analysis and report writing