SMC Theory
==========

Sliding Mode Control for a Double‑Inverted Pendulum: Bridging Theory and Implementation

Introduction – Why Sliding Mode Control?
----------------------------------------

The double‑inverted pendulum (DIP) is widely recognised as a **canonical benchmark** for the study of nonlinear, under‑actuated control systems. Inverted‑pendulum experiments have been used for decades to teach and validate control techniques; variants such as the rotational single‑arm pendulum, the cart pendulum and the **double inverted pendulum** offer escalating control challenges, and the inverted pendulum is often described as the most fundamental benchmark for robotics and control education [1]. In the DIP, two pendula are attached in series to a horizontally moving cart and only the cart is actuated. Consequently the system has fewer actuators than degrees of freedom and is both **under‑actuated** and **strongly nonlinear** [2]. Conventional linear controllers struggle with large deflections, parameter variations and model uncertainty.

Sliding Mode Control (SMC) addresses these issues by forcing the system state onto a pre‑defined **sliding manifold**. When the state reaches this manifold, the resulting closed‑loop dynamics become insensitive to matched disturbances and uncertainties [3]. The control law compensates modelling errors through the control input channel so that the plant behaves according to the reduced‑order dynamics on the manifold [3]. This robustness and finite‑time convergence make SMC attractive for under‑actuated systems such as the DIP. However, the discontinuous switching law of classic SMC induces **chattering**, a high‑frequency oscillation caused by rapid control switching when the state crosses the sliding surface. Chattering increases control effort, excites unmodelled high‑frequency modes and can cause wear in actuators. Introducing a boundary layer around the sliding surface alleviates chattering but enlarges the tracking error and slows the response [4].

To explore different trade‑offs between robustness, smoothness and complexity, this project implements four SMC variants – **classic (first‑order)**, **super‑twisting algorithm (STA)**, **adaptive SMC**, and **hybrid adaptive–STA**. Each variant is implemented in the provided Python code (``classic_smc.py``, ``sta_smc.py``, ``adaptive_smc.py``, ``hybrid_adaptive_sta_smc.py``), and the following sections link the theory to these implementations.

Structure of the report
^^^^^^^^^^^^^^^^^^^^^^^

The report is organised as follows. Each controller variant is presented with a concise theoretical background, a description of its implementation in the project, and an analysis of its practical implications. New sections map configuration parameters to mathematical symbols and discuss robustness issues such as singularity handling. A glossary of symbols and tables summarise the key results.

Variant I: Classic Sliding Mode Control (SMC)
----------------------------------------------

Principles and sliding surface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Classic SMC designs a linear **sliding surface** that combines position and velocity errors. For second‑order systems such as the DIP, the surface is typically a linear combination of the tracking error and its first derivative [5]. In this report the sliding surface is:

.. math::

    \sigma = \lambda_{1}\,\theta_{1} + \lambda_{2}\,\theta_{2} + k_{1}\,\dot{\theta}_{1} + k_{2}\,\dot{\theta}_{2}

where :math:`\theta_{i}` are the pendulum angles, :math:`\dot{\theta}_{i}` their angular velocities, and :math:`\lambda_{i}>0` are design gains. The implementation computes the sliding variable in the ``_compute_sliding_surface`` method of ``classic_smc.py``:

*"sigma = self.lam1 * theta1 + self.lam2 * theta2 + self.k1 * dtheta1 + self.k2 * dtheta2"* (see ``classic_smc.py``), directly matching the equation above.

Control law: equivalent and switching parts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The control input :math:`u` is decomposed into an **equivalent control** :math:`u_{\mathrm{eq}}` that cancels the nominal dynamics and a **robust switching** term :math:`u_{\mathrm{sw}}` that drives :math:`\sigma` toward zero. This decomposition, often written as :math:`u = u_{eq} + u_{sw}`, is standard in sliding‑mode design [5]:

.. math::

    u = u_{eq} - K\, \text{sat}\left( \frac{\sigma}{\epsilon} \right) - k_{d}\,\sigma

