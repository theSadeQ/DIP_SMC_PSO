# Sliding Mode Control for a Double‑Inverted Pendulum: Bridging Theory and Implementation

## Introduction – Why Sliding Mode Control?

The double‑inverted pendulum (DIP) is widely recognised as a **canonical benchmark** for the study of nonlinear, under‑actuated control systems. Inverted‑pendulum experiments have been used for decades to teach and validate control techniques; variants such as the rotational single‑arm pendulum, the cart pendulum and the **double inverted pendulum** offer escalating control challenges, and the inverted pendulum is often described as the most fundamental benchmark for robotics and control education \[1\]. In the DIP, two pendula are attached in series to a horizontally moving cart and only the cart is actuated. Consequently the system has fewer actuators than degrees of freedom and is both **under‑actuated** and **strongly nonlinear** \[2\]. Conventional linear controllers struggle with large deflections, parameter variations and model uncertainty.

Sliding Mode Control (SMC) addresses these issues by forcing the system state onto a pre‑defined **sliding manifold**. When the state reaches this manifold, the resulting closed‑loop dynamics become insensitive to matched disturbances and uncertainties \[3\]. The control law compensates modelling errors through the control input channel so that the plant behaves according to the reduced‑order dynamics on the manifold \[3\]. This robustness and finite‑time convergence make SMC attractive for under‑actuated systems such as the DIP. However, the discontinuous switching law of classic SMC induces **chattering**, a high‑frequency oscillation caused by rapid control switching when the state crosses the sliding surface. Chattering increases control effort, excites unmodelled high‑frequency modes and can cause wear in actuators. Introducing a boundary layer around the sliding surface alleviates chattering but enlarges the tracking error and slows the response \[4\].

To explore different trade‑offs between robustness, smoothness and complexity, this project implements four SMC variants – **classic (first‑order)**, **super‑twisting algorithm (STA)**, **adaptive SMC**, and **hybrid adaptive–STA**. Each variant is implemented in the provided Python code (`classic_smc.py`, `sta_smc.py`, `adaptive_smc.py`, `hybrid_adaptive_sta_smc.py`), and the following sections link the theory to these implementations.

### Structure of the report

The report is organised as follows. Each controller variant is presented with a concise theoretical background, a description of its implementation in the project, and an analysis of its practical implications. New sections map configuration parameters to mathematical symbols and discuss robustness issues such as singularity handling. A glossary of symbols and tables summarise the key results.

------------------------------------------------------------------------

## Variant I: Classic Sliding Mode Control (SMC)

### Principles and sliding surface

Classic SMC designs a linear **sliding surface** that combines position and velocity errors. For second‑order systems such as the DIP, the surface is typically a linear combination of the tracking error and its first derivative \[5\]. In this report the sliding surface is

    \sigma = \lambda_{1}\,\theta_{1} + \lambda_{2}\,\theta_{2} + k_{1}\,\dot{\theta}_{1} + k_{2}\,\dot{\theta}_{2},

where \(\theta_{i}\) are the pendulum angles, \(\dot{\theta}_{i}\) their angular velocities, and \(\lambda_{i}>0\) are design gains. The implementation computes the sliding variable in the `_compute_sliding_surface` method of `classic_smc.py`:

*“sigma = self.lam1 \* theta1 + self.lam2 \* theta2 + self.k1 \* dtheta1 + self.k2 \* dtheta2”* (see `classic_smc.py`), directly matching the equation above.

### Control law: equivalent and switching parts

The control input \u\ is decomposed into an **equivalent control** \u\_{\mathrm{eq}} that cancels the nominal dynamics and a **robust switching** term \u\_{\mathrm{sw}} that drives \(\sigma\) toward zero. This decomposition, often written as \(u = u_{eq} + u_{sw}\), is standard in sliding‑mode design \[5\]:

    u = u_{eq} - K\, sat\left( \frac{\sigma}{\epsilon} \right) - k_{d}\,\sigma.

#### Equivalent control computation

