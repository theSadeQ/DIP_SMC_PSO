#!/usr/bin/env python3
"""Phase 3 Integration Validation Test"""

def main():
    print("=== INTEGRATION STABILITY VALIDATION ===")

    # Test 1: Interface consistency
    try:
        from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
        from src.plant.models.full.dynamics import FullDIPDynamics
        from src.plant.models.lowrank.dynamics import LowRankDIPDynamics
        from src.plant import ConfigurationFactory
        import numpy as np

        configs = [
            ConfigurationFactory.create_default_config('simplified'),
            ConfigurationFactory.create_default_config('full'),
            ConfigurationFactory.create_default_config('lowrank')
        ]

        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]
        interface_success = 0

        for i, (cls, config) in enumerate(zip(dynamics_classes, configs)):
            try:
                dynamics = cls(config)
                state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
                control = np.array([1.0])
                result = dynamics.compute_dynamics(state, control, 0.0)
                if result.success:
                    interface_success += 1
                    print(f"PASS {cls.__name__}: Interface stable")
                else:
                    print(f"FAIL {cls.__name__}: Computation failed")
            except Exception as e:
                print(f"FAIL {cls.__name__}: Exception - {e}")

        print(f"Interface Stability: {interface_success}/3 ({interface_success/3*100:.1f}%)")

        # Test 2: Factory stability
        from src.controllers.factory import SMCFactory, SMCType, SMCConfig

        factory_success = 0
        factory_tests = [
            (SMCType.CLASSICAL, [10.0, 5.0, 8.0, 3.0, 15.0, 2.0]),
            (SMCType.ADAPTIVE, [10.0, 5.0, 8.0, 3.0, 2.0])
        ]

        for smc_type, gains in factory_tests:
            try:
                config = SMCConfig(gains=gains, max_force=100.0, dt=0.01)
                controller = SMCFactory.create_controller(smc_type, config)

                # Test control computation
                state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
                control_output = controller.compute_control(state, (), {})
                if hasattr(control_output, 'u'):
                    factory_success += 1
                    print(f"PASS {smc_type.value}: Factory stable")
                else:
                    print(f"FAIL {smc_type.value}: Output format issue")
            except Exception as e:
                print(f"FAIL {smc_type.value}: Factory exception - {e}")

        print(f"Factory Stability: {factory_success}/2 ({factory_success/2*100:.1f}%)")

        # Overall assessment
        overall_health = (interface_success + factory_success) / 5 * 100
        print(f"\nOVERALL INTEGRATION HEALTH: {overall_health:.1f}%")

        if overall_health >= 90:
            print("INTEGRATION AUDIT: PASSED - Foundation repair SUCCESSFUL")
            return True
        else:
            print("INTEGRATION AUDIT: Needs additional work")
            return False

    except Exception as e:
        print(f"CRITICAL ERROR in validation: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)