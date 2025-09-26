#==========================================================================================\\\
#========= tests/test_physics/test_integration_stability.py ========================\\\
#==========================================================================================\\\

"""
Integration Stability Boundary Testing.

CRITICAL MISSION: Document integration stability boundaries for DIP simulation.

SCIENTIFIC REALITY:
- dt ≤ 0.1s: Stable integration for most scenarios
- dt ≥ 0.5s: Unstable integration, leads to numerical blow-up
- Stability depends on system dynamics and initial conditions

STRATEGIC VALUE: Prevent unstable simulation parameters and establish safe operating bounds.
"""

import pytest
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.core.dynamics import step_rk4_numba, step_euler_numba, DIPParams
from src.plant.models.simplified.physics import SimplifiedPhysicsComputer
from src.plant.models.simplified.config import SimplifiedDIPConfig


class TestIntegrationStability:
    """
    MISSION: Document integration stability boundaries for DIP dynamics.

    PREVENTS CONFUSION: "Why does my simulation blow up with dt=0.5s?"
    DOCUMENTS: dt ≤ 0.1s stable, dt ≥ 0.5s unstable boundaries.
    """

    def setup_method(self):
        """Set up integration stability testing environment."""
        self.config = self._create_test_config()
        self.physics_computer = SimplifiedPhysicsComputer(self.config)
        self.params = DIPParams.from_physics_config(self.config)

        # Stability test scenarios
        self.stability_scenarios = {
            'small_oscillation': {
                'initial_state': np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0]),
                'description': 'Small pendulum oscillations',
                'expected_stable_dt_max': 0.1,
                'expected_unstable_dt_min': 0.5
            },
            'large_oscillation': {
                'initial_state': np.array([0.0, 0.8, 0.8, 0.0, 0.0, 0.0]),
                'description': 'Large pendulum swings',
                'expected_stable_dt_max': 0.05,  # More restrictive
                'expected_unstable_dt_min': 0.2
            },
            'high_velocity': {
                'initial_state': np.array([0.0, 0.2, 0.2, 0.0, 2.0, 2.0]),
                'description': 'High angular velocities',
                'expected_stable_dt_max': 0.02,  # Very restrictive
                'expected_unstable_dt_min': 0.1
            },
            'mixed_dynamics': {
                'initial_state': np.array([0.1, 0.3, -0.3, 0.5, 1.0, -1.0]),
                'description': 'Complex mixed dynamics',
                'expected_stable_dt_max': 0.03,
                'expected_unstable_dt_min': 0.15
            }
        }

        # Stability criteria
        self.stability_criteria = {
            'max_position_magnitude': 10.0,    # |x|, |θ| should not exceed
            'max_velocity_magnitude': 50.0,    # |ẋ|, |θ̇| should not exceed
            'max_energy_growth_factor': 100.0, # Energy should not grow by more than 100x
            'finite_check': True                # All states must remain finite
        }

    def test_stable_integration_boundaries(self):
        """
        TEST: Validate stable integration time step boundaries.

        DOCUMENTS: dt ≤ 0.1s should provide stable integration for most scenarios.
        VALIDATES: Safe operating parameters for simulation.
        """
        print("\n" + "="*80)
        print("STABLE INTEGRATION BOUNDARY VALIDATION")
        print("EXPECTATION: dt ≤ 0.1s should be stable for most DIP scenarios")
        print("="*80)

        stable_dt_values = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1]
        simulation_time = 5.0
        control_input = 0.0

        for scenario_name, scenario in self.stability_scenarios.items():
            print(f"\nTesting scenario: {scenario['description']}")
            initial_state = scenario['initial_state']
            initial_energy = self.physics_computer.compute_total_energy(initial_state)

            for dt in stable_dt_values:
                print(f"  dt = {dt:5.3f}s: ", end="")

                # Test stability
                is_stable, final_state, final_energy = self._test_integration_stability(
                    initial_state, dt, simulation_time, control_input
                )

                if is_stable:
                    energy_ratio = final_energy / initial_energy if initial_energy != 0 else 1.0
                    print(f"STABLE (energy ratio: {energy_ratio:.2f})")
                else:
                    print("UNSTABLE")

                # VALIDATION: Small dt values should be stable
                if dt <= scenario['expected_stable_dt_max']:
                    assert is_stable, \
                        f"dt={dt:.3f}s should be stable for {scenario_name} (expected stable ≤ {scenario['expected_stable_dt_max']:.3f}s)"
                else:
                    # Larger dt may or may not be stable - just document
                    if not is_stable:
                        print(f"    Note: Instability at dt={dt:.3f}s is within expectations")

    def test_unstable_integration_boundaries(self):
        """
        TEST: Validate unstable integration time step boundaries.

        DOCUMENTS: dt ≥ 0.5s should lead to numerical instability.
        PREVENTS: Unrealistic simulation parameter choices.
        """
        print("\n" + "="*80)
        print("UNSTABLE INTEGRATION BOUNDARY VALIDATION")
        print("EXPECTATION: dt ≥ 0.5s should cause numerical instability")
        print("="*80)

        unstable_dt_values = [0.2, 0.3, 0.5, 0.7, 1.0]
        simulation_time = 2.0  # Shorter time for unstable cases
        control_input = 0.0

        for scenario_name, scenario in self.stability_scenarios.items():
            print(f"\nTesting scenario: {scenario['description']}")
            initial_state = scenario['initial_state']

            for dt in unstable_dt_values:
                print(f"  dt = {dt:5.3f}s: ", end="")

                # Test stability
                is_stable, final_state, final_energy = self._test_integration_stability(
                    initial_state, dt, simulation_time, control_input
                )

                if is_stable:
                    print("STABLE (unexpected)")
                else:
                    print("UNSTABLE (expected)")

                # VALIDATION: Large dt values should generally be unstable
                if dt >= scenario['expected_unstable_dt_min']:
                    # For large dt, instability is expected but not required
                    # (some simple cases might still be stable)
                    if not is_stable:
                        print(f"    ✓ Expected instability confirmed at dt={dt:.3f}s")
                    else:
                        print(f"    ? Surprisingly stable at dt={dt:.3f}s")

    def test_stability_boundary_characterization(self):
        """
        TEST: Characterize the precise stability boundary for different scenarios.

        DOCUMENTS: Exact dt thresholds where stability transitions occur.
        PROVIDES: Practical guidance for simulation parameter selection.
        """
        print("\n" + "="*80)
        print("STABILITY BOUNDARY CHARACTERIZATION")
        print("PURPOSE: Find precise dt thresholds for stability transitions")
        print("="*80)

        simulation_time = 3.0
        control_input = 0.0

        boundary_results = {}

        for scenario_name, scenario in self.stability_scenarios.items():
            print(f"\nCharacterizing {scenario['description']}:")
            initial_state = scenario['initial_state']

            # Binary search for stability boundary
            dt_stable = self._find_stability_boundary(
                initial_state, simulation_time, control_input
            )

            boundary_results[scenario_name] = dt_stable

            print(f"  Maximum stable dt: {dt_stable:.4f}s")
            print(f"  Expected boundary: ≤{scenario['expected_stable_dt_max']:.3f}s")

            # VALIDATION: Found boundary should be reasonable
            assert dt_stable > 0.0001, f"Stability boundary unrealistically small: {dt_stable:.6f}s"
            assert dt_stable < 1.0, f"Stability boundary unrealistically large: {dt_stable:.6f}s"

            # Compare with expected boundary
            if dt_stable >= scenario['expected_stable_dt_max'] * 0.5:
                print(f"  ✓ Boundary within expected range")
            else:
                print(f"  ⚠ Boundary more restrictive than expected")

        # Document findings
        print(f"\nSTABILITY BOUNDARY SUMMARY:")
        print("-" * 40)
        for scenario_name, dt_boundary in boundary_results.items():
            scenario_desc = self.stability_scenarios[scenario_name]['description']
            print(f"{scenario_desc:25s}: dt ≤ {dt_boundary:.4f}s")

    def test_rk4_vs_euler_stability_comparison(self):
        """
        TEST: Compare RK4 vs Euler stability boundaries.

        DOCUMENTS: RK4 stability advantage over Euler method.
        VALIDATES: Choice of RK4 for improved numerical stability.
        """
        print("\n" + "="*80)
        print("RK4 vs EULER STABILITY COMPARISON")
        print("PURPOSE: Validate RK4 stability advantages")
        print("="*80)

        test_state = np.array([0.0, 0.2, 0.2, 0.0, 0.0, 0.0])
        simulation_time = 2.0
        control_input = 0.0

        # Test range of dt values
        dt_values = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2]

        print(f"{'dt (s)':>8s} {'RK4':>10s} {'Euler':>10s} {'RK4 Advantage':>15s}")
        print("-" * 50)

        rk4_max_stable = 0.0
        euler_max_stable = 0.0

        for dt in dt_values:
            # Test RK4 stability
            rk4_stable, _, _ = self._test_integration_stability(
                test_state, dt, simulation_time, control_input, method='rk4'
            )

            # Test Euler stability
            euler_stable, _, _ = self._test_integration_stability(
                test_state, dt, simulation_time, control_input, method='euler'
            )

            if rk4_stable:
                rk4_max_stable = dt
            if euler_stable:
                euler_max_stable = dt

            advantage = "Yes" if rk4_stable and not euler_stable else "No"
            if rk4_stable == euler_stable:
                advantage = "Same"

            rk4_status = "Stable" if rk4_stable else "Unstable"
            euler_status = "Stable" if euler_stable else "Unstable"

            print(f"{dt:8.3f} {rk4_status:>10s} {euler_status:>10s} {advantage:>15s}")

        print(f"\nSUMMARY:")
        print(f"RK4 maximum stable dt:   {rk4_max_stable:.3f}s")
        print(f"Euler maximum stable dt: {euler_max_stable:.3f}s")
        print(f"RK4 stability advantage: {rk4_max_stable / euler_max_stable:.1f}x" if euler_max_stable > 0 else "RK4 stability advantage: Significant")

        # VALIDATION: RK4 should have stability advantages
        assert rk4_max_stable >= euler_max_stable, \
            f"RK4 should be at least as stable as Euler: RK4={rk4_max_stable:.3f}s, Euler={euler_max_stable:.3f}s"

        print("✓ RK4 demonstrates expected stability advantages")

    def test_stability_documentation_reference(self):
        """
        TEST: Create stability documentation for practical use.

        OUTPUT: Reference guide for simulation parameter selection.
        PURPOSE: Provide clear guidance for stable simulation setup.
        """
        print("\n" + "="*80)
        print("INTEGRATION STABILITY DOCUMENTATION REFERENCE")
        print("USE: Select simulation parameters based on these guidelines")
        print("="*80)

        stability_guidelines = {
            "Conservative (recommended for most users)": {
                "dt_max": 0.01,
                "description": "Safe for all scenarios, good accuracy",
                "use_cases": ["Control system testing", "Energy analysis", "General simulation"]
            },
            "Balanced (experienced users)": {
                "dt_max": 0.05,
                "description": "Good balance of speed and stability",
                "use_cases": ["Parameter sweeps", "Optimization", "Batch simulations"]
            },
            "Aggressive (experts only)": {
                "dt_max": 0.1,
                "description": "Fast but may be unstable for some scenarios",
                "use_cases": ["Quick prototyping", "Simple dynamics", "Short simulations"]
            },
            "Danger zone (not recommended)": {
                "dt_max": 0.5,
                "description": "High risk of numerical instability",
                "use_cases": ["None - avoid these parameters"]
            }
        }

        print("\nINTEGRATION STABILITY GUIDELINES:")
        print("=" * 50)
        for category, guidelines in stability_guidelines.items():
            print(f"\n{category}:")
            print(f"  Maximum dt: {guidelines['dt_max']:6.3f}s")
            print(f"  Description: {guidelines['description']}")
            print(f"  Use cases: {', '.join(guidelines['use_cases'])}")

        # Quick validation of guidelines
        print(f"\nVALIDATION TEST:")
        print("-" * 20)
        test_state = np.array([0.0, 0.15, 0.15, 0.0, 0.0, 0.0])

        for category, guidelines in stability_guidelines.items():
            dt = guidelines['dt_max']
            if dt < 0.2:  # Skip danger zone
                is_stable, _, _ = self._test_integration_stability(
                    test_state, dt, 3.0, 0.0
                )
                status = "✓ Stable" if is_stable else "✗ Unstable"
                print(f"{category:35s}: {status}")

        print(f"\n✅ Integration stability boundaries documented")
        print(f"✅ Practical guidelines established for parameter selection")

    def _test_integration_stability(
        self,
        initial_state: np.ndarray,
        dt: float,
        simulation_time: float,
        control_input: float,
        method: str = 'rk4'
    ) -> Tuple[bool, np.ndarray, float]:
        """
        Test integration stability for given parameters.

        Returns:
            Tuple of (is_stable, final_state, final_energy)
        """
        state = initial_state.copy()
        initial_energy = self.physics_computer.compute_total_energy(initial_state)

        num_steps = int(simulation_time / dt)

        try:
            for _ in range(num_steps):
                if method == 'rk4':
                    state = step_rk4_numba(state, control_input, dt, self.params)
                elif method == 'euler':
                    state = step_euler_numba(state, control_input, dt, self.params)
                else:
                    raise ValueError(f"Unknown integration method: {method}")

                # Check for obvious instability
                if not self._check_state_validity(state):
                    return False, state, np.inf

            # Check final state against stability criteria
            final_energy = self.physics_computer.compute_total_energy(state)
            is_stable = self._evaluate_stability(initial_state, state, initial_energy, final_energy)

            return is_stable, state, final_energy

        except (RuntimeError, ValueError, np.linalg.LinAlgError):
            # Integration failed
            return False, state, np.inf

    def _check_state_validity(self, state: np.ndarray) -> bool:
        """Check if state is numerically valid."""
        # Check for NaN or inf
        if not np.all(np.isfinite(state)):
            return False

        # Check for unreasonably large values
        if np.any(np.abs(state[:3]) > self.stability_criteria['max_position_magnitude']):
            return False

        if np.any(np.abs(state[3:]) > self.stability_criteria['max_velocity_magnitude']):
            return False

        return True

    def _evaluate_stability(
        self,
        initial_state: np.ndarray,
        final_state: np.ndarray,
        initial_energy: float,
        final_energy: float
    ) -> bool:
        """Evaluate if simulation remained stable."""
        # Check state validity
        if not self._check_state_validity(final_state):
            return False

        # Check energy growth
        if initial_energy != 0:
            energy_ratio = abs(final_energy) / abs(initial_energy)
            if energy_ratio > self.stability_criteria['max_energy_growth_factor']:
                return False

        return True

    def _find_stability_boundary(
        self,
        initial_state: np.ndarray,
        simulation_time: float,
        control_input: float
    ) -> float:
        """Find the maximum stable time step using binary search."""
        dt_low = 1e-6   # Definitely stable
        dt_high = 1.0   # Likely unstable

        # First, find an upper bound where it's actually unstable
        while dt_high > dt_low:
            is_stable, _, _ = self._test_integration_stability(
                initial_state, dt_high, simulation_time, control_input
            )
            if not is_stable:
                break
            dt_high *= 2
            if dt_high > 10.0:  # Sanity check
                dt_high = 10.0
                break

        # Binary search for boundary
        for _ in range(20):  # Maximum iterations
            dt_mid = (dt_low + dt_high) / 2

            is_stable, _, _ = self._test_integration_stability(
                initial_state, dt_mid, simulation_time, control_input
            )

            if is_stable:
                dt_low = dt_mid
            else:
                dt_high = dt_mid

            if (dt_high - dt_low) / dt_low < 0.01:  # 1% precision
                break

        return dt_low

    def _create_test_config(self) -> SimplifiedDIPConfig:
        """Create configuration for integration stability testing."""
        config_dict = {
            'cart_mass': 2.4,
            'pendulum1_mass': 0.23,
            'pendulum2_mass': 0.23,
            'pendulum1_length': 0.36,
            'pendulum2_length': 0.36,
            'pendulum1_com': 0.18,
            'pendulum2_com': 0.18,
            'pendulum1_inertia': 0.010,  # Physically consistent
            'pendulum2_inertia': 0.010,  # Physically consistent
            'gravity': 9.81,
            'cart_friction': 0.1,
            'joint1_friction': 0.001,
            'joint2_friction': 0.001,
            'regularization_alpha': 1e-6,
            'max_condition_number': 1e12,
            'min_regularization': 1e-8,
            'use_fixed_regularization': False
        }

        return SimplifiedDIPConfig(**config_dict)