In `classic_smc.py` the `_compute_equivalent_control` method solves the dynamic equation of the DIP:

    M(q)\ddot{q} + C\left( q,\dot{q} \right)\dot{q} + G(q) = B\, u,

for the **cart force** \u\ required to satisfy \(\dot{\sigma}=0\). The inertia matrix \M(q)\ is computed from the physics parameters and then **regularised** by adding a small diagonal term. Before inversion the code checks the condition number of \M(q)\; if it is ill‑conditioned the method resorts to the pseudo‑inverse (`np.linalg.pinv`) to avoid numerical singularities. This careful handling prevents blow‑ups when the pendulum angles approach singular configurations. The resulting \u\_{\mathrm{eq}} is limited by the `max_force` parameter in the configuration.

#### Boundary layer and saturation

The switching term uses a **saturation function** to approximate the discontinuous sign function within a small **boundary layer** of width \(\epsilon\). Such smoothing reduces the chattering inherent in the discontinuous sign function, but it comes at a cost: introducing a boundary layer increases the tracking error and slows the response \[4\]. In the code, the `saturate` utility implements two approximations—a hyperbolic tangent (`method='tanh'`) and a linear clipping (`method='linear`)—that smooth the sign function. Figure 1 plots the ideal sign function alongside these saturations. Notice how both approximations approach the discontinuous sign outside the boundary layer and produce smoother transitions inside.

Saturation function approximations

*Figure 1 – Approximation of the sign function by the hyperbolic‑tangent and linear saturation methods. The boundary layer width \(\epsilon\) determines where the output transitions between −1 and 1.*

### Numerical robustness

The classic controller includes several robustness enhancements:
- **Condition‑number checking and regularisation:** The inertia matrix \M(q)\ is checked for ill‑conditioning and regularised by adding a small diagonal term (\(\varepsilon I\)). When ill‑conditioned, a pseudo‑inverse is used to compute the equivalent control.
- **Fallback control:** If the matrix inversion still fails due to singularity, the controller saturates the output to zero and returns an error flag, preventing instability.
- **Actuator saturation:** The control input is saturated by `max_force` to respect actuator limits.
These features make the classic SMC implementation stable and safe even when the model parameters deviate from their nominal values.

------------------------------------------------------------------------

## Variant II: Super‑Twisting Algorithm (STA) SMC

### Theory and formulation

The **super‑twisting algorithm** (STA) is a second‑order sliding mode technique that suppresses chattering by applying the discontinuity on the **derivative** of the control signal rather than on the control itself. By moving the discontinuity to the derivative, the control input becomes continuous, which greatly reduces high‑frequency oscillations while preserving the robustness of sliding‑mode control and guaranteeing finite‑time convergence to the sliding set \[6\]. The sliding variable \(\sigma\) for the STA controller is similar to the classic one but is scaled by separate gains. In `sta_smc.py` it is computed as

    \sigma = k_{1}\,\left( {\dot{\theta}}_{1} + \lambda_{1}\,\theta_{1} \right) + k_{2}\,\left( {\dot{\theta}}_{2} + \lambda_{2}\,\theta_{2} \right).

The STA control comprises two components:

1.  **Continuous term** \(u_{c}=-K_{1}\sqrt{\|\sigma\|}\,\mathrm{sgn}(\sigma)\); this term acts like a damping force proportional to \(\sqrt{\|\sigma\|}\).
2.  **Integral term** \(u_{i}\) generated by integrating the sign of \(\sigma\): the internal state \(z\) is updated as \(z\leftarrow z - K_{2}\,\mathrm{sgn}(\sigma)\,\mathrm{d}t\). The integral of the discontinuity produces a continuous control signal, effectively moving the discontinuity to its derivative.

The total control is \(u = u_{\mathrm{eq}} + u_{c} + z\). Because the discontinuity is applied to the derivative rather than to the control itself, the resulting control law is continuous and enforces finite‑time convergence of both the sliding variable and its derivative \[6\].  In our implementation the internal integrator for \(z\) is updated explicitly using the time step `dt`; the previously supported `semi_implicit` configuration key has been removed from the code and should not appear in `config.yaml`.

