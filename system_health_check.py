#==========================================================================================\\\
#============================== system_health_check.py =================================\\\
#==========================================================================================\\\

"""
System Health Check for DIP_SMC_PSO Project.
Simple ASCII validation without Unicode issues.
"""

import sys
import json
import traceback
from datetime import datetime
from pathlib import Path

def check_configuration_health():
    """Check configuration system health."""
    print("=" * 80)
    print("1. CONFIGURATION SYSTEM HEALTH")
    print("=" * 80)

    config_status = {
        "status": "UNKNOWN",
        "degraded_mode": False,
        "error_count": 0
    }

    try:
        from src.config import load_config

        # Try strict validation first
        try:
            config = load_config('config.yaml', allow_unknown=False)
            config_status["status"] = "HEALTHY"
            print("SUCCESS: Configuration loaded without degraded mode")

        except Exception as strict_error:
            # Count errors
            error_str = str(strict_error)
            config_status["error_count"] = error_str.count("controllers.")

            # Try degraded mode
            try:
                config = load_config('config.yaml', allow_unknown=True)
                config_status["status"] = "DEGRADED"
                config_status["degraded_mode"] = True
                print(f"WARNING: Configuration in DEGRADED MODE - {config_status['error_count']} schema issues")

            except Exception as degraded_error:
                config_status["status"] = "FAILED"
                print(f"ERROR: Configuration completely failed: {degraded_error}")

    except ImportError as e:
        config_status["status"] = "IMPORT_ERROR"
        print(f"ERROR: Import failed: {e}")

    return config_status

def check_imports():
    """Check critical import resolution."""
    print("\n" + "=" * 80)
    print("2. IMPORT RESOLUTION")
    print("=" * 80)

    critical_imports = [
        ("src.controllers.factory", "create_controller"),
        ("src.controllers.classical_smc", "ClassicalSMCController"),
        ("src.controllers.sta_smc", "STASMCController"),
        ("src.controllers.adaptive_smc", "AdaptiveSMCController"),
        ("src.controllers.hybrid_adaptive_sta_smc", "HybridAdaptiveSTASMCController"),
        ("src.core.dynamics", "SimplifiedDIPDynamics"),
        ("src.core.dynamics_full", "FullDIPDynamics"),
        ("src.optimizer.pso_optimizer", "PSOTuner"),
    ]

    successful = 0
    failed = 0

    for module_path, item_name in critical_imports:
        try:
            module = __import__(module_path, fromlist=[item_name])
            getattr(module, item_name)
            successful += 1
            print(f"SUCCESS: {module_path}.{item_name}")
        except Exception as e:
            failed += 1
            print(f"ERROR: {module_path}.{item_name} - {e}")

    total = len(critical_imports)
    score = (successful / total) * 100
    print(f"\nImport Score: {score:.1f}% ({successful}/{total})")

    return {"successful": successful, "failed": failed, "total": total, "score": score}

def check_controller_factory():
    """Test controller factory functionality."""
    print("\n" + "=" * 80)
    print("3. CONTROLLER FACTORY")
    print("=" * 80)

    controller_types = ["classical_smc", "sta_smc", "adaptive_smc", "hybrid_adaptive_sta_smc"]
    successful = 0
    failed = 0

    for ctrl_type in controller_types:
        try:
            from src.controllers.factory import create_controller

            # Use appropriate gains for each controller
            if ctrl_type == "classical_smc":
                gains = [5.0, 5.0, 5.0, 0.5, 0.5, 0.5]
            elif ctrl_type == "sta_smc":
                gains = [4.0, 4.0, 4.0, 0.4, 0.4, 0.4]
            elif ctrl_type == "adaptive_smc":
                gains = [10.0, 8.0, 5.0, 4.0, 1.0]
            elif ctrl_type == "hybrid_adaptive_sta_smc":
                gains = [5.0, 5.0, 5.0, 0.5]

            controller = create_controller(ctrl_type, gains=gains)
            successful += 1
            print(f"SUCCESS: {ctrl_type} controller created")

        except Exception as e:
            failed += 1
            print(f"ERROR: {ctrl_type} failed - {e}")

    total = len(controller_types)
    score = (successful / total) * 100
    print(f"\nController Factory Score: {score:.1f}% ({successful}/{total})")

    return {"successful": successful, "failed": failed, "total": total, "score": score}

def check_dynamics_models():
    """Test dynamics model instantiation."""
    print("\n" + "=" * 80)
    print("4. DYNAMICS MODELS")
    print("=" * 80)

    models = [
        ("src.core.dynamics", "SimplifiedDIPDynamics"),
        ("src.core.dynamics_full", "FullDIPDynamics"),
    ]

    successful = 0
    failed = 0

    for module_path, class_name in models:
        try:
            module = __import__(module_path, fromlist=[class_name])
            DynamicsClass = getattr(module, class_name)
            dynamics = DynamicsClass()
            successful += 1
            print(f"SUCCESS: {class_name} instantiated")
        except Exception as e:
            failed += 1
            print(f"ERROR: {class_name} failed - {e}")

    total = len(models)
    score = (successful / total) * 100
    print(f"\nDynamics Models Score: {score:.1f}% ({successful}/{total})")

    return {"successful": successful, "failed": failed, "total": total, "score": score}

