# 2. Application Context

## 2.1 Physical setup
  - **Sensors:** measure cart position $x$, pendulum angles $\theta_1$ and $\theta_2$, and the corresponding velocities $\dot{x}$, $\dot{\theta}_1$ and $\dot{\theta}_2$.  The implementation orders these six signals as $[x,\theta_1,\theta_2,\dot{x},\dot{\theta}_1,\dot{\theta}_2]$ when forming the state vector.  This naming follows the code and I/O contracts (see `io_contracts.csv`) and eliminates the ambiguous subscript ``_c`` used in earlier drafts.  Measurements are sampled at **100 Hz**, corresponding to a 10 ms sampling period, and form the state vector for control.  This rate matches the default simulation time step ``dt = 0.01`` defined in `config.yaml` [CIT-043].  Individual controller implementations may specify a smaller internal ``dt`` (e.g., 0.001 s for certain super‑twisting or adaptive variants), but the baseline configuration and logging operate on a 10 ms period.  The sensors are quantised with step sizes configured in `config.yaml` (0.01 rad for angles and 0.0005 m for position) [CIT-044]; these finite resolutions introduce small quantisation noise but do not affect the ordering or unit definitions.  In addition to quantisation, additive white measurement noise is applied in software: the `sensors` section of `config.yaml` specifies a standard deviation of **0.005 rad** for angle measurements (`angle_noise_std`) and **0.001 m** for the cart position (`position_noise_std`) [CIT-046].  These Gaussian noise levels are injected at each 10 ms sample.  In hardware‑in‑the‑loop (HIL) experiments the `hil.sensor_noise_std` parameter controls additional transmission noise (default zero).
- **Actuator:** a linear force actuator applies a horizontal force
  $F\in[-150,150]\,\text{N}$ to the cart.  The actuator saturates at the
  specified `max_force` in `config.yaml` [CIT-045].
- **Plant:** the double‑inverted pendulum on a cart has nominal parameters defined in `config.yaml`.  These include the cart mass $m_0=1.5\,\text{kg}$, pendulum masses $m_1=0.2\,\text{kg}$ and $m_2=0.15\,\text{kg}$, lengths $l_1=0.4\,\text{m}$ and $l_2=0.3\,\text{m}$, centre‑of‑mass distances $l_{1,\mathrm{com}}=0.2\,\text{m}$ and $l_{2,\mathrm{com}}=0.15\,\text{m}$, inertias $I_1=2.65\times10^{-3}\,\text{kg·m}^2$ and $I_2=1.15\times10^{-3}\,\text{kg·m}^2$, gravitational acceleration $g=9.81\,\text{m/s}^2$, and viscous friction coefficients $b_c=0.2$, $b_1=0.005$ and $b_2=0.004$【359986572901373†screenshot】.  Earlier drafts omitted the friction values; they are essential for accurate modelling and match the defaults in the configuration.  Photos and diagrams of the setup can be placed in the `img/` folder.

## 2.2 Constraints & disturbances
Before turning to the tuning bounds, note that the nominal physical parameters stated above—cart mass, pendulum masses, lengths, centre‑of‑mass distances, inertias and friction coefficients—are taken directly from the `physics` section of `config.yaml` [CIT-063].

| Parameter | Min Value | Max Value | Unit | Description |
|-----------|-----------|-----------|------|-------------|
| cart_mass | 1.0 | 2.0 | kg | Cart mass tuned by PSO [CIT-050] |
| pendulum1_mass | 0.1 | 0.3 | kg | Mass of first pendulum [CIT-051] |
| pendulum2_mass | 0.1 | 0.2 | kg | Mass of second pendulum [CIT-052] |
| pendulum1_length | 0.3 | 0.5 | m | Length of first pendulum [CIT-053] |
| pendulum2_length | 0.2 | 0.4 | m | Length of second pendulum [CIT-054] |
| pendulum1_com | 0.15 | 0.25 | m | Centre‑of‑mass distance of first pendulum [CIT-055] |
| pendulum2_com | 0.10 | 0.20 | m | Centre‑of‑mass distance of second pendulum [CIT-056] |
| pendulum1_inertia | 0.0015 | 0.004 | kg·m² | Inertia of first pendulum about pivot [CIT-057] |
| pendulum2_inertia | 0.0005 | 0.002 | kg·m² | Inertia of second pendulum about pivot [CIT-058] |
| boundary_layer | 0.01 | 0.05 | – | SMC boundary layer width (dimensionless) [CIT-059] |
| max_force | 150 | 150 | N | Actuator saturation limit (fixed at 150 N in `config.yaml`) [CIT-045] |
| cart_friction | 0.1 | 0.5 | – | Viscous friction coefficient for the cart [CIT-060] |
| joint1_friction | 0.001 | 0.01 | – | Friction coefficient for the first joint [CIT-061] |
| joint2_friction | 0.001 | 0.01 | – | Friction coefficient for the second joint [CIT-062] |

These minimum and maximum values are **not** arbitrary ±10 % variations;
they originate from the `pso.tune` section of `config.yaml` and define
the search domain used by the PSO tuner when jointly optimising
controller gains and selected physical parameters.  Each parameter is
sampled uniformly within its specified range when tuning is enabled.

Other sources of disturbance include quantisation noise and sensor
noise.  The sensors have finite resolution (0.01 rad for angles and
0.0005 m for position), and these quantisation steps are specified as
`quantization_angle` and `quantization_position` in `config.yaml` [CIT-044].
Additive measurement noise levels are defined in the `sensors` section
of the configuration and are set to **0.005 rad** for angles and **0.001 m** for position by default; these values mirror the `angle_noise_std` and `position_noise_std` entries in `config.yaml` [CIT-046].  Unmodelled higher‑order dynamics and external
perturbations may also act on the system.  The PSO tuner and
robustness tests vary the physical parameters within the above bounds
and inject sensor noise and disturbances to evaluate controller
performance under uncertainty.

## 2.3 Objectives ↔ KPIs
- **Objective:** track cart position reference quickly while keeping both
  pendulums upright and minimising control energy.
  - **KPIs:**  
    - *Settling time:* $t_s < 2\,\text{s}$ (`KPI‑001`)  
    - *Overshoot:* $M_p < 10 \%$ (`KPI‑002`)  
    - *IAE:* minimised over the simulation horizon (`KPI‑003`)
    - *Stability margins:* phase margin ≥ 45°, gain margin ≥ 6 dB (`KPI‑004`)