### Lyapunov stability and numerical verification

A Lyapunov function \(V=\tfrac12\sigma^{2}\) can be shown to decrease along system trajectories under the STA law, guaranteeing finite‑time convergence of both \(\sigma\) and \(\dot{\sigma}\) to zero. The project includes a test, `test_lyapunov_decrease_sta` in `tests/test_core/test_lyapunov.py`, that numerically confirms this property. The test evaluates \(V\) at successive time steps and asserts that \(V(t_{i+1}) < V(t_{i})\). This demonstrates that the implementation adheres to the theoretical stability proof and that the STA drives the system to the origin in the \((\sigma,\dot{\sigma})\)-plane more aggressively than classic SMC.

### Tuning guidance

Tuning the STA gains \(K_{1}\) and \(K_{2}\) is crucial. In practice:

- **\(K_{1}\)** determines the magnitude of the continuous term. It should be larger than the maximum possible derivative of the disturbance to ensure finite‑time convergence. Increasing \(K_{1}\) accelerates convergence but can amplify control effort.
- **\(K_{2}\)** governs the integral action. A higher \(K_{2}\) increases the speed of the integral term, improving sliding accuracy, but excessive \(K_{2}\) may cause oscillations. Selecting \(K_{2}\approx K_{1}\) is common to balance the proportional and integral actions.

The configuration file allows setting `K1_init` and `K2_init` for the hybrid controller and similar parameters for the pure STA controller under the `gains` entry. The `dt` parameter controls integration accuracy.

------------------------------------------------------------------------

## Variant III: Adaptive SMC

### Adaptation law and dead zone

Adaptive SMC adjusts the switching gain \(K\) on‑line to compensate for unknown disturbance bounds. Rather than fixing \(K\) using the worst‑case disturbance, the controller updates \(K(t)\) according to an adaptation law that increases the gain when the system is far from the sliding manifold and decreases it when the state enters a neighbourhood of the manifold. This approach eliminates the need for a priori knowledge of the disturbance bound and avoids overly conservative gains \[7\]. In `adaptive_smc.py`, the `compute_control` method implements the adaptation:

1. When \(|\sigma|\) exceeds a specified **dead zone** (parameter `dead_zone`), the switching gain grows proportionally to \(|\sigma|\).  Increasing the gain outside the dead zone enlarges the disturbance bound and improves robustness when the state is far from the sliding manifold.  This piece‑wise adaptation strategy is supported by nonlinear control theory: adaptive sliding‑mode controllers that allow the gain to increase until the sliding mode occurs and then decrease once the state enters a neighbourhood of the manifold achieve semi‑global stability without requiring a priori disturbance bounds \[8\].
2. Inside the dead zone the gain is held constant or allowed to decay slowly.  Decreasing the gain in this neighbourhood prevents unnecessary wind‑up and reduces chattering caused by measurement noise.  The nominal gain value is recovered through a leak term (`leak_rate`) and the growth rate is limited by `adapt_rate_limit` to avoid abrupt changes.

The gain is confined between `K_min` and `K_max` to prevent unbounded growth. A leak term (`leak_rate`) pulls the gain back toward its nominal value and prevents indefinite wind‑up. An additional limit (`adapt_rate_limit`) restricts how quickly the gain can change, avoiding abrupt jumps during adaptation.

### Practical considerations

Adaptive SMC eliminates the need for prior knowledge of disturbance bounds and produces a continuous control signal, reducing chattering. However, it introduces additional parameters (adaptation rate, leak rate, dead zone) that require tuning and may yield slower transient response compared to fixed‑gain SMC if tuned conservatively.

------------------------------------------------------------------------

## Variant IV: Hybrid Adaptive–STA SMC

### Unified sliding surface and recentering

