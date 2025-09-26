#==========================================================================================\\\
#========================= controller_factory_validation.py ============================\\\
#==========================================================================================\\\

"""
Comprehensive controller factory validation and SMC logic testing.

This module validates controller instantiation, reset interfaces, and control
computation for all SMC variants in the DIP_SMC_PSO project.
"""

import sys
import os
import traceback
import json
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_controller_factory_comprehensive():
    """
    Execute comprehensive controller factory validation.

    Tests:
    1. Controller factory functionality for all controller types
    2. Hybrid controller specific deep testing
    3. Reset interface implementation validation
    4. Control computation testing for all SMC variants

    Returns:
        Dict with detailed validation results
    """
    results = {
        'timestamp': datetime.now().isoformat(),
        'test_summary': {
            'controllers_tested': 0,
            'controllers_working': 0,
            'controllers_with_reset': 0,
            'hybrid_controller_status': 'UNKNOWN',
            'critical_failures': []
        },
        'controller_tests': {},
        'reset_interface_tests': {},
        'control_computation_tests': {},
        'detailed_errors': {}
    }

    # Define test controllers and their expected configurations
    test_controllers = {
        'classical_smc': {
            'default_gains': [5.0, 5.0, 5.0, 0.5, 0.5, 0.5],
            'expected_gain_count': 6
        },
        'sta_smc': {
            'default_gains': [5.0, 3.0, 4.0, 4.0, 0.4, 0.4],
            'expected_gain_count': 6
        },
        'adaptive_smc': {
            'default_gains': [10.0, 8.0, 5.0, 4.0, 1.0],
            'expected_gain_count': 5
        },
        'hybrid_adaptive_sta_smc': {
            'default_gains': [5.0, 5.0, 5.0, 0.5],
            'expected_gain_count': 4
        }
    }

    print("=" * 80)
    print("CONTROLLER FACTORY VALIDATION AND SMC LOGIC TESTING")
    print("=" * 80)

    # Test 1: Controller Factory Functionality
    print("\n1. CONTROLLER FACTORY COMPREHENSIVE TEST")
    print("-" * 50)

    factory_available = False
    factory_error = None

    try:
        from src.controllers.factory import create_controller, list_available_controllers
        factory_available = True
        available_controllers = list_available_controllers()
        print(f"[OK] Factory imported successfully")
        print(f"[OK] Available controllers: {available_controllers}")
    except Exception as e:
        factory_error = str(e)
        print(f"[ERROR] Factory import failed: {e}")
        results['critical_failures'].append(f"Factory import failed: {e}")

    if factory_available:
        for controller_type, config in test_controllers.items():
            results['test_summary']['controllers_tested'] += 1
            test_result = {
                'creation_success': False,
                'error': None,
                'gains_used': None,
                'controller_type': None
            }

            print(f"\nTesting {controller_type}:")

            try:
                # Test controller creation with default parameters
                controller = create_controller(
                    controller_type=controller_type,
                    gains=config['default_gains']
                )

                test_result['creation_success'] = True
                test_result['gains_used'] = config['default_gains']
                test_result['controller_type'] = type(controller).__name__
                results['test_summary']['controllers_working'] += 1

                print(f"  [OK] Created successfully: {type(controller).__name__}")
                print(f"  [OK] Gains: {config['default_gains']}")

                # Store controller for further testing
                results['controller_tests'][controller_type] = {
                    'controller_instance': controller,
                    'creation_result': test_result
                }

            except Exception as e:
                test_result['error'] = str(e)
                test_result['traceback'] = traceback.format_exc()
                print(f"  [ERROR] Creation failed: {e}")
                results['detailed_errors'][controller_type] = {
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }

                if controller_type == 'hybrid_adaptive_sta_smc':
                    results['test_summary']['hybrid_controller_status'] = 'FAILED'
                    results['critical_failures'].append(f"Hybrid controller creation failed: {e}")

            results['controller_tests'][controller_type] = test_result

    # Test 2: Hybrid Controller Specific Deep Test
    print(f"\n2. HYBRID CONTROLLER SPECIFIC DEEP TEST")
    print("-" * 50)

    hybrid_deep_test_result = {
        'creation_with_different_configs': False,
        'dt_attribute_access': False,
        'config_validation': False,
        'errors': []
    }

    if factory_available:
        try:
            # Test 1: Creation with explicit config
            print("Testing hybrid controller with explicit configuration...")

            # Try different creation approaches
            approaches = [
                ("default_gains", lambda: create_controller('hybrid_adaptive_sta_smc')),
                ("explicit_gains", lambda: create_controller('hybrid_adaptive_sta_smc', gains=[5.0, 5.0, 5.0, 0.5])),
                ("minimal_config", lambda: create_controller('hybrid_adaptive_sta_smc', config=None))
            ]

            for approach_name, create_func in approaches:
                try:
                    hybrid_controller = create_func()
                    print(f"  [OK] {approach_name}: Created successfully")
                    hybrid_deep_test_result['creation_with_different_configs'] = True

                    # Test dt attribute access (this was the previous failure point)
                    if hasattr(hybrid_controller, 'config'):
                        config = hybrid_controller.config
                        if hasattr(config, 'dt'):
                            dt_value = config.dt
                            print(f"    [OK] dt attribute accessible: {dt_value}")
                            hybrid_deep_test_result['dt_attribute_access'] = True
                        else:
                            print(f"    ! dt attribute not found in config")
                            hybrid_deep_test_result['errors'].append(f"{approach_name}: No dt attribute in config")
                    else:
                        print(f"    ! No config attribute found")
                        hybrid_deep_test_result['errors'].append(f"{approach_name}: No config attribute")

                    # Test config validation
                    if hasattr(hybrid_controller, 'config'):
                        config_dict = {}
                        for attr in dir(hybrid_controller.config):
                            if not attr.startswith('_'):
                                try:
                                    val = getattr(hybrid_controller.config, attr)
                                    if not callable(val):
                                        config_dict[attr] = val
                                except:
                                    pass
                        print(f"    [OK] Config attributes: {list(config_dict.keys())}")
                        hybrid_deep_test_result['config_validation'] = True

                    break  # Success, no need to try other approaches

                except Exception as e:
                    print(f"  [ERROR] {approach_name}: Failed - {e}")
                    hybrid_deep_test_result['errors'].append(f"{approach_name}: {e}")

            if hybrid_deep_test_result['creation_with_different_configs']:
                results['test_summary']['hybrid_controller_status'] = 'FUNCTIONAL'
                print("  [OK] Hybrid controller deep test: PASSED")
            else:
                results['test_summary']['hybrid_controller_status'] = 'FAILED'
                print("  [ERROR] Hybrid controller deep test: FAILED")

        except Exception as e:
            hybrid_deep_test_result['errors'].append(f"Deep test exception: {e}")
            results['test_summary']['hybrid_controller_status'] = 'FAILED'
            print(f"  [ERROR] Hybrid controller deep test failed: {e}")

    results['hybrid_deep_test'] = hybrid_deep_test_result

    # Test 3: Reset Interface Validation
    print(f"\n3. RESET INTERFACE VALIDATION")
    print("-" * 50)

    for controller_type, test_data in results['controller_tests'].items():
        if isinstance(test_data, dict) and 'controller_instance' in test_data:
            controller = test_data['controller_instance']
            reset_test_result = {
                'has_reset_method': False,
                'reset_callable': False,
                'reset_execution_success': False,
                'error': None
            }

            print(f"\nTesting reset interface for {controller_type}:")

            # Check if reset method exists
            if hasattr(controller, 'reset'):
                reset_test_result['has_reset_method'] = True
                print(f"  [OK] Has reset method")

                # Check if reset is callable
                if callable(getattr(controller, 'reset')):
                    reset_test_result['reset_callable'] = True
                    print(f"  [OK] Reset method is callable")

                    # Test reset execution
                    try:
                        controller.reset()
                        reset_test_result['reset_execution_success'] = True
                        results['test_summary']['controllers_with_reset'] += 1
                        print(f"  [OK] Reset executed successfully")
                    except Exception as e:
                        reset_test_result['error'] = str(e)
                        print(f"  [ERROR] Reset execution failed: {e}")
                else:
                    print(f"  [ERROR] Reset method is not callable")
            else:
                print(f"  [ERROR] No reset method found")

            results['reset_interface_tests'][controller_type] = reset_test_result

    # Test 4: Control Computation Testing
    print(f"\n4. CONTROL COMPUTATION TESTING")
    print("-" * 50)

    # Create test state vector (6-element for DIP)
    test_state = np.array([0.1, 0.0, 0.05, 0.0, 0.02, 0.0])  # [θ1, θ1_dot, θ2, θ2_dot, x, x_dot]
    last_control = 0.0

    for controller_type, test_data in results['controller_tests'].items():
        if isinstance(test_data, dict) and 'controller_instance' in test_data:
            controller = test_data['controller_instance']
            control_test_result = {
                'has_compute_control': False,
                'compute_control_callable': False,
                'computation_success': False,
                'control_output': None,
                'output_type': None,
                'error': None
            }

            print(f"\nTesting control computation for {controller_type}:")

            # Check if compute_control method exists
            if hasattr(controller, 'compute_control'):
                control_test_result['has_compute_control'] = True
                print(f"  [OK] Has compute_control method")

                # Check if compute_control is callable
                if callable(getattr(controller, 'compute_control')):
                    control_test_result['compute_control_callable'] = True
                    print(f"  [OK] compute_control method is callable")

                    # Test control computation
                    try:
                        control_output = controller.compute_control(test_state, last_control)
                        control_test_result['computation_success'] = True
                        control_test_result['control_output'] = float(control_output) if np.isscalar(control_output) else control_output
                        control_test_result['output_type'] = type(control_output).__name__

                        print(f"  [OK] Control computation successful")
                        print(f"    Output: {control_output}")
                        print(f"    Type: {type(control_output).__name__}")

                        # Validate output is reasonable
                        if np.isscalar(control_output) and np.isfinite(control_output):
                            print(f"  [OK] Output is finite scalar")
                        else:
                            print(f"  ! Output validation warning: not finite scalar")

                    except Exception as e:
                        control_test_result['error'] = str(e)
                        control_test_result['traceback'] = traceback.format_exc()
                        print(f"  [ERROR] Control computation failed: {e}")
                        results['detailed_errors'][f"{controller_type}_compute_control"] = {
                            'error': str(e),
                            'traceback': traceback.format_exc()
                        }
                else:
                    print(f"  [ERROR] compute_control method is not callable")
            else:
                print(f"  [ERROR] No compute_control method found")

            results['control_computation_tests'][controller_type] = control_test_result

    # Calculate final statistics
    working_controllers = results['test_summary']['controllers_working']
    total_controllers = results['test_summary']['controllers_tested']
    controllers_with_reset = results['test_summary']['controllers_with_reset']

    print(f"\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Controllers working: {working_controllers}/{total_controllers} ({100 * working_controllers / max(total_controllers, 1):.1f}%)")
    print(f"Reset interface implementation: {controllers_with_reset}/{total_controllers} ({100 * controllers_with_reset / max(total_controllers, 1):.1f}%)")
    print(f"Hybrid controller status: {results['test_summary']['hybrid_controller_status']}")

    if results['critical_failures']:
        print(f"\nCRITICAL FAILURES:")
        for failure in results['critical_failures']:
            print(f"  - {failure}")

    if results['test_summary']['hybrid_controller_status'] == 'FUNCTIONAL':
        print(f"\n[SUCCESS] Hybrid controller previously failing with 'ClassicalSMCConfig' object has no attribute 'dt' is now FUNCTIONAL")

    # Compute overall validation score
    validation_score = 0
    if factory_available:
        validation_score += 25  # Factory works
    validation_score += (working_controllers / max(total_controllers, 1)) * 50  # Controllers work
    validation_score += (controllers_with_reset / max(total_controllers, 1)) * 15  # Reset interfaces
    if results['test_summary']['hybrid_controller_status'] == 'FUNCTIONAL':
        validation_score += 10  # Hybrid controller fixed

    results['validation_score'] = validation_score
    results['validation_grade'] = 'A' if validation_score >= 90 else 'B' if validation_score >= 80 else 'C' if validation_score >= 70 else 'F'

    print(f"\nVALIDATION SCORE: {validation_score:.1f}/100 (Grade: {results['validation_grade']})")

    return results


