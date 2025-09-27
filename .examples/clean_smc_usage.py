#==========================================================================================\\\
#========================== examples/clean_smc_usage.py =============================\\\
#==========================================================================================\\\

"""
Example: Using the Clean SMC Factory Interface

This demonstrates the improved, focused SMC factory optimized for research and PSO tuning.
Shows the difference between the old complex factory and the new clean interface.
"""

import numpy as np
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from controllers import (
    # Clean API - Primary Interface
    SMCType,
    SMCFactory,
    SMCConfig,
    create_smc_for_pso,
    get_gain_bounds_for_pso,
    validate_smc_gains,

    # Convenience functions
    create_all_smc_controllers,
    get_all_gain_bounds,

    # Direct controller access
    ClassicalSMC
)

def demonstrate_clean_api():
    """Demonstrate the clean SMC factory API."""

    print("🧪 CLEAN SMC FACTORY DEMONSTRATION")
    print("=" * 60)

    # ========================================================================
    # METHOD 1: PSO-Optimized Creation (RECOMMENDED FOR RESEARCH)
    # ========================================================================
    print("\n1️⃣  PSO-Optimized Controller Creation")
    print("-" * 40)

    # Example gains for each controller type
    gains_classical = [10.0, 8.0, 15.0, 12.0, 50.0, 5.0]  # [k1, k2, lam1, lam2, K, kd]
    gains_adaptive = [10.0, 8.0, 15.0, 12.0, 0.5]         # [k1, k2, lam1, lam2, gamma]
    gains_sta = [25.0, 10.0, 15.0, 12.0, 20.0, 15.0]      # [K1, K2, k1, k2, lam1, lam2]
    gains_hybrid = [15.0, 12.0, 18.0, 15.0]               # [c1, lambda1, c2, lambda2]

    # Create controllers using PSO-optimized function
    classical = create_smc_for_pso(SMCType.CLASSICAL, gains_classical, max_force=100.0)
    adaptive = create_smc_for_pso(SMCType.ADAPTIVE, gains_adaptive, max_force=100.0)
    sta = create_smc_for_pso(SMCType.SUPER_TWISTING, gains_sta, max_force=100.0)
    hybrid = create_smc_for_pso(SMCType.HYBRID, gains_hybrid, max_force=100.0)

    print(f"✅ Created Classical SMC: {type(classical).__name__}")
    print(f"✅ Created Adaptive SMC:  {type(adaptive).__name__}")
    print(f"✅ Created STA SMC:       {type(sta).__name__}")
    print(f"✅ Created Hybrid SMC:    {type(hybrid).__name__}")

    # ========================================================================
    # METHOD 2: Factory with Clean Configuration
    # ========================================================================
    print("\n2️⃣  Factory with Clean Configuration")
    print("-" * 40)

    # Create configuration object with validation
    config = SMCConfig(
        gains=gains_classical,
        max_force=100.0,
        dt=0.01,
        boundary_layer=0.01
    )

    # Create controller using factory
    controller = SMCFactory.create_controller(SMCType.CLASSICAL, config)
    print(f"✅ Created via factory: {type(controller).__name__}")
    print(f"   Gains: {controller.gains}")

    # ========================================================================
    # METHOD 3: Batch Creation for Comparison Studies
    # ========================================================================
    print("\n3️⃣  Batch Creation for Comparison Studies")
    print("-" * 40)

    gains_dict = {
        "classical": gains_classical,
        "adaptive": gains_adaptive,
        "sta": gains_sta,
        "hybrid": gains_hybrid
    }

    controllers = create_all_smc_controllers(gains_dict, max_force=100.0)

    for name, ctrl in controllers.items():
        print(f"✅ {name}: {type(ctrl).__name__}")

    # ========================================================================
    # METHOD 4: PSO Integration Features
    # ========================================================================
    print("\n4️⃣  PSO Integration Features")
    print("-" * 40)

    # Get gain bounds for PSO optimization
    all_bounds = get_all_gain_bounds()

    for ctrl_type, bounds in all_bounds.items():
        print(f"📊 {ctrl_type.upper()} bounds: {len(bounds)} parameters")
        for i, (low, high) in enumerate(bounds):
            print(f"   Param {i+1}: [{low:.1f}, {high:.1f}]")

    # Validate gains before creating controllers
    print("\n🔍 Gain Validation:")
    test_gains = [10.0, 8.0, 15.0, 12.0, 50.0, 5.0]

    for smc_type in [SMCType.CLASSICAL, SMCType.ADAPTIVE, SMCType.SUPER_TWISTING, SMCType.HYBRID]:
        is_valid = validate_smc_gains(smc_type, test_gains)
        status = "✅ Valid" if is_valid else "❌ Invalid"
        print(f"   {smc_type.value}: {status}")

    # ========================================================================
    # METHOD 5: Direct Controller Usage (unchanged)
    # ========================================================================
    print("\n5️⃣  Direct Controller Usage")
    print("-" * 40)

    # You can still use controllers directly if needed
    direct_controller = ClassicalSMC(
        gains=gains_classical,
        max_force=100.0,
        boundary_layer=0.01
    )
    print(f"✅ Direct creation: {type(direct_controller).__name__}")

