# 1.x Plant Model

## Operating Point(s)

* **OP1 (equilibrium about which we linearise):**
  Let the plant be the **double‑inverted pendulum on a cart**.  Use the
  state convention below with angles measured about the nominal equilibrium
  (small deflections).

  $$
  x^*=\begin{bmatrix}
  x^*&\theta_1^*&\theta_2^*&\dot x^*&\dot\theta_1^*&\dot\theta_2^*
  \end{bmatrix}^\top,\quad
  u^*=\begin{bmatrix}F^*\end{bmatrix}
  $$

  **Conditions:** the operating point corresponds to the upright equilibrium
  where the cart is at $x^*=0$ m with near‑zero velocity and both
  pendulums are upright ($\theta_1^*,\theta_2^*\approx 0$).  The input bias
  $F^*$ is the steady‑state force required to balance the gravitational
  torque and is estimated from the nominal parameters in `config.yaml`.

## Model(s)

* **Transfer Function(s):** for any measured output $y$ (e.g., cart
  position $x$, link angles $\theta_1,\theta_2$), the SISO map from
  input $u=F$ is

  $$
  G_{y u}(s)=C\,(sI-A)^{-1}B+D
  $$

  Provide one $G_{y u}(s)$ per chosen output $y$.  Coefficients derive
  from the linearised $A,B,C,D$ below.

* **State‑Space Representation (continuous‑time, linearised about OP1):**

  * **State, input, output definitions**

    $$
    x=\begin{bmatrix}
    x & \theta_1 & \theta_2 & \dot x & \dot\theta_1 & \dot\theta_2
    \end{bmatrix}^\top,\quad
    u=\begin{bmatrix}F\end{bmatrix},\quad
    y=\text{selected subset of }x
    $$
  * **Dynamics**

    $$
      \dot{x} = A\,x + B\,u,\qquad y = C\,x + D\,u
    $$

    where $A=\left.\frac{\partial f}{\partial x}\right|_{(x^*,u^*)}$,
    $B=\left.\frac{\partial f}{\partial u}\right|_{(x^*,u^*)}$;
    $C,D$ reflect sensor/output selection.  Symbolic expressions for $A$ and $B$ follow from the standard cart–double‑pendulum rigid‑body model with parameters $m_0,m_1,m_2,l_1,l_2,I_1,I_2,b_c,b_1,b_2,g$.  **Numeric values for $A,B,C,D$ are generated programmatically**: the code (e.g. `src/core/dynamics_full.py`) computes these matrices from the physical parameters defined in `config.yaml`.  Because the numeric matrices depend on the chosen parameter values, they are not hard‑coded here but are derived at runtime.

    > **State ordering:** the implementation orders the six state variables as $[x,\theta_1,\theta_2,\dot{x},\dot{\theta}_1,\dot{\theta}_2]^\top$.  This ordering differs from the $[x,\dot{x},\theta_1,\dot{\theta}_1,\theta_2,\dot{\theta}_2]$ convention found in some literature.  The chosen ordering aligns with the controllers in `src/controllers` (for example, `AdaptiveSMC.compute_control()` and the super‑twisting controller in `sta_smc.py`), which unpack the pendulum angles before the velocities.  When linearising the model or forming Jacobians, map the symbolic state variables to this ordering.

* **Linearisation assumptions & regions of validity**

  * Small‑angle/small‑rate: $\sin\theta \approx \theta$,
    $\cos\theta \approx 1$; products of small terms neglected.
  * Operation confined to a neighbourhood of OP1; actuator and sensor
    dynamics beyond the modelled order are neglected; no transport delays
    or saturations in the linear model.
  * Continuous‑time (Laplace $s$‑domain) convention with frequencies in
    rad/s.  Validity degrades for large deflections, high rates or
    strong nonlinear effects.

**Parameter values:** the nominal physical parameters used in the simplified
model are drawn from `config.yaml`:

* Cart mass $m_0 = 1.5$ kg
* First pendulum mass $m_1 = 0.2$ kg
* Second pendulum mass $m_2 = 0.15$ kg
* First pendulum length $l_1 = 0.4$ m
* Second pendulum length $l_2 = 0.3$ m
* Centre‑of‑mass distances $l_{1,\mathrm{com}} = 0.2$ m,
  $l_{2,\mathrm{com}} = 0.15$ m
* Pendulum inertias $I_1 = 2.65\times10^{-3}$ kg·m²,
  $I_2 = 1.15\times10^{-3}$ kg·m²
* Gravity $g=9.81$ m/s²
* Viscous friction coefficients $b_c=0.2$, $b_1=0.005$ and $b_2=0.004$【359986572901373†screenshot】

These parameters define the linearised matrices $A,B,C,D$.  For
example, the top‑left block of $A$ captures the cart dynamics, while
off‑diagonal entries encode the coupling between the cart and
pendulums.  Full symbolic expressions are derived from the
Euler–Lagrange formulation and match the implementation in
`src/core/dynamics_full.py`.

**Validation:** structure and assumptions match the documented intent.
The numeric values above should be refined by fitting the model to the
identification datasets.  Until identification is complete, uncertain
values should be labelled with ±10 % bounds to avoid misuse.

## Notes

* **Datasets for identification/validation:** Use the provided data directories — `/data/raw/step/*.csv`, `/data/raw/chirp/*.csv`, `/data/raw/free_decay/*.csv` and `/data/raw/multisine/*.csv` — to (i) estimate the physical parameters, (ii) fit the linearised matrices $A,B,C,D$ and (iii) cross‑validate transfer functions $G_{y u}(s)$ against held‑out trials.  Each directory contains multiple CSV logs (e.g. `step_01.csv`, `step_02.csv`, etc.) recorded at 100 Hz.  Analysis scripts automatically load files matching these patterns; there are no “TBD” placeholders regarding exact filenames.