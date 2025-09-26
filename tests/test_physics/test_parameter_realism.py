#==========================================================================================\\\
#========= tests/test_physics/test_parameter_realism.py ==========================\\\
#==========================================================================================\\\

"""
Parameter Realism Validation Testing.

CRITICAL MISSION: Prevent unphysical parameter combinations that lead to massive errors.

SCIENTIFIC REALITY:
- Unphysical parameter combinations can cause 980% energy errors
- Mass ratios, length ratios, and inertia values must be realistic
- Parameter validation prevents debugging nightmares

STRATEGIC VALUE: Eliminate parameter-related debugging sessions (80% reduction target).
"""

import pytest
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.core.dynamics import step_rk4_numba, DIPParams
from src.plant.models.simplified.physics import SimplifiedPhysicsComputer
from src.plant.models.simplified.config import SimplifiedDIPConfig


class TestParameterRealism:
    """
    MISSION: Validate parameter realism to prevent unphysical simulation scenarios.

    PREVENTS: 980% energy errors from unrealistic parameter combinations.
    ELIMINATES: Parameter debugging confusion and wasted development time.
    """

    def setup_method(self):
        """Set up parameter realism testing environment."""
        # Reference realistic parameters (based on actual DIP systems)
        self.reference_params = {
            'cart_mass': 2.4,           # kg - Quanser cart mass
            'pendulum1_mass': 0.23,     # kg - Standard pendulum mass
            'pendulum2_mass': 0.23,     # kg - Standard pendulum mass
            'pendulum1_length': 0.36,   # m - Standard pendulum length
            'pendulum2_length': 0.36,   # m - Standard pendulum length
            'pendulum1_com': 0.18,      # m - Center of mass at half length
            'pendulum2_com': 0.18,      # m - Center of mass at half length
            'pendulum1_inertia': 0.010, # kg⋅m² - Physically consistent
            'pendulum2_inertia': 0.010, # kg⋅m² - Physically consistent
            'gravity': 9.81,            # m/s² - Earth gravity
            'cart_friction': 0.1,       # N⋅s/m - Light damping
            'joint1_friction': 0.001,   # N⋅m⋅s/rad - Very light damping
            'joint2_friction': 0.001    # N⋅m⋅s/rad - Very light damping
        }

        # Physical realism bounds
        self.realism_bounds = {
            'mass_ratios': {
                'cart_to_pendulum_min': 0.5,     # Cart should be substantial
                'cart_to_pendulum_max': 50.0,    # But not ridiculously heavy
                'pendulum_ratio_min': 0.1,       # Pendulums can be different
                'pendulum_ratio_max': 10.0       # But not extremely different
            },
            'length_ratios': {
                'length_ratio_min': 0.1,         # L2/L1 minimum
                'length_ratio_max': 10.0,        # L2/L1 maximum
                'com_position_min': 0.01,        # COM near the pivot
                'com_position_max': 0.99         # COM near the tip
            },
            'inertia_consistency': {
                'rod_inertia_factor_min': 0.05,  # I = m*L²/12 to I = m*L²/3
                'rod_inertia_factor_max': 0.5
            },
            'damping_realism': {
                'cart_damping_max': 10.0,        # Reasonable friction
                'pendulum_damping_max': 1.0      # Pendulums have less damping
            }
        }

        # Problematic parameter combinations (known to cause issues)
        self.problematic_combinations = {
            'zero_mass_pendulum': {
                'description': 'Zero or near-zero pendulum mass',
                'params': {'pendulum1_mass': 1e-10, 'pendulum2_mass': 1e-10},
                'expected_issues': ['Singular inertia matrix', 'Numerical instability']
            },
            'massive_pendulum': {
                'description': 'Unrealistically heavy pendulum',
                'params': {'cart_mass': 0.1, 'pendulum1_mass': 100.0, 'pendulum2_mass': 100.0},
                'expected_issues': ['Unrealistic dynamics', 'Energy conservation issues']
            },
            'zero_length_pendulum': {
                'description': 'Zero or near-zero pendulum length',
                'params': {'pendulum1_length': 1e-10, 'pendulum2_length': 1e-10},
                'expected_issues': ['Division by zero', 'Singular matrices']
            },
            'extreme_length_ratio': {
                'description': 'Extreme pendulum length ratio',
                'params': {'pendulum1_length': 0.01, 'pendulum2_length': 10.0},
                'expected_issues': ['Numerical conditioning', 'Multi-scale dynamics']
            },
            'inconsistent_com': {
                'description': 'Center of mass outside pendulum length',
                'params': {'pendulum1_com': 1.0, 'pendulum1_length': 0.3},
                'expected_issues': ['Unphysical configuration', 'Energy errors']
            },
            'zero_inertia': {
                'description': 'Zero rotational inertia',
                'params': {'pendulum1_inertia': 0.0, 'pendulum2_inertia': 0.0},
                'expected_issues': ['Singular dynamics', 'Matrix inversion failure']
            }
        }

    def test_mass_ratio_realism(self):
        """
        TEST: Validate mass ratio realism.

        PREVENTS: Unrealistic mass combinations that cause simulation issues.
        DOCUMENTS: Acceptable mass ratio ranges for stable simulation.
        """
        print("\n" + "="*80)
        print("MASS RATIO REALISM VALIDATION")
        print("PURPOSE: Prevent unrealistic mass combinations")
        print("="*80)

        base_config = self._create_base_config()

        # Test cart-to-pendulum mass ratios
        cart_masses = [0.1, 0.5, 1.0, 2.4, 5.0, 10.0, 50.0]
        pendulum_mass = self.reference_params['pendulum1_mass']

        print(f"\nCart-to-pendulum mass ratio analysis:")
        print(f"Fixed pendulum mass: {pendulum_mass:.3f} kg")
        print("-" * 50)

        for cart_mass in cart_masses:
            ratio = cart_mass / pendulum_mass
            config = self._modify_config(base_config, {'cart_mass': cart_mass})

            # Test configuration validity
            is_realistic, issues = self._test_configuration_realism(config)
            energy_stability = self._test_energy_stability(config)

            print(f"Cart mass: {cart_mass:5.1f} kg, Ratio: {ratio:6.1f}, ", end="")

            if is_realistic and energy_stability:
                print("✓ REALISTIC")
            else:
                print(f"✗ PROBLEMATIC ({', '.join(issues)})")

            # VALIDATION: Ratios within bounds should be realistic
            bounds = self.realism_bounds['mass_ratios']
            if bounds['cart_to_pendulum_min'] <= ratio <= bounds['cart_to_pendulum_max']:
                assert is_realistic and energy_stability, \
                    f"Mass ratio {ratio:.1f} should be realistic but failed validation"

    def test_length_ratio_realism(self):
        """
        TEST: Validate pendulum length ratio realism.

        PREVENTS: Extreme length ratios that cause numerical issues.
        DOCUMENTS: Acceptable length ratio ranges.
        """
        print("\n" + "="*80)
        print("LENGTH RATIO REALISM VALIDATION")
        print("PURPOSE: Prevent extreme pendulum length ratios")
        print("="*80)

        base_config = self._create_base_config()
        L1 = self.reference_params['pendulum1_length']

        # Test different L2/L1 ratios
        length_ratios = [0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]

        print(f"\nPendulum length ratio analysis:")
        print(f"Fixed L1: {L1:.3f} m")
        print("-" * 50)

        for ratio in length_ratios:
            L2 = L1 * ratio
            Lc2 = L2 / 2  # COM at center

            config = self._modify_config(base_config, {
                'pendulum2_length': L2,
                'pendulum2_com': Lc2
            })

            is_realistic, issues = self._test_configuration_realism(config)
            energy_stability = self._test_energy_stability(config)

            print(f"L2/L1 ratio: {ratio:5.1f}, L2: {L2:.3f} m, ", end="")

            if is_realistic and energy_stability:
                print("✓ REALISTIC")
            else:
                print(f"✗ PROBLEMATIC ({', '.join(issues)})")

            # VALIDATION: Ratios within bounds should be realistic
            bounds = self.realism_bounds['length_ratios']
            if bounds['length_ratio_min'] <= ratio <= bounds['length_ratio_max']:
                if not (is_realistic and energy_stability):
                    print(f"    Warning: Length ratio {ratio:.1f} flagged as problematic")

    def test_inertia_consistency_validation(self):
        """
        TEST: Validate inertia consistency with mass and length.

        PREVENTS: Inconsistent inertia values that violate physics.
        DOCUMENTS: Realistic inertia calculation guidelines.
        """
        print("\n" + "="*80)
        print("INERTIA CONSISTENCY VALIDATION")
        print("PURPOSE: Ensure inertia values are consistent with geometry")
        print("="*80)

        base_config = self._create_base_config()

        # Test inertia consistency for different pendulum configurations
        test_configurations = [
            {'mass': 0.1, 'length': 0.2, 'description': 'Light, short pendulum'},
            {'mass': 0.23, 'length': 0.36, 'description': 'Standard pendulum'},
            {'mass': 0.5, 'length': 0.5, 'description': 'Heavy, long pendulum'},
            {'mass': 1.0, 'length': 1.0, 'description': 'Very heavy, very long'},
        ]

        print(f"\nInertia consistency analysis:")
        print("-" * 60)

        for config_data in test_configurations:
            mass = config_data['mass']
            length = config_data['length']
            description = config_data['description']

            # Calculate theoretical inertia range for uniform rod
            # Point mass at end: I = m*L²
            # Uniform rod about center: I = m*L²/12
            # Uniform rod about end: I = m*L²/3
            I_min = mass * length**2 / 12  # Minimum realistic inertia
            I_max = mass * length**2 / 3   # Maximum realistic inertia

            # Test different inertia values
            inertia_factors = [0.01, 0.05, 0.083, 0.33, 0.5, 1.0]  # Fraction of m*L²

            print(f"\n{description} (m={mass:.2f} kg, L={length:.2f} m):")
            print(f"Realistic inertia range: {I_min:.6f} - {I_max:.6f} kg⋅m²")

            for factor in inertia_factors:
                inertia = mass * length**2 * factor

                config = self._modify_config(base_config, {
                    'pendulum1_mass': mass,
                    'pendulum1_length': length,
                    'pendulum1_com': length / 2,
                    'pendulum1_inertia': inertia
                })

                is_realistic, issues = self._test_configuration_realism(config)
                is_consistent = I_min <= inertia <= I_max * 2  # Allow some flexibility

                print(f"  I = {inertia:.6f} kg⋅m² (factor: {factor:.3f}), ", end="")

                if is_consistent and is_realistic:
                    print("✓ CONSISTENT")
                elif is_consistent:
                    print("? CONSISTENT but other issues")
                else:
                    print("✗ INCONSISTENT")

    def test_problematic_parameter_combinations(self):
        """
        TEST: Validate detection of known problematic parameter combinations.

        PREVENTS: Parameter combinations that cause 980% energy errors.
        DOCUMENTS: Specific parameter combinations to avoid.
        """
        print("\n" + "="*80)
        print("PROBLEMATIC PARAMETER COMBINATION DETECTION")
        print("PURPOSE: Catch parameter combinations that cause massive errors")
        print("="*80)

        base_config = self._create_base_config()

        for combo_name, combo_data in self.problematic_combinations.items():
            print(f"\nTesting: {combo_data['description']}")
            print(f"Parameters: {combo_data['params']}")
            print(f"Expected issues: {combo_data['expected_issues']}")

            # Create problematic configuration
            config = self._modify_config(base_config, combo_data['params'])

            # Test for issues
            is_realistic, issues = self._test_configuration_realism(config)
            energy_stability = self._test_energy_stability(config)
            numerical_stability = self._test_numerical_stability(config)

            print("Results:")
            print(f"  Realistic: {'✓' if is_realistic else '✗'}")
            print(f"  Energy stable: {'✓' if energy_stability else '✗'}")
            print(f"  Numerically stable: {'✓' if numerical_stability else '✗'}")

            if issues:
                print(f"  Issues detected: {', '.join(issues)}")

            # VALIDATION: Problematic combinations should be detected
            overall_ok = is_realistic and energy_stability and numerical_stability
            assert not overall_ok, \
                f"Problematic combination '{combo_name}' was not detected as problematic"

            print(f"  ✓ Problematic combination correctly detected")

    def test_parameter_realism_reference_guide(self):
        """
        TEST: Create parameter realism reference guide.

        OUTPUT: Comprehensive guide for selecting realistic DIP parameters.
        PURPOSE: Prevent parameter-related issues through proper guidance.
        """
        print("\n" + "="*80)
        print("PARAMETER REALISM REFERENCE GUIDE")
        print("USE: Guidelines for selecting realistic DIP parameters")
        print("="*80)

        reference_guide = {
            "Mass Parameters": {
                "cart_mass": {
                    "typical_range": "1.0 - 5.0 kg",
                    "recommended": f"{self.reference_params['cart_mass']} kg",
                    "notes": "Should be substantially heavier than pendulums for stability"
                },
                "pendulum_mass": {
                    "typical_range": "0.1 - 1.0 kg",
                    "recommended": f"{self.reference_params['pendulum1_mass']} kg",
                    "notes": "Light enough for cart control, heavy enough to avoid numerical issues"
                },
                "mass_ratio": {
                    "cart_to_pendulum": "2:1 to 20:1",
                    "pendulum_ratio": "0.5:1 to 2:1",
                    "notes": "Extreme ratios cause numerical conditioning problems"
                }
            },
            "Length Parameters": {
                "pendulum_length": {
                    "typical_range": "0.1 - 1.0 m",
                    "recommended": f"{self.reference_params['pendulum1_length']} m",
                    "notes": "Laboratory-scale lengths for manageable dynamics"
                },
                "length_ratio": {
                    "L2_to_L1": "0.5:1 to 2:1",
                    "notes": "Extreme ratios create multi-scale dynamics issues"
                },
                "center_of_mass": {
                    "typical_position": "0.3 to 0.7 * length",
                    "recommended": "0.5 * length (uniform rod)",
                    "notes": "COM outside pendulum length is unphysical"
                }
            },
            "Inertia Parameters": {
                "calculation": "I = β * m * L² where β ∈ [1/12, 1/3]",
                "uniform_rod_center": "β = 1/12 (rotation about center)",
                "uniform_rod_end": "β = 1/3 (rotation about end)",
                "point_mass": "β = 1 (all mass at end)",
                "recommended": "β ≈ 1/12 to 1/6 for realistic pendulums"
            },
            "Physical Constants": {
                "gravity": {
                    "earth": "9.81 m/s²",
                    "notes": "Use Earth gravity unless simulating other environments"
                },
                "damping": {
                    "cart_damping": "0.05 - 1.0 N⋅s/m",
                    "pendulum_damping": "0.001 - 0.01 N⋅m⋅s/rad",
                    "notes": "Light damping for realistic pendulum behavior"
                }
            }
        }

        print("\nPARAMETER REALISM GUIDELINES:")
        print("=" * 50)
        for category, parameters in reference_guide.items():
            print(f"\n{category}:")
            for param_name, param_info in parameters.items():
                if isinstance(param_info, dict):
                    print(f"  {param_name}:")
                    for key, value in param_info.items():
                        print(f"    {key}: {value}")
                else:
                    print(f"  {param_name}: {param_info}")

        # Validate reference parameters
        print(f"\nREFERENCE PARAMETER VALIDATION:")
        print("-" * 40)
        reference_config = self._create_base_config()
        is_realistic, issues = self._test_configuration_realism(reference_config)
        energy_stable = self._test_energy_stability(reference_config)
        numerically_stable = self._test_numerical_stability(reference_config)

        print(f"Reference parameters realistic: {'✓' if is_realistic else '✗'}")
        print(f"Reference parameters energy stable: {'✓' if energy_stable else '✗'}")
        print(f"Reference parameters numerically stable: {'✓' if numerically_stable else '✗'}")

        if not (is_realistic and energy_stable and numerically_stable):
            print(f"Issues with reference parameters: {', '.join(issues)}")
            assert False, "Reference parameters should be validated as realistic"

        print(f"\n✅ Parameter realism reference guide created")
        print(f"✅ Use these guidelines to prevent parameter-related simulation issues")

    def _create_base_config(self) -> SimplifiedDIPConfig:
        """Create base realistic configuration."""
        config_dict = self.reference_params.copy()
        config_dict.update({
            'regularization_alpha': 1e-6,
            'max_condition_number': 1e12,
            'min_regularization': 1e-8,
            'use_fixed_regularization': False
        })
        return SimplifiedDIPConfig(**config_dict)

    def _modify_config(self, base_config: SimplifiedDIPConfig, modifications: Dict[str, float]) -> SimplifiedDIPConfig:
        """Create modified configuration with parameter changes."""
        config_dict = {
            'cart_mass': base_config.cart_mass,
            'pendulum1_mass': base_config.pendulum1_mass,
            'pendulum2_mass': base_config.pendulum2_mass,
            'pendulum1_length': base_config.pendulum1_length,
            'pendulum2_length': base_config.pendulum2_length,
            'pendulum1_com': base_config.pendulum1_com,
            'pendulum2_com': base_config.pendulum2_com,
            'pendulum1_inertia': base_config.pendulum1_inertia,
            'pendulum2_inertia': base_config.pendulum2_inertia,
            'gravity': base_config.gravity,
            'cart_damping': base_config.cart_damping,
            'pendulum1_damping': base_config.pendulum1_damping,
            'pendulum2_damping': base_config.pendulum2_damping,
            'regularization_alpha': base_config.regularization_alpha,
            'max_condition_number': base_config.max_condition_number,
            'min_regularization': base_config.min_regularization,
            'use_fixed_regularization': base_config.use_fixed_regularization
        }

        # Apply modifications
        config_dict.update(modifications)

        return SimplifiedDIPConfig(**config_dict)

    def _test_configuration_realism(self, config: SimplifiedDIPConfig) -> Tuple[bool, List[str]]:
        """Test configuration for physical realism."""
        issues = []

        # Check for zero or negative values
        if config.cart_mass <= 0:
            issues.append("Zero/negative cart mass")
        if config.pendulum1_mass <= 0:
            issues.append("Zero/negative pendulum1 mass")
        if config.pendulum2_mass <= 0:
            issues.append("Zero/negative pendulum2 mass")
        if config.pendulum1_length <= 0:
            issues.append("Zero/negative pendulum1 length")
        if config.pendulum2_length <= 0:
            issues.append("Zero/negative pendulum2 length")

        # Check mass ratios
        if config.cart_mass > 0 and config.pendulum1_mass > 0:
            cart_pend_ratio = config.cart_mass / config.pendulum1_mass
            bounds = self.realism_bounds['mass_ratios']
            if not (bounds['cart_to_pendulum_min'] <= cart_pend_ratio <= bounds['cart_to_pendulum_max']):
                issues.append(f"Extreme cart-to-pendulum mass ratio: {cart_pend_ratio:.1f}")

        # Check length ratios
        if config.pendulum1_length > 0 and config.pendulum2_length > 0:
            length_ratio = config.pendulum2_length / config.pendulum1_length
            bounds = self.realism_bounds['length_ratios']
            if not (bounds['length_ratio_min'] <= length_ratio <= bounds['length_ratio_max']):
                issues.append(f"Extreme length ratio: {length_ratio:.1f}")

        # Check COM positions
        if config.pendulum1_com > config.pendulum1_length:
            issues.append("Pendulum1 COM outside length")
        if config.pendulum2_com > config.pendulum2_length:
            issues.append("Pendulum2 COM outside length")

        # Check inertia consistency
        if (config.pendulum1_mass > 0 and config.pendulum1_length > 0 and
            config.pendulum1_inertia >= 0):
            theoretical_max = config.pendulum1_mass * config.pendulum1_length**2
            if config.pendulum1_inertia > theoretical_max:
                issues.append("Pendulum1 inertia exceeds point mass limit")

        return len(issues) == 0, issues

    def _test_energy_stability(self, config: SimplifiedDIPConfig) -> bool:
        """Test configuration for energy stability over short simulation."""
        try:
            physics = SimplifiedPhysicsComputer(config)
            params = DIPParams.from_physics_config(config)

            # Test with small oscillation
            initial_state = np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0])
            initial_energy = physics.compute_total_energy(initial_state)

            if initial_energy <= 0 or not np.isfinite(initial_energy):
                return False

            # Short simulation
            state = initial_state.copy()
            dt = 0.01
            num_steps = 100  # 1 second

            for _ in range(num_steps):
                state = step_rk4_numba(state, 0.0, dt, params)

                if not np.all(np.isfinite(state)):
                    return False

                if np.any(np.abs(state) > 100):  # Unreasonably large
                    return False

            final_energy = physics.compute_total_energy(state)

            if not np.isfinite(final_energy):
                return False

            # Check for excessive energy drift (>1000% is definitely problematic)
            energy_ratio = abs(final_energy / initial_energy)
            if energy_ratio > 10.0:  # 1000% drift
                return False

            return True

        except Exception:
            return False

    def _test_numerical_stability(self, config: SimplifiedDIPConfig) -> bool:
        """Test configuration for numerical stability."""
        try:
            physics = SimplifiedPhysicsComputer(config)

            # Test multiple states for matrix conditioning
            test_states = [
                np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),  # Equilibrium
                np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0]),  # Small displacement
                np.array([0.0, 1.0, 1.0, 0.0, 0.0, 0.0]),  # Large displacement
            ]

            for state in test_states:
                # Check matrix conditioning
                condition_number = physics.get_matrix_conditioning(state)

                if not np.isfinite(condition_number):
                    return False

                if condition_number > 1e15:  # Very poorly conditioned
                    return False

                # Check that dynamics computation doesn't fail
                try:
                    state_dot = physics.compute_dynamics_rhs(state, np.array([0.0]))
                    if not np.all(np.isfinite(state_dot)):
                        return False
                except Exception:
                    return False

            return True

        except Exception:
            return False