The hybrid controller combines the adaptive law with the super‑twisting algorithm using a **single sliding surface** that captures both pendulum dynamics and cart recentering.  By default the sliding surface uses absolute joint coordinates:

\[
\sigma = c_{1}\,(\dot{\theta}_{1} + \lambda_{1}\,\theta_{1}) + c_{2}\,(\dot{\theta}_{2} + \lambda_{2}\,\theta_{2}) + k_{c}\,(\dot{x} + \lambda_{c}\,x),
\]

where \(c_{i}>0\) and \(\lambda_{i}>0\) weight the pendulum angle and velocity errors, and \(k_{c}\), \(\lambda_{c}\) weight the cart velocity and position in the sliding manifold.  Selecting **positive coefficients** ensures that the sliding manifold is attractive and defines a stable reduced‑order error surface—this is a standard requirement in sliding‑mode design【895515998216162†L326-L329】.  The terms involving the cart state encourage the cart to recenter without destabilising the pendula.  The implementation also supports a **relative formulation** in which the second pendulum is represented by \(\theta_{2}-\theta_{1}\) and \(\dot{\theta}_{2}-\dot{\theta}_{1}\); users can enable this mode with `use_relative_surface=True` to study coupled pendulum dynamics.  Keeping both options accessible avoids hard‑coding a specific manifold and lets users explore alternative designs.

The PD recentering behaviour is further reinforced by separate proportional–derivative gains \(p_{\mathrm{gain}}\) and \(p_{\lambda}\) applied to the cart velocity and position.  These gains shape the transient response of the cart and are exposed as `cart_p_gain` and `cart_p_lambda` in the configuration.

### Super‑twisting with adaptive gains

The hybrid control input consists of an equivalent part, a **super‑twisting continuous term** and an **integral term**.  The continuous term uses the square‑root law from the STA, \(-k_{1}\sqrt{\|\sigma\|}\,\mathrm{sgn}(\sigma)\), while the integral term \(z\) obeys \(\dot{z} = -k_{2}\,\mathrm{sgn}(\sigma)\).  Both gains \(k_{1}\) and \(k_{2}\) adapt online according to the same dead‑zone logic as in the adaptive SMC: when \(|\sigma|\) exceeds the dead‑zone threshold, the gains increase proportionally to \(|\sigma|\); inside the dead zone they are held constant or allowed to decay slowly.  To prevent runaway adaptation the gains are clipped at configurable maxima ``k1_max`` and ``k2_max``, and the integral term ``u_int`` is limited by ``u_int_max``.  Separating these bounds from the actuator saturation ensures that adaptation can proceed even when the actuator saturates【895515998216162†L326-L329】.  The equivalent control term \(u_{\mathrm{eq}}\) is **enabled by default**; it can be disabled via `enable_equivalent=False` if a purely sliding‑mode law is desired.  This piece‑wise adaptation law is supported by recent research showing that the gain should increase until sliding occurs and then decrease once the trajectory enters a neighbourhood of the manifold to avoid over‑estimation【462167782799487†L186-L195】.

### Advantages and tuning

The hybrid adaptive–STA controller inherits the robustness of second‑order sliding mode and the flexibility of adaptive gain scheduling while remaining simpler than earlier dual‑surface designs.  Its unified sliding surface ensures consistent dynamics across all modes, and the adaptive gains allow the controller to handle unknown disturbance bounds without a priori tuning.  However, this comes at the expense of additional parameters: the sliding surface weights \(c_{1},c_{2},\lambda_{1},\lambda_{2},k_{c},\lambda_{c}\), the PD recentering gains \(p_{\mathrm{gain}},p_{\lambda}\), adaptation rates and dead‑zone widths.  Careful tuning of these parameters is essential to balance response speed, robustness and chattering.

------------------------------------------------------------------------

## New Section: Controller Configuration and `config.yaml`

The `config.yaml` file defines tunable parameters for each controller. Mapping these keys to the mathematical symbols used in the theory clarifies how to adjust the controllers in practice. Table 1–4 summarise the mappings for each variant.

