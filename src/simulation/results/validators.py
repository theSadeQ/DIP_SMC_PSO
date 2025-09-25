#==========================================================================================\\\
#======================= src/simulation/results/validators.py =======================\\\
#==========================================================================================\\\

"""Result validation and sanity checking."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import numpy as np


class ResultValidator:
    """Validate simulation results for correctness and sanity."""

    @staticmethod
    def validate_basic_structure(result_container: Any) -> Tuple[bool, List[str]]:
        """Validate basic result structure."""
        errors = []

        states = result_container.get_states()
        times = result_container.get_times()

        if len(states) == 0:
            errors.append("Empty state trajectory")

        if len(times) == 0:
            errors.append("Empty time vector")

        if len(states) != len(times):
            errors.append(f"State/time length mismatch: {len(states)} vs {len(times)}")

        # Check for finite values
        if not np.all(np.isfinite(states)):
            errors.append("Non-finite values in states")

        if not np.all(np.isfinite(times)):
            errors.append("Non-finite values in times")

        return len(errors) == 0, errors

    @staticmethod
    def validate_time_consistency(times: np.ndarray, tolerance: float = 1e-10) -> Tuple[bool, List[str]]:
        """Validate time vector consistency."""
        errors = []

        if len(times) < 2:
            return True, errors

        # Check monotonic increasing
        time_diffs = np.diff(times)
        if np.any(time_diffs <= tolerance):
            errors.append("Time vector not strictly increasing")

        # Check uniform spacing (optional)
        dt_variation = np.std(time_diffs)
        if dt_variation > tolerance:
            errors.append(f"Non-uniform time spacing (std: {dt_variation})")

        return len(errors) == 0, errors

    @staticmethod
    def validate_physical_constraints(states: np.ndarray, bounds: Dict[str, Tuple[float, float]]) -> Tuple[bool, List[str]]:
        """Validate physical constraint satisfaction."""
        errors = []

        for constraint_name, (lower, upper) in bounds.items():
            if constraint_name == 'position':
                positions = states[:, :states.shape[1]//2]
                if np.any(positions < lower) or np.any(positions > upper):
                    errors.append(f"Position bounds violated: [{lower}, {upper}]")

            elif constraint_name == 'velocity':
                velocities = states[:, states.shape[1]//2:]
                if np.any(velocities < lower) or np.any(velocities > upper):
                    errors.append(f"Velocity bounds violated: [{lower}, {upper}]")

            elif constraint_name == 'energy':
                energy = np.sum(states**2, axis=1)
                if np.any(energy < lower) or np.any(energy > upper):
                    errors.append(f"Energy bounds violated: [{lower}, {upper}]")

        return len(errors) == 0, errors

    def comprehensive_validation(self, result_container: Any, validation_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform comprehensive result validation."""
        validation_config = validation_config or {}

        # Basic structure validation
        basic_valid, basic_errors = self.validate_basic_structure(result_container)

        # Time consistency validation
        times = result_container.get_times()
        time_valid, time_errors = self.validate_time_consistency(times)

        # Physical constraints validation
        physical_valid = True
        physical_errors = []
        if 'physical_bounds' in validation_config:
            states = result_container.get_states()
            physical_valid, physical_errors = self.validate_physical_constraints(
                states, validation_config['physical_bounds']
            )

        # Compile validation report
        overall_valid = basic_valid and time_valid and physical_valid

        return {
            'valid': overall_valid,
            'basic_structure': {
                'valid': basic_valid,
                'errors': basic_errors
            },
            'time_consistency': {
                'valid': time_valid,
                'errors': time_errors
            },
            'physical_constraints': {
                'valid': physical_valid,
                'errors': physical_errors
            }
        }