# Create and run this validation
from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
from src.plant.models.full.dynamics import FullDIPDynamics
from src.plant.models.lowrank.dynamics import LowRankDIPDynamics
from src.controllers.factory import SMCFactory, SMCType, SMCConfig
from src.plant import ConfigurationFactory
import numpy as np

def comprehensive_health_check():
    """Comprehensive system health validation"""
    results = {
        'interface_tests': 0,
        'factory_tests': 0,
        'integration_tests': 0,
        'total_score': 0
    }

    print("=== COMPREHENSIVE HEALTH CHECK ===")

    # Test 1: Interface signature consistency
    try:
        configs = [
            ConfigurationFactory.create_default_config('simplified'),
            ConfigurationFactory.create_default_config('full'),
            ConfigurationFactory.create_default_config('lowrank')
        ]

        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]

        for cls, config in zip(dynamics_classes, configs):
            dynamics = cls(config)
            state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
            control = np.array([1.0])
            result = dynamics.compute_dynamics(state, control, 0.0, test_param="validation")

            if result.success:
                results['interface_tests'] += 1

        print(f"Interface Health: {results['interface_tests']}/3")
    except Exception as e:
        print(f"Interface Test Error: {e}")

    # Test 2: Factory stability and thread safety
    try:
        factory_tests = [
            (SMCType.CLASSICAL, [10.0, 5.0, 8.0, 3.0, 15.0, 2.0]),
            (SMCType.ADAPTIVE, [10.0, 5.0, 8.0, 3.0, 2.0])
        ]

        for smc_type, gains in factory_tests:
            config = SMCConfig(gains=gains, max_force=100.0, dt=0.01)
            controller = SMCFactory.create_controller(smc_type, config)

            # Test control computation
            state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
            control_output = controller.compute_control(state, (), {})

            if hasattr(control_output, 'u'):
                results['factory_tests'] += 1

        print(f"Factory Health: {results['factory_tests']}/2")
    except Exception as e:
        print(f"Factory Test Error: {e}")

    # Test 3: Multi-threaded stability
    try:
        import threading
        thread_results = []

        def threaded_test():
            try:
                config = SMCConfig(gains=[10.0, 5.0, 8.0, 3.0, 15.0, 2.0], max_force=100.0)
                controller = SMCFactory.create_controller(SMCType.CLASSICAL, config)
                thread_results.append(controller is not None)
            except:
                thread_results.append(False)

        threads = [threading.Thread(target=threaded_test) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if all(thread_results):
            results['integration_tests'] = 1

        print(f"Thread Safety: {results['integration_tests']}/1")
    except Exception as e:
        print(f"Thread Safety Error: {e}")

    # Calculate overall health
    total_possible = 6  # 3 + 2 + 1
    total_actual = sum(results.values())
    health_percentage = (total_actual / total_possible) * 100

    print(f"\n=== OVERALL SYSTEM HEALTH: {health_percentage:.1f}% ===")

    return health_percentage >= 95

# Run the check
if __name__ == "__main__":
    health_passed = comprehensive_health_check()
    print(f"\nHealth Check: {'PASSED' if health_passed else 'FAILED'}")