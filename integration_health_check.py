#==========================================================================================\\\
#=========================== integration_health_check.py ===============================\\\
#==========================================================================================\\\

"""
Integration Health Check for DIP_SMC_PSO Project.
Corrected import paths and validation logic.
"""

import sys
import json
import traceback
from datetime import datetime
from pathlib import Path

def check_configuration_health():
    """Check configuration system health with corrected logic."""
    print("=" * 80)
    print("1. CONFIGURATION SYSTEM VALIDATION")
    print("=" * 80)

    config_status = {
        "status": "UNKNOWN",
        "degraded_mode": False,
        "error_count": 0,
        "details": []
    }

    try:
        from src.config import load_config

        # Try strict validation first
        try:
            config = load_config('config.yaml', allow_unknown=False)
            config_status["status"] = "HEALTHY"
            config_status["details"].append("Configuration loaded with strict validation")
            print("✓ HEALTHY: Configuration loaded without degraded mode")

        except Exception as strict_error:
            # Count schema validation errors
            error_str = str(strict_error)
            config_status["error_count"] = error_str.count("Value error")

            # Try degraded mode
            try:
                config = load_config('config.yaml', allow_unknown=True)
                config_status["status"] = "DEGRADED"
                config_status["degraded_mode"] = True
                config_status["details"].append(f"Schema validation issues: {config_status['error_count']}")
                print(f"⚠ DEGRADED: Configuration requires allow_unknown=True")
                print(f"  Schema validation issues found: {config_status['error_count']}")

            except Exception as degraded_error:
                config_status["status"] = "FAILED"
                config_status["details"].append(f"Complete failure: {degraded_error}")
                print(f"✗ FAILED: Configuration completely broken")

    except ImportError as e:
        config_status["status"] = "IMPORT_ERROR"
        config_status["details"].append(f"Import error: {e}")
        print(f"✗ IMPORT_ERROR: Cannot import config module: {e}")

    return config_status

def check_critical_imports():
    """Check critical import resolution with corrected paths."""
    print("\n" + "=" * 80)
    print("2. CRITICAL IMPORT RESOLUTION")
    print("=" * 80)

    # Updated import paths based on actual project structure
    critical_imports = [
        ("src.controllers.factory", "create_controller", "Controller factory"),
        ("src.controllers.classic_smc", "ClassicalSMCController", "Classical SMC controller"),
        ("src.controllers.sta_smc", "SuperTwistingSMCController", "Super-twisting SMC controller"),
        ("src.controllers.adaptive_smc", "AdaptiveSMCController", "Adaptive SMC controller"),
        ("src.controllers.hybrid_adaptive_sta_smc", "HybridAdaptiveSTASMCController", "Hybrid adaptive STA controller"),
        ("src.core.dynamics", "DIPDynamics", "Simplified dynamics (legacy)"),
        ("src.plant.models.simplified.dynamics", "SimplifiedDIPDynamics", "Simplified dynamics (new)"),
        ("src.core.dynamics_full", "FullDIPDynamics", "Full nonlinear dynamics"),
        ("src.optimizer.pso_optimizer", "PSOTuner", "PSO optimization"),
        ("src.config", "load_config", "Configuration loader"),
    ]

    successful = 0
    failed = 0
    details = {}

    for module_path, item_name, description in critical_imports:
        try:
            module = __import__(module_path, fromlist=[item_name])
            getattr(module, item_name)
            successful += 1
            details[f"{module_path}.{item_name}"] = "SUCCESS"
            print(f"✓ {description}: {module_path}.{item_name}")
        except Exception as e:
            failed += 1
            details[f"{module_path}.{item_name}"] = f"FAILED: {e}"
            print(f"✗ {description}: {e}")

    total = len(critical_imports)
    score = (successful / total) * 100
    print(f"\nImport Resolution Score: {score:.1f}% ({successful}/{total})")

    return {
        "successful": successful,
        "failed": failed,
        "total": total,
        "score": score,
        "details": details
    }

def check_controller_factory():
    """Test controller factory with proper configuration handling."""
    print("\n" + "=" * 80)
    print("3. CONTROLLER FACTORY VALIDATION")
    print("=" * 80)

    controller_configs = [
        ("classical_smc", [5.0, 5.0, 5.0, 0.5, 0.5, 0.5]),
        ("sta_smc", [4.0, 4.0, 4.0, 1.0, 1.0, 1.0]),  # Fixed K1 > K2 requirement
        ("adaptive_smc", [10.0, 8.0, 5.0, 4.0, 1.0]),
        ("hybrid_adaptive_sta_smc", [5.0, 5.0, 5.0, 0.5]),
    ]

    successful = 0
    failed = 0
    details = {}

    for ctrl_type, gains in controller_configs:
        try:
            from src.controllers.factory import create_controller
            controller = create_controller(ctrl_type, gains=gains)

            # Test that controller has compute_control method
            if hasattr(controller, 'compute_control'):
                successful += 1
                details[ctrl_type] = "SUCCESS"
                print(f"✓ {ctrl_type}: Controller created and validated")
            else:
                failed += 1
                details[ctrl_type] = "FAILED: Missing compute_control method"
                print(f"✗ {ctrl_type}: Missing compute_control method")

        except Exception as e:
            failed += 1
            details[ctrl_type] = f"FAILED: {e}"
            print(f"✗ {ctrl_type}: {e}")

    total = len(controller_configs)
    score = (successful / total) * 100
    print(f"\nController Factory Score: {score:.1f}% ({successful}/{total})")

    return {
        "successful": successful,
        "failed": failed,
        "total": total,
        "score": score,
        "details": details
    }

