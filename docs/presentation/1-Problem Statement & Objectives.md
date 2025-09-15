## Problem Statement for Double‑Inverted Pendulum (DIP) Control with SMC and PSO

### 1 Background and Challenges

The double‑inverted pendulum (DIP) mounted on a cart is a benchmark under‑actuated mechanical system with three degrees of freedom (the cart position and the angles of two pendulums) but only one control input. The system’s nonlinear equations of motion include significant coupling between the pendulums and the cart, and the upper “inverted” configuration is naturally unstable. Recent literature emphasises that nonlinear, unstable or under‑actuated systems are very difficult to control; they are primarily studied to test control algorithms rather than for practical utility 

``` math
1
```

. The DIP consists of a cart driven by a single actuator and two pendulums connected by a rotational linkage 

``` math
1
```

. The cart input must simultaneously regulate three states, so the system is under‑actuated and highly nonlinear. Consequently the model has one challenging equilibrium (the fully inverted position) which cannot be maintained without control 

``` math
1
```

.

Classical controllers (e.g., PID or linear quadratic regulators) have been applied to the inverted pendulum, but their performance degrades severely when faced with nonlinear dynamics, parametric variations or disturbances. A recent study on inverted‑pendulum disturbance reduction notes that the system is “nonlinear, unstable and under‑actuated” and that PID controllers tuned around a nominal operating point cannot handle uncertainties or unpredictable disturbances; the robustness decreases as parametric and structural uncertainties increase 

``` math
2
```

. Even state‑feedback and LQR designs fail to stabilise the DIP when model uncertainty and external disturbances are present 

``` math
2
```

. This motivates the use of more robust nonlinear control laws.

To address model uncertainty and facilitate controller development, this project provides two physics models: a simplified dynamics implementation (`src/core/dynamics.py`) for rapid gain tuning and a high‑fidelity model (`src/core/dynamics_full.py`) derived from the full Lagrangian. Controllers can be tuned quickly on the simplified model and then validated on the high‑fidelity model, ensuring that algorithms generalise beyond the idealised dynamics. The project also exposes both a command‑line interface (`simulate.py`) and an interactive Streamlit dashboard (`streamlit_app.py`), allowing users to configure simulations, run optimisation routines, visualise trajectories and verify the challenges described above without modifying code.

### 2 Sliding‑Mode Control (SMC) and Its Limitations

Sliding‑mode control (SMC) is a discontinuous control technique that forces the system trajectory onto a user‑defined sliding surface and keeps it there through a high‑frequency switching control law 

``` math
3
```

. This control law uses a discontinuous sign function, driving the state toward the sliding surface via rapid switching, which leads to the well‑known chattering phenomenon described below. Compared with linear or adaptive controllers, SMC is attractive because it offers robustness to parameter variations and external disturbances 

``` math
3
```

; once the system’s state reaches the sliding surface the dynamics become insensitive to interactions, disturbances or model variations, and an accurate plant model is unnecessary 

``` math
3
```

. For under‑actuated mechanical systems, SMC can handle coupling, non‑holonomic constraints and unknown payloads because only the bounds of the uncertainties are required 

``` math
3
```

. These features make SMC an excellent candidate for DIP stabilisation.

However, classical SMC suffers from the **chattering problem**: the control law uses a discontinuous sign function that switches at an infinitely high frequency, exciting unmodelled high‑frequency dynamics and causing undesirable oscillations. These oscillations lead to large control torques, mechanical wear, heat losses and reduced tracking accuracy. A review of SMC for under‑actuated systems explains that chattering is a major limitation; to overcome it, Slotine proposed replacing the sign function with a saturation function in a thin boundary layer around the sliding surface 

``` math
4
```

. This “boundary‑layer” approach introduces a continuous control law inside the layer and retains discontinuous control outside. Similarly, a robot‑manipulator study notes that the sign function in classical SMC excites high‑frequency modes and degrades performance; replacing it with smooth functions such as the sigmoid, saturation or hyperbolic tangent reduces chattering 

``` math
5
```

. Although boundary‑layer SMC softens the control signal, it introduces a trade‑off between chattering suppression and tracking accuracy; the size of the boundary layer must be chosen carefully to avoid large steady‑state errors.

Higher‑order SMC techniques address chattering by enforcing a sliding mode not only on the tracking error but also on its derivatives. Among these methods, the **super‑twisting algorithm** (STA) is a second‑order sliding mode that produces continuous control signals and eliminates chattering. Research on robot manipulators shows that replacing conventional SMC with super‑twisting significantly reduces the vibration range and amplitude of the control torque, even in the presence of noise 

``` math
7
```

. The algorithm “twists” both the sliding variable and its derivative, providing smooth control and improved disturbance rejection. A recent survey on adaptive super‑twisting global SMC for flexible manipulators highlights that SMC’s main flaw is chattering and that methods such as super‑twisting sliding mode and higher‑order SMC have been developed to mitigate it 

