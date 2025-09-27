#==========================================================================================\\\
#================== integration_coordinator_config_health_check.py =====================\\\
#==========================================================================================\\\
"""
Integration Coordinator - Configuration System Health Check
Checks for degraded mode warnings and schema validation errors.
"""

import sys
import os
import json
import traceback
import warnings
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_configuration_system_health():
    """Execute comprehensive Configuration System Health Check."""

    results = {
        'timestamp': datetime.now().isoformat(),
        'test_name': 'Configuration System Health Check',
        'validation_matrix': {},
        'config_tests': {},
        'summary': {
            'total_config_tests': 0,
            'passed_config_tests': 0,
            'degraded_mode_warnings': [],
            'schema_validation_errors': [],
            'critical_issues': []
        }
    }

    print("=== INTEGRATION COORDINATOR: Configuration System Health Check ===")
    print("Checking for degraded mode warnings and schema validation errors...")

    # Test 1: Main config.yaml loading
    print(f"\n--- Testing Main config.yaml Loading ---")
    config_loading_result = {
        'test_name': 'Main Config Loading',
        'success': False,
        'degraded_mode': False,
        'schema_errors': [],
        'warnings': [],
        'error_messages': []
    }
    results['summary']['total_config_tests'] += 1

    try:
        # Capture warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Try to load the main configuration
            try:
                from src.config import load_config
                config = load_config("config.yaml", allow_unknown=False)
                print("  + Main config.yaml loaded successfully")
                config_loading_result['success'] = True

                # Check for any warnings that might indicate degraded mode
                if w:
                    for warning in w:
                        warning_msg = str(warning.message)
                        print(f"  ! Warning: {warning_msg}")
                        config_loading_result['warnings'].append(warning_msg)

                        if 'degraded' in warning_msg.lower() or 'fallback' in warning_msg.lower():
                            config_loading_result['degraded_mode'] = True
                            results['summary']['degraded_mode_warnings'].append(warning_msg)

                # Test with strict validation (allow_unknown=False)
                print("  + Strict validation (allow_unknown=False) passed")

            except Exception as e:
                print(f"  X Main config loading failed: {e}")
                config_loading_result['error_messages'].append(f"Config loading failed: {e}")

                # Check if it's a schema validation error
                if 'schema' in str(e).lower() or 'validation' in str(e).lower():
                    results['summary']['schema_validation_errors'].append(str(e))

                # Try fallback with allow_unknown=True
                try:
                    config = load_config("config.yaml", allow_unknown=True)
                    print("  ! Fallback with allow_unknown=True succeeded - DEGRADED MODE")
                    config_loading_result['degraded_mode'] = True
                    config_loading_result['success'] = True
                    results['summary']['degraded_mode_warnings'].append("Main config requires allow_unknown=True")

                except Exception as e2:
                    print(f"  X Even fallback config loading failed: {e2}")
                    config_loading_result['error_messages'].append(f"Fallback loading failed: {e2}")

    except Exception as e:
        print(f"  X Configuration system import failed: {e}")
        config_loading_result['error_messages'].append(f"Import failed: {e}")

    results['config_tests']['main_config_loading'] = config_loading_result
    if config_loading_result['success']:
        results['summary']['passed_config_tests'] += 1

    # Test 2: Controller configurations validation
    print(f"\n--- Testing Controller Configurations ---")
    controller_config_result = {
        'test_name': 'Controller Config Validation',
        'success': False,
        'controller_configs_valid': {},
        'schema_errors': [],
        'warnings': [],
        'error_messages': []
    }
    results['summary']['total_config_tests'] += 1

    controller_types = ['classical_smc', 'sta_smc', 'adaptive_smc', 'hybrid_adaptive_sta_smc']

    try:
        # Test controller-specific configuration validation
        if config_loading_result['success']:
            from src.config import load_config
            config = load_config("config.yaml", allow_unknown=config_loading_result['degraded_mode'])

            for controller_type in controller_types:
                try:
                    if hasattr(config, 'controllers') and controller_type in config.controllers:
                        controller_config = config.controllers[controller_type]
                        print(f"  + {controller_type} config found and accessible")
                        controller_config_result['controller_configs_valid'][controller_type] = True
                    else:
                        print(f"  - {controller_type} config not found in main config")
                        controller_config_result['controller_configs_valid'][controller_type] = False

                except Exception as e:
                    print(f"  X {controller_type} config validation failed: {e}")
                    controller_config_result['controller_configs_valid'][controller_type] = False
                    controller_config_result['error_messages'].append(f"{controller_type}: {e}")

            # Overall controller config success
            valid_controllers = sum(controller_config_result['controller_configs_valid'].values())
            total_controllers = len(controller_types)
            controller_config_result['success'] = valid_controllers > 0

            print(f"  Controller configs valid: {valid_controllers}/{total_controllers}")

        else:
            print("  X Skipping controller config tests due to main config failure")
            controller_config_result['error_messages'].append("Main config loading failed")

    except Exception as e:
        print(f"  X Controller configuration testing failed: {e}")
        controller_config_result['error_messages'].append(f"Controller config test failed: {e}")

    results['config_tests']['controller_configs'] = controller_config_result
    if controller_config_result['success']:
        results['summary']['passed_config_tests'] += 1

    # Test 3: Physics parameters validation
    print(f"\n--- Testing Physics Parameters Validation ---")
    physics_config_result = {
        'test_name': 'Physics Config Validation',
        'success': False,
        'physics_params_valid': False,
        'schema_errors': [],
        'warnings': [],
        'error_messages': []
    }
    results['summary']['total_config_tests'] += 1

    try:
        if config_loading_result['success']:
            from src.config import load_config
            config = load_config("config.yaml", allow_unknown=config_loading_result['degraded_mode'])

            # Check for physics parameters
            if hasattr(config, 'physics'):
                physics_params = config.physics
                print("  + Physics parameters found in config")

                # Check for required physics parameters
                required_physics = ['cart_mass', 'pendulum1_mass', 'pendulum2_mass',
                                   'pendulum1_length', 'pendulum2_length']

                missing_params = []
                for param in required_physics:
                    if not hasattr(physics_params, param):
                        missing_params.append(param)

                if missing_params:
                    print(f"  - Missing physics parameters: {missing_params}")
                    physics_config_result['error_messages'].append(f"Missing physics parameters: {missing_params}")
                    physics_config_result['physics_params_valid'] = False
                else:
                    print("  + All required physics parameters present")
                    physics_config_result['physics_params_valid'] = True
                    physics_config_result['success'] = True

            elif hasattr(config, 'dip_params'):
                print("  + DIP parameters found in config (legacy format)")
                physics_config_result['physics_params_valid'] = True
                physics_config_result['success'] = True
            else:
                print("  X No physics/dip_params found in config")
                physics_config_result['error_messages'].append("No physics parameters found")

        else:
            print("  X Skipping physics config tests due to main config failure")
            physics_config_result['error_messages'].append("Main config loading failed")

    except Exception as e:
        print(f"  X Physics configuration testing failed: {e}")
        physics_config_result['error_messages'].append(f"Physics config test failed: {e}")

    results['config_tests']['physics_configs'] = physics_config_result
    if physics_config_result['success']:
        results['summary']['passed_config_tests'] += 1

    # Calculate validation matrix scores
    results['validation_matrix']['config_loading_works'] = config_loading_result['success']
    results['validation_matrix']['no_degraded_mode'] = not any([
        config_loading_result['degraded_mode'],
        len(results['summary']['degraded_mode_warnings']) == 0
    ])
    results['validation_matrix']['no_schema_errors'] = len(results['summary']['schema_validation_errors']) == 0
    results['validation_matrix']['controller_configs_valid'] = controller_config_result['success']
    results['validation_matrix']['physics_configs_valid'] = physics_config_result['success']

    # Calculate success rate
    results['summary']['success_rate'] = results['summary']['passed_config_tests'] / results['summary']['total_config_tests']

    # Overall assessment
    print(f"\n=== CONFIGURATION SYSTEM HEALTH SUMMARY ===")
    print(f"Passed Config Tests: {results['summary']['passed_config_tests']}/{results['summary']['total_config_tests']}")
    print(f"Success Rate: {results['summary']['success_rate']:.1%}")
    print(f"Degraded Mode Warnings: {len(results['summary']['degraded_mode_warnings'])}")
    print(f"Schema Validation Errors: {len(results['summary']['schema_validation_errors'])}")

    if results['summary']['success_rate'] == 1.0 and len(results['summary']['degraded_mode_warnings']) == 0:
        print("+ CONFIGURATION SYSTEM HEALTHY - VALIDATION PASSED")
        results['validation_matrix']['overall_status'] = 'HEALTHY'
    elif results['summary']['success_rate'] >= 0.67:
        print("! CONFIGURATION SYSTEM PARTIALLY HEALTHY - SOME ISSUES DETECTED")
        results['validation_matrix']['overall_status'] = 'PARTIAL'
    else:
        print("X CONFIGURATION SYSTEM UNHEALTHY - CRITICAL ISSUES DETECTED")
        results['validation_matrix']['overall_status'] = 'UNHEALTHY'

    return results


def main():
    """Main test execution function."""

    print("Integration Coordinator - Configuration System Health Check")
    print("=" * 80)

    # Execute tests
    config_results = test_configuration_system_health()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"integration_coordinator_config_health_check_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump(config_results, f, indent=2)

    print(f"\n+ Results saved to: {results_file}")

    return config_results


if __name__ == "__main__":
    try:
        results = main()

        # Exit with appropriate code
        if results['validation_matrix']['overall_status'] in ['HEALTHY', 'PARTIAL']:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(2)  # Critical error