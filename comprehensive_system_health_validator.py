#==========================================================================================\\\
#======================== comprehensive_system_health_validator.py ======================\\\
#==========================================================================================\\\

"""
Comprehensive System Health Validator for DIP_SMC_PSO Project.
Performs end-to-end integration testing and system health assessment.
"""

import sys
import json
import traceback
import warnings
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

class SystemHealthValidator:
    """Comprehensive system health validation with detailed reporting."""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "overall_health_score": 0.0,
            "configuration_health": "UNKNOWN",
            "validation_results": {},
            "critical_issues": [],
            "warnings": [],
            "import_status": {},
            "recommendations": []
        }

    def validate_configuration_system(self) -> Dict[str, Any]:
        """Test configuration system health and detect degraded mode."""
        print("=" * 80)
        print("1. CONFIGURATION SYSTEM HEALTH VALIDATION")
        print("=" * 80)

        config_health = {
            "status": "UNKNOWN",
            "degraded_mode": False,
            "validation_errors": [],
            "schema_issues": 0,
            "config_domains": []
        }

        try:
            # First try strict validation
            from src.config import load_config
            try:
                config = load_config('config.yaml', allow_unknown=False)
                config_health["status"] = "HEALTHY"
                config_health["degraded_mode"] = False
                config_health["config_domains"] = list(config.keys()) if hasattr(config, 'keys') else []
                print("✓ Configuration loaded successfully - NO DEGRADED MODE")

            except Exception as strict_error:
                print(f"✗ Strict validation failed: {strict_error}")
                config_health["validation_errors"].append(str(strict_error))

                # Try degraded mode
                try:
                    config = load_config('config.yaml', allow_unknown=True)
                    config_health["status"] = "DEGRADED"
                    config_health["degraded_mode"] = True

                    # Count schema issues
                    if "controllers" in str(strict_error):
                        config_health["schema_issues"] = str(strict_error).count("controllers.")

                    print(f"⚠ Configuration loaded in DEGRADED MODE (allow_unknown=True)")
                    print(f"  Schema issues detected: {config_health['schema_issues']}")

                except Exception as degraded_error:
                    config_health["status"] = "FAILED"
                    config_health["validation_errors"].append(str(degraded_error))
                    print(f"✗ Configuration completely failed: {degraded_error}")

        except ImportError as e:
            config_health["status"] = "IMPORT_ERROR"
            config_health["validation_errors"].append(f"Import error: {e}")
            print(f"✗ Configuration import failed: {e}")

        return config_health

    def validate_import_resolution(self) -> Dict[str, Any]:
        """Test critical import resolution across the system."""
        print("\n" + "=" * 80)
        print("2. IMPORT RESOLUTION VALIDATION")
        print("=" * 80)

        import_status = {
            "total_tested": 0,
            "successful": 0,
            "failed": 0,
            "details": {}
        }

        critical_imports = [
            ("src.controllers.factory", "create_controller"),
            ("src.controllers.classical_smc", "ClassicalSMCController"),
            ("src.controllers.sta_smc", "STASMCController"),
            ("src.controllers.adaptive_smc", "AdaptiveSMCController"),
            ("src.controllers.hybrid_adaptive_sta_smc", "HybridAdaptiveSTASMCController"),
            ("src.core.dynamics", "SimplifiedDIPDynamics"),
            ("src.core.dynamics_full", "FullDIPDynamics"),
            ("src.optimizer.pso_optimizer", "PSOTuner"),
            ("src.config", "load_config"),
            ("src.utils.validation.controller", "validate_gains"),
        ]

        for module_path, item_name in critical_imports:
            import_status["total_tested"] += 1
            try:
                module = __import__(module_path, fromlist=[item_name])
                getattr(module, item_name)
                import_status["successful"] += 1
                import_status["details"][f"{module_path}.{item_name}"] = "SUCCESS"
                print(f"✓ {module_path}.{item_name}")

            except Exception as e:
                import_status["failed"] += 1
                import_status["details"][f"{module_path}.{item_name}"] = f"FAILED: {e}"
                print(f"✗ {module_path}.{item_name} - {e}")

        import_score = (import_status["successful"] / import_status["total_tested"]) * 100
        print(f"\nImport Resolution Score: {import_score:.1f}% ({import_status['successful']}/{import_status['total_tested']})")

        return import_status

    def validate_controller_factory(self) -> Dict[str, Any]:
        """Test controller factory and instantiation."""
        print("\n" + "=" * 80)
        print("3. CONTROLLER FACTORY VALIDATION")
        print("=" * 80)

        factory_health = {
            "total_controllers": 0,
            "successful_creation": 0,
            "failed_creation": 0,
            "controller_results": {}
        }

        controller_types = ["classical_smc", "sta_smc", "adaptive_smc", "hybrid_adaptive_sta_smc"]

        for ctrl_type in controller_types:
            factory_health["total_controllers"] += 1
            try:
                from src.controllers.factory import create_controller

                # Use default gains
                if ctrl_type == "classical_smc":
                    gains = [5.0, 5.0, 5.0, 0.5, 0.5, 0.5]
                elif ctrl_type == "sta_smc":
                    gains = [4.0, 4.0, 4.0, 0.4, 0.4, 0.4]
                elif ctrl_type == "adaptive_smc":
                    gains = [10.0, 8.0, 5.0, 4.0, 1.0]
                elif ctrl_type == "hybrid_adaptive_sta_smc":
                    gains = [5.0, 5.0, 5.0, 0.5]

                controller = create_controller(ctrl_type, gains=gains)
                factory_health["successful_creation"] += 1
                factory_health["controller_results"][ctrl_type] = "SUCCESS"
                print(f"✓ {ctrl_type} controller created successfully")

            except Exception as e:
                factory_health["failed_creation"] += 1
                factory_health["controller_results"][ctrl_type] = f"FAILED: {e}"
                print(f"✗ {ctrl_type} controller failed: {e}")

        factory_score = (factory_health["successful_creation"] / factory_health["total_controllers"]) * 100
        print(f"\nController Factory Score: {factory_score:.1f}% ({factory_health['successful_creation']}/{factory_health['total_controllers']})")

        return factory_health

    def validate_dynamics_models(self) -> Dict[str, Any]:
        """Test dynamics model instantiation."""
        print("\n" + "=" * 80)
        print("4. DYNAMICS MODELS VALIDATION")
        print("=" * 80)

        dynamics_health = {
            "total_models": 0,
            "successful_creation": 0,
            "failed_creation": 0,
            "model_results": {}
        }

        dynamics_models = [
            ("src.core.dynamics", "SimplifiedDIPDynamics"),
            ("src.core.dynamics_full", "FullDIPDynamics"),
        ]

        for module_path, class_name in dynamics_models:
            dynamics_health["total_models"] += 1
            try:
                module = __import__(module_path, fromlist=[class_name])
                DynamicsClass = getattr(module, class_name)

                # Try to instantiate with empty config
                dynamics = DynamicsClass()
                dynamics_health["successful_creation"] += 1
                dynamics_health["model_results"][class_name] = "SUCCESS"
                print(f"✓ {class_name} instantiated successfully")

            except Exception as e:
                dynamics_health["failed_creation"] += 1
                dynamics_health["model_results"][class_name] = f"FAILED: {e}"
                print(f"✗ {class_name} failed: {e}")

        dynamics_score = (dynamics_health["successful_creation"] / dynamics_health["total_models"]) * 100
        print(f"\nDynamics Models Score: {dynamics_score:.1f}% ({dynamics_health['successful_creation']}/{dynamics_health['total_models']})")

        return dynamics_health

    def test_end_to_end_simulation(self) -> Dict[str, Any]:
        """Test a complete simulation workflow."""
        print("\n" + "=" * 80)
        print("5. END-TO-END SIMULATION VALIDATION")
        print("=" * 80)

        simulation_health = {
            "status": "UNKNOWN",
            "steps_completed": 0,
            "total_steps": 5,
            "test_results": {}
        }

        try:
            # Step 1: Create controller
            print("Step 1: Creating controller...")
            from src.controllers.factory import create_controller
            controller = create_controller("classical_smc", gains=[5.0, 5.0, 5.0, 0.5, 0.5, 0.5])
            simulation_health["steps_completed"] += 1
            simulation_health["test_results"]["controller_creation"] = "SUCCESS"
            print("✓ Controller created")

            # Step 2: Create dynamics
            print("Step 2: Creating dynamics model...")
            from src.core.dynamics import SimplifiedDIPDynamics
            dynamics = SimplifiedDIPDynamics()
            simulation_health["steps_completed"] += 1
            simulation_health["test_results"]["dynamics_creation"] = "SUCCESS"
            print("✓ Dynamics model created")

            # Step 3: Test control computation
            print("Step 3: Testing control computation...")
            import numpy as np
            test_state = np.array([0.1, 0.1, 0.05, 0.05, 0.0, 0.0])  # 6-element state
            last_control = np.array([0.0])
            control_output = controller.compute_control(test_state, last_control, [])
            simulation_health["steps_completed"] += 1
            simulation_health["test_results"]["control_computation"] = "SUCCESS"
            print(f"✓ Control computation successful: {control_output}")

            # Step 4: Test dynamics computation
            print("Step 4: Testing dynamics computation...")
            state_dot = dynamics.dynamics(test_state, control_output)
            simulation_health["steps_completed"] += 1
            simulation_health["test_results"]["dynamics_computation"] = "SUCCESS"
            print(f"✓ Dynamics computation successful: {state_dot.shape}")

            # Step 5: Test integration step
            print("Step 5: Testing integration step...")
            dt = 0.01
            new_state = test_state + dt * state_dot
            simulation_health["steps_completed"] += 1
            simulation_health["test_results"]["integration_step"] = "SUCCESS"
            simulation_health["status"] = "SUCCESS"
            print(f"✓ Integration step successful")

        except Exception as e:
            simulation_health["status"] = "FAILED"
            simulation_health["test_results"]["error"] = str(e)
            print(f"✗ Simulation test failed: {e}")

        sim_score = (simulation_health["steps_completed"] / simulation_health["total_steps"]) * 100
        print(f"\nEnd-to-End Simulation Score: {sim_score:.1f}% ({simulation_health['steps_completed']}/{simulation_health['total_steps']})")

        return simulation_health

    def calculate_overall_health_score(self) -> float:
        """Calculate composite system health score."""
        print("\n" + "=" * 80)
        print("6. OVERALL SYSTEM HEALTH CALCULATION")
        print("=" * 80)

        # Component weights
        weights = {
            "configuration": 0.20,
            "imports": 0.25,
            "controllers": 0.25,
            "dynamics": 0.15,
            "simulation": 0.15
        }

        # Component scores
        scores = {}

        # Configuration score
        config_result = self.results["validation_results"].get("configuration", {})
        if config_result.get("status") == "HEALTHY":
            scores["configuration"] = 100.0
        elif config_result.get("status") == "DEGRADED":
            scores["configuration"] = 60.0  # Degraded but functional
        else:
            scores["configuration"] = 0.0

        # Import score
        import_result = self.results["validation_results"].get("imports", {})
        if import_result.get("total_tested", 0) > 0:
            scores["imports"] = (import_result.get("successful", 0) / import_result.get("total_tested", 1)) * 100
        else:
            scores["imports"] = 0.0

        # Controller score
        controller_result = self.results["validation_results"].get("controllers", {})
        if controller_result.get("total_controllers", 0) > 0:
            scores["controllers"] = (controller_result.get("successful_creation", 0) / controller_result.get("total_controllers", 1)) * 100
        else:
            scores["controllers"] = 0.0

        # Dynamics score
        dynamics_result = self.results["validation_results"].get("dynamics", {})
        if dynamics_result.get("total_models", 0) > 0:
            scores["dynamics"] = (dynamics_result.get("successful_creation", 0) / dynamics_result.get("total_models", 1)) * 100
        else:
            scores["dynamics"] = 0.0

        # Simulation score
        simulation_result = self.results["validation_results"].get("simulation", {})
        if simulation_result.get("total_steps", 0) > 0:
            scores["simulation"] = (simulation_result.get("steps_completed", 0) / simulation_result.get("total_steps", 1)) * 100
        else:
            scores["simulation"] = 0.0

        # Calculate weighted average
        overall_score = sum(scores[component] * weights[component] for component in weights.keys())

        print(f"Component Scores:")
        for component, score in scores.items():
            print(f"  {component.capitalize()}: {score:.1f}% (weight: {weights[component]:.1%})")

        print(f"\nOverall System Health Score: {overall_score:.1f}%")

        # Health assessment
        if overall_score >= 90:
            health_status = "EXCELLENT"
            recommendation = "System ready for production deployment"
        elif overall_score >= 80:
            health_status = "GOOD"
            recommendation = "System ready with minor monitoring"
        elif overall_score >= 70:
            health_status = "FAIR"
            recommendation = "System functional but needs attention"
        elif overall_score >= 60:
            health_status = "DEGRADED"
            recommendation = "System partially functional - address critical issues"
        else:
            health_status = "POOR"
            recommendation = "System requires significant fixes before use"

        print(f"System Health Status: {health_status}")
        print(f"Recommendation: {recommendation}")

        return overall_score

    def run_complete_validation(self) -> Dict[str, Any]:
        """Execute complete system health validation."""
        print("COMPREHENSIVE SYSTEM HEALTH VALIDATION")
        print("DIP_SMC_PSO Project - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("=" * 80)

        # Execute all validation steps
        self.results["validation_results"]["configuration"] = self.validate_configuration_system()
        self.results["validation_results"]["imports"] = self.validate_import_resolution()
        self.results["validation_results"]["controllers"] = self.validate_controller_factory()
        self.results["validation_results"]["dynamics"] = self.validate_dynamics_models()
        self.results["validation_results"]["simulation"] = self.test_end_to_end_simulation()

        # Calculate overall health score
        self.results["overall_health_score"] = self.calculate_overall_health_score()

        # Set configuration health status
        config_result = self.results["validation_results"]["configuration"]
        self.results["configuration_health"] = config_result.get("status", "UNKNOWN")

        # Generate recommendations
        if self.results["overall_health_score"] < 80:
            self.results["recommendations"].append("Address configuration schema validation issues")
        if self.results["validation_results"]["imports"]["failed"] > 0:
            self.results["recommendations"].append("Fix import resolution failures")
        if self.results["validation_results"]["controllers"]["failed_creation"] > 0:
            self.results["recommendations"].append("Resolve controller factory issues")

        return self.results

def main():
    """Main validation execution."""
    validator = SystemHealthValidator()
    results = validator.run_complete_validation()

    # Save results
    output_file = f"system_health_validation_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print(f"Results saved to: {output_file}")
    print(f"Overall Health Score: {results['overall_health_score']:.1f}%")
    print(f"Configuration Status: {results['configuration_health']}")

    return results

if __name__ == "__main__":
    main()