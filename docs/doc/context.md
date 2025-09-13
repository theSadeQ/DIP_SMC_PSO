# 2. Application Context

## 2.1 Physical setup

The system under consideration is a **double inverted pendulum on a cart**.  Two rigid pendulums are mounted on a horizontally moving cart.  The following signals are measured and fed back for control:

  - **Sensors:** cart position $x$, pendulum angles $\theta_1$ and $\theta_2$, and the corresponding velocities $\dot{x}$, $\dot{\theta}_1$ and $\dot{\theta}_2$.  The six measured signals are ordered as $[x,\theta_1,\theta_2,\dot{x},\dot{\theta}_1,\dot{\theta}_2]$ in the implementation.  This naming matches the code and `io_contracts.csv` and supersedes the earlier $x_c$ notation.  Measurements are sampled at **100 Hz** (10 ms period), matching the default simulator time step (`simulation.dt = 0.01` in `config.yaml`).  Individual controller variants may integrate internally at smaller steps (e.g., 1 ms for super‑twisting or adaptive SMC), but logging and nominal simulations operate at 10 ms.  The sensors are quantised with step sizes defined in `config.yaml` (0.01 rad for angles and 0.0005 m for position), which introduce small quantisation noise in the measurements without affecting the ordering or units.  In addition to quantisation, additive white measurement noise is applied to each sample: the `sensors` section of `config.yaml` specifies a standard deviation of **0.005 rad** for angle measurements (`angle_noise_std`) and **0.001 m** for the cart position (`position_noise_std`).  These Gaussian noise levels model sensor imperfections.  In hardware‑in‑the‑loop configurations the `hil.sensor_noise_std` parameter introduces additional noise on the transmitted measurements (default zero).
- **Actuator:** a linear force actuator applies a horizontal force $F$ bounded by $\pm 150\,\text{N}$.  The commanded force is clipped to the `max_force` setting in `config.yaml` and the actuator saturates at that limit.
- **Plant parameters:** the nominal physical constants are taken from the `physics` section of `config.yaml`: cart mass $m_0=1.5\,\text{kg}$, first pendulum mass $m_1=0.2\,\text{kg}$, second pendulum mass $m_2=0.15\,\text{kg}$, lengths $l_1=0.4\,\text{m}$ and $l_2=0.3\,\text{m}$, centre‑of‑mass distances $l_{1,\mathrm{com}}=0.2\,\text{m}$ and $l_{2,\mathrm{com}}=0.15\,\text{m}$, inertias $I_1=2.65\times 10^{-3}\,\text{kg·m}^2$ and $I_2=1.15\times 10^{-3}\,\text{kg·m}^2$, gravitational acceleration $g=9.81\,\text{m/s}^2$, and viscous friction coefficients $b_c=0.2$, $b_1=0.005$ and $b_2=0.004$【359986572901373†screenshot】.  These values define the baseline simulation model.  Photographs or diagrams illustrating the apparatus can be placed in the `img/` folder.

## 2.2 Constraints & disturbances

Particle Swarm Optimisation (PSO) explores bounded ranges for key physical parameters and controller settings.  The bounds below are defined explicitly in the `pso.tune` section of `config.yaml` and arise from engineering judgement and physical feasibility for each parameter; they are **not** uniform percentage offsets.  Refer to `config.yaml` for the authoritative minimum and maximum values used during tuning.

| Parameter            | Min Value | Max Value | Unit | Description                                          |
|----------------------|-----------|-----------|------|------------------------------------------------------|
| cart_mass            | 1.0       | 2.0       | kg   | Cart mass subjected to tuning                        |
| pendulum1_mass       | 0.1       | 0.3       | kg   | Mass of the first pendulum                           |
| pendulum2_mass       | 0.1       | 0.2       | kg   | Mass of the second pendulum                          |
| pendulum1_length     | 0.3       | 0.5       | m    | Length of the first pendulum                         |
| pendulum2_length     | 0.2       | 0.4       | m    | Length of the second pendulum                        |
| pendulum1_com        | 0.15      | 0.25      | m    | Centre‑of‑mass distance of the first pendulum        |
| pendulum2_com        | 0.10      | 0.20      | m    | Centre‑of‑mass distance of the second pendulum       |
| pendulum1_inertia    | 0.0015    | 0.004     | kg·m² | Inertia of the first pendulum about the pivot        |
| pendulum2_inertia    | 0.0005    | 0.002     | kg·m² | Inertia of the second pendulum about the pivot       |
| boundary_layer       | 0.01      | 0.05      | –    | Width of the sliding‑mode boundary layer (ε), dimensionless |
| max_force            | 150       | 150       | N    | Actuator saturation limit (fixed at 150 N in the configuration) |
| cart_friction        | 0.1       | 0.5       | –    | Viscous friction coefficient for the cart            |
| joint1_friction      | 0.001     | 0.01      | –    | Friction coefficient for the first joint             |
| joint2_friction      | 0.001     | 0.01      | –    | Friction coefficient for the second joint            |

These bounds are taken directly from the `pso.tune` section of
`config.yaml` and define the domain explored by the PSO when physical
parameters are tuned alongside controller gains.  They are not uniform
percentages but reflect plausible engineering ranges for each
quantity.  Each parameter is sampled uniformly within its min/max
values when tuning is enabled.

Other sources of disturbance include quantisation noise arising from the
finite resolution of the sensors, additive measurement noise specified in
the `sensors` section of `config.yaml`, unmodelled higher‑order dynamics
and external perturbations.  In the default configuration the angle
measurements are quantised with a step size of **0.01 rad** and the
position measurement is quantised with a step size of **0.0005 m**;
these values correspond to `quantization_angle` and
`quantization_position` in `config.yaml`.  Additive measurement noise levels
are defined in the same `sensors` section and are set to **0.005 rad** for
angles and **0.001 m** for position by default, matching the
`angle_noise_std` and `position_noise_std` entries.  Control commands are not
quantised.  The PSO tuner and robustness tests vary these parameters
within the above bounds to assess controller performance under
uncertainty.

## 2.3 Objectives & KPIs

The primary objective is to track a desired cart position while keeping both pendulums upright and using minimal control energy.  Performance is evaluated with the following Key Performance Indicators (KPIs):

- **Settling time** $t_s$ – the time for the cart position to remain within 2 % of the reference; target: $t_s < 2\,\text{s}$ (`KPI‑001`).
- **Overshoot** $M_p$ – maximum overshoot relative to a step change in reference; target: $M_p < 10\%$ (`KPI‑002`).
- **Integral absolute error (IAE)** – the integral of the absolute position error over the simulation horizon; this metric should be minimised (`KPI‑003`).
- **Stability margins** – phase margin ≥ 45° and gain margin ≥ 6 dB for the linearised closed loop (`KPI‑004`).

These KPIs link requirements to specific tests as described in `test_protocols.md` and `requirements_traceability.csv`.