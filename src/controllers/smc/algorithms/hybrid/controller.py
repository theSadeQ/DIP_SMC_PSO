#==========================================================================================\\\
#============== src/controllers/smc/algorithms/hybrid/controller.py ================\\\
#==========================================================================================\\\

"""
Modular Hybrid SMC Controller.

Implements Hybrid Sliding Mode Control that intelligently switches between
multiple SMC algorithms based on system conditions and performance metrics.

Orchestrates:
- Multiple SMC controllers (Classical, Adaptive, Super-Twisting)
- Intelligent switching logic
- Smooth control transitions
- Performance monitoring and learning
"""

from typing import Dict, List, Union, Optional, Any
import numpy as np
import logging

from ..classical.controller import ModularClassicalSMC
from ..adaptive.controller import ModularAdaptiveSMC
from ..super_twisting.controller import ModularSuperTwistingSMC
from .switching_logic import HybridSwitchingLogic, ControllerState
from .config import HybridSMCConfig


class TransitionFilter:
    """Smoothing filter for control transitions between controllers."""

    def __init__(self, time_constant: float):
        """
        Initialize transition filter.

        Args:
            time_constant: Filter time constant for exponential smoothing
        """
        self.tau = time_constant
        self.previous_output = 0.0

    def filter(self, new_input: float, dt: float) -> float:
        """
        Apply exponential smoothing filter.

        Args:
            new_input: New control input
            dt: Time step

        Returns:
            Filtered output
        """
        if self.tau <= 0:
            return new_input

        alpha = dt / (self.tau + dt)
        filtered_output = alpha * new_input + (1 - alpha) * self.previous_output
        self.previous_output = filtered_output
        return filtered_output

    def reset(self, initial_value: float = 0.0) -> None:
        """Reset filter state."""
        self.previous_output = initial_value


