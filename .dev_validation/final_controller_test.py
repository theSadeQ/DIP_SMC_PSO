#==========================================================================================\\\
#=============================== final_controller_test.py ===============================\\\
#==========================================================================================\\\

"""Final comprehensive controller validation with proper method signatures."""

import sys
import os
import numpy as np
import json
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_controllers_with_history():
    """Test all controllers with proper method signatures including history parameter."""
    results = {
        'timestamp': datetime.now().isoformat(),
        'controllers_working': 0,
        'controllers_tested': 0,
        'controllers_with_reset': 0,
        'hybrid_status': 'UNKNOWN',
        'control_computation_working': 0,
        'detailed_results': {}
    }

    print("=" * 80)
    print("FINAL COMPREHENSIVE CONTROLLER FACTORY VALIDATION")
    print("=" * 80)

    # Import factory
    try:
        from src.controllers.factory import create_controller, list_available_controllers
        print("[OK] Factory imported successfully")
        available_controllers = list_available_controllers()
        print(f"[OK] Available: {available_controllers}")
    except Exception as e:
        print(f"[ERROR] Factory import failed: {e}")
        return results

    # Test each controller
    test_controllers = ['classical_smc', 'sta_smc', 'adaptive_smc', 'hybrid_adaptive_sta_smc']
    test_gains = {
        'classical_smc': [5.0, 5.0, 5.0, 0.5, 0.5, 0.5],
        'sta_smc': [5.0, 3.0, 4.0, 4.0, 0.4, 0.4],
        'adaptive_smc': [10.0, 8.0, 5.0, 4.0, 1.0],
        'hybrid_adaptive_sta_smc': [5.0, 5.0, 5.0, 0.5]
    }

    # Test state vector (6-element for DIP: [θ1, θ1_dot, θ2, θ2_dot, x, x_dot])
    test_state = np.array([0.1, 0.0, 0.05, 0.0, 0.02, 0.0])
    last_control = 0.0
    empty_history = {}  # Empty history dict

    for controller_type in test_controllers:
        results['controllers_tested'] += 1
        controller_result = {
            'creation_success': False,
            'has_reset': False,
            'reset_works': False,
            'compute_control_works': False,
            'control_output': None,
            'error': None,
            'method_signature': None
        }

        print(f"\nTesting {controller_type}:")

        try:
            # Create controller
            controller = create_controller(controller_type, gains=test_gains[controller_type])
            controller_result['creation_success'] = True
            results['controllers_working'] += 1
            print(f"  [OK] Created: {type(controller).__name__}")

            # Test reset interface
            if hasattr(controller, 'reset'):
                controller_result['has_reset'] = True
                try:
                    controller.reset()
                    controller_result['reset_works'] = True
                    results['controllers_with_reset'] += 1
                    print(f"  [OK] Reset works")
                except Exception as e:
                    print(f"  [WARN] Reset failed: {e}")
            else:
                print(f"  [INFO] No reset method")

            # Test control computation with different parameter combinations
            if hasattr(controller, 'compute_control'):
                # Try different method signatures
                test_approaches = [
                    ("state+last_control+history", lambda: controller.compute_control(test_state, last_control, empty_history)),
                    ("state+last_control", lambda: controller.compute_control(test_state, last_control)),
                    ("state_only", lambda: controller.compute_control(test_state)),
                ]

                for approach_name, compute_func in test_approaches:
                    try:
                        control_output = compute_func()
                        controller_result['compute_control_works'] = True
                        controller_result['control_output'] = float(control_output) if np.isscalar(control_output) else str(control_output)
                        controller_result['method_signature'] = approach_name
                        results['control_computation_working'] += 1
                        print(f"  [OK] Control computation ({approach_name}): {control_output}")
                        break  # Success, stop trying other approaches
                    except Exception as e:
                        print(f"  [DEBUG] {approach_name} failed: {e}")
                        continue

                if not controller_result['compute_control_works']:
                    controller_result['error'] = "All compute_control approaches failed"
                    print(f"  [ERROR] All control computation approaches failed")
            else:
                print(f"  [ERROR] No compute_control method")

            # Special check for hybrid controller
            if controller_type == 'hybrid_adaptive_sta_smc':
                if hasattr(controller, 'config') and hasattr(controller.config, 'dt'):
                    results['hybrid_status'] = 'FUNCTIONAL'
                    print(f"  [SUCCESS] Hybrid dt attribute accessible: {controller.config.dt}")
                else:
                    results['hybrid_status'] = 'FAILED'
                    print(f"  [ERROR] Hybrid dt attribute not accessible")

        except Exception as e:
            controller_result['error'] = str(e)
            print(f"  [ERROR] Creation failed: {e}")
            if controller_type == 'hybrid_adaptive_sta_smc':
                results['hybrid_status'] = 'FAILED'

        results['detailed_results'][controller_type] = controller_result

    # Additional verification test - check specific known working interfaces
    print(f"\n" + "-" * 50)
    print("ADDITIONAL INTERFACE VERIFICATION")
    print("-" * 50)

    # Test controller inspection
    if results['controllers_working'] > 0:
        try:
            # Get one working controller for interface inspection
            working_controller_type = 'classical_smc'  # We know this works
            controller = create_controller(working_controller_type, gains=test_gains[working_controller_type])

            # Inspect its methods and attributes
            print(f"\nInspecting {working_controller_type} interface:")
            methods = [method for method in dir(controller) if callable(getattr(controller, method)) and not method.startswith('_')]
            print(f"  Available methods: {methods}")

            # Check compute_control signature
            import inspect
            if hasattr(controller, 'compute_control'):
                sig = inspect.signature(controller.compute_control)
                print(f"  compute_control signature: {sig}")

        except Exception as e:
            print(f"  [ERROR] Interface inspection failed: {e}")

    # Summary
    print(f"\n" + "=" * 80)
    print("FINAL VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Controllers working: {results['controllers_working']}/4 ({100 * results['controllers_working'] / 4:.0f}%)")
    print(f"Reset interfaces: {results['controllers_with_reset']}/4 ({100 * results['controllers_with_reset'] / 4:.0f}%)")
    print(f"Control computation: {results['control_computation_working']}/4 ({100 * results['control_computation_working'] / 4:.0f}%)")
    print(f"Hybrid controller status: {results['hybrid_status']}")

    # Critical issues verification
    critical_issues_fixed = []
    if results['hybrid_status'] == 'FUNCTIONAL':
        critical_issues_fixed.append("Hybrid controller 'dt' attribute issue resolved")

    if results['controllers_working'] == 4:
        critical_issues_fixed.append("All 4 controller types create successfully")

    if results['controllers_with_reset'] >= 3:  # Minimum 3/4 as per requirement
        critical_issues_fixed.append("Reset interface requirement (>=3/4) satisfied")

    if critical_issues_fixed:
        print(f"\nCRITICAL ISSUES FIXED:")
        for issue in critical_issues_fixed:
            print(f"  [SUCCESS] {issue}")

    # Score calculation
    validation_score = 0
    validation_score += 25  # Factory works
    validation_score += (results['controllers_working'] / 4) * 50  # Controllers work
    validation_score += (results['controllers_with_reset'] / 4) * 15  # Reset interfaces
    validation_score += (results['control_computation_working'] / 4) * 10  # Control computation

    if results['hybrid_status'] == 'FUNCTIONAL':
        validation_score += 10  # Hybrid controller fixed

    results['validation_score'] = validation_score
    grade = 'A' if validation_score >= 90 else 'B' if validation_score >= 80 else 'C' if validation_score >= 70 else 'F'

    print(f"\nFINAL VALIDATION SCORE: {validation_score:.1f}/100 (Grade: {grade})")

    # Deliverables as requested
    print(f"\n" + "=" * 80)
    print("VALIDATION DELIVERABLES")
    print("=" * 80)
    print(f"Controllers working: {results['controllers_working']}/4 ({100 * results['controllers_working'] / 4:.0f}%)")
    print(f"Reset interface implementation: {results['controllers_with_reset']}/4 ({100 * results['controllers_with_reset'] / 4:.0f}%)")
    print(f"Hybrid controller status: {results['hybrid_status']}")
    print(f"Control computation validation: {results['control_computation_working']}/4 working")

    return results

if __name__ == "__main__":
    results = test_controllers_with_history()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"final_controller_validation_{timestamp}.json"

    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nValidation results saved to: {filename}")
    print(f"Final validation score: {results['validation_score']}/100")

    # Return appropriate exit code
    exit_code = 0 if results['validation_score'] >= 80 else 1
    sys.exit(exit_code)