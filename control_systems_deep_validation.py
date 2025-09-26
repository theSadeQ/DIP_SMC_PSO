#==========================================================================================\\\
#======================== control_systems_deep_validation.py =============================\\\
#==========================================================================================\\\

"""
Control Systems Specialist Deep Validation Script.

Comprehensive validation of controller factory functionality following
claimed 100% success from integration fixes.
"""

import sys
import traceback
import numpy as np
import json
from datetime import datetime
from src.controllers.factory import create_controller

def main():
    """Execute comprehensive controller validation."""
    print('=== CONTROL SYSTEMS SPECIALIST DEEP VALIDATION ===')
    print()

    # Test all controller types with comprehensive analysis
    controllers = ['classical_smc', 'sta_smc', 'adaptive_smc', 'hybrid_adaptive_sta_smc']

    # Default comprehensive config
    config = {
        'dt': 0.01,
        'max_force': 20.0,
        'boundary_layer': 0.1,
        'gains': [10.0, 5.0, 8.0, 3.0, 15.0, 2.0],
        'adaptation_rate': 1.0,
        'sta_gains': [1.0, 1.0],
        'switching_gain': 10.0
    }

    validation_results = {
        'timestamp': datetime.now().isoformat(),
        'mission_context': 'Independent verification of controller functionality',
        'primary_objectives': {
            'controller_factory_validation': 'all 4 controllers create and function',
            'hybrid_controller_dt_error_resolution': 'dt attribute error resolved',
            'reset_interface_implementation': 'target ≥3/4 controllers',
            'control_computation_verification': 'valid control outputs'
        },
        'controllers': {},
        'summary': {}
    }

    total_functional = 0
    total_reset_implemented = 0
    dt_attribute_errors = 0

    for ctrl_type in controllers:
        print(f'=== Testing {ctrl_type.upper()} ===')

        controller_result = {
            'creation_successful': False,
            'reset_interface_available': False,
            'control_computation_successful': False,
            'dt_attribute_accessible': False,
            'control_output_sample': None,
            'errors': [],
            'status': 'UNKNOWN'
        }

        try:
            # 1. Controller Creation Test
            controller = create_controller(ctrl_type, config)
            controller_result['creation_successful'] = True
            print(f'  [SUCCESS] Creation: SUCCESS')

            # 2. dt Attribute Check (especially for hybrid controller)
            if hasattr(controller, 'dt'):
                controller_result['dt_attribute_accessible'] = True
                print(f'  [SUCCESS] dt attribute: ACCESSIBLE ({controller.dt})')
            elif hasattr(controller, 'config') and hasattr(controller.config, 'dt'):
                controller_result['dt_attribute_accessible'] = True
                print(f'  [SUCCESS] dt attribute via config: ACCESSIBLE ({controller.config.dt})')
            else:
                print(f'  [WARNING] dt attribute: NOT DIRECTLY ACCESSIBLE')
                if ctrl_type == 'hybrid_adaptive_sta_smc':
                    dt_attribute_errors += 1

            # 3. Reset Interface Test
            if hasattr(controller, 'reset'):
                try:
                    controller.reset()
                    controller_result['reset_interface_available'] = True
                    total_reset_implemented += 1
                    print(f'  [SUCCESS] Reset interface: IMPLEMENTED AND FUNCTIONAL')
                except Exception as e:
                    controller_result['errors'].append(f'Reset method exists but failed: {e}')
                    print(f'  [ERROR] Reset interface: EXISTS BUT FAILED - {e}')
            else:
                print(f'  [WARNING] Reset interface: NOT IMPLEMENTED')

            # 4. Control Computation Test
            test_state = np.array([0.1, 0.0, 0.05, 0.0, 0.02, 0.0])
            control_output = controller.compute_control(test_state, np.array([0.0]), [])

            if control_output and 'u' in control_output:
                controller_result['control_computation_successful'] = True
                # Store a simplified version of the output
                controller_result['control_output_sample'] = {
                    'u': float(control_output['u']),
                    'controller_type': control_output.get('controller_type', 'unknown'),
                    'control_effort': float(control_output.get('control_effort', 0)),
                    'surface_magnitude': float(control_output.get('surface_magnitude', 0))
                }
                total_functional += 1
                print(f'  [SUCCESS] Control computation: SUCCESS (u={control_output.get("u", "N/A")})')

                # Extra info for hybrid controller
                if ctrl_type == 'hybrid_adaptive_sta_smc':
                    active_ctrl = control_output.get('active_controller', 'unknown')
                    print(f'  [INFO] Hybrid active controller: {active_ctrl}')
            else:
                controller_result['errors'].append(f'Control computation returned invalid result: {control_output}')
                print(f'  [ERROR] Control computation: FAILED')

            # Overall status determination
            if (controller_result['creation_successful'] and
                controller_result['control_computation_successful']):
                controller_result['status'] = 'FULLY FUNCTIONAL'
                print(f'  [PASS] {ctrl_type}: FULLY FUNCTIONAL')
            else:
                controller_result['status'] = 'PARTIALLY FUNCTIONAL'
                print(f'  [WARNING] {ctrl_type}: PARTIALLY FUNCTIONAL')

        except Exception as e:
            controller_result['errors'].append(str(e))
            controller_result['status'] = 'FAILED'
            print(f'  [FAIL] {ctrl_type}: FAILED - {e}')

            # Special check for hybrid controller dt error
            if ctrl_type == 'hybrid_adaptive_sta_smc' and "'dt'" in str(e):
                dt_attribute_errors += 1
                print(f'  [CRITICAL] dt attribute error still present in hybrid controller!')

        validation_results['controllers'][ctrl_type] = controller_result
        print()

    # Generate summary
    total_controllers = len(controllers)
    functional_percentage = (total_functional / total_controllers) * 100
    reset_percentage = (total_reset_implemented / total_controllers) * 100

    validation_results['summary'] = {
        'total_controllers_tested': total_controllers,
        'functional_controllers': total_functional,
        'functional_percentage': functional_percentage,
        'reset_interface_implemented': total_reset_implemented,
        'reset_percentage': reset_percentage,
        'dt_attribute_errors': dt_attribute_errors,
        'hybrid_controller_dt_resolved': dt_attribute_errors == 0,
        'acceptance_criteria_met': {
            'controllers_functional': functional_percentage >= 95,  # ≥95% (≥4/4)
            'reset_interface_coverage': reset_percentage >= 75,    # ≥75% (≥3/4)
            'hybrid_controller_operational': dt_attribute_errors == 0,
            'no_regressions': total_functional == total_controllers
        }
    }

    print('=== VALIDATION SUMMARY ===')
    print(f'Controller Creation: {total_functional}/{total_controllers} ({functional_percentage:.0f}%)')
    print(f'Reset Interface: {total_reset_implemented}/{total_controllers} ({reset_percentage:.0f}%)')
    print(f'Hybrid Controller dt Error: {"RESOLVED" if dt_attribute_errors == 0 else "STILL PRESENT"}')
    print()

    # Acceptance criteria evaluation
    criteria = validation_results['summary']['acceptance_criteria_met']
    print('=== ACCEPTANCE CRITERIA EVALUATION ===')
    for criterion, met in criteria.items():
        status = 'PASS' if met else 'FAIL'
        print(f'{criterion}: {status}')

    overall_pass = all(criteria.values())
    print(f'\nOVERALL STATUS: {"PASS" if overall_pass else "FAIL"}')

    # Save comprehensive results
    with open('control_systems_specialist_validation_2025_09_26.json', 'w') as f:
        json.dump(validation_results, f, indent=2)

    print(f'\nDetailed results saved to: control_systems_specialist_validation_2025_09_26.json')

    return overall_pass

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)