class ModularHybridSMC:
    """
    Modular Hybrid SMC using intelligent switching between multiple controllers.

    Provides optimal performance by selecting the most appropriate SMC algorithm
    based on current system conditions and performance metrics.
    """

    # Required for PSO optimization integration
    n_gains = 4  # [c1, lambda1, c2, lambda2] - surface gains only

    def __init__(self, config: HybridSMCConfig):
        """
        Initialize modular hybrid SMC.

        Args:
            config: Type-safe hybrid configuration object
        """
        self.config = config

        # Setup logging first
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize individual controllers
        self.controllers = {}
        self._initialize_controllers()

        # Initialize switching logic
        self.switching_logic = HybridSwitchingLogic(config)

        # Initialize transition filter
        if config.transition_smoothing:
            self.transition_filter = TransitionFilter(config.smoothing_time_constant)
        else:
            self.transition_filter = None

        # Internal state
        self.simulation_time = 0.0
        self.control_history = []
        self.switching_history = []

    def _initialize_controllers(self) -> None:
        """Initialize individual SMC controllers based on hybrid mode."""
        active_controllers = self.config.get_active_controllers()

        for controller_type in active_controllers:
            controller_config = self.config.get_controller_config(controller_type)

            if controller_type == 'classical':
                self.controllers['classical'] = ModularClassicalSMC(controller_config)
            elif controller_type == 'adaptive':
                self.controllers['adaptive'] = ModularAdaptiveSMC(controller_config)
            elif controller_type == 'supertwisting':
                self.controllers['supertwisting'] = ModularSuperTwistingSMC(controller_config)
            else:
                raise ValueError(f"Unknown controller type: {controller_type}")

        self.logger.info(f"Initialized hybrid SMC with controllers: {list(self.controllers.keys())}")

    def compute_control(self, state: np.ndarray, state_vars: Any, history: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute hybrid SMC control law.

        Args:
            state: System state [x, x_dot, theta1, theta1_dot, theta2, theta2_dot]
            state_vars: Controller internal state (for interface compatibility)
            history: Controller history (for interface compatibility)

        Returns:
            Control result dictionary
        """
        try:
            # Update simulation time
            self.simulation_time += self.config.dt

            # 1. Compute control for all active controllers
            all_control_results = {}
            for controller_name, controller in self.controllers.items():
                try:
                    result = controller.compute_control(state, state_vars, history)
                    all_control_results[controller_name] = result
                except Exception as e:
                    self.logger.warning(f"Controller {controller_name} failed: {e}")
                    all_control_results[controller_name] = {'u': 0.0, 'error': str(e)}

            # 2. Evaluate switching logic
            switching_decision = self.switching_logic.evaluate_switching(
                state, all_control_results, self.simulation_time
            )

            # 3. Execute switching if recommended
            switched = False
            if switching_decision:
                switched = self.switching_logic.execute_switch(switching_decision, self.simulation_time)
                if switched:
                    self.switching_history.append(switching_decision)
                    self.logger.info(f"Switched to {switching_decision.target_controller.value}: {switching_decision.reason}")

            # 4. Get control from active controller
            active_controller_name = self.switching_logic.get_current_controller()
            if active_controller_name in all_control_results:
                active_result = all_control_results[active_controller_name]
                u_active = active_result.get('u', 0.0)
            else:
                self.logger.error(f"Active controller {active_controller_name} not available")
                u_active = 0.0
                active_result = {'u': 0.0, 'error': 'Controller not available'}

            # 5. Apply transition smoothing if enabled
            if self.transition_filter and switched:
                # Reset filter on switch to prevent large transients
                self.transition_filter.reset(u_active)
                u_final = u_active
            elif self.transition_filter:
                u_final = self.transition_filter.filter(u_active, self.config.dt)
            else:
                u_final = u_active

            # 6. Apply final saturation
            u_saturated = np.clip(u_final, -self.config.max_force, self.config.max_force)

            # 7. Store control history
            self.control_history.append({
                'time': self.simulation_time,
                'active_controller': active_controller_name,
                'u_final': u_saturated,
                'u_raw': u_active,
                'switched': switched,
                'all_results': {name: result.get('u', 0.0) for name, result in all_control_results.items()}
            })

            # Limit history size
            if len(self.control_history) > 1000:
                self.control_history = self.control_history[-500:]

            # 8. Create comprehensive result
            return self._create_hybrid_result(
                u_saturated, active_controller_name, active_result,
                all_control_results, switching_decision, switched, state
            )

        except Exception as e:
            self.logger.error(f"Hybrid control computation failed: {e}")
            return self._create_error_result(str(e))

    def _create_hybrid_result(self, u_final: float, active_controller: str,
                            active_result: Dict[str, Any], all_results: Dict[str, Any],
                            switching_decision: Optional[Any], switched: bool,
                            state: np.ndarray) -> Dict[str, Any]:
        """Create comprehensive hybrid control result."""
        return {
            # Main output
            'u': float(u_final),

            # Hybrid control information
            'active_controller': active_controller,
            'switched_this_step': switched,
            'switching_decision': {
                'target': switching_decision.target_controller.value if switching_decision else None,
                'reason': switching_decision.reason if switching_decision else None,
                'confidence': switching_decision.confidence if switching_decision else 0.0
            } if switching_decision else None,

            # Active controller details
            'active_controller_output': active_result.get('u', 0.0),
            'surface_value': active_result.get('surface_value', 0.0),
            'surface_derivative': active_result.get('surface_derivative', 0.0),

            # All controller outputs (for comparison)
            'all_controller_outputs': {name: result.get('u', 0.0) for name, result in all_results.items()},
            'all_surface_values': {name: result.get('surface_value', 0.0) for name, result in all_results.items()},

            # Performance metrics
            'control_effort': abs(u_final),
            'surface_magnitude': abs(active_result.get('surface_value', 0.0)),
            'tracking_error': self._compute_tracking_error(state),

            # Transition smoothing
            'transition_filtering_active': self.transition_filter is not None,
            'control_before_filtering': active_result.get('u', 0.0),

            # Hybrid system status
            'controller_type': 'hybrid_smc',
            'hybrid_mode': self.config.hybrid_mode.value,
            'switching_criterion': self.config.switching_criterion.value,
            'simulation_time': self.simulation_time,

            # Individual controller specific info
            **self._extract_controller_specific_info(active_controller, active_result),

            # Switching analysis
            'switching_stats': {
                'total_switches': len(self.switching_history),
                'last_switch_time': self.switching_logic.last_switch_time,
                'time_since_last_switch': self.simulation_time - self.switching_logic.last_switch_time
            }
        }

    def _extract_controller_specific_info(self, controller_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract controller-specific information for logging."""
        controller_info = {}

        if controller_name == 'adaptive':
            controller_info.update({
                'adaptive_gain': result.get('adaptive_gain', 0.0),
                'adaptation_active': result.get('adaptation_active', False),
                'uncertainty_bound': result.get('uncertainty_bound', 0.0)
            })
        elif controller_name == 'supertwisting':
            controller_info.update({
                'K1': result.get('K1', 0.0),
                'K2': result.get('K2', 0.0),
                'u1_continuous': result.get('u1_continuous', 0.0),
                'u2_integral': result.get('u2_integral', 0.0),
                'finite_time_convergence': result.get('finite_time_convergence', False)
            })
        elif controller_name == 'classical':
            controller_info.update({
                'equivalent_control': result.get('equivalent_control', 0.0),
                'switching_control': result.get('switching_control', 0.0),
                'boundary_layer_active': result.get('boundary_layer_active', False)
            })

        return controller_info

    def _compute_tracking_error(self, state: np.ndarray) -> float:
        """Compute tracking error from system state."""
        if len(state) >= 6:
            # Assume desired position is 0 for all variables
            position_error = abs(state[0])  # Cart position
            angle_errors = abs(state[2]) + abs(state[4])  # Joint angles
            return position_error + angle_errors
        return 0.0

    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """Create error result with safe defaults."""
        return {
            'u': 0.0,
            'error': error_msg,
            'controller_type': 'hybrid_smc',
            'safe_mode': True,
            'active_controller': self.switching_logic.get_current_controller(),
            'simulation_time': self.simulation_time
        }

    @property
    def gains(self) -> List[float]:
        """Return gains from currently active controller."""
        active_controller_name = self.switching_logic.get_current_controller()
        if active_controller_name in self.controllers:
            return list(self.controllers[active_controller_name].gains)
        return []

    def get_active_controller_name(self) -> str:
        """Get name of currently active controller."""
        return self.switching_logic.get_current_controller()

    def get_active_controller(self) -> Union[ModularClassicalSMC, ModularAdaptiveSMC, ModularSuperTwistingSMC]:
        """Get currently active controller object."""
        active_name = self.get_active_controller_name()
        return self.controllers[active_name]

    def reset(self) -> None:
        """Reset controller to initial state (standard interface)."""
        self.reset_all_controllers()

    def reset_all_controllers(self) -> None:
        """Reset all individual controllers to initial state."""
        for controller in self.controllers.values():
            # Try different reset method names
            if hasattr(controller, 'reset'):
                controller.reset()
            elif hasattr(controller, 'reset_controller'):
                controller.reset_controller()
            elif hasattr(controller, 'reset_adaptation'):
                controller.reset_adaptation()

        # Reset hybrid-specific state
        self.simulation_time = 0.0
        self.control_history.clear()
        self.switching_history.clear()

        # Reset switching logic
        if hasattr(self.switching_logic, 'reset'):
            self.switching_logic.reset()

        # Reset transition filter
        if self.transition_filter:
            self.transition_filter.reset()

        self.logger.info("Reset all controllers and hybrid state")

    def force_switch_to_controller(self, controller_name: str) -> bool:
        """
        Force switch to specific controller.

        Args:
            controller_name: Name of controller to switch to

        Returns:
            True if switch successful, False if controller not available
        """
        if controller_name not in self.controllers:
            self.logger.error(f"Controller {controller_name} not available")
            return False

        # Create forced switching decision
        target_state = ControllerState(controller_name)
        self.switching_logic.current_controller = target_state
        self.switching_logic.last_switch_time = self.simulation_time

        # Reset transition filter on forced switch
        if self.transition_filter:
            self.transition_filter.reset()

        self.logger.info(f"Forced switch to {controller_name}")
        return True

    def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """Get comprehensive analysis of hybrid system performance."""
        switching_analysis = self.switching_logic.get_switching_analysis()

        # Individual controller analysis
        controller_analyses = {}
        for name, controller in self.controllers.items():
            if hasattr(controller, 'get_stability_analysis'):
                controller_analyses[name] = controller.get_stability_analysis()
            elif hasattr(controller, 'get_adaptation_analysis'):
                controller_analyses[name] = controller.get_adaptation_analysis()
            elif hasattr(controller, 'get_parameters'):
                controller_analyses[name] = controller.get_parameters()

        # Performance comparison
        if len(self.control_history) > 10:
            performance_comparison = self._analyze_controller_performance()
        else:
            performance_comparison = {'insufficient_data': True}

        return {
            'switching_analysis': switching_analysis,
            'controller_analyses': controller_analyses,
            'performance_comparison': performance_comparison,
            'configuration': self.config.to_dict(),
            'system_status': {
                'simulation_time': self.simulation_time,
                'active_controller': self.get_active_controller_name(),
                'total_control_steps': len(self.control_history),
                'total_switches': len(self.switching_history)
            }
        }

    def _analyze_controller_performance(self) -> Dict[str, Any]:
        """Analyze relative performance of different controllers."""
        # Group control history by controller
        controller_performance = {}

        for entry in self.control_history[-200:]:  # Last 200 steps
            controller = entry['active_controller']
            if controller not in controller_performance:
                controller_performance[controller] = {
                    'control_efforts': [],
                    'steps': 0,
                    'total_time': 0.0
                }

            controller_performance[controller]['control_efforts'].append(abs(entry['u_final']))
            controller_performance[controller]['steps'] += 1

        # Compute statistics
        performance_stats = {}
        for controller, data in controller_performance.items():
            if data['steps'] > 0:
                performance_stats[controller] = {
                    'avg_control_effort': np.mean(data['control_efforts']),
                    'std_control_effort': np.std(data['control_efforts']),
                    'max_control_effort': np.max(data['control_efforts']),
                    'usage_percentage': (data['steps'] / len(self.control_history[-200:])) * 100,
                    'total_steps': data['steps']
                }

        return performance_stats

    def tune_switching_parameters(self, **kwargs) -> None:
        """
        Tune switching parameters during runtime.

        Args:
            **kwargs: Parameters to update (switching_thresholds, hysteresis_margin, etc.)
        """
        # Note: Since config is frozen, this would require careful updating
        # For now, log the tuning request
        self.logger.info(f"Switching parameter tuning requested: {kwargs}")
        # Implementation would need to update switching logic parameters

    def get_parameters(self) -> Dict[str, Any]:
        """Get all hybrid system parameters."""
        return {
            'hybrid_config': self.config.to_dict(),
            'active_controller': self.get_active_controller_name(),
            'individual_controllers': {
                name: controller.get_parameters() if hasattr(controller, 'get_parameters') else {}
                for name, controller in self.controllers.items()
            },
            'switching_parameters': {
                'criterion': self.config.switching_criterion.value,
                'thresholds': self.config.switching_thresholds,
                'hysteresis_margin': self.config.hysteresis_margin,
                'min_switching_time': self.config.min_switching_time
            }
        }


# Backward compatibility facade
class HybridSMC:
    """Backward-compatible facade for the modular Hybrid SMC."""

    def __init__(self, hybrid_mode: str, controller_configs: Dict[str, Any],
                 dt: float, max_force: float, **kwargs):
        """
        Initialize Hybrid SMC with legacy interface.

        Args:
            hybrid_mode: Hybrid mode string
            controller_configs: Dictionary of controller configurations
            dt: Control timestep
            max_force: Maximum control force
            **kwargs: Additional parameters
        """
        # Convert to modular configuration (simplified)
        from .config import HybridMode

        hybrid_mode_enum = HybridMode(hybrid_mode)

        # This would need more sophisticated conversion logic
        config = HybridSMCConfig(
            hybrid_mode=hybrid_mode_enum,
            dt=dt,
            max_force=max_force,
            **kwargs
        )

        # Initialize modular controller
        self._controller = ModularHybridSMC(config)

    def compute_control(self, state: np.ndarray, state_vars: Any, history: Dict[str, Any]) -> Dict[str, Any]:
        """Compute control (delegates to modular controller)."""
        return self._controller.compute_control(state, state_vars, history)

    @property
    def gains(self) -> List[float]:
        """Return controller gains."""
        return self._controller.gains

    def get_active_controller_name(self) -> str:
        """Get active controller name."""
        return self._controller.get_active_controller_name()

    def reset_all_controllers(self) -> None:
        """Reset all controllers."""
        self._controller.reset_all_controllers()

    def get_parameters(self) -> Dict[str, Any]:
        """Get controller parameters."""
        return self._controller.get_parameters()