Equivalent control computation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In ``classic_smc.py`` the ``_compute_equivalent_control`` method solves the dynamic equation of the DIP:

.. math::

    M(q)\ddot{q} + C\left( q,\dot{q} \right)\dot{q} + G(q) = B\, u

for the **cart force** :math:`u` required to satisfy :math:`\dot{\sigma}=0`. The inertia matrix :math:`M(q)` is computed from the physics parameters and then **regularised** by adding a small diagonal term. Before inversion the code checks the condition number of :math:`M(q)`; if it is ill‑conditioned the method resorts to the pseudo‑inverse (``np.linalg.pinv``) to avoid numerical singularities. This careful handling prevents blow‑ups when the pendulum angles approach singular configurations. The resulting :math:`u_{\mathrm{eq}}` is limited by the ``max_force`` parameter in the configuration.

Boundary layer and saturation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The switching term uses a **saturation function** to approximate the discontinuous sign function within a small **boundary layer** of width :math:`\epsilon`. Such smoothing reduces the chattering inherent in the discontinuous sign function, but it comes at a cost: introducing a boundary layer increases the tracking error and slows the response [4]. In the code, the ``saturate`` utility implements two approximations—a hyperbolic tangent (``method='tanh'``) and a linear clipping (``method='linear'``)—that smooth the sign function. Both approximations approach the discontinuous sign outside the boundary layer and produce smoother transitions inside.

Numerical robustness
^^^^^^^^^^^^^^^^^^^^

The classic controller includes several robustness enhancements:

- **Condition‑number checking and regularisation:** The inertia matrix :math:`M(q)` is checked for ill‑conditioning and regularised by adding a small diagonal term (:math:`\varepsilon I`). When ill‑conditioned, a pseudo‑inverse is used to compute the equivalent control.
- **Fallback control:** If the matrix inversion still fails due to singularity, the controller saturates the output to zero and returns an error flag, preventing instability.
- **Actuator saturation:** The control input is saturated by ``max_force`` to respect actuator limits.

These features make the classic SMC implementation stable and safe even when the model parameters deviate from their nominal values.

Variant II: Super‑Twisting Algorithm (STA) SMC
----------------------------------------------

Theory and formulation
^^^^^^^^^^^^^^^^^^^^^^

The **super‑twisting algorithm** (STA) is a second‑order sliding mode technique that suppresses chattering by applying the discontinuity on the **derivative** of the control signal rather than on the control itself. By moving the discontinuity to the derivative, the control input becomes continuous, which greatly reduces high‑frequency oscillations while preserving the robustness of sliding‑mode control and guaranteeing finite‑time convergence to the sliding set [6]. The sliding variable :math:`\sigma` for the STA controller is similar to the classic one but is scaled by separate gains. In ``sta_smc.py`` it is computed as:

.. math::

    \sigma = k_{1}\,\left( {\dot{\theta}}_{1} + \lambda_{1}\,\theta_{1} \right) + k_{2}\,\left( {\dot{\theta}}_{2} + \lambda_{2}\,\theta_{2} \right)

The STA control comprises two components:

1. **Continuous term** :math:`u_{c}=-K_{1}\sqrt{|\sigma|}\,\text{sgn}(\sigma)`; this term acts like a damping force proportional to :math:`\sqrt{|\sigma|}`.
2. **Integral term** :math:`u_{i}` generated by integrating the sign of :math:`\sigma`: the internal state :math:`z` is updated as :math:`z\leftarrow z - K_{2}\,\text{sgn}(\sigma)\,\mathrm{d}t`. The integral of the discontinuity produces a continuous control signal, effectively moving the discontinuity to its derivative.

The total control is :math:`u = u_{\mathrm{eq}} + u_{c} + z`. Because the discontinuity is applied to the derivative rather than to the control itself, the resulting control law is continuous and enforces finite‑time convergence of both the sliding variable and its derivative [6]. In our implementation the internal integrator for :math:`z` is updated explicitly using the time step ``dt``; the previously supported ``semi_implicit`` configuration key has been removed from the code and should not appear in ``config.yaml``.

