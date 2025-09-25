#==========================================================================================\\\
#============ src/controllers/smc/algorithms/classical/boundary_layer.py =============\\\
#==========================================================================================\\\

"""
Boundary Layer Implementation for Classical SMC.

Implements boundary layer method for chattering reduction in sliding mode control.
Extracted from the original monolithic controller to provide focused, reusable
boundary layer logic.

Mathematical Background:
- Boundary layer thickness ε controls trade-off between chattering and tracking error
- Adaptive boundary layer: ε_eff = ε + α|ṡ| adapts to surface motion
- Switching function approximates sign(s) with continuous function within ±ε
"""

from typing import Union, Callable
import numpy as np
from ...core.switching_functions import SwitchingFunction


class BoundaryLayer:
    """
    Boundary layer implementation for chattering reduction.

    Provides continuous approximation to discontinuous switching within
    a thin layer around the sliding surface.
    """

    def __init__(self,
                 thickness: float,
                 slope: float = 0.0,
                 switch_method: str = "tanh"):
        """
        Initialize boundary layer.

        Args:
            thickness: Base boundary layer thickness ε > 0
            slope: Adaptive slope coefficient α ≥ 0 for ε_eff = ε + α|ṡ|
            switch_method: Switching function type ("tanh", "linear", "sign")
        """
        if thickness <= 0:
            raise ValueError("Boundary layer thickness must be positive")
        if slope < 0:
            raise ValueError("Boundary layer slope must be non-negative")

        self.base_thickness = thickness
        self.slope = slope
        self.switching_func = SwitchingFunction(switch_method)

    def get_effective_thickness(self, surface_derivative: float = 0.0) -> float:
        """
        Compute effective boundary layer thickness.

        For adaptive boundary layer: ε_eff = ε_base + α|ṡ|
        Larger thickness when surface is changing rapidly (high |ṡ|).

        Args:
            surface_derivative: Surface time derivative ṡ

        Returns:
            Effective boundary layer thickness
        """
        if self.slope == 0.0:
            return self.base_thickness

        adaptive_component = self.slope * abs(surface_derivative)
        return self.base_thickness + adaptive_component

    def apply_to_surface(self, surface_value: float,
                        surface_derivative: float = 0.0) -> float:
        """
        Apply boundary layer switching to surface value.

        Args:
            surface_value: Sliding surface value s
            surface_derivative: Surface derivative ṡ (for adaptive thickness)

        Returns:
            Switching function output ∈ [-1, 1]
        """
        effective_epsilon = self.get_effective_thickness(surface_derivative)
        return self.switching_func.compute(surface_value, effective_epsilon)

    def compute_switching_control(self, surface_value: float,
                                 switching_gain: float,
                                 surface_derivative: float = 0.0) -> float:
        """
        Compute switching control component.

        Args:
            surface_value: Sliding surface value s
            switching_gain: Switching gain K > 0
            surface_derivative: Surface derivative ṡ

        Returns:
            Switching control: u_switch = -K * switch_func(s/ε_eff)
        """
        if switching_gain <= 0:
            raise ValueError("Switching gain must be positive")

        switch_output = self.apply_to_surface(surface_value, surface_derivative)
        return -switching_gain * switch_output

    def is_in_boundary_layer(self, surface_value: float,
                           surface_derivative: float = 0.0) -> bool:
        """
        Check if system is within boundary layer.

        Args:
            surface_value: Sliding surface value s
            surface_derivative: Surface derivative ṡ

        Returns:
            True if |s| ≤ ε_eff, False otherwise
        """
        effective_epsilon = self.get_effective_thickness(surface_derivative)
        return abs(surface_value) <= effective_epsilon

    def get_chattering_index(self, surface_history: Union[list, np.ndarray],
                           dt: float = 0.01) -> float:
        """
        Compute chattering index from surface history.

        Measures high-frequency oscillations in sliding surface.
        Higher values indicate more chattering.

        Args:
            surface_history: Time series of surface values
            dt: Sampling time

        Returns:
            Chattering index (high-frequency energy measure)
        """
        if len(surface_history) < 3:
            return 0.0

        surface_array = np.asarray(surface_history)

        # Compute surface derivative approximation
        surface_derivative = np.gradient(surface_array, dt)

        # High-frequency component (simple high-pass filter)
        surface_mean = np.mean(surface_array)
        high_freq_component = surface_array - surface_mean

        # Chattering index as RMS of high-frequency derivative
        chattering_index = np.sqrt(np.mean(surface_derivative**2))

        return float(chattering_index)

    def update_thickness(self, new_thickness: float) -> None:
        """
        Update base boundary layer thickness.

        Args:
            new_thickness: New thickness value ε > 0
        """
        if new_thickness <= 0:
            raise ValueError("Boundary layer thickness must be positive")
        self.base_thickness = new_thickness

    def update_slope(self, new_slope: float) -> None:
        """
        Update adaptive slope coefficient.

        Args:
            new_slope: New slope coefficient α ≥ 0
        """
        if new_slope < 0:
            raise ValueError("Boundary layer slope must be non-negative")
        self.slope = new_slope

    def get_parameters(self) -> dict:
        """
        Get boundary layer parameters.

        Returns:
            Dictionary with current parameters
        """
        return {
            'base_thickness': self.base_thickness,
            'slope': self.slope,
            'switch_method': self.switching_func.method.value,
            'adaptive': self.slope > 0
        }

    def analyze_performance(self, surface_history: Union[list, np.ndarray],
                          control_history: Union[list, np.ndarray],
                          dt: float = 0.01) -> dict:
        """
        Analyze boundary layer performance.

        Args:
            surface_history: Time series of surface values
            control_history: Time series of control values
            dt: Sampling time

        Returns:
            Performance analysis dictionary
        """
        surface_array = np.asarray(surface_history)
        control_array = np.asarray(control_history)

        if len(surface_array) < 2 or len(control_array) < 2:
            return {'error': 'Insufficient data for analysis'}

        # Compute performance metrics
        analysis = {
            # Chattering metrics
            'chattering_index': self.get_chattering_index(surface_array, dt),
            'surface_rms': float(np.sqrt(np.mean(surface_array**2))),
            'control_rms': float(np.sqrt(np.mean(control_array**2))),

            # Boundary layer metrics
            'time_in_boundary': float(np.mean([
                self.is_in_boundary_layer(s) for s in surface_array
            ])),
            'avg_effective_thickness': self.base_thickness,  # Simplified

            # Performance indicators
            'steady_state_error': float(np.mean(np.abs(surface_array[-10:]))),
            'convergence_time': self._estimate_convergence_time(surface_array, dt),
        }

        # Add adaptive thickness statistics if applicable
        if self.slope > 0:
            surface_derivatives = np.gradient(surface_array, dt)
            effective_thicknesses = [
                self.get_effective_thickness(sd) for sd in surface_derivatives
            ]
            analysis.update({
                'min_effective_thickness': float(np.min(effective_thicknesses)),
                'max_effective_thickness': float(np.max(effective_thicknesses)),
                'avg_effective_thickness': float(np.mean(effective_thicknesses))
            })

        return analysis

    def _estimate_convergence_time(self, surface_history: np.ndarray,
                                  dt: float, tolerance: float = 0.1) -> float:
        """
        Estimate time to converge to boundary layer.

        Args:
            surface_history: Surface value time series
            dt: Sampling time
            tolerance: Convergence tolerance

        Returns:
            Estimated convergence time
        """
        # Find first time when |s| < tolerance for sustained period
        abs_surface = np.abs(surface_history)
        converged_indices = np.where(abs_surface < tolerance)[0]

        if len(converged_indices) == 0:
            return float('inf')  # Never converged

        # Look for sustained convergence (at least 10 samples)
        for i in range(len(converged_indices) - 10):
            if np.all(np.diff(converged_indices[i:i+10]) == 1):
                return float(converged_indices[i] * dt)

        return float(converged_indices[0] * dt)  # First convergence point