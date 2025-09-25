#==========================================================================================\\\
#==================== src/utils/visualization/static_plots.py =========================\\\
#==========================================================================================\\\

"""
Static plotting utilities for control system analysis.

Provides comprehensive plotting functions for control system performance,
phase portraits, time series analysis, and system identification.
"""

from __future__ import annotations
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import matplotlib.patches as patches

class ControlPlotter:
    """Static plotting utilities for control system analysis."""

    def __init__(self, style: str = 'seaborn-v0_8', figsize: Tuple[float, float] = (12, 8)):
        """Initialize plotter with style settings."""
        plt.style.use(style)
        self.default_figsize = figsize

    def plot_time_series(
        self,
        time: List[float],
        data: Dict[str, List[float]],
        title: str = "Time Series",
        ylabel: str = "Value",
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """Plot multiple time series on the same axes."""
        fig, ax = plt.subplots(figsize=self.default_figsize)

        for label, values in data.items():
            ax.plot(time, values, label=label, linewidth=2)

        ax.set_xlabel("Time (s)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_state_evolution(
        self,
        time: List[float],
        state_history: List[np.ndarray],
        state_labels: List[str] = None,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """Plot evolution of all state variables."""
        state_array = np.array(state_history)
        n_states = state_array.shape[1]

        if state_labels is None:
            state_labels = [f"State {i+1}" for i in range(n_states)]

        fig, axes = plt.subplots(n_states, 1, figsize=(12, 2*n_states), sharex=True)
        if n_states == 1:
            axes = [axes]

        for i, ax in enumerate(axes):
            ax.plot(time, state_array[:, i], linewidth=2, color=f'C{i}')
            ax.set_ylabel(state_labels[i])
            ax.grid(True, alpha=0.3)

        axes[-1].set_xlabel("Time (s)")
        fig.suptitle("State Evolution", fontsize=16)

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_phase_portrait(
        self,
        state_history: List[np.ndarray],
        x_idx: int = 0,
        y_idx: int = 1,
        title: str = "Phase Portrait",
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """Plot phase portrait of two state variables."""
        state_array = np.array(state_history)

        fig, ax = plt.subplots(figsize=self.default_figsize)

        # Plot trajectory
        ax.plot(state_array[:, x_idx], state_array[:, y_idx], 'b-', linewidth=2, alpha=0.7)

        # Mark start and end points
        ax.plot(state_array[0, x_idx], state_array[0, y_idx], 'go', markersize=10, label='Start')
        ax.plot(state_array[-1, x_idx], state_array[-1, y_idx], 'ro', markersize=10, label='End')

        # Add direction arrows
        n_arrows = 10
        arrow_indices = np.linspace(0, len(state_array)-2, n_arrows, dtype=int)
        for i in arrow_indices:
            dx = state_array[i+1, x_idx] - state_array[i, x_idx]
            dy = state_array[i+1, y_idx] - state_array[i, y_idx]
            ax.arrow(state_array[i, x_idx], state_array[i, y_idx], dx, dy,
                    head_width=0.02, head_length=0.02, fc='red', ec='red', alpha=0.6)

        ax.set_xlabel(f"State {x_idx + 1}")
        ax.set_ylabel(f"State {y_idx + 1}")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_control_performance(
        self,
        time: List[float],
        control_history: List[float],
        reference: Optional[List[float]] = None,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """Plot control input and reference tracking."""
        fig, axes = plt.subplots(2, 1, figsize=self.default_figsize, sharex=True)

        # Control input
        axes[0].plot(time, control_history, 'b-', linewidth=2, label='Control Input')
        axes[0].set_ylabel("Control Force (N)")
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()

        # Reference tracking (if provided)
        if reference is not None:
            axes[1].plot(time, reference, 'r--', linewidth=2, label='Reference')
            axes[1].set_ylabel("Reference")
        else:
            # Plot control effort distribution
            axes[1].hist(control_history, bins=50, alpha=0.7, edgecolor='black')
            axes[1].set_ylabel("Frequency")
            axes[1].set_title("Control Effort Distribution")

        axes[1].grid(True, alpha=0.3)
        axes[1].legend()
        axes[1].set_xlabel("Time (s)")

        fig.suptitle("Control Performance Analysis", fontsize=16)

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_sliding_surface(
        self,
        time: List[float],
        sigma_history: List[float],
        boundary_layer: Optional[float] = None,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """Plot sliding surface evolution for SMC analysis."""
        fig, ax = plt.subplots(figsize=self.default_figsize)

        ax.plot(time, sigma_history, 'b-', linewidth=2, label='Sliding Surface σ')

        # Add boundary layer if specified
        if boundary_layer is not None:
            ax.axhline(y=boundary_layer, color='red', linestyle='--', alpha=0.7, label='Boundary Layer')
            ax.axhline(y=-boundary_layer, color='red', linestyle='--', alpha=0.7)
            ax.fill_between(time, -boundary_layer, boundary_layer, alpha=0.2, color='yellow')

        ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Sliding Surface Value")
        ax.set_title("Sliding Surface Evolution")
        ax.grid(True, alpha=0.3)
        ax.legend()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_energy_analysis(
        self,
        time: List[float],
        kinetic_energy: List[float],
        potential_energy: List[float],
        total_energy: List[float],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """Plot system energy analysis."""
        fig, axes = plt.subplots(2, 1, figsize=self.default_figsize, sharex=True)

        # Energy components
        axes[0].plot(time, kinetic_energy, 'b-', linewidth=2, label='Kinetic Energy')
        axes[0].plot(time, potential_energy, 'r-', linewidth=2, label='Potential Energy')
        axes[0].plot(time, total_energy, 'k--', linewidth=2, label='Total Energy')
        axes[0].set_ylabel("Energy (J)")
        axes[0].set_title("System Energy Components")
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()

        # Energy conservation analysis
        energy_change = np.array(total_energy) - total_energy[0]
        axes[1].plot(time, energy_change, 'g-', linewidth=2)
        axes[1].set_xlabel("Time (s)")
        axes[1].set_ylabel("Energy Change (J)")
        axes[1].set_title("Energy Conservation Analysis")
        axes[1].grid(True, alpha=0.3)

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_performance_comparison(
        self,
        data_sets: Dict[str, Dict[str, List[float]]],
        metric_names: List[str],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """Plot performance comparison between different controllers."""
        n_metrics = len(metric_names)
        fig, axes = plt.subplots(n_metrics, 1, figsize=(12, 3*n_metrics), sharex=True)

        if n_metrics == 1:
            axes = [axes]

        for i, metric in enumerate(metric_names):
            for controller_name, controller_data in data_sets.items():
                if metric in controller_data:
                    axes[i].plot(controller_data['time'], controller_data[metric],
                               linewidth=2, label=controller_name)

            axes[i].set_ylabel(metric)
            axes[i].grid(True, alpha=0.3)
            axes[i].legend()

        axes[-1].set_xlabel("Time (s)")
        fig.suptitle("Controller Performance Comparison", fontsize=16)

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

class SystemVisualization:
    """High-level visualization for complete system analysis."""

    def __init__(self):
        """Initialize system visualization."""
        self.plotter = ControlPlotter()

    def create_complete_analysis_report(
        self,
        simulation_data: Dict[str, Any],
        output_dir: str = "analysis_plots"
    ) -> Dict[str, str]:
        """Generate complete visualization report for system analysis."""
        import os
        os.makedirs(output_dir, exist_ok=True)

        saved_plots = {}

        # Extract data
        time = simulation_data['time']
        states = simulation_data['states']
        controls = simulation_data['controls']

        # 1. State evolution
        fig = self.plotter.plot_state_evolution(time, states)
        path = os.path.join(output_dir, "state_evolution.png")
        fig.savefig(path, dpi=300, bbox_inches='tight')
        saved_plots['state_evolution'] = path
        plt.close(fig)

        # 2. Phase portraits
        fig = self.plotter.plot_phase_portrait(states, 0, 3)  # Position vs velocity
        path = os.path.join(output_dir, "phase_portrait.png")
        fig.savefig(path, dpi=300, bbox_inches='tight')
        saved_plots['phase_portrait'] = path
        plt.close(fig)

        # 3. Control performance
        fig = self.plotter.plot_control_performance(time, controls)
        path = os.path.join(output_dir, "control_performance.png")
        fig.savefig(path, dpi=300, bbox_inches='tight')
        saved_plots['control_performance'] = path
        plt.close(fig)

        # 4. Additional plots based on available data
        if 'sigma' in simulation_data:
            fig = self.plotter.plot_sliding_surface(time, simulation_data['sigma'])
            path = os.path.join(output_dir, "sliding_surface.png")
            fig.savefig(path, dpi=300, bbox_inches='tight')
            saved_plots['sliding_surface'] = path
            plt.close(fig)

        return saved_plots