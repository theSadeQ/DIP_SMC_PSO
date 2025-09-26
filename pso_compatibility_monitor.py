#==========================================================================================\\\
#============================ pso_compatibility_monitor.py ==============================\\\
#==========================================================================================\\\
"""
PSO Parameter Compatibility Monitor for ongoing repair validation.

Quick validation script to monitor PSO-controller parameter passing compatibility
during critical system repairs. Designed for rapid re-validation during interface
standardization work.

Usage:
    python pso_compatibility_monitor.py [controller_type]
    python pso_compatibility_monitor.py --all
"""

import sys
from pathlib import Path
import numpy as np
import traceback

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.config import load_config
    from src.controllers.factory import create_controller, list_available_controllers
    from src.optimizer.pso_optimizer import PSOTuner
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def quick_pso_test(controller_type: str) -> bool:
    """Quick PSO compatibility test for a controller type."""
    try:
        config = load_config("config.yaml", allow_unknown=True)

        # Test controller creation
        controller = create_controller(controller_type, config)

        # Test PSO factory function
        def pso_factory(gains):
            return create_controller(controller_type, config, gains)

        # Test PSO tuner creation
        pso_tuner = PSOTuner(
            controller_factory=pso_factory,
            config=config,
            seed=42
        )

        # Quick fitness test
        default_gains = controller.gains if hasattr(controller, 'gains') else [5.0, 5.0, 5.0, 0.5, 0.5, 0.5]
        test_particles = np.array([default_gains])
        fitness_result = pso_tuner._fitness(test_particles)

        return isinstance(fitness_result, np.ndarray) and len(fitness_result) > 0
    except Exception as e:
        print(f"  FAIL {controller_type}: {e}")
        return False


def main():
    """Main monitoring function."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            controllers = list_available_controllers()
        else:
            controllers = [sys.argv[1]]
    else:
        controllers = list_available_controllers()

    print("PSO Compatibility Monitor")
    print("=" * 40)

    working = []
    failed = []

    for controller_type in controllers:
        print(f"Testing {controller_type}...", end=" ")
        try:
            if quick_pso_test(controller_type):
                print("PASS")
                working.append(controller_type)
            else:
                print("FAIL")
                failed.append(controller_type)
        except Exception as e:
            print(f"ERROR: {e}")
            failed.append(controller_type)

    print("\n" + "=" * 40)
    print(f"Working: {len(working)}/{len(controllers)} ({len(working)/len(controllers)*100:.1f}%)")
    print(f"Failed: {len(failed)}")

    if working:
        print(f"Working: {', '.join(working)}")
    if failed:
        print(f"Failed: {', '.join(failed)}")

    # Return appropriate exit code
    if len(working) == len(controllers):
        print("\nAll controllers PSO-compatible!")
        return 0
    elif len(working) >= len(controllers) * 0.5:
        print(f"\n{len(working)}/{len(controllers)} controllers working (acceptable)")
        return 1
    else:
        print(f"\nOnly {len(working)}/{len(controllers)} controllers working (critical)")
        return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)