# Testing Guide

## Golden-Path Testing Workflow

This guide documents the canonical way to run tests locally and in CI.

### Prerequisites

1. **Python Environment**: Python 3.9+ with all dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**: Ensure `config.yaml` is present and valid:
   ```bash
   python validate_config.py
   ```

### Local Development

#### Single Command for Full Test Suite

```bash
python -m pytest
```

This runs all tests with the default configuration. For development work, you might want faster feedback:

```bash
# Quick smoke tests (config and core functionality)
python -m pytest tests/config_validation/ tests/test_core/test_config.py -v

# Run with limited output
python -m pytest --tb=short --disable-warnings
```

#### Development Tips

- **Test a specific module**: `python -m pytest tests/test_controllers/test_classical_smc.py -v`
- **Test with coverage**: `python -m pytest --cov=src --cov-report=html`
- **Run benchmarks**: `python -m pytest tests/test_benchmarks/ --benchmark-only`
- **Stop on first failure**: `python -m pytest -x`

### Configuration Requirements

The test suite expects:

1. **Valid YAML syntax** in `config.yaml`
2. **Complete controller defaults** with gains for all controller types
3. **UTF-8 encoding** for all config files (no special Unicode characters)

### Common Failure Patterns

#### 1. Configuration Issues
```
ValidationError: 10 validation errors for ConfigSchema
```
**Solution**: Run `python validate_config.py` and fix reported issues.

#### 2. Missing Gains
```
ValueError: Controller 'classical_smc': gains parameter is required
```
**Solution**: Ensure tests provide gains parameter or use the session-scoped `config` fixture.

#### 3. Fixture Conflicts
```
pytest.fixture registered multiple times
```
**Solution**: Use session-scoped fixtures from `tests/conftest.py` instead of defining new ones.

#### 4. Import/Path Issues
```
ModuleNotFoundError: No module named 'src'
```
**Solution**: Ensure working directory is project root and `PYTHONPATH` includes `src/`.

### Test Architecture

#### Fixtures (tests/conftest.py)
- `config`: Session-scoped configuration loading
- `physics_cfg`: Physics parameters from config
- `dynamics`: Simplified DIP dynamics
- `full_dynamics`: Full nonlinear DIP dynamics
- `initial_state`: Standard test initial conditions
- `make_hybrid`: Factory for hybrid controller testing

#### Test Categories
- **Unit tests**: Individual component testing (`tests/test_controllers/`)
- **Integration tests**: End-to-end workflows (`tests/test_app/`)
- **Property-based**: Hypothesis-driven testing (`tests/test_property_based.py`)
- **Performance**: Regression benchmarking (`tests/test_benchmarks/`)
- **Configuration**: Schema validation (`tests/config_validation/`)

### CI Pipeline

The CI runs three stages:

1. **Config Validation** (`validate_config.py`)
   - Fast YAML syntax check
   - Configuration schema validation
   - Fail-fast if config is broken

2. **Smoke Tests**
   - Core configuration loading
   - Basic functionality verification
   - Runs in ~30 seconds

3. **Full Test Suite**
   - Complete test matrix across Python versions
   - All test categories including benchmarks
   - Fails pipeline on any test failure

### Environment Variables

The following environment variables affect test behavior:

- `MPLBACKEND=Agg`: Required for headless matplotlib (set automatically in conftest.py)
- `PYTHONPATH`: Should include `src/` directory
- `CI`: Detected automatically by pytest for CI-specific behavior

### Sample .env File

For local development, create a `.env` file:

```env
# Optional: Override config file location
CONFIG_PATH=config.yaml

# Optional: Set global random seed
GLOBAL_SEED=42

# Optional: Reduce simulation time for faster tests
SIMULATION_DURATION=1.0
```

### Troubleshooting

#### Tests Pass Locally but Fail in CI
1. Check Python version compatibility
2. Verify all dependencies are in `requirements.txt`
3. Ensure no system-specific paths in tests

#### Performance Regressions
1. Run benchmarks: `pytest tests/test_benchmarks/ --benchmark-only`
2. Compare with baseline: `pytest --benchmark-compare`
3. Check for memory leaks or infinite loops

#### Flaky Tests
1. Add deterministic seeds to random components
2. Use temporary directories for file operations
3. Mock external dependencies and network calls

For additional support, see the project documentation or file an issue.