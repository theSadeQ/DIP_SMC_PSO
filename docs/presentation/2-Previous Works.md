# Previous Work Before the Project

This document synthesises pre‑project research on sliding‑mode control (SMC) and optimisation for a double‑inverted pendulum (DIP). It combines insights extracted from the project’s source code with a detailed review of recent literature. Throughout, references are cited using the numerical style and a full list is provided at the end.

## 1 Architectural Overview

### 1.1 Controller subsystem (`src/controllers`)

The project contains several controllers implementing different variants of sliding‑mode control and other strategies. A **factory** (`factory.py`) maps a descriptive name to the appropriate class. It performs tolerant imports (first attempting to import from a top‑level `controllers` namespace and falling back to `src.controllers`) and validates configuration keys and gain lists. It also centralises common parameter checks (e.g., boundary‑layer positivity, horizon integer checking for model‑predictive control) to ensure that incorrect configurations are caught early.

The controllers are implemented as follows:

- `classic_smc.py` **– Classical SMC.** The controller constructs a linear sliding surface

``` math
\sigma = \lambda_{1}\theta_{1} + \lambda_{2}\theta_{2} + k_{1}{\dot{\theta}}_{1} + k_{2}{\dot{\theta}}_{2},
```

where \$(\theta\_{1},\theta\_{2})\$ are the pendulum angles and \$\dot{\theta}\_{i}\$ their velocities. The equivalent control term is computed by inverting the system’s inertia matrix and compensating Coriolis and gravity terms (functions provided by `src/core/dynamics.py`). A discontinuous **robust term** uses a sign or saturation function to counteract uncertainties: `u_robust = -K\,\mathrm{sat}(\sigma/\varepsilon) - k_d \sigma`. The control output is clipped to the actuator limit (`max_force`). This implementation prioritises robustness but results in significant chattering, consistent with classical SMC theory.

- `sta_smc.py` **– Super‑twisting SMC.** This file implements the *super‑twisting algorithm*, a second‑order sliding‑mode controller. It defines the same sliding surface but applies a continuous control law

``` math
u = u_{eq} - k_{1}|\sigma|^{1/2}sat(\sigma/\varepsilon) - k_{2}z,
```

where \$z\$ is an integral of \$\mathrm{sign}(\sigma)\$ and \$k_1, k_2\$ are gains. A damping gain may be added to the sliding surface. Because the discontinuous sign function is integrated, the resulting control signal is continuous and reduces chattering. The project supports toggling the equivalent control and adjusting the integration method (semi‑implicit or explicit).

- `adaptive_smc.py` **– Adaptive SMC.** The adaptive controller extends classical SMC by introducing an adaptive switching gain \$K\$. In the `compute_control` method the gain is updated according to

``` math
\dot{K} = \gamma\,|\sigma| - \alpha\,\left( K - K_{init} \right)\quad\quad\text{when }|\sigma| > \text{dead\_zone},
```

and \$\dot{K}= -\alpha\\(K-K\_{\mathrm{init}})\$ inside the dead zone. Here `gamma` and `alpha` are adaptation and leak rates, respectively. This *dead‑zone mechanism* prevents gain wind‑up by halting adaptation when the sliding surface is small. The updated \$K\$ is clamped between `K_min` and `K_max`, and a rate limiter avoids abrupt jumps. The control law thus adapts the switching gain on‑line to maintain robustness while limiting chattering.

- `hybrid_adaptive_sta_smc.py` **– Hybrid STA–adaptive SMC.** This advanced controller combines super‑twisting control with adaptive gains. It maintains two adaptive gains \$k_1\$ (associated with the square‑root term) and \$k_2\$ (associated with the integral term). The adaptation laws are similar to the single‑gain case but applied separately. A PD term penalises cart displacement to keep the cart centred. Inside the `compute_control` method the sliding surface is computed, dead‑zone conditions are checked, and integrals are updated. The hybrid controller aims to achieve finite‑time convergence and low chattering by blending continuous control with adaptive robustness.

- **Other controllers.** `mpc_controller.py` implements a model‑predictive controller for reference tracking. `swing_up_smc.py` uses an energy‑based strategy to swing the pendulum upright before handing control to a stabilising SMC. These are beyond the scope of this review but illustrate the modularity of the controller subsystem.

### 1.2 Core subsystem (`src/core`)

The **core** module encapsulates the physical model and simulation routines:

- `dynamics.py` defines a simplified double‑inverted pendulum model. It computes inertia, Coriolis and gravity matrices from physical parameters, implements friction terms and integrates the equations of motion using a fixed‑step Runge–Kutta 4 solver. The file also defines `DIPParams`, a data class representing the physical parameters.

