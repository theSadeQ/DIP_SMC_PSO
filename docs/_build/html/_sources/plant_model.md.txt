# 1.x Plant Model

## Operating Point(s)

* **OP1 (equilibrium about which we linearize):**
  Let the plant be the **double-inverted pendulum on a cart**. Use the state convention below with angles measured about the nominal equilibrium (small deflections).

  $$
  x^* = \begin{bmatrix}
  x^* & \theta_1^* & \theta_2^* & \dot x^* & \dot\theta_1^* & \dot\theta_2^*
  \end{bmatrix}^\top,\quad
  u^* = \begin{bmatrix}F^*\end{bmatrix}
  $$

  **Conditions:** the operating point corresponds to the upright equilibrium
  where the cart is at $x^*=0\,\text{m}$ with near‑zero velocity and both
  pendulums are upright ($\theta_1^*,\theta_2^*\approx 0$).  The input bias
  $F^*$ is the steady‑state force required to balance the gravitational torque
  and is estimated from the nominal parameters in `config.yaml`.

## Model(s)

* **Transfer Function(s):** for any measured output $y$ (e.g., cart position $x$, link angles $\theta_1,\theta_2$), the SISO map from input $u=F$ is

  $$
  G_{y u}(s)\;=\;C\,(sI-A)^{-1}B\;+\;D
  $$

  Provide one $G_{y u}(s)$ per chosen output $y$. *(Coefficients derive from the linearized $A,B,C,D$ below.)*&#x20;

* **State-Space Representation (continuous-time, linearized about OP1):**

  * **State, input, output definitions**

    $$
    x = \begin{bmatrix}
    x & \theta_1 & \theta_2 & \dot x & \dot\theta_1 & \dot\theta_2
    \end{bmatrix}^\top,\quad
    u = \begin{bmatrix}F\end{bmatrix},\quad
    y = \text{selected subset/linear map of }x
    $$
  * **Dynamics**

    $$
      \dot{x} \;=\; A\,x + B\,u,\qquad y \;=\; C\,x + D\,u
    $$

    where $A=\left.\frac{\partial f}{\partial x}\right|_{(x^*,u^*)}$, $B=\left.\frac{\partial f}{\partial u}\right|_{(x^*,u^*)}$; $C,D$ reflect sensor/output selection.  Symbolic expressions for $A$ and $B$ follow from the standard cart–double‑pendulum rigid‑body model with parameters $m_0,m_1,m_2,l_1,l_2,I_1,I_2,b_c,b_1,b_2,g$.  **Numeric values for $A,B,C,D$ are generated programmatically**: the simulation code (e.g. `src/core/dynamics_full.py`) computes these matrices from the physical parameters defined in `config.yaml`.  Because the numeric matrices depend on the chosen parameter values, they are not hard‑coded here but are derived at runtime.

    > **State ordering:** the internal implementation orders the six state variables as $[x,\theta_1,\theta_2,\dot{x},\dot{\theta}_1,\dot{\theta}_2]^\top$.  This differs from the $[x,\dot{x},\theta_1,\dot{\theta}_1,\theta_2,\dot{\theta}_2]$ ordering sometimes used in literature.  The chosen ordering matches the state unpacking in the controllers (see `AdaptiveSMC.compute_control()` and the super‑twisting controller in `sta_smc.py`), where the second and third entries are the pendulum angles and the remaining entries are velocities.  When computing Jacobians or linearising the dynamics one should therefore map the symbolic state vector to this ordering. [CIT-032]

* **Linearization assumptions & regions of validity**

  * Small-angle/small-rate: $\sin\theta \approx \theta$, $\cos\theta \approx 1$; products of small terms neglected.
  * Operation confined to a neighborhood of OP1 (angles and velocities remain small); actuator and sensor dynamics beyond the modeled order are neglected; no transport delays or saturations in the linear model.
  * Continuous-time (Laplace $s$-domain) convention with frequencies in rad/s.
    *Validity degrades for large deflections, high rates, or strong nonlinear effects (e.g., impacts, saturation).*&#x20;

**Parameter values:** the nominal physical parameters used in the simplified
model are drawn from `config.yaml`.  The list below now includes the
viscous friction coefficients, which were absent in earlier drafts:

* Cart mass \(m_0 = 1.5\,\text{kg}\) [CIT-033]
* First pendulum mass \(m_1 = 0.2\,\text{kg}\) [CIT-034]
* Second pendulum mass \(m_2 = 0.15\,\text{kg}\) [CIT-035]
* First pendulum length \(l_1 = 0.4\,\text{m}\) [CIT-036]
* Second pendulum length \(l_2 = 0.3\,\text{m}\) [CIT-037]
* Centre‑of‑mass distances \(l_{1,\mathrm{com}} = 0.2\,\text{m}\),
  \(l_{2,\mathrm{com}} = 0.15\,\text{m}\) [CIT-038]
* Pendulum inertias \(I_1 = 2.65\times10^{-3}\,\text{kg·m}^2\),
  \(I_2 = 1.15\times10^{-3}\,\text{kg·m}^2\) [CIT-039]
* Gravity \(g=9.81\,\text{m/s}^2\) [CIT-040]
* Viscous friction coefficients \(b_c=0.2\), \(b_1=0.005\) and \(b_2=0.004\) [CIT-041]

These parameters define the linearised matrices \(A,B,C,D\).  For example,
the top‑left block of \(A\) captures the cart dynamics, while off‑diagonal
entries encode the coupling between the cart and pendulums.  Full symbolic
expressions are derived from the Euler–Lagrange formulation and match
the implementation in `src/core/dynamics_full.py`.

**Validation:** structure and assumptions match the documented intent.  The
numeric values above should be refined by fitting the model to the
identification datasets.  Until identification is complete, care must be
taken to label uncertain values clearly (e.g. with ±10 % bounds) to avoid
misuse.

## Notes

* **Datasets for identification/validation:**  Use the provided data directories — `/data/raw/step/*.csv`, `/data/raw/chirp/*.csv`, `/data/raw/free_decay/*.csv` and `/data/raw/multisine/*.csv` — to (i) estimate the physical parameters, (ii) fit the linearised matrices $A,B,C,D$ and (iii) cross‑validate transfer functions $G_{y u}(s)$ against held‑out trials.  Each directory contains multiple CSV logs (e.g. `step_01.csv`, `step_02.csv`, etc.) recorded at 100 Hz.  The analysis scripts automatically load files matching these patterns and there is no longer any “TBD” regarding exact filenames.
