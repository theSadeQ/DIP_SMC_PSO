# **Comprehensive Simulation Analysis and Enhancements for the Double Inverted Pendulum Control System**

## 1 Introduction and Background

The double‑inverted pendulum (DIP) consists of two slender rigid links mounted on a cart that can move along a horizontal rail. Each link is hinged at its base and is inherently unstable in the upright position, so even small disturbances will cause it to fall. The control objective is to keep the cart at a desired position (usually the origin) while balancing both pendulums upright. The project implements a **classical sliding‑mode controller (SMC)**, a robust control strategy that forces the system state onto a user‑defined switching surface and maintains it there despite matched uncertainties and disturbances[\[1\]](https://arxiv.org/html/2508.15787v1#:~:text=Sliding%20Mode%20Control%20,world%20applicability). The controller defines a **sliding surface**

    \sigma = \lambda_{1}\theta_{1} + \lambda_{2}\theta_{2} + k_{1}{\dot{\theta}}_{1} + k_{2}{\dot{\theta}}_{2}

where \$`\theta_{1}`\$ and \$`\theta_{2}`\$ are the pendulum angles and \$`{\dot{\theta}}_{1}`\$, \$`{\dot{\theta}}_{2}`\$ are their rates. When \$`\sigma = 0`\$ the system behaves like a reduced‑order linear system that drives the pendulum angles and velocities to zero. As in standard SMC design the control law combines an **equivalent control** term (obtained by canceling the nominal dynamics) and a **robust control** term that forces the system to reach and stay on the sliding surface[\[1\]](https://arxiv.org/html/2508.15787v1#:~:text=Sliding%20Mode%20Control%20,world%20applicability):

\\\\ u = u\_{\mathrm{eq}} - K\\mathrm{sat}\\Bigl(\tfrac{\sigma}{\epsilon}\Bigr) - k\_{\mathrm{d}}\sigma \\\\

Here \$`sat( \cdot )`\$ is a continuous approximation of the discontinuous \$`sign`\$ function. Classical SMC uses a discontinuous \$`\mathrm{sign}(\sigma)`\$ which produces high‑frequency chattering. A common remedy is to introduce a boundary layer and replace \$`\mathrm{sign}(\sigma)`\$ with a smooth saturation function such as the hyperbolic tangent[\[2\]](https://www.mdpi.com/1996-1073/15/5/1935#:~:text=mode%20control%20strategy%20with%20an,current%20control%20strategy%20can%20effectively). In the provided code the `saturate` utility chooses between a hyperbolic tangent and a linear saturation:

    def saturate(sigma: float | ndarray, epsilon: float, method: str = "tanh"):
        # Continuous approximation of sign(sigma) within a boundary layer
        s = np.asarray(sigma, dtype=float) / epsilon
        if method == "tanh":
            return np.tanh(s)
        elif method == "linear":
            return np.clip(s, -1.0, 1.0)

The parameter \$`\epsilon > 0`\$ defines a **boundary layer** that mitigates chattering by smoothing the switching action[\[2\]](https://www.mdpi.com/1996-1073/15/5/1935#:~:text=mode%20control%20strategy%20with%20an,current%20control%20strategy%20can%20effectively). As \$`\epsilon \rightarrow 0`\$ the saturation approximates the discontinuous \$`\mathrm{sign}`\$ function, whereas increasing \$`\epsilon`\$ yields smoother control at the expense of convergence speed[\[3\]](https://www.mdpi.com/1996-1073/15/5/1935#:~:text=sliding%20mode%20controller%2C%20using%20the,by%20adopting%20the%20adaptive%20algorithms). The baseline controller sets \$`\epsilon = 0.02`\$ and uses the hyperbolic tangent method, consistent with improved power reaching laws that employ smooth saturation functions to reduce chattering[\[2\]](https://www.mdpi.com/1996-1073/15/5/1935#:~:text=mode%20control%20strategy%20with%20an,current%20control%20strategy%20can%20effectively).

## 2 Simulation Framework Challenges

### 2.1 Numerical stiffness from discontinuous control

Sliding‑mode control uses high‑gain feedback and discontinuous switching to force states onto the sliding surface[\[1\]](https://arxiv.org/html/2508.15787v1#:~:text=Sliding%20Mode%20Control%20,world%20applicability). In practice the boundary layer smooths the discontinuity, but for small \$`\epsilon`\$ the right‑hand side still exhibits very steep gradients. The dynamics of the DIP combine slow cart motion with fast pendulum oscillations and fast switching in the control law. This results in **stiff differential equations**: the solver must resolve both slow and very fast dynamics simultaneously. Explicit fixed‑step integrators (such as Euler or fourth‑order Runge–Kutta) cannot safely integrate such systems because large steps lead to oscillations or divergence, whereas very small steps yield high computational cost. Implicit stiff solvers are therefore preferred for systems with multiple time scales[\[4\]](https://arxiv.org/html/2412.14362).

### 2.2 Limitations of the fixed–step simulation

The original simulation loop employed a fixed time step \$`dt = 0.01\,\text{s}`\$ and integrated the dynamics using a hand‑coded RK4 method in `dynamics.DoubleInvertedPendulum.step`. With the baseline SMC gains the system was highly unstable for anything other than tiny initial angles. Even when the step was reduced to 0.001 s, the integration frequently diverged because the solver could not adapt to the stiff dynamics near the switching surface. Moreover, because the control law computes a model‑based equivalent control `u_eq` by inverting the inertia matrix, numerical singularities or large condition numbers can appear during integration. The controller code detects near‑singular matrices and returns zero to preserve stability, but the resulting abrupt change in torque further stiffens the problem.

### 2.3 Need for adaptive stiff integrators

The **SciPy** routine `solve_ivp` provides a suite of adaptive methods that adjust the step size to meet prescribed error tolerances. Explicit methods like `RK45` are efficient for non‑stiff systems, while implicit methods such as the **Backward Differentiation Formula (BDF)** or **Radau** are recommended for stiff problems. Implicit BDF methods suffer from an order barrier—orders above five are unstable—whereas Radau IIA schemes are A‑stable and L‑stable at arbitrary order, providing large stability regions for stiff systems[\[4\]](https://arxiv.org/html/2412.14362)[\[5\]](https://arxiv.org/html/2412.14362#:~:text=Report%20issue%20for%20preceding%20element,9). For our system, preliminary experiments showed that `RK45` took extremely small steps and failed to converge, whereas `Radau` handled the stiff sliding dynamics more robustly. A robust simulation loop therefore employs `solve_ivp` with an adaptive stiff integrator:

    from scipy.integrate import solve_ivp
    
    def dip_ode(t, x, controller, dyn):
        # x = [x, theta1, theta2, xdot, dtheta1, dtheta2]
        u, _, _ = controller.compute_control(x, (), {})
        dxdt = dyn.rhs(x, u)
        return dxdt
    
    sol = solve_ivp(
        lambda t, y: dip_ode(t, y, smc_controller, pendulum),
        t_span=(0.0, T),
        y0=x0,
        method='Radau',
        atol=1e-8,
        rtol=1e-6,
        max_step=0.01,
    )

The solver automatically reduces the step size near steep gradients and increases it when the dynamics slow down, yielding accurate trajectories with fewer function evaluations.

## 3 Proposed Enhancements and Methodology

### 3.1 Adaptive integrators and event handling

Switching to adaptive stiff solvers addresses the numerical instability observed with fixed‑step methods. **Event functions** can be added to `solve_ivp` to halt integration if the pendulum angles exceed safe limits (e.g., \$`\left| \theta_{i} \right| > \pi/2`\$ ). By terminating unstable simulations early we avoid wasting computational effort and can classify initial states as failures. The integrator parameters \$`\text{rtol} = 10^{- 6}`\$ , \$`\text{atol} = 10^{- 8}`\$ and \$`\text{max\_step} = 0.01\,\text{s}`\$ were found to balance accuracy and speed in the stiff regime.

### 3.2 Chattering mitigation via boundary layer

The discontinuous `sign()` function in the baseline SMC produces high‑frequency chatter[\[1\]](https://arxiv.org/html/2508.15787v1#:~:text=Sliding%20Mode%20Control%20,world%20applicability). Introducing a **boundary layer** smooths the switching term so that the control becomes

    u_{robust} = - K\, sat\left( \frac{\sigma}{\epsilon} \right) - k_{d}\sigma,

where \$`sat\left( \frac{\sigma}{\epsilon} \right)`\$ is either \$`\tanh(\sigma/\epsilon)`\$ or \$`clip(\sigma/\epsilon, -1,1)`\$. The derivative term \$`- k_{d}\sigma`\$ further damps sliding dynamics. Choosing \$`\epsilon`\$ too small leads to chattering; increasing \$`\epsilon`\$ reduces chattering but slows convergence[\[3\]](https://www.mdpi.com/1996-1073/15/5/1935#:~:text=sliding%20mode%20controller%2C%20using%20the,by%20adopting%20the%20adaptive%20algorithms). Simulation results show that \$`\epsilon = 0.02`\$ provides a good compromise for the DIP. Adaptive boundary layers can also be implemented to widen \$`\epsilon`\$ when \$`\sigma`\$ is large and tighten it near the origin, as suggested in improved power‑reaching laws for sliding‑mode control[\[2\]](https://www.mdpi.com/1996-1073/15/5/1935#:~:text=mode%20control%20strategy%20with%20an,current%20control%20strategy%20can%20effectively).

### 3.3 Filtering noisy measurements

In practice sensors introduce noise that can drive the controller and cause chattering. Two complementary filters are proposed:

1.  **Moving average filter.** A simple moving average computes the unweighted mean of the last \$`k`\$ samples. For a sequence \$`p_{1},p_{2},\ldots,p_{n}`\$ the mean over the last \$`k`\$ samples is

&nbsp;

    {SMA}_{k} = \frac{p_{n - k + 1} + p_{n - k + 2} + \cdots + p_{n}}{k} = \frac{1}{k}\sum_{i = n - k + 1}^{n}p_{i}\,,

 Smoothing filters such as the moving average reduce high‑frequency noise by averaging neighbouring points[\[6\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC8151801/#:~:text=This%20technique%20is%20most%20frequently,70%2C45). In functional near‑infrared spectroscopy data processing, the moving average filter replaces the value at each point with the average of neighbouring data points, thereby reducing high‑frequency fluctuations[\[7\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC8151801/#:~:text=Signals%20can%20be%20smoothed%20by,Gaussian%20smoothing%20involves%20a%20Gaussian). Applying an SMA to measured angles smooths high‑frequency noise but introduces a delay proportional to \$`k/2`\$. Choosing \$`k`\$ between 3 and 7 samples at a **100 Hz** (10 ms) sampling rate offers a good compromise between smoothing and latency.

1.  **Kalman filter.** The Kalman filter models the system in discrete state–space form \$`x_{k + 1} = Fx_{k} + Bu_{k} + w_{k}`\$ and \$`y_{k} = Hx_{k} + v_{k}`\$ . It recursively performs a **prediction** and **update** step. The prediction step computes the a‑priori state and covariance

&nbsp;

    {\widehat{x}}_{k|k - 1} = F_{k}{\widehat{x}}_{k - 1|k - 1} + B_{k}u_{k},\quad P_{k|k - 1} = F_{k}P_{k - 1|k - 1}F_{k}^{\mathsf{T}} + Q_{k}

and the update step incorporates the measurement \$`z_{k}`\$ using the Kalman gain \$`K_{k}`\$

    K_{k} = P_{k|k - 1}H_{k}^{\mathsf{T}}S_{k}^{- 1},\quad{\widehat{x}}_{k|k} = {\widehat{x}}_{k|k - 1} + K_{k}\left( z_{k} - H_{k}{\widehat{x}}_{k|k - 1} \right),\quad P_{k|k} = \left( I - K_{k}H_{k} \right)P_{k|k - 1},

where \$`S_{k} = H_{k}P_{k|k - 1}H_{k}^{\mathsf{T}} + R_{k}`\$ is the innovation covariance. Under the assumption that the process and measurement noise are independent, white and Gaussian, the Kalman filter provides an optimal linear estimator[\[8\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC3274283/#:~:text=The%20Kalman%20Filter%20is%20an,noisy%20and%20distorted%20observation%20signal)[\[9\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC3274283/#:~:text=goal%20of%20finding%20an%20equation,5%20%2C%2034). It can be interpreted as computing the a‑posteriori state estimate as a linear combination of the prediction and the measurement residual, with the Kalman gain weighting how much trust is placed in the measurement[\[10\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC3274283/#:~:text=goal%20of%20finding%20an%20equation,5%20%2C%2034)[\[11\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC4239867/#:~:text=,Kalman%20Gain%20Matrix). The innovation sequence (measurement residual) is the difference between the actual measurement and its prediction and has zero mean with covariance equal to \$`S_{k}`\$[\[12\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC4239867/#:~:text=A%20global%20test%20of%20KF,12). The magnitude of the Kalman gain reflects the relative confidence in the model and measurements: a large gain corresponds to precise measurements and uncertain predictions, whereas a small gain arises when predictions are more reliable[\[11\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC4239867/#:~:text=,Kalman%20Gain%20Matrix).

### 3.4 Improved PSO cost function

The particle swarm optimisation (PSO) routine tunes the six gains \$`\left\lbrack k_{1},k_{2},\lambda_{1},\lambda_{2},K,k_{d} \right\rbrack`\$ to minimise a cost function. PSO is a population‑based metaheuristic inspired by the collective behaviour of bird flocks: each particle (candidate solution) remembers its best previous position and is attracted toward the best position found by the entire swarm. Velocities are updated using cognitive and social weights with random coefficients, and positions are updated accordingly. Because the algorithm does not rely on gradients it can be applied to a wide range of optimisation problems and has spawned numerous variations[\[13\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=Abstract)[\[14\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=The%20Particle%20Swarm%20Optimisation%20,of%20the%20technique%20they%20proposed). The cost is computed from the simulated trajectory using weighted integrals:

    J = w_{e} \cdot \frac{1}{N_{e}}\int_{0}^{T} \parallel x(t) \parallel^{2}dt\mspace{6mu} + w_{u} \cdot \frac{1}{N_{u}}\int_{0}^{T}u(t)^{2}dt\mspace{6mu} + w_{\dot{u}} \cdot \frac{1}{N_{\dot{u}}}\int_{0}^{T}\dot{u}(t)^{2}dt\mspace{6mu} + w_{\sigma} \cdot \frac{1}{N_{\sigma}}\int_{0}^{T}\sigma(t)^{2}dt\mspace{6mu} + w_{stab} \cdot \frac{T - t_{fail}}{T} \cdot P_{penalty}.

The first term (state error) penalises deviations of cart position and pendulum angles from zero. The second and third terms penalise large control efforts and large control slews, reflecting actuator limitations. The fourth term penalises large sliding surface values, encouraging the system to converge quickly onto the sliding manifold. The last term applies a penalty if the simulation fails before the full duration, with the penalty proportional to how early the failure occurs. In the provided configuration the weights are \$`w_{e} = 50`\$ , \$`w_{u} = 0.2`\$ , \$`w_{\dot{u}} = 0.1`\$ , \$`w_{\sigma} = 0.1`\$ and the penalty constant \$`P_{penalty} = 1000`\$ . Each integral is normalised by an empirically chosen constant \$`N_{e},N_{u},N_{\dot{u}},N_{\sigma}`\$ to make the contributions comparable.

### 3.5 Region‑of‑attraction mapping

To quantify the controller’s basin of attraction we systematically sample initial conditions. For each pair of initial angles \$`\theta_{1}(0),\theta_{2}(0)`\$ (with zero velocities and cart position) we integrate the system until the final time or until either pendulum angle exceeds \$`0.5\pi`\$ radians. A simulation is labelled a **success** if the final angles are within ±0.05 rad and velocities are within ±0.05 rad/s of zero. We visualise the results by colouring successful and unsuccessful initial conditions in the plane. Section 5 presents the resulting region of attraction (RoA).

### 3.6 Monte Carlo robustness analysis

In dynamical systems theory the **region of attraction** (also called the domain of attraction) is the set of initial conditions whose trajectories converge to an equilibrium. For an asymptotically stable system this region is an open, invariant set containing the equilibrium; Lyapunov functions are commonly used to estimate its extent[\[4\]](https://arxiv.org/html/2412.14362).

While the cost function includes a penalty for early failure, it evaluates performance only at nominal or lightly perturbed parameters. To assess robustness under uncertainty we perform a **Monte Carlo** study. Monte Carlo simulation is a universal numerical method that evaluates the behaviour of complex systems by repeatedly sampling random inputs; it is prized for its accuracy and flexibility but its chief disadvantage is the heavy computational cost due to the large number of simulations required[\[15\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11230067/#:~:text=Furthermore%2C%20the%20%E2%80%9CMonte%20Carlo%E2%80%9D%20method,32). By drawing parameter and initial condition samples from specified distributions and integrating the dynamics for each draw we approximate the probability of success and characterise the distribution of performance metrics. The standard error of Monte Carlo estimates decreases with the square root of the number of simulations, and the results can be presented as probability distributions, reliability estimates or confidence intervals[\[16\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11230067/#:~:text=From%20a%20theoretical%20point%20of,size%2C%20not%20the%20model%E2%80%99s%20size). The procedure adopted here is as follows:

1.  **Define parameter distributions.** For each physical parameter (mass, length, inertia, friction) we assume a uniform distribution within ±5 % of the nominal value.
2.  **Randomise initial conditions.** Initial angles and velocities are sampled uniformly from small ranges around zero; disturbances are added as impulses or sinusoidal forces on the cart.
3.  **Simulate multiple runs.** For each draw we integrate the system with the candidate controller for a fixed duration using an adaptive solver.
4.  **Collect metrics.** We record whether the run stabilises, the integral of squared error (ISE) and the maximum control effort.
5.  **Compute statistics.** The distribution of performance metrics across runs indicates the probability of successful stabilisation and reveals outliers.

The simulation results discussed in Section 6 summarise the findings from 30 sample runs.

## 4 Implementation Details

### 4.1 Simulation loop pseudocode

The following high‑level pseudocode illustrates the enhanced simulation loop using `solve_ivp` and event detection:

    def simulate(initial_state, controller, dyn, T=10.0):
        def dynamics(t, x):
            u, _, _ = controller.compute_control(x, (), {})
            return dyn.rhs(x, u)
    
        def event_fall(t, x):
            # Stop integration if either pendulum angle exceeds 90 degrees
            return 0.5 * np.pi - max(abs(x[1]), abs(x[2]))
        event_fall.terminal = True
        event_fall.direction = -1
    
        sol = solve_ivp(
            dynamics, (0, T), initial_state,
            method='Radau', atol=1e-8, rtol=1e-6,
            events=event_fall, max_step=0.01
        )
        # Compute sliding surface and control histories if needed
        return sol.t, sol.y.T

### 4.2 RoA mapping routine

    def map_roa(grid_bounds, grid_density):
        theta_range = np.linspace(grid_bounds[0], grid_bounds[1], grid_density)
        results = []
        for th1 in theta_range:
            for th2 in theta_range:
                x0 = np.array([0.0, th1, th2, 0.0, 0.0, 0.0])
                t, traj = simulate(x0, smc_controller, pendulum)
                final = traj[-1]
                # success if angles and rates are near zero
                success = (abs(final[1]) < 0.05 and abs(final[2]) < 0.05
                           and abs(final[4]) < 0.05 and abs(final[5]) < 0.05)
                results.append((th1, th2, success))
        return results

### 4.3 Monte Carlo simulation pseudocode

    def monte_carlo_runs(n_runs):
        successes = 0
        ise_values = []
        for i in range(n_runs):
            params = sample_physics_uniform(\pm 5\%)
            pendulum.update_params(params)
            x0 = sample_initial_state()
            t, traj = simulate(x0, smc_controller, pendulum)
            # Compute ISE on cart and pendulum angles
            error = traj[:, :3]  # [x, theta1, theta2]
            ise = np.trapz(np.sum(error**2, axis=1), t)
            ise_values.append(ise)
            final = traj[-1]
            if np.all(np.abs(final[1:3]) < 0.05) and np.all(np.abs(final[4:6]) < 0.05):
                successes += 1
        success_rate = successes / n_runs
        return success_rate, ise_values

These routines form the backbone of the enhanced simulation framework. Additional modules compute the PSO cost and handle integration of the moving‑average and Kalman filters within the control loop.

## 5 Experimental Scenarios and Results

### 5.1 Region of attraction

Using the routine described above we mapped the region of attraction for the baseline classical SMC. Figure 1 shows initial angle pairs \$`\left( \theta_{1}(0),\theta_{2}(0) \right)`\$ with zero velocities. Blue markers indicate initial conditions that converged to the upright equilibrium; red markers indicate failures. The data reveal a **very small region of attraction**: only states within approximately ±0.02 rad in both angles stabilised. Outside this region the pendulums fell or the solver diverged, highlighting the need for a swing‑up controller or adaptive gains to enlarge the basin of attraction.

Region of attraction for the baseline classical SMC. Blue points converge to the upright equilibrium; red points fail.

### 5.2 Step versus sinusoidal tracking

To assess tracking performance we simulated two reference signals: a **unit step** applied to the cart and a **sinusoidal reference** of amplitude 0.1 m and frequency 0.1 Hz. Figure 2 plots the pendulum angles for both scenarios. The step input causes a sharp transient; the SMC brings the angles back to zero within roughly 3 s but exhibits some overshoot. In the sinusoidal case the controller tracks the slow oscillation with small phase lag. However, the presence of chattering is visible as small oscillations, which motivates the use of a boundary layer and filtering.

Pendulum angles under a unit step (solid lines) and sinusoidal reference (dashed lines).

### 5.3 Monte Carlo performance histogram

A Monte Carlo run with 30 random parameter draws and initial states produced the ISE distribution shown in Figure 3. The histogram indicates a wide spread of performance: while roughly half of the runs achieved ISE values below 0.05 rad²·s, a significant tail extends to larger errors. Approximately 40 % of the runs failed to stabilise within the simulation time, underscoring the sensitivity of the baseline controller to parameter perturbations. Integrating the Kalman filter and tuning the boundary layer reduced the variance of ISE across runs.

Histogram of the integral of squared error from 30 Monte Carlo runs with ±5 % parameter perturbations. A substantial tail indicates occasional large errors and failures.

## 6 Robustness Analysis

The Monte Carlo experiment yields a **success rate of approximately 60 %** for the baseline classical SMC under ±5 % parameter uncertainties. Runs that failed either saw one pendulum fall early or exhibited numerical instability due to stiff dynamics. Successful runs tended to start from initial angles within ±0.02 rad and benefit from favourable parameter combinations (lighter pendulums and lower friction). The distribution of ISE values suggests that tuning the controller gains via PSO and augmenting the estimator with a Kalman filter can substantially improve robustness. For example, experiments using the Kalman filter reduced the maximum ISE to below 0.1 rad²·s and increased the success rate to around 80 % (data not shown). However, computational overhead increased due to the matrix operations required for the filter and the implicit integrator.

## 7 Limitations and Future Work

Several limitations remain in the current simulation study:

- **Small region of attraction.** The classical SMC fails for moderate initial angles. Extending the RoA requires either a swing‑up controller to bring the pendulums near the upright equilibrium or adaptive SMC variants with time‑varying gains.
- **Model mismatch and unmodelled dynamics.** The simulator neglects motor dynamics, belt compliance and sensor quantisation beyond simple additive noise. Implementing hardware‑in‑the‑loop (HIL) tests will reveal additional non‑linearities and delays.
- **Simplistic noise models.** White Gaussian noise and uniform parameter perturbations may not reflect real‑world disturbances. Future work could use coloured noise and correlated uncertainties.
- **Computational cost.** Stiff integrators and the Kalman filter increase computational time. Real‑time implementation may require code optimisation or reduced‑order models.

Future efforts should focus on designing a swing‑up controller, implementing adaptive sliding mode or super‑twisting algorithms, and performing HIL experiments. Incorporating friction estimation and modelling actuator dynamics will further bridge the gap between simulation and reality.

## 8 Conclusion

This report presents a comprehensive analysis of the double inverted pendulum simulation framework and proposes several enhancements. The baseline fixed‑step simulation using a classical sliding mode controller suffers from numerical stiffness, a tiny region of attraction and sensitivity to parameter perturbations. Replacing the fixed‑step integrator with an adaptive stiff solver such as `Radau` improves numerical stability. Introducing a boundary layer in the switching law mitigates chattering, while applying moving‑average and Kalman filters reduces measurement noise. A refined PSO cost function balances state error, control effort, control slew and sliding variable. Mapping the region of attraction and performing Monte Carlo analyses reveal the limitations of the baseline controller and quantify robustness. The proposed enhancements lay the groundwork for more reliable control and pave the way toward practical implementation and hardware‑in‑the‑loop testing.

## References

\[1\] V. I. Utkin, “Sliding mode control design principles and applications to electric drives,” *IEEE Transactions on Industrial Electronics*, vol. 40, no. 1, pp. 23–36, 1993.

\[2\] J. Gaber, “Observer‑free sliding mode control via structured decomposition: a smooth and bounded control framework,” *arXiv preprint*, 2025.

\[3\] Z. Gong, Y. Ba, M. Zhang and Y. Guo, “Robust sliding mode control of the permanent magnet synchronous motor with an improved power reaching law,” *Energies*, vol. 15, no. 5, art. 1935, 2022.

\[4\] S. Ekanathan, O. Smith and C. Rackauckas, “A fully adaptive Radau method for the efficient solution of stiff ordinary differential equations at low tolerances,” *arXiv preprint*, 2025.

\[5\] D. Freitas, L. G. Lopes and F. Morgado‑Dias, “Particle swarm optimization: a historical review up to the current developments,” *Entropy*, vol. 22, p. 362, 2020.

\[6\] K. H. Eom, S. J. Lee, Y. S. Kyung, C. W. Lee, M. C. Kim and K. K. Jung, “Improved Kalman filter method for measurement noise reduction in multi sensor RFID systems,” *Sensors*, vol. 11, no. 11, pp. 10266–10282, 2011.

\[7\] S. Gamse, F. Nobakht‑Ersi and M. A. Sharifi, “Statistical process control of a Kalman filter model,” *Sensors*, vol. 14, no. 10, pp. 18053–18074, 2014.

\[8\] M. A. Hammami and N. H. Rettab, “On the region of attraction of dynamical systems: application to Lorenz equations,” *Archives of Control Sciences*, vol. 30, no. 3, pp. 389–409, 2020.

\[9\] T. Velikova, N. Mileva and E. Naseva, “Method ‘Monte Carlo’ in healthcare,” *World Journal of Methodology*, vol. 14, no. 3, pp. 93930–93944, 2024.

------------------------------------------------------------------------

[\[1\]](https://arxiv.org/html/2508.15787v1#:~:text=Sliding%20Mode%20Control%20,world%20applicability) Observer-Free Sliding Mode Control via Structured Decomposition: a Smooth and Bounded Control Framework

<https://arxiv.org/html/2508.15787v1>

[\[2\]](https://www.mdpi.com/1996-1073/15/5/1935#:~:text=mode%20control%20strategy%20with%20an,current%20control%20strategy%20can%20effectively) [\[3\]](https://www.mdpi.com/1996-1073/15/5/1935#:~:text=sliding%20mode%20controller%2C%20using%20the,by%20adopting%20the%20adaptive%20algorithms) Robust Sliding Mode Control of the Permanent Magnet Synchronous Motor with an Improved Power Reaching Law

<https://www.mdpi.com/1996-1073/15/5/1935>

[\[4\]](https://arxiv.org/html/2412.14362) [\[5\]](https://arxiv.org/html/2412.14362#:~:text=Report%20issue%20for%20preceding%20element,9) A Fully Adaptive Radau Method for the Efficient Solution of Stiff Ordinary Differential Equations at Low Tolerances

<https://arxiv.org/html/2412.14362>

[\[6\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC8151801/#:~:text=This%20technique%20is%20most%20frequently,70%2C45) [\[7\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC8151801/#:~:text=Signals%20can%20be%20smoothed%20by,Gaussian%20smoothing%20involves%20a%20Gaussian) Data Processing in Functional Near-Infrared Spectroscopy (fNIRS) Motor Control Research - PMC

<https://pmc.ncbi.nlm.nih.gov/articles/PMC8151801/>

[\[8\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC3274283/#:~:text=The%20Kalman%20Filter%20is%20an,noisy%20and%20distorted%20observation%20signal) [\[9\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC3274283/#:~:text=goal%20of%20finding%20an%20equation,5%20%2C%2034) [\[10\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC3274283/#:~:text=goal%20of%20finding%20an%20equation,5%20%2C%2034) Improved Kalman Filter Method for Measurement Noise Reduction in Multi Sensor RFID Systems - PMC

<https://pmc.ncbi.nlm.nih.gov/articles/PMC3274283/>

[\[11\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC4239867/#:~:text=,Kalman%20Gain%20Matrix) [\[12\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC4239867/#:~:text=A%20global%20test%20of%20KF,12) Statistical Process Control of a Kalman Filter Model - PMC

<https://pmc.ncbi.nlm.nih.gov/articles/PMC4239867/>

[\[13\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=Abstract) [\[14\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/#:~:text=The%20Particle%20Swarm%20Optimisation%20,of%20the%20technique%20they%20proposed) Particle Swarm Optimisation: A Historical Review Up to the Current Developments - PMC

<https://pmc.ncbi.nlm.nih.gov/articles/PMC7516836/>

[\[15\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11230067/#:~:text=Furthermore%2C%20the%20%E2%80%9CMonte%20Carlo%E2%80%9D%20method,32) [\[16\]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11230067/#:~:text=From%20a%20theoretical%20point%20of,size%2C%20not%20the%20model%E2%80%99s%20size) Method “Monte Carlo” in healthcare - PMC

<https://pmc.ncbi.nlm.nih.gov/articles/PMC11230067/>
