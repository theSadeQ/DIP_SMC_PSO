#==========================================================================================\
#======== tests/test_benchmarks/validation/test_parameter_realism.py ====================\
#==========================================================================================\

"""
Realistic Parameter Calibration and Validation - Mission 7 Parameter Engineering

ENGINEERING EXCELLENCE: Transform benchmark parameters from "arbitrary" to "meaningful."
This module ensures all benchmark parameters reflect real-world control engineering
constraints, enabling scientifically valid performance comparisons and eliminating
the "unrealistic parameter problem" that undermines benchmark credibility.

PARAMETER ENGINEERING OBJECTIVES:
- Establish physically meaningful parameter ranges for all components
- Validate parameter combinations against engineering constraints
- Provide realistic test scenarios based on actual hardware setups
- Enable parameter sensitivity analysis for robust benchmarking

VALIDATION HIERARCHY:
1. Physics-based bounds (cannot violate laws of physics)
2. Engineering constraints (practical hardware limitations)
3. Control theory limits (stability and performance bounds)
4. Experimental validation (real-world measurement ranges)

SUCCESS CRITERIA:
- All benchmark parameters are engineering-validated
- Test scenarios reflect real hardware configurations
- Parameter sensitivity analysis completed
- Benchmark results are scientifically meaningful
"""

import pytest
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import sys
import warnings
from scipy import stats
import math

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "src"))

try:
    from src.controllers.factory.smc_factory import SMCFactory, SMCType, SMCConfig
    from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
    from src.plant.models.full.dynamics import FullDIPDynamics
    from src.config import load_config
    from src.utils.config_compatibility import wrap_physics_config
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


class ParameterValidationLevel(Enum):
    """Levels of parameter validation rigor."""
    PHYSICS_BOUNDS = "physics_bounds"        # Cannot violate physics
    ENGINEERING_LIMITS = "engineering_limits" # Practical hardware constraints
    CONTROL_THEORY = "control_theory"        # Stability and performance bounds
    EXPERIMENTAL = "experimental"            # Real-world measurement ranges


class HardwareConfiguration(Enum):
    """Standard hardware configurations for realistic testing."""
    DESKTOP_LAB = "desktop_lab"              # Small lab setup
    INDUSTRIAL_PROTOTYPE = "industrial"     # Industrial-scale prototype
    RESEARCH_PLATFORM = "research"          # High-precision research setup
    EDUCATIONAL_KIT = "educational"         # Educational demonstration
    MICRO_SCALE = "micro_scale"            # Miniature/MEMS scale


@dataclass
class ParameterBounds:
    """Physical and engineering bounds for a parameter."""
    min_value: float
    max_value: float
    typical_range: Tuple[float, float]
    unit: str
    validation_level: ParameterValidationLevel
    justification: str


@dataclass
class RealisticScenario:
    """Complete realistic test scenario with validated parameters."""
    name: str
    hardware_config: HardwareConfiguration
    description: str
    physics_params: Dict[str, float]
    control_gains: Dict[str, List[float]]  # Per controller type
    expected_performance: Dict[str, Tuple[float, float]]  # (min, max) ranges
    validation_notes: str