### Classical SMC

| `config.yaml` key | Mathematical symbol(s) | Description |
|----|----|----|
| `gains` (in `controller_defaults`) | \(\lambda_{1},\lambda_{2},k_{1},k_{2},K,k_{\mathrm{d}}\) | Initial values for sliding surface weights (\(\lambda_{1},\lambda_{2}\)), velocity gains (\(k_{1},k_{2}\)), switching gain \(K\) and damping gain \(k_{\mathrm{d}}\). They appear in \(\sigma\) and \(u_{\mathrm{sw}}\). |
| `boundary_layer` | \(\epsilon\) | Half‑width of the boundary layer used in the saturation function. |
| `max_force` | Saturation limit | Maximum magnitude of the control input \(u\). |
| `controllability_threshold` | – | Lower bound on \(|L\cdot M^{-1}\cdot B|\) used to decide when to compute the equivalent control. If \(|L\cdot M^{-1}\cdot B|\) falls below this threshold, the feedforward term is disabled to avoid amplification of ill‑conditioned inversions.  Defaults to \(10^{-4}\) when omitted. |
<!-- Removed `rate_weight` and `use_adaptive_boundary` rows as these parameters are no longer used in the implementation. -->

### Super‑Twisting SMC

| `config.yaml` key | Mathematical symbol(s) | Description |
|----|----|----|
| `gains` | \(\lambda_{1},\lambda_{2},k_{1},K_{1},K_{2},k_{\mathrm{d}}\) | Sliding surface weights, velocity gains, super‑twisting proportional gain \(K_{1}\), integral gain \(K_{2}\) and optional damping gain. |
| `damping_gain` | \(k_{\mathrm{d}}\) | Linear damping added to the control law. |
| `dt` | \(\mathrm{d}t\) | Integration time step for updating the internal state \(z\). |
| `max_force` | Saturation limit | Maximum control magnitude. |
<!-- Removed `semi_implicit` and `rate_weight` parameters as they are no longer used. -->

### Adaptive SMC

| `config.yaml` key | Mathematical symbol(s) | Description |
|----|----|----|
| `gains` | \(\lambda_{1},\lambda_{2},k_{1},k_{2},K_{0}\) | Initial sliding surface and switching gain values. |
<!-- Removed `rate_weight` row; the updated controller does not include a control‑rate term. -->
| `leak_rate` | \(\alpha\) | Forgetting factor that allows the adaptive gain to decay when disturbances subside. |
| `dead_zone` | \(\delta\) | Dead‑zone width for suppressing gain growth when \(|\sigma|\) is small. |
| `adapt_rate_limit` | \(\Gamma_{\max}\) | Upper limit on how fast the gain can grow. |
| `K_{\min}`, `K_{\max}` | \(K_{\min},K_{\max}\) | Hard bounds on the adaptive gain. |
| `dt` | \(\mathrm{d}t\) | Time step for numerical integration. |
| `smooth_switch` | – | If true, uses a smooth transition function to improve continuity near switching events. |
| `boundary_layer` | \(\epsilon\) | Boundary layer width for the saturation function. |

### Hybrid Adaptive–STA SMC

