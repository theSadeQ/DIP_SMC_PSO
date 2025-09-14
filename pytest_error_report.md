# PyTest Error Report

**Date:** 2025-09-14
**Command:** `python -m pytest`
**Duration:** 39.25s
**Results:** 47 failed, 123 passed, 9 errors

## Test Summary

**Total Tests Collected:** 179
**Platform:** win32
**Python Version:** 3.13.7
**pytest Version:** 8.4.2

## Test Results Overview

### Status Breakdown
- **Passed:** 123 tests (68.7%)
- **Failed:** 47 tests (26.3%)
- **Errors:** 9 tests (5.0%)
- **Success Rate:** 68.7%

## Key Error Categories

### 1. Configuration/Setup Errors
Multiple tests failing due to configuration attribute errors:
```
AttributeError: 'dict' object has no attribute 'adaptive_smc'
```
Affecting:
- `tests/test_controllers/test_adaptive_smc.py` (3 errors)
- `tests/test_controllers/test_hybrid_adaptive_sta_smc.py` (1 error)
- `tests/test_controllers/test_sta_smc.py` (2 errors)

### 2. Benchmark Fixture Issues
```
PytestBenchmarkWarning: Benchmark fixture was not used at all in this test!
```
Affecting performance benchmarks in `tests/test_benchmarks/`

### 3. Core Controller Factory Issues
Configuration access pattern failing across multiple controller tests:
```python
@pytest.fixture
def adaptive_controller(config):
    gains = config.controller_defaults.adaptive_smc.gains
    #       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # AttributeError: 'dict' object has no attribute 'adaptive_smc'
```

## Detailed Error Categories

### Configuration-Related Errors (37 tests)
```
src.config.InvalidConfigurationError: Configuration validation failed:
- controller_defaults: Field required
- controllers: Field required
- pso: Field required
- physics: Field required
- physics_uncertainty: Field required
- simulation: Field required
- verification: Field required
- cost_function: Field required
- sensors: Field required
- hil: Field required
```

### Benchmark Warning Errors (3 tests)
```
pytest_benchmark.logger.PytestBenchmarkWarning: Benchmark fixture was not used at all in this test!
```

**Affected Tests:**
- `test_controller_compute_speed[classical_smc]`
- `test_controller_compute_speed[sta_smc]`
- `test_controller_compute_speed[adaptive_smc]`

### Test Implementation Issues

#### 1. Import/Module Errors
- Missing dependencies or circular imports
- Module path resolution issues

#### 2. Fixture Dependency Issues
- `physics_params` fixture not found
- Fixture dependency chain broken

#### 3. Test Data/Configuration Issues
- Invalid test configurations
- Missing test data files

## Failed Tests by Module

### `tests/config_validation/test_config_validation.py`
- 1 failure out of 8 tests

### `tests/test_app/test_cli.py`
- 5 failures out of 12 tests

### `tests/test_app/test_data_export.py`
- 1 failure out of 3 tests

### `tests/test_benchmarks/test_performance.py`
- 12 failures out of 12 tests

### `tests/test_benchmarks/test_statistical_benchmarks.py`
- 1 failure out of 1 test

### `tests/test_controllers/test_controller_basics.py`
- 1 failure out of 5 tests

### `tests/test_controllers/test_hybrid_extra.py`
- 5 failures out of 11 tests

### `tests/test_core/test_dynamics.py`
- 2 failures out of 9 tests

### `tests/test_core/test_dynamics_extra.py`
- 6 failures out of 6 tests

## Recommended Actions

### Immediate (Critical)
1. **Fix YAML syntax error in `config.yaml` line 153**
   - Review and correct the malformed YAML syntax
   - Validate entire config file structure

2. **Restore missing configuration sections**
   - Add back all required top-level configuration sections
   - Validate against the ConfigSchema

### Short-term (High Priority)
1. **Fix test fixture dependencies**
   - Restore `physics_params` fixture in appropriate conftest.py
   - Validate fixture dependency chains

2. **Review benchmark test implementations**
   - Fix benchmark fixture usage warnings
   - Update test implementations to properly use benchmark fixtures

### Medium-term (Medium Priority)
1. **Systematic test review**
   - Review failing integration tests
   - Update test expectations where needed
   - Fix test data dependencies

2. **Configuration validation**
   - Add configuration file validation to CI/CD
   - Create configuration file backup/restore mechanism

## Test Environment Details

```
Platform: win32
Python: 3.13.7
pytest: 8.4.2
pytest-benchmark: 5.1.0
pytest-hypothesis: 6.138.15
Working Directory: D:\Projects\main\DIP_SMC_PSO
```

## Next Steps

1. Fix the critical YAML configuration error first
2. Run pytest again to assess remaining issues
3. Focus on configuration-related test failures
4. Address test fixture and implementation issues
5. Validate all tests pass before committing changes

---

*This report was generated automatically by running pytest with verbose output and error capturing.*