def demonstrate_pso_workflow():
    """Demonstrate typical PSO optimization workflow."""

    print("\n\n🔬 PSO OPTIMIZATION WORKFLOW EXAMPLE")
    print("=" * 60)

    def fitness_function(gains_array: np.ndarray, controller_type: str) -> float:
        """
        Example fitness function for PSO optimization.

        In real usage, this would:
        1. Create controller with gains
        2. Run simulation scenarios
        3. Evaluate performance metrics
        4. Return fitness score
        """
        try:
            # Validate gains
            if not validate_smc_gains(controller_type, gains_array):
                return float('inf')  # Invalid gains get worst fitness

            # Create controller
            controller = create_smc_for_pso(
                smc_type=controller_type,
                gains=gains_array,
                max_force=100.0,
                dt=0.01
            )

            # Simulate dummy test scenario
            test_state = np.array([0.1, 0.2, -0.15, 0.0, 0.1, -0.05])

            # Get controller initial state and history
            state_vars = controller.initialize_state()
            history = controller.initialize_history()

            # Compute control (this would be in a simulation loop)
            result = controller.compute_control(test_state, state_vars, history)

            # Extract control value (format depends on controller)
            if hasattr(result, 'u'):
                control_effort = abs(result.u)
            elif isinstance(result, tuple):
                control_effort = abs(result[0])
            else:
                control_effort = abs(float(result))

            # Return negative control effort as fitness (minimize effort)
            return control_effort

        except Exception as e:
            print(f"⚠️  Error in fitness function: {e}")
            return float('inf')

    # Example PSO optimization for Classical SMC
    print("🎯 Example: PSO optimization for Classical SMC")
    print("-" * 50)

    # Get bounds for Classical SMC
    bounds = get_gain_bounds_for_pso(SMCType.CLASSICAL)
    print(f"📊 Optimizing {len(bounds)} parameters with bounds:")
    for i, (low, high) in enumerate(bounds):
        print(f"   Param {i+1}: [{low:.1f}, {high:.1f}]")

    # Simulate PSO population
    population_size = 5
    print(f"\n🧬 Testing {population_size} candidate solutions:")

    for i in range(population_size):
        # Generate random gains within bounds
        gains = []
        for low, high in bounds:
            gains.append(np.random.uniform(low, high))

        # Evaluate fitness
        fitness = fitness_function(np.array(gains), SMCType.CLASSICAL)

        print(f"   Candidate {i+1}: fitness = {fitness:.3f}")

    print("\n✨ In real PSO, this process would continue until convergence!")

if __name__ == "__main__":
    demonstrate_clean_api()
    demonstrate_pso_workflow()

    print("\n\n🎉 CLEAN SMC FACTORY BENEFITS:")
    print("=" * 60)
    print("✅ Focused on 4 SMC controllers only")
    print("✅ Type-safe with clear interfaces")
    print("✅ PSO-optimized convenience functions")
    print("✅ Unified parameter validation")
    print("✅ Clean separation of concerns")
    print("✅ Research-ready with gain bounds")
    print("✅ Backward compatible when needed")
    print("\n🚀 Ready for serious SMC research and PSO optimization!")