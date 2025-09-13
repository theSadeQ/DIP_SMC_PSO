# Symbols & Units

| Symbol | Meaning | Unit |
|:------:|---------|:----:|
| $u(t)$ | Control input (force applied to cart) | N |
| $x$ | Cart position | m |
| $\dot{x}$ | Cart velocity | m/s |
| $\theta_1$ | Angle of first pendulum | rad |
| $\dot{\theta}_1$ | Angular rate of first pendulum | rad/s |
| $\theta_2$ | Angle of second pendulum | rad |
| $\dot{\theta}_2$ | Angular rate of second pendulum | rad/s |
| $m_0$ | Mass of cart | kg |
| $m_1$ | Mass of first pendulum | kg |
| $m_2$ | Mass of second pendulum | kg |
| $l_1$ | Length of first pendulum | m |
| $l_2$ | Length of second pendulum | m |
| $g$ | Gravitational acceleration | m/s² |
| $l_{1,\mathrm{com}}$ | Centre‑of‑mass distance of first pendulum | m |
| $l_{2,\mathrm{com}}$ | Centre‑of‑mass distance of second pendulum | m |
| $I_1$ | Inertia of first pendulum about pivot | kg·m² |
| $I_2$ | Inertia of second pendulum about pivot | kg·m² |
| $b_c$ | Viscous friction coefficient for the cart | – |
| $b_1$ | Friction coefficient for the first joint | – |
| $b_2$ | Friction coefficient for the second joint | – |
| $k_1,k_2$ | Sliding‑surface gains weighting pendulum velocity and angle terms | – |
| $\lambda_1,\lambda_2$ | Slope parameters defining the sliding surface (convert angle errors to rate errors) | 1/s |
| $K$ | Switching gain multiplying the saturated sliding variable in the classical SMC control law | N |
| $k_d$ | Derivative (linear) gain used to damp the sliding surface dynamics | N/rad |
| $K_1,K_2$ | Algorithmic gains for the super‑twisting SMC (square‑root and integral terms) | N |
| $c_1,c_2$ | Gains defining the hybrid adaptive sliding surface | – |
| $\alpha$ | Proportional gain on the sliding variable $\sigma$ in adaptive SMC | N·s/rad |
| $\gamma$ | Adaptation rate for the switching gain $K$ in adaptive SMC (adds to $K$ proportionally to $|\sigma|$) | N/rad |
| $\sigma$ | Sliding surface value combining weighted angle and velocity errors | rad/s |
| $z$ | Internal integrator state used in the super‑twisting algorithm | N |
| $\varepsilon$ | Boundary‑layer width; scales the saturation function inside the switching law | rad/s |

> Use **unique symbols**, SI units by default. Extend this table as needed.
