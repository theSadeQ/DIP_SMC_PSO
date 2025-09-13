# 3. System Architecture

## 3.1 Loop topology
PID / FF / Observer / MPC

## 3.2 Interface contracts
See `docs/io_contracts.csv` for authoritative signal names, units, rates, and ranges.

## 3.3 Timing, latency, and fallback
- **Sampling:** `T_s = ... s`
- **Quantization:** `n_bits = ...`
- **Delays:** `τ = ... s`
- **Fallback modes:** _safe-state definitions and triggers_

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
