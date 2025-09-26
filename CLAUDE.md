# CLAUDE.md — Team Memory & Project Conventions (Combined)

> This file unifies the content previously split across **CLAUDE.md** and **.CLAUDE.md**. Keep exactly one copy in the repo. If you prefer a clean root, store it as **.CLAUDE.md**.

------

## 1) Project Overview

**Double‑Inverted Pendulum Sliding Mode Control with PSO Optimization**

A comprehensive Python framework for simulating, controlling, and analyzing a double‑inverted pendulum (DIP) system. It provides multiple SMC variants, optimization (PSO), a CLI and a Streamlit UI, plus rigorous testing and documentation.

------

## 2) Architecture

### 2.1 High‑Level Modules

- **Controllers**: classical SMC, super‑twisting, adaptive, hybrid adaptive STA‑SMC, swing‑up; experimental MPC.
- **Dynamics/Plant**: simplified and full nonlinear dynamics (plus low‑rank); shared base interfaces.
- **Core Engine**: simulation runner, unified simulation context, batch/Numba vectorized simulators.
- **Optimization**: PSO tuner (operational); additional algorithms staged via an optimization core.
- **Utils**: validation, control primitives (e.g., saturation), monitoring, visualization, analysis, types, reproducibility, dev tools.
- **HIL**: plant server + controller client for hardware‑in‑the‑loop experiments.

### 2.2 Representative Layout (merged)

```
src/
├─ controllers/
│  ├─ classic_smc.py
│  ├─ sta_smc.py
│  ├─ adaptive_smc.py
│  ├─ hybrid_adaptive_sta_smc.py
│  ├─ swing_up_smc.py
│  ├─ mpc_controller.py
│  └─ factory.py
├─ core/
│  ├─ dynamics.py
│  ├─ dynamics_full.py
│  ├─ simulation_runner.py
│  ├─ simulation_context.py
│  └─ vector_sim.py
├─ plant/
│  ├─ models/
│  │  ├─ simplified/
│  │  ├─ full/
│  │  └─ lowrank/
│  ├─ configurations/
│  └─ core/
├─ optimizer/
│  └─ pso_optimizer.py
├─ utils/
│  ├─ validation/
│  ├─ control/
│  ├─ monitoring/
│  ├─ visualization/
│  ├─ analysis/
│  ├─ types/
│  ├─ reproducibility/
│  └─ development/
└─ hil/
   ├─ plant_server.py
   └─ controller_client.py
```

**Top‑level**

```
simulate.py        # CLI entry
streamlit_app.py   # Web UI
config.yaml        # Main configuration
requirements.txt   # Pinned deps / ranges
run_tests.py       # Test runner helper
README.md, CHANGELOG.md
```

------

## 3) Key Technologies

- Python 3.9+
- NumPy, SciPy, Matplotlib
- Numba for vectorized/batch simulation
- PySwarms / Optuna for optimization (PSO primary)
- Pydantic‑validated YAML configs
- pytest + pytest‑benchmark; Hypothesis where useful
- Streamlit for UI

------

## 4) Usage & Essential Commands

### 4.1 Simulations

```bash
python simulate.py --ctrl classical_smc --plot
python simulate.py --ctrl sta_smc --plot
python simulate.py --load tuned_gains.json --plot
python simulate.py --print-config
```

### 4.2 PSO Optimization

```bash
python simulate.py --ctrl classical_smc --run-pso --save gains_classical.json
python simulate.py --ctrl adaptive_smc --run-pso --seed 42 --save gains_adaptive.json
python simulate.py --ctrl hybrid_adaptive_sta_smc --run-pso --save gains_hybrid.json
```

### 4.3 HIL

```bash
python simulate.py --run-hil --plot
python simulate.py --config custom_config.yaml --run-hil
```

### 4.4 Testing

```bash
python run_tests.py
python -m pytest tests/test_controllers/test_classical_smc.py -v
python -m pytest tests/test_benchmarks/ --benchmark-only
python -m pytest tests/ --cov=src --cov-report=html
```

### 4.5 Web Interface

```bash
streamlit run streamlit_app.py
```

------

## 5) Configuration System

- Central `config.yaml` with strict validation.
- Domains: physics params, controller settings, PSO parameters, simulation settings, HIL config.
- Prefer “configuration first”: define parameters before implementation changes.

------

## 6) Development Guidelines

### 6.1 Code Style

- Type hints everywhere; clear, example‑rich docstrings.
- ASCII header format for Python files (≈90 chars width).
- Explicit error types; avoid broad excepts.

### 6.2 Adding New Controllers

