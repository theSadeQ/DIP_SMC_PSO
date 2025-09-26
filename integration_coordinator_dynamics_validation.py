#==========================================================================================\\\
#=================== integration_coordinator_dynamics_validation.py ====================\\\
#==========================================================================================\\\
"""
Integration Coordinator - Dynamics Models Deep Validation
Tests all 3 dynamics models with empty config instantiation to resolve integration failures.
"""

import sys
import os
import json
import traceback
import numpy as np
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_dynamics_models_comprehensive():
    """Execute comprehensive Dynamics Models test for all 3 model types."""

    results = {
        'timestamp': datetime.now().isoformat(),
        'test_name': 'Dynamics Models Deep Validation',
        'validation_matrix': {},
        'dynamics_tests': {},
        'summary': {
            'total_models': 3,
            'functional_models': 0,
            'success_rate': 0.0,
            'critical_issues': []
        }
    }

    # Test the three main dynamics models
    dynamics_types = [
        {'name': 'SimplifiedDIPDynamics', 'module': 'src.plant.models.simplified.dynamics', 'config_required': True},
        {'name': 'FullDIPDynamics', 'module': 'src.plant.models.full.dynamics', 'config_required': True},
        {'name': 'LowRankDIPDynamics', 'module': 'src.plant.models.lowrank.dynamics', 'config_required': True}
    ]

    print("=== INTEGRATION COORDINATOR: Dynamics Models Deep Validation ===")
    print(f"Testing {len(dynamics_types)} dynamics model types...")

    # Test state for dynamics computation
    test_state = np.array([0.1, 0.0, 0.2, 0.0, 0.0, 0.0])  # 6-element state for DIP
    test_control = 0.5  # Test control input

    for dynamics_info in dynamics_types:
        model_name = dynamics_info['name']
        module_path = dynamics_info['module']

        print(f"\n--- Testing {model_name} ---")

        dynamics_result = {
            'name': model_name,
            'module': module_path,
            'import_success': False,
            'empty_config_instantiation': False,
            'with_config_instantiation': False,
            'compute_derivatives_success': False,
            'error_messages': [],
            'warnings': []
        }

        try:
            # Test 1: Import the dynamics model
            try:
                module = __import__(module_path, fromlist=[model_name])
                dynamics_class = getattr(module, model_name)
                print(f"  + {model_name} import successful")
                dynamics_result['import_success'] = True

            except Exception as e:
                print(f"  X {model_name} import failed: {e}")
                dynamics_result['error_messages'].append(f"Import failed: {e}")
                dynamics_result['import_success'] = False
                results['dynamics_tests'][model_name] = dynamics_result
                continue

            # Test 2: Empty config instantiation (main issue from prompt)
            try:
                # Try instantiation with no arguments (empty config)
                dynamics_empty = dynamics_class()
                print(f"  + {model_name} empty config instantiation successful")
                dynamics_result['empty_config_instantiation'] = True

                # Test computation with empty config model
                try:
                    derivatives = dynamics_empty.compute_derivatives(test_state, test_control)
                    print(f"  + {model_name} compute_derivatives with empty config successful")
                    dynamics_result['compute_derivatives_success'] = True
                except Exception as e:
                    print(f"  - {model_name} compute_derivatives with empty config failed: {e}")
                    dynamics_result['warnings'].append(f"Compute derivatives (empty): {e}")

            except Exception as e:
                print(f"  X {model_name} empty config instantiation failed: {e}")
                dynamics_result['error_messages'].append(f"Empty config instantiation: {e}")

            # Test 3: With default configuration
            try:
                # Create minimal default physics configuration
                default_config = {
                    'm1': 1.0, 'm2': 1.0,  # masses
                    'l1': 1.0, 'l2': 1.0,  # lengths
                    'J1': 0.083, 'J2': 0.083,  # inertias
                    'g': 9.81,  # gravity
                    'd1': 0.1, 'd2': 0.1,  # damping
                    'c1': 0.1, 'c2': 0.1   # friction (if needed)
                }

                dynamics_with_config = dynamics_class(default_config)
                print(f"  + {model_name} with config instantiation successful")
                dynamics_result['with_config_instantiation'] = True

                # Test computation with configured model
                try:
                    derivatives = dynamics_with_config.compute_derivatives(test_state, test_control)
                    print(f"  + {model_name} compute_derivatives with config successful")
                    print(f"    Derivatives shape: {np.array(derivatives).shape}")

                    # Validate derivatives are reasonable
                    derivatives_array = np.array(derivatives)
                    if derivatives_array.shape == (6,) and not np.any(np.isnan(derivatives_array)):
                        print(f"  + {model_name} derivatives validation passed")
                        dynamics_result['derivatives_valid'] = True
                    else:
                        print(f"  - {model_name} derivatives validation failed: shape or NaN issues")
                        dynamics_result['warnings'].append("Derivatives shape or NaN issues")

                except Exception as e:
                    print(f"  X {model_name} compute_derivatives with config failed: {e}")
                    dynamics_result['error_messages'].append(f"Compute derivatives (config): {e}")

            except Exception as e:
                print(f"  X {model_name} with config instantiation failed: {e}")
                dynamics_result['error_messages'].append(f"With config instantiation: {e}")

        except Exception as e:
            print(f"  X Unexpected error in {model_name}: {e}")
            dynamics_result['error_messages'].append(f"Unexpected error: {e}")

        # Store results
        results['dynamics_tests'][model_name] = dynamics_result

        # Count functional models (at least import + one instantiation method works)
        if (dynamics_result['import_success'] and
            (dynamics_result['empty_config_instantiation'] or dynamics_result['with_config_instantiation'])):
            results['summary']['functional_models'] += 1
            print(f"  + {model_name}: FUNCTIONAL")
        else:
            results['summary']['critical_issues'].append(f"{model_name}: Not functional")
            print(f"  X {model_name}: ISSUES DETECTED")

    # Calculate validation matrix scores
    results['validation_matrix']['dynamics_3_of_3'] = results['summary']['functional_models'] == 3
    results['validation_matrix']['dynamics_2_of_3'] = results['summary']['functional_models'] >= 2
    results['validation_matrix']['empty_config_working'] = any(
        model.get('empty_config_instantiation', False)
        for model in results['dynamics_tests'].values()
    )

    # Calculate success rate
    results['summary']['success_rate'] = results['summary']['functional_models'] / results['summary']['total_models']

    # Overall assessment
    print(f"\n=== DYNAMICS MODELS TEST SUMMARY ===")
    print(f"Functional Models: {results['summary']['functional_models']}/3")
    print(f"Success Rate: {results['summary']['success_rate']:.1%}")

    if results['summary']['functional_models'] == 3:
        print("+ ALL DYNAMICS MODELS FUNCTIONAL - VALIDATION PASSED")
        results['validation_matrix']['overall_status'] = 'PASSED'
    elif results['summary']['functional_models'] >= 2:
        print("! MOST DYNAMICS MODELS FUNCTIONAL - VALIDATION PARTIALLY PASSED")
        results['validation_matrix']['overall_status'] = 'PARTIAL'
    else:
        print("X MULTIPLE DYNAMICS MODEL FAILURES - VALIDATION FAILED")
        results['validation_matrix']['overall_status'] = 'FAILED'

    return results


