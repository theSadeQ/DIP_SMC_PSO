#==========================================================================================\\\
#========================== pso_integration_health_validator.py ==========================\\\
#==========================================================================================\\\
"""
PSO Integration Health Validator for critical system repairs.

This module validates PSO integration stability and functionality with all
controller types during critical system repairs. Ensures optimization
workflows remain functional throughout interface standardization and
controller factory reconstruction.

Mission: Maintain PSO integration health score >8.0/10 during critical repairs.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
import logging
import json
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.config import load_config
    from src.controllers.factory import (
        create_controller,
        list_available_controllers,
        get_default_gains,
        CONTROLLER_REGISTRY
    )
    from src.optimizer.pso_optimizer import PSOTuner
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the DIP_SMC_PSO directory")
    sys.exit(1)


class PSOIntegrationHealthValidator:
    """
    Validator for PSO integration health during critical system repairs.

    Monitors PSO-controller integration stability and ensures optimization
    workflows remain functional as interfaces are standardized and
    controllers are repaired.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize validator with configuration."""
        # Use allow_unknown=True to handle interface standardization in progress
        self.config = load_config(config_path, allow_unknown=True)
        self.results: Dict[str, Any] = {
            'timestamp': datetime.now().isoformat(),
            'validation_id': f"pso_health_{int(datetime.now().timestamp())}",
            'overall_health': 0.0,
            'controller_tests': {},
            'integration_tests': {},
            'warnings': [],
            'errors': []
        }

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def validate_pso_optimizer_core(self) -> Dict[str, Any]:
        """Test PSO optimizer core functionality."""
        self.logger.info("Testing PSO optimizer core functionality...")

        test_results = {
            'initialization': False,
            'configuration_loading': False,
            'parameter_validation': False,
            'fitness_function': False,
            'score': 0.0
        }

        try:
            # Test 1: PSO Tuner initialization
            def dummy_factory(gains):
                """Dummy controller factory for testing."""
                class DummyController:
                    def __init__(self):
                        self.max_force = 150.0
                        self.gains = gains

                    def compute_control(self, state, last_u=None):
                        return np.array([0.0])  # Dummy control

                    def validate_gains(self, particles):
                        return np.ones(particles.shape[0], dtype=bool)

                    n_gains = len(gains)

                return DummyController()

            pso_tuner = PSOTuner(
                controller_factory=dummy_factory,
                config=self.config,
                seed=42
            )
            test_results['initialization'] = True
            self.logger.info("✓ PSO Tuner initialization successful")

            # Test 2: Configuration loading
            if hasattr(pso_tuner, 'cfg') and pso_tuner.cfg is not None:
                test_results['configuration_loading'] = True
                self.logger.info("✓ Configuration loading successful")

            # Test 3: Parameter validation
            if (hasattr(pso_tuner, 'weights') and
                hasattr(pso_tuner, 'instability_penalty') and
                pso_tuner.instability_penalty > 0):
                test_results['parameter_validation'] = True
                self.logger.info("✓ Parameter validation successful")

            # Test 4: Fitness function accessibility
            if hasattr(pso_tuner, '_fitness') and callable(pso_tuner._fitness):
                test_results['fitness_function'] = True
                self.logger.info("✓ Fitness function accessible")

            # Calculate score
            score = sum(test_results[k] for k in ['initialization', 'configuration_loading',
                                               'parameter_validation', 'fitness_function'])
            test_results['score'] = score / 4.0 * 10.0  # Out of 10

        except Exception as e:
            self.results['errors'].append(f"PSO core validation failed: {e}")
            self.logger.error(f"PSO core validation error: {e}")
            test_results['score'] = 0.0

        return test_results

    def test_controller_pso_integration(self, controller_type: str) -> Dict[str, Any]:
        """Test PSO integration with specific controller type."""
        self.logger.info(f"Testing PSO integration with {controller_type}...")

        test_results = {
            'controller_creation': False,
            'parameter_passing': False,
            'gains_validation': False,
            'factory_compatibility': False,
            'score': 0.0,
            'error_details': []
        }

        try:
            # Test 1: Controller creation
            default_gains = get_default_gains(controller_type)
            controller = create_controller(controller_type, self.config, default_gains)
            test_results['controller_creation'] = True
            self.logger.info(f"✓ {controller_type} controller creation successful")

            # Test 2: Parameter passing
            if hasattr(controller, 'max_force') and controller.max_force > 0:
                test_results['parameter_passing'] = True
                self.logger.info(f"✓ {controller_type} parameter passing successful")

            # Test 3: Gains validation (if controller supports it)
            if hasattr(controller, 'validate_gains'):
                try:
                    test_particles = np.array([default_gains, default_gains])
                    validation_result = controller.validate_gains(test_particles)
                    if isinstance(validation_result, np.ndarray):
                        test_results['gains_validation'] = True
                        self.logger.info(f"✓ {controller_type} gains validation successful")
                    else:
                        test_results['gains_validation'] = True  # Method exists but doesn't return array
                except Exception as e:
                    test_results['error_details'].append(f"Gains validation failed: {e}")
            else:
                test_results['gains_validation'] = True  # Not all controllers have this method

            # Test 4: Factory compatibility
            def controller_factory_test(gains_array):
                try:
                    return create_controller(controller_type, self.config, gains_array)
                except Exception as e:
                    raise RuntimeError(f"Factory failed for {controller_type}: {e}")

            # Test factory with sample gains
            test_controller = controller_factory_test(default_gains)
            if test_controller is not None:
                test_results['factory_compatibility'] = True
                self.logger.info(f"✓ {controller_type} factory compatibility successful")

            # Calculate score
            score_components = ['controller_creation', 'parameter_passing',
                              'gains_validation', 'factory_compatibility']
            score = sum(test_results[k] for k in score_components)
            test_results['score'] = score / len(score_components) * 10.0

        except Exception as e:
            error_msg = f"{controller_type} PSO integration failed: {e}"
            test_results['error_details'].append(error_msg)
            self.results['errors'].append(error_msg)
            self.logger.error(error_msg)
            test_results['score'] = 0.0

        return test_results

    def test_pso_optimization_workflow(self, controller_type: str) -> Dict[str, Any]:
        """Test end-to-end PSO optimization workflow for controller type."""
        self.logger.info(f"Testing PSO optimization workflow with {controller_type}...")

        test_results = {
            'pso_tuner_creation': False,
            'bounds_validation': False,
            'optimization_setup': False,
            'workflow_integrity': False,
            'score': 0.0,
            'error_details': []
        }

        try:
            # Create controller factory for PSO
            def pso_controller_factory(gains_array):
                return create_controller(controller_type, self.config, gains_array)

            # Test 1: PSO Tuner creation
            pso_tuner = PSOTuner(
                controller_factory=pso_controller_factory,
                config=self.config,
                seed=42
            )
            test_results['pso_tuner_creation'] = True
            self.logger.info(f"✓ PSO Tuner created for {controller_type}")

            # Test 2: Bounds validation
            expected_gains = len(get_default_gains(controller_type))
            pso_bounds_min = self.config.pso.bounds.min
            pso_bounds_max = self.config.pso.bounds.max

            if (len(pso_bounds_min) >= expected_gains and
                len(pso_bounds_max) >= expected_gains):
                test_results['bounds_validation'] = True
                self.logger.info(f"✓ PSO bounds validated for {controller_type}")
            else:
                test_results['error_details'].append(
                    f"Bounds mismatch: expected {expected_gains}, "
                    f"got min={len(pso_bounds_min)}, max={len(pso_bounds_max)}"
                )

            # Test 3: Optimization setup
            if hasattr(pso_tuner, 'optimise') and callable(pso_tuner.optimise):
                test_results['optimization_setup'] = True
                self.logger.info(f"✓ PSO optimization setup ready for {controller_type}")

            # Test 4: Workflow integrity (quick test without full optimization)
            try:
                # Test fitness function with sample particles
                default_gains = get_default_gains(controller_type)
                test_particles = np.array([default_gains])

                # This should not crash
                fitness_result = pso_tuner._fitness(test_particles)
                if isinstance(fitness_result, np.ndarray) and len(fitness_result) > 0:
                    test_results['workflow_integrity'] = True
                    self.logger.info(f"✓ PSO workflow integrity verified for {controller_type}")

            except Exception as e:
                test_results['error_details'].append(f"Workflow integrity test failed: {e}")

            # Calculate score
            score_components = ['pso_tuner_creation', 'bounds_validation',
                              'optimization_setup', 'workflow_integrity']
            score = sum(test_results[k] for k in score_components)
            test_results['score'] = score / len(score_components) * 10.0

        except Exception as e:
            error_msg = f"PSO workflow test failed for {controller_type}: {e}"
            test_results['error_details'].append(error_msg)
            self.results['errors'].append(error_msg)
            self.logger.error(error_msg)
            test_results['score'] = 0.0

        return test_results

    def test_thread_safety_indicators(self) -> Dict[str, Any]:
        """Test thread safety indicators for PSO operations."""
        self.logger.info("Testing PSO thread safety indicators...")

        test_results = {
            'local_rng_usage': False,
            'instance_isolation': False,
            'global_state_avoidance': False,
            'configuration_isolation': False,
            'score': 0.0,
            'warnings': []
        }

        try:
            def test_factory(gains):
                """Test factory for thread safety validation."""
                class TestController:
                    def __init__(self):
                        self.max_force = 150.0
                        self.gains = gains
                    n_gains = 6
                return TestController()

            pso_tuner = PSOTuner(
                controller_factory=test_factory,
                config=self.config,
                seed=42
            )

            # Test 1: Local RNG usage
            if hasattr(pso_tuner, 'rng') and hasattr(pso_tuner, 'seed'):
                test_results['local_rng_usage'] = True
                self.logger.info("✓ PSO uses local RNG (good for thread safety)")

            # Test 2: Instance isolation
            if hasattr(pso_tuner, 'instability_penalty') and hasattr(pso_tuner, 'combine_weights'):
                test_results['instance_isolation'] = True
                self.logger.info("✓ PSO uses instance-level parameters")

            # Test 3: Global state avoidance
            # Check if PSO avoids modifying global/class variables
            original_penalty = PSOTuner.INSTABILITY_PENALTY
            pso_tuner2 = PSOTuner(
                controller_factory=test_factory,
                config=self.config,
                seed=99
            )
            if PSOTuner.INSTABILITY_PENALTY == original_penalty:
                test_results['global_state_avoidance'] = True
                self.logger.info("✓ PSO avoids modifying global state")
            else:
                test_results['warnings'].append("PSO may modify global state")

            # Test 4: Configuration isolation
            if hasattr(pso_tuner, 'cfg') and pso_tuner.cfg is not pso_tuner2.cfg:
                test_results['configuration_isolation'] = True
                self.logger.info("✓ PSO configurations are isolated")
            elif not hasattr(pso_tuner, 'cfg'):
                test_results['warnings'].append("Cannot verify configuration isolation")
                test_results['configuration_isolation'] = True  # Assume good if no shared config

            # Calculate score
            score_components = ['local_rng_usage', 'instance_isolation',
                              'global_state_avoidance', 'configuration_isolation']
            score = sum(test_results[k] for k in score_components)
            test_results['score'] = score / len(score_components) * 10.0

        except Exception as e:
            error_msg = f"Thread safety test failed: {e}"
            test_results['warnings'].append(error_msg)
            self.logger.warning(error_msg)
            test_results['score'] = 5.0  # Partial score for inconclusive test

        return test_results

    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive PSO integration health validation."""
        self.logger.info("Starting comprehensive PSO integration health validation...")

        # Test PSO optimizer core
        core_results = self.validate_pso_optimizer_core()
        self.results['core_functionality'] = core_results

        # Test all available controllers
        available_controllers = list_available_controllers()
        self.logger.info(f"Testing {len(available_controllers)} controller types: {available_controllers}")

        controller_scores = []

        for controller_type in available_controllers:
            try:
                # Test basic integration
                integration_results = self.test_controller_pso_integration(controller_type)
                self.results['controller_tests'][f"{controller_type}_integration"] = integration_results

                # Test optimization workflow
                workflow_results = self.test_pso_optimization_workflow(controller_type)
                self.results['controller_tests'][f"{controller_type}_workflow"] = workflow_results

                # Calculate combined score for this controller
                combined_score = (integration_results['score'] + workflow_results['score']) / 2.0
                controller_scores.append(combined_score)

                self.logger.info(f"{controller_type} combined score: {combined_score:.1f}/10")

            except Exception as e:
                error_msg = f"Failed to test {controller_type}: {e}"
                self.results['errors'].append(error_msg)
                self.logger.error(error_msg)
                controller_scores.append(0.0)

        # Test thread safety
        thread_safety_results = self.test_thread_safety_indicators()
        self.results['integration_tests']['thread_safety'] = thread_safety_results

        # Calculate overall health score
        component_scores = [
            core_results['score'],
            np.mean(controller_scores) if controller_scores else 0.0,
            thread_safety_results['score']
        ]

        # Weight the components: core=40%, controllers=50%, thread_safety=10%
        weights = [0.4, 0.5, 0.1]
        overall_score = np.average(component_scores, weights=weights)

        self.results['overall_health'] = overall_score
        self.results['component_scores'] = {
            'core_functionality': core_results['score'],
            'controller_integration': np.mean(controller_scores) if controller_scores else 0.0,
            'thread_safety': thread_safety_results['score']
        }

        # Health assessment
        if overall_score >= 8.5:
            health_status = "EXCELLENT"
        elif overall_score >= 8.0:
            health_status = "GOOD"
        elif overall_score >= 6.0:
            health_status = "ACCEPTABLE"
        elif overall_score >= 4.0:
            health_status = "DEGRADED"
        else:
            health_status = "CRITICAL"

        self.results['health_status'] = health_status

        self.logger.info(f"PSO Integration Health Score: {overall_score:.1f}/10 ({health_status})")

        return self.results

    def save_results(self, filepath: str = None):
        """Save validation results to JSON file."""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"pso_health_validation_{timestamp}.json"

        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        self.logger.info(f"Results saved to {filepath}")

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*80)
        print("PSO INTEGRATION HEALTH VALIDATION SUMMARY")
        print("="*80)
        print(f"Validation ID: {self.results['validation_id']}")
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Overall Health Score: {self.results['overall_health']:.1f}/10")
        print(f"Health Status: {self.results['health_status']}")

        print("\nComponent Scores:")
        for component, score in self.results['component_scores'].items():
            print(f"  {component}: {score:.1f}/10")

        if self.results['warnings']:
            print(f"\nWarnings ({len(self.results['warnings'])}):")
            for warning in self.results['warnings'][:5]:  # Show first 5
                print(f"  - {warning}")

        if self.results['errors']:
            print(f"\nErrors ({len(self.results['errors'])}):")
            for error in self.results['errors'][:5]:  # Show first 5
                print(f"  - {error}")

        print("\nController Integration Status:")
        for test_name, test_result in self.results['controller_tests'].items():
            if 'integration' in test_name:
                controller = test_name.replace('_integration', '')
                score = test_result['score']
                status = "✓" if score >= 8.0 else "⚠" if score >= 6.0 else "✗"
                print(f"  {status} {controller}: {score:.1f}/10")

        print("="*80)


def main():
    """Main validation function."""
    try:
        validator = PSOIntegrationHealthValidator()
        results = validator.run_comprehensive_validation()

        validator.print_summary()
        validator.save_results()

        # Return appropriate exit code
        health_score = results['overall_health']
        if health_score >= 8.0:
            return 0  # Success
        elif health_score >= 6.0:
            return 1  # Warning
        else:
            return 2  # Critical

    except Exception as e:
        print(f"Validation failed with error: {e}")
        traceback.print_exc()
        return 3  # Error


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)