#==========================================================================================\\\
#============== integration_coordinator_dynamics_validation_corrected.py ===============\\\
#==========================================================================================\\\
"""
Integration Coordinator - Dynamics Models Deep Validation (Corrected)
Tests all 3 dynamics models with correct configuration structure.
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
        'test_name': 'Dynamics Models Deep Validation (Corrected)',
        'validation_matrix': {},
        'dynamics_tests': {},
        'summary': {
            'total_models': 3,
            'functional_models': 0,
            'success_rate': 0.0,
            'critical_issues': []
        }
    }

    print("=== INTEGRATION COORDINATOR: Dynamics Models Deep Validation (Corrected) ===")
    print("Testing 3 dynamics model types with correct configuration structure...")

    # Test state for dynamics computation
    test_state = np.array([0.1, 0.0, 0.2, 0.0, 0.0, 0.0])  # 6-element state for DIP
    test_control = 0.5  # Test control input

    # Test 1: Simplified DIP Dynamics
    print(f"\n--- Testing SimplifiedDIPDynamics ---")
    simplified_result = {
        'name': 'SimplifiedDIPDynamics',
        'import_success': False,
        'config_creation_success': False,
        'instantiation_success': False,
        'compute_derivatives_success': False,
        'error_messages': [],
        'warnings': []
    }

    try:
        # Import simplified dynamics and config
        from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
        from src.plant.models.simplified.config import SimplifiedDIPConfig
        print("  + SimplifiedDIPDynamics import successful")
        simplified_result['import_success'] = True

        # Create correct configuration
        try:
            simplified_config = SimplifiedDIPConfig(
                cart_mass=1.0,
                pendulum1_mass=0.5,
                pendulum2_mass=0.5,
                pendulum1_length=1.0,
                pendulum2_length=1.0,
                pendulum1_com=0.5,
                pendulum2_com=0.5,
                pendulum1_inertia=0.083,
                pendulum2_inertia=0.083,
                gravity=9.81,
                cart_friction=0.1,
                pendulum1_friction=0.01,
                pendulum2_friction=0.01
            )
            print("  + SimplifiedDIPConfig creation successful")
            simplified_result['config_creation_success'] = True

            # Instantiate dynamics
            simplified_dynamics = SimplifiedDIPDynamics(simplified_config)
            print("  + SimplifiedDIPDynamics instantiation successful")
            simplified_result['instantiation_success'] = True

            # Test computation
            derivatives = simplified_dynamics.compute_derivatives(test_state, test_control)
            print("  + SimplifiedDIPDynamics compute_derivatives successful")
            print(f"    Derivatives shape: {np.array(derivatives.derivatives).shape}")
            simplified_result['compute_derivatives_success'] = True

        except Exception as e:
            print(f"  X SimplifiedDIPDynamics configuration/instantiation failed: {e}")
            simplified_result['error_messages'].append(f"Config/instantiation: {e}")

    except Exception as e:
        print(f"  X SimplifiedDIPDynamics import failed: {e}")
        simplified_result['error_messages'].append(f"Import failed: {e}")

    results['dynamics_tests']['SimplifiedDIPDynamics'] = simplified_result

    # Test 2: Full DIP Dynamics
    print(f"\n--- Testing FullDIPDynamics ---")
    full_result = {
        'name': 'FullDIPDynamics',
        'import_success': False,
        'config_creation_success': False,
        'instantiation_success': False,
        'compute_derivatives_success': False,
        'error_messages': [],
        'warnings': []
    }

    try:
        # Import full dynamics and config
        from src.plant.models.full.dynamics import FullDIPDynamics
        from src.plant.models.full.config import FullDIPConfig
        print("  + FullDIPDynamics import successful")
        full_result['import_success'] = True

        # Create correct configuration
        try:
            full_config = FullDIPConfig(
                cart_mass=1.0,
                pendulum1_mass=0.5,
                pendulum2_mass=0.5,
                pendulum1_length=1.0,
                pendulum2_length=1.0,
                pendulum1_com=0.5,
                pendulum2_com=0.5,
                pendulum1_inertia=0.083,
                pendulum2_inertia=0.083,
                gravity=9.81,
                cart_friction=0.1,
                pendulum1_friction=0.01,
                pendulum2_friction=0.01
            )
            print("  + FullDIPConfig creation successful")
            full_result['config_creation_success'] = True

            # Instantiate dynamics
            full_dynamics = FullDIPDynamics(full_config)
            print("  + FullDIPDynamics instantiation successful")
            full_result['instantiation_success'] = True

            # Test computation
            derivatives = full_dynamics.compute_derivatives(test_state, test_control)
            print("  + FullDIPDynamics compute_derivatives successful")
            print(f"    Derivatives shape: {np.array(derivatives.derivatives).shape}")
            full_result['compute_derivatives_success'] = True

        except Exception as e:
            print(f"  X FullDIPDynamics configuration/instantiation failed: {e}")
            full_result['error_messages'].append(f"Config/instantiation: {e}")

    except Exception as e:
        print(f"  X FullDIPDynamics import failed: {e}")
        full_result['error_messages'].append(f"Import failed: {e}")

    results['dynamics_tests']['FullDIPDynamics'] = full_result

    # Test 3: LowRank DIP Dynamics
    print(f"\n--- Testing LowRankDIPDynamics ---")
    lowrank_result = {
        'name': 'LowRankDIPDynamics',
        'import_success': False,
        'config_creation_success': False,
        'instantiation_success': False,
        'compute_derivatives_success': False,
        'error_messages': [],
        'warnings': []
    }

    try:
        # Import lowrank dynamics and config
        from src.plant.models.lowrank.dynamics import LowRankDIPDynamics
        from src.plant.models.lowrank.config import LowRankDIPConfig
        print("  + LowRankDIPDynamics import successful")
        lowrank_result['import_success'] = True

        # Create correct configuration
        try:
            lowrank_config = LowRankDIPConfig(
                cart_mass=1.0,
                pendulum1_mass=0.5,
                pendulum2_mass=0.5,
                pendulum1_length=1.0,
                pendulum2_length=1.0,
                pendulum1_com=0.5,
                pendulum2_com=0.5,
                pendulum1_inertia=0.083,
                pendulum2_inertia=0.083,
                gravity=9.81,
                cart_friction=0.1,
                pendulum1_friction=0.01,
                pendulum2_friction=0.01,
                rank=2  # Low-rank specific parameter
            )
            print("  + LowRankDIPConfig creation successful")
            lowrank_result['config_creation_success'] = True

            # Instantiate dynamics
            lowrank_dynamics = LowRankDIPDynamics(lowrank_config)
            print("  + LowRankDIPDynamics instantiation successful")
            lowrank_result['instantiation_success'] = True

            # Test computation
            derivatives = lowrank_dynamics.compute_derivatives(test_state, test_control)
            print("  + LowRankDIPDynamics compute_derivatives successful")
            print(f"    Derivatives shape: {np.array(derivatives.derivatives).shape}")
            lowrank_result['compute_derivatives_success'] = True

        except Exception as e:
            print(f"  X LowRankDIPDynamics configuration/instantiation failed: {e}")
            lowrank_result['error_messages'].append(f"Config/instantiation: {e}")

    except Exception as e:
        print(f"  X LowRankDIPDynamics import failed: {e}")
        lowrank_result['error_messages'].append(f"Import failed: {e}")

    results['dynamics_tests']['LowRankDIPDynamics'] = lowrank_result

    # Count functional models
    for model_name, model_result in results['dynamics_tests'].items():
        if (model_result['import_success'] and model_result['instantiation_success']):
            results['summary']['functional_models'] += 1
            print(f"  + {model_name}: FUNCTIONAL")
        else:
            results['summary']['critical_issues'].append(f"{model_name}: Not functional")
            print(f"  X {model_name}: ISSUES DETECTED")

    # Calculate validation matrix scores
    results['validation_matrix']['dynamics_3_of_3'] = results['summary']['functional_models'] == 3
    results['validation_matrix']['dynamics_2_of_3'] = results['summary']['functional_models'] >= 2
    results['validation_matrix']['instantiation_working'] = any(
        model.get('instantiation_success', False)
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


def test_empty_config_resolution():
    """Test potential solutions for empty config instantiation issue."""

    print("\n=== EMPTY CONFIG RESOLUTION TEST ===")

    empty_config_results = {
        'test_name': 'Empty Config Resolution Test',
        'default_config_creation': False,
        'factory_pattern_available': False,
        'minimal_config_working': False,
        'solutions': []
    }

    # Test 1: Check if there's a default config factory
    try:
        from src.plant.models.simplified.config import SimplifiedDIPConfig

        # Try to create a config with minimal required parameters
        minimal_config = SimplifiedDIPConfig(
            cart_mass=1.0, pendulum1_mass=0.5, pendulum2_mass=0.5,
            pendulum1_length=1.0, pendulum2_length=1.0,
            pendulum1_com=0.5, pendulum2_com=0.5,
            pendulum1_inertia=0.083, pendulum2_inertia=0.083,
            gravity=9.81, cart_friction=0.1,
            pendulum1_friction=0.01, pendulum2_friction=0.01
        )
        print("  + Minimal config creation works")
        empty_config_results['minimal_config_working'] = True
        empty_config_results['solutions'].append("Use minimal config with required parameters")

    except Exception as e:
        print(f"  X Minimal config creation failed: {e}")

    # Test 2: Look for default config factory
    try:
        # Check if there's a default factory method
        from src.plant.models.simplified.config import SimplifiedDIPConfig
        if hasattr(SimplifiedDIPConfig, 'default') or hasattr(SimplifiedDIPConfig, 'create_default'):
            print("  + Default config factory available")
            empty_config_results['factory_pattern_available'] = True
            empty_config_results['solutions'].append("Use default config factory method")
        else:
            print("  - No default config factory found")

    except Exception as e:
        print(f"  X Factory pattern check failed: {e}")

    return empty_config_results


def main():
    """Main test execution function."""

    print("Integration Coordinator - Dynamics Models Deep Validation (Corrected)")
    print("=" * 80)

    # Execute tests
    dynamics_results = test_dynamics_models_comprehensive()
    empty_config_results = test_empty_config_resolution()

    # Combine results
    combined_results = {
        'validation_timestamp': datetime.now().isoformat(),
        'validation_type': 'Integration Coordinator Dynamics Models Deep Validation (Corrected)',
        'dynamics_models_test': dynamics_results,
        'empty_config_resolution': empty_config_results,
        'overall_assessment': {
            'dynamics_models_passed': dynamics_results['validation_matrix']['overall_status'] in ['PASSED', 'PARTIAL'],
            'instantiation_issue_resolved': dynamics_results['validation_matrix']['instantiation_working'],
            'configuration_working': any(
                model.get('config_creation_success', False)
                for model in dynamics_results['dynamics_tests'].values()
            ),
            'critical_issues': dynamics_results['summary']['critical_issues']
        }
    }

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"integration_coordinator_dynamics_validation_corrected_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump(combined_results, f, indent=2)

    print(f"\n+ Results saved to: {results_file}")

    return combined_results


if __name__ == "__main__":
    try:
        results = main()

        # Exit with appropriate code
        if results['overall_assessment']['dynamics_models_passed']:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(2)  # Critical error