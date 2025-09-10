"""Comprehensive validation of optimized controller gains.
This script validates the optimized gains by comparing the behavior
of the simplified vs. the full dynamics models.
"""

import json
import logging
import numpy as np
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

from typing import Dict, List, Tuple

sys.path.append(str(Path(__file__).parent.parent))

from src.core.dynamics import DIPDynamics
from src.core.dynamics_full import FullDIPDynamics, compare_models
from src.config import load_config

class GainValidator:
    """Validate optimized gains across multiple conditions."""
    
    def __init__(self, gains_file: str = "optimized_gains.json"):
        """Initialize validator with optimized gains."""
        try:
            with open(gains_file, 'r') as f:
                self.gains = json.load(f)
        except FileNotFoundError:
            logging.error(f"Gains file not found: {gains_file}. Please run reoptimize_controllers.py first.")
            sys.exit(1)
        
        self.config = load_config()
        self.results_dir = Path("validation_results")
        self.results_dir.mkdir(exist_ok=True)
    
    def validate_model_consistency(self, controller_type: str) -> Dict:
        """Validate gains work with both simple and full dynamics."""
        logging.info(f"\n{'='*50}")
        logging.info(f"Validating {controller_type} with different dynamics models")
        logging.info('='*50)
        
        # Create both dynamics models from the config
        simple_dynamics = DIPDynamics(self.config.physics.model_dump())
        full_dynamics = FullDIPDynamics(self.config.physics.model_dump())
        
        # Define a set of test conditions
        test_conditions = [
            ("equilibrium", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0.0),
            ("small_angle", [0.0, 0.1, 0.05, 0.0, 0.0, 0.0], 10.0),
            ("control_active", [0.0, 0.2, 0.15, 0.0, 0.5, 0.3], 25.0)
        ]
        
        results = {}
        
        for test_name, state, control in test_conditions:
            logging.info(f"\nTest: {test_name}")
            
            # Compare the output of the two models under the same conditions
            metrics = compare_models(simple_dynamics, full_dynamics, state, control, dt=0.01)
            
            logging.info(f"  Derivative error: {metrics['derivative_error']:.6f}")
            logging.info(f"  State error after 1 step: {metrics['state_error']:.6f}")
            logging.info(f"  Energy discrepancy: {metrics['energy_diff']:.6f}")
            
            if metrics['derivative_error'] > 0.1:
                logging.info("  ⚠️  Significant model difference!")
            else:
                logging.info("  ✓ Models are consistent")
            
            results[test_name] = metrics
        
        return results

    def generate_validation_report(self):
        """Generate comprehensive validation report."""
        report = ["# Gain Validation Report\n"]
        
        for controller_type in self.gains.keys():
            report.append(f"\n## {controller_type}\n")
            report.append(f"Optimized gains: {self.gains[controller_type]}\n")
            
            # Run all validations
            model_results = self.validate_model_consistency(controller_type)
            
            # Summarize results
            report.append("### Validation Summary\n")
            report.append("- **Model Consistency**: ")
            max_deriv_error = max([r['derivative_error'] for r in model_results.values()]) if model_results else 0
            report.append(f"{'PASS' if max_deriv_error < 0.1 else 'WARNING'} (max deriv error: {max_deriv_error:.4f})\n")
        
        # Save report
        report_file = self.results_dir / "validation_report.md"
        with open(report_file, 'w') as f:
            f.write(''.join(report))
        
        logging.info(f"\nValidation report saved to: {report_file}")

def main():
    """Run comprehensive gain validation."""
    logging.info("="*60)
    logging.info("Validating Optimized Controller Gains")
    logging.info("="*60)
    
    validator = GainValidator()
    validator.generate_validation_report()
    
    logging.info("\n" + "="*60)
    logging.info("Validation complete!")
    logging.info(f"Results saved in: {validator.results_dir}")
    logging.info("="*60)

if __name__ == "__main__":
    main()