1. Implement in `src/controllers/`.
2. Add to `src/controllers/factory.py`.
3. Extend `config.yaml`.
4. Add tests under `tests/test_controllers/`.

### 6.3 Batch Simulation

```python
from src.core.vector_sim import run_batch_simulation
results = run_batch_simulation(controller, dynamics, initial_conditions, sim_params)
```

### 6.4 Configuration Loading

```python
from src.config import load_config
config = load_config("config.yaml", allow_unknown=False)
```

------

## 7) Testing & Coverage Standards

### 7.1 Architecture of Tests

- Unit, integration, property‑based, benchmarks, and scientific validation.
- Example patterns:

```bash
pytest tests/test_controllers/ -k "not integration"
pytest tests/ -k "full_dynamics"
pytest --benchmark-only --benchmark-compare --benchmark-compare-fail=mean:5%
```

### 7.2 Coverage Targets

- **Overall** ≥ 85%
- **Critical components** (controllers, plant models, simulation engines) ≥ 95%
- **Safety‑critical** mechanisms: **100%**

### 7.3 Quality Gates (MANDATORY)

- Every new `.py` file has a `test_*.py` peer.
- Every public function/method has dedicated tests.
- Validate theoretical properties for critical algorithms.
- Include performance benchmarks for perf‑critical code.

------

## 8) Visualization & Analysis Toolkit

- Real‑time animations (DIPAnimator), static performance plots, project movie generator.
- Statistical analysis: confidence intervals, bootstrap, Welch’s t‑test, ANOVA, Monte Carlo.
- Real‑time monitoring (latency, deadline misses, weakly‑hard constraints) for control loops.

------

## 9) Production Safety & Readiness (Snapshot)

**Production Readiness Score: 6.1/10** (recently improved)

### Verified Improvements

- **Dependency safety**: numpy 2.0 issues resolved; version bounds added; verification tests green.
- **Memory safety**: bounded metric collections; cleanup mechanisms; memory monitoring.
- **SPOF removal**: DI/factory registry; multi‑source resilient config; graceful degradation.

### Outstanding Risks — DO NOT DEPLOY MULTI‑THREADED

- **Thread safety**: suspected deadlocks; concurrent ops unsafe; validation currently failing.
- Safe for **single‑threaded** operation with monitoring.

### Validation Commands

```bash
python scripts/verify_dependencies.py
python scripts/test_memory_leak_fixes.py
python scripts/test_spof_fixes.py
python scripts/test_thread_safety_fixes.py  # currently failing
```

------

## 10) Workspace Organization & Hygiene

### 10.1 Clean Root

Keep visible items ≤ 12 (core files/dirs only). Hide dev/build clutter behind dot‑prefixed folders.

**Visible files**: `simulate.py`, `streamlit_app.py`, `config.yaml`, `requirements.txt`, `README.md`, `CHANGELOG.md`

**Visible dirs**: `src/`, `tests/`, `docs/`, `notebooks/`, `benchmarks/`, `config/`

**Hidden dev dirs (examples)**: `.archive/`, `.build/`, `.dev_tools/`, `.scripts/`, `.tools/`
 Move **CLAUDE.md → .CLAUDE.md** if you prefer a clean root.

### 10.2 Universal Cache Cleanup

```bash
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
rm -rf .pytest_cache .ruff_cache .numba_cache .benchmarks .hypothesis
```

### 10.3 Backup & Docs Artifacts

```bash
find . -name "*.bak" -o -name "*.backup" -o -name "*~" | xargs -I{} mv {} .archive/ 2>/dev/null
# Docs build artifacts → archive
mv docs/_build docs/_static docs/.github docs/.gitignore docs/.lycheeignore .archive/
```

### 10.4 Enhanced .gitignore

```gitignore
**/__pycache__/
**/*.py[cod]
**/*$py.class
.benchmarks/
.numba_cache/
.pytest_cache/
.ruff_cache/
.hypothesis/
docs/_build/
docs/_static/
*.bak
*.backup
*~
```

### 10.5 Automation & Verification

```bash
# Helper for a clean view
echo "(create) .dev_tools/clean_view.sh to list essentials, key dirs, hidden tools"

# Health checks
ls | wc -l                                    # target ≤ 12
find . -name "__pycache__" | wc -l            # target = 0
find . -name "*.bak" -o -name "*.backup" -o -name "*~" | wc -l  # target = 0
```

### 10.6 After Moving/Consolidation — Update References

1. Search & replace hardcoded paths.
2. Update README and diagrams.
3. Fix CI workflows.
4. Re‑run tests.

------

## 11) Controller Factory & Example Snippets