def save_validation_results(results: Dict[str, Any], filename: str = None) -> str:
    """Save validation results to JSON file."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"controller_factory_validation_{timestamp}.json"

    # Clean results for JSON serialization
    clean_results = {}
    for key, value in results.items():
        if key == 'controller_tests':
            # Remove controller instances which can't be serialized
            clean_controller_tests = {}
            for ctrl_type, ctrl_data in value.items():
                if isinstance(ctrl_data, dict):
                    clean_ctrl_data = {k: v for k, v in ctrl_data.items() if k != 'controller_instance'}
                    clean_controller_tests[ctrl_type] = clean_ctrl_data
                else:
                    clean_controller_tests[ctrl_type] = ctrl_data
            clean_results[key] = clean_controller_tests
        else:
            clean_results[key] = value

    filepath = os.path.join(project_root, filename)
    with open(filepath, 'w') as f:
        json.dump(clean_results, f, indent=2, default=str)

    return filepath


def main():
    """Main validation execution."""
    print("Starting comprehensive controller factory validation...")

    # Execute validation
    results = test_controller_factory_comprehensive()

    # Save results
    results_file = save_validation_results(results)
    print(f"\nValidation results saved to: {results_file}")

    # Return validation score for CI/automation
    return results['validation_score']


if __name__ == "__main__":
    validation_score = main()
    print(f"\nFinal validation score: {validation_score}/100")

    # Exit with appropriate code for CI
    exit_code = 0 if validation_score >= 80 else 1
    sys.exit(exit_code)