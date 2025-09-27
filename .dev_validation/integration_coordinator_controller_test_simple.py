#==========================================================================================\\\
#================== integration_coordinator_controller_test_simple.py ==================\\\
#==========================================================================================\\\
"""
Integration Coordinator - Controller Factory Comprehensive Test (Simple Version)
Validates all 4 controllers can be created and function properly.
"""

import sys
import os
import json
import traceback
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_controller_factory_comprehensive():
    """Execute comprehensive Controller Factory test for all 4 controllers."""

    results = {
        'timestamp': datetime.now().isoformat(),
        'test_name': 'Controller Factory Comprehensive Test',
        'validation_matrix': {},
        'controller_tests': {},
        'summary': {
            'total_controllers': 4,
            'functional_controllers': 0,
            'success_rate': 0.0,
            'critical_issues': []
        }
    }

    # Test data for controllers
    controller_types = ['classical_smc', 'sta_smc', 'adaptive_smc', 'hybrid_adaptive_sta_smc']
    test_state = [0.1, 0.0, 0.2, 0.0]  # Simple test state

    print("=== INTEGRATION COORDINATOR: Controller Factory Comprehensive Test ===")
    print(f"Testing {len(controller_types)} controller types...")

    try:
        # Import factory
        from src.controllers.factory import create_controller, list_available_controllers, get_default_gains
        print("+ Factory import successful")

        # Test available controllers listing
        available = list_available_controllers()
        print(f"+ Available controllers: {available}")
        results['validation_matrix']['factory_import'] = True
        results['validation_matrix']['list_controllers'] = True

    except Exception as e:
        print(f"X Factory import failed: {e}")
        results['validation_matrix']['factory_import'] = False
        results['validation_matrix']['list_controllers'] = False
        results['summary']['critical_issues'].append(f"Factory import failed: {e}")
        return results

    # Test each controller type
    for controller_type in controller_types:
        print(f"\n--- Testing {controller_type} ---")

        controller_result = {
            'type': controller_type,
            'creation_success': False,
            'compute_control_success': False,
            'gains_retrieval_success': False,
            'error_messages': [],
            'warnings': []
        }

        try:
            # Test 1: Get default gains
            try:
                default_gains = get_default_gains(controller_type)
                print(f"  + Default gains retrieved: {default_gains}")
                controller_result['gains_retrieval_success'] = True
                controller_result['default_gains'] = default_gains
            except Exception as e:
                print(f"  X Default gains failed: {e}")
                controller_result['error_messages'].append(f"Default gains: {e}")

            # Test 2: Create controller with default configuration
            try:
                controller = create_controller(controller_type)
                print(f"  + Controller created successfully")
                controller_result['creation_success'] = True

                # Test 3: Verify controller has required methods
                if hasattr(controller, 'compute_control'):
                    print(f"  + compute_control method exists")

                    # Test 4: Test control computation with minimal state
                    try:
                        control_output = controller.compute_control(test_state)
                        print(f"  + Control computation successful: {control_output}")
                        controller_result['compute_control_success'] = True
                        controller_result['test_output'] = float(control_output) if hasattr(control_output, '__float__') else str(control_output)

                    except Exception as e:
                        print(f"  X Control computation failed: {e}")
                        controller_result['error_messages'].append(f"Control computation: {e}")

                else:
                    print(f"  X compute_control method missing")
                    controller_result['error_messages'].append("compute_control method missing")

            except Exception as e:
                print(f"  X Controller creation failed: {e}")
                controller_result['error_messages'].append(f"Creation failed: {e}")
                controller_result['creation_success'] = False

        except Exception as e:
            print(f"  X Unexpected error in {controller_type}: {e}")
            controller_result['error_messages'].append(f"Unexpected error: {e}")

        # Store results
        results['controller_tests'][controller_type] = controller_result

        # Count functional controllers
        if controller_result['creation_success'] and controller_result['compute_control_success']:
            results['summary']['functional_controllers'] += 1
            print(f"  + {controller_type}: FULLY FUNCTIONAL")
        else:
            results['summary']['critical_issues'].append(f"{controller_type}: Not fully functional")
            print(f"  X {controller_type}: ISSUES DETECTED")

    # Calculate validation matrix scores
    results['validation_matrix']['controllers_4_of_4'] = results['summary']['functional_controllers'] == 4
    results['validation_matrix']['controllers_3_of_4'] = results['summary']['functional_controllers'] >= 3
    results['validation_matrix']['controllers_2_of_4'] = results['summary']['functional_controllers'] >= 2

    # Calculate success rate
    results['summary']['success_rate'] = results['summary']['functional_controllers'] / results['summary']['total_controllers']

    # Special focus on hybrid controller (mentioned in prompt)
    if 'hybrid_adaptive_sta_smc' in results['controller_tests']:
        hybrid_result = results['controller_tests']['hybrid_adaptive_sta_smc']
        results['validation_matrix']['hybrid_controller_functional'] = (
            hybrid_result['creation_success'] and hybrid_result['compute_control_success']
        )

    # Overall assessment
    print(f"\n=== CONTROLLER FACTORY TEST SUMMARY ===")
    print(f"Functional Controllers: {results['summary']['functional_controllers']}/4")
    print(f"Success Rate: {results['summary']['success_rate']:.1%}")

    if results['summary']['functional_controllers'] == 4:
        print("+ ALL CONTROLLERS FUNCTIONAL - VALIDATION PASSED")
        results['validation_matrix']['overall_status'] = 'PASSED'
    elif results['summary']['functional_controllers'] >= 3:
        print("! MOST CONTROLLERS FUNCTIONAL - VALIDATION PARTIALLY PASSED")
        results['validation_matrix']['overall_status'] = 'PARTIAL'
    else:
        print("X MULTIPLE CONTROLLER FAILURES - VALIDATION FAILED")
        results['validation_matrix']['overall_status'] = 'FAILED'

    return results


def main():
    """Main test execution function."""

    print("Integration Coordinator - Controller Factory Comprehensive Validation")
    print("=" * 80)

    # Execute tests
    controller_results = test_controller_factory_comprehensive()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"integration_coordinator_controller_factory_validation_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump(controller_results, f, indent=2)

    print(f"\n+ Results saved to: {results_file}")

    return controller_results


if __name__ == "__main__":
    try:
        results = main()

        # Exit with appropriate code
        if results['validation_matrix']['overall_status'] == 'PASSED':
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(2)  # Critical error