# 5.x Test Protocols

## Test Matrix

| Test ID | Scenario              | KPI                          | Pass/Fail Criteria                                     | Notes |
|---------|-----------------------|------------------------------|--------------------------------------------------------|-------|
| T‑001   | Step input $r$: 0→1 m | Settling time & overshoot    | $t_s \\le 2\\,\\text{s}$ and $M_p \\le 10\\,\\%$ [CIT-075]             |       |
| T‑002   | +10 % plant gain      | Stability margins             | phase margin ≥ 45°, gain margin ≥ 6 dB [CIT-076]                 |       |
| T‑003   | Fault detection (persistent residual) | FDI residual & status | FDI declares FAULT after persistence threshold (no safe‑state control) [CIT-077] |       |

## Procedures

- **Preconditions:** ensure the simulation environment is configured with the
  nominal parameters from `config.yaml` and that the controller gains are
  set to the baseline values or those produced by the PSO tuner.  Initialise
  the state at the upright equilibrium with small perturbations.
- **Equipment/scripts:** use `python simulate.py --controller classical_smc` (or another
  controller name such as `sta_smc`, `adaptive_smc`, etc.) to run the step and
  robustness tests.  For a detailed frequency‑domain comparison, run
  `python scripts/run_model_comparison.py`, which linearises the plant and computes
  Bode plots and phase/gain margins.  For fault‑detection testing, enable the
  FDI system by setting `fdi.enabled: true` in `config.yaml` and optionally pass
  `--plot-fdi` to `simulate.py` to display the residuals.  The FDI module uses a
  configurable residual threshold and persistence counter.  In the default
  configuration (`src/fault_detection/fdi.py`) the base residual threshold is
  **0.5** and a fault is declared only after the residual norm exceeds this
  threshold for **10** consecutive samples (100 ms at 100 Hz) [CIT-048].  Adaptive
  thresholding and CUSUM drift detection can be enabled via the same
  configuration: when `adaptive` is set to `true` the threshold becomes
  `μ + threshold_factor⋅σ` over the last `window_size` residuals (defaults: window
  of 50 samples and `threshold_factor = 3.0`); when `cusum_enabled` is `true` a
  cumulative sum of residual deviations is compared against `cusum_threshold`
  (default 5.0) to detect slow drifts [CIT-049].  Both adaptive and CUSUM features are
  disabled by default.  Logs are stored under `/data/raw/<test_id>/`.
- **Data collection:** record the full state vector, control input,
  reference and error signals at **100 Hz** (10 ms sampling) [CIT-043].  For each test ID, store the log
  under `/data/raw/<test_id>/`.
- **Analysis steps:** compute settling time by finding when the cart
  position remains within 2 % of the reference for at least 1 s.  Compute
  overshoot as the maximum deviation above the reference.  Compute integral of squared
  error (ISE) and integral of absolute error (IAE) by numerical integration as
  metrics of tracking performance.  For frequency‑domain tests (T‑002),
  linearise the plant with `python scripts/run_model_comparison.py` and
  compute phase/gain margins.  For the fault‑detection test (T‑003), plot the
  residual norm over time using `python tests/test_fault_detection/test_fdi.py`
  (or a custom script) and verify the time at which the FDI system changes
  status from OK to FAULT.
- **Pass/fail criteria:** T‑001 passes if $t_s \\le 2\\,\\text{s}$ and the
  overshoot ($M_p$) satisfies $M_p \\le 10\\%$.  T‑002 passes if the phase
  margin is at least 45° and gain margin is at least 6 dB.  T‑003 passes if
  the FDI system declares a fault when the residual norm exceeds the adaptive
  or fixed threshold for the specified persistence counter.  In the default
  configuration this means the residual norm must exceed **0.5** for **10**
  consecutive samples.  No safe‑state control is currently implemented; a
  fault merely changes the status from “OK” to “FAULT”.