``` math
8
```

. The super‑twisting controller maintains the finite‑time convergence and robustness of SMC while producing a continuous control signal 

``` math
8
```

.

To explore chattering mitigation and ensure the controller can initialise from a hanging position, this project implements a full suite of controllers in `src/controllers`. In addition to the boundary‑layer and super‑twisting designs, it includes an **adaptive SMC** that updates its switching gains online 

``` math
8
```

, a **hybrid adaptive super‑twisting SMC** that couples the super‑twisting algorithm with adaptive laws for finite‑time convergence, and an **energy‑based swing‑up controller** (`SwingUpSMC`) that injects energy to swing the pendulums upright before handing control to a stabilising SMC. A linear model predictive controller (`MPCController`) is also provided as a baseline. These implementations define the solution space explored in subsequent sections.

### 3 Automated Gain Tuning via Particle Swarm Optimisation (PSO)

The performance of sliding‑mode controllers depends strongly on the choice of sliding‑surface coefficients and switching gains. Traditionally these gains are selected through trial and error, which is time consuming and may not yield optimal performance. Particle swarm optimisation (PSO) is a population‑based stochastic optimisation algorithm inspired by the social behaviour of bird flocking or fish schooling 

``` math
6
```

. Each particle in the swarm represents a candidate solution (e.g., a set of controller gains) and adjusts its position and velocity based on its own experience and that of its neighbours 

``` math
6
```

. PSO requires no gradient information and can handle continuous, discrete or non‑differentiable objective functions; it has been widely applied to tune controller parameters in nonlinear control problems 

``` math
6
```

. A study on PSO‑optimised sliding‑mode control notes that PSO is particularly effective at finding global optima for nonlinear, high‑dimensional problems and has better convergence properties than other evolutionary algorithms 

``` math
5
```

. The PSO algorithm iteratively updates the particles’ velocities as a combination of inertial motion, a cognitive component driving the particle toward its own best position and a social component driving it toward the global best 

``` math
6
```

. Because PSO is derivative‑free and easily parallelisable, it is well suited to the automated tuning of SMC gains.

A key feature of the PSO tuner (`src/optimizer/pso_optimizer.py`) in this project is its ability to perform **robust optimisation**. When the `physics_uncertainty` section of `config.yaml` is enabled, each candidate gain vector is evaluated not only on the nominal physics but also on multiple perturbed models in which masses, lengths, inertias and friction coefficients are randomly varied within specified percentages. The tuner aggregates the costs across these models, so the optimal gains minimise error and control effort over a distribution of dynamics. This ensures that the final gains are resilient to real‑world parametric uncertainty and improves the reliability of the resulting controllers.

### 4 Problem Definition and Objectives

1.  **Design and optimise robust control strategies.** The overarching goal is to design, implement and optimise nonlinear controllers for the double‑inverted pendulum that mitigate chattering and eliminate tedious manual tuning. This goal is broken down into the following sub‑objectives:

2.  **Implement a suite of nonlinear controllers.** The project implements and compares the following controllers:

    1.  **Classical SMC with a boundary layer** – implemented in `classic_smc.py`, this controller replaces the discontinuous sign function with a smooth saturation (or tanh) function to reduce chattering 

    - 
      ``` math
      4
      ```
      .

    2.  **Super‑twisting SMC** – a second‑order sliding‑mode controller (`sta_smc.py`) that produces continuous control signals and provides finite‑time convergence while eliminating chattering 

    - 
      ``` math
      7
      ```
      ``` math
      8
      ```
      .

    3.  **Adaptive SMC** – implemented in `adaptive_smc.py`, this controller adjusts its switching gains online to handle parametric uncertainties and unknown payloads 

    - 
      ``` math
      8
      ```
      .

    4.  **Hybrid adaptive super‑twisting SMC** – `hybrid_adaptive_sta_smc.py` combines the super‑twisting algorithm with adaptive gain laws, ensuring finite‑time convergence, smooth control and robustness to modelling errors.
    5.  **Energy‑based swing‑up SMC** – the `SwingUpSMC` controller in `swing_up_smc.py` uses an energy‑based law to swing the pendulums upright from the hanging configuration and hands off to a stabilising SMC once the angles are within tolerance, enabling recovery from arbitrary initial conditions.
    6.  **Model predictive controller (optional)** – `mpc_controller.py` provides a linear MPC baseline for comparison.

3.  **Automate gain tuning with PSO.** The PSO algorithm searches over sliding‑surface coefficients and switching gains to minimise objectives such as the integral absolute error and control effort 

- 
  ``` math
  5
  ```
  ``` math
  6
  ```
  . Hyper‑parameters of the PSO (inertia, cognitive and social weights) are tuned automatically, and the tuner supports robust optimisation by evaluating candidates on multiple perturbed models as described above.