def check_dynamics_models():
    """Test dynamics model instantiation with corrected paths."""
    print("\n" + "=" * 80)
    print("4. DYNAMICS MODELS VALIDATION")
    print("=" * 80)

    # Test both legacy and new import paths
    dynamics_tests = [
        ("Legacy DIPDynamics", "src.core.dynamics", "DIPDynamics"),
        ("New SimplifiedDIPDynamics", "src.plant.models.simplified.dynamics", "SimplifiedDIPDynamics"),
        ("Full DIPDynamics", "src.core.dynamics_full", "FullDIPDynamics"),
    ]

    successful = 0
    failed = 0
    details = {}

    for test_name, module_path, class_name in dynamics_tests:
        try:
            module = __import__(module_path, fromlist=[class_name])
            DynamicsClass = getattr(module, class_name)

            # Try instantiation with empty config for simplified models
            if "Full" in class_name:
                # FullDIPDynamics requires config
                try:
                    dynamics = DynamicsClass({})  # Empty config dict
                except TypeError:
                    # Try with more specific config structure
                    config = {"physics": {}}
                    dynamics = DynamicsClass(config)
            else:
                dynamics = DynamicsClass()

            # Test that it has a dynamics method
            if hasattr(dynamics, 'dynamics'):
                successful += 1
                details[test_name] = "SUCCESS"
                print(f"✓ {test_name}: Instantiated and validated")
            else:
                failed += 1
                details[test_name] = "FAILED: Missing dynamics method"
                print(f"✗ {test_name}: Missing dynamics method")

        except Exception as e:
            failed += 1
            details[test_name] = f"FAILED: {e}"
            print(f"✗ {test_name}: {e}")

    total = len(dynamics_tests)
    score = (successful / total) * 100
    print(f"\nDynamics Models Score: {score:.1f}% ({successful}/{total})")

    return {
        "successful": successful,
        "failed": failed,
        "total": total,
        "score": score,
        "details": details
    }

def test_end_to_end_workflow():
    """Test complete simulation workflow."""
    print("\n" + "=" * 80)
    print("5. END-TO-END SIMULATION WORKFLOW")
    print("=" * 80)

    steps = [
        "Create controller",
        "Create dynamics",
        "Test control computation",
        "Test dynamics computation",
        "Test integration step"
    ]

    steps_completed = 0
    total_steps = len(steps)
    step_details = {}

    try:
        # Step 1: Create controller
        print(f"Step 1: {steps[0]}...")
        from src.controllers.factory import create_controller
        controller = create_controller("classical_smc", gains=[5.0, 5.0, 5.0, 0.5, 0.5, 0.5])
        steps_completed += 1
        step_details[steps[0]] = "SUCCESS"
        print("✓ Controller created")

        # Step 2: Create dynamics using legacy path
        print(f"Step 2: {steps[1]}...")
        try:
            from src.core.dynamics import DIPDynamics
            dynamics = DIPDynamics()
        except:
            # Try new path
            from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
            dynamics = SimplifiedDIPDynamics()

        steps_completed += 1
        step_details[steps[1]] = "SUCCESS"
        print("✓ Dynamics model created")

        # Step 3: Test control computation
        print(f"Step 3: {steps[2]}...")
        import numpy as np
        test_state = np.array([0.1, 0.1, 0.05, 0.05, 0.0, 0.0])  # 6-element state
        last_control = np.array([0.0])
        control_output = controller.compute_control(test_state, last_control, [])
        steps_completed += 1
        step_details[steps[2]] = f"SUCCESS - Control: {control_output}"
        print(f"✓ Control computation: {control_output}")

        # Step 4: Test dynamics computation
        print(f"Step 4: {steps[3]}...")
        state_dot = dynamics.dynamics(test_state, control_output)
        steps_completed += 1
        step_details[steps[3]] = f"SUCCESS - Shape: {state_dot.shape}"
        print(f"✓ Dynamics computation: shape {state_dot.shape}")

        # Step 5: Test integration step
        print(f"Step 5: {steps[4]}...")
        dt = 0.01
        new_state = test_state + dt * state_dot
        steps_completed += 1
        step_details[steps[4]] = "SUCCESS - Integration complete"
        print("✓ Integration step completed")

    except Exception as e:
        error_step = steps[steps_completed] if steps_completed < len(steps) else "Unknown"
        step_details[error_step] = f"FAILED: {e}"
        print(f"✗ Failed at step {steps_completed + 1}: {e}")

    score = (steps_completed / total_steps) * 100
    print(f"\nEnd-to-End Workflow Score: {score:.1f}% ({steps_completed}/{total_steps})")

    return {
        "steps_completed": steps_completed,
        "total_steps": total_steps,
        "score": score,
        "step_details": step_details
    }

