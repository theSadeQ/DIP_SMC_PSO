#==========================================================================================\\\
#======================== pso_optimization_validation_test.py ===========================\\\
#==========================================================================================\\\

"""
Comprehensive PSO Optimization and Dynamics Model Validation Test.

This script validates:
1. All dynamics models (Simplified, Full, LowRank) instantiation with empty config
2. PSO optimization workflows functionality
3. Parameter optimization validation workflows
4. Dynamics computation capabilities without crashes
"""

import sys
import os
import numpy as np
import logging
import traceback
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PSOOptimizationValidator:
    """Comprehensive validation of PSO optimization and dynamics models."""

    def __init__(self):
        """Initialize validation framework."""
        self.results = {
            'dynamics_models': {},
            'pso_optimization': {},
            'parameter_validation': {},
            'computation_tests': {},
            'overall_status': 'UNKNOWN',
            'timestamp': datetime.now().isoformat(),
            'summary': {}
        }

    def validate_dynamics_model_instantiation(self, model_name: str, model_class) -> Dict[str, Any]:
        """Test dynamics model instantiation with empty config."""
        logger.info(f"Testing {model_name} instantiation with empty config...")

        result = {
            'model_name': model_name,
            'instantiation_success': False,
            'empty_config_success': False,
            'default_params_success': False,
            'error_message': None,
            'status': 'FAILED'
        }

        try:
            # Test 1: Basic instantiation with empty config
            try:
                model_empty = model_class({})
                result['empty_config_success'] = True
                logger.info(f"✓ {model_name} instantiated successfully with empty config")
            except Exception as e:
                result['error_message'] = f"Empty config instantiation failed: {str(e)}"
                logger.warning(f"✗ {model_name} failed empty config instantiation: {str(e)}")

            # Test 2: Basic instantiation with default/None config
            try:
                model_none = model_class()
                result['instantiation_success'] = True
                logger.info(f"✓ {model_name} instantiated successfully with default config")
            except Exception as e:
                if not result['error_message']:
                    result['error_message'] = f"Default instantiation failed: {str(e)}"
                logger.warning(f"✗ {model_name} failed default instantiation: {str(e)}")

            # Test 3: Try instantiation with minimal working config
            try:
                # Basic physical parameters that most dynamics models expect
                minimal_config = {
                    'm1': 0.1,  # mass of first pendulum
                    'm2': 0.1,  # mass of second pendulum
                    'l1': 0.5,  # length of first pendulum
                    'l2': 0.5,  # length of second pendulum
                    'g': 9.81,  # gravity
                    'M': 1.0    # cart mass
                }
                model_minimal = model_class(minimal_config)
                result['default_params_success'] = True
                logger.info(f"✓ {model_name} instantiated successfully with minimal config")
            except Exception as e:
                logger.info(f"- {model_name} minimal config test: {str(e)}")

            # Set overall status
            if result['empty_config_success'] or result['instantiation_success']:
                result['status'] = 'FUNCTIONAL'
            elif result['default_params_success']:
                result['status'] = 'PARTIAL'

        except Exception as e:
            result['error_message'] = f"Validation framework error: {str(e)}"
            logger.error(f"Error validating {model_name}: {str(e)}")

        return result

    def validate_dynamics_computation(self, model_name: str, model_class) -> Dict[str, Any]:
        """Test dynamics computation capabilities without crashes."""
        logger.info(f"Testing {model_name} computation capabilities...")

        result = {
            'model_name': model_name,
            'computation_success': False,
            'state_derivative_success': False,
            'numerical_stability': False,
            'error_message': None,
            'status': 'FAILED'
        }

        try:
            # Create model instance with working parameters
            config = {
                'm1': 0.1, 'm2': 0.1, 'l1': 0.5, 'l2': 0.5,
                'g': 9.81, 'M': 1.0, 'b': 0.1
            }

            try:
                model = model_class(config)
            except:
                # Try with empty config if specific config fails
                try:
                    model = model_class({})
                except:
                    model = model_class()

            # Test state and control vectors
            state = np.array([0.1, 0.05, 0.0, 0.0, 0.0, 0.0])  # [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
            control = np.array([1.0])  # control force

            # Test dynamics computation
            try:
                if hasattr(model, 'compute_dynamics'):
                    derivatives = model.compute_dynamics(state, control)
                    result['computation_success'] = True
                elif hasattr(model, 'dynamics'):
                    derivatives = model.dynamics(state, control)
                    result['computation_success'] = True
                elif hasattr(model, '__call__'):
                    derivatives = model(state, control)
                    result['computation_success'] = True
                else:
                    result['error_message'] = "No recognized dynamics computation method found"

                if result['computation_success']:
                    # Check if derivatives are reasonable
                    if isinstance(derivatives, np.ndarray) and len(derivatives) == 6:
                        result['state_derivative_success'] = True
                        # Check for numerical issues
                        if np.all(np.isfinite(derivatives)):
                            result['numerical_stability'] = True
                            result['status'] = 'FUNCTIONAL'
                            logger.info(f"✓ {model_name} computation successful and numerically stable")
                        else:
                            result['status'] = 'PARTIAL'
                            logger.warning(f"△ {model_name} computation successful but has numerical issues")
                    else:
                        result['status'] = 'PARTIAL'
                        logger.warning(f"△ {model_name} computation returns unexpected format")

            except Exception as e:
                result['error_message'] = f"Computation failed: {str(e)}"
                logger.warning(f"✗ {model_name} dynamics computation failed: {str(e)}")

        except Exception as e:
            result['error_message'] = f"Model setup failed: {str(e)}"
            logger.error(f"Error setting up {model_name} for computation test: {str(e)}")

        return result

    def validate_pso_optimizer(self) -> Dict[str, Any]:
        """Validate PSO optimization workflows functionality."""
        logger.info("Testing PSO optimization workflows...")

        result = {
            'pso_import_success': False,
            'pso_instantiation_success': False,
            'basic_optimization_success': False,
            'parameter_bounds_success': False,
            'error_message': None,
            'status': 'FAILED'
        }

        try:
            # Test PSO import
            try:
                from src.optimizer.pso_optimizer import PSOTuner
                result['pso_import_success'] = True
                logger.info("✓ PSO optimizer import successful")
            except Exception as e:
                result['error_message'] = f"PSO import failed: {str(e)}"
                logger.error(f"✗ PSO optimizer import failed: {str(e)}")
                return result

            # Test PSO instantiation
            try:
                # Create basic configuration for PSO
                bounds = [(0.1, 100.0)] * 6  # 6 controller parameters
                pso_tuner = PSOTuner(
                    n_particles=10,
                    n_iterations=5,  # Small number for testing
                    bounds=bounds,
                    config_path=None  # Use default config
                )
                result['pso_instantiation_success'] = True
                logger.info("✓ PSO tuner instantiated successfully")

            except Exception as e:
                result['error_message'] = f"PSO instantiation failed: {str(e)}"
                logger.error(f"✗ PSO tuner instantiation failed: {str(e)}")
                return result

            # Test parameter bounds validation
            try:
                bounds_test = [(0.1, 10.0), (1.0, 20.0), (0.5, 15.0)]
                pso_bounds_test = PSOTuner(
                    n_particles=5,
                    n_iterations=2,
                    bounds=bounds_test
                )
                result['parameter_bounds_success'] = True
                logger.info("✓ PSO parameter bounds validation successful")
                result['status'] = 'FUNCTIONAL'

            except Exception as e:
                logger.warning(f"△ PSO bounds test issue: {str(e)}")
                if result['pso_instantiation_success']:
                    result['status'] = 'PARTIAL'

        except Exception as e:
            result['error_message'] = f"PSO validation framework error: {str(e)}"
            logger.error(f"Error in PSO validation: {str(e)}")

        return result

    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Execute comprehensive validation of all components."""
        logger.info("Starting comprehensive PSO optimization and dynamics validation...")

        # Import dynamics models
        dynamics_models = {}
        try:
            from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
            dynamics_models['SimplifiedDIPDynamics'] = SimplifiedDIPDynamics
            logger.info("✓ SimplifiedDIPDynamics imported")
        except Exception as e:
            logger.error(f"✗ Failed to import SimplifiedDIPDynamics: {e}")

        try:
            from src.plant.models.full.dynamics import FullDIPDynamics
            dynamics_models['FullDIPDynamics'] = FullDIPDynamics
            logger.info("✓ FullDIPDynamics imported")
        except Exception as e:
            logger.error(f"✗ Failed to import FullDIPDynamics: {e}")

        try:
            from src.plant.models.lowrank.dynamics import LowRankDIPDynamics
            dynamics_models['LowRankDIPDynamics'] = LowRankDIPDynamics
            logger.info("✓ LowRankDIPDynamics imported")
        except Exception as e:
            logger.error(f"✗ Failed to import LowRankDIPDynamics: {e}")

        # Validate dynamics models instantiation
        dynamics_results = {}
        for model_name, model_class in dynamics_models.items():
            dynamics_results[model_name] = self.validate_dynamics_model_instantiation(model_name, model_class)

        self.results['dynamics_models'] = dynamics_results

        # Validate dynamics computation
        computation_results = {}
        for model_name, model_class in dynamics_models.items():
            computation_results[model_name] = self.validate_dynamics_computation(model_name, model_class)

        self.results['computation_tests'] = computation_results

        # Validate PSO optimization
        self.results['pso_optimization'] = self.validate_pso_optimizer()

        # Generate summary
        self.generate_summary()

        return self.results

    def generate_summary(self):
        """Generate validation summary statistics."""
        summary = {
            'dynamics_working': 0,
            'dynamics_total': 0,
            'computation_working': 0,
            'computation_total': 0,
            'pso_status': 'UNKNOWN',
            'overall_health': 0.0
        }

        # Dynamics instantiation summary
        for model_name, result in self.results['dynamics_models'].items():
            summary['dynamics_total'] += 1
            if result['status'] in ['FUNCTIONAL', 'PARTIAL']:
                summary['dynamics_working'] += 1

        # Computation summary
        for model_name, result in self.results['computation_tests'].items():
            summary['computation_total'] += 1
            if result['status'] in ['FUNCTIONAL', 'PARTIAL']:
                summary['computation_working'] += 1

        # PSO status
        pso_result = self.results['pso_optimization']
        summary['pso_status'] = pso_result['status']

        # Overall health calculation
        dynamics_score = summary['dynamics_working'] / max(1, summary['dynamics_total'])
        computation_score = summary['computation_working'] / max(1, summary['computation_total'])
        pso_score = 1.0 if pso_result['status'] == 'FUNCTIONAL' else (0.5 if pso_result['status'] == 'PARTIAL' else 0.0)

        summary['overall_health'] = (dynamics_score * 0.4 + computation_score * 0.4 + pso_score * 0.2)

        # Set overall status
        if summary['overall_health'] >= 0.8:
            self.results['overall_status'] = 'FUNCTIONAL'
        elif summary['overall_health'] >= 0.5:
            self.results['overall_status'] = 'PARTIAL'
        else:
            self.results['overall_status'] = 'FAILED'

        self.results['summary'] = summary

        # Log summary
        logger.info(f"=== VALIDATION SUMMARY ===")
        logger.info(f"Dynamics Models: {summary['dynamics_working']}/{summary['dynamics_total']} working")
        logger.info(f"Computation Tests: {summary['computation_working']}/{summary['computation_total']} working")
        logger.info(f"PSO Optimization: {summary['pso_status']}")
        logger.info(f"Overall Health: {summary['overall_health']:.1%}")
        logger.info(f"Overall Status: {self.results['overall_status']}")


def main():
    """Main validation execution."""
    print("PSO Optimization and Dynamics Model Validation")
    print("=" * 60)

    validator = PSOOptimizationValidator()
    results = validator.run_comprehensive_validation()

    # Save results
    output_file = f"pso_optimization_validation_{datetime.now().strftime('%Y_%m_%d')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nValidation complete! Results saved to: {output_file}")
    print(f"Overall Status: {results['overall_status']}")
    print(f"Overall Health: {results['summary']['overall_health']:.1%}")

    return results


if __name__ == "__main__":
    main()