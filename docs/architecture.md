# 3. System Architecture

## 3.1 Loop topology
The controller architecture uses a **sliding‑mode control** law with optional
feedforward compensation and state estimation.  A simplified loop comprises:

- **Reference generator:** provides the desired cart position trajectory.
- **Error computation:** computes the deviation between the reference and
  the measured outputs (cart position and pendulum angles).
- **Sliding‑mode controller:** computes the control force $F$ using a
  classical, super‑twisting or adaptive SMC algorithm.  PSO tunes the
  SMC gains online or offline to minimise tracking error and chattering.
 - **Actuator saturation:** limits the commanded force to $\pm150\,\text{N}$ by clipping it to the `max_force` setting.  The fault‑detection system merely sets a status flag; it does not alter the control command.  Any safe‑state behaviour (for example, commanding zero force) must be implemented by a higher‑level supervisor. [CIT-045][CIT-064][CIT-065]
- **Plant dynamics:** the double inverted pendulum described in §1.
- **Observer (optional):** estimates unmeasured states; the current
  implementation measures all six state components directly.
- **PSO tuner:** adjusts controller gains by running multiple simulations
  and evaluating cost functions.  The tuner operates offline and writes
  tuned gains to JSON files for subsequent use. [CIT-070]

## 3.2 Interface contracts
See `io_contracts.csv` for authoritative signal names, units, rates, and ranges.

## 3.3 Timing, latency, and fallback
 - **Sampling:** the simulation and control operate at a base period $T_s=10\,\text{ms}$ (0.01 s), matching the `simulation.dt` parameter (0.01) in `config.yaml` [CIT-043].  Individual controller implementations may integrate internally at 1 ms, but the baseline configuration and logging use a 10 ms sample period.
 - **Quantization:** sensor measurements are quantised according to the step
   sizes configured in `config.yaml`.  By default the angle sensors are
   quantised with a resolution of **0.01 rad** and the cart position
   sensor is quantised with a resolution of **0.0005 m** (see the
   `sensors.quantization_angle` and `sensors.quantization_position`
   entries) [CIT-044].  These finite step sizes introduce quantisation noise that
   is modelled during simulation.  **Control commands are not
   quantised**; the actuator command is a continuous value which is
   subsequently saturated to the ±150 N limit [CIT-045].
- **Delays:** in hardware‑in‑the‑loop (HIL) operation, a network latency of
  up to 20 ms is tolerated; sequence numbers and CRC‑32 checks are used
  to detect dropped or out‑of‑order packets. [CIT-067][CIT-066]
 - **Fallback modes:** if numerical instabilities, actuator saturation or communication timeouts occur, the simulation raises an exception or clips the control input.  The current implementation **does not** automatically command a safe state; it simply saturates the force to the allowed limits and logs the fault.  External supervisory logic is responsible for deciding whether to zero the force and allow the pendulums to swing down before resuming operation.

## 3.4 Main block diagram
```mermaid
flowchart LR
  R[Reference r(t)] --> E[Σ]
  Y[Output y(t)] -->|−| E
  E --> C[Controller]
  C --> U[Actuator u(t)]
  U --> P[Plant]
  P --> Y
  D[Disturbance d(t)] --> P
```