- `dynamics_full.py` extends the model with additional nonlinearities (e.g., dynamic friction and mass distributions) to match high‑fidelity dynamics. The selection between `dynamics.py` and `dynamics_full.py` is controlled by the configuration file (`use_full_dynamics`).

- `simulation_context.py` loads the validated configuration via `load_config`, selects the appropriate dynamics model and uses the controller factory to instantiate controllers. It hides details about physics selection and provides accessors `get_dynamics_model` and `create_controller`.

- `simulation_runner.py` orchestrates simulations. It determines the number of integration steps deterministically by rounding the desired simulation time to an integer multiple of the time step, ensuring that the actual simulation duration matches the configuration. The runner injects faults (sensor freeze or actuator stuck) via a `FaultInjector`, calls the controller’s `compute_control` at each step, and accumulates time, state and control histories. By explicitly computing the number of steps and using consistent seeds for any randomness, the runner ensures that repeated simulations with the same configuration produce identical results.

- `vector_sim.py` (used by the optimizer) performs batch simulations of many particles in parallel. It leverages NumPy array operations to evaluate hundreds of candidate gain sets simultaneously.

### 1.3 Optimizer subsystem (`src/optimizer`)

The project uses **Particle Swarm Optimization (PSO)** to tune controller gains. The class `PSOTuner` in `pso_optimizer.py` accepts a controller factory and a configuration object. Key features include:

- **Seeding and determinism.** The constructor records a global seed from the configuration (`global_seed`) or an explicit argument. During optimisation the internal RNG is reset to this seed before generating perturbed physics models or drawing random numbers. A context manager (`_seeded_global_numpy`) temporarily sets NumPy’s global seed. These measures ensure that PSO runs are reproducible.

- **Robust optimisation.** The method `_iter_perturbed_physics` yields a sequence of physical parameter sets: the nominal parameters followed by random perturbations sampled within ±5 % of nominal values (the ranges come from `physics_uncertainty.n_evals` and other fields). For each candidate controller, the cost function simulates the system under each perturbed model and combines costs using a convex combination (70 % mean, 30 % max) to penalise worst‑case performance. This robust sampling encourages gains that perform well across model uncertainties.

- **Cost components and normalization.** The cost function weights tracking error, control effort, control rate and sliding surface magnitude. Normalisation functions avoid divide‑by‑zero errors and apply penalties if trajectories contain NaNs or if the controller becomes unstable. Vectorised batch simulations allow evaluating many particles per PSO iteration efficiently.

### 1.4 Hardware‑in‑the‑Loop and tests

The `hil` directory contains `plant_server.py` and `controller_client.py`, which implement a network interface between the simulated/physical plant and the controller. The client sends computed control commands and receives sensor measurements. The plant may run in simulation or on actual hardware. The HIL interface includes safety features such as saturating commands and falling back to a PD controller during communication failures.

The `tests` directory includes unit and integration tests covering controllers, dynamics, the factory, and the optimizer. Of particular importance are tests for **determinism** (`tests/test_optimizer/test_cli_determinism.py`) that verify repeated PSO runs yield identical results and tests for **fault injection**.

### 1.5 Configuration (`config.yaml`)

The configuration file defines physical parameters, default controller gains, simulation parameters and PSO settings. For instance, the **PSO** section specifies `n_particles=20`, cognitive and social coefficients `c1` and `c2` both set to 2.0, inertia weight `w=0.7`, and iteration count `iters=200`. The file also configures the number of robust samples (`physics_uncertainty.n_evals=10`), the time step (`dt=0.01`) and the `global_seed=42`. Controller sections provide boundaries for gains (e.g., `K_min` and `K_max` in adaptive SMC), adaptation rates (`gamma1`, `gamma2` in hybrid STA–adaptive SMC), dead‑zone widths and boundary layers. The **hybrid STA–adaptive SMC** configuration maps directly to the theoretical formulation of the hybrid super‑twisting controller and ensures that the sliding surface and adaptation laws match the design. By centralising parameters in `config.yaml`, the project enables reproducible experiments and systematic tuning.

## 2 Controller Implementation Analysis

This section analyses each controller’s implementation in relation to sliding‑mode theory and references recent research.

### 2.1 Classical SMC

The classical SMC implements a first‑order sliding surface and a discontinuous control. In `classic_smc.py`, the equivalent control is obtained by inverting the inertia matrix and subtracting the Coriolis and gravity vectors. The robust term uses `sat(\sigma/\epsilon)`; the `boundary_layer` parameter sets the width of the saturation region. Gains `(k_1,k_2,\lambda_1,\lambda_2,K,k_d)` are read from the configuration or provided explicitly. The `saturate` function prevents division by zero when the boundary layer is extremely small. Control outputs are limited to `±max_force`.