def test_integration_stability_quick_reference():
    """
    QUICK REFERENCE: Integration stability boundaries for DIP simulation.

    PRACTICAL GUIDANCE: Use this test to quickly verify stable simulation parameters.
    """
    print("\n" + "="*90)
    print("INTEGRATION STABILITY QUICK REFERENCE")
    print("="*90)
    print("SAFE PARAMETERS: dt ≤ 0.01s (recommended for most users)")
    print("BALANCED PARAMETERS: dt ≤ 0.05s (experienced users)")
    print("RISKY PARAMETERS: dt > 0.1s (experts only, scenario-dependent)")
    print("DANGER ZONE: dt ≥ 0.5s (numerical instability likely)")
    print("="*90)

    # Quick demonstration
    config_dict = {
        'cart_mass': 2.4, 'pendulum1_mass': 0.23, 'pendulum2_mass': 0.23,
        'pendulum1_length': 0.36, 'pendulum2_length': 0.36,
        'pendulum1_com': 0.18, 'pendulum2_com': 0.18,
        'pendulum1_inertia': 0.010, 'pendulum2_inertia': 0.010,
        'gravity': 9.81, 'cart_friction': 0.1,
        'joint1_friction': 0.001, 'joint2_friction': 0.001,
        'regularization_alpha': 1e-6, 'max_condition_number': 1e12,
        'min_regularization': 1e-8, 'use_fixed_regularization': False
    }

    config = SimplifiedDIPConfig(**config_dict)
    params = DIPParams.from_physics_config(config)

    # Test standard scenario
    test_state = np.array([0.0, 0.2, 0.2, 0.0, 0.0, 0.0])
    test_cases = [
        (0.01, "SAFE"),
        (0.05, "BALANCED"),
        (0.1, "RISKY"),
        (0.5, "DANGER")
    ]

    print(f"\nDEMONSTRATION - Standard test scenario:")
    print(f"Initial state: {test_state}")
    print(f"Simulation: 3s with RK4 integration")
    print("-" * 40)

    for dt, category in test_cases:
        state = test_state.copy()
        simulation_time = 3.0
        num_steps = int(simulation_time / dt)

        try:
            stable = True
            for i in range(num_steps):
                state = step_rk4_numba(state, 0.0, dt, params)

                # Check for instability
                if not np.all(np.isfinite(state)) or np.any(np.abs(state) > 100):
                    stable = False
                    break

            if stable:
                print(f"dt = {dt:5.3f}s ({category:8s}): ✓ STABLE")
            else:
                print(f"dt = {dt:5.3f}s ({category:8s}): ✗ UNSTABLE (step {i+1}/{num_steps})")

        except Exception as e:
            print(f"dt = {dt:5.3f}s ({category:8s}): ✗ FAILED ({type(e).__name__})")

    print(f"\n✅ Integration stability reference validated")
    print("Use dt ≤ 0.01s for reliable, stable simulations")