4.  **Validate controllers on multiple dynamics models.** Controllers tuned on the simplified model are validated on the high‑fidelity model (`dynamics_full.py`) to assess performance under more realistic dynamics. Disturbance rejection and noise robustness are also evaluated.

5.  **Provide interactive user interfaces.** A command‑line interface (`simulate.py`) allows batch simulations and data export, while the Streamlit dashboard (`streamlit_app.py`) enables users to modify configuration parameters, run the PSO tuner, visualise trajectories and compute performance metrics interactively. These tools facilitate reproducible experimentation and make the algorithms accessible to practitioners.

6.  **Develop an integrated system for experimentation and reliability.**

7.  **Fault Detection and Isolation (FDI).** The `FDIsystem` in `src/fault_detection/fdi.py` compares one‑step model predictions with measured states and monitors a residual norm. When the residual exceeds a threshold for a specified number of consecutive steps, the system flags a fault. The FDI module records residual histories for later analysis and can be extended to incorporate innovations from an extended Kalman filter.

8.  **Hardware‑in‑the‑loop (HIL) simulation.** The `src/hil` package implements a UDP‑based plant server (`plant_server.py`) and controller client (`controller_client.py`) that communicate over a network. The plant server integrates the pendulum dynamics (light or full) and returns sensor measurements, optionally with latency and noise, while the controller client runs one of the controllers and sends control commands. This infrastructure enables closed‑loop experiments with remote simulators or physical hardware and bridges the gap between software simulations and real‑world deployment.

### 5 Expected Contributions

- **Comprehensive characterisation of the DIP control problem.** This report details why the double‑inverted pendulum is under‑actuated, nonlinear and naturally unstable and summarises the limitations of classical linear controllers 

&nbsp;

- 
  ``` math
  1
  ```
  ``` math
  2
  ```
  .

&nbsp;

- **Dual‑model simulation framework.** By providing both a simplified dynamics model (`dynamics.py`) for rapid experimentation and a high‑fidelity model (`dynamics_full.py`) for validation, the project offers a realistic yet efficient environment for controller design.

- **Implementation of a rich set of controllers.** Classical SMC with boundary layers, super‑twisting SMC, adaptive SMC, hybrid adaptive super‑twisting SMC, an energy‑based swing‑up controller and a linear MPC baseline are implemented. These controllers can be compared systematically to evaluate chattering reduction, robustness and energy efficiency.

- **Robust PSO‑based gain tuning.** The PSO tuner automates the selection of sliding‑surface and switching gains, performs hyper‑parameter searches and supports robust optimisation across multiple perturbed physics models defined in `config.yaml`, yielding gains that perform well under parametric uncertainty 

&nbsp;

- 
  ``` math
  5
  ```
  ``` math
  6
  ```
  .

&nbsp;

- **User‑friendly interfaces and tooling.** Command‑line and Streamlit interfaces simplify simulation, tuning and visualisation, while benchmarking scripts and notebooks provide reproducible experiments.

- **Fault detection and hardware‑in‑the‑loop capabilities.** The FDI module enables monitoring of residuals for anomaly detection, and the HIL client/server infrastructure permits testing controllers with networked plants or physical devices, expanding the applicability of the controllers beyond simulations.

- **Comprehensive evaluation and analysis.** The controllers are evaluated on high‑fidelity models with disturbances, measurement noise and parameter uncertainty; metrics such as tracking error, control effort, chattering amplitude and settling time are reported to identify trade‑offs between robustness and chattering mitigation.

### 6 References

1. Al Juboori, A.M., Hussain, M.T., & Guler Qanber, A.S., “Swing‑up control of double‑inverted pendulum systems,” *Nonlinear Systems* (2024).  
2. Osman, N., et al., “Inverted pendulum system disturbance and uncertainty effects reduction using sliding mode‑based control design,” *Proc. SSD 2021*.  
3. Belhocine, M., Hamerlain, M., & Bouyoucef, K., “Robot control using a sliding mode,” *ISIC 1997*.  
4. Idrees, M., Ullah, S., & Muhammad, S., “Sliding mode control design for stabilization of underactuated mechanical systems,” *J. Control Theory Appl.*, 2019.  
5. Saidi, K., Boumediene, A., & Massoum, S., “An optimal PSO‑based sliding‑mode control scheme for the robot manipulator,” *Electrotechnical Review*, 2020.  
6. Benuwa, B.B., Ghansah, B., Wornyo, D.K., & Adabunu, S.A., “A comprehensive review of particle swarm optimization,” *Int. J. Eng. Res. Afr.*, 2016.  
7. Nguyen, T.L., & Vu, H.T., “Super‑twisting sliding mode based nonlinear control for planar dual arm robots,” *IAES Int. J. Robot. Autom.*, 2020.  
8. Lochan, K., Seneviratne, L., & Hussain, I., “Adaptive global super‑twisting sliding mode control for trajectory tracking of two‑link flexible manipulators,” *IEEE Access*, 2025.

------------------------------------------------------------------------

------------------------------------------------------------------------