class EngineeringParameterValidator:
    """Validates benchmark parameters against engineering constraints."""

    def __init__(self):
        """Initialize parameter validation system."""
        self.parameter_bounds = self._establish_parameter_bounds()
        self.realistic_scenarios = self._create_realistic_scenarios()

    def _establish_parameter_bounds(self) -> Dict[str, ParameterBounds]:
        """Establish engineering-validated parameter bounds."""

        bounds = {}

        # === CART PARAMETERS ===
        bounds['cart_mass'] = ParameterBounds(
            min_value=0.1,      # 100g minimum (micro-scale)
            max_value=50.0,     # 50kg maximum (industrial)
            typical_range=(0.5, 5.0),  # Desktop lab range
            unit="kg",
            validation_level=ParameterValidationLevel.PHYSICS_BOUNDS,
            justification="Physical mass cannot be negative or infinite"
        )

        bounds['cart_friction'] = ParameterBounds(
            min_value=0.0001,   # Near-frictionless bearings
            max_value=2.0,      # High-friction sliding
            typical_range=(0.01, 0.5),  # Typical mechanical systems
            unit="N·s/m",
            validation_level=ParameterValidationLevel.ENGINEERING_LIMITS,
            justification="Based on typical linear bearing friction coefficients"
        )

        # === PENDULUM 1 PARAMETERS (Bottom pendulum) ===
        bounds['pendulum1_mass'] = ParameterBounds(
            min_value=0.01,     # 10g minimum
            max_value=10.0,     # 10kg maximum
            typical_range=(0.1, 2.0),
            unit="kg",
            validation_level=ParameterValidationLevel.PHYSICS_BOUNDS,
            justification="Physical mass constraints"
        )

        bounds['pendulum1_length'] = ParameterBounds(
            min_value=0.05,     # 5cm minimum (micro-scale)
            max_value=3.0,      # 3m maximum (large-scale)
            typical_range=(0.2, 1.0),  # Desktop lab scale
            unit="m",
            validation_level=ParameterValidationLevel.ENGINEERING_LIMITS,
            justification="Practical laboratory and workspace constraints"
        )

        bounds['pendulum1_inertia'] = ParameterBounds(
            min_value=1e-6,     # Very small rod
            max_value=10.0,     # Large distributed mass
            typical_range=(0.001, 1.0),
            unit="kg·m²",
            validation_level=ParameterValidationLevel.PHYSICS_BOUNDS,
            justification="Moment of inertia for realistic rod geometries"
        )

        bounds['joint1_friction'] = ParameterBounds(
            min_value=1e-6,     # High-quality bearings
            max_value=0.5,      # High-friction pivot
            typical_range=(0.001, 0.1),
            unit="N·m·s",
            validation_level=ParameterValidationLevel.ENGINEERING_LIMITS,
            justification="Typical rotational bearing friction"
        )

        # === PENDULUM 2 PARAMETERS (Top pendulum) ===
        bounds['pendulum2_mass'] = ParameterBounds(
            min_value=0.005,    # 5g minimum
            max_value=5.0,      # 5kg maximum
            typical_range=(0.05, 1.0),
            unit="kg",
            validation_level=ParameterValidationLevel.PHYSICS_BOUNDS,
            justification="Physical mass constraints"
        )

        bounds['pendulum2_length'] = ParameterBounds(
            min_value=0.03,     # 3cm minimum
            max_value=2.0,      # 2m maximum
            typical_range=(0.1, 0.8),
            unit="m",
            validation_level=ParameterValidationLevel.ENGINEERING_LIMITS,
            justification="Workspace and stability constraints"
        )

        bounds['pendulum2_inertia'] = ParameterBounds(
            min_value=1e-7,     # Very small rod
            max_value=5.0,      # Large distributed mass
            typical_range=(0.0001, 0.5),
            unit="kg·m²",
            validation_level=ParameterValidationLevel.PHYSICS_BOUNDS,
            justification="Moment of inertia for realistic rod geometries"
        )

        bounds['joint2_friction'] = ParameterBounds(
            min_value=1e-6,     # High-quality bearings
            max_value=0.2,      # High-friction pivot
            typical_range=(0.0001, 0.05),
            unit="N·m·s",
            validation_level=ParameterValidationLevel.ENGINEERING_LIMITS,
            justification="Typical rotational bearing friction"
        )

        # === ENVIRONMENTAL PARAMETERS ===
        bounds['gravity'] = ParameterBounds(
            min_value=9.75,     # Lowest Earth gravity
            max_value=9.85,     # Highest Earth gravity
            typical_range=(9.80, 9.82),
            unit="m/s²",
            validation_level=ParameterValidationLevel.PHYSICS_BOUNDS,
            justification="Earth surface gravity variation"
        )

        bounds['max_force'] = ParameterBounds(
            min_value=1.0,      # Small actuator
            max_value=1000.0,   # Large industrial actuator
            typical_range=(10.0, 200.0),  # Desktop lab actuators
            unit="N",
            validation_level=ParameterValidationLevel.ENGINEERING_LIMITS,
            justification="Typical actuator force capabilities"
        )

        return bounds

    def _create_realistic_scenarios(self) -> List[RealisticScenario]:
        """Create realistic test scenarios based on actual hardware configurations."""

        scenarios = []

        # === DESKTOP LAB SETUP ===
        scenarios.append(RealisticScenario(
            name="Desktop Lab Setup",
            hardware_config=HardwareConfiguration.DESKTOP_LAB,
            description="Typical university laboratory double inverted pendulum",
            physics_params={
                'cart_mass': 1.2,
                'cart_friction': 0.15,
                'pendulum1_mass': 0.35,
                'pendulum1_length': 0.48,
                'pendulum1_inertia': 0.027,
                'joint1_friction': 0.015,
                'pendulum2_mass': 0.18,
                'pendulum2_length': 0.28,
                'pendulum2_inertia': 0.012,
                'joint2_friction': 0.008,
                'gravity': 9.81,
                'max_force': 80.0
            },
            control_gains={
                'classical': [12.0, 6.0, 4.0, 2.5, 45.0, 1.2],
                'adaptive': [10.0, 5.0, 3.0, 2.0, 0.8],
                'super_twisting': [18.0, 12.0, 8.0, 5.0, 3.0, 1.8],
                'hybrid': [15.0, 4.0, 10.0, 2.5]
            },
            expected_performance={
                'settling_time': (3.0, 8.0),         # seconds
                'control_energy': (50.0, 200.0),     # J·s
                'overshoot': (0.02, 0.08),          # m
                'steady_state_error': (0.001, 0.01) # m
            },
            validation_notes="Based on Quanser and Feedback Instruments systems"
        ))

        # === INDUSTRIAL PROTOTYPE ===
        scenarios.append(RealisticScenario(
            name="Industrial Prototype",
            hardware_config=HardwareConfiguration.INDUSTRIAL_PROTOTYPE,
            description="Large-scale industrial crane control prototype",
            physics_params={
                'cart_mass': 15.0,
                'cart_friction': 0.8,
                'pendulum1_mass': 2.5,
                'pendulum1_length': 1.2,
                'pendulum1_inertia': 1.2,
                'joint1_friction': 0.25,
                'pendulum2_mass': 0.8,
                'pendulum2_length': 0.6,
                'pendulum2_inertia': 0.3,
                'joint2_friction': 0.15,
                'gravity': 9.81,
                'max_force': 800.0
            },
            control_gains={
                'classical': [8.0, 4.0, 2.5, 1.5, 25.0, 0.8],
                'adaptive': [6.0, 3.0, 2.0, 1.2, 0.5],
                'super_twisting': [12.0, 8.0, 5.0, 3.0, 2.0, 1.2],
                'hybrid': [10.0, 2.5, 6.0, 1.8]
            },
            expected_performance={
                'settling_time': (8.0, 20.0),
                'control_energy': (1000.0, 5000.0),
                'overshoot': (0.1, 0.3),
                'steady_state_error': (0.01, 0.05)
            },
            validation_notes="Scaled from industrial overhead crane dynamics"
        ))

        # === HIGH-PRECISION RESEARCH PLATFORM ===
        scenarios.append(RealisticScenario(
            name="Research Platform",
            hardware_config=HardwareConfiguration.RESEARCH_PLATFORM,
            description="High-precision research platform with low friction",
            physics_params={
                'cart_mass': 0.8,
                'cart_friction': 0.02,  # Air bearings
                'pendulum1_mass': 0.25,
                'pendulum1_length': 0.6,
                'pendulum1_inertia': 0.03,
                'joint1_friction': 0.002,  # Precision bearings
                'pendulum2_mass': 0.12,
                'pendulum2_length': 0.35,
                'pendulum2_inertia': 0.005,
                'joint2_friction': 0.001,
                'gravity': 9.81,
                'max_force': 50.0
            },
            control_gains={
                'classical': [15.0, 8.0, 6.0, 4.0, 60.0, 1.8],
                'adaptive': [12.0, 6.0, 4.0, 2.5, 1.2],
                'super_twisting': [22.0, 15.0, 12.0, 8.0, 4.0, 2.5],
                'hybrid': [18.0, 5.0, 15.0, 3.5]
            },
            expected_performance={
                'settling_time': (2.0, 5.0),
                'control_energy': (20.0, 80.0),
                'overshoot': (0.005, 0.02),
                'steady_state_error': (0.0001, 0.002)
            },
            validation_notes="Based on precision control research setups"
        ))

        # === EDUCATIONAL KIT ===
        scenarios.append(RealisticScenario(
            name="Educational Kit",
            hardware_config=HardwareConfiguration.EDUCATIONAL_KIT,
            description="Compact educational demonstration kit",
            physics_params={
                'cart_mass': 0.4,
                'cart_friction': 0.25,
                'pendulum1_mass': 0.15,
                'pendulum1_length': 0.25,
                'pendulum1_inertia': 0.008,
                'joint1_friction': 0.02,
                'pendulum2_mass': 0.08,
                'pendulum2_length': 0.15,
                'pendulum2_inertia': 0.002,
                'joint2_friction': 0.012,
                'gravity': 9.81,
                'max_force': 20.0
            },
            control_gains={
                'classical': [20.0, 12.0, 8.0, 5.0, 80.0, 2.5],
                'adaptive': [15.0, 8.0, 6.0, 3.5, 1.8],
                'super_twisting': [30.0, 20.0, 15.0, 10.0, 6.0, 3.5],
                'hybrid': [25.0, 7.0, 20.0, 5.0]
            },
            expected_performance={
                'settling_time': (1.5, 4.0),
                'control_energy': (5.0, 25.0),
                'overshoot': (0.01, 0.04),
                'steady_state_error': (0.0005, 0.005)
            },
            validation_notes="Typical of commercial educational kits"
        ))

        return scenarios

    def validate_parameter_value(self, param_name: str, value: float) -> Tuple[bool, str]:
        """Validate a single parameter value against engineering constraints."""

        if param_name not in self.parameter_bounds:
            return False, f"Unknown parameter: {param_name}"

        bounds = self.parameter_bounds[param_name]

        # Check absolute bounds
        if value < bounds.min_value:
            return False, f"{param_name}={value} below minimum {bounds.min_value} {bounds.unit}"

        if value > bounds.max_value:
            return False, f"{param_name}={value} above maximum {bounds.max_value} {bounds.unit}"

        # Check if within typical range (warning, not error)
        if not (bounds.typical_range[0] <= value <= bounds.typical_range[1]):
            warning_msg = f"{param_name}={value} outside typical range {bounds.typical_range} {bounds.unit}"
            warnings.warn(warning_msg)

        return True, "Valid parameter"

    def validate_physics_consistency(self, physics_params: Dict[str, float]) -> Tuple[bool, List[str]]:
        """Validate physics parameter consistency and engineering relationships."""

        errors = []

        # === MASS RATIO CHECKS ===
        if 'cart_mass' in physics_params and 'pendulum1_mass' in physics_params:
            cart_mass = physics_params['cart_mass']
            pend1_mass = physics_params['pendulum1_mass']
            mass_ratio = pend1_mass / cart_mass

            if mass_ratio > 2.0:
                errors.append(f"Pendulum1/cart mass ratio {mass_ratio:.2f} > 2.0 (unstable)")
            elif mass_ratio < 0.01:
                errors.append(f"Pendulum1/cart mass ratio {mass_ratio:.2f} < 0.01 (negligible dynamics)")

        if 'pendulum1_mass' in physics_params and 'pendulum2_mass' in physics_params:
            pend1_mass = physics_params['pendulum1_mass']
            pend2_mass = physics_params['pendulum2_mass']
            pend_ratio = pend2_mass / pend1_mass

            if pend_ratio > 1.5:
                errors.append(f"Pendulum2/pendulum1 mass ratio {pend_ratio:.2f} > 1.5 (top-heavy)")

        # === LENGTH RATIO CHECKS ===
        if 'pendulum1_length' in physics_params and 'pendulum2_length' in physics_params:
            len1 = physics_params['pendulum1_length']
            len2 = physics_params['pendulum2_length']
            len_ratio = len2 / len1

            if len_ratio > 1.2:
                errors.append(f"Pendulum2/pendulum1 length ratio {len_ratio:.2f} > 1.2 (unusual geometry)")
            elif len_ratio < 0.3:
                errors.append(f"Pendulum2/pendulum1 length ratio {len_ratio:.2f} < 0.3 (very short top)")

        # === INERTIA CONSISTENCY CHECKS ===
        # Check if moment of inertia is consistent with mass and length for rod model
        if all(p in physics_params for p in ['pendulum1_mass', 'pendulum1_length', 'pendulum1_inertia']):
            mass = physics_params['pendulum1_mass']
            length = physics_params['pendulum1_length']
            inertia = physics_params['pendulum1_inertia']

            # For uniform rod: I = (1/3) * m * L^2
            expected_inertia = (1/3) * mass * length**2
            inertia_ratio = inertia / expected_inertia

            if inertia_ratio > 3.0 or inertia_ratio < 0.1:
                errors.append(f"Pendulum1 inertia ratio {inertia_ratio:.2f} inconsistent with uniform rod model")

        if all(p in physics_params for p in ['pendulum2_mass', 'pendulum2_length', 'pendulum2_inertia']):
            mass = physics_params['pendulum2_mass']
            length = physics_params['pendulum2_length']
            inertia = physics_params['pendulum2_inertia']

            expected_inertia = (1/3) * mass * length**2
            inertia_ratio = inertia / expected_inertia

            if inertia_ratio > 3.0 or inertia_ratio < 0.1:
                errors.append(f"Pendulum2 inertia ratio {inertia_ratio:.2f} inconsistent with uniform rod model")

        # === ACTUATOR FORCE CHECKS ===
        if 'max_force' in physics_params and 'cart_mass' in physics_params:
            max_force = physics_params['max_force']
            cart_mass = physics_params['cart_mass']
            max_acceleration = max_force / cart_mass

            if max_acceleration > 100.0:  # 10g acceleration limit
                errors.append(f"Maximum acceleration {max_acceleration:.1f} m/s² exceeds reasonable limits")
            elif max_acceleration < 0.5:
                errors.append(f"Maximum acceleration {max_acceleration:.1f} m/s² may be insufficient for control")

        return len(errors) == 0, errors

    def validate_control_gains(self, controller_type: SMCType, gains: List[float]) -> Dict[str, bool]:
        """Validate control gains for engineering feasibility."""

        validation_results = {}

        # Get expected number of gains
        expected_counts = {
            SMCType.CLASSICAL: 6,
            SMCType.ADAPTIVE: 5,
            SMCType.SUPER_TWISTING: 6,
            SMCType.HYBRID: 4
        }

        expected_count = expected_counts.get(controller_type, 4)

        # Check gain count
        validation_results['correct_count'] = len(gains) == expected_count

        # Check for positive gains (most SMC gains should be positive)
        validation_results['all_positive'] = all(g > 0 for g in gains)

        # Check for reasonable magnitudes (controller-specific)
        if controller_type == SMCType.CLASSICAL:
            # Typical classical SMC gains: [K1, K2, K3, K4, lambda, eta]
            validation_results['reasonable_proportional'] = 1.0 <= gains[0] <= 50.0 if len(gains) > 0 else False
            validation_results['reasonable_derivative'] = 0.5 <= gains[1] <= 30.0 if len(gains) > 1 else False
            validation_results['reasonable_switching'] = 0.1 <= gains[-1] <= 10.0 if len(gains) > 0 else False

        elif controller_type == SMCType.ADAPTIVE:
            # Adaptive gains should include adaptation rates
            validation_results['reasonable_adaptation'] = 0.1 <= gains[-1] <= 5.0 if len(gains) > 0 else False

        elif controller_type == SMCType.SUPER_TWISTING:
            # Super-twisting gains should be properly ordered
            if len(gains) >= 6:
                validation_results['alpha_beta_relationship'] = gains[4] > gains[5]  # α > β typically

        # Check gain ratios for stability
        if len(gains) >= 2:
            max_ratio = max(gains) / min(gains) if min(gains) > 0 else float('inf')
            validation_results['reasonable_gain_spread'] = max_ratio < 1000.0  # Avoid extreme ratios

        return validation_results

    def validate_scenario_consistency(self, scenario: RealisticScenario) -> Dict[str, bool]:
        """Validate complete scenario for internal consistency."""

        validation = {}

        # Validate physics parameters
        physics_valid, physics_errors = self.validate_physics_consistency(scenario.physics_params)
        validation['physics_consistent'] = physics_valid

        # Validate individual parameter bounds
        param_validations = []
        for param_name, value in scenario.physics_params.items():
            is_valid, _ = self.validate_parameter_value(param_name, value)
            param_validations.append(is_valid)
        validation['all_parameters_in_bounds'] = all(param_validations)

        # Validate control gains for each controller type
        gain_validations = []
        for controller_name, gains in scenario.control_gains.items():
            # Map controller name to type
            controller_map = {
                'classical': SMCType.CLASSICAL,
                'adaptive': SMCType.ADAPTIVE,
                'super_twisting': SMCType.SUPER_TWISTING,
                'hybrid': SMCType.HYBRID
            }

            if controller_name in controller_map:
                smc_type = controller_map[controller_name]
                gain_validation = self.validate_control_gains(smc_type, gains)
                gain_validations.append(all(gain_validation.values()))

        validation['all_gains_valid'] = all(gain_validations)

        # Validate expected performance ranges
        perf_validations = []
        for metric_name, (min_val, max_val) in scenario.expected_performance.items():
            perf_validations.append(min_val < max_val and min_val >= 0)
        validation['performance_ranges_valid'] = all(perf_validations)

        return validation

    def get_realistic_scenario_by_name(self, name: str) -> Optional[RealisticScenario]:
        """Get realistic scenario by name."""
        for scenario in self.realistic_scenarios:
            if scenario.name == name:
                return scenario
        return None

    def analyze_parameter_sensitivity(self, base_params: Dict[str, float],
                                    perturbation_percent: float = 10.0) -> Dict[str, Dict[str, float]]:
        """Analyze parameter sensitivity for robust benchmarking."""

        sensitivity_analysis = {}

        for param_name, base_value in base_params.items():
            if param_name in self.parameter_bounds:
                bounds = self.parameter_bounds[param_name]

                # Calculate perturbation within bounds
                perturbation = base_value * (perturbation_percent / 100.0)

                min_perturbed = max(bounds.min_value, base_value - perturbation)
                max_perturbed = min(bounds.max_value, base_value + perturbation)

                sensitivity_analysis[param_name] = {
                    'base_value': base_value,
                    'min_perturbed': min_perturbed,
                    'max_perturbed': max_perturbed,
                    'perturbation_range': max_perturbed - min_perturbed,
                    'relative_sensitivity': (max_perturbed - min_perturbed) / base_value
                }

        return sensitivity_analysis


