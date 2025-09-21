# Symbols & Units

| Symbol | Meaning | Unit |
|:------:|---------|:----:|
| $u(t)$ | Control input (force applied to cart) [CIT-001] | N |
| $x$ | Cart position [CIT-002] | m |
| $\dot{x}$ | Cart velocity [CIT-003] | m/s |
| $\theta_1$ | Angle of first pendulum [CIT-004] | rad |
| $\dot{\theta}_1$ | Angular rate of first pendulum [CIT-005] | rad/s |
| $\theta_2$ | Angle of second pendulum [CIT-006] | rad |
| $\dot{\theta}_2$ | Angular rate of second pendulum [CIT-007] | rad/s |
| $m_0$ | Mass of cart [CIT-008] | kg |
| $m_1$ | Mass of first pendulum [CIT-009] | kg |
| $m_2$ | Mass of second pendulum [CIT-010] | kg |
| $l_1$ | Length of first pendulum [CIT-011] | m |
| $l_2$ | Length of second pendulum [CIT-012] | m |
| $g$ | Gravitational acceleration [CIT-013] | m/s² |
| $l_{1,\mathrm{com}}$ | Centre‑of‑mass distance of first pendulum [CIT-014] | m |
| $l_{2,\mathrm{com}}$ | Centre‑of‑mass distance of second pendulum [CIT-015] | m |
| $I_1$ | Inertia of first pendulum about pivot [CIT-016] | kg·m² |
| $I_2$ | Inertia of second pendulum about pivot [CIT-017] | kg·m² |
| $b_c$ | Viscous friction coefficient for the cart [CIT-018] | – |
| $b_1$ | Friction coefficient for the first joint [CIT-019] | – |
| $b_2$ | Friction coefficient for the second joint [CIT-020] | – |
| $k_1,k_2$ | Sliding‑surface gains weighting pendulum velocity and angle terms [CIT-021] | – |
| $\lambda_1,\lambda_2$ | Slope parameters defining the sliding surface (convert angle errors to rate errors) [CIT-022] | 1/s |
| $K$ | Switching gain multiplying the saturated sliding variable in the classical SMC control law [CIT-023] | N |
| $k_d$ | Derivative (linear) gain used to damp the sliding surface dynamics [CIT-024] | N/rad |
| $K_1,K_2$ | Algorithmic gains for the super‑twisting SMC (square‑root and integral terms) [CIT-025] | N |
| $c_1,c_2$ | Gains defining the hybrid adaptive sliding surface [CIT-026] | – |
| $\alpha$ | Proportional gain on the sliding variable $\sigma$ in adaptive SMC [CIT-027] | N·s/rad |
| $\gamma$ | Adaptation rate for the switching gain $K$ in adaptive SMC (adds to $K$ proportionally to $|\sigma|$) [CIT-028] | N/rad |
| $\sigma$ | Sliding surface value combining weighted angle and velocity errors [CIT-029] | rad/s |
| $z$ | Internal integrator state used in the super‑twisting algorithm [CIT-030] | N |
| $\varepsilon$ | Boundary‑layer width; scales the saturation function inside the switching law [CIT-031] | rad/s |

> Use **unique symbols**, SI units by default. Extend this table as needed.