```python
from src.controllers.factory import create_controller
controller = create_controller(
  'classical_smc',
  config=controller_config,
  gains=[10.0, 5.0, 8.0, 3.0, 15.0, 2.0]
)
control_output = controller.compute_control(state, last_control, history)
# Optimization (PSO)
from src.optimizer.pso_optimizer import PSOTuner
# ... initialize bounds, tuner, and run pso.optimize(...)
# Monitoring
from src.utils.monitoring.latency import LatencyMonitor
monitor = LatencyMonitor(dt=0.01)
start = monitor.start()
# ... loop ...
missed = monitor.end(start)
```

------

## 12) Multi-Agent Orchestration System

**4-Agent Parallel Orchestration for DIP SMC PSO Project**

This project implements an advanced **Ultimate Orchestrator** pattern specifically designed for complex control systems engineering tasks. The system automatically deploys 4 specialized agents in parallel for maximum efficiency and comprehensive validation coverage.

### 12.1 Project-Specific Agent Architecture

**🔵 Ultimate Orchestrator (Blue)** - Master conductor for DIP SMC PSO tasks
- Headless CI coordinator for integration validation and critical fixes
- Strategic planning with dependency-free task decomposition
- Parallel delegation to 3 subordinate domain specialists
- JSON-structured artifact integration and production readiness assessment

**Subordinate Specialist Agents (Parallel Execution):**
- 🌈 **Integration Coordinator** - DIP system health, configuration validation, dynamics models testing
- 🔴 **Control Systems Specialist** - SMC controller validation, factory testing, stability analysis
- 🔵 **PSO Optimization Engineer** - Parameter tuning workflows, convergence validation, optimization integration

### 12.2 Automatic Orchestration for DIP SMC PSO

**Integration Validation Workflow:**
```bash
# When Claude encounters: prompt/integration_recheck_validation_prompt.md
# Automatically deploys: Ultimate Orchestrator + 3 specialists in parallel
# Validates: Controllers (4/4), Dynamics (3/3), PSO workflows
# Result: 90% system health, production deployment recommendation
```

**Critical Fixes Orchestration:**
```bash
# When Claude encounters: prompt/integration_critical_fixes_orchestration.md
# Automatically deploys: All 4 agents with strategic coordination
# Fixes: Hybrid controller failures, configuration degraded mode, reset interfaces
# Result: 100% functional capability, all blocking issues resolved
```

### 12.3 DIP SMC PSO Validation Standards

**Controller Domain Validation:**
- Factory pattern testing (classical_smc, sta_smc, adaptive_smc, hybrid_adaptive_sta_smc)
- Reset interface compliance verification
- 6-element state vector computation testing
- Configuration system stability assessment

**Dynamics Models Validation:**
- SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics instantiation
- Empty configuration handling and fallback behavior
- Constructor parameter binding verification

**PSO Integration Validation:**
- Parameter bounds definition and enforcement
- Controller factory integration testing
- Optimization result serialization and packaging
- Convergence criteria and termination validation

### 12.4 Production Readiness Framework

**Quality Gates for DIP SMC PSO:**
- **System Health Threshold:** ≥90% composite score from all agents
- **Validation Matrix:** Must pass ≥6/7 critical components
- **Controller Health:** All 4 controller types must create successfully
- **Dynamics Health:** All 3 dynamics models must instantiate correctly
- **Configuration Health:** Degraded mode warnings acceptable, blocking errors not allowed

**Expected Artifacts:**
```
validation/
├─ controller_factory_results.json      # 4/4 controllers validation
├─ dynamics_models_results.json         # 3/3 dynamics models validation
├─ pso_workflow_results.json            # PSO optimization validation
├─ system_health_score.json             # Composite health assessment
└─ integration_validation_report.md     # Complete validation summary
```

### 12.5 DIP SMC PSO Orchestration Commands

The orchestrator recognizes and automatically handles:
- **Integration validation requests** - Comprehensive system health verification
- **Critical fixes orchestration** - Multi-domain problem resolution
- **Production readiness assessment** - Deployment go/no-go decisions
- **Regression detection** - Comparison with baseline system claims

This specialized orchestration ensures consistent, high-quality validation and development workflows specifically tailored for double-inverted pendulum sliding mode control systems with PSO optimization.

------

## 13) Success Criteria

- Clean root (≤ 12 visible entries), caches removed, backups archived.
- Test coverage gates met (85% overall / 95% critical / 100% safety‑critical).
- Single‑threaded operation stable; no dependency conflicts; memory bounded.
- Clear, validated configuration; reproducible experiments.

------

### Appendix: Notes

- Keep this file authoritative for style, testing, and operational posture.
- Treat it as versioned team memory; update via PRs with a short change log.