# ============================================================================
# PYTEST TEST CASES
# ============================================================================

@pytest.fixture
def parameter_validator():
    """Create parameter validator for testing."""
    return EngineeringParameterValidator()


class TestParameterRealism:
    """Test suite for realistic parameter calibration and validation."""

    def test_parameter_bounds_establishment(self, parameter_validator):
        """Test that all parameter bounds are properly established."""

        bounds = parameter_validator.parameter_bounds

        # Should have bounds for all critical parameters
        expected_parameters = [
            'cart_mass', 'cart_friction',
            'pendulum1_mass', 'pendulum1_length', 'pendulum1_inertia', 'joint1_friction',
            'pendulum2_mass', 'pendulum2_length', 'pendulum2_inertia', 'joint2_friction',
            'gravity', 'max_force'
        ]

        for param in expected_parameters:
            assert param in bounds, f"Missing parameter bounds for {param}"

            bound = bounds[param]
            assert bound.min_value < bound.max_value, f"Invalid bounds for {param}"
            assert bound.typical_range[0] <= bound.typical_range[1], f"Invalid typical range for {param}"
            assert bound.min_value <= bound.typical_range[0], f"Typical range below minimum for {param}"
            assert bound.typical_range[1] <= bound.max_value, f"Typical range above maximum for {param}"
            assert len(bound.unit) > 0, f"Missing unit for {param}"
            assert len(bound.justification) > 0, f"Missing justification for {param}"

    def test_individual_parameter_validation(self, parameter_validator):
        """Test individual parameter validation logic."""

        # Test valid parameters
        valid, msg = parameter_validator.validate_parameter_value('cart_mass', 1.0)
        assert valid, f"Should validate typical cart mass: {msg}"

        valid, msg = parameter_validator.validate_parameter_value('gravity', 9.81)
        assert valid, f"Should validate Earth gravity: {msg}"

        # Test invalid parameters - below minimum
        valid, msg = parameter_validator.validate_parameter_value('cart_mass', -1.0)
        assert not valid, "Should reject negative mass"
        assert "below minimum" in msg, "Should explain why parameter is invalid"

        # Test invalid parameters - above maximum
        valid, msg = parameter_validator.validate_parameter_value('cart_mass', 100.0)
        assert not valid, "Should reject unreasonably large mass"
        assert "above maximum" in msg, "Should explain why parameter is invalid"

        # Test unknown parameter
        valid, msg = parameter_validator.validate_parameter_value('unknown_param', 1.0)
        assert not valid, "Should reject unknown parameters"
        assert "Unknown parameter" in msg, "Should explain unknown parameter"

    def test_physics_consistency_validation(self, parameter_validator):
        """Test physics consistency checks between parameters."""

        # Test valid, consistent parameters
        valid_params = {
            'cart_mass': 1.0,
            'pendulum1_mass': 0.3,
            'pendulum2_mass': 0.2,
            'pendulum1_length': 0.5,
            'pendulum2_length': 0.3,
            'pendulum1_inertia': 0.025,  # ≈ (1/3) * 0.3 * 0.5²
            'pendulum2_inertia': 0.006,  # ≈ (1/3) * 0.2 * 0.3²
            'max_force': 50.0
        }

        is_consistent, errors = parameter_validator.validate_physics_consistency(valid_params)
        assert is_consistent, f"Valid parameters should be consistent. Errors: {errors}"

        # Test inconsistent mass ratios
        bad_mass_params = valid_params.copy()
        bad_mass_params['pendulum1_mass'] = 5.0  # Much larger than cart

        is_consistent, errors = parameter_validator.validate_physics_consistency(bad_mass_params)
        assert not is_consistent, "Should detect bad mass ratios"
        assert any("mass ratio" in error for error in errors), "Should explain mass ratio problem"

        # Test inconsistent inertia
        bad_inertia_params = valid_params.copy()
        bad_inertia_params['pendulum1_inertia'] = 0.5  # Much too large for rod

        is_consistent, errors = parameter_validator.validate_physics_consistency(bad_inertia_params)
        assert not is_consistent, "Should detect inconsistent inertia"
        assert any("inertia" in error.lower() for error in errors), "Should explain inertia problem"

    def test_realistic_scenarios_creation(self, parameter_validator):
        """Test creation and validation of realistic scenarios."""

        scenarios = parameter_validator.realistic_scenarios

        # Should have multiple realistic scenarios
        assert len(scenarios) >= 3, "Should provide multiple realistic scenarios"

        # Validate each scenario
        for scenario in scenarios:
            assert len(scenario.name) > 0, "Scenario should have name"
            assert len(scenario.description) > 0, "Scenario should have description"
            assert isinstance(scenario.hardware_config, HardwareConfiguration), "Should specify hardware config"

            # Validate physics parameters
            assert len(scenario.physics_params) >= 10, "Should specify all critical physics parameters"

            # Validate control gains
            assert len(scenario.control_gains) >= 2, "Should provide gains for multiple controllers"

            # Validate expected performance
            assert len(scenario.expected_performance) >= 3, "Should specify expected performance metrics"

            # All expected performance ranges should be valid
            for metric_name, (min_val, max_val) in scenario.expected_performance.items():
                assert min_val < max_val, f"Invalid performance range for {metric_name}"
                assert min_val >= 0, f"Negative performance value for {metric_name}"

    def test_control_gain_validation(self, parameter_validator):
        """Test control gain validation for different controller types."""

        # Test classical SMC gains
        classical_gains = [10.0, 5.0, 3.0, 2.0, 50.0, 1.0]
        validation = parameter_validator.validate_control_gains(SMCType.CLASSICAL, classical_gains)

        assert validation['correct_count'], "Should have correct number of classical SMC gains"
        assert validation['all_positive'], "All classical SMC gains should be positive"
        assert validation['reasonable_proportional'], "Proportional gains should be reasonable"
        assert validation['reasonable_derivative'], "Derivative gains should be reasonable"

        # Test adaptive SMC gains
        adaptive_gains = [8.0, 4.0, 2.5, 1.5, 0.5]
        validation = parameter_validator.validate_control_gains(SMCType.ADAPTIVE, adaptive_gains)

        assert validation['correct_count'], "Should have correct number of adaptive SMC gains"
        assert validation['all_positive'], "All adaptive SMC gains should be positive"

        # Test invalid gains - wrong count
        wrong_count_gains = [1.0, 2.0]  # Too few for classical SMC
        validation = parameter_validator.validate_control_gains(SMCType.CLASSICAL, wrong_count_gains)

        assert not validation['correct_count'], "Should detect wrong gain count"

        # Test invalid gains - negative values
        negative_gains = [10.0, -5.0, 3.0, 2.0, 50.0, 1.0]
        validation = parameter_validator.validate_control_gains(SMCType.CLASSICAL, negative_gains)

        assert not validation['all_positive'], "Should detect negative gains"

    def test_scenario_consistency_validation(self, parameter_validator):
        """Test complete scenario consistency validation."""

        # Get a realistic scenario
        desktop_scenario = parameter_validator.get_realistic_scenario_by_name("Desktop Lab Setup")
        assert desktop_scenario is not None, "Should find Desktop Lab Setup scenario"

        # Validate scenario consistency
        validation = parameter_validator.validate_scenario_consistency(desktop_scenario)

        assert validation['physics_consistent'], "Desktop scenario physics should be consistent"
        assert validation['all_parameters_in_bounds'], "All parameters should be within bounds"
        assert validation['all_gains_valid'], "All control gains should be valid"
        assert validation['performance_ranges_valid'], "Performance ranges should be valid"

        # Test modified scenario with inconsistent physics
        bad_scenario = RealisticScenario(
            name="Bad Test Scenario",
            hardware_config=HardwareConfiguration.DESKTOP_LAB,
            description="Test scenario with bad parameters",
            physics_params={
                'cart_mass': 0.1,
                'pendulum1_mass': 10.0,  # Much too large relative to cart
                'pendulum1_length': 0.5,
                'pendulum1_inertia': 0.025,
                'gravity': 9.81,
                'max_force': 50.0
            },
            control_gains={
                'classical': [10.0, 5.0, 3.0, 2.0, 50.0, 1.0]
            },
            expected_performance={
                'settling_time': (3.0, 8.0)
            },
            validation_notes="Test scenario"
        )

        validation = parameter_validator.validate_scenario_consistency(bad_scenario)
        assert not validation['physics_consistent'], "Should detect physics inconsistency"

    def test_parameter_sensitivity_analysis(self, parameter_validator):
        """Test parameter sensitivity analysis functionality."""

        # Test with Desktop Lab parameters
        desktop_scenario = parameter_validator.get_realistic_scenario_by_name("Desktop Lab Setup")

        sensitivity = parameter_validator.analyze_parameter_sensitivity(
            desktop_scenario.physics_params,
            perturbation_percent=15.0
        )

        # Should analyze all provided parameters
        assert len(sensitivity) == len(desktop_scenario.physics_params), "Should analyze all parameters"

        # Validate sensitivity analysis structure
        for param_name, analysis in sensitivity.items():
            assert 'base_value' in analysis, f"Missing base value for {param_name}"
            assert 'min_perturbed' in analysis, f"Missing min perturbed for {param_name}"
            assert 'max_perturbed' in analysis, f"Missing max perturbed for {param_name}"
            assert 'perturbation_range' in analysis, f"Missing perturbation range for {param_name}"
            assert 'relative_sensitivity' in analysis, f"Missing relative sensitivity for {param_name}"

            # Validate analysis values
            assert analysis['min_perturbed'] <= analysis['base_value'], f"Min perturbed should be <= base for {param_name}"
            assert analysis['base_value'] <= analysis['max_perturbed'], f"Base should be <= max perturbed for {param_name}"
            assert analysis['perturbation_range'] >= 0, f"Perturbation range should be positive for {param_name}"
            assert analysis['relative_sensitivity'] >= 0, f"Relative sensitivity should be positive for {param_name}"

    def test_hardware_configuration_scenarios(self, parameter_validator):
        """Test that scenarios cover different hardware configurations."""

        scenarios = parameter_validator.realistic_scenarios

        # Should cover major hardware configurations
        hardware_configs = {scenario.hardware_config for scenario in scenarios}

        expected_configs = [
            HardwareConfiguration.DESKTOP_LAB,
            HardwareConfiguration.INDUSTRIAL_PROTOTYPE,
            HardwareConfiguration.RESEARCH_PLATFORM,
            HardwareConfiguration.EDUCATIONAL_KIT
        ]

        for expected_config in expected_configs:
            assert expected_config in hardware_configs, f"Missing scenario for {expected_config.value}"

        # Each hardware configuration should have different parameter ranges
        scenario_params = {}
        for scenario in scenarios:
            scenario_params[scenario.hardware_config] = scenario.physics_params

        # Industrial should have larger masses and forces than desktop lab
        if (HardwareConfiguration.INDUSTRIAL_PROTOTYPE in scenario_params and
            HardwareConfiguration.DESKTOP_LAB in scenario_params):

            industrial = scenario_params[HardwareConfiguration.INDUSTRIAL_PROTOTYPE]
            desktop = scenario_params[HardwareConfiguration.DESKTOP_LAB]

            assert industrial['cart_mass'] > desktop['cart_mass'], "Industrial should have larger cart mass"
            assert industrial['max_force'] > desktop['max_force'], "Industrial should have larger actuator"

    def test_engineering_validation_levels(self, parameter_validator):
        """Test that parameters are validated at appropriate engineering levels."""

        bounds = parameter_validator.parameter_bounds

        # Physics bounds should be most restrictive
        physics_params = [name for name, bound in bounds.items()
                         if bound.validation_level == ParameterValidationLevel.PHYSICS_BOUNDS]
        assert len(physics_params) > 0, "Should have physics-level validations"

        # Engineering limits should be practical
        engineering_params = [name for name, bound in bounds.items()
                            if bound.validation_level == ParameterValidationLevel.ENGINEERING_LIMITS]
        assert len(engineering_params) > 0, "Should have engineering-level validations"

        # Mass and inertia should be physics-validated
        assert 'cart_mass' in physics_params, "Cart mass should be physics-validated"
        assert 'pendulum1_inertia' in physics_params, "Inertia should be physics-validated"

        # Friction parameters should be engineering-validated
        friction_params = [name for name in bounds.keys() if 'friction' in name]
        for friction_param in friction_params:
            bound = bounds[friction_param]
            assert bound.validation_level in [ParameterValidationLevel.ENGINEERING_LIMITS,
                                            ParameterValidationLevel.PHYSICS_BOUNDS], \
                f"Friction parameter {friction_param} should be engineering/physics validated"

    def test_benchmark_parameter_meaningfulness(self, parameter_validator):
        """Test that benchmark parameters produce meaningful results."""

        # Test with realistic scenario
        research_scenario = parameter_validator.get_realistic_scenario_by_name("Research Platform")

        # Create mock dynamics to test parameter meaningfulness
        physics_config = wrap_physics_config(research_scenario.physics_params)
        dynamics = SimplifiedDIPDynamics(physics_config)

        # Test that system is controllable (not completely unstable)
        test_state = np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0])  # Small angles
        test_control = 1.0

        state_dot = dynamics.compute_dynamics(test_state, test_control)

        # System should respond to control input
        assert np.any(np.abs(state_dot) > 1e-6), "System should respond to control input"
        assert np.all(np.isfinite(state_dot)), "System dynamics should be numerically stable"

        # Control authority should be reasonable
        max_acceleration = abs(state_dot[3])  # Cart acceleration
        assert max_acceleration < 50.0, "Control authority should not be excessive"
        assert max_acceleration > 0.1, "Control authority should be sufficient"


if __name__ == "__main__":
    # Run standalone parameter validation
    validator = EngineeringParameterValidator()

    print("Engineering Parameter Validation Report")
    print("=" * 50)

    # Test all realistic scenarios
    for scenario in validator.realistic_scenarios:
        print(f"\nValidating: {scenario.name}")
        print(f"Hardware: {scenario.hardware_config.value}")

        validation = validator.validate_scenario_consistency(scenario)

        if all(validation.values()):
            print("✅ All validations PASSED")
        else:
            print("❌ Some validations FAILED:")
            for check, result in validation.items():
                if not result:
                    print(f"  - {check}: FAILED")

        # Show key parameters
        params = scenario.physics_params
        print(f"  Cart mass: {params['cart_mass']} kg")
        print(f"  Max force: {params['max_force']} N")
        print(f"  Pendulum lengths: {params['pendulum1_length']:.2f}m, {params['pendulum2_length']:.2f}m")

    print(f"\nParameter bounds established for {len(validator.parameter_bounds)} parameters")
    print(f"Realistic scenarios created: {len(validator.realistic_scenarios)}")
    print("\n✅ Parameter validation framework ready for benchmarking")