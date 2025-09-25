# Testing and Benchmarks

How to run tests and performance benchmarks mapped to the current layout.

## Run tests

```bash
python run_tests.py
pytest -q
```

Useful selectors:

```bash
pytest -q -k "full_dynamics"
pytest tests/test_analysis/performance/ -q
```

## Coverage

```bash
pytest --cov=src --cov-report=html
```

## Benchmarks

See `docs/benchmarks_methodology.md` and run:

```bash
pytest tests/test_analysis/performance/ --benchmark-only
```

