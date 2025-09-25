#==========================================================================================\\\
#============ src/controllers/smc/algorithms/hybrid/switching_logic.py ==============\\\
#==========================================================================================\\\

"""
Hybrid Switching Logic for Multi-Controller SMC.

Implements intelligent switching between multiple SMC controllers based on:
- System performance metrics
- Operating conditions
- Predictive analysis
- Learning algorithms

Mathematical Background:
- Switching functions prevent controller chattering
- Hysteresis bands ensure stable transitions
- Performance indices guide optimal controller selection
"""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from collections import deque
from enum import Enum

from .config import HybridSMCConfig, SwitchingCriterion


class ControllerState(Enum):
    """Current active controller state."""
    CLASSICAL = "classical"
    ADAPTIVE = "adaptive"
    SUPERTWISTING = "supertwisting"


class SwitchingDecision:
    """Represents a switching decision with reasoning."""

    def __init__(self, target_controller: ControllerState, reason: str,
                 confidence: float, metrics: Dict[str, float]):
        self.target_controller = target_controller
        self.reason = reason
        self.confidence = confidence  # 0.0 to 1.0
        self.metrics = metrics
        self.timestamp = None  # Will be set by switching logic


class HybridSwitchingLogic:
    """
    Intelligent switching logic for hybrid SMC controllers.

    Manages controller selection based on system performance,
    operating conditions, and learned preferences.
    """

    def __init__(self, config: HybridSMCConfig):
        """
        Initialize hybrid switching logic.

        Args:
            config: Hybrid SMC configuration
        """
        self.config = config
        self.active_controllers = config.get_active_controllers()

        # Initialize with first available controller
        initial_controller = self.active_controllers[0]
        self.current_controller = ControllerState(initial_controller)

        # State tracking
        self.last_switch_time = 0.0
        self.switch_history = []

        # Performance tracking
        self.performance_history = {
            controller: deque(maxlen=config.performance_window)
            for controller in self.active_controllers
        }
        self.current_performance_metrics = {}

        # Learning state (if enabled)
        if config.enable_learning:
            self.learned_thresholds = list(config.switching_thresholds)
            self.threshold_adaptation_history = []
        else:
            self.learned_thresholds = None

        # Prediction state (if enabled)
        if config.enable_predictive_switching:
            self.prediction_buffer = deque(maxlen=config.prediction_horizon)
        else:
            self.prediction_buffer = None

    def evaluate_switching(self, system_state: np.ndarray, control_results: Dict[str, Any],
                          current_time: float) -> Optional[SwitchingDecision]:
        """
        Evaluate whether to switch controllers.

        Args:
            system_state: Current system state
            control_results: Results from all controllers
            current_time: Current simulation time

        Returns:
            SwitchingDecision if switching recommended, None otherwise
        """
        # Check if switching is allowed based on timing
        if not self.config.is_switching_allowed(self.last_switch_time, current_time):
            return None

        # Update performance metrics
        self._update_performance_metrics(control_results, system_state)

        # Determine switching criterion and evaluate
        if self.config.switching_criterion == SwitchingCriterion.SURFACE_MAGNITUDE:
            decision = self._evaluate_surface_magnitude_switching(control_results)
        elif self.config.switching_criterion == SwitchingCriterion.CONTROL_EFFORT:
            decision = self._evaluate_control_effort_switching(control_results)
        elif self.config.switching_criterion == SwitchingCriterion.TRACKING_ERROR:
            decision = self._evaluate_tracking_error_switching(system_state)
        elif self.config.switching_criterion == SwitchingCriterion.ADAPTATION_RATE:
            decision = self._evaluate_adaptation_rate_switching(control_results)
        elif self.config.switching_criterion == SwitchingCriterion.PERFORMANCE_INDEX:
            decision = self._evaluate_performance_index_switching(control_results)
        elif self.config.switching_criterion == SwitchingCriterion.TIME_BASED:
            decision = self._evaluate_time_based_switching(current_time)
        else:
            raise ValueError(f"Unknown switching criterion: {self.config.switching_criterion}")

        # Apply predictive analysis if enabled
        if decision and self.config.enable_predictive_switching:
            decision = self._apply_predictive_analysis(decision, system_state)

        # Apply learning if enabled
        if decision and self.config.enable_learning:
            self._update_learned_thresholds(decision, control_results)

        return decision

    def execute_switch(self, decision: SwitchingDecision, current_time: float) -> bool:
        """
        Execute a switching decision.

        Args:
            decision: Switching decision to execute
            current_time: Current time

        Returns:
            True if switch was executed, False if prevented by hysteresis
        """
        # Apply hysteresis check
        if not self._check_hysteresis_condition(decision):
            return False

        # Record switch
        decision.timestamp = current_time
        self.switch_history.append({
            'time': current_time,
            'from': self.current_controller.value,
            'to': decision.target_controller.value,
            'reason': decision.reason,
            'confidence': decision.confidence,
            'metrics': decision.metrics.copy()
        })

        # Execute switch
        previous_controller = self.current_controller
        self.current_controller = decision.target_controller
        self.last_switch_time = current_time

        return True

    def get_current_controller(self) -> str:
        """Get name of currently active controller."""
        return self.current_controller.value

    def _update_performance_metrics(self, control_results: Dict[str, Any], system_state: np.ndarray) -> None:
        """Update performance metrics for all controllers."""
        # Extract common metrics
        metrics = {}

        # Tracking error (assuming state format [x, x_dot, theta1, theta1_dot, theta2, theta2_dot])
        if len(system_state) >= 6:
            position_error = np.sqrt(system_state[0]**2)  # Cart position error
            angle_errors = np.sqrt(system_state[2]**2 + system_state[4]**2)  # Joint angle errors
            metrics['tracking_error'] = position_error + angle_errors
        else:
            metrics['tracking_error'] = 0.0

        # Control effort
        active_controller = self.current_controller.value
        if active_controller in control_results:
            metrics['control_effort'] = abs(control_results[active_controller].get('u', 0.0))
        else:
            metrics['control_effort'] = 0.0

        # Surface magnitude
        if active_controller in control_results:
            metrics['surface_magnitude'] = abs(control_results[active_controller].get('surface_value', 0.0))
        else:
            metrics['surface_magnitude'] = 0.0

        # Store current metrics
        self.current_performance_metrics = metrics

        # Update performance history for current controller
        if active_controller in self.performance_history:
            performance_index = self.config.compute_weighted_performance(metrics)
            self.performance_history[active_controller].append(performance_index)

    def _evaluate_surface_magnitude_switching(self, control_results: Dict[str, Any]) -> Optional[SwitchingDecision]:
        """Evaluate switching based on sliding surface magnitude."""
        current_controller = self.current_controller.value

        if current_controller not in control_results:
            return None

        surface_magnitude = abs(control_results[current_controller].get('surface_value', 0.0))
        thresholds = self.learned_thresholds or self.config.switching_thresholds

        # Determine target controller based on surface magnitude
        if surface_magnitude > thresholds[-1]:  # High surface magnitude
            # Switch to most aggressive controller (usually Super-Twisting or Adaptive)
            if 'supertwisting' in self.active_controllers:
                target = ControllerState.SUPERTWISTING
                reason = f"High surface magnitude {surface_magnitude:.3f} > {thresholds[-1]:.3f}"
            elif 'adaptive' in self.active_controllers:
                target = ControllerState.ADAPTIVE
                reason = f"High surface magnitude {surface_magnitude:.3f} > {thresholds[-1]:.3f}"
            else:
                return None

        elif surface_magnitude < thresholds[0]:  # Low surface magnitude
            # Switch to classical controller for efficiency
            if 'classical' in self.active_controllers:
                target = ControllerState.CLASSICAL
                reason = f"Low surface magnitude {surface_magnitude:.3f} < {thresholds[0]:.3f}"
            else:
                return None

        else:
            # Medium range - stay with current or use adaptive
            if 'adaptive' in self.active_controllers and current_controller != 'adaptive':
                target = ControllerState.ADAPTIVE
                reason = f"Medium surface magnitude {surface_magnitude:.3f}"
            else:
                return None

        if target.value == current_controller:
            return None

        # Calculate confidence based on how far from threshold
        distance_from_threshold = min(
            abs(surface_magnitude - thresh) for thresh in thresholds
        )
        max_distance = max(thresholds) - min(thresholds)
        confidence = min(1.0, distance_from_threshold / max_distance)

        return SwitchingDecision(
            target_controller=target,
            reason=reason,
            confidence=confidence,
            metrics={'surface_magnitude': surface_magnitude}
        )

    def _evaluate_control_effort_switching(self, control_results: Dict[str, Any]) -> Optional[SwitchingDecision]:
        """Evaluate switching based on control effort."""
        current_controller = self.current_controller.value

        if current_controller not in control_results:
            return None

        control_effort = abs(control_results[current_controller].get('u', 0.0))
        effort_threshold = self.config.max_force * 0.8  # 80% of max force

        if control_effort > effort_threshold:
            # High control effort - switch to smoother controller
            if 'classical' in self.active_controllers and current_controller != 'classical':
                target = ControllerState.CLASSICAL
                reason = f"High control effort {control_effort:.3f} > {effort_threshold:.3f}"
                confidence = min(1.0, (control_effort - effort_threshold) / (self.config.max_force - effort_threshold))

                return SwitchingDecision(
                    target_controller=target,
                    reason=reason,
                    confidence=confidence,
                    metrics={'control_effort': control_effort}
                )

        return None

    def _evaluate_tracking_error_switching(self, system_state: np.ndarray) -> Optional[SwitchingDecision]:
        """Evaluate switching based on tracking error."""
        tracking_error = self.current_performance_metrics.get('tracking_error', 0.0)
        error_threshold = 0.1  # Configurable threshold

        if tracking_error > error_threshold:
            # High tracking error - switch to more aggressive controller
            current_controller = self.current_controller.value

            if 'supertwisting' in self.active_controllers and current_controller != 'supertwisting':
                target = ControllerState.SUPERTWISTING
            elif 'adaptive' in self.active_controllers and current_controller != 'adaptive':
                target = ControllerState.ADAPTIVE
            else:
                return None

            reason = f"High tracking error {tracking_error:.3f} > {error_threshold:.3f}"
            confidence = min(1.0, tracking_error / (2 * error_threshold))

            return SwitchingDecision(
                target_controller=target,
                reason=reason,
                confidence=confidence,
                metrics={'tracking_error': tracking_error}
            )

        return None

    def _evaluate_adaptation_rate_switching(self, control_results: Dict[str, Any]) -> Optional[SwitchingDecision]:
        """Evaluate switching based on adaptation rate (for adaptive controllers)."""
        current_controller = self.current_controller.value

        if current_controller == 'adaptive' and 'adaptive' in control_results:
            adaptation_rate = control_results['adaptive'].get('adaptation_rate', 0.0)
            high_adaptation_threshold = 10.0  # Configurable

            if adaptation_rate > high_adaptation_threshold:
                # High adaptation rate indicates uncertainty - might switch to Super-Twisting
                if 'supertwisting' in self.active_controllers:
                    target = ControllerState.SUPERTWISTING
                    reason = f"High adaptation rate {adaptation_rate:.3f}"
                    confidence = min(1.0, adaptation_rate / (2 * high_adaptation_threshold))

                    return SwitchingDecision(
                        target_controller=target,
                        reason=reason,
                        confidence=confidence,
                        metrics={'adaptation_rate': adaptation_rate}
                    )

        return None

    def _evaluate_performance_index_switching(self, control_results: Dict[str, Any]) -> Optional[SwitchingDecision]:
        """Evaluate switching based on comprehensive performance index."""
        current_controller = self.current_controller.value

        # Calculate performance for each available controller
        controller_performances = {}
        for controller_name in self.active_controllers:
            if controller_name in self.performance_history and len(self.performance_history[controller_name]) > 5:
                recent_performance = list(self.performance_history[controller_name])[-5:]
                controller_performances[controller_name] = np.mean(recent_performance)

        if len(controller_performances) < 2:
            return None

        # Find best performing controller
        best_controller = min(controller_performances.keys(), key=lambda k: controller_performances[k])
        current_performance = controller_performances.get(current_controller, float('inf'))
        best_performance = controller_performances[best_controller]

        # Switch if another controller is significantly better
        improvement_threshold = 0.1  # 10% improvement needed
        if (best_controller != current_controller and
            current_performance > best_performance * (1 + improvement_threshold)):

            target = ControllerState(best_controller)
            improvement = (current_performance - best_performance) / current_performance
            reason = f"Performance improvement {improvement:.2%} by switching to {best_controller}"
            confidence = min(1.0, improvement / 0.5)  # Cap at 50% improvement

            return SwitchingDecision(
                target_controller=target,
                reason=reason,
                confidence=confidence,
                metrics={'performance_improvement': improvement}
            )

        return None

    def _evaluate_time_based_switching(self, current_time: float) -> Optional[SwitchingDecision]:
        """Evaluate switching based on time (round-robin or scheduled switching)."""
        # Simple round-robin switching every 2 seconds
        switching_period = 2.0
        controller_index = int(current_time / switching_period) % len(self.active_controllers)
        target_controller_name = self.active_controllers[controller_index]

        if target_controller_name != self.current_controller.value:
            target = ControllerState(target_controller_name)
            reason = f"Time-based switching at t={current_time:.1f}s"
            confidence = 1.0

            return SwitchingDecision(
                target_controller=target,
                reason=reason,
                confidence=confidence,
                metrics={'switching_time': current_time}
            )

        return None

    def _check_hysteresis_condition(self, decision: SwitchingDecision) -> bool:
        """Check if switching decision passes hysteresis condition."""
        # Simple hysteresis: require high confidence for switching
        return decision.confidence > 0.6

    def _apply_predictive_analysis(self, decision: SwitchingDecision, system_state: np.ndarray) -> Optional[SwitchingDecision]:
        """Apply predictive analysis to switching decision."""
        # Store current state for prediction
        if self.prediction_buffer is not None:
            self.prediction_buffer.append({
                'state': system_state.copy(),
                'metrics': self.current_performance_metrics.copy(),
                'decision': decision
            })

        # Simple prediction: only switch if trend supports it
        if len(self.prediction_buffer) >= 3:
            recent_metrics = [entry['metrics'].get('surface_magnitude', 0)
                            for entry in list(self.prediction_buffer)[-3:]]

            # Check if trend supports switching decision
            if decision.target_controller == ControllerState.SUPERTWISTING:
                # Expect increasing surface magnitude trend
                trend = np.polyfit(range(len(recent_metrics)), recent_metrics, 1)[0]
                if trend <= 0:  # Decreasing trend, don't switch to aggressive controller
                    return None
            elif decision.target_controller == ControllerState.CLASSICAL:
                # Expect decreasing surface magnitude trend
                trend = np.polyfit(range(len(recent_metrics)), recent_metrics, 1)[0]
                if trend >= 0:  # Increasing trend, don't switch to gentle controller
                    return None

        return decision

    def _update_learned_thresholds(self, decision: SwitchingDecision, control_results: Dict[str, Any]) -> None:
        """Update learned switching thresholds based on decision outcomes."""
        if not self.config.enable_learning or self.learned_thresholds is None:
            return

        # Simple learning: adjust thresholds based on switching success
        # This would require feedback on switching outcome quality
        # For now, just record the decision for future analysis
        self.threshold_adaptation_history.append({
            'decision': decision,
            'thresholds': self.learned_thresholds.copy(),
            'metrics': self.current_performance_metrics.copy()
        })

    def get_switching_analysis(self) -> Dict[str, Any]:
        """Get comprehensive analysis of switching behavior."""
        return {
            'current_controller': self.current_controller.value,
            'switch_history': self.switch_history[-10:],  # Last 10 switches
            'performance_history': {
                controller: list(history)[-20:]  # Last 20 entries
                for controller, history in self.performance_history.items()
            },
            'switching_statistics': self._compute_switching_statistics(),
            'learned_thresholds': self.learned_thresholds,
            'configuration': {
                'criterion': self.config.switching_criterion.value,
                'thresholds': self.config.switching_thresholds,
                'hysteresis_margin': self.config.hysteresis_margin,
                'min_switching_time': self.config.min_switching_time
            }
        }

    def _compute_switching_statistics(self) -> Dict[str, Any]:
        """Compute statistics about switching behavior."""
        if not self.switch_history:
            return {'total_switches': 0}

        # Count switches by controller
        switch_counts = {}
        for switch in self.switch_history:
            from_controller = switch['from']
            to_controller = switch['to']

            key = f"{from_controller}_to_{to_controller}"
            switch_counts[key] = switch_counts.get(key, 0) + 1

        # Time between switches
        switch_times = [switch['time'] for switch in self.switch_history]
        if len(switch_times) > 1:
            time_intervals = [switch_times[i+1] - switch_times[i]
                            for i in range(len(switch_times)-1)]
            avg_switch_interval = np.mean(time_intervals)
            std_switch_interval = np.std(time_intervals)
        else:
            avg_switch_interval = 0.0
            std_switch_interval = 0.0

        return {
            'total_switches': len(self.switch_history),
            'switch_counts': switch_counts,
            'avg_switch_interval': avg_switch_interval,
            'std_switch_interval': std_switch_interval,
            'most_recent_switch': self.switch_history[-1] if self.switch_history else None
        }