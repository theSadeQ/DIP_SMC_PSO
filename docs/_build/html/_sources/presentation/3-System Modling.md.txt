# **A Comprehensive Technical Report on the Modeling and Configuration of a Cart‑Based Double Inverted Pendulum System**

### **Introduction**

#### **Purpose and Scope**

This report provides a theoretical and practical foundation for modelling and controlling a cart‑based double inverted pendulum (DIP) system{cite}`dip_khalil_2002_nonlinear_systems`.  The goal is to deliver a self‑contained guide for control systems engineers working with Python‑based simulations{cite}`dip_khalil_2002_nonlinear_systems`.  The document derives the nonlinear equations of motion from first principles, enumerates all required physical, simulation and controller parameters, and proposes a formal configuration schema.  Where appropriate, the report cross‑references the accompanying project files (particularly the high‑fidelity implementation in `src/core/dynamics.py` and the configuration file `config.yaml`) to ensure applicability to real simulation code `DIP_SMC_PSO/src/core/dynamics.py` `DIP_SMC_PSO/config.yaml`.

#### **The Double Inverted Pendulum as a Benchmark Problem**

A double inverted pendulum consists of two pendulums attached in series to a cart.  The second pendulum is attached to the end of the first, so the system has three degrees of freedom: the cart position and the two pendulum angles.  Only one actuator applies a horizontal force to the cart, making the system underactuated; there is one control input for three state variables.  Control of such a system is challenging because it is inherently unstable and will fall over unless stabilised {cite}`dip_khalil_2002_nonlinear_systems`.  Classical control literature emphasises that the DIPC’s single actuator must regulate three degrees of freedom, making the system underactuated{cite}`dip_khalil_2002_nonlinear_systems`.

The double inverted pendulum also exhibits chaotic dynamics.  The motion is governed by coupled ordinary differential equations that display strong sensitivity to initial conditions{cite}`dip_khalil_2002_nonlinear_systems`.  Small changes in starting state can lead to vastly different trajectories, so an accurate nonlinear model is essential for control design.  These properties make the DIP a popular benchmark for advanced control strategies, including sliding‑mode control, optimal control and reinforcement learning.

#### **Methodology**

The dynamic model is derived using Lagrangian mechanics, an energy‑based formulation widely used for open‑chain robots and underactuated systems {cite}`smc_utkin_2013_sliding_mode_control`.  In this approach the kinetic and potential energies of each component are computed and combined to form the Lagrangian L=T−VL = T - V.  The Euler–Lagrange equations are then applied to obtain the equations of motion (EOM).  For the double inverted pendulum, the Lagrangian is the difference between the sum of kinetic energies and the sum of gravitational potentials {cite}`dip_khalil_2002_nonlinear_systems`.  The resulting nonlinear second‑order differential equations are transformed into a state‑space form suitable for control design.  The derived model is validated by comparing with the high‑fidelity implementation in the accompanying Python project (`DoubleInvertedPendulum` class), ensuring that parameter names and units match those in `config.yaml`.

------

## **Section 1: System Dynamics and Mathematical Modeling**

### **1.1 System Definition, Assumptions, and Nomenclature**

#### **System Diagram**

The double inverted pendulum on a cart comprises a cart of mass mcm_{c} that translates horizontally on a track.  Two rigid pendulum links are attached in series; the first link (mass m1m_{1}, length l1l_{1}) is pinned to the cart and the second link (mass m2m_{2}, length l2l_{2}) is attached to the end of the first.  The centres of mass of the links are located at distances lc1l_{c1} and lc2l_{c2} from their respective pivots.  Angles θ1\theta_{1} and θ2\theta_{2} are measured from the upward vertical, and the horizontal displacement of the cart is xx.  Gravity acts downward with acceleration gg.  A horizontal force uu applied to the cart constitutes the single control input.  A schematic of the system is shown in Figure 1{cite}`dip_khalil_2002_nonlinear_systems`.

