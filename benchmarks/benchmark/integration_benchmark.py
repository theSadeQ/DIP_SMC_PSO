#==========================================================================================\\\
#=============== benchmarks/benchmark/integration_benchmark.py ===========================\\\
#==========================================================================================\\\
"""
Integration benchmarking orchestration class.

This module provides the main IntegrationBenchmark class that orchestrates
comprehensive testing and analysis of numerical integration methods. It
maintains backward compatibility with the original API while leveraging
the new modular architecture for enhanced functionality.

Key Features:
* **Legacy API Support**: Original method signatures preserved
* **Enhanced Analysis**: Comprehensive comparison and profiling
* **Modular Backend**: Uses specialized analysis and comparison modules
* **Conservation Validation**: Physics-based correctness verification
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Import from modular structure
from ..integration import EulerIntegrator, RK4Integrator, AdaptiveRK45Integrator
from ..analysis import EnergyAnalyzer, PerformanceProfiler
from ..comparison import IntegrationMethodComparator, ComparisonScenario

# Original imports for compatibility
sys.path.append("../..")
from src.config import load_config
from src.controllers.classic_smc import ClassicalSMC
from src.plant import SimplifiedDIPDynamics as DIPDynamics
from src.utils.config_compatibility import wrap_physics_config


class IntegrationBenchmark:
    """
    Enhanced benchmarking suite with modular architecture.

    This class maintains compatibility with the original IntegrationBenchmark
    while leveraging the new modular design for improved functionality.

    The class provides both legacy methods for backward compatibility and
    enhanced methods that utilize the full power of the modular framework.

    Attributes
    ----------
    DEFAULT_GAINS : np.ndarray
        Default controller gains for consistent testing
    physics : dict
        Physical system parameters
    dynamics : DIPDynamics
        System dynamics model
    controller : ClassicalSMC
        Default controller for testing
    x0 : np.ndarray
        Default initial conditions
    """

    # Preserve original default gains for backward compatibility
    DEFAULT_GAINS = np.array([10.0, 5.0, 3.0, 2.0, 50.0, 1.0])  # [k1, k2, lam1, lam2, K, kd]

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the benchmark with dynamics and controller from config.

        Parameters
        ----------
        config_path : str, optional
            Path to configuration file. Defaults to "config.yaml".
        """
        cfg = load_config(config_path, allow_unknown=True)
        # Normalize physics configuration for attribute access
        self.physics = wrap_physics_config(cfg.physics.model_dump())
        self.dynamics = DIPDynamics(self.physics)
        self.controller = ClassicalSMC(self.DEFAULT_GAINS, max_force=150.0, boundary_layer=0.02)
        self.x0 = np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0])

        # Initialize new modular components
        self.euler_integrator = EulerIntegrator(self.dynamics)
        self.rk4_integrator = RK4Integrator(self.dynamics)
        self.rk45_integrator = AdaptiveRK45Integrator(self.dynamics)
        self.energy_analyzer = EnergyAnalyzer(self.physics)

    # ==========================================================================
    # Legacy API Methods (Preserved for Backward Compatibility)
    # ==========================================================================

    def euler_integrate(self, sim_time: float, dt: float, use_controller: bool = True) -> Dict[str, Any]:
        """
        Run simulation using Euler method (maintains original API).

        Parameters
        ----------
        sim_time : float
            Total simulation duration in seconds
        dt : float
            Time step for fixed-step integrator
        use_controller : bool, optional
            If True, use closed-loop control; if False, open-loop

        Returns
        -------
        dict
            Dictionary containing simulation results (compatible with original format)
        """
        controller = self.controller if use_controller else None
        result = self.euler_integrator.integrate(self.x0, sim_time, dt, controller)
        return result.to_dict()

    def rk4_integrate(self, sim_time: float, dt: float, use_controller: bool = True) -> Dict[str, Any]:
        """
        Run simulation using RK4 method (maintains original API).

        Parameters
        ----------
        sim_time : float
            Total simulation duration in seconds
        dt : float
            Time step for fixed-step integrator
        use_controller : bool, optional
            If True, use closed-loop control; if False, open-loop

        Returns
        -------
        dict
            Dictionary containing simulation results (compatible with original format)
        """
        controller = self.controller if use_controller else None
        result = self.rk4_integrator.integrate(self.x0, sim_time, dt, controller)
        return result.to_dict()

    def rk45_integrate(self, sim_time: float, rtol: float = 1e-8) -> Dict[str, Any]:
        """
        Run open-loop simulation using adaptive RK45 (maintains original API).

        Parameters
        ----------
        sim_time : float
            Total simulation duration
        rtol : float, optional
            Relative tolerance for adaptive-step solver

        Returns
        -------
        dict
            Dictionary containing simulation results (compatible with original format)
        """
        result = self.rk45_integrator.integrate_open_loop(self.x0, sim_time, rtol=rtol)
        return result.to_dict()

    def calculate_energy_drift(self, result: Dict[str, Any]) -> np.ndarray:
        """
        Calculate energy drift (maintains original API).

        This method now uses the enhanced EnergyAnalyzer for more accurate
        and comprehensive energy analysis.

        Parameters
        ----------
        result : dict
            Integration result dictionary from legacy methods

        Returns
        -------
        np.ndarray
            Energy drift values throughout trajectory
        """
        return self.energy_analyzer.compute_energy_drift(result)

    # ==========================================================================
    # Enhanced Methods Using Modular Architecture
    # ==========================================================================

    def comprehensive_comparison(self, scenarios: Optional[List[ComparisonScenario]] = None) -> Dict[str, Any]:
        """
        Run comprehensive comparison across multiple scenarios.

        This extends the original functionality with systematic comparison
        across different initial conditions, time steps, and physics parameters.

        Parameters
        ----------
        scenarios : list of ComparisonScenario, optional
            List of test scenarios. If None, uses standard scenarios.

        Returns
        -------
        dict
            Comprehensive comparison results with rankings and analysis
        """
        comparator = IntegrationMethodComparator(self.physics)

        if scenarios is None:
            scenarios = comparator.create_standard_scenarios()

        results = comparator.run_comprehensive_comparison(scenarios)
        return results

    def analyze_method_accuracy(self, method_name: str, sim_time: float = 5.0,
                               dt_values: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Analyze accuracy properties of a specific integration method.

        Parameters
        ----------
        method_name : str
            Name of method ('Euler', 'RK4', or 'RK45')
        sim_time : float, optional
            Simulation duration
        dt_values : list of float, optional
            List of time steps to test

        Returns
        -------
        dict
            Comprehensive accuracy analysis results
        """
        if dt_values is None:
            dt_values = [0.1, 0.05, 0.01, 0.005, 0.001]

        method_map = {
            'Euler': self.euler_integrate,
            'RK4': self.rk4_integrate
        }

        if method_name not in method_map and method_name != 'RK45':
            raise ValueError(f"Unknown method: {method_name}")

        accuracy_results = {}

        for dt in dt_values:
            if method_name == 'RK45':
                rtol = dt * 1e-3  # Scale relative tolerance with dt
                result = self.rk45_integrate(sim_time, rtol=rtol)
            else:
                result = method_map[method_name](sim_time, dt, use_controller=False)

            # Comprehensive accuracy analysis
            analysis = self.energy_analyzer.analyze_energy_conservation(result)
            accuracy_results[dt] = {
                'energy_drift': analysis.energy_drift,
                'max_drift': analysis.max_energy_drift,
                'mean_drift': analysis.mean_energy_drift,
                'relative_error': analysis.relative_energy_error,
                'conservation_violated': analysis.conservation_violated,
                'execution_time': result.get('time', result.elapsed_time if hasattr(result, 'elapsed_time') else 1.0)
            }

        return accuracy_results

    def profile_performance(self, methods: Optional[List[str]] = None,
                          sim_time: float = 5.0, dt: float = 0.01) -> Dict[str, Dict[str, float]]:
        """
        Profile computational performance of integration methods.

        Parameters
        ----------
        methods : list of str, optional
            List of method names to test
        sim_time : float, optional
            Simulation duration
        dt : float, optional
            Time step for fixed-step methods

        Returns
        -------
        dict
            Performance profile with timing and efficiency metrics
        """
        if methods is None:
            methods = ['Euler', 'RK4', 'RK45']

        results = []

        for method_name in methods:
            if method_name == 'Euler':
                result_dict = self.euler_integrate(sim_time, dt, use_controller=False)
            elif method_name == 'RK4':
                result_dict = self.rk4_integrate(sim_time, dt, use_controller=False)
            elif method_name == 'RK45':
                rtol = dt * 1e-3
                result_dict = self.rk45_integrate(sim_time, rtol=rtol)
            else:
                continue

            results.append(result_dict)

        return PerformanceProfiler.create_performance_profile(results)

    def validate_conservation_laws(self, method_name: str = 'RK4',
                                 sim_time: float = 10.0, dt: float = 0.01) -> Dict[str, Any]:
        """
        Validate conservation laws for Hamiltonian systems.

        This method temporarily sets friction to zero and tests energy
        conservation properties of the integration scheme.

        Parameters
        ----------
        method_name : str, optional
            Integration method to test
        sim_time : float, optional
            Simulation duration
        dt : float, optional
            Time step

        Returns
        -------
        dict
            Conservation law validation results
        """
        base_physics = self.physics.to_dict() if hasattr(self.physics, 'to_dict') else dict(self.physics)
        conservative_physics = dict(base_physics)
        conservative_physics.update({
            'cart_friction': 0.0,
            'joint1_friction': 0.0,
            'joint2_friction': 0.0
        })

        analysis_time = min(sim_time, 2.0)
        analysis_dt = min(dt, 0.005)
        temp_config = wrap_physics_config(conservative_physics)
        temp_dynamics = DIPDynamics(temp_config)
        temp_energy_analyzer = EnergyAnalyzer(temp_config)

        if method_name == 'Euler':
            integrator = EulerIntegrator(temp_dynamics)
            result = integrator.integrate(self.x0, analysis_time, analysis_dt, controller=None)
        elif method_name == 'RK4':
            integrator = RK4Integrator(temp_dynamics)
            result = integrator.integrate(self.x0, analysis_time, analysis_dt, controller=None)
        elif method_name == 'RK45':
            integrator = AdaptiveRK45Integrator(temp_dynamics)
            rtol = dt * 1e-3
            result = integrator.integrate_open_loop(self.x0, analysis_time, rtol=rtol)
        else:
            raise ValueError(f"Unknown method: {method_name}")

        accuracy_analysis = temp_energy_analyzer.analyze_energy_conservation(result)
        hamiltonian_analysis = temp_energy_analyzer.check_hamiltonian_structure(result)

        return {
            'method': method_name,
            'energy_analysis': accuracy_analysis,
            'hamiltonian_analysis': hamiltonian_analysis,
            'physics_conservative': True,
            'test_duration': analysis_time,
            'time_step': analysis_dt if method_name != 'RK45' else f"adaptive(rtol={analysis_dt*1e-3})"
        }
