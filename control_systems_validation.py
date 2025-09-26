#==========================================================================================\\\
#=============================== control_systems_validation.py ==========================\\\
#==========================================================================================\\\

"""
Control Systems Validation Specialist - Comprehensive DIP SMC PSO Validation
Independent verification of claimed fixes for controllers and dynamics models
"""

import sys
import traceback
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import time
import json

def log_test(test_name: str, status: str, message: str = "", details: Any = None):
    """Log test results with consistent formatting"""
    timestamp = time.strftime("%H:%M:%S")
    status_symbol = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "WARN"
    print(f"[{timestamp}] {status_symbol} {test_name}: {message}")
    if details and status == "FAIL":
        print(f"    Details: {details}")

class ControlSystemsValidator:
    """Comprehensive validation of controllers and dynamics models"""

    def __init__(self):
        self.results = {
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'controllers': {},
            'dynamics': {},
            'reset_interfaces': {},
            'summary': {},
            'issues': []
        }

    def validate_controller_factory(self) -> Dict[str, Any]:
        """Test all 4 controller types through factory creation"""
        log_test("CONTROLLER FACTORY", "INFO", "Starting controller factory validation")

        factory_results = {}

        try:
            # Import the factory (only need create_controller function)
            from src.controllers.factory import create_controller
            log_test("Factory Import", "PASS", "Successfully imported controller factory")

            # Test configurations for each controller type
            test_configs = {
                'classical_smc': {
                    'gains': [10.0, 5.0, 8.0, 3.0, 15.0, 2.0],
                    'max_force': 100.0,
                    'dt': 0.01
                },
                'sta_smc': {
                    'gains': [10.0, 5.0, 8.0, 3.0, 15.0, 2.0],
                    'alpha': 0.5,
                    'beta': 2.0,
                    'max_force': 100.0,
                    'dt': 0.01
                },
                'adaptive_smc': {
                    'gains': [10.0, 5.0, 8.0, 3.0, 2.0],
                    'adaptation_rates': [1.0, 1.0, 1.0, 1.0, 1.0],
                    'max_force': 100.0,
                    'dt': 0.01
                },
                'hybrid_adaptive_sta_smc': {
                    'gains': [10.0, 5.0, 8.0, 3.0, 2.0],
                    'adaptation_rates': [1.0, 1.0, 1.0, 1.0, 1.0],
                    'alpha': 0.5,
                    'beta': 2.0,
                    'max_force': 100.0,
                    'dt': 0.01
                }
            }

            # Test each controller type
            for ctrl_type, config in test_configs.items():
                try:
                    log_test(f"{ctrl_type.upper()}", "INFO", f"Testing controller: {ctrl_type}")

                    # Test factory creation
                    controller = create_controller(ctrl_type, config)
                    log_test(f"{ctrl_type} Creation", "PASS", "Factory creation successful")

                    # Test control computation
                    state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
                    try:
                        control_output = controller.compute_control(state, np.array([0.0]), {})

                        if isinstance(control_output, dict) and 'u' in control_output:
                            log_test(f"{ctrl_type} Compute", "PASS", f"Control output: {control_output['u']}")
                            factory_results[ctrl_type] = {
                                'creation': 'PASS',
                                'computation': 'PASS',
                                'control_value': float(control_output['u'])
                            }
                        else:
                            log_test(f"{ctrl_type} Compute", "FAIL", f"Invalid control output format: {type(control_output)}")
                            factory_results[ctrl_type] = {'creation': 'PASS', 'computation': 'FAIL', 'error': f'Invalid output format: {type(control_output)}'}

                    except Exception as e:
                        log_test(f"{ctrl_type} Compute", "FAIL", f"Control computation failed: {e}")
                        factory_results[ctrl_type] = {'creation': 'PASS', 'computation': 'FAIL', 'error': str(e)}

                except Exception as e:
                    log_test(f"{ctrl_type} Creation", "FAIL", f"Factory creation failed: {e}")
                    factory_results[ctrl_type] = {'creation': 'FAIL', 'error': str(e)}

        except Exception as e:
            log_test("Factory Import", "FAIL", f"Failed to import controller factory: {e}")
            factory_results['import_error'] = str(e)

        return factory_results

    def validate_dynamics_models(self) -> Dict[str, Any]:
        """Test all 3 dynamics models with instantiation and computation"""
        log_test("DYNAMICS MODELS", "INFO", "Starting dynamics models validation")

        dynamics_results = {}

        try:
            # Import dynamics classes
            from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
            from src.plant.models.full.dynamics import FullDIPDynamics
            from src.plant.models.lowrank.dynamics import LowRankDIPDynamics
            from src.plant import ConfigurationFactory

            log_test("Dynamics Import", "PASS", "Successfully imported all dynamics classes")

            # Test each dynamics model
            dynamics_classes = [
                ('simplified', SimplifiedDIPDynamics),
                ('full', FullDIPDynamics),
                ('lowrank', LowRankDIPDynamics)
            ]

            for model_name, dynamics_class in dynamics_classes:
                try:
                    log_test(f"{model_name.upper()}", "INFO", f"Testing dynamics: {model_name}")

                    # Test with default config
                    config = ConfigurationFactory.create_default_config(model_name)
                    dynamics = dynamics_class(config)
                    log_test(f"{model_name} Creation", "PASS", "Dynamics instantiation successful")

                    # Test dynamics computation
                    state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
                    control = np.array([1.0])

                    result = dynamics.compute_dynamics(state, control, 0.0)

                    if result.success:
                        log_test(f"{model_name} Compute", "PASS", f"Dynamics computation successful, derivatives shape: {result.state_derivative.shape}")
                        dynamics_results[model_name] = {
                            'creation': 'PASS',
                            'computation': 'PASS',
                            'derivatives_shape': result.state_derivative.shape,
                            'derivatives_norm': float(np.linalg.norm(result.state_derivative))
                        }
                    else:
                        log_test(f"{model_name} Compute", "FAIL", "Dynamics computation returned success=False")
                        dynamics_results[model_name] = {'creation': 'PASS', 'computation': 'FAIL', 'error': 'success=False'}

                except Exception as e:
                    log_test(f"{model_name} Test", "FAIL", f"Error testing {model_name}: {e}")
                    dynamics_results[model_name] = {'creation': 'FAIL', 'error': str(e)}

        except Exception as e:
            log_test("Dynamics Import", "FAIL", f"Failed to import dynamics: {e}")
            dynamics_results['import_error'] = str(e)

        return dynamics_results

    def validate_reset_interfaces(self) -> Dict[str, Any]:
        """Test reset() method functionality across controllers"""
        log_test("RESET INTERFACES", "INFO", "Starting reset interface validation")

        reset_results = {}

        try:
            from src.controllers.factory import create_controller

            controller_types = ['classical_smc', 'sta_smc', 'adaptive_smc', 'hybrid_adaptive_sta_smc']

            for ctrl_type in controller_types:
                try:
                    # Create controller with minimal config
                    config = {'gains': [10.0, 5.0, 8.0, 3.0, 15.0, 2.0], 'max_force': 100.0, 'dt': 0.01}
                    if ctrl_type in ['sta_smc', 'hybrid_adaptive_sta_smc']:
                        config.update({'alpha': 0.5, 'beta': 2.0})
                    if ctrl_type in ['adaptive_smc', 'hybrid_adaptive_sta_smc']:
                        config.update({'adaptation_rates': [1.0, 1.0, 1.0, 1.0, 1.0]})
                        config['gains'] = [10.0, 5.0, 8.0, 3.0, 2.0]  # Different gain structure for adaptive

                    controller = create_controller(ctrl_type, config)

                    # Test if reset method exists
                    if hasattr(controller, 'reset'):
                        try:
                            controller.reset()
                            log_test(f"{ctrl_type} Reset", "PASS", "Reset method executed successfully")
                            reset_results[ctrl_type] = {'has_reset': True, 'reset_works': True}
                        except Exception as e:
                            log_test(f"{ctrl_type} Reset", "FAIL", f"Reset method failed: {e}")
                            reset_results[ctrl_type] = {'has_reset': True, 'reset_works': False, 'error': str(e)}
                    else:
                        log_test(f"{ctrl_type} Reset", "WARN", "No reset method found")
                        reset_results[ctrl_type] = {'has_reset': False, 'reset_works': False}

                except Exception as e:
                    log_test(f"{ctrl_type} Reset Setup", "FAIL", f"Failed to create controller for reset test: {e}")
                    reset_results[ctrl_type] = {'error': str(e)}

        except Exception as e:
            log_test("Reset Import", "FAIL", f"Failed to import for reset testing: {e}")
            reset_results['import_error'] = str(e)

        return reset_results

    def validate_critical_hybrid_controller(self) -> Dict[str, Any]:
        """Special deep validation of hybrid_adaptive_sta_smc controller"""
        log_test("HYBRID CONTROLLER", "INFO", "Deep validation of hybrid_adaptive_sta_smc")

        hybrid_results = {}

        try:
            from src.controllers.factory import create_controller

            # Test the specific configuration that was failing
            config = {
                'gains': [10.0, 5.0, 8.0, 3.0, 2.0],
                'adaptation_rates': [1.0, 1.0, 1.0, 1.0, 1.0],
                'alpha': 0.5,
                'beta': 2.0,
                'max_force': 100.0,
                'dt': 0.01
            }

            controller = create_controller('hybrid_adaptive_sta_smc', config)
            log_test("Hybrid Creation", "PASS", "Hybrid controller created successfully")

            # Test multiple control computations to verify stability
            states = [
                np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0]),
                np.array([0.0, 0.0, 0.0, 0.1, 0.2, 0.3]),
                np.array([0.5, -0.5, 0.2, -0.1, 0.3, -0.2])
            ]

            control_outputs = []
            for i, state in enumerate(states):
                try:
                    control_output = controller.compute_control(state, np.array([0.0]), {})
                    if isinstance(control_output, dict) and 'u' in control_output:
                        control_outputs.append(float(control_output['u']))
                        log_test(f"Hybrid Compute {i+1}", "PASS", f"Control: {control_outputs[-1]:.3f}")
                    else:
                        log_test(f"Hybrid Compute {i+1}", "FAIL", f"Invalid control output format: {type(control_output)}")
                        hybrid_results['computation_error'] = f"Invalid output format: {type(control_output)}"
                        return hybrid_results
                except Exception as e:
                    log_test(f"Hybrid Compute {i+1}", "FAIL", f"Control computation failed: {e}")
                    hybrid_results['computation_error'] = str(e)
                    return hybrid_results

            hybrid_results = {
                'creation': 'PASS',
                'multiple_computations': 'PASS',
                'control_outputs': control_outputs,
                'output_range': [min(control_outputs), max(control_outputs)]
            }

        except Exception as e:
            log_test("Hybrid Creation", "FAIL", f"Hybrid controller creation failed: {e}")
            hybrid_results = {'creation': 'FAIL', 'error': str(e)}

        return hybrid_results

    def run_comprehensive_validation(self):
        """Execute all validation tests and compile results"""
        print("=" * 80)
        print("CONTROL SYSTEMS VALIDATION SPECIALIST")
        print("Comprehensive DIP SMC PSO Component Validation")
        print("=" * 80)
        print()

        # Run all validation tests
        self.results['controllers'] = self.validate_controller_factory()

        # Controllers validation complete

        self.results['dynamics'] = self.validate_dynamics_models()
        self.results['reset_interfaces'] = self.validate_reset_interfaces()
        self.results['hybrid_deep_test'] = self.validate_critical_hybrid_controller()

        # Generate summary
        self.generate_summary()

        # Print final report
        self.print_validation_report()

        return self.results

    def generate_summary(self):
        """Generate validation summary statistics"""
        summary = {}

        # Controller summary
        controller_passed = sum(1 for result in self.results['controllers'].values()
                              if isinstance(result, dict) and result.get('creation') == 'PASS' and result.get('computation') == 'PASS')
        controller_total = len([k for k in self.results['controllers'].keys() if k != 'import_error'])

        # Dynamics summary
        dynamics_passed = sum(1 for result in self.results['dynamics'].values()
                            if isinstance(result, dict) and result.get('creation') == 'PASS' and result.get('computation') == 'PASS')
        dynamics_total = len([k for k in self.results['dynamics'].keys() if k != 'import_error'])

        # Reset interface summary
        reset_working = sum(1 for result in self.results['reset_interfaces'].values()
                          if isinstance(result, dict) and result.get('reset_works') == True)
        reset_total = len([k for k in self.results['reset_interfaces'].keys() if k != 'import_error'])

        summary = {
            'controllers': {'passed': controller_passed, 'total': controller_total, 'percentage': (controller_passed/max(controller_total,1))*100},
            'dynamics': {'passed': dynamics_passed, 'total': dynamics_total, 'percentage': (dynamics_passed/max(dynamics_total,1))*100},
            'reset_interfaces': {'working': reset_working, 'total': reset_total, 'percentage': (reset_working/max(reset_total,1))*100},
            'hybrid_special': self.results['hybrid_deep_test'].get('creation') == 'PASS' and
                            self.results['hybrid_deep_test'].get('multiple_computations') == 'PASS',
            'overall_health': ((controller_passed + dynamics_passed + reset_working) / max(controller_total + dynamics_total + reset_total, 1)) * 100
        }

        self.results['summary'] = summary

    def print_validation_report(self):
        """Print comprehensive validation report"""
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY REPORT")
        print("=" * 80)

        summary = self.results['summary']

        print(f"\nCONTROLLERS: {summary['controllers']['passed']}/{summary['controllers']['total']} ({summary['controllers']['percentage']:.1f}%)")
        for ctrl_type, result in self.results['controllers'].items():
            if isinstance(result, dict) and 'creation' in result:
                status = "PASS" if result.get('creation') == 'PASS' and result.get('computation') == 'PASS' else "FAIL"
                print(f"  {ctrl_type:25} {status}")

        print(f"\nDYNAMICS MODELS: {summary['dynamics']['passed']}/{summary['dynamics']['total']} ({summary['dynamics']['percentage']:.1f}%)")
        for model_name, result in self.results['dynamics'].items():
            if isinstance(result, dict) and 'creation' in result:
                status = "PASS" if result.get('creation') == 'PASS' and result.get('computation') == 'PASS' else "FAIL"
                print(f"  {model_name:25} {status}")

        print(f"\nRESET INTERFACES: {summary['reset_interfaces']['working']}/{summary['reset_interfaces']['total']} ({summary['reset_interfaces']['percentage']:.1f}%)")
        for ctrl_type, result in self.results['reset_interfaces'].items():
            if isinstance(result, dict):
                has_reset = "YES" if result.get('has_reset') else "NO"
                works = "WORKS" if result.get('reset_works') else "FAILS" if result.get('has_reset') else "N/A"
                print(f"  {ctrl_type:25} {has_reset:5} {works}")

        print(f"\nHYBRID CONTROLLER SPECIAL TEST: {'PASS' if summary['hybrid_special'] else 'FAIL'}")

        print(f"\nOVERALL VALIDATION HEALTH: {summary['overall_health']:.1f}%")

        # Detailed issues
        issues = []
        for ctrl_type, result in self.results['controllers'].items():
            if isinstance(result, dict) and (result.get('creation') == 'FAIL' or result.get('computation') == 'FAIL'):
                issues.append(f"Controller {ctrl_type}: {result.get('error', 'Unknown error')}")

        for model_name, result in self.results['dynamics'].items():
            if isinstance(result, dict) and (result.get('creation') == 'FAIL' or result.get('computation') == 'FAIL'):
                issues.append(f"Dynamics {model_name}: {result.get('error', 'Unknown error')}")

        if issues:
            print(f"\nCRITICAL ISSUES IDENTIFIED ({len(issues)}):")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
        else:
            print("\nNO CRITICAL ISSUES IDENTIFIED")

        # Validation conclusion
        if summary['overall_health'] >= 90:
            print("\nPASS VALIDATION CONCLUSION: FIXES VERIFIED - System integration successful")
        elif summary['overall_health'] >= 75:
            print("\nWARN VALIDATION CONCLUSION: PARTIAL SUCCESS - Some issues remain")
        else:
            print("\nFAIL VALIDATION CONCLUSION: SIGNIFICANT ISSUES - Requires additional fixes")

def main():
    """Main validation execution"""
    validator = ControlSystemsValidator()
    results = validator.run_comprehensive_validation()

    # Save detailed results to file
    results_file = f"validation_results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: {results_file}")

    # Return exit code based on validation success
    health = results['summary']['overall_health']
    return 0 if health >= 75 else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFATAL ERROR in validation: {e}")
        traceback.print_exc()
        sys.exit(1)