# 1. Theoretical Background — Overview

## 1.1 Control Problem
- **Plant:** the system is a **double‑inverted pendulum on a cart**.
  Two rigid pendulums of lengths $l_1$ and $l_2$ are mounted on a cart
  of mass $m_0$.  The cart moves horizontally on a track and exerts a
  force $F$ to maintain the pendulums in the upright position.  The
  complete state vector is
  $x=[x,\theta_1,\theta_2,\dot{x},\dot{\theta}_1,\dot{\theta}_2]^\top$.

  > **State ordering note:** the implementation orders the pendulum angles before the velocities.  This $[x,\theta_1,\theta_2,\dot{x},\dot{\theta}_1,\dot{\theta}_2]$ ordering matches the state unpacking in the controllers (e.g. `AdaptiveSMC.compute_control()` and `SuperTwistingSMC`), where entries 1–2 correspond to the angles and entries 3–5 to the velocities.  Some literature uses $[x,\dot{x},\theta_1,\dot{\theta}_1,\theta_2,\dot{\theta}_2]$; adjust derivations accordingly when comparing with the code.
- **Inputs/Outputs/Disturbances:** the single input is the horizontal
  force $F$ (N).  Outputs include the cart position $x$ (m) and the
  pendulum angles $\theta_1,\theta_2$ (rad).  Disturbances arise from
  friction in the cart and joints, sensor noise and unmodelled dynamics.
  Gravity acts as a constant bias.
- **Operating regimes:** the controller is designed for small deviations
  about the upright equilibrium.  Linearisation assumptions
  ($\sin\theta\approx\theta$, $\cos\theta\approx1$) hold when
  $|\theta_1|,|\theta_2|\ll1$.  Operating modes include startup
  (swing‑up and stabilisation), set‑point changes (cart tracking) and
  fault handling (sensor dropout, actuator saturation).

## 1.2 Targets
- **Bandwidth:** approximately 3 rad/s.
- **Overshoot:** less than 10 %.
- **Settling time:** less than 2 s (to 2 % of the reference).
- **Steady‑state error:** less than 0.01 m.
- **Margins:** phase margin at least 45°, gain margin at least 6 dB.

> Keep SI units; define every symbol in `symbols.md`.

## 1.3 References
Papers, books and datasheets relevant to sliding‑mode control,
double‑inverted pendulum dynamics and PSO tuning.  See the repository
README for citations and further reading.