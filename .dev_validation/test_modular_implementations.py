#==========================================================================================\\\
#========================= test_modular_implementations.py ===============================\\\
#==========================================================================================\\\

"""
Test script for all modular DIP implementations.

Tests the complete modular architecture including:
- Configuration system
- Physics computers
- Dynamics models
- Integration with unified configuration
"""

import numpy as np
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_configurations():
    """Test all configuration classes."""
    print("Testing Configuration System...")

    try:
        from plant.configurations import (
            ConfigurationFactory,
            UnifiedConfiguration,
            DIPModelType,
            BaseDIPConfig
        )

        # Test factory pattern
        print("  + Testing configuration factory...")

        # Test default configurations
        simplified_config = ConfigurationFactory.create_default_config(DIPModelType.SIMPLIFIED)
        print(f"    + Simplified config created: {type(simplified_config).__name__}")

        full_config = ConfigurationFactory.create_default_config(DIPModelType.FULL)
        print(f"    + Full config created: {type(full_config).__name__}")

        lowrank_config = ConfigurationFactory.create_default_config(DIPModelType.LOWRANK)
        print(f"    + Low-rank config created: {type(lowrank_config).__name__}")

        # Test preset configurations
        print("  + Testing preset configurations...")

        # Test available presets
        simplified_presets = ConfigurationFactory.get_available_presets("simplified")
        print(f"    + Simplified presets: {simplified_presets}")

        full_presets = ConfigurationFactory.get_available_presets("full")
        print(f"    + Full presets: {full_presets}")

        lowrank_presets = ConfigurationFactory.get_available_presets("lowrank")
        print(f"    + Low-rank presets: {lowrank_presets}")

        # Test unified configuration
        print("  + Testing unified configuration...")
        full_config_dict = {
            'cart_mass': 2.0,
            'pendulum1_mass': 0.1,
            'pendulum2_mass': 0.1,
            'pendulum1_length': 0.5,
            'pendulum2_length': 0.5,
            'pendulum1_com': 0.25,
            'pendulum2_com': 0.25,
            'pendulum1_inertia': 0.01,
            'pendulum2_inertia': 0.01
        }
        unified_config = UnifiedConfiguration("full", full_config_dict)
        validation = unified_config.validate()
        print(f"    + Unified config validation: {validation['is_valid']}")

        print("Configuration System: PASSED\n")
        return True

    except Exception as e:
        print(f"Configuration System: FAILED - {e}\n")
        return False

def test_physics_computers():
    """Test all physics computer implementations."""
    print("Testing Physics Computers...")

    try:
        from plant.models.simplified import SimplifiedPhysicsComputer, SimplifiedDIPConfig
        from plant.models.full import FullFidelityPhysicsComputer, FullDIPConfig
        from plant.models.lowrank import LowRankPhysicsComputer, LowRankDIPConfig

        # Test state
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
        control_input = np.array([1.0])

        # Test simplified physics
        print("  + Testing simplified physics computer...")
        simplified_config = SimplifiedDIPConfig.create_default()
        simplified_physics = SimplifiedPhysicsComputer(simplified_config)

        simplified_result = simplified_physics.compute_dynamics_rhs(state, control_input)
        print(f"    + Simplified dynamics computed: shape {simplified_result.shape}")

        # Test full physics
        print("  + Testing full physics computer...")
        # Create a minimal full config for testing
        full_config = FullDIPConfig(
            cart_mass=1.0,
            pendulum1_mass=0.1,
            pendulum2_mass=0.1,
            pendulum1_length=0.5,
            pendulum2_length=0.5,
            pendulum1_com=0.25,
            pendulum2_com=0.25,
            pendulum1_inertia=0.01,
            pendulum2_inertia=0.01
        )
        full_physics = FullFidelityPhysicsComputer(full_config)

        full_result = full_physics.compute_complete_dynamics_rhs(state, control_input, 0.0)
        print(f"    + Full dynamics computed: shape {full_result.shape}")

        # Test low-rank physics
        print("  + Testing low-rank physics computer...")
        lowrank_config = LowRankDIPConfig.create_default()
        lowrank_physics = LowRankPhysicsComputer(lowrank_config)

        lowrank_result = lowrank_physics.compute_simplified_dynamics_rhs(state, control_input)
        print(f"    + Low-rank dynamics computed: shape {lowrank_result.shape}")

        print("Physics Computers: PASSED\n")
        return True

    except Exception as e:
        print(f"Physics Computers: FAILED - {e}\n")
        import traceback
        traceback.print_exc()
        return False