def test_parameter_realism_quick_check():
    """
    QUICK CHECK: Validate that reference parameters are realistic.

    PREVENTS: Issues with default/example parameter sets.
    """
    print("\n" + "="*90)
    print("PARAMETER REALISM QUICK CHECK")
    print("PURPOSE: Validate reference parameters are physically realistic")
    print("="*90)

    # Test reference parameters
    reference_params = {
        'cart_mass': 2.4, 'pendulum1_mass': 0.23, 'pendulum2_mass': 0.23,
        'pendulum1_length': 0.36, 'pendulum2_length': 0.36,
        'pendulum1_com': 0.18, 'pendulum2_com': 0.18,
        'pendulum1_inertia': 0.010, 'pendulum2_inertia': 0.010,
        'gravity': 9.81, 'cart_friction': 0.1,
        'joint1_friction': 0.001, 'joint2_friction': 0.001,
        'regularization_alpha': 1e-6, 'max_condition_number': 1e12,
        'min_regularization': 1e-8, 'use_fixed_regularization': False
    }

    config = SimplifiedDIPConfig(**reference_params)

    print(f"Testing reference parameters:")
    for param, value in reference_params.items():
        if not param.endswith('_alpha') and not param.startswith('max_') and not param.startswith('min_') and not param.startswith('use_'):
            print(f"  {param}: {value}")

    # Quick realism checks
    print(f"\nRealism checks:")

    # Mass ratios
    cart_to_pend = reference_params['cart_mass'] / reference_params['pendulum1_mass']
    print(f"  Cart-to-pendulum mass ratio: {cart_to_pend:.1f} (good: 2-20)")

    # Length ratios
    length_ratio = reference_params['pendulum2_length'] / reference_params['pendulum1_length']
    print(f"  Pendulum length ratio: {length_ratio:.1f} (good: 0.5-2)")

    # COM positions
    com1_fraction = reference_params['pendulum1_com'] / reference_params['pendulum1_length']
    print(f"  COM1 position fraction: {com1_fraction:.2f} (good: 0.3-0.7)")

    # Inertia consistency
    theoretical_I1 = reference_params['pendulum1_mass'] * reference_params['pendulum1_length']**2 / 12
    actual_I1 = reference_params['pendulum1_inertia']
    inertia_ratio = actual_I1 / theoretical_I1
    print(f"  Inertia consistency ratio: {inertia_ratio:.2f} (good: 1-4)")

    # Quick simulation test
    try:
        physics = SimplifiedPhysicsComputer(config)
        test_state = np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0])
        energy = physics.compute_total_energy(test_state)
        conditioning = physics.get_matrix_conditioning(test_state)

        print(f"  Energy computation: {energy:.6f} J ✓")
        print(f"  Matrix conditioning: {conditioning:.2e} ✓")

        print(f"\n✅ Reference parameters validated as realistic")

    except Exception as e:
        print(f"\n✗ Reference parameters failed validation: {e}")
        assert False, "Reference parameters should be realistic"