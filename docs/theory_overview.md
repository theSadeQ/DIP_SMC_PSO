# 1. Theoretical Background â€” Overview

## 1.1 Control Problem
- **Plant:** the system is a **doubleâ€‘inverted pendulum on a cart**.  Two
  rigid pendulums of lengths $l_1$ and $l_2$ are mounted on a cart of mass
  $m_0$.  The cart moves horizontally on a track and exerts a force $F$
  to maintain the pendulums in the upright position.  The complete state
  vector is $x=[x,\theta_1,\theta_2,\dot{x},\dot{\theta}_1,\dot{\theta}_2]^\top$.

  > **Note on state ordering:** the implementation orders the pendulum angles ahead of the velocities.  This $[x,\theta_1,\theta_2,\dot{x},\dot{\theta}_1,\dot{\theta}_2]$ ordering matches the controllers in `src/controllers` where state unpacking uses indices 1â€“2 for the angles and 3â€“5 for the velocities.  Some texts use $[x,\dot{x},\theta_1,\dot{\theta}_1,\theta_2,\dot{\theta}_2]$ instead; adjust your derivations accordingly when comparing with the code. [CIT-032]
- **Inputs/Outputs/Disturbances:** the single input is the horizontal force
  $F\,[\text{N}]$ applied by the actuator.  Outputs include the cart
  position $x\,[\text{m}]$ and the pendulum angles $\theta_1,\theta_2$
  $[\text{rad}]$.  Disturbances arise from friction in the cart and joints,
  sensor noise and unmodelled dynamics.  Gravity acts as a constant bias.
- **Operating regimes:** the controller is designed for small deviations
  about the upright equilibrium.  Linearisation assumptions ($\sin\theta\approx\theta$,
  $\cos\theta\approx1$) hold when $|\theta_1|,|\theta_2|\ll1$.  Operating
  modes include startup (swingâ€‘up and stabilisation), setâ€‘point changes
  (cart tracking) and fault handling (sensor dropout, actuator saturation). [CIT-071]

## 1.2 Targets
- **Bandwidth:** $\omega_{\mathrm{bw}} = 3\,\text{rad/s}$ (approximate).
- **Overshoot:** $M_p < 10\%$. [CIT-075]
- **Settling time:** $t_s < 2\,\text{s}$ (to 2Â % of the reference). [CIT-075]
- **Steadyâ€‘state error:** $e_{\mathrm{ss}} < 0.01\,\text{m}$.
- **Margins:** phase margin PM â‰¥Â 45Â°, gain margin GM â‰¥Â 6Â dB. [CIT-076]

> Keep SI units; define every symbol in `symbols.md`.

## 1.3 References
- Papers, books and datasheets relevant to slidingâ€‘mode control,
  doubleâ€‘inverted pendulum dynamics and PSO tuning.  See the repository
  README for citations and further reading.

SMC implementations referenced in this work: classical SMC, superâ€‘twisting SMC, and adaptive SMC are implemented in the codebase. [CIT-072][CIT-073][CIT-074]