Lyapunov stability and numerical verification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A Lyapunov function :math:`V=\tfrac12\sigma^{2}` can be shown to decrease along system trajectories under the STA law, guaranteeing finite‑time convergence of both :math:`\sigma` and :math:`\dot{\sigma}` to zero. The project includes a test, ``test_lyapunov_decrease_sta`` in ``tests/test_core/test_lyapunov.py``, that numerically confirms this property. The test evaluates :math:`V` at successive time steps and asserts that :math:`V(t_{i+1}) < V(t_{i})`. This demonstrates that the implementation adheres to the theoretical stability proof and that the STA drives the system to the origin in the :math:`(\sigma,\dot{\sigma})`-plane more aggressively than classic SMC.

Tuning guidance
^^^^^^^^^^^^^^^

Tuning the STA gains :math:`K_{1}` and :math:`K_{2}` is crucial. In practice:

- **K₁** determines the magnitude of the continuous term. It should be larger than the maximum possible derivative of the disturbance to ensure finite‑time convergence. Increasing :math:`K_{1}` accelerates convergence but can amplify control effort.
- **K₂** governs the integral action. A higher :math:`K_{2}` increases the speed of the integral term, improving sliding accuracy, but excessive :math:`K_{2}` may cause oscillations. Selecting :math:`K_{2}\approx K_{1}` is common to balance the proportional and integral actions.

The configuration file allows setting ``K1_init`` and ``K2_init`` for the hybrid controller and similar parameters for the pure STA controller under the ``gains`` entry. The ``dt`` parameter controls integration accuracy.

Variant III: Adaptive SMC
-------------------------

Adaptation law and dead zone
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Adaptive SMC adjusts the switching gain :math:`K` on‑line to compensate for unknown disturbance bounds. Rather than fixing :math:`K` using the worst‑case disturbance, the controller updates :math:`K(t)` according to an adaptation law that increases the gain when the system is far from the sliding manifold and decreases it when the state enters a neighbourhood of the manifold. This approach eliminates the need for a priori knowledge of the disturbance bound and avoids overly conservative gains [7]. In ``adaptive_smc.py``, the ``compute_control`` method implements the adaptation:

1. When :math:`|\sigma|` exceeds a specified **dead zone** (parameter ``dead_zone``), the switching gain grows proportionally to :math:`|\sigma|`. Increasing the gain outside the dead zone enlarges the disturbance bound and improves robustness when the state is far from the sliding manifold. This piece‑wise adaptation strategy is supported by nonlinear control theory: adaptive sliding‑mode controllers that allow the gain to increase until the sliding mode occurs and then decrease once the state enters a neighbourhood of the manifold achieve semi‑global stability without requiring a priori disturbance bounds [8].

2. Inside the dead zone the gain is held constant or allowed to decay slowly. Decreasing the gain in this neighbourhood prevents unnecessary wind‑up and reduces chattering caused by measurement noise. The nominal gain value is recovered through a leak term (``leak_rate``) and the growth rate is limited by ``adapt_rate_limit`` to avoid abrupt changes.

The gain is confined between ``K_min`` and ``K_max`` to prevent unbounded growth. A leak term (``leak_rate``) pulls the gain back toward its nominal value and prevents indefinite wind‑up. An additional limit (``adapt_rate_limit``) restricts how quickly the gain can change, avoiding abrupt jumps during adaptation.

Practical considerations
^^^^^^^^^^^^^^^^^^^^^^^

Adaptive SMC eliminates the need for prior knowledge of disturbance bounds and produces a continuous control signal, reducing chattering. However, it introduces additional parameters (adaptation rate, leak rate, dead zone) that require tuning and may yield slower transient response compared to fixed‑gain SMC if tuned conservatively.

Variant IV: Hybrid Adaptive–STA SMC
-----------------------------------

