#==========================================================================================\\\
#======================== src/simulation/safety/monitors.py ========================\\\
#==========================================================================================\\\

"""Performance and safety monitoring for simulation execution."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import numpy as np

from ..core.interfaces import PerformanceMonitor


class SimulationPerformanceMonitor(PerformanceMonitor):
    """Monitor simulation execution performance."""

    def __init__(self):
        """Initialize performance monitor."""
        self._timing_data = {}
        self._active_operations = {}

    def start_timing(self, operation: str) -> None:
        """Start timing an operation."""
        self._active_operations[operation] = time.perf_counter()

    def end_timing(self, operation: str) -> float:
        """End timing and return elapsed time."""
        if operation not in self._active_operations:
            return 0.0

        elapsed = time.perf_counter() - self._active_operations[operation]
        del self._active_operations[operation]

        if operation not in self._timing_data:
            self._timing_data[operation] = []
        self._timing_data[operation].append(elapsed)

        return elapsed

    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = {}
        for operation, times in self._timing_data.items():
            if times:
                stats[operation] = {
                    'mean': np.mean(times),
                    'std': np.std(times),
                    'min': np.min(times),
                    'max': np.max(times),
                    'count': len(times),
                    'total': np.sum(times)
                }
        return stats


class SafetyMonitor:
    """Monitor safety violations and system health."""

    def __init__(self):
        """Initialize safety monitor."""
        self.violation_count = 0
        self.violation_history = []
        self.warning_count = 0
        self.warning_history = []

    def record_violation(self, violation_type: str, message: str, step: int) -> None:
        """Record a safety violation."""
        self.violation_count += 1
        self.violation_history.append({
            'type': violation_type,
            'message': message,
            'step': step,
            'timestamp': time.time()
        })

    def record_warning(self, warning_type: str, message: str, step: int) -> None:
        """Record a safety warning."""
        self.warning_count += 1
        self.warning_history.append({
            'type': warning_type,
            'message': message,
            'step': step,
            'timestamp': time.time()
        })

    def get_safety_report(self) -> Dict[str, Any]:
        """Get comprehensive safety report."""
        return {
            'violation_count': self.violation_count,
            'warning_count': self.warning_count,
            'recent_violations': self.violation_history[-10:],
            'recent_warnings': self.warning_history[-10:],
            'safety_score': self._compute_safety_score()
        }

    def _compute_safety_score(self) -> float:
        """Compute overall safety score (0-1, higher is better)."""
        total_events = self.violation_count + self.warning_count
        if total_events == 0:
            return 1.0

        # Weight violations more heavily than warnings
        weighted_events = self.violation_count * 2 + self.warning_count
        return max(0.0, 1.0 - weighted_events / (total_events + 10))


class SystemHealthMonitor:
    """Monitor overall system health and performance."""

    def __init__(self, history_length: int = 1000):
        """Initialize system health monitor."""
        self.history_length = history_length
        self.state_history = []
        self.control_history = []
        self.performance_metrics = {}

    def update(self, state: np.ndarray, control: float, metrics: Dict[str, float]) -> None:
        """Update system health with new data."""
        # Store state and control history
        self.state_history.append(state.copy())
        self.control_history.append(control)

        # Maintain history length
        if len(self.state_history) > self.history_length:
            self.state_history.pop(0)
            self.control_history.pop(0)

        # Update performance metrics
        for key, value in metrics.items():
            if key not in self.performance_metrics:
                self.performance_metrics[key] = []
            self.performance_metrics[key].append(value)

            if len(self.performance_metrics[key]) > self.history_length:
                self.performance_metrics[key].pop(0)

    def get_health_status(self) -> Dict[str, Any]:
        """Get current system health status."""
        if not self.state_history:
            return {'status': 'no_data'}

        # Analyze state stability
        recent_states = np.array(self.state_history[-50:])
        state_stability = self._analyze_stability(recent_states)

        # Analyze control effort
        recent_controls = np.array(self.control_history[-50:])
        control_effort = self._analyze_control_effort(recent_controls)

        # Overall health score
        health_score = (state_stability + (1.0 - control_effort)) / 2

        return {
            'status': 'healthy' if health_score > 0.8 else 'degraded' if health_score > 0.5 else 'poor',
            'health_score': health_score,
            'state_stability': state_stability,
            'control_effort': control_effort,
            'data_points': len(self.state_history)
        }

    def _analyze_stability(self, states: np.ndarray) -> float:
        """Analyze state stability (0-1, higher is more stable)."""
        if len(states) < 2:
            return 1.0

        # Compute state variations
        variations = np.std(states, axis=0)
        max_variation = np.max(variations)

        # Normalize to 0-1 scale (assuming max variation of 10 is unstable)
        stability = max(0.0, 1.0 - max_variation / 10.0)
        return stability

    def _analyze_control_effort(self, controls: np.ndarray) -> float:
        """Analyze control effort (0-1, higher means more effort)."""
        if len(controls) < 2:
            return 0.0

        # RMS control effort
        rms_effort = np.sqrt(np.mean(controls**2))

        # Normalize to 0-1 scale (assuming effort of 100 is maximum)
        effort = min(1.0, rms_effort / 100.0)
        return effort