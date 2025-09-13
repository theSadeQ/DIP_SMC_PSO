# 5. Analysis & Verification Plan

## 5.1 Tuning & Methods
The controllers are tuned using **particle swarm optimisation (PSO)**.
PSO minimises a weighted cost function composed of four terms: the
**integral of squared error (ISE)**, the **control effort**, the
**control rate (slew)** and the **energy of the sliding variable**.  These
quantities are the only ones used to rank candidate gains in
`src/optimizer/pso_optimizer.py` and are configured via the weights in
`config.yaml`【732825508736690†screenshot】.  Earlier drafts erroneously
suggested that **integral absolute error (IAE)** and overshoot were part
of the optimisation cost; in fact they are used only for post‑tuning
validation.

The weighting of each term in the cost is governed by
`cost_function.weights` in `config.yaml`.  The default configuration sets
`state_error` to 50.0, `control_effort` to 0.2, `control_rate` to 0.1 and
`stability` to 0.1.  During optimisation the PSO tuner normalises the
integral of squared error, the integral of squared control, the integral
of squared control rate and the sliding‑variable energy, and then
multiplies each normalised metric by its corresponding weight.  Larger
`state_error` favours tracking accuracy, while larger `control_effort`
or `control_rate` encourage energy efficiency and smoother actuation.
The `stability` weight scales the energy of the sliding variable and is
also applied to the instability penalty for early failures.  These
values mirror the `cost_function` section of `config.yaml` and are
applied in the implementation via `self.weights` in
`PSOTuner._compute_cost_from_traj`.

The PSO search bounds are defined under `pso.bounds` and
correspond one‑to‑one with the gains required by each controller as
well as any tunable physical parameters.

Each controller class expects a specific length and ordering of gains, and the implementation enforces positivity constraints:

* **Classical SMC** – accepts a six‑element vector `[k1, k2, λ1, λ2, K, kd]`.  The gains `k1` and `k2` weight pendulum velocity/angle terms in the sliding surface, `λ1` and `λ2` set the surface slope (1/s), `K` is the switching gain and `kd` is an optional derivative gain used for damping.  The constructor checks that `k1`, `k2`, `λ1`, `λ2` and `K` are strictly positive and that `kd` is non‑negative; otherwise a `ValueError` is raised.  Exactly six numbers must be supplied; any extras are ignored.

* **Super‑twisting SMC (STA)** – uses two algorithmic gains `K1` and `K2` together with surface parameters `[k1, k2, λ1, λ2]`.  A six‑element vector `[K1, K2, k1, k2, λ1, λ2]` specifies all parameters explicitly; a two‑element vector `[K1, K2]` is also accepted and defaults the surface gains to positive constants `[5.0, 3.0, 2.0, 1.0]`.  Only the first six entries are used; additional values are ignored.  All gains must be strictly positive to ensure finite‑time convergence【MorenoOsorio2012†L27-L40】.

* **Adaptive SMC** – requires at least five gains `[k1, k2, λ1, λ2, γ]`.  The first four define the sliding surface and must be strictly positive; `γ` is the adaptation rate driving the switching gain and must also be positive.  Fewer than five gains is a configuration error; additional values are ignored.  A separate proportional coefficient `α` multiplies the sliding surface (`u = u_sw - α·σ`) and is configured independently (default 0.5) outside of the PSO‑optimised vector【462167782799487†L186-L195】.

* **Hybrid adaptive super‑twisting SMC** – requires at least four gains `[c1, λ1, c2, λ2]`.  Extra entries are ignored.  Positivity of `c1`, `c2` and the slope parameters `λ1`, `λ2` is enforced.  Additional adaptation limits, damping gains and recentering parameters are configured via `config.yaml` and are not part of the PSO‑tuned vector【895515998216162†L326-L329】.

Optional tuning of physical parameters—masses, lengths, centre‑of‑mass distances, friction coefficients and the boundary‑layer width—is controlled by `pso.tune`.  When enabled the PSO evaluates each candidate gain vector (and any drawn parameters) across a suite of step and disturbance scenarios before computing the cost.

**Metrics:** The optimisation and validation use several metrics:
IAE and ISE over the simulation horizon; percentage overshoot relative to
the setpoint; steady‑state error; settling time; and bandwidth and phase/gain
margins from the linearised plant models.  Control energy (integral of
|F| over time) is also monitored.

**Robustness:** Robustness is assessed by varying plant parameters within
their PSO bounds (as defined in the `physics_uncertainty` and `pso.tune`
sections of `config.yaml`).  In the default configuration this equates to
approximately ±5 % variation on masses, lengths, centre‑of‑mass
distances and inertias, and ±10 % variation on viscous friction
coefficients.  These draws, together with injected sensor noise,
actuator saturation and friction disturbances, test the robustness of
the controller.  The controller must maintain stability and acceptable
performance for all sampled variations.

## 5.2 Datasets
Identification: `/data/raw/step/*.csv`, `/data/raw/chirp/*.csv`,
`/data/raw/free_decay/*.csv` and `/data/raw/multisine/*.csv` contain raw
experimental or simulated data used to estimate the plant parameters.
Validation: `/data/raw/step_validation/*.csv` and other reserved files are
held out for validating the identified models and controllers.

## 5.3 KPIs & Pass/Fail
| KPI ID | Definition | Target | Measured by (Test ID) | Pass/Fail Threshold |
|--------|------------|--------|-----------------------|---------------------|
| KPI‑001 | Settling time | $t_s < 2\,\text{s}$ | T‑001 | $t_s \le 2\,\text{s}$ |
| KPI‑002 | Overshoot | < 10 % | T‑001 | $M_p \le 10\,\%$ |
| KPI‑003 | IAE | minimised | T‑001, T‑002 | IAE within tuned bounds |
| KPI‑004 | Stability margin | PM ≥ 45°, GM ≥ 6 dB | T‑002 | margins met |

## 5.4 Logging Conventions
Simulations and experiments are logged at **100 Hz**, corresponding to a 10 ms sampling period.  This matches the default simulator time step `dt = 0.01` defined in `config.yaml`.  Some controllers integrate internally at smaller steps (e.g. 1 ms for super‑twisting or adaptive variants), but all logging and nominal simulations operate at 100 Hz.  Logs include time stamps, full state vectors and control inputs.  Raw logs are
comma‑separated value (CSV) files under `/data/raw/`; processed summaries
are stored in `/data/processed/`.  Each log includes metadata such as
configuration hash, controller gains, seed and test ID for reproducibility.