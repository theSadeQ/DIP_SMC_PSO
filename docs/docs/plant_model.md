# 1.x Plant Model

## Operating Point(s)

* **OP1 (equilibrium about which we linearize):**
  Let the plant be the **double-inverted pendulum on a cart**. Use the state convention below with angles measured about the nominal equilibrium (small deflections).

  $$
  x^*=\begin{bmatrix}
  x_c^*&\dot x_c^*&\theta_1^*&\dot\theta_1^*&\theta_2^*&\dot\theta_2^*
  \end{bmatrix}^\top,\quad
  u^*=\begin{bmatrix}F^*\end{bmatrix}
  $$

  **Conditions (to be finalized):** cart at setpoint $x_c^*$ with near-zero velocity; small pendulum deviations about the chosen upright/near-upright reference $(\theta_1^*,\theta_2^*)\approx 0$; input bias $F^*$ chosen to satisfy static equilibrium. *(Numeric values TBD from identification data.)*&#x20;

## Model(s)

* **Transfer Function(s):** for any measured output $y$ (e.g., cart position $x_c$, link angles $\theta_1,\theta_2$), the SISO map from input $u=F$ is

  $$
  G_{y u}(s)\;=\;C\,(sI-A)^{-1}B\;+\;D
  $$

  Provide one $G_{y u}(s)$ per chosen output $y$. *(Coefficients derive from the linearized $A,B,C,D$ below.)*&#x20;

* **State-Space Representation (continuous-time, linearized about OP1):**

  * **State, input, output definitions**

    $$
    x=\begin{bmatrix}
    x_c & \dot x_c & \theta_1 & \dot\theta_1 & \theta_2 & \dot\theta_2
    \end{bmatrix}^\top,\quad
    u=\begin{bmatrix}F\end{bmatrix},\quad
    y = \text{selected subset/linear map of }x
    $$
  * **Dynamics**

    $$
      \dot{x} \;=\; A\,x + B\,u,\qquad y \;=\; C\,x + D\,u
    $$

    where $A=\left.\frac{\partial f}{\partial x}\right|_{(x^*,u^*)}$, $B=\left.\frac{\partial f}{\partial u}\right|_{(x^*,u^*)}$; $C,D$ reflect sensor/output selection. *(Symbolic $A,B$ follow from the standard cart–double-pendulum rigid-body model with parameters $m_0,m_1,m_2,l_1,l_2,I_1,I_2,b_c,b_1,b_2,g$; numeric instantiation TBD from identification.)*&#x20;

* **Linearization assumptions & regions of validity**

  * Small-angle/small-rate: $\sin\theta \approx \theta$, $\cos\theta \approx 1$; products of small terms neglected.
  * Operation confined to a neighborhood of OP1 (angles and velocities remain small); actuator and sensor dynamics beyond the modeled order are neglected; no transport delays or saturations in the linear model.
  * Continuous-time (Laplace $s$-domain) convention with frequencies in rad/s.
    *Validity degrades for large deflections, high rates, or strong nonlinear effects (e.g., impacts, saturation).*&#x20;

**Validation (completeness & accuracy):** Structure and assumptions match the documented intent; however, **numeric OP1 values, parameter set, and $A,B,C,D$ (hence $G(s)$) are not yet specified** and must be extracted/fit from the identification data before proceeding. Flagging these as **TBD** to avoid misuse.&#x20;

## Notes

* **Datasets for identification/validation (reference paths only; exact filenames TBD):**
  `/data/raw/step/*.csv`, `/data/raw/chirp/*.csv`, `/data/raw/free_decay/*.csv`, `/data/raw/multisine/*.csv` — to be used to (i) estimate parameters, (ii) fit $A,B,C,D$, and (iii) cross-validate $G_{yu}(s)$ against held-out trials. Link dataset references explicitly in the next revision of the report. &#x20;
