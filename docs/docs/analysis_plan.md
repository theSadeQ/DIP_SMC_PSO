# 5. Analysis & Verification Plan

## 5.1 Tuning & Methods
- Approach: Rule-based / Optimization / ...
- Metrics: IAE, ISE, Overshoot, Bandwidth
- Robustness: Margins, Sensitivity, Uncertainty

## 5.2 Datasets
- Identification: `/data/raw/...`
- Validation: `/data/raw/...`

## 5.3 KPIs & Pass/Fail
| KPI ID | Definition | Target | Measured by (Test ID) | Pass/Fail Threshold |
|--------|------------|--------|-----------------------|---------------------|
| KPI-001| Settling time | t_s < 2 s | T-001 | t_s ≤ 2 s |

## 5.4 Logging Conventions
- Signals, rates, file formats, timebase. Store processed data in `/data/processed/`.