def test_simulation_workflow():
    """Test end-to-end simulation workflow."""
    print("\n" + "=" * 80)
    print("5. END-TO-END SIMULATION")
    print("=" * 80)

    steps_completed = 0
    total_steps = 5

    try:
        # Step 1: Create controller
        print("Step 1: Creating controller...")
        from src.controllers.factory import create_controller
        controller = create_controller("classical_smc", gains=[5.0, 5.0, 5.0, 0.5, 0.5, 0.5])
        steps_completed += 1
        print("SUCCESS: Controller created")

        # Step 2: Create dynamics
        print("Step 2: Creating dynamics...")
        from src.core.dynamics import SimplifiedDIPDynamics
        dynamics = SimplifiedDIPDynamics()
        steps_completed += 1
        print("SUCCESS: Dynamics created")

        # Step 3: Test control computation
        print("Step 3: Testing control computation...")
        import numpy as np
        test_state = np.array([0.1, 0.1, 0.05, 0.05, 0.0, 0.0])
        last_control = np.array([0.0])
        control_output = controller.compute_control(test_state, last_control, [])
        steps_completed += 1
        print(f"SUCCESS: Control output = {control_output}")

        # Step 4: Test dynamics computation
        print("Step 4: Testing dynamics computation...")
        state_dot = dynamics.dynamics(test_state, control_output)
        steps_completed += 1
        print(f"SUCCESS: State derivative shape = {state_dot.shape}")

        # Step 5: Test integration step
        print("Step 5: Testing integration...")
        dt = 0.01
        new_state = test_state + dt * state_dot
        steps_completed += 1
        print("SUCCESS: Integration completed")

    except Exception as e:
        print(f"ERROR: Simulation failed at step {steps_completed + 1}: {e}")

    score = (steps_completed / total_steps) * 100
    print(f"\nSimulation Workflow Score: {score:.1f}% ({steps_completed}/{total_steps})")

    return {"steps_completed": steps_completed, "total_steps": total_steps, "score": score}

def calculate_overall_health(results):
    """Calculate overall system health score."""
    print("\n" + "=" * 80)
    print("6. OVERALL SYSTEM HEALTH")
    print("=" * 80)

    # Component weights
    weights = {
        "configuration": 0.20,
        "imports": 0.25,
        "controllers": 0.25,
        "dynamics": 0.15,
        "simulation": 0.15
    }

    # Get scores
    config_score = 100.0 if results["config"]["status"] == "HEALTHY" else (60.0 if results["config"]["status"] == "DEGRADED" else 0.0)
    import_score = results["imports"]["score"]
    controller_score = results["controllers"]["score"]
    dynamics_score = results["dynamics"]["score"]
    simulation_score = results["simulation"]["score"]

    # Calculate weighted average
    overall_score = (
        config_score * weights["configuration"] +
        import_score * weights["imports"] +
        controller_score * weights["controllers"] +
        dynamics_score * weights["dynamics"] +
        simulation_score * weights["simulation"]
    )

    print(f"Component Scores:")
    print(f"  Configuration: {config_score:.1f}% (weight: {weights['configuration']:.1%})")
    print(f"  Imports: {import_score:.1f}% (weight: {weights['imports']:.1%})")
    print(f"  Controllers: {controller_score:.1f}% (weight: {weights['controllers']:.1%})")
    print(f"  Dynamics: {dynamics_score:.1f}% (weight: {weights['dynamics']:.1%})")
    print(f"  Simulation: {simulation_score:.1f}% (weight: {weights['simulation']:.1%})")

    print(f"\nOVERALL SYSTEM HEALTH SCORE: {overall_score:.1f}%")

    # Health assessment
    if overall_score >= 90:
        status = "EXCELLENT - Ready for production"
    elif overall_score >= 80:
        status = "GOOD - Ready with monitoring"
    elif overall_score >= 70:
        status = "FAIR - Functional but needs attention"
    elif overall_score >= 60:
        status = "DEGRADED - Partially functional"
    else:
        status = "POOR - Requires fixes"

    print(f"System Status: {status}")

    return overall_score, status

def main():
    """Main health check execution."""
    print("COMPREHENSIVE SYSTEM HEALTH VALIDATION")
    print("DIP_SMC_PSO Project")
    print("Timestamp: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

    # Run all checks
    results = {
        "timestamp": datetime.now().isoformat(),
        "config": check_configuration_health(),
        "imports": check_imports(),
        "controllers": check_controller_factory(),
        "dynamics": check_dynamics_models(),
        "simulation": test_simulation_workflow()
    }

    # Calculate overall health
    overall_score, status = calculate_overall_health(results)
    results["overall_health_score"] = overall_score
    results["system_status"] = status

    # Save results
    output_file = f"system_health_validation_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print(f"Results saved to: {output_file}")
    print(f"Overall Health Score: {overall_score:.1f}%")
    print(f"Configuration Status: {results['config']['status']}")

    return results

if __name__ == "__main__":
    main()