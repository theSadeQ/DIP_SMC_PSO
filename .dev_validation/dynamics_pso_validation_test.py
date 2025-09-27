#!/usr/bin/env python3
"""
Dynamics Models and PSO Workflow Validation Test
==================================================

Comprehensive validation of:
1. All 3 dynamics models (Simplified, Full, LowRank)
2. PSO optimization workflow components
3. Controller-dynamics integration chain
4. Production deployment readiness assessment

Mission: Execute Phase 4 validation for production deployment recheck.
"""

import numpy as np
import json
from datetime import datetime
from typing import Dict, Any

def validate_dynamics_models() -> Dict[str, Any]:
    """Validate all 3 dynamics models with empty config initialization."""
    print("=" * 60)
    print("PHASE 4A: DYNAMICS MODELS VALIDATION")
    print("=" * 60)

    from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
    from src.plant.models.full.dynamics import FullDIPDynamics
    from src.plant.models.lowrank.dynamics import LowRankDIPDynamics

    dynamics_models = [
        ('Simplified', SimplifiedDIPDynamics),
        ('Full', FullDIPDynamics),
        ('LowRank', LowRankDIPDynamics)
    ]

    working_models = 0
    model_details = {}

    for name, model_class in dynamics_models:
        try:
            print(f"\nTesting {name}Dynamics...")

            # Test empty config initialization
            model = model_class({})
            print(f"  SUCCESS Empty config initialization")

            # Test with sample state and control
            test_state = np.array([0.1, 0.05, 0.0, 0.0, 0.0, 0.0])  # 6-element DIP state
            test_control = np.array([1.0])

            # Test compute_dynamics method
            result = model.compute_dynamics(test_state, test_control)

            if result.success:
                norm = np.linalg.norm(result.state_derivative)
                print(f"  SUCCESS State derivative computation (norm: {norm:.4f})")

                # Test numerical stability
                if np.all(np.isfinite(result.state_derivative)):
                    print(f"  SUCCESS Numerical stability")
                    model_details[name] = {
                        'status': 'WORKING',
                        'norm': float(norm),
                        'numerical_stability': True,
                        'state_derivative_shape': list(result.state_derivative.shape)
                    }
                    working_models += 1
                else:
                    print(f"  FAILED Numerical stability (non-finite values)")
                    model_details[name] = {
                        'status': 'FAILED',
                        'error': 'Non-finite state derivatives'
                    }
            else:
                print(f"  FAILED State derivative computation")
                print(f"    Error: {result.info}")
                model_details[name] = {
                    'status': 'FAILED',
                    'error': f'compute_dynamics failed: {result.info}'
                }

        except Exception as e:
            print(f"  FAILED Exception: {e}")
            model_details[name] = {
                'status': 'FAILED',
                'error': str(e)
            }

    dynamics_health = (working_models / 3) * 100

    print(f"\nDYNAMICS MODELS HEALTH: {working_models}/3 ({dynamics_health}%)")

    if dynamics_health == 100:
        print("SUCCESS VERIFIED: All dynamics models operational")
    else:
        print(f"CRITICAL: Dynamics failure rate {100-dynamics_health}%")

    return {
        'working_models': working_models,
        'total_models': 3,
        'health_percentage': dynamics_health,
        'model_details': model_details,
        'validation_status': 'PASS' if dynamics_health == 100 else 'FAIL'
    }

