#==========================================================================================\\\
#=============================== experimental_design.py ===============================\\\
#==========================================================================================\\\
"""
Standardized experimental design for SMC controllers comparison.

This module defines test scenarios, performance metrics, and experimental
protocols for comparing Classical SMC, Adaptive SMC, STA SMC, and Hybrid SMC
controllers on the double inverted pendulum system.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Callable, Tuple
from enum import Enum


class ControllerType(Enum):
    """Enumeration of controller types for comparison."""
    CLASSICAL_SMC = "Classical SMC"
    ADAPTIVE_SMC = "Adaptive SMC"
    STA_SMC = "STA SMC"
    HYBRID_ADAPTIVE_STA = "Hybrid Adaptive-STA SMC"


@dataclass
class TestScenario:
    """Defines a standardized test scenario."""
    name: str
    description: str
    initial_state: np.ndarray
    reference_trajectory: Callable[[float], np.ndarray]
    disturbance_function: Callable[[float], float]
    parameter_uncertainty: Dict[str, float]
    noise_level: float
    duration: float
    dt: float = 0.01


@dataclass
class PerformanceMetrics:
    """Container for all performance metrics."""
    # Time domain metrics
    settling_time: float
    rise_time: float
    overshoot: float
    steady_state_error: float

    # Control quality metrics
    chattering_index: float
    control_energy: float
    rms_control_effort: float

    # Robustness metrics
    disturbance_rejection: float
    noise_sensitivity: float
    parameter_sensitivity: float


class ExperimentalDesign:
    """Comprehensive experimental design for SMC comparison study."""

    def __init__(self):
        self.scenarios = self._create_test_scenarios()
        self.metrics_calculator = MetricsCalculator()

    def _create_test_scenarios(self) -> List[TestScenario]:
        """Create standardized test scenarios based on literature review."""

        scenarios = []

        # Scenario 1: Nominal Performance - Standard Swing-up
        scenarios.append(TestScenario(
            name="S1_Nominal_Swingup",
            description="Standard swing-up from hanging position to upright",
            initial_state=np.array([0, 0, np.pi, np.pi, 0, 0, 0, 0]),  # Both pendulums hanging
            reference_trajectory=lambda t: np.array([0, 0, 0, 0]),  # Upright position
            disturbance_function=lambda t: 0.0,  # No disturbance
            parameter_uncertainty={},  # Nominal parameters
            noise_level=0.0,  # No noise
            duration=15.0
        ))

        # Scenario 2: Step Disturbance Rejection
        scenarios.append(TestScenario(
            name="S2_Step_Disturbance",
            description="Step disturbance rejection during stabilization",
            initial_state=np.array([0, 0, 0.1, 0.1, 0, 0, 0, 0]),  # Near upright
            reference_trajectory=lambda t: np.array([0, 0, 0, 0]),
            disturbance_function=lambda t: 5.0 if 5.0 <= t <= 7.0 else 0.0,  # 5N step for 2s
            parameter_uncertainty={},
            noise_level=0.0,
            duration=12.0
        ))

        # Scenario 3: Sinusoidal Disturbance
        scenarios.append(TestScenario(
            name="S3_Sinusoidal_Disturbance",
            description="Sinusoidal disturbance tracking performance",
            initial_state=np.array([0, 0, 0.05, 0.05, 0, 0, 0, 0]),
            reference_trajectory=lambda t: np.array([0, 0, 0, 0]),
            disturbance_function=lambda t: 3.0 * np.sin(2*np.pi*0.5*t),  # 0.5 Hz, 3N amplitude
            parameter_uncertainty={},
            noise_level=0.0,
            duration=10.0
        ))

        # Scenario 4: Parameter Uncertainty - Mass Variation
        scenarios.append(TestScenario(
            name="S4_Mass_Uncertainty",
            description="Performance under mass parameter uncertainty",
            initial_state=np.array([0, 0, np.pi, np.pi, 0, 0, 0, 0]),
            reference_trajectory=lambda t: np.array([0, 0, 0, 0]),
            disturbance_function=lambda t: 0.0,
            parameter_uncertainty={
                'cart_mass': 0.2,      # ±20% variation
                'pendulum1_mass': 0.15, # ±15% variation
                'pendulum2_mass': 0.15  # ±15% variation
            },
            noise_level=0.0,
            duration=15.0
        ))

        # Scenario 5: Length Parameter Uncertainty
        scenarios.append(TestScenario(
            name="S5_Length_Uncertainty",
            description="Performance under length parameter uncertainty",
            initial_state=np.array([0, 0, 0.2, 0.2, 0, 0, 0, 0]),
            reference_trajectory=lambda t: np.array([0, 0, 0, 0]),
            disturbance_function=lambda t: 0.0,
            parameter_uncertainty={
                'pendulum1_length': 0.1,  # ±10% variation
                'pendulum2_length': 0.1   # ±10% variation
            },
            noise_level=0.0,
            duration=12.0
        ))

        # Scenario 6: Measurement Noise Sensitivity
        scenarios.append(TestScenario(
            name="S6_Noise_Sensitivity",
            description="Robustness to measurement noise",
            initial_state=np.array([0, 0, 0.1, 0.1, 0, 0, 0, 0]),
            reference_trajectory=lambda t: np.array([0, 0, 0, 0]),
            disturbance_function=lambda t: 0.0,
            parameter_uncertainty={},
            noise_level=0.01,  # 1% RMS noise on all measurements
            duration=10.0
        ))

        # Scenario 7: Large Initial Deviation
        scenarios.append(TestScenario(
            name="S7_Large_Initial_Deviation",
            description="Recovery from large initial deviations",
            initial_state=np.array([0, 0, 0.5, 0.3, 0, 0, 0, 0]),  # Large angles
            reference_trajectory=lambda t: np.array([0, 0, 0, 0]),
            disturbance_function=lambda t: 0.0,
            parameter_uncertainty={},
            noise_level=0.0,
            duration=8.0
        ))

        # Scenario 8: Tracking Performance
        scenarios.append(TestScenario(
            name="S8_Reference_Tracking",
            description="Cart position reference tracking",
            initial_state=np.array([0, 0, 0, 0, 0, 0, 0, 0]),  # Start upright
            reference_trajectory=lambda t: np.array([
                0.5 * np.sin(2*np.pi*0.2*t),  # 0.2 Hz cart position
                0, 0, 0
            ]),
            disturbance_function=lambda t: 0.0,
            parameter_uncertainty={},
            noise_level=0.005,  # Low noise during tracking
            duration=15.0
        ))

        return scenarios

    def get_monte_carlo_parameters(self, base_scenario: TestScenario, n_trials: int = 100) -> List[Dict]:
        """Generate Monte Carlo parameter variations for statistical analysis."""

        parameter_sets = []

        for _ in range(n_trials):
            params = {}

            # Generate random parameter variations
            for param, uncertainty in base_scenario.parameter_uncertainty.items():
                # Uniform distribution: ±uncertainty as percentage
                variation = np.random.uniform(-uncertainty, uncertainty)
                params[param] = 1.0 + variation

            parameter_sets.append(params)

        return parameter_sets

    def get_experimental_matrix(self) -> Dict[str, List[TestScenario]]:
        """Return organized experimental matrix by test category."""

        matrix = {
            'nominal_performance': [s for s in self.scenarios if 'Nominal' in s.name],
            'disturbance_rejection': [s for s in self.scenarios if 'Disturbance' in s.name],
            'parameter_uncertainty': [s for s in self.scenarios if 'Uncertainty' in s.name],
            'noise_sensitivity': [s for s in self.scenarios if 'Noise' in s.name],
            'tracking_performance': [s for s in self.scenarios if 'Tracking' in s.name],
            'large_deviations': [s for s in self.scenarios if 'Large' in s.name]
        }

        return matrix


class MetricsCalculator:
    """Calculate standardized performance metrics from simulation data."""

    def calculate_all_metrics(self,
                            time: np.ndarray,
                            states: np.ndarray,
                            control: np.ndarray,
                            reference: np.ndarray) -> PerformanceMetrics:
        """Calculate all performance metrics from simulation data."""

        return PerformanceMetrics(
            settling_time=self._calculate_settling_time(time, states, reference),
            rise_time=self._calculate_rise_time(time, states, reference),
            overshoot=self._calculate_overshoot(states, reference),
            steady_state_error=self._calculate_steady_state_error(states, reference),
            chattering_index=self._calculate_chattering_index(control),
            control_energy=self._calculate_control_energy(time, control),
            rms_control_effort=self._calculate_rms_control(control),
            disturbance_rejection=self._calculate_disturbance_rejection(states),
            noise_sensitivity=self._calculate_noise_sensitivity(states),
            parameter_sensitivity=self._calculate_parameter_sensitivity(states)
        )

    def _calculate_settling_time(self, time: np.ndarray, states: np.ndarray,
                               reference: np.ndarray, tolerance: float = 0.02) -> float:
        """Calculate 2% settling time for pendulum angles."""
        # Focus on pendulum angles (θ1, θ2)
        angle_errors = np.abs(states[:, 2:4] - reference[:, 2:4])
        max_error = np.max(angle_errors, axis=1)

        # Find last time when error exceeded tolerance
        settling_indices = np.where(max_error > tolerance)[0]

        if len(settling_indices) == 0:
            return 0.0  # Already settled
        else:
            return time[settling_indices[-1]]

    def _calculate_rise_time(self, time: np.ndarray, states: np.ndarray,
                           reference: np.ndarray) -> float:
        """Calculate 10%-90% rise time for the dominant angle."""
        # Use θ1 (first pendulum angle) as primary metric
        angle_response = np.abs(states[:, 2] - reference[:, 2])

        if len(angle_response) == 0:
            return 0.0

        final_value = angle_response[-1]

        # Find 10% and 90% points
        ten_percent = 0.1 * final_value
        ninety_percent = 0.9 * final_value

        t10_idx = np.where(angle_response >= ten_percent)[0]
        t90_idx = np.where(angle_response >= ninety_percent)[0]

        if len(t10_idx) == 0 or len(t90_idx) == 0:
            return 0.0

        return time[t90_idx[0]] - time[t10_idx[0]]

    def _calculate_overshoot(self, states: np.ndarray, reference: np.ndarray) -> float:
        """Calculate maximum overshoot percentage."""
        angle_errors = np.abs(states[:, 2:4] - reference[:, 2:4])
        max_error = np.max(angle_errors)
        final_error = np.mean(angle_errors[-10:])  # Average of last 10 points

        if final_error == 0:
            return 0.0

        overshoot = ((max_error - final_error) / final_error) * 100
        return max(0.0, overshoot)

    def _calculate_steady_state_error(self, states: np.ndarray, reference: np.ndarray) -> float:
        """Calculate RMS steady-state error for last 20% of simulation."""
        n_steady = max(1, len(states) // 5)  # Last 20% of data
        steady_states = states[-n_steady:]
        steady_ref = reference[-n_steady:]

        errors = steady_states[:, 2:4] - steady_ref[:, 2:4]  # Focus on angles
        return np.sqrt(np.mean(errors**2))

    def _calculate_chattering_index(self, control: np.ndarray) -> float:
        """Calculate chattering index based on control signal variations."""
        if len(control) < 2:
            return 0.0

        # High-frequency content measurement
        control_diff = np.diff(control.flatten())
        chattering = np.sqrt(np.mean(control_diff**2))

        return chattering

    def _calculate_control_energy(self, time: np.ndarray, control: np.ndarray) -> float:
        """Calculate total control energy (integral of |u|²)."""
        if len(time) < 2:
            return 0.0

        dt = time[1] - time[0]
        energy = np.sum(control**2) * dt

        return energy

    def _calculate_rms_control(self, control: np.ndarray) -> float:
        """Calculate RMS control effort."""
        return np.sqrt(np.mean(control**2))

    def _calculate_disturbance_rejection(self, states: np.ndarray) -> float:
        """Placeholder for disturbance rejection metric."""
        # This would be calculated by comparing performance with/without disturbances
        return 0.0

    def _calculate_noise_sensitivity(self, states: np.ndarray) -> float:
        """Placeholder for noise sensitivity metric."""
        # This would be calculated by comparing performance with/without noise
        return 0.0

    def _calculate_parameter_sensitivity(self, states: np.ndarray) -> float:
        """Placeholder for parameter sensitivity metric."""
        # This would be calculated by comparing performance across parameter variations
        return 0.0


# Usage example
if __name__ == "__main__":
    # Create experimental design
    experiment = ExperimentalDesign()

    # Print scenario summary
    print("=== SMC Comparison Experimental Design ===")
    print(f"Total scenarios: {len(experiment.scenarios)}")

    matrix = experiment.get_experimental_matrix()
    for category, scenarios in matrix.items():
        print(f"\n{category.replace('_', ' ').title()}: {len(scenarios)} scenarios")
        for scenario in scenarios:
            print(f"  - {scenario.name}: {scenario.description}")