| `config.yaml` key | Mathematical symbol(s) | Description |
|----|----|----|
| `gains` (in `controller_defaults`) | \(c_{1},\lambda_{1},c_{2},\lambda_{2}\) | Gains defining the sliding surfaces: \(c_{1}\), \(c_{2}\) scale the velocity terms and \(\lambda_{1},\lambda_{2}\) the position terms. |
| `max_force` | Saturation limit | Maximum cart force. |
| `dt` | \(\mathrm{d}t\) | Time step used for updating adaptive gains and the STA integrator. |
| `k1_init`, `k2_init` | \(k_{1}(0),k_{2}(0)\) | Initial values for the adaptive super‑twisting gains. |
| `gamma1`, `gamma2` | \(\gamma_{1},\gamma_{2}\) | Adaptation rates for \(k_{1}\) and \(k_{2}\) respectively. Larger values yield faster adaptation but can increase oscillatory behaviour. |
| `dead_zone` | \(\delta\) | Dead‑zone width preventing gain wind‑up due to noise. |
| `enable_equivalent` | – | If true, includes an equivalent control term computed from the system dynamics.  This option replaces the deprecated `use_equivalent` flag, which is still accepted as an alias.  The equivalent control is **enabled by default** in the revised implementation. |
| `use_relative_surface` | – | When true, defines the sliding surface using relative coordinates \(\theta_{2}-\theta_{1}\) and \(\dot{\theta}_{2}-\dot{\theta}_{1}\).  When false (default), uses absolute angles.  This switch allows users to explore alternative manifold definitions without modifying code. |
| `k1_max`, `k2_max` | – | Maximum allowed values for the adaptive gains \(k_{1}\) and \(k_{2}\).  Bounding these gains independently of the actuator limit prevents runaway adaptation and preserves stability【895515998216162†L326-L329】. |
| `u_int_max` | – | Maximum absolute value of the integral term in the super‑twisting algorithm.  Decoupling this bound from `max_force` avoids overly conservative integral clipping and improves robustness. |
| `damping_gain` | \(k_{\mathrm{d}}\) | Linear damping gain applied to the super‑twisting control. |
| `adapt_rate_limit` | \(\Gamma_{\max}\) | Maximum rate of change allowed for the adaptive super‑twisting gains. |
| `sat_soft_width` | \(\delta_{\mathrm{soft}}\) | Width of the soft saturation used in the adaptation law to smooth transitions near the dead zone. |
| `cart_gain` | \(k_{c}\) | Weight applied to the cart velocity and position in the sliding surface for recentering. |
| `cart_lambda` | \(\lambda_{c}\) | Rate applied to the cart position term in the sliding surface. |
| `cart_p_gain` | \(p_{\mathrm{gain}}\) | Proportional gain for the cart recentering term. |
| `cart_p_lambda` | \(p_{\lambda}\) | Derivative gain for the cart recentering term. |

These tables enable practitioners to relate the theoretical parameters (gains, boundary layer, adaptation rates) to the YAML file used to configure the controllers.

------------------------------------------------------------------------

## New Section: Robustness and Singularity Handling

High‑performance control of the DIP requires careful handling of numerical issues and singularities inherent in the dynamic model. The inertia matrix \M(q)\ can become ill‑conditioned when the pendulum angles approach certain configurations, leading to large rounding errors in its inversion. The implementation addresses these problems as follows:

- **Condition‑number checking:** The `_compute_equivalent_control` method in both `classic_smc.py` and `sta_smc.py` computes the condition number of \M(q)\ (`np.linalg.cond`). If the condition number exceeds a threshold (`singularity_cond_threshold` in `config.yaml`), the method logs a warning and uses a pseudo‑inverse instead of the standard inverse.
- **Matrix regularisation:** To prevent singularities due to modelling uncertainties, a small regularisation term \(\varepsilon I\) is added to \M(q)\ before inversion. This ensures that \(M(q)+\varepsilon I\) is always invertible, albeit with some approximation error.
- **Safe inversion with pseudo‑inverse:** When the matrix is ill‑conditioned, the code uses `np.linalg.pinv`, which computes the Moore–Penrose pseudo‑inverse and yields a least‑squares solution that minimises the effect of noise.
- **Regularisation justification:**  Adding a positive constant to the diagonal of a symmetric matrix shifts all of its eigenvalues upward and can convert an indefinite matrix into a positive‑definite one【385796022798831†L145-L149】.  This mathematical result justifies the use of the diagonal regularisation term \(\varepsilon I\): by perturbing \(M(q)\) in this way, \(M(q)+\varepsilon I\) remains invertible even when \(M(q)\) is nearly singular, though at the cost of a small approximation error.
- **Fallback control:** If the pseudo‑inverse computation still fails (for example, if the system becomes uncontrollable), the controller saturates the output to zero and reports failure rather than producing unbounded values. This conservative action prevents destabilisation.