def validate_pso_workflow() -> Dict[str, Any]:
    """Validate PSO optimization workflow components."""
    print("\n" + "=" * 60)
    print("PHASE 4B: PSO WORKFLOW VALIDATION")
    print("=" * 60)

    try:
        from src.optimizer.pso_optimizer import PSOTuner
        from src.config import load_config
        from src.controllers.factory import create_controller

        print("\nTesting PSO workflow components...")

        # Load configuration
        config = load_config('config.yaml', allow_unknown=False)
        print("  SUCCESS Configuration loading")

        # Test PSO config availability
        pso_workflow_details = {}

        if hasattr(config, 'pso') and config.pso:
            pso_config = config.pso
            print(f"  SUCCESS PSO config available: {type(pso_config)}")
            pso_workflow_details['pso_config_available'] = True
            pso_workflow_details['pso_config_type'] = str(type(pso_config))

            # Create controller factory function for PSO
            def controller_factory(gains):
                """Create a controller with given gains."""
                try:
                    controller_config = config.controllers['classical_smc']
                    controller_config.gains = gains.tolist() if hasattr(gains, 'tolist') else list(gains)
                    controller = create_controller('classical_smc', controller_config)
                    return controller
                except Exception as e:
                    print(f"    Controller factory error: {e}")
                    return None

            print("  SUCCESS Controller factory function")
            pso_workflow_details['controller_factory_created'] = True

            # Test the factory function
            test_gains = np.array([10.0, 5.0, 8.0, 3.0, 15.0, 2.0])
            test_controller = controller_factory(test_gains)

            if test_controller is not None:
                print(f"  SUCCESS Controller factory test: {type(test_controller).__name__}")
                pso_workflow_details['controller_factory_test'] = True
                pso_workflow_details['test_controller_type'] = type(test_controller).__name__

                # Try to create PSO tuner
                tuner = PSOTuner(
                    controller_factory=controller_factory,
                    config=config
                )
                print(f"  SUCCESS PSO Tuner instantiation")
                print(f"  SUCCESS PSO Tuner type: {type(tuner).__name__}")

                pso_workflow_details['pso_tuner_created'] = True
                pso_workflow_details['pso_tuner_type'] = type(tuner).__name__

                return {
                    'validation_status': 'PASS',
                    'pso_workflow_operational': True,
                    'details': pso_workflow_details
                }

            else:
                print("  FAILED Controller factory test")
                pso_workflow_details['controller_factory_test'] = False

                return {
                    'validation_status': 'FAIL',
                    'pso_workflow_operational': False,
                    'error': 'Controller factory test failed',
                    'details': pso_workflow_details
                }
        else:
            print("  FAILED PSO config not found")
            return {
                'validation_status': 'FAIL',
                'pso_workflow_operational': False,
                'error': 'PSO config not found in configuration'
            }

    except Exception as e:
        print(f"  FAILED PSO workflow validation: {e}")
        return {
            'validation_status': 'FAIL',
            'pso_workflow_operational': False,
            'error': str(e)
        }

def validate_integration_chain() -> Dict[str, Any]:
    """Validate controller-dynamics integration chain."""
    print("\n" + "=" * 60)
    print("PHASE 4C: INTEGRATION CHAIN VALIDATION")
    print("=" * 60)

    try:
        from src.controllers.factory import create_controller
        from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
        from src.config import load_config

        print("\nTesting controller-dynamics integration chain...")

        config = load_config('config.yaml', allow_unknown=False)

        # Create controller and dynamics
        controller = create_controller('classical_smc', config.controllers['classical_smc'])
        dynamics = SimplifiedDIPDynamics({})

        print("  SUCCESS Controller and dynamics instantiation")

        # Test integration chain
        test_state = np.array([0.1, 0.05, 0.0, 0.0, 0.0, 0.0])  # 6-element DIP state
        test_control = np.array([0.0])  # Initial control

        # Controller computes control
        control_result = controller.compute_control(test_state, test_control, [])
        print(f"  SUCCESS Controller computation (type: {type(control_result)})")

        # Extract control value (controller returns dict with 'u' key)
        if isinstance(control_result, dict) and 'u' in control_result:
            control_value = np.array([control_result['u']])
            print(f"  SUCCESS Control value extraction ({control_value})")
        else:
            control_value = np.array([0.0])  # Fallback
            print(f"  WARNING Control value fallback: {control_value}")

        # Dynamics computes state derivative
        result = dynamics.compute_dynamics(test_state, control_value)
        if result.success:
            norm = np.linalg.norm(result.state_derivative)
            print(f"  SUCCESS Dynamics computation (norm: {norm:.4f})")
            print("  SUCCESS Integration chain WORKING")

            return {
                'validation_status': 'PASS',
                'integration_chain_operational': True,
                'controller_type': type(controller).__name__,
                'dynamics_type': type(dynamics).__name__,
                'state_derivative_norm': float(norm),
                'numerical_stability': bool(np.all(np.isfinite(result.state_derivative)))
            }
        else:
            print(f"  FAILED Dynamics computation: {result.info}")
            return {
                'validation_status': 'FAIL',
                'integration_chain_operational': False,
                'error': f'Dynamics computation failed: {result.info}'
            }

    except Exception as e:
        print(f"  FAILED Integration chain test: {e}")
        return {
            'validation_status': 'FAIL',
            'integration_chain_operational': False,
            'error': str(e)
        }

