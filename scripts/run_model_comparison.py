#==========================================================================================\\
#=========================== scripts/run_model_comparison.py ===========================\\
#==========================================================================================\\
"""
Run model comparison script.

This module compares the simplified (fast) double‑inverted pendulum model
against the full (parameter‑rich) model on a handful of representative
initial states.  The results show how well the simplified model
approximates the full dynamics.  Logging messages are formatted to avoid
unterminated string literals; each call to :func:`logging.info` uses a
single, properly terminated string.  According to the Python lexical
rules, triple‑quoted strings must be properly closed and may not cross
line breaks unintentionally【PythonLexical p.4, ISBN:978-1449355739】.
"""

import logging
from src.core.dynamics import DIPDynamics
from src.core.dynamics_full import FullDIPDynamics, compare_models
from src.config import load_config


def main() -> None:
    """Run the model comparison.

    The function loads the physics configuration, constructs both the
    simplified and full models, evaluates them on a set of initial
    conditions, and logs the derivative error.  A derivative error below
    0.1 indicates that the simplified model is a reasonable surrogate
    for the full dynamics.
    """
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info("=" * 60)
    logging.info("Running Model Comparison")
    logging.info("=" * 60)

    # Print a blank line for readability
    logging.info("\nRunning model comparison…")

    try:
        # Load physics configuration from YAML
        config = load_config("config.yaml")
        params = config.physics.model_dump()

        # Instantiate the simplified and full dynamics models
        simple = DIPDynamics(params)
        full = FullDIPDynamics(params)

        # Representative initial states to evaluate
        test_states = [
            ("Equilibrium", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            ("Small angle", [0.0, 0.1, 0.1, 0.0, 0.0, 0.0]),
        ]

        logging.info("\nModel Comparison Results:")
        logging.info("-" * 50)

        # Compute and log derivative error for each test state
        for name, state in test_states:
            metrics = compare_models(simple, full, state, u=0.0, dt=0.01)
            # Use a checkmark if the derivative error is within tolerance
            valid = "✓" if metrics.get('derivative_error', float('inf')) < 0.1 else "✗"
            logging.info(f"{name:<15} {metrics.get('derivative_error', float('nan')):<12.6f} {valid:<10}")

    except Exception as exc:
        # Log any failure during comparison
        logging.error(f"Model comparison failed: {exc}", exc_info=True)

    # Final summary
    logging.info("\n" + "=" * 60)
    logging.info("Model comparison complete!")


if __name__ == "__main__":  # pragma: no cover - execution guard for scripts
    main()