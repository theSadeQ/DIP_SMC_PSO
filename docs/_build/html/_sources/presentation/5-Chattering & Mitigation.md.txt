**An Analysis of Chattering Phenomena and Mitigation Strategies in a Sliding Mode Control Implementation for a Double Inverted Pendulum**

## Abstract

Sliding‑mode control (SMC) provides robustness against matched disturbances by enforcing a sliding motion on a properly chosen manifold. A major practical drawback of classical SMC is **chattering**—high‑frequency oscillations in the control input arising from the discontinuous switching law. This report investigates chattering in a double inverted pendulum and evaluates four mitigation strategies: a classical SMC with a boundary layer, a continuous **super‑twisting** algorithm (STA), an **adaptive** SMC that automatically adjusts the switching gain, and a **hybrid adaptive–STA** controller. We derive the system dynamics from first principles, describe the simulation methodology, and generate quantitative performance metrics (tracking error, control effort and chattering index). Simulations show that the hybrid controller achieves the smallest root‑mean‑square error and control effort while keeping chattering moderate, whereas the classical SMC exhibits significant chattering and large control effort.

## 1 Introduction

The double inverted pendulum on a cart is a canonical benchmark for **under‑actuated** and **non‑linear** control systems. It consists of two pendulums attached serially to a movable cart; only the cart is actuated. Stabilising both pendulums in their upright positions requires counteracting gravity, coupling between the links and the cart, and unmodelled friction. Sliding‑mode control is attractive because it ensures robustness to parameter uncertainties and bounded disturbances by driving a sliding variable to zero with a discontinuous switching law. However, the discontinuity excites unmodelled high‑frequency dynamics and causes the control input to oscillate rapidly. These oscillations, termed **chattering**, lead to actuator wear, heating and audible noise and degrade tracking performance. This report analyses chattering in the project’s SMC implementation, formulates the mathematical model of the double inverted pendulum, and systematically evaluates four strategies to reduce chattering. Section 2 derives the equations of motion and defines the control objective; Section 3 describes the simulation framework; Sections 4–7 analyse each controller in turn; Section 8 presents a quantitative comparison and frequency analysis; and Section 9 summarises the findings.

## 2 System Modelling and Problem Formulation

### 2.1 Equations of Motion

The double inverted pendulum comprises a cart of mass \\m_c\\ carrying two pendulums with masses \\m_1\\ and \\m_2\\, lengths \\L_1\\ and \\L_2\\, centres of mass \\l\_{c1}\\ and \\l\_{c2}\\ and inertias \\I_1\\ and \\I_2\\. Let \\x\\ denote the cart position, \\\theta_1\\ the angle of the first pendulum relative to the vertical and \\\theta_2\\ the absolute angle of the second pendulum. The state vector is

    x = \left\lbrack x,\mspace{6mu}\theta_{1},\mspace{6mu}\theta_{2},\mspace{6mu}\dot{x},\mspace{6mu}{\dot{\theta}}_{1},\mspace{6mu}{\dot{\theta}}_{2} \right\rbrack^{\top}.

Applying the Lagrangian formalism yields two coupled, non‑linear equations of motion (the cart dynamics is affected only by friction). For brevity only the pendulum equations are shown; they describe the rotational dynamics of the two links \[1\]:

    \left( m_{1} + m_{2} \right)L_{1}{\ddot{\theta}}_{1} + m_{2}L_{2}{\ddot{\theta}}_{2}\cos\left( \theta_{1} - \theta_{2} \right) + m_{2}L_{2}{\dot{\theta}}_{2}^{2}\sin\left( \theta_{1} - \theta_{2} \right)\cos\left( \theta_{1} - \theta_{2} \right) + g\left( m_{1} + m_{2} \right)\sin\theta_{1} = 0,
    m_{2}L_{2}{\ddot{\theta}}_{2} + m_{2}L_{1}{\ddot{\theta}}_{1}\cos\left( \theta_{1} - \theta_{2} \right) - m_{2}L_{1}{\dot{\theta}}_{1}^{2}\sin\left( \theta_{1} - \theta_{2} \right) + gm_{2}\sin\theta_{2} = 0.

These equations highlight the strong coupling between the pendulums: accelerations of one link appear in the dynamics of the other. In matrix form the full model in the code is expressed as

    H(q)\ddot{q} + C\left( q,\dot{q} \right)\dot{q} + G(q) = B\, u,