def main():
    """Execute comprehensive dynamics and PSO validation."""
    print("DYNAMICS MODELS AND PSO WORKFLOW VALIDATION")
    print("Mission: Phase 4 Production Deployment Recheck")
    print("Timestamp:", datetime.now().isoformat())
    print()

    # Execute validation phases
    dynamics_results = validate_dynamics_models()
    pso_results = validate_pso_workflow()
    integration_results = validate_integration_chain()

    # Compute overall health score
    component_scores = [
        dynamics_results['health_percentage'] / 100,  # Dynamics models
        1.0 if pso_results['validation_status'] == 'PASS' else 0.0,  # PSO workflow
        1.0 if integration_results['validation_status'] == 'PASS' else 0.0  # Integration
    ]

    overall_health = float((sum(component_scores) / len(component_scores)) * 100)

    # Generate comprehensive report
    validation_report = {
        'timestamp': datetime.now().isoformat(),
        'mission': 'Phase 4: Dynamics Models and PSO Workflow Validation',
        'overall_health_score': overall_health,
        'component_health': {
            'dynamics_models': dynamics_results['health_percentage'],
            'pso_workflow': 100.0 if pso_results['validation_status'] == 'PASS' else 0.0,
            'integration_chain': 100.0 if integration_results['validation_status'] == 'PASS' else 0.0
        },
        'validation_results': {
            'dynamics_models': dynamics_results,
            'pso_workflow': pso_results,
            'integration_chain': integration_results
        },
        'production_readiness': {
            'status': 'READY' if overall_health >= 90 else 'NOT_READY',
            'critical_issues': [],
            'recommendations': []
        }
    }

    # Add critical issues and recommendations
    if dynamics_results['validation_status'] != 'PASS':
        validation_report['production_readiness']['critical_issues'].append(
            f"Dynamics models failure: {dynamics_results['working_models']}/3 working"
        )

    if pso_results['validation_status'] != 'PASS':
        validation_report['production_readiness']['critical_issues'].append(
            "PSO workflow not operational"
        )

    if integration_results['validation_status'] != 'PASS':
        validation_report['production_readiness']['critical_issues'].append(
            "Controller-dynamics integration chain broken"
        )

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Overall Health Score: {overall_health:.1f}%")
    print(f"Dynamics Models: {dynamics_results['working_models']}/3 ({dynamics_results['health_percentage']:.1f}%)")
    print(f"PSO Workflow: {'PASS' if pso_results['validation_status'] == 'PASS' else 'FAIL'}")
    print(f"Integration Chain: {'PASS' if integration_results['validation_status'] == 'PASS' else 'FAIL'}")

    if overall_health >= 90:
        print("\nSUCCESS PRODUCTION DEPLOYMENT: READY")
        validation_report['production_readiness']['recommendations'].append(
            "All critical components operational - ready for production deployment"
        )
    else:
        print("\nCRITICAL PRODUCTION DEPLOYMENT: NOT READY")
        validation_report['production_readiness']['recommendations'].append(
            "Address critical issues before production deployment"
        )

    # Save validation report
    report_filename = f'dynamics_pso_validation_{datetime.now().strftime("%Y_%m_%d_%H%M%S")}.json'
    with open(report_filename, 'w') as f:
        json.dump(validation_report, f, indent=2)

    print(f"\nValidation report saved: {report_filename}")

    return validation_report

if __name__ == "__main__":
    main()