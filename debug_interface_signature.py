#!/usr/bin/env python3
"""Debug interface signature issues"""

import sys
import inspect
from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
from src.plant.models.full.dynamics import FullDIPDynamics
from src.plant.models.lowrank.dynamics import LowRankDIPDynamics
from src.plant.models.base.dynamics_interface import BaseDynamicsModel
from src.plant import ConfigurationFactory

def test_signatures():
    print("=== INTERFACE SIGNATURE DEBUG ===")

    # Get configs
    simplified_config = ConfigurationFactory.create_default_config("simplified")
    full_config = ConfigurationFactory.create_default_config("full")
    lowrank_config = ConfigurationFactory.create_default_config("lowrank")

    # Create instances
    dynamics_instances = [
        SimplifiedDIPDynamics(simplified_config),
        FullDIPDynamics(full_config),
        LowRankDIPDynamics(lowrank_config)
    ]

    # Get reference signature
    base_signature = inspect.signature(BaseDynamicsModel.compute_dynamics)
    print(f"Base signature: {base_signature}")
    base_params = list(base_signature.parameters.keys())[1:]  # Skip 'self'
    print(f"Base params: {base_params}")

    # Test each instance
    for dynamics in dynamics_instances:
        method_signature = inspect.signature(dynamics.compute_dynamics)
        method_params = list(method_signature.parameters.keys())  # Already bound, no self

        print(f"\n{dynamics.__class__.__name__}:")
        print(f"  Signature: {method_signature}")
        print(f"  Params: {method_params}")
        print(f"  Match: {base_params == method_params}")

        if base_params != method_params:
            print(f"  ERROR: Expected {base_params}, got {method_params}")
            return False

    print("\n✅ ALL SIGNATURES MATCH!")
    return True

if __name__ == "__main__":
    success = test_signatures()
    sys.exit(0 if success else 1)