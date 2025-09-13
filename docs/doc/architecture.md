# 3. System Architecture

## 3.1 Loop topology
The controller architecture uses a **sliding‑mode control** law with
optional feedforward compensation and state estimation.  A simplified
loop comprises:

- **Reference generator:** provides the desired cart position trajectory.
- **Error computation:** computes the deviation between the reference
  and the measured outputs (cart position and pendulum angles).
- **Sliding‑mode controller:** computes the control force $F$ using a
  classical, super‑twisting or adaptive SMC algorithm.  PSO tunes the
  SMC gains online or offline to minimise tracking error and chattering.
 - **Actuator saturation:** limits the commanded force to ±150 N by clipping it to the `max_force` setting.  The fault‑detection system only changes a status flag; it does **not** modify the control command.  Any safe‑state actions (such as zeroing the force) must be provided by an external supervisor.
- **Plant dynamics:** the double inverted pendulum described in §1.
- **Observer (optional):** estimates unmeasured states; the current
  implementation measures all six state components directly.
- **PSO tuner:** adjusts controller gains by running multiple
  simulations and evaluating cost functions.  The tuner operates
  offline and writes tuned gains to JSON files for subsequent use.

## 3.2 Interface contracts
See `io_contracts.csv` for authoritative signal names, units, rates and ranges.

## 3.3 Timing, latency and fallback
 - **Sampling:** the simulation and control operate at a base sample period $T_s=10$ ms (0.01 s), matching the `simulation.dt` value (0.01) in `config.yaml`.  Some controllers may integrate internally at 1 ms, but the baseline simulation and logging use a 10 ms period.
 - **Quantization:** sensor measurements are quantised according to
   the step sizes specified in `config.yaml`.  In the default
   configuration the angle measurements are quantised with a
   resolution of **0.01 rad** and the cart position is quantised with a
   resolution of **0.0005 m** (`sensors.quantization_angle` and
   `sensors.quantization_position`).  These finite resolutions
   introduce quantisation noise in the sensor readings.  **Control
   commands are not quantised**; the computed force is a continuous
   value which is then clipped to the ±150 N saturation limit.
- **Delays:** in hardware‑in‑the‑loop (HIL) operation, a network latency of
  up to 20 ms is tolerated; sequence numbers and CRC‑32 checks are used
  to detect dropped or out‑of‑order packets.
 - **Fallback modes:** if numerical instabilities, actuator saturation or communication timeouts occur, the simulation raises an exception or clips the control input.  The baseline controllers **do not** automatically command a safe‑state; they simply saturate the force and log the event.  A higher‑level supervisor must decide whether to zero the force and allow the pendulums to swing down before clearing the fault.

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