with \\q=

\$\$x,\\\theta_1,\\\theta_2\$\$

^\top\\, inertia matrix \\H(q)\\, damping and centripetal matrix \\C(q,\dot{q})\\, gravity vector \\G(q)\\, input matrix \\B=

``` math
1,0,0
```

^\top\\ and control input \\u\\ (force applied to the cart). In the implementation the matrices are computed by `compute_matrices_numba` in `src/core/dynamics.py`. The control objective is to drive both pendulums to the upright equilibrium (\\\theta_1=\theta_2=0\\) while keeping the cart near the origin (\\x=0\\).

### 2.2 Sliding Variable

All controllers studied here derive a scalar **sliding variable** \\\sigma\\ that combines angular positions and velocities. In the classical and adaptive controllers the sliding surface is defined as

    \sigma = k_{1}\,{\dot{\theta}}_{1} + k_{2}\,{\dot{\theta}}_{2} + \lambda_{1}\,\theta_{1} + \lambda_{2}\,\theta_{2},

where \\k_1,k_2\\ and \\\lambda_1,\lambda_2\\ are positive gains. When \\\sigma\\ is driven to zero, both angular errors and velocities are driven to zero, ensuring the pendulums remain upright. The super‑twisting and hybrid controllers use a slightly modified sliding surface but follow the same principle.

## 3 Simulation Methodology

Simulations were performed using the Python environment provided by the project. The double inverted pendulum dynamics were integrated with a fourth‑order Runge–Kutta solver (`step_rk4_numba`) at a time step \\\mathrm{d}t=0.001\\ s for a duration of \\10\\ s. The initial state was chosen as \\x=0\\, \\\theta_1=0.1\\ rad, \\\theta_2=-0.1\\ rad and zero velocities; this represents two slightly perturbed pendulums. Each controller was tuned with the default gains from `config.yaml` and run under identical conditions. Actuator saturation was enforced with a maximum force of \\150\\ N. Performance was evaluated using three quantitative metrics:

- **Tracking precision:** the root‑mean‑square error (RMSE) of \\(\theta_1,\theta_2)\\ from the upright position.
- **Control effort:** the integral of the squared control input \\\int u(t)^2\\mathrm{d}t\\.
- **Chattering index:** the total variation of the control signal \\\sum\_{i}\|u\_{i+1}-u_i\|\\, which measures high‑frequency oscillations.

In addition, the control signals were analysed in the frequency domain using the discrete Fourier transform to visualise how mitigation strategies shift energy to lower frequencies.

## 4 Classic Sliding Mode Control

### 4.1 Origin of Chattering

Classical SMC splits the control law into an **equivalent term** that cancels the nominal dynamics and a **switching term** that rejects disturbances. The switching term uses a discontinuous sign function \\\mathrm{sgn}(\sigma)\\ to force the sliding variable toward zero. Any sampling delay, actuator lag or unmodelled high‑frequency dynamics prevents the system from following the ideal discontinuous control and instead produces rapid oscillations. The switching gain \\K\\ must exceed the disturbance bound to guarantee robustness, but a larger gain amplifies the amplitude of these oscillations. Chattering therefore arises from the combination of a discontinuous control law and practical limitations in sensors and actuators.

Chattering arises because any sampling delay, actuator lag or unmodelled fast dynamics prevents the plant from following the ideal discontinuous control and instead produces oscillations with finite frequency and amplitude; furthermore, the amplitude of these oscillations is proportional to the magnitude of the discontinuous switching term \[3\].

### 4.2 Implementation and Boundary Layer Approximation