def test_legacy_dynamics_imports():
    """Test legacy dynamics import paths that might be used in integration tests."""

    print("\n=== LEGACY DYNAMICS IMPORT TEST ===")

    legacy_import_results = {
        'timestamp': datetime.now().isoformat(),
        'test_name': 'Legacy Dynamics Import Test',
        'imports_tested': 0,
        'imports_successful': 0,
        'legacy_paths': {}
    }

    # Test various import paths that integration tests might use
    legacy_import_paths = [
        ('Core Dynamics', 'src.core.dynamics', 'DIPDynamics'),
        ('Simplified Direct', 'src.plant.models.simplified.dynamics', 'SimplifiedDIPDynamics'),
        ('Full Direct', 'src.plant.models.full.dynamics', 'FullDIPDynamics'),
        ('LowRank Direct', 'src.plant.models.lowrank.dynamics', 'LowRankDIPDynamics'),
        ('Plant Core', 'src.plant.core', 'DIPDynamics'),
        ('Legacy Core', 'src.core.dynamics', 'DoubleInvertedPendulum'),
    ]

    for name, module_path, class_name in legacy_import_paths:
        legacy_import_results['imports_tested'] += 1

        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"  + {name}: {module_path}.{class_name}")
            legacy_import_results['imports_successful'] += 1
            legacy_import_results['legacy_paths'][name] = {
                'status': 'success',
                'module': module_path,
                'class': class_name
            }

        except Exception as e:
            print(f"  X {name}: {module_path}.{class_name} - {e}")
            legacy_import_results['legacy_paths'][name] = {
                'status': 'failed',
                'module': module_path,
                'class': class_name,
                'error': str(e)
            }

    legacy_import_results['success_rate'] = legacy_import_results['imports_successful'] / legacy_import_results['imports_tested']

    print(f"\nLegacy Import Resolution: {legacy_import_results['imports_successful']}/{legacy_import_results['imports_tested']} ({legacy_import_results['success_rate']:.1%})")

    return legacy_import_results


def main():
    """Main test execution function."""

    print("Integration Coordinator - Dynamics Models Deep Validation")
    print("=" * 80)

    # Execute tests
    dynamics_results = test_dynamics_models_comprehensive()
    legacy_results = test_legacy_dynamics_imports()

    # Combine results
    combined_results = {
        'validation_timestamp': datetime.now().isoformat(),
        'validation_type': 'Integration Coordinator Dynamics Models Deep Validation',
        'dynamics_models_test': dynamics_results,
        'legacy_imports_test': legacy_results,
        'overall_assessment': {
            'dynamics_models_passed': dynamics_results['validation_matrix']['overall_status'] in ['PASSED', 'PARTIAL'],
            'empty_config_issue_resolved': dynamics_results['validation_matrix']['empty_config_working'],
            'legacy_imports_working': legacy_results['success_rate'] > 0.5,
            'critical_issues': dynamics_results['summary']['critical_issues']
        }
    }

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"integration_coordinator_dynamics_validation_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump(combined_results, f, indent=2)

    print(f"\n+ Results saved to: {results_file}")

    return combined_results


if __name__ == "__main__":
    try:
        results = main()

        # Exit with appropriate code
        if (results['overall_assessment']['dynamics_models_passed'] and
            results['overall_assessment']['legacy_imports_working']):
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(2)  # Critical error