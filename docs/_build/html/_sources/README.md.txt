# Optimal Sliding Mode Control for a Double-Inverted Pendulum via PSO

[![Validate ResearchPlanSpec](https://github.com/theSadeQ/DIP_SMC_PSO/actions/workflows/validate.yml/badge.svg)](https://github.com/theSadeQ/DIP_SMC_PSO/actions/workflows/validate.yml)

## How to validate a ResearchPlan JSON

Run the validator locally:

```bash
python repo_validate.py plans/my_plan.json
```

**Exit codes:** 0 = no errors; 1 = validation errors present.

**Output:** machine-readable JSON report with `errors[]` and `warnings[]`.

### Schema version policy

Plans should include a schema version marker:

```json
{ "metadata": { "schema_version": "1.0", "...": "..." }, ... }
```

Currently missing or non-1.x versions produce a **WARNING** (accepted).
To enforce as errors later, set:

```bash
SCHEMA_VERSION_ENFORCE=error python repo_validate.py plans/my_plan.json
```

or use CLI flag:

```bash
python repo_validate.py --schema-version-enforce error plans/my_plan.json
```

### Performance limits

For safety and resource management:

```bash
# Set file size limit (default: 2MB) and timeout (default: 10s)
python repo_validate.py --max-bytes 1000000 --timeout-s 5 plans/my_plan.json

# Disable JSON Schema validation for faster processing
python repo_validate.py --jsonschema-off plans/my_plan.json
```

Keep examples in this README in sync with actual CLI output.

---

This project provides a comprehensive Python-based simulation environment for designing, tuning, and analyzing advanced sliding mode controllers (SMC) for a double-inverted pendulum on a cart. It features multiple controller types, automated gain tuning via Particle Swarm Optimization (PSO), and both command-line and interactive web-based interfaces.

## Key Features

-   **Advanced Controllers:** Implements three variants of Sliding Mode Control:
    -   **Classical SMC:** With a boundary layer for chattering reduction.
    -   **Super-Twisting SMC (STA):** A second-order SMC for continuous control and chattering elimination.
    -   **Adaptive SMC:** An adaptive controller that tunes its gains online to handle uncertainties.
-   **Automated Gain Tuning:** Utilizes Particle Swarm Optimization (PSO) to automatically find optimal controller gains based on a multi-objective cost function.
-   **Dual Dynamics Models:** Includes both a simplified nonlinear model for rapid iteration and a full, high-fidelity nonlinear model for accurate final validation.
-   **Command-Line Interface:** A powerful CLI (`simulate.py`) allows for running simulations, launching PSO optimizations, and saving/loading gains from the terminal.
-   **Interactive Web Application:** A Streamlit-based dashboard (`streamlit_app.py`) provides an interactive way to run simulations, tune controllers, and visualize results in real-time.

### New in Step 3

The latest iteration of the project introduces several improvements aimed at increasing robustness, physical realism and reproducibility:

- **Strict configuration validation:** All physical parameters (masses, lengths, inertias) must be strictly positive and friction coefficients non‑negative.  The simulation horizon must be at least one integration step (`duration ≥ dt`), and the diagonal regularization used in the dynamics model is enforced to be strictly positive.
- **Deprecated API removal:** The global function `set_allow_unknown_config()` has been removed in favor of explicit per‑call control through the `allow_unknown` argument to `load_config()`; passing the deprecated function now raises a `RuntimeError`.
- **Numerical stability detection:** The simulation runner raises a `NumericalInstabilityError` when the dynamics become ill‑conditioned, rather than propagating NaN values.  This makes failure modes explicit and easier to handle programmatically.
- **Continuous switching guidance:** The `saturate()` helper emits a warning when the linear switching method is used, encouraging the smoother hyperbolic‑tangent approximation to reduce chattering.  The boundary‑layer width (`epsilon`) should be chosen relative to measurement noise amplitude for a balance between robustness and steady‑state accuracy.
- **Moderate equivalent‑control saturation:** The model‑based equivalent control in the hybrid controller is now clamped to ±10×`max_force`.  This prevents the feedforward term from saturating the actuator before the adaptive sliding components engage.
- **Network integrity for HIL:** UDP communication between the plant server and controller client now includes sequence numbers and CRC‑32 checksums on every packet.  This enables detection of dropped, duplicate or corrupted packets and ensures that only fresh, verified measurements are used.
- **Reproducible noise injection:** The HIL plant server uses a per‑instance `numpy.random.Generator` seeded via the configuration’s `global_seed` to generate sensor noise.  Supplying a seed yields repeatable simulations; omitting it produces fresh noise sequences every run.
-   **Comprehensive Test Suite:** Includes a full suite of pytest unit and integration tests to ensure the correctness and robustness of all components.

## Getting Started

Follow these steps to set up and run the project on your local machine.

### 1. Prerequisites

-   Python 3.9 or newer
-   `pip` for package management

### 2. Installation

First, clone the repository to your local machine:

```bash
git clone <your-repository-url>
cd <repository-directory-name>
```

Next, install the required Python dependencies from the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Testing

This project includes a comprehensive and high-performance test suite to ensure correctness, stability, and scientific validity.

### Running the Tests

To run the complete test suite, execute the main test runner script from the root of the project:

```bash
python run_tests.py
```

This script will execute the full `pytest` suite located in the `tests/` directory. This includes the model comparison test, which checks for behavioral consistency between the simplified and full dynamics models.

### Test Suite Architecture

The test suite is built for speed and robustness. Key features include:

-   **Numba Acceleration:** Core simulations are executed using a custom, Numba-accelerated batch simulation engine (`src/core/vector_sim.py`) for maximum performance.
-   **Batch Testing:** Many tests run simulations in large batches with randomized initial conditions to ensure controllers are robust.
-   **Coverage:** The suite includes unit tests for individual components, integration tests for system-wide behavior, and scientific validation tests for principles like Lyapunov stability and chattering reduction.

### CI lanes & selectors

```bash
pytest -q -k "full_dynamics"
python dev/runner.py c1-02
python dev/runner.py c1-03
```

## Usage

You can interact with the simulation environment in two primary ways: through the command-line interface or the interactive web application.

### Command-Line Interface (CLI)

The `simulate.py` script is the main entry point for command-line operations.

To run a basic simulation with the classical controller and plot the results:

```bash
python simulate.py --ctrl classical --plot
```

To run a PSO optimization for the Super-Twisting controller:

```bash
python simulate.py --ctrl sta --save tuned_sta_gains.json
```

To run a simulation using pre-tuned gains and the full dynamics model:

```bash
python simulate.py --load tuned_sta_gains.json --full-dynamics --plot
```

For a full list of commands and options, run:

```bash
python simulate.py --help
```

### Interactive Web Application

For a more visual and interactive experience, you can launch the Streamlit dashboard.

To start the web application:

```bash
streamlit run streamlit_app.py
```

This will open a new tab in your web browser where you can select different controllers, run simulations, and view plots of the results interactively.

## Project Structure

The project is organized into several key directories:

-   `src/`: Contains all the main source code, including controllers and the core dynamics engine.
-   `tests/`: The Pytest test suite.
-   `scripts/`: Standalone scripts for tasks like re-optimization.
-   `docs/`: Detailed project documentation.

For a complete overview of the project's layout, please see the Project Structure Documentation.

## Performance Benchmarks (pytest-benchmark)

This project includes automated performance tests powered by **pytest-benchmark**.

### How to run
- Run only the benchmarks (recommended for CI comparisons):
  ```bash
  pytest --benchmark-only --benchmark-autosave
  ```
- Or run the full suite including benchmarks:
  ```bash
  pytest
  ```

### What gets measured
- **Controller microbenchmarks**: `compute_control` for each controller type (`classical_smc`, `sta_smc`, `adaptive_smc`) on a fixed state, to capture pure control-law overhead.
- **End-to-end throughput**: Batch simulation for 50 particles over 1.0s of sim time using the Numba vectorized engine.

### Comparing runs & catching regressions
Each run is saved under `.benchmarks/` when using `--benchmark-autosave`. To compare against the latest saved baseline and **fail on regressions** (e.g., if mean time grows by ≥5%), use:

```bash
pytest --benchmark-only --benchmark-compare        --benchmark-compare-fail=mean:5%
```

You can adjust the threshold as needed (e.g., `median:3%`, `max:10%`).

### Configuration
Benchmarks honor `config.yaml` values (e.g., `simulation.dt`, `controllers.*.max_force`, and whether to use the full dynamics). For quicker local runs, you can reduce workload via test fixtures (see `tests/conftest.py`).

Results include min/median/mean/stddev and number of rounds/iterations, enabling data-driven decisions about performance trade-offs.

## ResearchPlan Validation

This project includes a comprehensive validation system for ResearchPlan JSON specifications.

### Validate a ResearchPlan file

```bash
python repo_validate.py fixtures/valid_plan.json
python repo_validate.py fixtures/invalid_plan.json
```

### Using Make (if available)

```bash
# Validate default fixture
make validate

# Validate specific file
make validate FILE=fixtures/invalid_plan.json

# Run all validation tests
make test-validation
```

### Exit Codes

- **Exit 0**: Validation passed (no errors)
- **Exit 1**: Validation failed (has errors)

The validator generates machine-readable JSON reports with detailed error messages, field locations, and severity levels. See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete validation documentation and error model.
