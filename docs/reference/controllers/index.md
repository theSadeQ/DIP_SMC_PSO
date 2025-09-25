# Controllers

This section maps to `src/controllers/` and documents controller implementations and factories.

- Key modules:
  - {py:mod}`src.controllers.smc` (SMC variants: classical, super-twisting, adaptive, hybrid)
  - {py:mod}`src.controllers.factory` (controller factories)
  - {py:mod}`src.controllers.mpc` (experimental MPC)
  - {py:mod}`src.controllers.specialized` (swing-up control)

See tests under `tests/test_utils/control/` and `tests/test_utils/analysis/` for examples of usage and validation patterns.

```{toctree}
:maxdepth: 1

classical-smc
super-twisting-smc
adaptive-smc
hybrid-adaptive-smc
```