def test_dynamics_models():
    """Test all dynamics model implementations."""
    print("Testing Dynamics Models...")

    try:
        from plant.models.simplified import SimplifiedDIPDynamics, SimplifiedDIPConfig
        from plant.models.full import FullDIPDynamics, FullDIPConfig
        from plant.models.lowrank import LowRankDIPDynamics, LowRankDIPConfig

        # Test state
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
        control_input = np.array([1.0])

        # Test simplified dynamics
        print("  + Testing simplified dynamics model...")
        simplified_config = SimplifiedDIPConfig.create_default()
        simplified_dynamics = SimplifiedDIPDynamics(simplified_config)

        result = simplified_dynamics.compute_dynamics(state, control_input)
        print(f"    + Simplified dynamics result: success={result.success}")

        # Test full dynamics
        print("  + Testing full dynamics model...")
        full_config = FullDIPConfig(
            cart_mass=1.0,
            pendulum1_mass=0.1,
            pendulum2_mass=0.1,
            pendulum1_length=0.5,
            pendulum2_length=0.5,
            pendulum1_com=0.25,
            pendulum2_com=0.25,
            pendulum1_inertia=0.01,
            pendulum2_inertia=0.01
        )
        full_dynamics = FullDIPDynamics(full_config)

        result = full_dynamics.compute_dynamics(state, control_input)
        print(f"    + Full dynamics result: success={result.success}")

        # Test low-rank dynamics
        print("  + Testing low-rank dynamics model...")
        lowrank_config = LowRankDIPConfig.create_default()
        lowrank_dynamics = LowRankDIPDynamics(lowrank_config)

        result = lowrank_dynamics.compute_dynamics(state, control_input)
        print(f"    + Low-rank dynamics result: success={result.success}")

        print("Dynamics Models: PASSED\n")
        return True

    except Exception as e:
        print(f"Dynamics Models: FAILED - {e}\n")
        import traceback
        traceback.print_exc()
        return False

def test_plant_package_imports():
    """Test main plant package imports."""
    print("Testing Plant Package Imports...")

    try:
        # Test main package imports
        from plant import (
            DoubleInvertedPendulum,
            SimplifiedDIPDynamics,
            FullDIPDynamics,
            LowRankDIPDynamics,
            ConfigurationFactory,
            UnifiedConfiguration,
            DIPModelType
        )

        print("  + All main imports successful")

        # Test that we can create instances
        from plant.models.simplified import SimplifiedDIPConfig
        config = SimplifiedDIPConfig.create_default()
        simplified = DoubleInvertedPendulum(config)  # Should be SimplifiedDIPDynamics
        print(f"    + Default dynamics created: {type(simplified).__name__}")

        # Test configuration factory through main package
        config = ConfigurationFactory.create_default_config("simplified")
        print(f"    + Configuration created through main package: {type(config).__name__}")

        print("Plant Package Imports: PASSED\n")
        return True

    except Exception as e:
        print(f"Plant Package Imports: FAILED - {e}\n")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test integration between components."""
    print("Testing Component Integration...")

    try:
        from plant.configurations import ConfigurationFactory, DIPModelType
        from plant.models.simplified import SimplifiedDIPDynamics
        from plant.models.full import FullDIPDynamics
        from plant.models.lowrank import LowRankDIPDynamics

        # Test integration with different configurations
        print("  + Testing configuration-dynamics integration...")

        # Test each model type with factory-created configs
        model_types = [
            ("simplified", SimplifiedDIPDynamics),
            ("full", FullDIPDynamics),
            ("lowrank", LowRankDIPDynamics)
        ]

        state = np.array([0.0, 0.1, -0.1, 0.0, 0.0, 0.0])
        control_input = np.array([0.5])

        for model_name, model_class in model_types:
            config = ConfigurationFactory.create_default_config(model_name)

            if model_name == "full":
                # Full model needs additional parameters
                config = ConfigurationFactory.create_config(model_name, {
                    'cart_mass': 1.0,
                    'pendulum1_mass': 0.1,
                    'pendulum2_mass': 0.1,
                    'pendulum1_length': 0.5,
                    'pendulum2_length': 0.5,
                    'pendulum1_com': 0.25,
                    'pendulum2_com': 0.25,
                    'pendulum1_inertia': 0.01,
                    'pendulum2_inertia': 0.01
                })

            dynamics = model_class(config)
            result = dynamics.compute_dynamics(state, control_input)

            print(f"    + {model_name.capitalize()} integration: success={result.success}")

        print("Component Integration: PASSED\n")
        return True

    except Exception as e:
        print(f"Component Integration: FAILED - {e}\n")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Starting Modular DIP Implementation Tests\n")
    print("=" * 60)

    test_results = []

    # Run all test suites
    test_results.append(test_configurations())
    test_results.append(test_physics_computers())
    test_results.append(test_dynamics_models())
    test_results.append(test_plant_package_imports())
    test_results.append(test_integration())

    # Summary
    print("=" * 60)
    passed = sum(test_results)
    total = len(test_results)

    if passed == total:
        print(f"ALL TESTS PASSED ({passed}/{total})")
        print("\nModular DIP implementation is working correctly!")
        return True
    else:
        print(f"SOME TESTS FAILED ({passed}/{total} passed)")
        failed = total - passed
        print(f"\n{failed} test suite(s) failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)