By systematically checking for singularities and regularising the matrix inversion, the project ensures that the control law remains well‑defined even when the physical system operates near its limits or when the model parameters are uncertain.

------------------------------------------------------------------------

## Comparative Summary and Recommendations

The four implemented SMC variants offer a spectrum of robustness, smoothness and complexity. **Classic SMC** provides a simple and effective baseline; it achieves finite‑time convergence but suffers from chattering and requires known disturbance bounds. **Super‑twisting SMC** adds a second‑order sliding mechanism that reduces chattering and yields continuous control; it demands tuning of two gains and a higher computational cost. **Adaptive SMC** learns the disturbance bound on‑line, eliminating the need to specify \(K\) a priori; its continuous control avoids chattering but involves more parameters and possible slower response. **Hybrid adaptive–STA** combines adaptive gain adjustment with the super‑twisting algorithm while relying on a **single sliding surface**.  This unified approach retains the robustness and smoothness of second‑order sliding mode, allows the gains to adapt to unknown disturbances, and simplifies the switching logic compared with earlier dual‑surface designs.  The trade‑off is a larger set of tunable parameters (sliding surface weights, adaptation rates, dead‑zone widths and recentering gains), making careful tuning essential.

For a given DIP application, the choice among these controllers should consider the available actuator bandwidth, desired response speed and tolerance to chattering.  The configuration tables provide a starting point for tuning, and the robust implementation ensures safe operation even under parameter variations and modelling uncertainties.

------------------------------------------------------------------------

## References

\[1\] A. Boubaker, “The inverted pendulum: a fundamental benchmark in control theory and robotics,” *International Journal of Automation & Control*, vol. 8, no. 2, pp. 94–115, 2014.

\[2\] I. Irfan, U. Irfan, M. W. Ahmad and A. Saleem, “Control strategies for a double inverted pendulum system,” *PLOS ONE*, vol. 18, no. 3, p. e0282522, 2023.

\[3\] H. Dong, M. Zhu and S. Cui, “Integral sliding mode control for nonlinear systems with matched and unmatched perturbations,” *IEEE Transactions on Automatic Control*, vol. 57, no. 11, pp. 2986–2991, 2012.

\[4\] S. Saha and S. Banerjee, “Methodologies of chattering attenuation in sliding mode controller,” *International Journal of Hybrid Information Technology*, vol. 9, no. 2, pp. 221–232, 2016.

\[5\] A. Parvat, P. G. Kadam and V. R. Prasanna, “Design and implementation of sliding mode controller for level control,” in *Proc. Int. Conf. Control, Instrumentation, Energy and Communication*, 2013, pp. 71–75.

\[6\] S. u. Din, A. Hussain, M. F. Iftikhar and M. A. Rahman, “Smooth super‑twisting sliding mode control for the class of underactuated systems,” *PLOS ONE*, vol. 13, no. 9, p. e0204095, 2018.

\[7\] R. Roy, “Adaptive sliding mode control without knowledge of uncertainty bounds,” *International Journal of Control*, vol. 93, no. 12, pp. 3051–3062, 2020.

\[8\] Y. Sun, Y. Wang and B. Wu, “Adaptive gain sliding mode control for uncertain nonlinear systems using barrier‑like functions,” *Nonlinear Dynamics*, vol. 99, no. 4, pp. 2775–2787, 2020.

\[9\] A. Levant and V. Orlov, “Sliding mode manifolds and their design,” in *Recent Advances in Sliding Modes: Theory and Applications*, IOP Publishing, 2017, ch. 1, pp. 1–31.

\[10\] S. Li and M. Hibi, “Positive definiteness via off‑diagonal scaling of a symmetric indefinite matrix,” *Applied Mathematics and Computation*, vol. 371, p. 124959, 2020.

------------------------------------------------------------------------