Classical SMC offers strong robustness against matched uncertainties but suffers from high‑frequency chattering. Researchers continue to refine classical SMC using adaptive laws and disturbance observers. For example, recent work on permanent‑magnet synchronous motors introduces a **full‑order adaptive SMC with an extended state observer**; the controller adapts the switching gain through a law that minimises chattering while maintaining robustness, and the observer estimates disturbances that are compensated in the control law[\[1\]](https://www.nature.com/articles/s41598-023-33455-x#:~:text=In%20order%20to%20achieve%20speed,been%20validated%20in%20the%20test). Although this project’s implementation does not include an observer, the adaptation and observer ideas are relevant when considering future extensions.

### 2.2 Super‑twisting (STA) SMC

`sta_smc.py` implements the super‑twisting algorithm (STA), a high‑order sliding‑mode method that achieves continuous control and finite‑time convergence. The algorithm updates an auxiliary state variable `z` (the integral of the sign function) and computes the control as `-k1*np.sqrt(abs(sigma))*np.sign(sigma) - k2*z` plus an optional equivalent control. Damping and boundary‑layer parameters help adjust convergence speed and reduce chattering.

Recent literature reports that **super‑twisting algorithms** mitigate chattering while retaining robustness. In a 2024 study on quadrotor control, an improved *nonsingular adaptive super‑twisting sliding mode controller* uses the super‑twisting algorithm and optimises the gains using particle swarm optimization (PSO)[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11466434/#:~:text=This%20paper%20presents%20an%20improved,Simulation%20results%20demonstrate). The authors design an adaptive law based on Lyapunov stability to adjust the gains, ensuring that the controller can reject unknown disturbances. Simulation results show that PSO‑tuned super‑twisting controllers reduce tracking errors and effectively reject disturbances[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11466434/#:~:text=This%20paper%20presents%20an%20improved,Simulation%20results%20demonstrate). This aligns with the project’s hybrid STA–adaptive controller, where adaptive gains and PSO tuning are used to improve performance.

### 2.3 Adaptive SMC

The adaptive SMC adjusts the switching gain on‑line. In `adaptive_smc.py`, the `compute_control` method calculates the sliding surface and updates the gain \$K\$ based on the magnitude of \$\sigma\$. The adaptation law uses a **dead‑zone**: if \$\|\sigma\|\leq \text{dead_zone}\$, the gain decays towards its initial value at rate `leak_rate`; if \$\|\sigma\|\$ is large, the gain grows proportionally to `adapt_rate`, but the growth is limited by `adapt_rate_limit` and clamped between `K_min` and `K_max`. A leak term prevents wind‑up and resets the gain when the system nears the sliding surface.

Adaptive SMC techniques aim to reduce chattering by adjusting gains according to system states. An illustrative example is the **full‑order adaptive SMC with extended state observer** for high‑speed motor drives[\[1\]](https://www.nature.com/articles/s41598-023-33455-x#:~:text=In%20order%20to%20achieve%20speed,been%20validated%20in%20the%20test): the switching gain adaptation law minimises chattering, and an extended state observer estimates disturbances for compensation, enhancing anti‑disturbance capability. Another trend is to combine adaptive SMC with higher‑order methods, as in the project’s hybrid controller.

### 2.4 Hybrid STA–adaptive SMC

The hybrid controller merges super‑twisting dynamics and adaptive gain adaptation. In `hybrid_adaptive_sta_smc.py`, the sliding surface is formed using gains `c1, c2, lambda1, lambda2`. Two adaptive gains `k1` and `k2` are updated based on the sliding surface: `k1` growth is driven by `gamma1*|sigma|` outside a dead zone and decays otherwise; `k2` follows a similar law with rate `gamma2`. The control law combines an STA term (`-k1*sqrt(|sigma|)*sat(sigma)`), an integral term using `k2` and an integral state `u_int`, and a PD term that penalises cart displacement. The adaptation ensures that the gains increase when errors are large and decrease when the system is near the sliding surface. The file also enforces rate limits and clamps to prevent unbounded growth.

Hybrid STA–adaptive controllers integrate features from multiple SMC formulations. Recent research demonstrates that **hybrid methods** can achieve finite‑time convergence and robustness. For example, combining STA with adaptive gain laws and PSO tuning improved quadrotor control performance in the PLoS One study[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11466434/#:~:text=This%20paper%20presents%20an%20improved,Simulation%20results%20demonstrate). Future work could formalise stability proofs for such hybrid systems and explore more sophisticated adaptation laws.

## 3 Optimization Engine Breakdown

The PSO tuner implements robust optimisation and deterministic sampling. PSO parameters (e.g., `n_particles`, `w`, `c1`, `c2`) are defined in `config.yaml`. The algorithm iteratively updates particle positions (candidate gain vectors) based on local and global best positions, weighting inertia, cognitive and social components. Key implementation aspects include:

- **Robust sampling via** `_iter_perturbed_physics`**.** Before computing a cost, the tuner yields the nominal physics parameters and several perturbed sets. For each candidate, the system is simulated under each perturbation using `vector_sim.py`. Costs are aggregated using 0.7 mean + 0.3 max to penalise outliers. Perturbations ensure that tuned gains generalise to model uncertainties.

- **Cost computation and penalties.** The cost function integrates squared tracking error, squared control effort, and squared control rate, weighted by `weights.state_error`, `weights.control_effort` and `weights.control_rate`. If simulation trajectories contain NaNs or the system diverges, a large penalty `instability_penalty` is applied. Normalisation prevents dividing by small numbers.

- **Determinism.** The tuner stores a seed and uses a local random number generator (`rng = np.random.default_rng(seed)`). Before generating perturbations, it resets the RNG to this seed, ensuring that each call to the cost function yields the same sequence of perturbations. Combined with deterministic integration in `simulation_runner.py`, this guarantees reproducible optimisation results.

- **PSO hyper‑parameter search.** The configuration includes a `hyper_search` sub‑section specifying ranges for inertia and acceleration coefficients. The script `reoptimize_controllers.py` performs random searches over these ranges to find meta‑parameters that improve convergence. The PSO tuner can thus be used hierarchically: meta‑optimization tunes PSO parameters, which in turn tune controller gains.

## 4 Innovations in Sliding‑Mode Control Formulations

The project implements classical and high‑order SMC controllers. Recent literature has proposed several innovations that extend these formulations.

### 4.1 High‑order and Super‑twisting Methods

High‑order sliding‑mode control (HOSM) achieves finite‑time convergence with continuous control. The **super‑twisting algorithm** implemented in the project is a second‑order HOSM method. Recent work has extended it further: the PLoS One study on quadrotor control proposes a **nonsingular adaptive super‑twisting controller** tuned via PSO. The controller combines an adaptive law that adjusts gains based on the sliding surface and a super‑twisting term. Simulations demonstrate improved disturbance rejection and smaller tracking errors[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11466434/#:~:text=This%20paper%20presents%20an%20improved,Simulation%20results%20demonstrate). These results motivate using adaptive HOSM with metaheuristic optimisation in other systems such as the DIP.

### 4.2 Terminal and Prescribed‑Performance SMC

**Terminal sliding‑mode control (TSMC)** uses nonlinear sliding surfaces to achieve finite‑time convergence. A recent open‑access article designs a **prescribed‑performance non‑singular fast terminal sliding mode (PPNFTSM) controller** for robotic manipulators[\[3\]](https://jeas.springeropen.com/articles/10.1186/s44147-024-00553-0#:~:text=Considering%20the%20improvement%20of%20transient,performance%20and%20strong%20robust%20performance). The controller introduces performance functions with constraint effects, transforms the tracking error using a hyperbolic tangent, designs a new error performance index, and combines the resulting variable with a non‑singular fast terminal sliding‑mode term. Stability is proven via Lyapunov functions, and simulations show that tracking deviations approach a delimited region with prescribed transient performance and strong robustness without requiring an initial tracking condition[\[3\]](https://jeas.springeropen.com/articles/10.1186/s44147-024-00553-0#:~:text=Considering%20the%20improvement%20of%20transient,performance%20and%20strong%20robust%20performance). Integrating such PPNFTSM surfaces into the DIP controller could yield faster convergence and improved transient performance.

### 4.3 Integral and Dynamic Integral SMC

**Integral sliding‑mode control (ISMC)** eliminates the reaching phase by adding an integral of the error to the sliding surface. A recent Science Progress paper proposes a **dynamic integral sliding mode control** (DISMC) for power electronic converters[\[4\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10450744/#:~:text=for%20power%20electronic%20converters%2C%20which,cost%2C%20conversion%20speed%20and%20implementation). The dynamic integral sliding manifold eliminates the reaching phase and reduces matched and unmatched uncertainties, producing a continuous control signal suitable for pulse‑width modulation. The authors combine dynamic and integral SMC to provide a smooth control signal and robust performance[\[5\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10450744/#:~:text=In%20this%20section%2C%20the%20design,achieve%20the%20required%20performance%20and). Adapting a dynamic integral sliding surface to the DIP could improve chattering behaviour and robustness from the initial time.

### 4.4 Hierarchical Sliding‑Mode Control

**Hierarchical sliding‑mode control (HSMC)** constructs multiple sliding surfaces in a hierarchical structure, enabling control of underactuated systems. In a recent hierarchical SMC for a rotary inverted pendulum, the authors design separate sliding surfaces for the underactuated angles and use PSO to tune controller gains. Their results show that PSO‑tuned hierarchical SMC improves adaptability and robustness, successfully swinging up and stabilising the pendulum[\[6\]](https://www.researchgate.net/publication/382125063_Optimized_Hierarchical_Sliding_Mode_Control_for_the_Swing-up_and_Stabilization_of_a_Rotary_Inverted_Pendulum#:~:text=This%20paper%20presents%20a%20study,of%20combining%20optimization%20algorithms%20with). Integrating hierarchical sliding surfaces into the DIP controller could handle underactuation and improve energy efficiency.

## 5 Advancements in Metaheuristic Optimisation for SMC Parameter Tuning

Metaheuristic algorithms automate controller tuning by searching high‑dimensional parameter spaces. The project employs standard PSO; recent research explores hybrid and enhanced variants.

### 5.1 Hybrid PSO and Enhanced PSO

Hybrid PSO variants incorporate mechanisms such as inertia weight adaptation, genetic crossover or elitism to improve convergence. A 2024 study proposes a **hybrid enhanced PSO (HEPSO)‑SMC** for manipulators, combining PSO with adaptive inertia weights, uniform distribution factors and golden search to avoid local minima. While the full article is not reproduced here, such hybrids generally yield faster convergence and better robustness. Applying HEPSO to tune the DIP controllers could reduce the computational cost of optimisation.

### 5.2 PSO‑tuned Super‑twisting SMC – A Concrete Example

The PLoS One paper on quadrotor control provides a concrete example of PSO‑tuned SMC. The authors use PSO to optimise the gains of a nonsingular adaptive super‑twisting controller. Their PSO parameters include population size, inertia, cognitive and social coefficients, and they minimise a cost combining tracking errors and control effort. The resulting controller exhibits improved tracking accuracy and disturbance rejection compared with manual tuning[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11466434/#:~:text=This%20paper%20presents%20an%20improved,Simulation%20results%20demonstrate). This demonstrates that PSO can effectively tune high‑order SMC controllers in practice.

### 5.3 PSO‑tuned Hierarchical SMC

In the hierarchical SMC for rotary inverted pendulum, PSO is used to tune multiple layers of sliding surfaces. The method defines separate sliding surfaces for the underactuated dynamics and applies PSO to optimise the gains associated with each surface. The authors report that PSO‑tuned hierarchical SMC enhances adaptability and robustness, making it well suited for swing‑up and stabilisation tasks[\[6\]](https://www.researchgate.net/publication/382125063_Optimized_Hierarchical_Sliding_Mode_Control_for_the_Swing-up_and_Stabilization_of_a_Rotary_Inverted_Pendulum#:~:text=This%20paper%20presents%20a%20study,of%20combining%20optimization%20algorithms%20with). This illustrates the effectiveness of PSO in tuning complex sliding‑mode structures.

## 6 Intelligent and Adaptive SMC for Dynamic Environments

Recent research integrates artificial intelligence techniques with SMC to handle dynamic environments and unknown nonlinearities.

### 6.1 Fuzzy Logic in SMC

Fuzzy logic can approximate unknown functions and tune switching surfaces. A 2021 PLoS One article develops **fractional and integral order fuzzy sliding mode controllers** for a skid‑steered vehicle subject to friction variations[\[7\]](https://journals.plos.org/plosone/article#:~:text=caused%20by%20wheel,minimized%20by%20fuzzy%20tuning%20approach). The fuzzy controller reduces the effect of ground–tire interaction and minimises chattering by adjusting the switching function. Simulations show that fuzzy sliding‑mode controllers reduce state errors and chattering compared with conventional SMC[\[7\]](https://journals.plos.org/plosone/article#:~:text=caused%20by%20wheel,minimized%20by%20fuzzy%20tuning%20approach). Incorporating fuzzy logic into the DIP controllers could enhance robustness to friction and parameter variations.

### 6.2 Neural‑network‑based SMC

Neural networks can approximate unknown dynamics and adapt sliding surfaces. A 2025 article introduces a **radial basis function neural network adaptive hierarchical sliding‑mode control (RBFNNA‑HSMC)** for a tendon‑driven manipulator[\[8\]](https://cjme.springeropen.com/articles/10.1186/s10033-024-01172-9#:~:text=Tracking%20control%20of%20tendon,3%7D%20rad). The method combines a high‑fidelity elastic tendon model with radial basis neural network adaptive control and hierarchical sliding‑mode control. Lyapunov analysis demonstrates stability, and simulations and experiments show superior trajectory tracking compared with classical HSMC. The maximum tracking errors in a two‑degree‑of‑freedom manipulator are below \$2.6\times 10^{-3}\\\text{rad}\$[\[8\]](https://cjme.springeropen.com/articles/10.1186/s10033-024-01172-9#:~:text=Tracking%20control%20of%20tendon,3%7D%20rad). This highlights the potential of neural networks to enhance sliding‑mode control for complex manipulators; similar techniques could be applied to the DIP to approximate unmodelled dynamics.

### 6.3 Reinforcement Learning with SMC

Reinforcement learning (RL) offers model‑free adaptation by learning control policies from interactions. A 2024 arXiv preprint proposes an **adaptive integral terminal sliding‑mode controller (AITSM) combined with deep reinforcement learning** for zero‑force control of upper‑limb exoskeleton robots[\[9\]](https://arxiv.org/abs/2407.18309). The controller uses an integral terminal sliding surface to ensure finite‑time convergence and includes an exponential switching term to reduce chattering. A Proximal Policy Optimization (PPO) agent with an attention mechanism and LSTM networks adjusts controller parameters in real time, enabling the system to cope with uncertainties and disturbances. Simulations show that the RL‑enhanced controller achieves robust zero‑force control while reducing chattering[\[9\]](https://arxiv.org/abs/2407.18309). Applying RL to tune sliding‑mode gains in the DIP could enable adaptation to changing dynamics without requiring explicit models.

## 7 Experimental Validation and Practical Insights

While this project focuses on simulation and optimisation, experimental validation is critical. Hardware‑in‑the‑Loop (HIL) testing bridges the gap between simulation and reality. The project’s HIL interface allows the same controller code to run on both simulated and physical plants. During HIL tests the controller must account for sensor noise, communication delays and unmodelled dynamics; observers (e.g., neural networks) and adaptive gains help compensate these effects. Studies on hierarchical SMC for rotary inverted pendulums show that PSO‑tuned sliding‑mode controllers can be successfully implemented on hardware[\[6\]](https://www.researchgate.net/publication/382125063_Optimized_Hierarchical_Sliding_Mode_Control_for_the_Swing-up_and_Stabilization_of_a_Rotary_Inverted_Pendulum#:~:text=This%20paper%20presents%20a%20study,of%20combining%20optimization%20algorithms%20with). Future work should extend the DIP controllers to physical experiments, using the robust optimisation and adaptation techniques described here.

## 8 Synthesis and Recommendations

### 8.1 Key Trends

1.  **Finite‑time convergence and chattering reduction.** High‑order methods such as super‑twisting and terminal sliding mode achieve finite‑time convergence and continuous control, significantly reducing chattering[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11466434/#:~:text=This%20paper%20presents%20an%20improved,Simulation%20results%20demonstrate)[\[3\]](https://jeas.springeropen.com/articles/10.1186/s44147-024-00553-0#:~:text=Considering%20the%20improvement%20of%20transient,performance%20and%20strong%20robust%20performance).

2.  **Adaptive and intelligent tuning.** Adaptive SMC, fuzzy logic, neural networks and reinforcement learning allow controllers to adjust gains or compensate unknown dynamics online. These methods improve robustness and performance in dynamic environments[\[7\]](https://journals.plos.org/plosone/article#:~:text=caused%20by%20wheel,minimized%20by%20fuzzy%20tuning%20approach)[\[8\]](https://cjme.springeropen.com/articles/10.1186/s10033-024-01172-9#:~:text=Tracking%20control%20of%20tendon,3%7D%20rad)[\[9\]](https://arxiv.org/abs/2407.18309).

3.  **Metaheuristic optimisation.** Particle swarm optimisation and its hybrid variants automate tuning of sliding surfaces and gains. Robust sampling and seeding ensure reproducibility and good performance under uncertainty[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11466434/#:~:text=This%20paper%20presents%20an%20improved,Simulation%20results%20demonstrate)[\[6\]](https://www.researchgate.net/publication/382125063_Optimized_Hierarchical_Sliding_Mode_Control_for_the_Swing-up_and_Stabilization_of_a_Rotary_Inverted_Pendulum#:~:text=This%20paper%20presents%20a%20study,of%20combining%20optimization%20algorithms%20with).

4.  **Hierarchical and integral formulations.** Hierarchical SMC and dynamic integral SMC eliminate the reaching phase and handle underactuated dynamics or slow convergence, offering new avenues for robust control[\[6\]](https://www.researchgate.net/publication/382125063_Optimized_Hierarchical_Sliding_Mode_Control_for_the_Swing-up_and_Stabilization_of_a_Rotary_Inverted_Pendulum#:~:text=This%20paper%20presents%20a%20study,of%20combining%20optimization%20algorithms%20with)[\[4\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10450744/#:~:text=for%20power%20electronic%20converters%2C%20which,cost%2C%20conversion%20speed%20and%20implementation).

### 8.2 Research Gaps and Open Questions

- **Stability proofs for hybrid controllers.** Hybrid STA–adaptive controllers combine multiple adaptation laws and high‑order terms; rigorous Lyapunov proofs for such systems are still limited.

- **Sample efficiency and safety in RL.** Reinforcement‑learning‑based SMC requires many interactions and may be unsafe on hardware. Reducing sample requirements and ensuring safe exploration remain open problems.

- **Sim‑to‑real transfer.** Optimisation in simulation may not translate directly to hardware. Domain randomisation, robust optimisation and HIL testing are critical to bridge this gap.

- **Computational complexity.** Higher‑order sliding modes and hybrid metaheuristics increase computational load. Efficient implementations and model reduction techniques are needed for real‑time control on embedded hardware.

### 8.3 Actionable Recommendations

1.  **Explore hierarchical and terminal sliding surfaces for the DIP.** Combining hierarchical sliding surfaces with PPNFTSM or dynamic integral manifolds could yield faster convergence and improved robustness.

2.  **Apply hybrid PSO variants.** Use hybrid PSO (e.g., HEPSO) to tune high‑order and adaptive SMC parameters, balancing exploration and exploitation.

3.  **Integrate intelligent adaptation.** Incorporate fuzzy logic, neural networks or reinforcement learning to adapt switching functions and gains. For example, use an RBF network to estimate unmodelled dynamics and combine it with an adaptive SMC law.

4.  **Pursue experimental validation.** Implement the optimised controllers on physical hardware via the HIL interface. Use domain randomisation and robust tuning to ensure that controllers handle friction, delays and disturbances.

## References

1.  Xin Zhang & Ruikang Wang, “Non‑singular fast terminal sliding mode control of robotic manipulator with prescribed performance,” *Journal of Engineering and Applied Science*, 2024. The paper designs a PPNFTSM controller that introduces performance functions, transforms errors using a hyperbolic tangent and combines them with a non‑singular fast terminal sliding surface. Stability is proven via Lyapunov analysis and simulations show finite‑time convergence and robust performance[\[3\]](https://jeas.springeropen.com/articles/10.1186/s44147-024-00553-0#:~:text=Considering%20the%20improvement%20of%20transient,performance%20and%20strong%20robust%20performance).

2.  Yasir Mehmood *et al.*, “Robust fractional and integral fuzzy sliding mode controller for a skid‑steered vehicle subjected to friction variations,” *PLOS One*, 2021. The authors design fuzzy fractional and integral sliding mode controllers that reduce the effects of friction variations and minimise chattering[\[7\]](https://journals.plos.org/plosone/article#:~:text=caused%20by%20wheel,minimized%20by%20fuzzy%20tuning%20approach).

3.  Yudong Zhang *et al.*, “Neural Network Adaptive Hierarchical Sliding Mode Control for the Trajectory Tracking of a Tendon‑Driven Manipulator,” *Chinese Journal of Mechanical Engineering*, 2025. The paper proposes an RBF neural network adaptive hierarchical SMC method that combines elastic tendon dynamics with hierarchical SMC and radial basis neural networks. Stability is established and experiments demonstrate superior tracking accuracy[\[8\]](https://cjme.springeropen.com/articles/10.1186/s10033-024-01172-9#:~:text=Tracking%20control%20of%20tendon,3%7D%20rad).

4.  Morteza Mirzaee & Reza Kazemi, “Adaptive Terminal Sliding Mode Control Using Deep Reinforcement Learning for Zero‑Force Control of Exoskeleton Robot Systems,” arXiv preprint 2024. The controller combines an adaptive integral terminal sliding surface with an exponential reaching law and a PPO‑based DRL agent with attention and LSTM mechanisms. It achieves finite‑time convergence, reduces chattering and adapts to disturbances[\[9\]](https://arxiv.org/abs/2407.18309).

5.  Xin Zhang *et al.*, “Optimized hierarchical sliding mode control for the swing‑up and stabilisation of a rotary inverted pendulum,” ResearchGate preprint 2024. This work constructs hierarchical sliding surfaces and uses particle swarm optimisation to tune controller gains, achieving improved adaptability and robustness for swing‑up and stabilization[\[6\]](https://www.researchgate.net/publication/382125063_Optimized_Hierarchical_Sliding_Mode_Control_for_the_Swing-up_and_Stabilization_of_a_Rotary_Inverted_Pendulum#:~:text=This%20paper%20presents%20a%20study,of%20combining%20optimization%20algorithms%20with).

6.  Mudasar Riaz *et al.*, “A novel dynamic integral sliding mode control for power electronic converters,” *Science Progress*, 2021. The authors design a dynamic integral sliding manifold that eliminates the reaching phase and provides a continuous control signal. The combination of dynamic and integral SMC yields robust performance and reduces matched and unmatched uncertainties[\[4\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10450744/#:~:text=for%20power%20electronic%20converters%2C%20which,cost%2C%20conversion%20speed%20and%20implementation)[\[5\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10450744/#:~:text=In%20this%20section%2C%20the%20design,achieve%20the%20required%20performance%20and).

7.  An improved nonsingular adaptive super‑twisting sliding mode controller for quadcopter control,” *PLOS One*, 2024. The paper utilises the super‑twisting algorithm with an adaptive gain law and tunes gains via PSO. Simulation results show reduced tracking errors and robust disturbance rejection[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11466434/#:~:text=This%20paper%20presents%20an%20improved,Simulation%20results%20demonstrate).

8.  Zhaolin Huang *et al.*, “Full‑order adaptive sliding mode control with extended state observer for high‑speed PMSM speed regulation,” *Scientific Reports*, 2023. The controller adapts switching gains and uses an extended state observer to estimate disturbances, improving anti‑disturbance capability while reducing chattering[\[1\]](https://www.nature.com/articles/s41598-023-33455-x#:~:text=In%20order%20to%20achieve%20speed,been%20validated%20in%20the%20test).

------------------------------------------------------------------------

[\[1\]](https://www.nature.com/articles/s41598-023-33455-x#:~:text=In%20order%20to%20achieve%20speed,been%20validated%20in%20the%20test) Full-order adaptive sliding mode control with extended state observer for high-speed PMSM speed regulation \| Scientific Reports

<https://www.nature.com/articles/s41598-023-33455-x>

[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11466434/#:~:text=This%20paper%20presents%20an%20improved,Simulation%20results%20demonstrate) An improved nonsingular adaptive super twisting sliding mode controller for quadcopter - PMC

<https://pmc.ncbi.nlm.nih.gov/articles/PMC11466434/>

[\[3\]](https://jeas.springeropen.com/articles/10.1186/s44147-024-00553-0#:~:text=Considering%20the%20improvement%20of%20transient,performance%20and%20strong%20robust%20performance) Non-singular fast terminal sliding mode control of robotic manipulator with prescribed performance \| Journal of Engineering and Applied Science \| Full Text

<https://jeas.springeropen.com/articles/10.1186/s44147-024-00553-0>

[\[4\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10450744/#:~:text=for%20power%20electronic%20converters%2C%20which,cost%2C%20conversion%20speed%20and%20implementation) [\[5\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10450744/#:~:text=In%20this%20section%2C%20the%20design,achieve%20the%20required%20performance%20and) A novel dynamic integral sliding mode control for power electronic converters - PMC

<https://pmc.ncbi.nlm.nih.gov/articles/PMC10450744/>

[\[6\]](https://www.researchgate.net/publication/382125063_Optimized_Hierarchical_Sliding_Mode_Control_for_the_Swing-up_and_Stabilization_of_a_Rotary_Inverted_Pendulum#:~:text=This%20paper%20presents%20a%20study,of%20combining%20optimization%20algorithms%20with) (PDF) Optimized Hierarchical Sliding Mode Control for the Swing-Up and Stabilization of a Rotary Inverted Pendulum

<https://www.researchgate.net/publication/382125063_Optimized_Hierarchical_Sliding_Mode_Control_for_the_Swing-up_and_Stabilization_of_a_Rotary_Inverted_Pendulum>

[\[7\]](https://journals.plos.org/plosone/article#:~:text=caused%20by%20wheel,minimized%20by%20fuzzy%20tuning%20approach) Robust fuzzy sliding mode controller for a skid-steered vehicle subjected to friction variations \| PLOS One

<https://journals.plos.org/plosone/article>

[\[8\]](https://cjme.springeropen.com/articles/10.1186/s10033-024-01172-9#:~:text=Tracking%20control%20of%20tendon,3%7D%20rad) Neural Network Adaptive Hierarchical Sliding Mode Control for the Trajectory Tracking of a Tendon-Driven Manipulator \| Chinese Journal of Mechanical Engineering \| Full Text

<https://cjme.springeropen.com/articles/10.1186/s10033-024-01172-9>

[\[9\]](https://arxiv.org/abs/2407.18309) \[2407.18309\] Adaptive Terminal Sliding Mode Control Using Deep Reinforcement Learning for Zero-Force Control of Exoskeleton Robot Systems

<https://arxiv.org/abs/2407.18309>
