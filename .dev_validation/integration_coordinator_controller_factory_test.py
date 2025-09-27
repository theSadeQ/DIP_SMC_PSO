#==========================================================================================\\\
#================= integration_coordinator_controller_factory_test.py ==================\\\
#==========================================================================================\\\
"""
Integration Coordinator - Controller Factory Comprehensive Test
Validates all 4 controllers can be created and function properly.
"""

import sys
import os
import json
import traceback
from datetime import datetime
from typing import Dict, Any, List

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
        print("✓ Factory import successful")

        # Test available controllers listing
        available = list_available_controllers()
        print(f"✓ Available controllers: {available}")
        results['validation_matrix']['factory_import'] = True
        results['validation_matrix']['list_controllers'] = True

    except Exception as e:
        print(f"✗ Factory import failed: {e}")
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
                print(f"  ✓ Default gains retrieved: {default_gains}")
                controller_result['gains_retrieval_success'] = True
                controller_result['default_gains'] = default_gains
            except Exception as e:
                print(f"  ✗ Default gains failed: {e}")
                controller_result['error_messages'].append(f"Default gains: {e}")

            # Test 2: Create controller with default configuration
            try:
                controller = create_controller(controller_type)
                print(f"  ✓ Controller created successfully")
                controller_result['creation_success'] = True

                # Test 3: Verify controller has required methods
                if hasattr(controller, 'compute_control'):
                    print(f"  ✓ compute_control method exists")

                    # Test 4: Test control computation with minimal state
                    try:
                        control_output = controller.compute_control(test_state)
                        print(f"  ✓ Control computation successful: {control_output}")
                        controller_result['compute_control_success'] = True
                        controller_result['test_output'] = float(control_output) if hasattr(control_output, '__float__') else str(control_output)

                    except Exception as e:
                        print(f"  ✗ Control computation failed: {e}")
                        controller_result['error_messages'].append(f"Control computation: {e}")

                else:
                    print(f"  ✗ compute_control method missing")
                    controller_result['error_messages'].append("compute_control method missing")

            except Exception as e:
                print(f"  ✗ Controller creation failed: {e}")
                controller_result['error_messages'].append(f"Creation failed: {e}")
                controller_result['creation_success'] = False

        except Exception as e:
            print(f"  ✗ Unexpected error in {controller_type}: {e}")
            controller_result['error_messages'].append(f"Unexpected error: {e}")

        # Store results
        results['controller_tests'][controller_type] = controller_result

        # Count functional controllers
        if controller_result['creation_success'] and controller_result['compute_control_success']:
            results['summary']['functional_controllers'] += 1
            print(f"  ✓ {controller_type}: FULLY FUNCTIONAL")
        else:
            results['summary']['critical_issues'].append(f"{controller_type}: Not fully functional")
            print(f"  ✗ {controller_type}: ISSUES DETECTED")

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
        print("✓ ALL CONTROLLERS FUNCTIONAL - VALIDATION PASSED")
        results['validation_matrix']['overall_status'] = 'PASSED'
    elif results['summary']['functional_controllers'] >= 3:
        print("⚠ MOST CONTROLLERS FUNCTIONAL - VALIDATION PARTIALLY PASSED")
        results['validation_matrix']['overall_status'] = 'PARTIAL'
    else:
        print("✗ MULTIPLE CONTROLLER FAILURES - VALIDATION FAILED")
        results['validation_matrix']['overall_status'] = 'FAILED'

    return results


def test_import_resolution():
    """Test direct import resolution for controllers."""

    print("\n=== IMPORT RESOLUTION TEST ===")

    import_results = {
        'timestamp': datetime.now().isoformat(),
        'test_name': 'Import Resolution Test',
        'imports_tested': 0,
        'imports_successful': 0,
        'import_details': {},
        'critical_imports': []
    }

    # Test critical imports
    test_imports = [
        ('Factory', 'src.controllers.factory', 'create_controller'),
        ('Classical SMC', 'src.controllers.smc.algorithms.classical.controller', 'ModularClassicalSMC'),
        ('STA SMC', 'src.controllers.smc.algorithms.super_twisting.controller', 'ModularSuperTwistingSMC'),
        ('Adaptive SMC', 'src.controllers.smc.algorithms.adaptive.controller', 'ModularAdaptiveSMC'),
        ('Hybrid SMC', 'src.controllers.smc.algorithms.hybrid.controller', 'ModularHybridSMC'),
        ('Dynamics Core', 'src.core.dynamics', 'DIPDynamics'),
        ('Hybrid Config', 'src.controllers.smc.algorithms.hybrid.config', 'HybridMode'),
        ('Classical Config', 'src.controllers.smc.algorithms.classical.config', 'ClassicalSMCConfig'),
    ]

    for name, module_path, class_name in test_imports:
        import_results['imports_tested'] += 1

        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"  ✓ {name}: {module_path}.{class_name}")
            import_results['imports_successful'] += 1
            import_results['import_details'][name] = {
                'status': 'success',
                'module': module_path,
                'class': class_name
            }

        except Exception as e:
            print(f"  ✗ {name}: {module_path}.{class_name} - {e}")
            import_results['import_details'][name] = {
                'status': 'failed',
                'module': module_path,
                'class': class_name,
                'error': str(e)
            }
            import_results['critical_imports'].append(f"{name}: {e}")

    import_results['success_rate'] = import_results['imports_successful'] / import_results['imports_tested']

    print(f"\nImport Resolution: {import_results['imports_successful']}/{import_results['imports_tested']} ({import_results['success_rate']:.1%})")

    return import_results


def main():
    """Main test execution function."""

    print("Integration Coordinator - Controller Factory Comprehensive Validation")
    print("=" * 80)

    # Execute tests
    controller_results = test_controller_factory_comprehensive()
    import_results = test_import_resolution()

    # Combine results
    combined_results = {
        'validation_timestamp': datetime.now().isoformat(),
        'validation_type': 'Integration Coordinator Controller Factory Test',
        'controller_factory_test': controller_results,
        'import_resolution_test': import_results,
        'overall_assessment': {
            'controller_factory_passed': controller_results['validation_matrix']['overall_status'] == 'PASSED',
            'import_resolution_passed': import_results['success_rate'] > 0.8,
            'critical_issues': controller_results['summary']['critical_issues'] + import_results['critical_imports']
        }
    }

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"integration_coordinator_controller_factory_validation_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump(combined_results, f, indent=2)

    print(f"\n✓ Results saved to: {results_file}")

    return combined_results


if __name__ == "__main__":
    try:
        results = main()

        # Exit with appropriate code
        if (results['overall_assessment']['controller_factory_passed'] and
            results['overall_assessment']['import_resolution_passed']):
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(2)  # Critical error