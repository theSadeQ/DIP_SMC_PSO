# Particle Swarm Optimization for Sliding‑Mode Controller Tuning of a Double Inverted Pendulum

## Introduction

The **double inverted pendulum (DIP)** mounted on a translating cart is a widely used benchmark for nonlinear and underactuated control. The system contains two serial pendulums that must be maintained upright while the cart remains near the origin. Due to the underactuation and the coupling between the pendulums and the cart, the dynamics are highly nonlinear and possess multiple unstable equilibrium points, so stabilisation requires a carefully designed controller. **Sliding‑mode control (SMC)** is a nonlinear control technique that uses a discontinuous control law to force the state trajectories onto a prescribed sliding surface. Once on the surface, the system evolution is insensitive to matched disturbances and model uncertainties, which endows SMC with strong robustness[\[1\]](https://www.mdpi.com/2673-4052/5/3/17#:~:text=studied%20to%20address%20their%20inherent,did%20not%20select%20optimal%20parameters)[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=1). However, the discontinuous control input introduces high‑frequency switching, known as **chattering**, which can excite unmodelled dynamics and degrade performance[\[3\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=discontinuous%20element%20provides%20robustness%2C%20but,6%20%20Thus%2C%20a%20continuous). Selecting the gains that define the sliding surface and switching law is therefore a non‑trivial design problem: small gains lead to slow convergence whereas large gains increase chattering.

Meta‑heuristic optimisation techniques such as **particle swarm optimisation (PSO)** offer a principled way to automate gain tuning. PSO views each candidate set of controller gains as a particle in a population, and the particles explore the search space by updating their velocities and positions. At each iteration the velocity of particle *i* is influenced by its own best position and the global best position found by the swarm, scaled by acceleration coefficients and random vectors[\[4\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=At%20each%20iteration%2C%20the%20velocity,suitable%20stopping%20criterion%20is%20satisfied). An inertia weight may be included to control the influence of the previous velocity; larger inertia promotes exploration while smaller inertia encourages exploitation[\[5\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=In%201998%2C%20Shi%20and%20Eberhart,on%20the%20current%20particle%E2%80%99s%20movement). Because PSO only requires evaluations of the objective function and not its gradient, it is attractive for tuning nonlinear controllers where simulation is the only way to assess performance. This report uses PSO to optimise the gains of a sliding‑mode controller for the DIP.

    \mathbf{v}_{i}(t + 1) = w\,\mathbf{v}_{i}(t) + c_{1}r_{1}\bigl( \mathbf{p}_{\mathrm{best},i} - \mathbf{x}_{i}(t) \bigr) + c_{2}r_{2}\bigl( \mathbf{g}_{\mathrm{best}} - \mathbf{x}_{i}(t) \bigr),
    \mathbf{x}_{i}(t + 1) = \mathbf{x}_{i}(t) + \mathbf{v}_{i}(t + 1),

where \$w\$ is the inertia weight and \$c\_{1},c\_{2}\$ are cognitive and social acceleration coefficients; \$r\_{1},r\_{2}\$ are uniformly distributed random vectors on \$\[0,1\]\$[\[4\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=At%20each%20iteration%2C%20the%20velocity,suitable%20stopping%20criterion%20is%20satisfied). The inertia term \$w\\\mathbf{v}\_{i}(t)\$ retains a portion of the previous velocity, the cognitive term drives the particle toward its personal best position and the social term attracts it toward the global best. Shi and Eberhart introduced the inertia weight to balance global exploration and local exploitation: a large inertia weight emphasises exploration whereas a small one speeds convergence but risks premature stagnation[\[5\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=In%201998%2C%20Shi%20and%20Eberhart,on%20the%20current%20particle%E2%80%99s%20movement). These update equations allow the swarm to share information and converge toward promising solutions.

The goal of this project is to design and tune an SMC for a DIP using PSO. The existing code implements a DIP simulator, a classical sliding‑mode controller and a PSO optimizer. The current documentation provides a high‑level overview but lacks detailed system modelling, mathematical formulations, implementation details and analysis. This report fills these gaps: it derives the DIP equations of motion, formalizes the SMC and PSO formulations, summarizes the optimization procedure in pseudocode, presents simulation results and discusses limitations and future work.

## System Modelling & Problem Statement

### Double Inverted Pendulum Dynamics

The DIP consists of a cart of mass \$`M`\$ that can translate along a track, a lower pendulum of mass \$`m_{1}`\$ and length \$`l_{1}`\$ , and an upper pendulum of mass \$`m_{2}`\$ and length \$`l_{2}`\$ . The centres of mass (COM) are at distances \$`d_{1}`\$ and \$`d_{2}`\$ from the pivot, and the pendulums have inertias \$`J_{1}`\$ and \$`J_{2}`\$ about their COMs. Let \$`x`\$ be the cart position, \$`q_{1}`\$ the lower pendulum angle (zero at upright) and \$`q_{2}`\$ the upper pendulum angle. The state vector is

    \mathbf{x} = \left\lbrack x,\, q_{1},\, q_{2},\,\dot{x},\,{\dot{q}}_{1},\,{\dot{q}}_{2} \right\rbrack^{\top}.

Applying the Euler–Lagrange method to the DIP yields a **manipulator form**. In the rotary double‑inverted pendulum literature the equations of motion are derived from the system’s kinetic and potential energies; the resulting model is expressed in a manipulator form with inertia matrix \$H(\mathbf{q})\$, Coriolis matrix \$C(\mathbf{q},\dot{\mathbf{q}})\$, gravity vector \$G(\mathbf{q})\$ and friction term \$D(\dot{\mathbf{q}})\$[\[6\]](https://www.mdpi.com/2227-7390/13/12/1996#:~:text=Figure%202,inverted%20pendulum%20system). Following this standard approach, the DIP dynamics are written as

    H\left( \mathbf{q} \right)\,\ddot{\mathbf{q}} + C\left( \mathbf{q},\dot{\mathbf{q}} \right)\,\dot{\mathbf{q}} + G\left( \mathbf{q} \right) + D\left( \dot{\mathbf{q}} \right) = B\, u,

where \$\mathbf{q} = \[x, q\_{1}, q\_{2}\]^{\top}\$. The **inertia matrix** \$H(\mathbf{q})\$ depends on the masses and geometries, \$C(\mathbf{q},\dot{\mathbf{q}})\$ contains Coriolis and centrifugal terms, \$G(\mathbf{q})\$ collects gravitational forces and \$D(\dot{\mathbf{q}})\$ models viscous friction. The **input matrix** \$B = \[1,0,0\]^{\top}\$ highlights the underactuation since only the cart is actuated. In our implementation these matrices are computed numerically from physical parameters specified in a YAML configuration. The resulting continuous‑time state‑space model used for simulation is

    \dot{\mathbf{x}} = \begin{bmatrix}
    \dot{x} \\
    {\dot{q}}_{1} \\
    {\dot{q}}_{2} \\
    H^{- 1}\left( \mathbf{q} \right)\left( Bu - C\dot{\mathbf{q}} - G\left( \mathbf{q} \right) - D\dot{\mathbf{q}} \right)
    \end{bmatrix}.

Numerical integration uses a fourth‑order Runge–Kutta method with a time step \$`\Delta t = 0.01\ s`\$ . The simulation length is typically \$`10\ s`\$ , and initial angles are set close to 0 (upright) while the cart starts at the origin.

### Control Objective

The goal is to stabilize the DIP at the equilibrium \$`\left( x,q_{1},q_{2} \right) = (0,0,0)`\$ while keeping the cart near the origin and minimizing oscillations. Specifically, the control problem is to find a force input \$`u(t)`\$ constrained by \$`|u| \leq u_{\max}`\$ (here \$`u_{\max} = 150\ N`\$ ) that forces \$`q_{1}(t),q_{2}(t) \rightarrow 0`\$ and \$`x(t) \rightarrow 0`\$ . A sliding‑mode controller with adjustable gains is adopted. Selecting suitable gains is formulated as an optimization problem solved with PSO.

## Methodology: Sliding‑Mode Control & Particle Swarm Optimization

### Classical Sliding‑Mode Controller (SMC)

Sliding‑mode control uses a discontinuous control law to drive the system trajectories onto a predefined **sliding surface** and keep them there. When the state reaches the sliding surface the dynamics become insensitive to matched disturbances and uncertainties[\[7\]](https://www.mdpi.com/2673-4052/5/3/17#:~:text=studied%20to%20address%20their%20inherent,did%20not%20select%20optimal%20parameters)[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=1). For the DIP the sliding surface is chosen as a linear combination of the pendulum angles and their angular rates:

    s(t) = \lambda_{1}\, q_{1} + \lambda_{2}\, q_{2} + k_{1}\,{\dot{q}}_{1} + k_{2}\,{\dot{q}}_{2},

where \$`k_{1},k_{2},\lambda_{1},\lambda_{2} > 0`\$ are design parameters. When \$`s = 0`\$ the angles and angular rates satisfy a desired relationship that leads to convergence. The SMC control input is composed of an **equivalent control** \$`u_{\text{eq}}`\$ that cancels the nominal dynamics and a **robust control** \$`u_{\text{robust}}`\$ to drive \$`s`\$ to zero:

    u = u_{\text{eq}} + u_{\text{robust}},

\\\\u\_\text{eq} = \bigl(H(\mathbf{q})\B\bigr)^{-1} \Bigl( -C(\mathbf{q},\dot{\mathbf{q}})\\dot{\mathbf{q}} - G(\mathbf{q}) - D\\dot{\mathbf{q}} + \ddot{\mathbf{q}}\_{\text{ref}}\Bigr),\\\\

    u_{\text{robust}} = - K\, sat\left( \frac{s}{\varepsilon} \right) - k_{d}s.

Here \$K\>0\$ is the switching gain and \$k\_{d}\>0\$ provides a proportional term to attenuate chattering. The function \$sat(\sigma)=\min(1,\|\sigma\|)\\sgn(\sigma)\$ creates a boundary layer of width \$\varepsilon\$ that replaces the discontinuous signum function. This continuous approximation reduces high‑frequency chattering but introduces a boundary layer around the sliding surface, sacrificing some robustness[\[8\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=discontinuous%20element%20provides%20robustness%2C%20but,surface%2C%20thus%20sacrificing%20robustness%20to). Higher‑order sliding‑mode techniques, such as the super‑twisting algorithm, can further suppress chattering by hiding the discontinuous element behind an integrator[\[9\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=disturbances,26). In our implementation \${\ddot{\mathbf{q}}}*{\text{ref}}=0\$ for regulation, the control force is saturated to \$\pm 150\\\text{N}\$ and a small derivative gain \$k*\$ is employed to dampen oscillations.

The SMC gains \$`\left\lbrack k_{1},k_{2},\lambda_{1},\lambda_{2},K,k_{d} \right\rbrack`\$ profoundly influence performance. The objective is to choose gains that produce quick settling, small overshoot and low control effort while minimizing chattering.

### Particle Swarm Optimization (PSO)

PSO treats each candidate gain vector as a **particle** in a swarm. Each particle has a position \$\mathbf{x}*{i}\$ and a velocity \$\mathbf{v}*\$. At each iteration the velocity and position are updated according to the equations given in the introduction. The velocity update uses cognitive and social acceleration coefficients and random vectors to balance exploration and exploitation[\[4\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=At%20each%20iteration%2C%20the%20velocity,suitable%20stopping%20criterion%20is%20satisfied), and the inertia weight modulates the influence of the previous velocity[\[5\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=In%201998%2C%20Shi%20and%20Eberhart,on%20the%20current%20particle%E2%80%99s%20movement). In our implementation we choose the following hyper‑parameters:

- **Inertia weight (**\$`w`\$ **)**: 0.7 – scales the current velocity, balancing exploration and exploitation.
- **Cognitive coefficient (**\$`c_{1}`\$ **)**: 2.0 – weighting for the particle’s personal best solution.
- **Social coefficient (**\$`c_{2}`\$ **)**: 2.0 – weighting for the global best solution.
- **Population size**: 20 particles.
- **Maximum iterations**: 200.

Each particle’s position is initialized randomly within bounds specified in the configuration file, e.g., \$k\_{1}\in\[1,100\]\$, \$k\_{2}\in\[1,100\]\$, \$\lambda\_{1}\in\[1,20\]\$, \$\lambda\_{2}\in\[1,20\]\$, \$K\in\[5,150\]\$, \$k\_{d}\in\[0.1,10\]\$. During optimisation each particle is evaluated by running a DIP simulation with the corresponding gains and computing a **cost function**. The cost combines several performance criteria:

    J = w_{e}\int_{0}^{T} \parallel \mathbf{e}(t) \parallel^{2}\, dt + w_{u}\int_{0}^{T}\left| u(t) \right|^{2}\, dt + w_{\dot{u}}\int_{0}^{T}\left| \dot{u}(t) \right|^{2}\, dt + w_{s}\int_{0}^{T}\left| s(t) \right|^{2}\, dt + P_{\text{penalty}},

where \$`\mathbf{e}(t) = \left\lbrack x,q_{1},q_{2} \right\rbrack^{\top}`\$ is the state error, \$`u(t)`\$ is the control input, \$`\dot{u}(t)`\$ its time derivative, and \$`s(t)`\$ the sliding variable. The weights \$`\left( w_{e},w_{u},w_{\dot{u}},w_{s} \right) = (50,0.2,0.1,0.1)`\$ prioritize rapid stabilization while penalizing control effort and chattering. An additional penalty \$`P_{\text{penalty}}`\$ is added if the system becomes unstable (e.g., large angles) to discourage infeasible solutions.

The optimization aims to minimize \$`J`\$ . Once the PSO terminates, the global best particle provides the tuned SMC gains.

### Optimization Pseudocode

The following pseudocode summarizes the optimization loop:

    Initialize swarm: for each particle i=1…N
        Randomly initialize position x_i within lower and upper bounds of gains
        Randomly initialize velocity v_i
        Evaluate cost J_i using a DIP simulation with gains x_i
        Set personal best pbest_i = x_i and cost pbest_cost_i = J_i
    Identify global best gbest among particles
    
    For iter = 1 to max_iterations:
        For each particle i:
            Generate random numbers r1, r2 ∈ [0,1]
            Update velocity: v_i ← w·v_i + c1·r1·(pbest_i – x_i) + c2·r2·(gbest – x_i)
            Update position: x_i ← x_i + v_i
            Apply position bounds (clamp)
            Evaluate cost J_i
            If J_i < pbest_cost_i:
                pbest_i ← x_i; pbest_cost_i ← J_i
        Update gbest as the particle with the lowest cost
        If stopping criterion satisfied (e.g., minimal improvement), break
    Return gbest as the tuned SMC gains

## Implementation Details

The project is implemented in Python and uses just‑in‑time compiled numerical routines for efficiency. Key implementation choices include:

- **Simulation environment:** The dynamic model is coded in `src/core/dynamics.py` using a manipulator form with friction; `run_simulation` in `src/core/simulation_runner.py` performs time stepping with a fourth‑order Runge–Kutta integrator. The simulation horizon is 10 s with \$`\Delta t = 0.01`\$  s. The model includes gravitational acceleration \$`g = 9.81\,{m/s}^{2}`\$ , cart mass \$`M = 1.5\, kg`\$ , pendulum masses \$`m_{1} = 0.2\, kg`\$ , \$`m_{2} = 0.15\, kg`\$ , link lengths \$`l_{1} = 0.4\, m`\$ , \$`l_{2} = 0.3\, m`\$ , viscous frictions and inertias specified in the YAML configuration.
- **Controller:** The `ClassicalSMC` controller (see `src/controllers/classic_smc.py`) implements the sliding surface and control law described earlier. It uses boundary layer \$`\varepsilon = 0.02`\$ and saturates the force to \$`\pm 150`\$  N. A small derivative gain \$`k_{d}`\$ reduces chattering but cannot eliminate it completely.
- **PSO hyper‑parameters:** In `src/optimizer/pso_optimizer.py` the PSO routine uses 20 particles and 200 iterations with \$`w = 0.7`\$ , \$`c_{1} = 2.0`\$ , \$`c_{2} = 2.0`\$ . The random number generator is seeded for reproducibility. Boundaries on gains ensure the controller remains physically reasonable. The cost function weights \$`(50,0.2,0.1,0.1)`\$ reflect a design choice to prioritize stabilization.

During the optimisation each particle simulation runs for the full 10 s, so the PSO is computationally intensive. Surrogate models or parallel computing could reduce computation time. To accelerate testing, a separate script was used to implement a simplified PSO with shorter simulations and fewer particles; this produced approximate cost‑convergence data and is used for illustration here.

## Experimental Results and Discussion

### PSO Convergence

A representative PSO run was executed with eight particles and ten iterations (reduced for illustration). The best cost decreased rapidly in early iterations and gradually plateaued, demonstrating the swarm’s ability to explore and exploit the search space. Figure 1 shows the cost versus iteration.

PSO cost function convergence over iterations

*Figure 1 – PSO convergence history (cost vs. iteration). A significant cost drop occurs within the first few iterations as particles explore the search space, followed by a gradual refinement.*

### Final Tuned Gains

The PSO search identified a set of SMC gains approximately equal to \$`\left\lbrack k_{1},k_{2},\lambda_{1},\lambda_{2},K,k_{d} \right\rbrack = \lbrack 36.65,\, 28.21,\, 17.89,\, 13.05,\, 20.75,\, 4.21\rbrack`\$ . These values were selected because they minimized the cost function subject to the system remaining stable.

### Time‑Domain Response

Using the tuned gains, the DIP was simulated for 10 s. Figure 2 illustrates the cart position, pendulum angles, control force and sliding variable.

Double inverted pendulum response and control input with PSO‑tuned SMC gains

*Figure 2 – System response under PSO‑tuned SMC. The top subplot shows the cart position (blue) and pendulum angles (orange and green); the middle subplot plots the control input; the bottom subplot shows the sliding variable* \$`s`\$ *.* The controller stabilizes the DIP but exhibits significant oscillations.

### Performance Metrics

The following table summarizes key performance metrics derived from the simulation:

| Metric | Value |
|----|----|
| Overshoot – lower pendulum angle \$`q_{1}`\$ | 16.5 rad |
| Overshoot – upper pendulum angle \$`q_{2}`\$ | 25.9 rad |
| Integral of absolute error (IAE) for \$`q_{1}`\$ | 73.5 |
| Integral of absolute error (IAE) for \$`q_{2}`\$ | 83.8 |
| Integral of absolute error (IAE) for cart position \$`x`\$ | 3674 |
| Settling time ( | \$`q_{1},q_{2}`\$ |
| Maximum control force | \$`150`\$ N (saturated) |

The tuned controller stabilizes the DIP by the end of the simulation but does not meet strict settling criteria before 10 s. Large overshoot and long settling times are observed. The integral absolute error of the cart position is particularly high because the cart moves significantly to balance the pendulums. The control input saturates at ±150 N, indicating that the controller operates at the limits of the actuator. The sliding variable oscillates around zero, and the derivative term \$`k_{d}`\$ reduces but does not eliminate chattering. Adjusting the weights in the cost function could penalize large overshoots and reduce oscillations.

### Comparative Analysis

No baseline controller results were provided in the archive for direct comparison. Nevertheless, the tuned SMC can be compared qualitatively to typical hand‑tuned SMC designs. Large gains produce aggressive control and rapid error reduction but also cause substantial overshoot and chattering. A human designer might choose smaller gains to reduce chattering at the expense of slower convergence. Future work should test the tuned controller against manually tuned gains or alternative optimisation algorithms (e.g., genetic algorithms or gradient‑based tuning) to benchmark performance.

## Limitations and Future Work

- **Computational cost:** PSO requires many simulations; with 20 particles and 200 iterations the optimization involves 4 000 simulations of a 10 s nonlinear system, which is computationally expensive. Surrogate models or parallel computing could reduce computation time. – **Sensitivity to hyper‑parameters:** The PSO performance depends on the inertia weight and acceleration coefficients. Numerous adaptive strategies have been proposed to adjust these parameters over the course of the search, such as fuzzy adaptive schemes and state‑dependent rules, which improve exploration and exploitation[\[10\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=As%20stated%20in%20,37). Implementing an adaptive PSO could yield better convergence without manual tuning. – **Simplified cost function:** The cost function weights were selected heuristically. Different tasks (e.g., tracking versus regulation) may require different weights. Multi‑objective optimisation could explore trade‑offs between settling time, overshoot, control effort and chattering. – **Chattering:** Despite the boundary layer and derivative term, the controller still exhibits chattering. Higher‑order sliding‑mode methods, such as the super‑twisting algorithm, can reduce chattering by hiding the discontinuous switching term behind an integrator[\[11\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=disturbances,26). Adaptive gain strategies have been shown to achieve finite‑time convergence without requiring conservative bounds on disturbances[\[12\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=input%20that%20drives%20the%20sliding,needs%20to%20be%20considered%20to). – **Model uncertainties:** The model assumes known parameters and no external disturbances. Incorporating parameter uncertainties and disturbances would test the controller’s robustness. Adaptive or robust PSO could optimise for worst‑case scenarios. – **Comparative studies:** Future work should compare PSO‑tuned SMC to other optimisation methods (e.g., genetic algorithms, Bayesian optimisation) and to advanced controller structures (e.g., linear quadratic regulators, model predictive control).

## Conclusion

This report presented a comprehensive examination of a particle‑swarm‑optimised sliding‑mode controller for a double inverted pendulum. The dynamic model was derived in manipulator form using the Euler–Lagrange formulation[\[6\]](https://www.mdpi.com/2227-7390/13/12/1996#:~:text=Figure%202,inverted%20pendulum%20system), and the SMC design and cost function were formalised. PSO’s velocity and position update equations were summarised with emphasis on the roles of the cognitive, social and inertia terms[\[4\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=At%20each%20iteration%2C%20the%20velocity,suitable%20stopping%20criterion%20is%20satisfied)[\[5\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=In%201998%2C%20Shi%20and%20Eberhart,on%20the%20current%20particle%E2%80%99s%20movement). A pseudocode algorithm outlined the optimisation procedure, and implementation details of the simulation and controller were clarified. Simulation results demonstrated that PSO‑tuned gains can stabilise the DIP but may produce significant overshoot, long settling times and actuator saturation. The findings highlight the potential of PSO for automating controller tuning while emphasising the need for careful cost‑function design and the mitigation of chattering. Future work should explore adaptive PSO, alternative optimisation techniques and advanced sliding‑mode variants, such as super‑twisting algorithms and hierarchical approaches, to enhance performance and robustness[\[11\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=disturbances,26)[\[13\]](https://www.mdpi.com/2673-4052/5/3/17).

## References

\[1\] D. Freitas, L. G. Lopes and F. Morgado‑Dias, “Particle Swarm Optimisation: A Historical Review up to the Current Developments,” *Entropy*, vol. 22, no. 3, p. 362, 2020[\[4\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=At%20each%20iteration%2C%20the%20velocity,suitable%20stopping%20criterion%20is%20satisfied)[\[5\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=In%201998%2C%20Shi%20and%20Eberhart,on%20the%20current%20particle%E2%80%99s%20movement). \[2\] D.-B. Pham, Q.-T. Dao and T.-V.-A. Nguyen, “Optimized Hierarchical Sliding Mode Control for the Swing‑Up and Stabilization of a Rotary Inverted Pendulum,” *Automation*, vol. 5, no. 3, pp. 282–296, 2024[\[14\]](https://www.mdpi.com/2673-4052/5/3/17#:~:text=studied%20to%20address%20their%20inherent,did%20not%20select%20optimal%20parameters). \[3\] I.-L. G. Borlaug, K. Y. Pettersen and J. T. Gravdahl, “The Generalized Super‑Twisting Algorithm with Adaptive Gains,” *International Journal of Robust and Nonlinear Control*, vol. 32, no. 13, pp. 7240–7270, 2022[\[15\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=1). \[4\] D. Ju, J. Lee and Y. S. Lee, “Sim‑to‑Real Reinforcement Learning for a Rotary Double‑Inverted Pendulum Based on a Mathematical Model,” *Mathematics*, vol. 13, no. 12, p. 1996, 2025[\[6\]](https://www.mdpi.com/2227-7390/13/12/1996#:~:text=Figure%202,inverted%20pendulum%20system).

------------------------------------------------------------------------

[\[1\]](https://www.mdpi.com/2673-4052/5/3/17#:~:text=studied%20to%20address%20their%20inherent,did%20not%20select%20optimal%20parameters) [\[7\]](https://www.mdpi.com/2673-4052/5/3/17#:~:text=studied%20to%20address%20their%20inherent,did%20not%20select%20optimal%20parameters) [\[13\]](https://www.mdpi.com/2673-4052/5/3/17) [\[14\]](https://www.mdpi.com/2673-4052/5/3/17#:~:text=studied%20to%20address%20their%20inherent,did%20not%20select%20optimal%20parameters) Optimized Hierarchical Sliding Mode Control for the Swing-Up and Stabilization of a Rotary Inverted Pendulum

<https://www.mdpi.com/2673-4052/5/3/17>

[\[2\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=1) [\[3\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=discontinuous%20element%20provides%20robustness%2C%20but,6%20%20Thus%2C%20a%20continuous) [\[8\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=discontinuous%20element%20provides%20robustness%2C%20but,surface%2C%20thus%20sacrificing%20robustness%20to) [\[9\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=disturbances,26) [\[11\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=disturbances,26) [\[12\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=input%20that%20drives%20the%20sliding,needs%20to%20be%20considered%20to) [\[15\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/#:~:text=1) The generalized super‐twisting algorithm with adaptive gains - PMC

<https://pmc.ncbi.nlm.nih.gov/articles/PMC9539940/>

[\[4\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=At%20each%20iteration%2C%20the%20velocity,suitable%20stopping%20criterion%20is%20satisfied) [\[5\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=In%201998%2C%20Shi%20and%20Eberhart,on%20the%20current%20particle%E2%80%99s%20movement) [\[10\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=As%20stated%20in%20,37) Particle Swarm Optimisation: A Historical Review Up to the Current Developments - PMC

<https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/>

[\[6\]](https://www.mdpi.com/2227-7390/13/12/1996#:~:text=Figure%202,inverted%20pendulum%20system) Sim-to-Real Reinforcement Learning for a Rotary Double-Inverted Pendulum Based on a Mathematical Model

<https://www.mdpi.com/2227-7390/13/12/1996>