Unified sliding surface and recentering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The hybrid controller combines the adaptive law with the super‑twisting algorithm using a **single sliding surface** that captures both pendulum dynamics and cart recentering. By default the sliding surface uses absolute joint coordinates:

.. math::

    \sigma = c_{1}\,(\dot{\theta}_{1} + \lambda_{1}\,\theta_{1}) + c_{2}\,(\dot{\theta}_{2} + \lambda_{2}\,\theta_{2}) + k_{c}\,(\dot{x} + \lambda_{c}\,x)

where :math:`c_{i}>0` and :math:`\lambda_{i}>0` weight the pendulum angle and velocity errors, and :math:`k_{c}`, :math:`\lambda_{c}` weight the cart velocity and position in the sliding manifold. Selecting **positive coefficients** ensures that the sliding manifold is attractive and defines a stable reduced‑order error surface—this is a standard requirement in sliding‑mode design. The terms involving the cart state encourage the cart to recenter without destabilising the pendula. The implementation also supports a **relative formulation** in which the second pendulum is represented by :math:`\theta_{2}-\theta_{1}` and :math:`\dot{\theta}_{2}-\dot{\theta}_{1}`; users can enable this mode with ``use_relative_surface=True`` to study coupled pendulum dynamics. Keeping both options accessible avoids hard‑coding a specific manifold and lets users explore alternative designs.

The PD recentering behaviour is further reinforced by separate proportional–derivative gains :math:`p_{\mathrm{gain}}` and :math:`p_{\lambda}` applied to the cart velocity and position. These gains shape the transient response of the cart and are exposed as ``cart_p_gain`` and ``cart_p_lambda`` in the configuration.

Super‑twisting with adaptive gains
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The hybrid control input consists of an equivalent part, a **super‑twisting continuous term** and an **integral term**. The continuous term uses the square‑root law from the STA, :math:`-k_{1}\sqrt{|\sigma|}\,\text{sgn}(\sigma)`, while the integral term :math:`z` obeys :math:`\dot{z} = -k_{2}\,\text{sgn}(\sigma)`. Both gains :math:`k_{1}` and :math:`k_{2}` adapt online according to the same dead‑zone logic as in the adaptive SMC: when :math:`|\sigma|` exceeds the dead‑zone threshold, the gains increase proportionally to :math:`|\sigma|`; inside the dead zone they are held constant or allowed to decay slowly. To prevent runaway adaptation the gains are clipped at configurable maxima ``k1_max`` and ``k2_max``, and the integral term ``u_int`` is limited by ``u_int_max``. Separating these bounds from the actuator saturation ensures that adaptation can proceed even when the actuator saturates. The equivalent control term :math:`u_{\mathrm{eq}}` is **enabled by default**; it can be disabled via ``enable_equivalent=False`` if a purely sliding‑mode law is desired. This piece‑wise adaptation law is supported by recent research showing that the gain should increase until sliding occurs and then decrease once the trajectory enters a neighbourhood of the manifold to avoid over‑estimation.

Advantages and tuning
^^^^^^^^^^^^^^^^^^^^

The hybrid adaptive–STA controller inherits the robustness of second‑order sliding mode and the flexibility of adaptive gain scheduling while remaining simpler than earlier dual‑surface designs. Its unified sliding surface ensures consistent dynamics across all modes, and the adaptive gains allow the controller to handle unknown disturbance bounds without a priori tuning. However, this comes at the expense of additional parameters: the sliding surface weights :math:`c_{1},c_{2},\lambda_{1},\lambda_{2},k_{c},\lambda_{c}`, the PD recentering gains :math:`p_{\mathrm{gain}},p_{\lambda}`, adaptation rates and dead‑zone widths. Careful tuning of these parameters is essential to balance response speed, robustness and chattering.

Controller Configuration and config.yaml
----------------------------------------

The ``config.yaml`` file defines tunable parameters for each controller. Mapping these keys to the mathematical symbols used in the theory clarifies how to adjust the controllers in practice.