def calculate_integration_health_score(results):
    """Calculate overall integration health score."""
    print("\n" + "=" * 80)
    print("6. INTEGRATION HEALTH SCORE CALCULATION")
    print("=" * 80)

    # Component weights for integration health
    weights = {
        "configuration": 0.15,  # Can function in degraded mode
        "imports": 0.30,        # Critical for integration
        "controllers": 0.25,    # Core functionality
        "dynamics": 0.20,       # Core functionality
        "workflow": 0.10        # End-to-end integration
    }

    # Calculate component scores
    config_result = results["configuration"]
    if config_result["status"] == "HEALTHY":
        config_score = 100.0
    elif config_result["status"] == "DEGRADED":
        config_score = 75.0  # Degraded mode is acceptable for integration
    else:
        config_score = 0.0

    import_score = results["imports"]["score"]
    controller_score = results["controllers"]["score"]
    dynamics_score = results["dynamics"]["score"]
    workflow_score = results["workflow"]["score"]

    # Calculate weighted integration health score
    integration_score = (
        config_score * weights["configuration"] +
        import_score * weights["imports"] +
        controller_score * weights["controllers"] +
        dynamics_score * weights["dynamics"] +
        workflow_score * weights["workflow"]
    )

    print(f"Integration Health Components:")
    print(f"  Configuration: {config_score:.1f}% (weight: {weights['configuration']:.1%})")
    print(f"  Import Resolution: {import_score:.1f}% (weight: {weights['imports']:.1%})")
    print(f"  Controller Factory: {controller_score:.1f}% (weight: {weights['controllers']:.1%})")
    print(f"  Dynamics Models: {dynamics_score:.1f}% (weight: {weights['dynamics']:.1%})")
    print(f"  End-to-End Workflow: {workflow_score:.1f}% (weight: {weights['workflow']:.1%})")

    print(f"\nINTEGRATION HEALTH SCORE: {integration_score:.1f}%")

    # Health status assessment
    if integration_score >= 90:
        status = "EXCELLENT"
        recommendation = "System integration ready for production deployment"
    elif integration_score >= 80:
        status = "GOOD"
        recommendation = "System integration ready with standard monitoring"
    elif integration_score >= 70:
        status = "ACCEPTABLE"
        recommendation = "System integration functional with minor issues to address"
    elif integration_score >= 60:
        status = "DEGRADED"
        recommendation = "System integration partially functional - address critical issues"
    else:
        status = "POOR"
        recommendation = "System integration requires significant fixes"

    print(f"Integration Status: {status}")
    print(f"Recommendation: {recommendation}")

    return integration_score, status, recommendation

def main():
    """Execute comprehensive integration health validation."""
    print("COMPREHENSIVE INTEGRATION HEALTH VALIDATION")
    print("DIP_SMC_PSO Project")
    print("Timestamp: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

    # Execute all validation components
    results = {
        "timestamp": datetime.now().isoformat(),
        "validation_type": "integration_health_check",
        "configuration": check_configuration_health(),
        "imports": check_critical_imports(),
        "controllers": check_controller_factory(),
        "dynamics": check_dynamics_models(),
        "workflow": test_end_to_end_workflow()
    }

    # Calculate integration health score
    integration_score, status, recommendation = calculate_integration_health_score(results)

    results["integration_health_score"] = integration_score
    results["integration_status"] = status
    results["recommendation"] = recommendation

    # Save comprehensive results
    output_file = f"integration_health_validation_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Final summary
    print("\n" + "=" * 80)
    print("INTEGRATION HEALTH VALIDATION COMPLETE")
    print("=" * 80)
    print(f"Results saved to: {output_file}")
    print(f"Integration Health Score: {integration_score:.1f}%")
    print(f"Configuration Status: {results['configuration']['status']}")
    print(f"Overall Assessment: {status}")
    print(f"Recommendation: {recommendation}")

    # Critical issues summary
    critical_issues = []
    if results["configuration"]["status"] == "FAILED":
        critical_issues.append("Configuration system completely broken")
    if results["imports"]["score"] < 50:
        critical_issues.append("Critical import resolution failures")
    if results["controllers"]["score"] < 75:
        critical_issues.append("Controller factory issues")
    if results["dynamics"]["score"] < 50:
        critical_issues.append("Dynamics model instantiation problems")

    if critical_issues:
        print(f"\nCritical Issues Identified:")
        for issue in critical_issues:
            print(f"  - {issue}")

    return results

if __name__ == "__main__":
    main()