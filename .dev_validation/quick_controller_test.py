#==========================================================================================\\\
#================================ quick_controller_test.py ==============================\\\
#==========================================================================================\\\

"""Quick controller validation test script for immediate execution."""

import sys
import os
import numpy as np
import json
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_controllers():
    """Test all controllers quickly."""
    results = {
        'timestamp': datetime.now().isoformat(),
        'controllers_working': 0,
        'controllers_tested': 0,
        'controllers_with_reset': 0,
        'hybrid_status': 'UNKNOWN',
        'control_computation_working': 0,
        'detailed_results': {}
    }

    print("=" * 60)
    print("QUICK CONTROLLER VALIDATION TEST")
    print("=" * 60)

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

    test_state = np.array([0.1, 0.0, 0.05, 0.0, 0.02, 0.0])

    for controller_type in test_controllers:
        results['controllers_tested'] += 1
        controller_result = {
            'creation_success': False,
            'has_reset': False,
            'reset_works': False,
            'compute_control_works': False,
            'control_output': None,
            'error': None
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

            # Test control computation
            if hasattr(controller, 'compute_control'):
                try:
                    control_output = controller.compute_control(test_state, 0.0)
                    controller_result['compute_control_works'] = True
                    controller_result['control_output'] = float(control_output) if np.isscalar(control_output) else str(control_output)
                    results['control_computation_working'] += 1
                    print(f"  [OK] Control computation: {control_output}")
                except Exception as e:
                    controller_result['error'] = str(e)
                    print(f"  [ERROR] Control computation failed: {e}")
            else:
                print(f"  [ERROR] No compute_control method")

            # Special check for hybrid controller
            if controller_type == 'hybrid_adaptive_sta_smc':
                if hasattr(controller, 'config') and hasattr(controller.config, 'dt'):
                    results['hybrid_status'] = 'FUNCTIONAL'
                    print(f"  [OK] Hybrid dt attribute accessible: {controller.config.dt}")
                else:
                    results['hybrid_status'] = 'FAILED'
                    print(f"  [ERROR] Hybrid dt attribute not accessible")

        except Exception as e:
            controller_result['error'] = str(e)
            print(f"  [ERROR] Creation failed: {e}")
            if controller_type == 'hybrid_adaptive_sta_smc':
                results['hybrid_status'] = 'FAILED'

        results['detailed_results'][controller_type] = controller_result

    # Summary
    print(f"\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Controllers working: {results['controllers_working']}/4 ({100 * results['controllers_working'] / 4:.0f}%)")
    print(f"Reset interfaces: {results['controllers_with_reset']}/4 ({100 * results['controllers_with_reset'] / 4:.0f}%)")
    print(f"Control computation: {results['control_computation_working']}/4 ({100 * results['control_computation_working'] / 4:.0f}%)")
    print(f"Hybrid controller status: {results['hybrid_status']}")

    # Score calculation
    validation_score = 0
    validation_score += 25  # Factory works
    validation_score += (results['controllers_working'] / 4) * 50  # Controllers work
    validation_score += (results['controllers_with_reset'] / 4) * 15  # Reset interfaces
    validation_score += (results['control_computation_working'] / 4) * 10  # Control computation

    if results['hybrid_status'] == 'FUNCTIONAL':
        validation_score += 10  # Hybrid controller fixed
        print(f"\n[SUCCESS] Hybrid controller is FUNCTIONAL (dt attribute issue resolved)")

    results['validation_score'] = validation_score
    grade = 'A' if validation_score >= 90 else 'B' if validation_score >= 80 else 'C' if validation_score >= 70 else 'F'

    print(f"\nVALIDATION SCORE: {validation_score:.1f}/100 (Grade: {grade})")

    return results

if __name__ == "__main__":
    results = test_controllers()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"controller_validation_{timestamp}.json"

    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to: {filename}")
    print(f"Final validation score: {results['validation_score']}/100")

    # Return appropriate exit code
    exit_code = 0 if results['validation_score'] >= 80 else 1
    sys.exit(exit_code)