Classical SMC
^^^^^^^^^^^^^

.. list-table:: Classical SMC Configuration
   :header-rows: 1
   :widths: 30 30 40

   * - config.yaml key
     - Mathematical symbol(s)
     - Description
   * - gains (in controller_defaults)
     - :math:`\lambda_{1},\lambda_{2},k_{1},k_{2},K,k_{\mathrm{d}}`
     - Initial values for sliding surface weights, velocity gains, switching gain and damping gain
   * - boundary_layer
     - :math:`\epsilon`
     - Half‑width of the boundary layer used in the saturation function
   * - max_force
     - Saturation limit
     - Maximum magnitude of the control input :math:`u`
   * - controllability_threshold
     - –
     - Lower bound on :math:`|L\cdot M^{-1}\cdot B|` used to decide when to compute the equivalent control

Super‑Twisting SMC
^^^^^^^^^^^^^^^^^

.. list-table:: Super-Twisting SMC Configuration
   :header-rows: 1
   :widths: 30 30 40

   * - config.yaml key
     - Mathematical symbol(s)
     - Description
   * - gains
     - :math:`\lambda_{1},\lambda_{2},k_{1},K_{1},K_{2},k_{\mathrm{d}}`
     - Sliding surface weights, velocity gains, super‑twisting proportional and integral gains
   * - damping_gain
     - :math:`k_{\mathrm{d}}`
     - Linear damping added to the control law
   * - dt
     - :math:`\mathrm{d}t`
     - Integration time step for updating the internal state :math:`z`
   * - max_force
     - Saturation limit
     - Maximum control magnitude

Adaptive SMC
^^^^^^^^^^^^

.. list-table:: Adaptive SMC Configuration
   :header-rows: 1
   :widths: 30 30 40

   * - config.yaml key
     - Mathematical symbol(s)
     - Description
   * - gains
     - :math:`\lambda_{1},\lambda_{2},k_{1},k_{2},K_{0}`
     - Initial sliding surface and switching gain values
   * - leak_rate
     - :math:`\alpha`
     - Forgetting factor that allows the adaptive gain to decay when disturbances subside
   * - dead_zone
     - :math:`\delta`
     - Dead‑zone width for suppressing gain growth when :math:`|\sigma|` is small
   * - adapt_rate_limit
     - :math:`\Gamma_{\max}`
     - Upper limit on how fast the gain can grow
   * - K_min, K_max
     - :math:`K_{\min},K_{\max}`
     - Hard bounds on the adaptive gain
   * - dt
     - :math:`\mathrm{d}t`
     - Time step for numerical integration
   * - smooth_switch
     - –
     - If true, uses a smooth transition function to improve continuity near switching events
   * - boundary_layer
     - :math:`\epsilon`
     - Boundary layer width for the saturation function

Robustness and Singularity Handling
-----------------------------------

High‑performance control of the DIP requires careful handling of numerical issues and singularities inherent in the dynamic model. The inertia matrix :math:`M(q)` can become ill‑conditioned when the pendulum angles approach certain configurations, leading to large rounding errors in its inversion. The implementation addresses these problems as follows:

- **Condition‑number checking:** The ``_compute_equivalent_control`` method in both ``classic_smc.py`` and ``sta_smc.py`` computes the condition number of :math:`M(q)` (``np.linalg.cond``). If the condition number exceeds a threshold (``singularity_cond_threshold`` in ``config.yaml``), the method logs a warning and uses a pseudo‑inverse instead of the standard inverse.
- **Matrix regularisation:** To prevent singularities due to modelling uncertainties, a small regularisation term :math:`\varepsilon I` is added to :math:`M(q)` before inversion. This ensures that :math:`M(q)+\varepsilon I` is always invertible, albeit with some approximation error.
- **Safe inversion with pseudo‑inverse:** When the matrix is ill‑conditioned, the code uses ``np.linalg.pinv``, which computes the Moore–Penrose pseudo‑inverse and yields a least‑squares solution that minimises the effect of noise.
- **Regularisation justification:** Adding a positive constant to the diagonal of a symmetric matrix shifts all of its eigenvalues upward and can convert an indefinite matrix into a positive‑definite one. This mathematical result justifies the use of the diagonal regularisation term :math:`\varepsilon I`: by perturbing :math:`M(q)` in this way, :math:`M(q)+\varepsilon I` remains invertible even when :math:`M(q)` is nearly singular, though at the cost of a small approximation error.
- **Fallback control:** If the pseudo‑inverse computation still fails (for example, if the system becomes uncontrollable), the controller saturates the output to zero and reports failure rather than producing unbounded values. This conservative action prevents destabilisation.

