#==========================================================================================\\\
#=================== src/controllers/smc/core/gain_validation.py ====================\\\
#==========================================================================================\\\

"""
Gain Validation for SMC Controllers.

Provides centralized validation logic for SMC controller parameters.
Ensures gains satisfy stability requirements from sliding mode theory.

Mathematical Requirements:
- Surface gains (k1, k2, λ1, λ2) must be positive for Hurwitz stability
- Switching gains (K) must be positive to guarantee reaching condition
- Derivative gains (kd) must be non-negative for damping
- Adaptation gains must satisfy boundedness conditions
"""

from typing import List, Union, Dict, Optional, Sequence
import numpy as np
from dataclasses import dataclass
from enum import Enum


class SMCControllerType(Enum):
    """SMC controller types with different gain requirements."""
    CLASSICAL = "classical"
    ADAPTIVE = "adaptive"
    SUPER_TWISTING = "super_twisting"
    HYBRID = "hybrid"


@dataclass
class GainBounds:
    """Bounds for SMC controller gains."""
    min_value: float
    max_value: float
    name: str
    description: str

    def validate(self, value: float) -> bool:
        """Check if value is within bounds."""
        return self.min_value <= value <= self.max_value


class SMCGainValidator:
    """
    Centralized gain validation for all SMC controller types.

    Provides type-specific validation rules based on SMC theory requirements.
    """

    def __init__(self):
        """Initialize gain validator with standard bounds."""
        self._gain_bounds = self._initialize_standard_bounds()

    def _initialize_standard_bounds(self) -> Dict[SMCControllerType, List[GainBounds]]:
        """Initialize standard gain bounds for each controller type."""
        return {
            SMCControllerType.CLASSICAL: [
                GainBounds(0.1, 1000.0, "k1", "Joint 1 position gain"),
                GainBounds(0.1, 1000.0, "k2", "Joint 2 position gain"),
                GainBounds(0.1, 1000.0, "lam1", "Joint 1 velocity gain"),
                GainBounds(0.1, 1000.0, "lam2", "Joint 2 velocity gain"),
                GainBounds(0.1, 1000.0, "K", "Switching gain"),
                GainBounds(0.0, 1000.0, "kd", "Derivative gain (non-negative)"),
            ],
            SMCControllerType.ADAPTIVE: [
                GainBounds(0.1, 1000.0, "k1", "Joint 1 position gain"),
                GainBounds(0.1, 1000.0, "k2", "Joint 2 position gain"),
                GainBounds(0.1, 1000.0, "lam1", "Joint 1 velocity gain"),
                GainBounds(0.1, 1000.0, "lam2", "Joint 2 velocity gain"),
                GainBounds(0.01, 10.0, "gamma", "Adaptation rate"),
            ],
            SMCControllerType.SUPER_TWISTING: [
                GainBounds(1.0, 1000.0, "K1", "First twisting gain"),
                GainBounds(1.0, 1000.0, "K2", "Second twisting gain"),
                GainBounds(0.1, 1000.0, "k1", "Joint 1 position gain"),
                GainBounds(0.1, 1000.0, "k2", "Joint 2 position gain"),
                GainBounds(0.1, 1000.0, "lam1", "Joint 1 velocity gain"),
                GainBounds(0.1, 1000.0, "lam2", "Joint 2 velocity gain"),
            ],
            SMCControllerType.HYBRID: [
                GainBounds(0.1, 1000.0, "c1", "First surface coefficient"),
                GainBounds(0.1, 1000.0, "lambda1", "First surface slope"),
                GainBounds(0.1, 1000.0, "c2", "Second surface coefficient"),
                GainBounds(0.1, 1000.0, "lambda2", "Second surface slope"),
            ]
        }

    def validate_gains(self, gains: Union[List[float], np.ndarray],
                      controller_type: Union[SMCControllerType, str]) -> Dict[str, any]:
        """
        Validate gains for specific SMC controller type.

        Args:
            gains: List or array of gain values
            controller_type: Type of SMC controller

        Returns:
            Validation result dictionary
        """
        # Normalize controller type
        if isinstance(controller_type, str):
            try:
                controller_type = SMCControllerType(controller_type.lower())
            except ValueError:
                return {
                    'valid': False,
                    'error': f"Unknown controller type: {controller_type}"
                }

        # Get gain bounds for this controller type
        if controller_type not in self._gain_bounds:
            return {
                'valid': False,
                'error': f"No validation rules for controller type: {controller_type}"
            }

        bounds_list = self._gain_bounds[controller_type]
        gains_array = np.asarray(gains, dtype=float)

        # Check gain count
        expected_count = len(bounds_list)
        if len(gains_array) < expected_count:
            return {
                'valid': False,
                'error': f"{controller_type.value} requires at least {expected_count} gains, got {len(gains_array)}"
            }

        # Validate each gain
        violations = []
        for i, (gain_value, bounds) in enumerate(zip(gains_array, bounds_list)):
            if not bounds.validate(gain_value):
                violations.append({
                    'index': i,
                    'name': bounds.name,
                    'value': gain_value,
                    'bounds': (bounds.min_value, bounds.max_value),
                    'description': bounds.description
                })

        # Check for NaN or infinite values
        if not np.all(np.isfinite(gains_array)):
            violations.append({
                'error': 'Gains contain NaN or infinite values',
                'invalid_indices': np.where(~np.isfinite(gains_array))[0].tolist()
            })

        # Return validation result
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'controller_type': controller_type.value,
            'gains_checked': len(bounds_list),
            'gains_provided': len(gains_array)
        }

    def validate_stability_conditions(self, gains: Union[List[float], np.ndarray],
                                    controller_type: Union[SMCControllerType, str]) -> Dict[str, any]:
        """
        Validate SMC-specific stability conditions.

        Args:
            gains: Gain values
            controller_type: Type of SMC controller

        Returns:
            Stability analysis result
        """
        # Normalize controller type
        if isinstance(controller_type, str):
            controller_type = SMCControllerType(controller_type.lower())

        gains_array = np.asarray(gains, dtype=float)
        stability_issues = []

        if controller_type == SMCControllerType.CLASSICAL:
            # Classical SMC: surface gains must be positive
            if len(gains_array) >= 4:
                surface_gains = gains_array[:4]  # [k1, k2, lam1, lam2]
                if any(g <= 0 for g in surface_gains):
                    stability_issues.append("Surface gains [k1, k2, λ1, λ2] must be positive for Hurwitz stability")

            # Switching gain must be positive
            if len(gains_array) >= 5 and gains_array[4] <= 0:
                stability_issues.append("Switching gain K must be positive for reaching condition")

        elif controller_type == SMCControllerType.ADAPTIVE:
            # Adaptive SMC: surface gains and adaptation rate
            if len(gains_array) >= 4:
                surface_gains = gains_array[:4]
                if any(g <= 0 for g in surface_gains):
                    stability_issues.append("Surface gains must be positive for stability")

            # Adaptation rate bounds
            if len(gains_array) >= 5:
                gamma = gains_array[4]
                if gamma <= 0:
                    stability_issues.append("Adaptation rate γ must be positive")
                if gamma > 1.0:
                    stability_issues.append("Large adaptation rate may cause instability")

        elif controller_type == SMCControllerType.SUPER_TWISTING:
            # Super-twisting: specific gain relationships
            if len(gains_array) >= 2:
                K1, K2 = gains_array[0], gains_array[1]
                if K1 <= 0 or K2 <= 0:
                    stability_issues.append("Twisting gains K1, K2 must be positive")

                # Super-twisting stability condition: K1 > K2 > 0
                if K2 >= K1:
                    stability_issues.append("Super-twisting stability requires K1 > K2 > 0")

        elif controller_type == SMCControllerType.HYBRID:
            # Hybrid controller: all gains positive
            if any(g <= 0 for g in gains_array):
                stability_issues.append("All hybrid controller gains must be positive")

        return {
            'stable': len(stability_issues) == 0,
            'issues': stability_issues,
            'controller_type': controller_type.value
        }

    def get_recommended_ranges(self, controller_type: Union[SMCControllerType, str]) -> Dict[str, tuple]:
        """
        Get recommended gain ranges for controller type.

        Args:
            controller_type: Type of SMC controller

        Returns:
            Dictionary mapping gain names to (min, max) ranges
        """
        if isinstance(controller_type, str):
            controller_type = SMCControllerType(controller_type.lower())

        if controller_type not in self._gain_bounds:
            return {}

        bounds_list = self._gain_bounds[controller_type]
        return {
            bounds.name: (bounds.min_value, bounds.max_value)
            for bounds in bounds_list
        }

    def update_bounds(self, controller_type: Union[SMCControllerType, str],
                     gain_name: str, min_val: float, max_val: float) -> None:
        """
        Update gain bounds for specific controller and gain.

        Args:
            controller_type: Type of SMC controller
            gain_name: Name of gain to update
            min_val: Minimum value
            max_val: Maximum value
        """
        if isinstance(controller_type, str):
            controller_type = SMCControllerType(controller_type.lower())

        if controller_type not in self._gain_bounds:
            raise ValueError(f"Unknown controller type: {controller_type}")

        bounds_list = self._gain_bounds[controller_type]
        for bounds in bounds_list:
            if bounds.name == gain_name:
                bounds.min_value = min_val
                bounds.max_value = max_val
                return

        raise ValueError(f"Gain '{gain_name}' not found for controller type {controller_type}")


# Convenience functions for direct validation
def validate_smc_gains(gains: Union[List[float], np.ndarray],
                      controller_type: str = "classical") -> bool:
    """
    Quick validation of SMC gains.

    Args:
        gains: Gain values
        controller_type: Type of SMC controller

    Returns:
        True if gains are valid, False otherwise
    """
    validator = SMCGainValidator()
    result = validator.validate_gains(gains, controller_type)
    return result['valid']


def check_stability_conditions(gains: Union[List[float], np.ndarray],
                              controller_type: str = "classical") -> bool:
    """
    Quick check of SMC stability conditions.

    Args:
        gains: Gain values
        controller_type: Type of SMC controller

    Returns:
        True if stability conditions are satisfied, False otherwise
    """
    validator = SMCGainValidator()
    result = validator.validate_stability_conditions(gains, controller_type)
    return result['stable']


def get_gain_bounds_for_controller(controller_type: str) -> Dict[str, tuple]:
    """
    Get gain bounds for specific controller type.

    Args:
        controller_type: Type of SMC controller

    Returns:
        Dictionary of gain bounds
    """
    validator = SMCGainValidator()
    return validator.get_recommended_ranges(controller_type)