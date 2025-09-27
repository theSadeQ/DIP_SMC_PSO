#!/usr/bin/env python3
"""
Final Controller Factory Validation for Production Deployment
Validates all 4 controllers with comprehensive interface testing
"""

from src.controllers.factory import create_controller
from src.config import load_config
import numpy as np
import json
from datetime import datetime

def run_controller_validation():
    config = load_config('config.yaml', allow_unknown=False)
    controllers = ['classical_smc', 'adaptive_smc', 'sta_smc', 'hybrid_adaptive_sta_smc']

    # Final Controller Factory Validation Results
    validation_results = {
        'test_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_controllers': len(controllers),
        'passed_controllers': 0,
        'failed_controllers': 0,
        'controller_details': {},
        'critical_tests': {
            'factory_instantiation': 0,
            'reset_method_coverage': 0,
            'compute_control_interface': 0,
            'attribute_integrity': 0,
            'output_format_compliance': 0
        },
        'production_ready': False
    }

    # Test state vector and history (proper interface)
    test_state = np.array([0.1, 0.0, 0.05, 0.0, 0.0, 0.0])
    last_control = 0.0
    history = {'states': [], 'controls': [], 'time': []}

    print('=== FINAL CONTROLLER FACTORY VALIDATION ===')
    print(f'Testing {len(controllers)} controllers with production interface requirements')
    print()

    for ctrl_name in controllers:
        print(f'Testing Controller: {ctrl_name}')

        test_results = {
            'instantiation': False,
            'reset_method': False,
            'compute_control': False,
            'attributes_valid': False,
            'output_format_valid': False,
            'control_value': None,
            'error_messages': []
        }

        try:
            # Test 1: Factory instantiation
            controller = create_controller(ctrl_name, config.controllers[ctrl_name])
            test_results['instantiation'] = True
            validation_results['critical_tests']['factory_instantiation'] += 1
            print(f'  [PASS] Instantiation - Type: {type(controller).__name__}')

            # Test 2: Reset method
            if hasattr(controller, 'reset') and callable(getattr(controller, 'reset')):
                controller.reset()
                test_results['reset_method'] = True
                validation_results['critical_tests']['reset_method_coverage'] += 1
                print('  [PASS] Reset method working')
            else:
                test_results['error_messages'].append('Missing reset method')
                print('  [FAIL] Reset method missing')

            # Test 3: Compute control interface with proper validation
            try:
                control_output = controller.compute_control(test_state, last_control, history)
                test_results['compute_control'] = True
                validation_results['critical_tests']['compute_control_interface'] += 1

                # Test 4: Output format validation (expecting dictionary with 'u' key)
                if isinstance(control_output, dict) and 'u' in control_output:
                    control_value = control_output['u']
                    if isinstance(control_value, (int, float, np.number)):
                        test_results['output_format_valid'] = True
                        test_results['control_value'] = float(control_value)
                        validation_results['critical_tests']['output_format_compliance'] += 1
                        print(f'  [PASS] Control output format valid - u={control_value:.4f}')
                    else:
                        test_results['error_messages'].append(f'Invalid control value type: {type(control_value)}')
                        print(f'  [FAIL] Invalid control value type: {type(control_value)}')
                else:
                    test_results['error_messages'].append(f'Invalid output format: {type(control_output)}')
                    print(f'  [FAIL] Invalid output format - expected dict with u key')

            except Exception as e:
                test_results['error_messages'].append(f'Compute control error: {str(e)}')
                print(f'  [FAIL] Compute control error: {str(e)}')

            # Test 5: Attribute integrity
            required_attrs = ['compute_control', '__class__', '__dict__']
            missing_attrs = [attr for attr in required_attrs if not hasattr(controller, attr)]
            if not missing_attrs:
                test_results['attributes_valid'] = True
                validation_results['critical_tests']['attribute_integrity'] += 1
                print('  [PASS] All required attributes present')
            else:
                test_results['error_messages'].append(f'Missing attributes: {missing_attrs}')
                print(f'  [FAIL] Missing attributes: {missing_attrs}')

            # Overall controller assessment - ALL 5 tests must pass
            all_tests_passed = all([
                test_results['instantiation'],
                test_results['reset_method'],
                test_results['compute_control'],
                test_results['output_format_valid'],
                test_results['attributes_valid']
            ])

            if all_tests_passed:
                validation_results['passed_controllers'] += 1
                print(f'  [SUCCESS] {ctrl_name} - ALL TESTS PASSED')
            else:
                validation_results['failed_controllers'] += 1
                failed_tests = [k for k, v in test_results.items()
                              if k.endswith(('instantiation', 'reset_method', 'compute_control',
                                            'output_format_valid', 'attributes_valid')) and not v]
                print(f'  [PARTIAL] {ctrl_name} - Failed: {failed_tests}')

            print()

        except Exception as e:
            validation_results['failed_controllers'] += 1
            test_results['error_messages'].append(f'Critical failure: {str(e)}')
            print(f'  [CRITICAL] {ctrl_name} - Critical failure: {str(e)}')
            print()

        validation_results['controller_details'][ctrl_name] = test_results

    # Calculate final metrics
    total_controllers = validation_results['total_controllers']
    coverage_stats = {}
    for test_name, passed_count in validation_results['critical_tests'].items():
        coverage_stats[test_name] = (passed_count / total_controllers) * 100

    overall_health = (validation_results['passed_controllers'] / total_controllers) * 100
    validation_results['production_ready'] = overall_health == 100

    print('=== CONTROLLER FACTORY VALIDATION SUMMARY ===')
    print(f'Total Controllers: {total_controllers}')
    print(f'Fully Functional: {validation_results["passed_controllers"]}')
    print(f'Failed/Partial: {validation_results["failed_controllers"]}')
    print()
    print('Coverage Statistics:')
    for test_name, percentage in coverage_stats.items():
        status = '[PASS]' if percentage == 100 else '[FAIL]'
        print(f'  {status} {test_name}: {percentage:.1f}%')
    print()
    print(f'Overall Controller Health: {overall_health:.1f}%')

    if overall_health == 100:
        print('[SUCCESS] PRODUCTION READY: All 4 controllers fully functional')
        print('- 100% factory instantiation coverage')
        print('- 100% reset method interface coverage')
        print('- 100% compute control interface coverage')
        print('- 100% output format compliance')
        print('- 100% attribute integrity validation')
    elif overall_health >= 75:
        print('[WARNING] PARTIAL READINESS: Most controllers functional')
    else:
        print('[CRITICAL] NOT PRODUCTION READY: Significant controller failures')

    # Reset Interface Specific Summary
    reset_working = validation_results['critical_tests']['reset_method_coverage']
    print(f'\nRESET INTERFACE VALIDATION: {reset_working}/4 controllers ({(reset_working/4)*100:.0f}%)')

    # Save results
    output_file = 'controller_factory_validation_final.json'
    with open(output_file, 'w') as f:
        json.dump(validation_results, f, indent=2)

    print(f'\nValidation results saved to: {output_file}')

    return validation_results

if __name__ == "__main__":
    run_controller_validation()