By systematically checking for singularities and regularising the matrix inversion, the project ensures that the control law remains well‑defined even when the physical system operates near its limits or when the model parameters are uncertain.

Comparative Summary and Recommendations
---------------------------------------

The four implemented SMC variants offer a spectrum of robustness, smoothness and complexity. **Classic SMC** provides a simple and effective baseline; it achieves finite‑time convergence but suffers from chattering and requires known disturbance bounds. **Super‑twisting SMC** adds a second‑order sliding mechanism that reduces chattering and yields continuous control; it demands tuning of two gains and a higher computational cost. **Adaptive SMC** learns the disturbance bound on‑line, eliminating the need to specify :math:`K` a priori; its continuous control avoids chattering but involves more parameters and possible slower response. **Hybrid adaptive–STA** combines adaptive gain adjustment with the super‑twisting algorithm while relying on a **single sliding surface**. This unified approach retains the robustness and smoothness of second‑order sliding mode, allows the gains to adapt to unknown disturbances, and simplifies the switching logic compared with earlier dual‑surface designs. The trade‑off is a larger set of tunable parameters (sliding surface weights, adaptation rates, dead‑zone widths and recentering gains), making careful tuning essential.

For a given DIP application, the choice among these controllers should consider the available actuator bandwidth, desired response speed and tolerance to chattering. The configuration tables provide a starting point for tuning, and the robust implementation ensures safe operation even under parameter variations and modelling uncertainties.

References
----------

[1] A. Boubaker, "The inverted pendulum: a fundamental benchmark in control theory and robotics," *International Journal of Automation & Control*, vol. 8, no. 2, pp. 94–115, 2014.

[2] I. Irfan, U. Irfan, M. W. Ahmad and A. Saleem, "Control strategies for a double inverted pendulum system," *PLOS ONE*, vol. 18, no. 3, p. e0282522, 2023.

[3] H. Dong, M. Zhu and S. Cui, "Integral sliding mode control for nonlinear systems with matched and unmatched perturbations," *IEEE Transactions on Automatic Control*, vol. 57, no. 11, pp. 2986–2991, 2012.

[4] S. Saha and S. Banerjee, "Methodologies of chattering attenuation in sliding mode controller," *International Journal of Hybrid Information Technology*, vol. 9, no. 2, pp. 221–232, 2016.

[5] A. Parvat, P. G. Kadam and V. R. Prasanna, "Design and implementation of sliding mode controller for level control," in *Proc. Int. Conf. Control, Instrumentation, Energy and Communication*, 2013, pp. 71–75.

[6] S. u. Din, A. Hussain, M. F. Iftikhar and M. A. Rahman, "Smooth super‑twisting sliding mode control for the class of underactuated systems," *PLOS ONE*, vol. 13, no. 9, p. e0204095, 2018.

[7] R. Roy, "Adaptive sliding mode control without knowledge of uncertainty bounds," *International Journal of Control*, vol. 93, no. 12, pp. 3051–3062, 2020.

[8] Y. Sun, Y. Wang and B. Wu, "Adaptive gain sliding mode control for uncertain nonlinear systems using barrier‑like functions," *Nonlinear Dynamics*, vol. 99, no. 4, pp. 2775–2787, 2020.