![Double‑Inverted Pendulum on a Cart](https://chatgpt.com/c/media/rId25.png)

#### **Model Assumptions**

1. **Rigid links.** Each pendulum link is treated as a rigid body with constant mass and moment of inertia.  There is no flexural deformation{cite}`dip_khalil_2002_nonlinear_systems`.
2. **Planar motion.** The cart moves along a one‑dimensional horizontal track, and the pendulums swing in the vertical plane.  Lateral motions are neglected{cite}`dip_khalil_2002_nonlinear_systems`.
3. **Angles measured from the upward vertical.** The angles θ1\theta_{1} and θ2\theta_{2} are measured from the upright vertical; positive rotations correspond to counter‑clockwise motion{cite}`dip_khalil_2002_nonlinear_systems`.
4. **Viscous friction.** Friction at the cart and joints is modelled as linear viscous friction with coefficients bx,bθ1,bθ2b_{x},b_{\theta_{1}},b_{\theta_{2}}.  Coulomb friction and stiction are neglected{cite}`dip_khalil_2002_nonlinear_systems`.
5. **Instantaneous motor dynamics.** The actuator that applies the force uu to the cart is assumed to have negligible dynamics; the force is applied directly to the cart mass{cite}`dip_khalil_2002_nonlinear_systems`.
6. **Unactuated pendulum joints.** Only the cart is actuated.  The pendulum joints do not receive external torques; therefore the generalized forces associated with θ1\theta_{1} and θ2\theta_{2} consist solely of viscous damping{cite}`dip_khalil_2002_nonlinear_systems`.

#### **Nomenclature**

Table 1.1 summarises the symbols used in the mathematical model and their correspondence with the project’s configuration file.  All physical parameters are defined in the `physics` section of `config.yaml` `DIP_SMC_PSO/config.yaml`.

| Symbol                     | Parameter Name (`config.yaml`) | Description                                                  | SI Units    |
| -------------------------- | ------------------------------ | ------------------------------------------------------------ | ----------- |
| mcm_{c}                    | `cart_mass`                    | Mass of the cart                                             | kg          |
| m1m_{1}                    | `pendulum1_mass`               | Mass of the first pendulum link                              | kg          |
| m2m_{2}                    | `pendulum2_mass`               | Mass of the second pendulum link                             | kg          |
| l1l_{1}                    | `pendulum1_length`             | Full length of the first pendulum                            | m           |
| l2l_{2}                    | `pendulum2_length`             | Full length of the second pendulum                           | m           |
| lc1l_{c1}                  | `pendulum1_com`                | Distance from the first joint to the centre of mass of link 1 | m           |
| lc2l_{c2}                  | `pendulum2_com`                | Distance from the second joint to the centre of mass of link 2 | m           |
| I1I_{1}                    | `pendulum1_inertia`            | Moment of inertia of link 1 about its centre of mass         | kg·m²       |
| I2I_{2}                    | `pendulum2_inertia`            | Moment of inertia of link 2 about its centre of mass         | kg·m²       |
| gg                         | `gravity`                      | Gravitational acceleration                                   | m·s⁻²       |
| bxb_{x}                    | `cart_friction`                | Viscous friction coefficient of the cart                     | N·s·m⁻¹     |
| bθ1b_{\theta_{1}}          | `joint1_friction`              | Viscous friction coefficient of the first joint              | N·m·s·rad⁻¹ |
| bθ2b_{\theta_{2}}          | `joint2_friction`              | Viscous friction coefficient of the second joint             | N·m·s·rad⁻¹ |
| κ_mthr\kappa\_ \text{mthr} | `singularity_cond_threshold`   | Condition‑number threshold for inertia matrix regularisation | —           |

### **1.2 Lagrangian Formulation and Derivation**

Lagrangian mechanics provides a systematic way of deriving the equations of motion for systems with generalized coordinates.  The Lagrangian LL is defined as the difference between the total kinetic energy TT and the total potential energy VV: L=T−VL = T - V.  For the double inverted pendulum on a cart, the generalized coordinates are q=[x,θ1,θ2]⊤q = \left[ x,\theta_{1},\theta_{2} \right]^{\top} and their time derivatives q˙=[x˙,θ˙1,θ˙2]⊤\dot{q} = \left[ \dot{x},{\dot{\theta}}_{1},{\dot{\theta}}_{2} \right]^{\top}.

#### **Kinetic Energy (T)**

The kinetic energy of the system consists of translational and rotational energies of the cart and both pendulum links{cite}`dip_khalil_2002_nonlinear_systems`.  To derive these terms, first express the positions of the centres of mass relative to an inertial frame.  Taking the cart’s origin as the zero height and measuring angles from the upward vertical (see Figure 1), the coordinates of the centres of mass are{cite}`dip_khalil_2002_nonlinear_systems`

x1=x+lc1sin⁡θ1,y1=lc1cos⁡θ1,x2=x+l1sin⁡θ1+lc2sin⁡θ2,y2=l1cos⁡θ1+lc2cos⁡θ2.\begin{aligned} x_1 &= x + l_{c1} \sin \theta_1, &\quad y_1 &= l_{c1} \cos \theta_1,\\ x_2 &= x + l_{1} \sin \theta_1 + l_{c2} \sin \theta_2, &\quad y_2 &= l_{1} \cos \theta_1 + l_{c2} \cos \theta_2. \end{aligned}

Differentiating these expressions gives the velocities of the centres of mass{cite}`dip_khalil_2002_nonlinear_systems`:

x˙_1=x˙+lc1θ˙_1cos⁡θ1,y˙_1=− lc1θ˙_1sin⁡θ1,x˙_2=x˙+l1θ˙_1cos⁡θ1+lc2θ˙_2cos⁡θ2,y˙_2=− l1θ˙_1sin⁡θ1−lc2θ˙_2sin⁡θ2.\begin{aligned} \dot{x}\_1 &= \dot{x} + l_{c1}\dot{\theta}\_1 \cos \theta_1, &\quad \dot{y}\_1 &= -\,l_{c1}\dot{\theta}\_1 \sin \theta_1,\\ \dot{x}\_2 &= \dot{x} + l_{1}\dot{\theta}\_1 \cos \theta_1 + l_{c2} \dot{\theta}\_2 \cos \theta_2, &\quad \dot{y}\_2 &= -\,l_{1}\dot{\theta}\_1 \sin \theta_1 - l_{c2} \dot{\theta}\_2 \sin \theta_2. \end{aligned}

The cart has no rotational energy, so its kinetic energy is purely translational: Tc=12mcx˙2T_{c} = \frac12 m_{c}\dot{x}^{2}{cite}`dip_khalil_2002_nonlinear_systems`.  For the pendulum links, each centre of mass has translational kinetic energy and each link has rotational kinetic energy about its centre of mass.  Denoting I1I_{1} and I2I_{2} as the moments of inertia of the links about their centres of mass, the energies are{cite}`dip_khalil_2002_nonlinear_systems`

T_1=12m_1(x˙_12+y˙_12)+12I_1θ˙_12,T_2=12m_2(x˙_22+y˙_22)+12I_2θ˙_22.\begin{aligned} T\_{1} &= \frac{1}{2} m\_{1}\Bigl( \dot{x}\_1^2 + \dot{y}\_1^2 \Bigr) + \frac{1}{2} I\_{1}\dot{\theta}\_1^2,\\ T\_{2} &= \frac{1}{2} m\_{2}\Bigl( \dot{x}\_2^2 + \dot{y}\_2^2 \Bigr) + \frac{1}{2} I\_{2}\dot{\theta}\_2^2. \end{aligned}

Substituting the velocity expressions and simplifying yields{cite}`dip_khalil_2002_nonlinear_systems`

T_1=12m_1(x˙+lc1θ˙_1cos⁡θ1)2+12m_1(lc1θ˙_1sin⁡θ1)2+12I_1θ˙_12,T_2=12m_2(x˙+l1θ˙_1cos⁡θ1+lc2θ˙_2cos⁡θ2)2+12m_2(l1θ˙_1sin⁡θ1+lc2θ˙_2sin⁡θ2)2+12I_2θ˙_22.\begin{aligned} T\_{1} &= \frac{1}{2} m\_{1} \bigl( \dot{x} + l_{c1}\dot{\theta}\_1 \cos \theta_1 \bigr)^2 + \frac{1}{2} m\_{1} \bigl( l_{c1}\dot{\theta}\_1 \sin \theta_1 \bigr)^2 + \frac{1}{2} I\_{1}\dot{\theta}\_1^2,\\ T\_{2} &= \frac{1}{2} m\_{2} \bigl( \dot{x} + l_{1}\dot{\theta}\_1 \cos \theta_1 + l_{c2}\dot{\theta}\_2 \cos \theta_2 \bigr)^2 + \frac{1}{2} m\_{2} \bigl( l_{1}\dot{\theta}\_1 \sin \theta_1 + l_{c2}\dot{\theta}\_2 \sin \theta_2 \bigr)^2 + \frac{1}{2} I\_{2}\dot{\theta}\_2^2. \end{aligned}

The total kinetic energy is the sum T=Tc+T1+T2T = T_{c} + T_{1} + T_{2}{cite}`dip_khalil_2002_nonlinear_systems`.

#### **Potential Energy (V)**

Choosing the cart’s height as the zero potential energy reference, the gravitational potential energy of each pendulum depends on its vertical position{cite}`dip_khalil_2002_nonlinear_systems`:

V_1=m_1g l_c1cos⁡θ_1,V_2=m_2g(l_1cos⁡θ_1+l_c2cos⁡θ_2){cite}`dip_khalil_2002_nonlinear_systems`.V\_{1} = m\_{1} g\,l\_{c1} \cos \theta\_{1},\qquad V\_{2} = m\_{2} g \bigl( l\_{1} \cos \theta\_{1} + l\_{c2} \cos \theta\_{2} \bigr){cite}`dip_khalil_2002_nonlinear_systems`.

The total potential energy is

V=V_1+V_2=m_1g l_c1cos⁡θ_1+m_2g(l_1cos⁡θ_1+l_c2cos⁡θ_2){cite}`dip_khalil_2002_nonlinear_systems`.V = V\_{1} + V\_{2} = m\_{1} g\,l\_{c1} \cos \theta\_{1} + m\_{2} g \bigl( l\_{1} \cos \theta\_{1} + l\_{c2} \cos \theta\_{2} \bigr){cite}`dip_khalil_2002_nonlinear_systems`.

#### **The Lagrangian (L)**

The Lagrangian is defined as the difference between kinetic and potential energies{cite}`dip_khalil_2002_nonlinear_systems`:

L(q,q˙)=T−V.L\left( q,\dot{q} \right) = T - V.

### **1.3 Derivation of the Equations of Motion (EOM)**

To derive the equations of motion we apply the Euler–Lagrange equations{cite}`dip_khalil_2002_nonlinear_systems`

ddt(∂L∂q˙_i)−∂L∂q_i=Q_i,\frac{d}{dt}\Bigl( \frac{\partial L}{\partial \dot{q}\_{i}} \Bigr) - \frac{\partial L}{\partial q\_{i}} = Q\_{i},

where qi∈{x,θ1,θ2}q_{i} \in \{ x,\theta_{1},\theta_{2}\} and QiQ_{i} are the generalized forces.  The cart experiences an external force uu and viscous friction −bxx˙- b_{x}\dot{x}, so Qx=u−bxx˙Q_{x} = u - b_{x}\dot{x}.  The pendulum joints are unactuated, so their generalized forces consist solely of viscous damping: Qθ1=−bθ1θ˙1Q_{\theta_{1}} = - b_{\theta_{1}}{\dot{\theta}}_{1} and Qθ2=−bθ2θ˙2Q_{\theta_{2}} = - b_{\theta_{2}}{\dot{\theta}}_{2}{cite}`smc_utkin_2013_sliding_mode_control`.

#### **Equation for the Cart Coordinate (x)**

The derivative of the Lagrangian with respect to x˙\dot{x} collects the contributions of the translational velocities of all three bodies:

∂L∂x˙=m_cx˙+m_1(x˙+lc1θ˙_1cos⁡θ_1)+m_2(x˙+l1θ˙_1cos⁡θ_1+lc2θ˙_2cos⁡θ_2).\frac{\partial L}{\partial \dot{x}} = m\_{c} \dot{x} + m\_{1} \bigl( \dot{x} + l_{c1}\dot{\theta}\_{1} \cos \theta\_{1} \bigr) + m\_{2} \bigl( \dot{x} + l_{1}\dot{\theta}\_{1} \cos \theta\_{1} + l_{c2}\dot{\theta}\_{2} \cos \theta\_{2} \bigr).

Taking the time derivative and noting that ∂L/∂x=0\partial L/\partial x = 0 (the Lagrangian does not depend explicitly on xx), the Euler–Lagrange equation for xx becomes

(mc+m1+m2)x¨+(m1lc1+m2l1)θ¨1cos⁡θ1+m2lc2θ¨2cos⁡θ2−(m1lc1+m2l1)θ˙12sin⁡θ1−m2lc2θ˙22sin⁡θ2=u−bxx˙.\begin{aligned} &\bigl( m_{c} + m_{1} + m_{2} \bigr)\ddot{x} + \bigl( m_{1}l_{c1} + m_{2}l_{1} \bigr){\ddot{\theta}}_{1}\cos \theta_{1} + m_{2}l_{c2}{\ddot{\theta}}_{2}\cos \theta_{2}\\ &\quad - \bigl( m_{1}l_{c1} + m_{2}l_{1} \bigr){\dot{\theta}}_{1}^{2}\sin \theta_{1} - m_{2}l_{c2}{\dot{\theta}}_{2}^{2}\sin \theta_{2} = u - b_{x}\dot{x}. \end{aligned}

The first three terms group the accelerations of the cart and the pendulum angles weighted by their mass distributions, whereas the sine terms originate from differentiating cos⁡θ\cos \theta.  The viscous friction bxx˙b_{x}\dot{x} opposes motion and appears on the right‑hand side along with the input force uu{cite}`dip_khalil_2002_nonlinear_systems` `DIP_SMC_PSO/src/core/dynamics.py` `DIP_SMC_PSO/src/core/dynamics_full.py`.

#### **Equation for the First Pendulum Angle (θ1\theta_{1})**

Applying the Euler–Lagrange equation to θ1\theta_{1} involves differentiating LL with respect to θ˙1{\dot{\theta}}_{1} and θ1\theta_{1}.  After grouping terms and making use of trigonometric identities (see, for example, the derivation for the simple double pendulum {cite}`dip_khalil_2002_nonlinear_systems`), one obtains

(m_1l_c1+m_2l_1)x¨cos⁡θ_1+(I_1+m_1l_c12+m_2l_12)θ¨_1+m_2l_1l_c2cos⁡(θ_1−θ_2) θ¨_2−m_2l_1l_c2sin⁡(θ_1−θ_2) θ˙22+(m_1l_c1+m_2l_1)g sin⁡θ_1=−bθ_1θ˙_1.\begin{aligned} &(m\_{1}l\_{c1} + m\_{2}l\_{1})\ddot{x}\cos \theta\_{1} + \bigl( I\_{1} + m\_{1}l\_{c1}^{2} + m\_{2}l\_{1}^{2} \bigr)\ddot{\theta}\_{1} + m\_{2}l\_{1}l\_{c2}\cos\bigl( \theta\_{1}- \theta\_{2} \bigr)\,\ddot{\theta}\_{2}\\ &\quad - m\_{2}l\_{1}l\_{c2}\sin\bigl( \theta\_{1}- \theta\_{2} \bigr)\,{\dot{\theta}}_{2}^{2} + \bigl( m\_{1}l\_{c1} + m\_{2}l\_{1} \bigr)g\,\sin \theta\_{1} = - b_{\theta\_{1}}\dot{\theta}\_{1}. \end{aligned}

The term proportional to θ˙22sin⁡(θ1−θ2){\dot{\theta}}_{2}^{2}\sin\left( \theta_{1} - \theta_{2} \right) arises from Coriolis and centrifugal effects and couples the dynamics of θ1\theta_{1} and θ2\theta_{2}.  The gravitational torque terms are proportional to sin⁡θ1\sin \theta_{1} and vanish when the pendulum is upright{cite}`dip_khalil_2002_nonlinear_systems` `DIP_SMC_PSO/src/core/dynamics.py` `DIP_SMC_PSO/src/core/dynamics_full.py`.

#### **Equation for the Second Pendulum Angle (θ2\theta_{2})**

Repeating the procedure for θ2\theta_{2} yields

m_2l_c2x¨cos⁡θ_2+m_2l_1l_c2cos⁡(θ_1−θ_2) θ¨_1+(I_2+m_2l_c22)θ¨_2+m_2l_1l_c2sin⁡(θ_1−θ_2) θ˙12+m_2l_c2g sin⁡θ_2=−bθ_2θ˙_2.\begin{aligned} &m\_{2}l\_{c2}\ddot{x}\cos \theta\_{2} + m\_{2}l\_{1}l\_{c2}\cos\bigl( \theta\_{1}- \theta\_{2} \bigr)\,\ddot{\theta}\_{1} + \bigl( I\_{2} + m\_{2}l\_{c2}^{2} \bigr)\ddot{\theta}\_{2}\\ &\quad + m\_{2}l\_{1}l\_{c2}\sin\bigl( \theta\_{1}- \theta\_{2} \bigr)\,{\dot{\theta}}_{1}^{2} + m\_{2}l\_{c2} g\,\sin \theta\_{2} = - b_{\theta\_{2}}\dot{\theta}\_{2}. \end{aligned}

The two coupled pendulum equations highlight the nonlinear interactions between θ1\theta_{1} and θ2\theta_{2}.  The terms containing cos⁡(θ1−θ2)\cos\left( \theta_{1} - \theta_{2} \right) multiply the angular accelerations and represent inertial coupling, whereas those containing sin⁡(θ1−θ2)\sin\left( \theta_{1} - \theta_{2} \right) multiply squared angular velocities and correspond to Coriolis/centrifugal effects{cite}`dip_khalil_2002_nonlinear_systems` `DIP_SMC_PSO/src/core/dynamics.py` `DIP_SMC_PSO/src/core/dynamics_full.py`.

### **1.4 State‑Space Representation in Matrix Form**

The derived equations can be rearranged into the standard manipulator form{cite}`dip_khalil_2002_nonlinear_systems`

M(q) q¨+C(q,q˙) q˙+G(q)=B u,M(q)\,\ddot{q} + C\bigl( q,\dot{q} \bigr)\,\dot{q} + G(q) = B\, u,

where q=[x,θ1,θ2]⊤q = \left[ x,\theta_{1},\theta_{2} \right]^{\top}, q˙=[x˙,θ˙1,θ˙2]⊤\dot{q} = \left[ \dot{x},{\dot{\theta}}_{1},{\dot{\theta}}_{2} \right]^{\top}, q¨\ddot{q} contains the accelerations, and BB maps the scalar input force to the generalized coordinates.  The matrices M(q)M(q), C(q,q˙)C\bigl( q,\dot{q} \bigr) and G(q)G(q) are derived directly from the equations of motion{cite}`dip_khalil_2002_nonlinear_systems` `DIP_SMC_PSO/src/core/dynamics.py` `DIP_SMC_PSO/src/core/dynamics_full.py`.

#### **Inertia Matrix** M(q)M(q)

M(q)=[m_c+m_1+m_2(m_1l_c1+m_2l_1)cos⁡θ_1m_2l_c2cos⁡θ_2(m_1l_c1+m_2l_1)cos⁡θ_1I_1+m_1l_c12+m_2l_12m_2l_1l_c2cos⁡(θ_1−θ_2)m_2l_c2cos⁡θ_2m_2l_1l_c2cos⁡(θ_1−θ_2)I_2+m_2l_c22].M(q) = \begin{bmatrix} m\_{c} + m\_{1} + m\_{2} & \bigl(m\_{1}l\_{c1} + m\_{2}l\_{1}\bigr)\cos \theta\_{1} & m\_{2}l\_{c2}\cos \theta\_{2} \\ \bigl(m\_{1}l\_{c1} + m\_{2}l\_{1}\bigr)\cos \theta\_{1} & I\_{1} + m\_{1}l\_{c1}^{2} + m\_{2}l\_{1}^{2} & m\_{2}l\_{1}l\_{c2}\cos\bigl( \theta\_{1} - \theta\_{2} \bigr) \\ m\_{2}l\_{c2}\cos \theta\_{2} & m\_{2}l\_{1}l\_{c2}\cos\bigl( \theta\_{1} - \theta\_{2} \bigr) & I\_{2} + m\_{2}l\_{c2}^{2} \end{bmatrix}.

This symmetric, positive‑definite matrix reflects the mass distribution of the system and the coupling between coordinates{cite}`dip_khalil_2002_nonlinear_systems` `DIP_SMC_PSO/src/core/dynamics.py` `DIP_SMC_PSO/src/core/dynamics_full.py`.

#### **Coriolis, Centrifugal and Damping Matrix** C(q,q˙)C\bigl( q,\dot{q} \bigr)

The matrix C(q,q˙)C\bigl( q,\dot{q} \bigr) multiplies the velocity vector q˙\dot{q} and aggregates viscous damping and Coriolis/centrifugal terms.  Matching the structure implemented in `compute_matrices_numba` within `src/core/dynamics.py`, it is{cite}`dip_khalil_2002_nonlinear_systems` `DIP_SMC_PSO/src/core/dynamics.py` `DIP_SMC_PSO/src/core/dynamics_full.py`

C(q,q˙)=[b_x000b_θ_1− m_2 l_1 l_c2 sin⁡(θ_1−θ_2) θ˙_20m_2 l_1 l_c2 sin⁡(θ_1−θ_2) θ˙_1b_θ_2].C(q, \dot{q}) = \begin{bmatrix} b\_{x} & 0 & 0 \\ 0 & b\_{\theta\_{1}} & -\,m\_{2}\,l\_{1}\,l\_{c2}\,\sin\bigl( \theta\_{1} - \theta\_{2} \bigr)\,\dot{\theta}\_{2} \\ 0 & m\_{2}\,l\_{1}\,l\_{c2}\,\sin\bigl( \theta\_{1} - \theta\_{2} \bigr)\,\dot{\theta}\_{1} & b\_{\theta\_{2}} \end{bmatrix}.

The diagonal entries represent viscous friction at the cart and joints, whereas the off‑diagonal terms couple the pendulum velocities.  Notice that CC is not symmetric; the skew‑symmetric part generates the Coriolis and centrifugal forces while the symmetric part corresponds to damping{cite}`dip_khalil_2002_nonlinear_systems` `DIP_SMC_PSO/src/core/dynamics.py` `DIP_SMC_PSO/src/core/dynamics_full.py`.

#### **Gravity Vector** G(q)G(q)

G(q)=[0(m_1l_c1+m_2l_1)g sin⁡θ_1m_2l_c2g sin⁡θ_2].G(q) = \begin{bmatrix} 0 \\ \bigl(m\_{1}l\_{c1} + m\_{2}l\_{1}\bigr) g\,\sin \theta\_{1} \\ m\_{2}l\_{c2} g\,\sin \theta\_{2} \end{bmatrix}.

The input matrix is B=[1,0,0]⊤B = [ 1,0,0]^{\top} because only the cart coordinate is actuated{cite}`dip_khalil_2002_nonlinear_systems` `DIP_SMC_PSO/src/core/dynamics.py` `DIP_SMC_PSO/src/core/dynamics_full.py`.

#### **Code Implementation and Verification**

The theoretical matrices MM, CC and GG derived above are implemented in the Python project through JIT‑compiled functions `DIP_SMC_PSO/src/core/dynamics.py` `DIP_SMC_PSO/src/core/dynamics_full.py`.  Table 1.2 maps key terms in the matrices to their implementations in `src/core/dynamics.py` and `src/core/dynamics_full.py` to verify correctness.

| Derived term            | Mathematical expression                                      | Corresponding code snippet                                   |
| ----------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| Inertia M11M_{11}       | mc+m1+m2m_{c} + m_{1} + m_{2}                                | `h11 = m_c + m1 + m2` in `compute_matrices_numba` (simplified) and `compute_inertia_numba` (full) |
| Inertia M12M_{12}       | (m1lc1+m2l1)cos⁡θ1\bigl( m_{1}l_{c1} + m_{2}l_{1} \bigr)\cos \theta_{1} | `h12 = (m1 * lc1 + m2 * l1) * c1` in the simplified model and full model |
| Coriolis term C12C_{12} | − m2l1lc2sin⁡(θ1−θ2) θ˙2-\, m_{2}l_{1}l_{c2}\sin\bigl( \theta_{1} - \theta_{2} \bigr)\,{\dot{\theta}}_{2} | `C[1,2] = -c_coeff * s12 * q2dot` where `c_coeff = m2 * l1 * lc2` |
| Coriolis term C23C_{23} | + m2l1lc2sin⁡(θ1−θ2) θ˙1+\, m_{2}l_{1}l_{c2}\sin\bigl( \theta_{1} - \theta_{2} \bigr)\,{\dot{\theta}}_{1} | `C[2,1] = +c_coeff * s12 * q1dot`                            |
| Gravity term G2G_{2}    | (m1lc1+m2l1)g sin⁡θ1\bigl( m_{1}l_{c1} + m_{2}l_{1} \bigr)g\,\sin \theta_{1} | `g2 = (m1 * lc1 + m2 * l1) * gravity * s1` and stored in `G{cite}`dip_khalil_2002_nonlinear_systems`` |
| Gravity term G3G_{3}    | m2lc2g sin⁡θ2m_{2}l_{c2}g\,\sin \theta_{2}                    | `g3 = (m2 * lc2) * gravity * s2` and stored in `G{cite}`dip_khalil_2002_nonlinear_systems``        |

Both `dynamics.py` (simplified) and `dynamics_full.py` implement the same inertia matrix M(q)M(q) `DIP_SMC_PSO/src/core/dynamics.py` `DIP_SMC_PSO/src/core/dynamics_full.py`{cite}`dip_khalil_2002_nonlinear_systems`.  The simplified model represents damping and Coriolis/centrifugal effects via a 3×33 \times 3 matrix C(q,q˙)C\bigl( q,\dot{q} \bigr) multiplied by the velocity vector.  The full model (`dynamics_full.py`) uses a 3×13 \times 1 vector `c` returned by `compute_centrifugal_coriolis_vector_numba`, which contains both damping and nonlinear velocity products.  The sign conventions in the full model were tuned so that subtracting this vector in the equation Mq¨=B u−c−GM\ddot{q} = B\,u - c - G reproduces the same dynamics as the simplified model.  Additionally, the full model includes a mechanism to compute the condition number of MM and return NaNs when the matrix is ill‑conditioned, a safeguard absent from the simplified version `DIP_SMC_PSO/config.yaml`{cite}`smc_levant_2003_higher_order_smc`.

#### **First‑Order State‑Space Representation**

For control design and simulation it is convenient to rewrite the manipulator equation as a first‑order system{cite}`dip_khalil_2002_nonlinear_systems`.  Define the six‑dimensional state vector

x_s=[xθ_1θ_2x˙θ˙_1θ˙_2]⊤{cite}`dip_khalil_2002_nonlinear_systems`.\boldsymbol{x}\_{s} = \begin{bmatrix} x & \theta\_{1} & \theta\_{2} & \dot{x} & \dot{\theta}\_{1} & \dot{\theta}\_{2} \end{bmatrix}^{\top}{cite}`dip_khalil_2002_nonlinear_systems`.

The time derivative of this vector follows from the manipulator form{cite}`dip_khalil_2002_nonlinear_systems`.  Solving M(q) q¨=B u−C(q,q˙) q˙−G(q)M(q)\,\ddot{q} = B\,u - C\bigl( q,\dot{q} \bigr)\,\dot{q} - G(q) for q¨\ddot{q} gives

q¨=M(q)−1(B u−C(q,q˙) q˙−G(q)).\ddot{q} = M(q)^{-1}\Bigl( B\,u - C(q, \dot{q})\,\dot{q} - G(q) \Bigr).

Stacking the velocities and accelerations yields the first‑order state‑space equations{cite}`dip_khalil_2002_nonlinear_systems`

x˙_s=[x˙θ˙_1θ˙_2M(q)−1(B u−C(q,q˙) q˙−G(q))]=f(x_s)+g(x_s) u,\dot{\boldsymbol{x}}\_{s} = \begin{bmatrix} \dot{x} \\ \dot{\theta}\_{1} \\ \dot{\theta}\_{2} \\ M(q)^{-1}\bigl( B\,u - C(q,\dot{q})\,\dot{q} - G(q) \bigr) \end{bmatrix} = f(\boldsymbol{x}\_{s}) + g(\boldsymbol{x}\_{s})\,u,

where ff encodes the drift dynamics (including friction and gravity) and gg maps the input force to accelerations.  This compact representation is used by the simulator to propagate the state through numerical integration.

### **1.5 Derivation of the Coriolis Matrix Using Christoffel Symbols**

The velocity‑dependent terms in the manipulator equation can be systematically derived from the inertia matrix rather than guessed.  A rigorous approach introduces the **Christoffel symbols of the first kind**, which relate derivatives of the inertia matrix to velocity‑product terms{cite}`smc_slotine_li_1991_applied_nonlinear_control`{cite}`smc_slotine_li_1991_applied_nonlinear_control`.  For an nn‑DOF system with inertia matrix M(q)M(q), the symbol Γijk\Gamma_{ijk} is defined by partial derivatives of the mass matrix as

Γijk=∂Mik∂qj−12 ∂Mij∂qk.\Gamma_{ijk} = \frac{\partial M_{ik}}{\partial q_{j}} - \frac{1}{2}\,\frac{\partial M_{ij}}{\partial q_{k}}.

This formula arises from Lagrangian variational calculus and expresses how changes in the inertia matrix along one coordinate couple to accelerations in another{cite}`smc_slotine_li_1991_applied_nonlinear_control`{cite}`smc_slotine_li_1991_applied_nonlinear_control`.  Once the three‑dimensional array of Christoffel symbols has been computed, the Coriolis matrix is obtained by summing over the joint velocities:

Cij(q,q˙)=∑k=1nΓijk q˙k,C_{ij}\bigl( q,\dot{q} \bigr) = \sum_{k = 1}^{n}\Gamma_{ijk}\,{\dot{q}}_{k},

so that each entry CijC_{ij} is linear in the velocity vector q˙\dot{q}{cite}`smc_slotine_li_1991_applied_nonlinear_control`{cite}`smc_slotine_li_1991_applied_nonlinear_control`.  Computing CC for the double inverted pendulum therefore proceeds in three steps:

1. **Differentiate the inertia matrix.**  Starting from the matrix M(q)M(q) derived earlier, take partial derivatives of each element with respect to the generalized coordinates θ1\theta_{1} and θ2\theta_{2}.  The mass matrix does not depend on xx, so ∂M/∂x=0\partial M/\partial x = 0.  For example, differentiating the off‑diagonal term M12=(m1lc1+m2l1)cos⁡θ1M_{12} = \bigl( m_{1}l_{c1} + m_{2}l_{1} \bigr)\cos\theta_{1} with respect to θ1\theta_{1} yields −(m1lc1+m2l1)sin⁡θ1- \bigl( m_{1}l_{c1} + m_{2}l_{1} \bigr)\sin\theta_{1}, whereas ∂M12/∂θ2=0\partial M_{12}/\partial\theta_{2} = 0{cite}`smc_slotine_li_1991_applied_nonlinear_control`{cite}`smc_slotine_li_1991_applied_nonlinear_control`.
2. **Form the Christoffel symbols.**  For each index triple (i,j,k)(i,j,k), use the definition above to compute Γijk\Gamma_{ijk}.  Because MM is symmetric, many symbols vanish.  For instance, the only non‑zero symbols with i=2i = 2 or i=3i = 3 correspond to derivatives of the coupling term m2l1lc2cos⁡(θ1−θ2)m_{2}l_{1}l_{c2}\cos\bigl( \theta_{1} - \theta_{2} \bigr){cite}`smc_slotine_li_1991_applied_nonlinear_control`{cite}`smc_slotine_li_1991_applied_nonlinear_control`.
3. **Construct** C(q,q˙)C\bigl( q,\dot{q} \bigr).  Summing Γijk q˙k\Gamma_{ijk}\,{\dot{q}}_{k} over kk gives each entry of the Coriolis matrix{cite}`smc_slotine_li_1991_applied_nonlinear_control`{cite}`smc_slotine_li_1991_applied_nonlinear_control`.  For the double inverted pendulum, this procedure reproduces exactly the off‑diagonal velocity‑product terms shown in Section 1.4; for example,

C23=m2l1lc2 sin⁡(θ1−θ2) θ˙1,C12=− m2l1lc2 sin⁡(θ1−θ2) θ˙2,C_{23} = m_{2}l_{1}l_{c2}\,\sin\bigl( \theta_{1} - \theta_{2} \bigr)\,{\dot{\theta}}_{1},\quad\quad C_{12} = -\, m_{2}l_{1}l_{c2}\,\sin\bigl( \theta_{1} - \theta_{2} \bigr)\,{\dot{\theta}}_{2},

while the diagonal entries C11=bxC_{11} = b_{x}, C22=bθ1C_{22} = b_{\theta_{1}} and C33=bθ2C_{33} = b_{\theta_{2}} arise from viscous damping (see the next subsection).  The explicit derivation via Christoffel symbols confirms that the final matrix C(q,q˙)C\bigl( q,\dot{q} \bigr) presented earlier is correct.

### **1.6 Derivation of Non‑Actuated Generalized Forces**

The Euler–Lagrange equations require generalized forces QiQ_{i} on the right‑hand side.  In our model, the only non‑conservative effects are viscous friction and the input force uu.  A convenient way of incorporating dissipation is through the **Rayleigh dissipation function** DD.  For a mechanical system with viscous damping coefficients CjkC_{jk}, Rayleigh showed that one can define

D=12∑j=1m∑k=1mCjk q˙j q˙k,D = \frac{1}{2}\sum_{j = 1}^{m}{\sum_{k = 1}^{m}C_{jk}}\,{\dot{q}}_{j}\,{\dot{q}}_{k},

and then the generalized forces are given by

Qj=− ∂V∂qj−∂D∂q˙j,Q_{j} = - \,\frac{\partial V}{\partial q_{j}} - \frac{\partial D}{\partial{\dot{q}}_{j}},

so that the Euler–Lagrange equations become ddt(∂L/∂q˙j)−∂L/∂qj+∂D/∂q˙j=0\frac{d}{dt}\bigl( \partial L/\partial{\dot{q}}_{j} \bigr) - \partial L/\partial q_{j} + \partial D/\partial{\dot{q}}_{j} = 0.  In the double inverted pendulum, the potential energy VV depends only on the angles and yields the gravity vector G(q)G(q); the dissipative forces arise from linear viscous friction.  Choosing

D=12 bx x˙2+12 bθ1 θ˙_12+12 bθ2 θ˙_22,D = \frac{1}{2}\, b_{x}\,\dot{x}^{2} + \frac{1}{2}\, b_{\theta_{1}}\,\dot{\theta}\_{1}^{2} + \frac{1}{2}\, b_{\theta_{2}}\,\dot{\theta}\_{2}^{2},

we obtain the generalized forces

Qx=u−bx x˙,Qθ1=− bθ1 θ˙1,Qθ2=− bθ2 θ˙2.Q_{x} = u - b_{x}\,\dot{x},\quad Q_{\theta_{1}} = - \, b_{\theta_{1}}\,{\dot{\theta}}_{1},\quad Q_{\theta_{2}} = - \, b_{\theta_{2}}\,{\dot{\theta}}_{2}.

Only the cart coordinate experiences the external input uu; the pendulum joints are unactuated, so their generalized forces consist solely of viscous damping.  These expressions complete the derivation of the right‑hand side terms used in Section 1.3.

### **1.7 Model Singularities and Regularisation**

In multibody systems the inertia matrix may lose rank in certain configurations, leading to **singularities** in the equations of motion.  When a robot is near a singularity, it effectively loses one or more degrees of freedom and may require infinite joint accelerations to follow a finite Cartesian motion.  A singularity can be detected mathematically when the rank of the robot’s Jacobian or, equivalently, the determinant of the inertia matrix falls to zero.

For the double inverted pendulum, singular configurations occur when the pendulum links align colinearly with each other or with the vertical axis.  In these cases the coupling terms in the inertia matrix vanish, and the determinant of M(q)M(q) becomes zero.  Physically, the system can no longer generate independent accelerations in all three coordinates: for example, if both links are aligned and hanging downward, a horizontal force on the cart cannot change the relative angles, so θ¨1{\ddot{\theta}}_{1} and θ¨2{\ddot{\theta}}_{2} become indeterminate.  The manipulator‑form equations M(q) q¨=B u−C(q,q˙) q˙−G(q)M(q)\,\ddot{q} = B\, u - C\bigl( q,\dot{q} \bigr)\,\dot{q} - G(q) therefore fail because M(q)M(q) is not invertible.

The accompanying software mitigates this issue by monitoring the **condition number** of M(q)M(q).  The `config.yaml` file defines a parameter `singularity_cond_threshold` that specifies the maximum acceptable condition number; if κ(M)=∥M∥ ∥M−1∥\kappa(M) = \| M \|\,\| M^{- 1} \| exceeds this threshold, the functions `compute_matrices_numba` or `compute_inertia_numba` flag a singularity and return `NaN` values.  This regularisation prevents numerical instabilities during simulation.  By carefully choosing the initial conditions and limiting the range of motion (e.g., avoiding configurations where θ1≈θ2\theta_{1} \approx \theta_{2} or both angles approach ±π\pm \pi), controllers can steer the system away from singularities `DIP_SMC_PSO/config.yaml`.

------

[11](https://apmonitor.com/do/index.php/Main/DoubleInvertedPendulum#:~:text=L %3D T - V where T is the kinetic energy and V is the potential energy.) Double Inverted Pendulum Control — Dynamic Optimization

https://apmonitor.com/do/index.php/Main/DoubleInvertedPendulum

[22](https://en.wikipedia.org/wiki/Double_pendulum#:~:text=double pendulum is a physical system that exhibits rich dynamic behavior with a strong sensitivity to initial conditions) Double pendulum – chaotic motion and sensitivity to initial conditions

https://en.wikipedia.org/wiki/Double_pendulum

[33](https://en.wikipedia.org/wiki/Lagrangian_mechanics#:~:text=Dissipation (i.e. non,54) Lagrangian mechanics – Rayleigh dissipation and generalized forces

https://en.wikipedia.org/wiki/Lagrangian_mechanics

[44](https://adamheins.com/blog/lagrangian-mechanics-three-ways#:~:text=The Coriolis matrix) Implementing Lagrangian Mechanics Three Ways

https://adamheins.com/blog/lagrangian-mechanics-three-ways

[55](https://modernrobotics.northwestern.edu/nu-gm-book-resource/8-1-lagrangian-formulation-of-dynamics-part-2-of-2/#:~:text=Gamma of theta depends only on the joint values theta) Modern Robotics – Lagrangian formulation of dynamics (velocity‑product terms and Christoffel symbols)

https://modernrobotics.northwestern.edu/nu-gm-book-resource/8-1-lagrangian-formulation-of-dynamics-part-2-of-2/

[66](https://robodk.com/blog/robot-singularities/#:~:text=A singularity is a particular,move in an unexpected manner) Robot Singularities: What Are They and How to Beat Them – RoboDK blog

https://robodk.com/blog/robot-singularities/

## References

```{bibliography}
```
