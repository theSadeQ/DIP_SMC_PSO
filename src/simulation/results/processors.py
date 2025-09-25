#==========================================================================================\\\
#======================= src/simulation/results/processors.py =======================\\\
#==========================================================================================\\\

"""Result processing and analysis tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class ResultProcessor:
    """Process and analyze simulation results."""

    @staticmethod
    def compute_statistics(states: np.ndarray) -> Dict[str, Any]:
        """Compute basic statistics for state trajectories."""
        return {
            'mean': np.mean(states, axis=0),
            'std': np.std(states, axis=0),
            'min': np.min(states, axis=0),
            'max': np.max(states, axis=0),
            'final_state': states[-1] if len(states) > 0 else None,
            'trajectory_length': len(states)
        }

    @staticmethod
    def compute_energy_metrics(states: np.ndarray) -> Dict[str, float]:
        """Compute energy-related metrics."""
        if len(states) == 0:
            return {}

        # Assume first half are positions, second half are velocities
        n_states = states.shape[1] // 2
        positions = states[:, :n_states]
        velocities = states[:, n_states:]

        kinetic_energy = 0.5 * np.sum(velocities**2, axis=1)
        potential_energy = np.sum(positions**2, axis=1)  # Simplified
        total_energy = kinetic_energy + potential_energy

        return {
            'avg_kinetic': float(np.mean(kinetic_energy)),
            'avg_potential': float(np.mean(potential_energy)),
            'avg_total': float(np.mean(total_energy)),
            'energy_variation': float(np.std(total_energy))
        }

    @staticmethod
    def compute_control_metrics(controls: np.ndarray) -> Dict[str, float]:
        """Compute control effort metrics."""
        if len(controls) == 0:
            return {}

        return {
            'rms_control': float(np.sqrt(np.mean(controls**2))),
            'max_control': float(np.max(np.abs(controls))),
            'total_effort': float(np.sum(np.abs(controls))),
            'switching_frequency': float(np.sum(np.diff(np.sign(controls)) != 0))
        }

    def analyze_trajectory(self, result_container: Any) -> Dict[str, Any]:
        """Comprehensive trajectory analysis."""
        states = result_container.get_states()
        times = result_container.get_times()

        analysis = {
            'state_statistics': self.compute_statistics(states),
            'energy_metrics': self.compute_energy_metrics(states),
            'simulation_time': float(times[-1] - times[0]) if len(times) > 1 else 0.0,
            'time_step': float(times[1] - times[0]) if len(times) > 1 else 0.0
        }

        # Add control analysis if available
        if hasattr(result_container, 'controls') and result_container.controls is not None:
            analysis['control_metrics'] = self.compute_control_metrics(result_container.controls)

        return analysis