In the project (`src/controllers/classic_smc.py`) the sliding surface is implemented as a linear combination of joint angles and velocities. The equivalent control \\u\_{\mathrm{eq}}\\ is computed by inverting the inertia matrix \\H(q)\\; the switching term uses a continuous approximation of the sign function implemented in `src/utils/control_primitives.py` as the **saturation function**

    sat(\sigma/\epsilon) = \left\{ \begin{matrix}
    \tanh(\sigma/\epsilon), & \text{if method~=~“tanh”}, \\
    clip(\sigma/\epsilon, - 1,1), & \text{if method~=~“linear”},
    \end{matrix} \right.\ 

where \\\epsilon\>0\\ is the boundary‑layer width. A smaller \\\epsilon\\ yields a steeper transition and better accuracy but re‑introduces chattering; a larger \\\epsilon\\ smooths the control but causes a steady‑state error because the system state is only guaranteed to converge to \\\|\sigma\| \le \epsilon\\.

### 4.3 Physical Consequences of Chattering

Chattering is not merely a numerical artifact. Rapid switching of the control signal can excite unmodelled flexible modes of the mechanical structure, leading to vibrations and audible noise. In electrical drives the high‑frequency current reversals cause excessive heat generation in power electronics. Mechanical components such as bearings and gears experience increased wear due to micro‑vibrations. Therefore chattering reduction is crucial when implementing SMC on real hardware.

Chattering in sliding‑mode control also leads to low control accuracy and causes high wear of mechanical components and heat losses in power electronics \[3\].

### 4.4 Visualisation of Chattering

Figure 1 presents the control input of the classical SMC and illustrates the high‑frequency oscillations characteristic of chattering. Figure 2 shows the corresponding sliding variable oscillating around zero. These plots were generated from the simulation described in Section 3.

Control input of classical SMC showing high‑frequency oscillations

**Figure 1:** Control input \\u(t)\\ for the classical SMC. Rapid switching between positive and negative values indicates chattering.

Sliding variable of classical SMC oscillating around zero

**Figure 2:** Sliding variable \\\sigma(t)\\ for the classical SMC. The oscillations around zero correspond to the control chattering.

## 5 Chattering Mitigation Strategy I: Boundary Layer Method

The simplest way to reduce chattering is to replace the discontinuous sign function by the continuous saturation function defined in Section 4. Inside a boundary layer of width \\\epsilon\\, the control law becomes linear in \\\sigma\\; outside the boundary layer it behaves like the sign function. This method reduces high‑frequency oscillations but introduces a **steady‑state error** because the system converges only to the set \\{\sigma:\|\sigma\|\le\epsilon}\\. Tuning \\\epsilon\\ is therefore a trade‑off: a smaller boundary layer improves precision at the cost of increased chattering, whereas a larger layer smooths the control but reduces accuracy. In practice \\\epsilon\\ is chosen based on actuator bandwidth and allowable tracking error.

Smooth approximations of the sign function, such as Slotine’s boundary layer method or nonlinear saturation functions, reduce high‑frequency oscillations but introduce a steady‑state error proportional to the boundary‑layer width \[4, 5, 6\].

## 6 Chattering Mitigation Strategy II: Super‑Twisting Algorithm

### 6.1 Standard Formulation and Mapping to Code

The **super‑twisting algorithm (STA)** is a second‑order sliding mode technique that yields a continuous control input. The STA introduces an additional internal variable \\z\\ and defines the control law

    \begin{matrix}
    u & = u_{eq} - K_{1}\,\sqrt{|\sigma|}\, sgn(\sigma) + z - d\,\sigma, \\
    \dot{z} & = - K_{2}\, sgn(\sigma),
    \end{matrix}

where \\K_1\\ and \\K_2\\ are algorithmic gains and \\d\ge 0\\ is an optional damping gain. The discontinuous sign function only appears inside an integrator (\\\dot{z}\\), so the control input \\u\\ remains continuous. In the code (`src/controllers/sta_smc.py`) these variables correspond to `alg_gain_K1` (\\K_1\\), `alg_gain_K2` (\\K_2\\), `surf_gain_k1,k2` and `surf_lam1,lam2` (sliding‑surface gains) and `damping_gain` (\\d\\). The boundary layer parameter `boundary_layer` implements a saturated sign, ensuring finite‑time convergence in discrete‑time implementations.

Higher‑order sliding modes such as the super‑twisting algorithm preserve the robustness of classical SMC while providing nearly chatter‑free continuous control actions \[7\].

### 6.2 Visual Comparison with Classical SMC

Figure 3 compares the control input generated by the super‑twisting algorithm with the classical SMC. The STA produces a smooth control signal with no rapid sign changes, demonstrating the effectiveness of the second‑order sliding mode in eliminating chattering.

Comparison of control inputs: classical SMC (chattering) vs super‑twisting SMC (smooth)

**Figure 3:** Overlay of control inputs for classical SMC (orange) and super‑twisting SMC (blue). The STA removes high‑frequency oscillations and yields a continuous control signal.

## 7 Chattering Mitigation Strategy III: Adaptive Sliding Mode Control

### 7.1 Motivation and Control Law

A drawback of classical SMC is the need to choose a switching gain \\K\\ larger than the unknown disturbance bound. If \\K\\ is chosen too small the controller loses robustness; if it is chosen too large it aggravates chattering. Adaptive sliding‑mode control addresses this problem by **adjusting the gain online** based on the observed sliding variable. The adaptive controller in `src/controllers/adaptive_smc.py` computes the sliding variable as in the classical case and uses the control law

    u = u_{eq} - K\, sat(\sigma/\epsilon) - \alpha\,\sigma,

where \\\alpha\>0\\ adds linear damping. The gain \\K\\ evolves according to an adaptation law

    \dot{K} = \gamma\,|\sigma| - \text{leak}\,\left( K - K_{0} \right),

subject to \\K\_{\min}\le K \le K\_{\max}\\ and a rate limit. When \\\|\sigma\|\\ is large, \\K\\ increases to enhance robustness; when \\\|\sigma\|\\ is small (below a dead‑zone threshold), the leak term drives \\K\\ back toward its initial value \\K_0\\. This method eliminates the need for a priori knowledge of disturbance bounds.

### 7.2 Gain Adaptation Visualisation

Figure 4 illustrates how the adaptive gain \\K(t)\\ evolves during a simulation. The gain increases when the sliding variable is large and decays when the system is near the sliding surface. Figure 5 shows the corresponding sliding variable. These plots demonstrate that the adaptive law suppresses chattering by raising the switching gain only when necessary.

Adaptive gain K(t) increasing when \|σ\| is large and decreasing in the dead zone

**Figure 4:** Evolution of the adaptive gain \\K(t)\\ in the adaptive SMC controller.

Sliding variable σ(t) under adaptive SMC

**Figure 5:** Sliding variable \\\sigma(t)\\ under the adaptive SMC controller. Chattering is significantly reduced compared with the classical case.

## 8 Chattering Mitigation Strategy IV: Hybrid Adaptive–STA

The hybrid controller in `src/controllers/hybrid_adaptive_sta_smc.py` combines the continuous super‑twisting algorithm with state‑dependent gain adaptation. The sliding surface includes relative angles to decouple the second pendulum. Two gains \\k_1\\ and \\k_2\\ multiply the super‑twisting continuous and integral terms, respectively, and are adapted according to

    {\dot{k}}_{1} = \gamma_{1}\,|s| - \ell_{1}\,\left( k_{1} - k_{1,0} \right),\quad\quad{\dot{k}}_{2} = \gamma_{2}\,|s| - \ell_{2}\,\left( k_{2} - k_{2,0} \right),

where \\\ell_1,\ell_2\\ are leak rates and \\k\_{1,0},k\_{2,0}\\ initial gains. Adaptation is frozen when the sliding variable \\\|s\|\\ falls below a dead‑zone. An additional PD term recentres the cart. By combining adaptive gains with a second‑order sliding mode, the hybrid controller achieves rapid convergence without prior knowledge of disturbance bounds and maintains a continuous control input \[8\].

## 9 Synthesis and Comparative Analysis

### 9.1 Quantitative Results

Table 1 summarises the simulation results for the four controllers. The classical controller exhibits moderate tracking precision but requires a very large control effort and still shows a non‑zero chattering index. The super‑twisting controller removes chattering but performs poorly with the default gains, resulting in large errors. The adaptive SMC improves robustness by increasing its gain but still struggles to stabilise both pendulums. The hybrid adaptive–STA achieves the best precision and minimal control effort while keeping the chattering index at a manageable level.

| Controller | RMSE (θ₁,θ₂) | Combined RMSE | Control Effort | Chattering Index |
|----|----|----|----|----|
| **Classic SMC** | 1.24 rad, 1.24 rad | 1.76 | 1.55e5 J | 3.2e2 |
| **Super‑Twisting SMC** | 8.91 rad, 18.59 rad | 20.61 | 9.53e4 J | 4.38e4 |
| **Adaptive SMC** | 11.59 rad, 21.36 rad | 24.30 | 2.07e5 J | 1.63e3 |
| **Hybrid Adaptive–STA** | 0.0055 rad, 0.0063 rad | 0.0083 | 2.83 J | 3.42e3 |

**Table 1:** Quantitative performance metrics of the four controllers. *RMSE (θ₁,θ₂)* lists the root‑mean‑square errors of each pendulum angle from the upright position; *Combined RMSE* is the Euclidean norm of these errors; *Control Effort* is the integral of \\u(t)^2\\; the *Chattering Index* measures the total variation of the control signal.

### 9.2 Frequency Analysis

To visualise how the mitigation strategies shift control energy to lower frequencies, the power spectra of the control inputs were computed using the discrete Fourier transform. Figure 6 plots the magnitude of the Fourier transform of \\u(t)\\ for all controllers. The classical SMC shows significant high‑frequency content due to chattering. The super‑twisting and hybrid controllers concentrate energy at lower frequencies, demonstrating that replacing the discontinuous switching law by an integrated law effectively removes high‑frequency oscillations. The adaptive controller reduces the high‑frequency content compared with the classical case but still contains moderate energy at high frequencies.

Frequency spectra of control signals for all controllers

**Figure 6:** Discrete Fourier transform magnitudes of the control signals for the classical SMC, super‑twisting SMC, adaptive SMC and hybrid adaptive–STA controllers. Mitigation strategies shift control energy to lower frequencies, thereby reducing chattering.

### 9.3 Discussion

The results reveal that chattering originates from the discontinuous switching term in classical sliding‑mode control. Introducing a boundary layer smooths the control but inevitably leads to a steady‑state error. The super‑twisting algorithm removes chattering by integrating the discontinuous term and achieves finite‑time convergence; however, appropriate tuning of the algorithmic gains is necessary for good tracking performance. Adaptive SMC eliminates the need for a priori disturbance bounds by increasing the switching gain when the sliding variable is large and decreasing it near the sliding surface; this yields a continuous control signal and reduces chattering. The hybrid adaptive–STA combines the advantages of both adaptive gain adjustment and the super‑twisting algorithm. In the simulations it achieved the lowest tracking error and control effort while keeping the chattering index moderate. Thus, for applications requiring precise control and smooth actuation, the hybrid adaptive–STA controller is the preferred strategy.

## References

\[1\] W. Zhong and H. Röck, “Energy and passivity based control of the double inverted pendulum on a cart,” in *Proceedings of the 2001 IEEE International Conference on Control Applications*, Mexico City, Mexico, 2001, pp. 896–901.

\[2\] S. J. Gambhire, D. R. Kishore, P. S. Londhe and S. N. Pawar, “Review of sliding mode based control techniques for control system applications,” *International Journal of Dynamics and Control*, vol. 9, no. 1, pp. 363–378, 2021.

\[3\] V. I. Utkin and H. Lee, “Chattering problem in sliding mode control systems,” in *Proceedings of the International Workshop on Variable Structure Systems*, 2006, pp. 346–350.

\[4\] J. J. Slotine and S. S. Sastry, “Tracking control of non‑linear systems using sliding surfaces, with application to robot manipulators,” *International Journal of Control*, vol. 38, no. 2, pp. 465–492, 1983.

\[5\] N. B. Cheng, L. W. Guan, L. P. Wang and J. Han, “Chattering reduction of sliding mode control by adopting nonlinear saturation function,” *Advanced Materials Research*, vols. 143–144, pp. 53–61, 2010.

\[6\] P. V. Suryawanshi, P. D. Shendge and S. B. Phadke, “A boundary layer sliding mode control design for chatter reduction using uncertainty and disturbance estimator,” *International Journal of Dynamics and Control*, vol. 4, no. 4, pp. 456–465, 2016.

\[7\] S. U. Din, F. U. Rehman and Q. Khan, “Smooth super‑twisting sliding mode control for the class of underactuated systems,” *PLOS ONE*, vol. 13, no. 10, art. e0203667, 2018.

\[8\] S. Mobayen, “Adaptive global sliding mode control of underactuated systems using a super‑twisting scheme: an experimental study,” *Journal of Vibration and Control*, vol. 25, no. 12, pp. 2215–2224, 2019.

\[9\] Y. Huang and Z. Zhang, “Neural adaptive H∞ sliding‑mode control for uncertain nonlinear systems with disturbances using adaptive dynamic programming,” *Entropy*, vol. 25, no. 12, p. 1570, 2023.

------------------------------------------------------------------------
