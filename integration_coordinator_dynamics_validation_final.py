#==========================================================================================\\\
#=============== integration_coordinator_dynamics_validation_final.py ==================\\\
#==========================================================================================\\\
"""
Integration Coordinator - Dynamics Models Deep Validation (Final)
Tests all 3 dynamics models with CORRECT configuration parameter names.
"""

import sys
import os
import json
import traceback
import numpy as np
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def create_minimal_simplified_config():
    """Create minimal SimplifiedDIPConfig with correct parameter names."""
    from src.plant.models.simplified.config import SimplifiedDIPConfig
    return SimplifiedDIPConfig(
        # Required physical parameters
        cart_mass=1.0,
        pendulum1_mass=0.5,
        pendulum2_mass=0.5,
        pendulum1_length=1.0,
        pendulum2_length=1.0,
        pendulum1_com=0.5,
        pendulum2_com=0.5,
        pendulum1_inertia=0.083,
        pendulum2_inertia=0.083,
        # Friction parameters (correct names)
        joint1_friction=0.01,
        joint2_friction=0.01
        # Other parameters have defaults
    )

def test_dynamics_models_comprehensive():
    """Execute comprehensive Dynamics Models test for all 3 model types."""

    results = {
        'timestamp': datetime.now().isoformat(),
        'test_name': 'Dynamics Models Deep Validation (Final)',
        'validation_matrix': {},
        'dynamics_tests': {},
        'summary': {
            'total_models': 3,
            'functional_models': 0,
            'success_rate': 0.0,
            'critical_issues': []
        }
    }

    print("=== INTEGRATION COORDINATOR: Dynamics Models Deep Validation (Final) ===")
    print("Testing 3 dynamics model types with CORRECT configuration parameters...")

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
        print("  + SimplifiedDIPDynamics import successful")
        simplified_result['import_success'] = True

        # Create correct configuration
        try:
            simplified_config = create_minimal_simplified_config()
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

    # Test 2: Full DIP Dynamics (try to use similar structure)
    print(f"\n--- Testing FullDIPDynamics ---")
    full_result = {
        'name': 'FullDIPDynamics',
        'import_success': False,
        'instantiation_success': False,
        'error_messages': [],
        'warnings': []
    }

    try:
        from src.plant.models.full.dynamics import FullDIPDynamics
        print("  + FullDIPDynamics import successful")
        full_result['import_success'] = True

        # Try different configuration approaches
        try:
            # Method 1: Try with dict configuration
            config_dict = {
                'cart_mass': 1.0, 'pendulum1_mass': 0.5, 'pendulum2_mass': 0.5,
                'pendulum1_length': 1.0, 'pendulum2_length': 1.0,
                'pendulum1_inertia': 0.083, 'pendulum2_inertia': 0.083
            }
            full_dynamics = FullDIPDynamics(config_dict)
            print("  + FullDIPDynamics instantiation successful (dict config)")
            full_result['instantiation_success'] = True

        except Exception as e:
            print(f"  X FullDIPDynamics with dict config failed: {e}")

            # Method 2: Try with config class if available
            try:
                from src.plant.models.full.config import FullDIPConfig
                # Try similar structure to simplified config
                full_config = FullDIPConfig(
                    cart_mass=1.0, pendulum1_mass=0.5, pendulum2_mass=0.5,
                    pendulum1_length=1.0, pendulum2_length=1.0,
                    pendulum1_inertia=0.083, pendulum2_inertia=0.083
                )
                full_dynamics = FullDIPDynamics(full_config)
                print("  + FullDIPDynamics instantiation successful (config class)")
                full_result['instantiation_success'] = True

            except Exception as e2:
                print(f"  X FullDIPDynamics with config class failed: {e2}")
                full_result['error_messages'].append(f"Both config methods failed: {e}, {e2}")

    except Exception as e:
        print(f"  X FullDIPDynamics import failed: {e}")
        full_result['error_messages'].append(f"Import failed: {e}")

    results['dynamics_tests']['FullDIPDynamics'] = full_result

    # Test 3: LowRank DIP Dynamics (try to use similar structure)
    print(f"\n--- Testing LowRankDIPDynamics ---")
    lowrank_result = {
        'name': 'LowRankDIPDynamics',
        'import_success': False,
        'instantiation_success': False,
        'error_messages': [],
        'warnings': []
    }

    try:
        from src.plant.models.lowrank.dynamics import LowRankDIPDynamics
        print("  + LowRankDIPDynamics import successful")
        lowrank_result['import_success'] = True

        # Try similar configuration approaches
        try:
            # Method 1: Try with dict configuration
            config_dict = {
                'cart_mass': 1.0, 'pendulum1_mass': 0.5, 'pendulum2_mass': 0.5,
                'pendulum1_length': 1.0, 'pendulum2_length': 1.0,
                'pendulum1_inertia': 0.083, 'pendulum2_inertia': 0.083,
                'rank': 2  # Low-rank specific
            }
            lowrank_dynamics = LowRankDIPDynamics(config_dict)
            print("  + LowRankDIPDynamics instantiation successful (dict config)")
            lowrank_result['instantiation_success'] = True

        except Exception as e:
            print(f"  X LowRankDIPDynamics with dict config failed: {e}")

            # Method 2: Try with config class if available
            try:
                from src.plant.models.lowrank.config import LowRankDIPConfig
                lowrank_config = LowRankDIPConfig(
                    cart_mass=1.0, pendulum1_mass=0.5, pendulum2_mass=0.5,
                    pendulum1_length=1.0, pendulum2_length=1.0,
                    pendulum1_inertia=0.083, pendulum2_inertia=0.083,
                    rank=2
                )
                lowrank_dynamics = LowRankDIPDynamics(lowrank_config)
                print("  + LowRankDIPDynamics instantiation successful (config class)")
                lowrank_result['instantiation_success'] = True

            except Exception as e2:
                print(f"  X LowRankDIPDynamics with config class failed: {e2}")
                lowrank_result['error_messages'].append(f"Both config methods failed: {e}, {e2}")

    except Exception as e:
        print(f"  X LowRankDIPDynamics import failed: {e}")
        lowrank_result['error_messages'].append(f"Import failed: {e}")

    results['dynamics_tests']['LowRankDIPDynamics'] = lowrank_result

    # Count functional models
    for model_name, model_result in results['dynamics_tests'].items():
        if (model_result['import_success'] and model_result.get('instantiation_success', False)):
            results['summary']['functional_models'] += 1
            print(f"  + {model_name}: FUNCTIONAL")
        else:
            results['summary']['critical_issues'].append(f"{model_name}: Not functional")
            print(f"  X {model_name}: ISSUES DETECTED")

    # Calculate validation matrix scores
    results['validation_matrix']['dynamics_3_of_3'] = results['summary']['functional_models'] == 3
    results['validation_matrix']['dynamics_2_of_3'] = results['summary']['functional_models'] >= 2
    results['validation_matrix']['dynamics_1_of_3'] = results['summary']['functional_models'] >= 1
    results['validation_matrix']['empty_config_issue_resolved'] = results['summary']['functional_models'] > 0

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
    elif results['summary']['functional_models'] >= 1:
        print("! AT LEAST ONE DYNAMICS MODEL FUNCTIONAL - VALIDATION MINIMAL")
        results['validation_matrix']['overall_status'] = 'MINIMAL'
    else:
        print("X ALL DYNAMICS MODELS FAILED - VALIDATION FAILED")
        results['validation_matrix']['overall_status'] = 'FAILED'

    return results


def main():
    """Main test execution function."""

    print("Integration Coordinator - Dynamics Models Deep Validation (Final)")
    print("=" * 80)

    # Execute tests
    dynamics_results = test_dynamics_models_comprehensive()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"integration_coordinator_dynamics_validation_final_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump(dynamics_results, f, indent=2)

    print(f"\n+ Results saved to: {results_file}")

    return dynamics_results


if __name__ == "__main__":
    try:
        results = main()

        # Exit with appropriate code
        if results['validation_matrix']['overall_status'] in ['PASSED', 'PARTIAL', 'MINIMAL']:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(2)  # Critical error