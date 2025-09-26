#==========================================================================================\\\
#==================== final_integration_health_validator.py ===========================\\\
#==========================================================================================\\\

"""
Final Integration Health Validator for DIP_SMC_PSO Project.
ASCII-only output with comprehensive validation.
"""

import sys
import json
import traceback
from datetime import datetime

def validate_system_health():
    """Execute comprehensive system health validation."""

    print("COMPREHENSIVE SYSTEM HEALTH VALIDATION")
    print("DIP_SMC_PSO Project - Integration Health Assessment")
    print("Timestamp: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

    results = {
        "timestamp": datetime.now().isoformat(),
        "validation_components": {},
        "overall_health_score": 0.0,
        "integration_status": "UNKNOWN",
        "critical_issues": [],
        "recommendations": []
    }

    # 1. Configuration System Health
    print("\n1. CONFIGURATION SYSTEM HEALTH")
    print("-" * 40)

    config_health = {"status": "UNKNOWN", "degraded_mode": False, "score": 0}

    try:
        from src.config import load_config

        # Test strict validation
        try:
            config = load_config('config.yaml', allow_unknown=False)
            config_health = {"status": "HEALTHY", "degraded_mode": False, "score": 100}
            print("SUCCESS: Configuration loaded with strict validation")
        except:
            # Test degraded mode
            try:
                config = load_config('config.yaml', allow_unknown=True)
                config_health = {"status": "DEGRADED", "degraded_mode": True, "score": 75}
                print("WARNING: Configuration requires degraded mode (allow_unknown=True)")
            except Exception as e:
                config_health = {"status": "FAILED", "degraded_mode": False, "score": 0}
                print(f"ERROR: Configuration failed: {e}")

    except ImportError as e:
        config_health = {"status": "IMPORT_ERROR", "degraded_mode": False, "score": 0}
        print(f"ERROR: Configuration import failed: {e}")

    results["validation_components"]["configuration"] = config_health

    # 2. Critical Import Resolution
    print("\n2. CRITICAL IMPORT RESOLUTION")
    print("-" * 40)

    critical_imports = [
        ("src.controllers.factory", "create_controller"),
        ("src.controllers.classic_smc", "ClassicalSMCController"),
        ("src.controllers.sta_smc", "SuperTwistingSMCController"),
        ("src.controllers.adaptive_smc", "AdaptiveSMCController"),
        ("src.controllers.hybrid_adaptive_sta_smc", "HybridAdaptiveSTASMCController"),
        ("src.core.dynamics", "DIPDynamics"),
        ("src.core.dynamics_full", "FullDIPDynamics"),
        ("src.optimizer.pso_optimizer", "PSOTuner"),
    ]

    import_successful = 0
    import_total = len(critical_imports)

    for module_path, item_name in critical_imports:
        try:
            module = __import__(module_path, fromlist=[item_name])
            getattr(module, item_name)
            import_successful += 1
            print(f"SUCCESS: {module_path}.{item_name}")
        except Exception as e:
            print(f"ERROR: {module_path}.{item_name} - {str(e)[:60]}...")

    import_score = (import_successful / import_total) * 100
    print(f"Import Resolution Score: {import_score:.1f}% ({import_successful}/{import_total})")

    results["validation_components"]["imports"] = {
        "successful": import_successful,
        "total": import_total,
        "score": import_score
    }

    # 3. Controller Factory Validation
    print("\n3. CONTROLLER FACTORY VALIDATION")
    print("-" * 40)

    controller_types = [
        ("classical_smc", [5.0, 5.0, 5.0, 0.5, 0.5, 0.5]),
        ("sta_smc", [4.0, 4.0, 4.0, 1.0, 1.0, 1.0]),
        ("adaptive_smc", [10.0, 8.0, 5.0, 4.0, 1.0]),
        ("hybrid_adaptive_sta_smc", [5.0, 5.0, 5.0, 0.5]),
    ]

    controller_successful = 0
    controller_total = len(controller_types)

    for ctrl_type, gains in controller_types:
        try:
            from src.controllers.factory import create_controller
            controller = create_controller(ctrl_type, gains=gains)
            controller_successful += 1
            print(f"SUCCESS: {ctrl_type} controller created")
        except Exception as e:
            print(f"ERROR: {ctrl_type} - {str(e)[:60]}...")

    controller_score = (controller_successful / controller_total) * 100
    print(f"Controller Factory Score: {controller_score:.1f}% ({controller_successful}/{controller_total})")

    results["validation_components"]["controllers"] = {
        "successful": controller_successful,
        "total": controller_total,
        "score": controller_score
    }

    # 4. End-to-End Workflow Test
    print("\n4. END-TO-END WORKFLOW TEST")
    print("-" * 40)

    workflow_steps = 0
    total_workflow_steps = 4

    try:
        # Step 1: Create controller
        from src.controllers.factory import create_controller
        controller = create_controller("classical_smc", gains=[5.0, 5.0, 5.0, 0.5, 0.5, 0.5])
        workflow_steps += 1
        print("SUCCESS: Step 1 - Controller created")

        # Step 2: Create dynamics
        from src.core.dynamics import DIPDynamics
        dynamics = DIPDynamics()
        workflow_steps += 1
        print("SUCCESS: Step 2 - Dynamics created")

        # Step 3: Test control computation
        import numpy as np
        test_state = np.array([0.1, 0.1, 0.05, 0.05, 0.0, 0.0])
        control_output = controller.compute_control(test_state, np.array([0.0]), [])
        workflow_steps += 1
        print(f"SUCCESS: Step 3 - Control computed: {control_output}")

        # Step 4: Test dynamics computation
        state_dot = dynamics.dynamics(test_state, control_output)
        workflow_steps += 1
        print(f"SUCCESS: Step 4 - Dynamics computed: shape {state_dot.shape}")

    except Exception as e:
        print(f"ERROR: Workflow failed at step {workflow_steps + 1}: {str(e)[:60]}...")

    workflow_score = (workflow_steps / total_workflow_steps) * 100
    print(f"End-to-End Workflow Score: {workflow_score:.1f}% ({workflow_steps}/{total_workflow_steps})")

    results["validation_components"]["workflow"] = {
        "steps_completed": workflow_steps,
        "total_steps": total_workflow_steps,
        "score": workflow_score
    }

    # 5. Calculate Overall Integration Health Score
    print("\n5. INTEGRATION HEALTH SCORE CALCULATION")
    print("-" * 40)

    # Component weights
    weights = {
        "configuration": 0.15,  # Degraded mode acceptable
        "imports": 0.35,        # Critical for integration
        "controllers": 0.30,    # Core functionality
        "workflow": 0.20        # End-to-end integration
    }

    # Calculate weighted score
    overall_score = (
        config_health["score"] * weights["configuration"] +
        import_score * weights["imports"] +
        controller_score * weights["controllers"] +
        workflow_score * weights["workflow"]
    )

    print(f"Component Scores:")
    print(f"  Configuration: {config_health['score']:.1f}% (weight: {weights['configuration']:.1%})")
    print(f"  Import Resolution: {import_score:.1f}% (weight: {weights['imports']:.1%})")
    print(f"  Controller Factory: {controller_score:.1f}% (weight: {weights['controllers']:.1%})")
    print(f"  End-to-End Workflow: {workflow_score:.1f}% (weight: {weights['workflow']:.1%})")

    print(f"\nOVERALL INTEGRATION HEALTH SCORE: {overall_score:.1f}%")

    # Determine integration status
    if overall_score >= 90:
        integration_status = "EXCELLENT"
        recommendation = "System ready for production deployment"
    elif overall_score >= 80:
        integration_status = "GOOD"
        recommendation = "System ready with standard monitoring"
    elif overall_score >= 70:
        integration_status = "ACCEPTABLE"
        recommendation = "System functional with minor issues to address"
    elif overall_score >= 60:
        integration_status = "DEGRADED"
        recommendation = "System partially functional - address critical issues"
    else:
        integration_status = "POOR"
        recommendation = "System requires significant fixes before deployment"

    print(f"Integration Status: {integration_status}")
    print(f"Recommendation: {recommendation}")

    # Identify critical issues
    critical_issues = []
    if config_health["status"] == "FAILED":
        critical_issues.append("Configuration system completely broken")
    if import_score < 50:
        critical_issues.append("Critical import failures affecting system integration")
    if controller_score < 75:
        critical_issues.append("Controller factory issues affecting core functionality")
    if workflow_score < 50:
        critical_issues.append("End-to-end workflow failures")

    # Set final results
    results["overall_health_score"] = overall_score
    results["integration_status"] = integration_status
    results["recommendations"] = [recommendation]
    results["critical_issues"] = critical_issues

    # Save results
    output_file = f"integration_health_validation_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Final Summary
    print("\n" + "=" * 80)
    print("INTEGRATION HEALTH VALIDATION COMPLETE")
    print("=" * 80)
    print(f"Results saved to: {output_file}")
    print(f"Overall Health Score: {overall_score:.1f}%")
    print(f"Configuration Status: {config_health['status']}")
    print(f"Integration Status: {integration_status}")

    if critical_issues:
        print(f"\nCritical Issues:")
        for i, issue in enumerate(critical_issues, 1):
            print(f"  {i}. {issue}")

    return results

def main():
    """Main validation execution."""
    try:
        results = validate_system_health()
        return results
    except Exception as e:
        print(f"CRITICAL ERROR: Validation failed with exception: {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()