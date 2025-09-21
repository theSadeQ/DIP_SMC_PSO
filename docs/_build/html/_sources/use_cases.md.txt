# 4. Use Cases & Operating Modes

## Mode inventory
Startup, Normal operation, Set‑point change, Shutdown, Fault handling.

---

The system supports several operating modes: **Startup**, **Normal
operation**, **Set‑point change**, **Shutdown** and **Fault handling**.  Each
use case below describes the mode, preconditions, sequence of steps,
expected responses and acceptance criteria.

### Use Case: UC‑Start‑01 — Startup
- **Mode:** Startup (swing‑up and stabilisation).
- **Preconditions:** system powered on; all sensors calibrated; pendulums
  may be hanging down.  Controller gains are initialised to nominal
  values.
- **Steps:**
  1. Engage the swing‑up routine to bring both pendulums toward the
     upright position using energy‑based control.
  2. When \(|\theta_1|,|\theta_2|<0.2\,\text{rad}\) and velocities are low,
     switch to the sliding‑mode stabilising controller [CIT-047].
  3. Continue stabilisation until both angles are within ±0.05 rad and
     cart velocity is near zero [CIT-047].
- **Expected response:** pendulums reach upright and settle; cart remains
  near the origin; controller switches seamlessly between swing‑up and
  stabilising modes.
- **KPIs:** Settling time (`KPI‑001`); overshoot (`KPI‑002`); energy used.
- **Acceptance criteria:** system reaches upright equilibrium within 5 s;
  no actuator saturation occurs.

### Use Case: UC‑Setpoint‑01 — Normal operation / set‑point change
- **Mode:** Normal operation.
- **Preconditions:** system stabilised in upright position; controller
  gains tuned.
- **Steps:**
  1. Receive a new cart position reference \(r\).
  2. Compute the error \(e = r - x\) and apply the sliding‑mode
     control law to generate the force command.
  3. Monitor the state; if \(|x - r| < 0.02\,\text{m}\) and
     \(|\theta_1|,|\theta_2|<0.05\,\text{rad}\) for 1 s, mark the
     manoeuvre as complete.
- **Expected response:** the cart tracks the new reference with
  minimal overshoot; pendulums remain upright.
- **KPIs:** Settling time, overshoot, IAE, stability margins.
- **Acceptance criteria:** manoeuvre completes within 2 s; overshoot <10 %.

### Use Case: UC‑Fault‑01 — Fault handling (sensor dropout)
 - **Mode:** Fault handling.
 - **Preconditions:** the fault‑detection module (`FDIsystem`) is enabled and the system is
   running under a selected controller.
 - **Steps:**
   1. For each sample the FDI computes a one‑step prediction of the state using the
      dynamics model and compares it to the current measurement.  The residual norm
      is evaluated on selected state components and optionally weighted.
  2. If the residual exceeds the configured `residual_threshold` for
      `persistence_counter` consecutive samples (10 by default), the FDI declares a
      fault.  In the default configuration (`FDIsystem` in
      `src/fault_detection/fdi.py`) the residual threshold is **0.5** and a
      fault is declared only after the residual norm exceeds 0.5 for ten
      consecutive 100 Hz samples [CIT-048].  Adaptive thresholding and CUSUM may adjust
      this threshold dynamically [CIT-049].
  3. Upon fault declaration the FDI system returns status "FAULT" and logs
      the detection time and residual norm.  The current implementation
      **does not automatically alter the control command**; external
      supervisory logic is responsible for deciding whether to engage a safe
      state (e.g. set the force to zero) or continue operation.  Thus a
      fault merely changes the reported status and records the event.

 - **Expected response:** the residual norm crosses the threshold and, after
   the configured persistence counter, the FDI status changes from
   "OK" to "FAULT".  Control continues unchanged unless a higher‑level
   supervisor intervenes.  Logs record the time of detection and the
   residual magnitude.

 - **KPIs:** time to detection and correct status change; successful fault
   detection (residual crosses the adaptive or fixed threshold and
   persists for the configured window).

 - **Acceptance criteria:** the FDI system declares a fault when the residual
   threshold is persistently exceeded; the detection time and residual
   are logged.  No specific safe‑state timing is defined because the
   controller does not enter a safe mode automatically.

> Consider edge cases: sensor dropout, saturation, actuator faults.
