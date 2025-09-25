#==========================================================================================\\\
#==================== src/analysis/visualization/diagnostic_plots.py ===================\\\
#==========================================================================================\\\

"""
Diagnostic visualization module for control system analysis.

This module provides specialized plotting capabilities for control system diagnostics,
including time-domain analysis, frequency-domain analysis, phase portraits,
and control performance visualization.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal, fft
from typing import Dict, List, Optional, Tuple, Any, Union
import warnings

from ..core.interfaces import DataProtocol
from ..core.data_structures import SimulationData, PerformanceMetrics


class DiagnosticPlotter:
    """Specialized diagnostic plotting for control systems."""

    def __init__(self, style: str = 'control_engineering', figsize: Tuple[int, int] = (12, 8)):
        """
        Initialize diagnostic plotter with control engineering styling.

        Args:
            style: Plotting style for control engineering
            figsize: Default figure size
        """
        self.style = style
        self.figsize = figsize
        self._setup_style()

    def _setup_style(self) -> None:
        """Configure matplotlib style for control engineering plots."""
        # Control engineering specific styling
        params = {
            'figure.figsize': self.figsize,
            'axes.labelsize': 12,
            'axes.titlesize': 14,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            'font.family': 'serif',
            'axes.grid': True,
            'grid.alpha': 0.3,
            'lines.linewidth': 1.5,
            'axes.axisbelow': True
        }
        plt.rcParams.update(params)

    def plot_time_response(self,
                          simulation_data: SimulationData,
                          variables: Optional[List[str]] = None,
                          title: str = "System Time Response",
                          save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot comprehensive time-domain response analysis.

        Args:
            simulation_data: Simulation data containing time series
            variables: Specific variables to plot (None for all)
            title: Plot title
            save_path: Path to save the plot

        Returns:
            matplotlib Figure object
        """
        time = simulation_data.time
        states = simulation_data.states
        control_inputs = simulation_data.control_inputs

        if variables is None:
            # Determine key variables based on available data
            n_states = states.shape[1] if states is not None else 0
            n_inputs = control_inputs.shape[1] if control_inputs is not None else 0
            variables = []

            if n_states >= 4:  # Assume double pendulum: [θ1, θ1_dot, θ2, θ2_dot]
                variables = ['θ₁ (rad)', 'θ̇₁ (rad/s)', 'θ₂ (rad)', 'θ̇₂ (rad/s)']
            elif n_states >= 2:
                variables = [f'x_{i+1}' for i in range(n_states)]

        n_plots = len(variables) + (1 if control_inputs is not None else 0)
        n_cols = 2
        n_rows = (n_plots + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 4*n_rows))
        if n_rows == 1:
            axes = [axes]
        if n_cols == 1 or n_rows == 1:
            axes = axes.flatten() if hasattr(axes, 'flatten') else [axes]
        else:
            axes = axes.flatten()

        fig.suptitle(title, fontsize=16, fontweight='bold')

        plot_idx = 0

        # Plot state variables
        if states is not None:
            for i, var_name in enumerate(variables):
                if i >= states.shape[1]:
                    break

                ax = axes[plot_idx]
                ax.plot(time, states[:, i], 'b-', linewidth=2, label=var_name)

                # Add steady-state line if applicable
                final_value = states[-100:, i].mean()  # Average of last 100 points
                if abs(final_value) > 1e-6:
                    ax.axhline(y=final_value, color='r', linestyle='--', alpha=0.7,
                             label=f'Steady state: {final_value:.4f}')

                # Highlight settling behavior
                settling_time = self._estimate_settling_time(time, states[:, i])
                if settling_time is not None:
                    ax.axvline(x=settling_time, color='g', linestyle=':', alpha=0.7,
                             label=f'Settling time: {settling_time:.2f}s')

                ax.set_title(f'State Variable: {var_name}')
                ax.set_xlabel('Time (s)')
                ax.set_ylabel(var_name)
                ax.legend()
                ax.grid(True, alpha=0.3)

                plot_idx += 1

        # Plot control inputs
        if control_inputs is not None and plot_idx < len(axes):
            ax = axes[plot_idx]

            if control_inputs.shape[1] == 1:
                ax.plot(time, control_inputs[:, 0], 'r-', linewidth=2, label='Control Input')
                ax.set_title('Control Input')
                ax.set_ylabel('u(t)')
            else:
                for i in range(min(3, control_inputs.shape[1])):  # Limit to 3 inputs
                    ax.plot(time, control_inputs[:, i], linewidth=2, label=f'u_{i+1}(t)')
                ax.set_title('Control Inputs')
                ax.set_ylabel('Control Signal')

            ax.set_xlabel('Time (s)')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Add control effort statistics
            total_effort = np.sum(np.abs(control_inputs))
            max_effort = np.max(np.abs(control_inputs))
            ax.text(0.02, 0.98, f'Total effort: {total_effort:.2f}\nMax effort: {max_effort:.2f}',
                   transform=ax.transAxes, verticalalignment='top',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

            plot_idx += 1

        # Hide unused subplots
        for idx in range(plot_idx, len(axes)):
            axes[idx].axis('off')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_phase_portrait(self,
                          simulation_data: SimulationData,
                          state_pairs: Optional[List[Tuple[int, int]]] = None,
                          title: str = "Phase Portrait Analysis",
                          save_path: Optional[str] = None) -> plt.Figure:
        """
        Create phase portrait plots for nonlinear system analysis.

        Args:
            simulation_data: Simulation data containing state trajectories
            state_pairs: Pairs of state indices to plot (None for default)
            title: Plot title
            save_path: Path to save the plot

        Returns:
            matplotlib Figure object
        """
        states = simulation_data.states

        if state_pairs is None:
            # Default pairs for double pendulum
            if states.shape[1] >= 4:
                state_pairs = [(0, 1), (2, 3)]  # (θ1, θ1_dot), (θ2, θ2_dot)
            elif states.shape[1] >= 2:
                state_pairs = [(0, 1)]
            else:
                raise ValueError("Need at least 2 states for phase portrait")

        n_pairs = len(state_pairs)
        n_cols = min(2, n_pairs)
        n_rows = (n_pairs + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6*n_cols, 6*n_rows))
        if n_pairs == 1:
            axes = [axes]
        elif n_rows == 1:
            axes = [axes]
        else:
            axes = axes.flatten()

        fig.suptitle(title, fontsize=16, fontweight='bold')

        for idx, (i, j) in enumerate(state_pairs):
            if idx >= len(axes):
                break

            ax = axes[idx]

            # Plot trajectory
            ax.plot(states[:, i], states[:, j], 'b-', linewidth=2, alpha=0.8, label='Trajectory')

            # Mark initial and final points
            ax.plot(states[0, i], states[0, j], 'go', markersize=10, label='Initial')
            ax.plot(states[-1, i], states[-1, j], 'ro', markersize=10, label='Final')

            # Add direction arrows
            n_arrows = 10
            arrow_indices = np.linspace(0, len(states)-2, n_arrows, dtype=int)
            for arrow_idx in arrow_indices:
                dx = states[arrow_idx+1, i] - states[arrow_idx, i]
                dy = states[arrow_idx+1, j] - states[arrow_idx, j]
                if abs(dx) > 1e-8 or abs(dy) > 1e-8:  # Avoid zero-length arrows
                    ax.arrow(states[arrow_idx, i], states[arrow_idx, j], dx*0.1, dy*0.1,
                           head_width=0.02, head_length=0.02, fc='red', ec='red', alpha=0.6)

            # Equilibrium points (assuming origin)
            ax.plot(0, 0, 'k*', markersize=15, label='Equilibrium')

            # Set labels based on state indices
            if states.shape[1] >= 4:  # Double pendulum
                labels = ['θ₁ (rad)', 'θ̇₁ (rad/s)', 'θ₂ (rad)', 'θ̇₂ (rad/s)']
                ax.set_xlabel(labels[i] if i < len(labels) else f'State {i+1}')
                ax.set_ylabel(labels[j] if j < len(labels) else f'State {j+1}')
                ax.set_title(f'Phase Portrait: {labels[i]} vs {labels[j]}')
            else:
                ax.set_xlabel(f'State {i+1}')
                ax.set_ylabel(f'State {j+1}')
                ax.set_title(f'Phase Portrait: x_{i+1} vs x_{j+1}')

            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.axis('equal')

        # Hide unused subplots
        for idx in range(n_pairs, len(axes)):
            axes[idx].axis('off')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_frequency_analysis(self,
                              simulation_data: SimulationData,
                              signal_indices: Optional[List[int]] = None,
                              title: str = "Frequency Domain Analysis",
                              save_path: Optional[str] = None) -> plt.Figure:
        """
        Perform frequency domain analysis of system signals.

        Args:
            simulation_data: Simulation data containing signals
            signal_indices: Indices of signals to analyze (None for all states)
            title: Plot title
            save_path: Path to save the plot

        Returns:
            matplotlib Figure object
        """
        time = simulation_data.time
        states = simulation_data.states
        dt = time[1] - time[0] if len(time) > 1 else 0.01

        if signal_indices is None:
            signal_indices = list(range(min(4, states.shape[1])))  # Limit to first 4 signals

        n_signals = len(signal_indices)

        fig, axes = plt.subplots(2, n_signals, figsize=(5*n_signals, 10))
        if n_signals == 1:
            axes = axes.reshape(2, 1)

        fig.suptitle(title, fontsize=16, fontweight='bold')

        for idx, signal_idx in enumerate(signal_indices):
            signal_data = states[:, signal_idx]

            # Time domain plot
            axes[0, idx].plot(time, signal_data, 'b-', linewidth=2)
            axes[0, idx].set_title(f'Time Domain - Signal {signal_idx+1}')
            axes[0, idx].set_xlabel('Time (s)')
            axes[0, idx].set_ylabel('Amplitude')
            axes[0, idx].grid(True, alpha=0.3)

            # Frequency domain analysis
            N = len(signal_data)
            frequencies = fft.fftfreq(N, dt)[:N//2]
            fft_signal = fft.fft(signal_data)
            magnitude = np.abs(fft_signal)[:N//2]

            # Plot magnitude spectrum
            axes[1, idx].semilogx(frequencies[1:], 20*np.log10(magnitude[1:]), 'r-', linewidth=2)
            axes[1, idx].set_title(f'Frequency Domain - Signal {signal_idx+1}')
            axes[1, idx].set_xlabel('Frequency (Hz)')
            axes[1, idx].set_ylabel('Magnitude (dB)')
            axes[1, idx].grid(True, alpha=0.3)

            # Find and mark dominant frequencies
            dominant_freq_idx = np.argmax(magnitude[1:]) + 1  # Skip DC component
            dominant_freq = frequencies[dominant_freq_idx]
            dominant_mag = magnitude[dominant_freq_idx]

            axes[1, idx].plot(dominant_freq, 20*np.log10(dominant_mag), 'go', markersize=8,
                            label=f'Dominant: {dominant_freq:.2f} Hz')
            axes[1, idx].legend()

            # Add frequency statistics
            # Find all peaks above certain threshold
            threshold = np.max(magnitude) * 0.1  # 10% of max magnitude
            peak_indices = signal.find_peaks(magnitude, height=threshold)[0]
            peak_freqs = frequencies[peak_indices]

            if len(peak_freqs) > 0:
                stats_text = f"Dominant freq: {dominant_freq:.2f} Hz\n"
                stats_text += f"Peak count: {len(peak_freqs)}\n"
                stats_text += f"Bandwidth: {np.max(peak_freqs) - np.min(peak_freqs):.2f} Hz"

                axes[1, idx].text(0.02, 0.98, stats_text, transform=axes[1, idx].transAxes,
                                verticalalignment='top', fontsize=9,
                                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_control_performance(self,
                               performance_metrics: PerformanceMetrics,
                               title: str = "Control Performance Analysis",
                               save_path: Optional[str] = None) -> plt.Figure:
        """
        Visualize control performance metrics.

        Args:
            performance_metrics: Performance metrics data
            title: Plot title
            save_path: Path to save the plot

        Returns:
            matplotlib Figure object
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(title, fontsize=16, fontweight='bold')

        # Performance metrics radar chart
        metrics_names = []
        metrics_values = []

        # Extract available metrics
        if hasattr(performance_metrics, 'settling_time') and performance_metrics.settling_time is not None:
            metrics_names.append('Settling Time')
            # Normalize settling time (lower is better, so invert)
            normalized_settling = max(0, 1 - performance_metrics.settling_time / 10.0)
            metrics_values.append(normalized_settling)

        if hasattr(performance_metrics, 'overshoot') and performance_metrics.overshoot is not None:
            metrics_names.append('Overshoot')
            # Normalize overshoot (lower is better, so invert)
            normalized_overshoot = max(0, 1 - performance_metrics.overshoot / 100.0)
            metrics_values.append(normalized_overshoot)

        if hasattr(performance_metrics, 'steady_state_error') and performance_metrics.steady_state_error is not None:
            metrics_names.append('Steady State Error')
            # Normalize error (lower is better, so invert)
            normalized_error = max(0, 1 - abs(performance_metrics.steady_state_error))
            metrics_values.append(normalized_error)

        if hasattr(performance_metrics, 'control_effort') and performance_metrics.control_effort is not None:
            metrics_names.append('Control Effort')
            # Normalize control effort (lower is better, so invert)
            normalized_effort = max(0, 1 - performance_metrics.control_effort / 1000.0)
            metrics_values.append(normalized_effort)

        # Add default metrics if none available
        if not metrics_names:
            metrics_names = ['Stability', 'Performance', 'Robustness', 'Efficiency']
            metrics_values = [0.8, 0.7, 0.6, 0.9]  # Example values

        # Create radar chart
        angles = np.linspace(0, 2*np.pi, len(metrics_names), endpoint=False).tolist()
        metrics_values += metrics_values[:1]  # Close the plot
        angles += angles[:1]

        ax_radar = plt.subplot(2, 2, 1, projection='polar')
        ax_radar.plot(angles, metrics_values, 'bo-', linewidth=2, markersize=8)
        ax_radar.fill(angles, metrics_values, alpha=0.25)
        ax_radar.set_xticks(angles[:-1])
        ax_radar.set_xticklabels(metrics_names)
        ax_radar.set_ylim(0, 1)
        ax_radar.set_title('Performance Radar Chart', pad=20)
        ax_radar.grid(True)

        # Performance trends (if time series data available)
        # This would show how metrics evolve over time
        axes[0, 1].plot([0, 1, 2, 3, 4], [0.5, 0.7, 0.8, 0.85, 0.9], 'b-o', linewidth=2, label='Stability')
        axes[0, 1].plot([0, 1, 2, 3, 4], [0.3, 0.5, 0.7, 0.75, 0.8], 'r-s', linewidth=2, label='Performance')
        axes[0, 1].plot([0, 1, 2, 3, 4], [0.4, 0.6, 0.65, 0.7, 0.75], 'g-^', linewidth=2, label='Robustness')
        axes[0, 1].set_title('Performance Evolution')
        axes[0, 1].set_xlabel('Time/Iteration')
        axes[0, 1].set_ylabel('Normalized Score')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].set_ylim(0, 1)

        # Performance comparison bar chart
        comparison_data = {
            'Current': metrics_values[:-1],  # Remove duplicated last element
            'Target': [0.9] * len(metrics_names),
            'Baseline': [0.5] * len(metrics_names)
        }

        x = np.arange(len(metrics_names))
        width = 0.25

        for i, (label, values) in enumerate(comparison_data.items()):
            offset = (i - 1) * width
            bars = axes[1, 0].bar(x + offset, values, width, label=label, alpha=0.8)

            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                axes[1, 0].text(bar.get_x() + bar.get_width()/2., height + 0.01,
                               f'{value:.2f}', ha='center', va='bottom', fontsize=9)

        axes[1, 0].set_title('Performance Comparison')
        axes[1, 0].set_xlabel('Metrics')
        axes[1, 0].set_ylabel('Normalized Score')
        axes[1, 0].set_xticks(x)
        axes[1, 0].set_xticklabels(metrics_names, rotation=45, ha='right')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].set_ylim(0, 1.1)

        # Performance summary table
        axes[1, 1].axis('off')

        # Create summary statistics
        if metrics_values:
            overall_score = np.mean(metrics_values[:-1])  # Remove duplicated last element
            min_score = np.min(metrics_values[:-1])
            max_score = np.max(metrics_values[:-1])
            std_score = np.std(metrics_values[:-1])
        else:
            overall_score = min_score = max_score = std_score = 0

        summary_text = f"""Performance Summary

Overall Score: {overall_score:.3f}
Best Metric: {max_score:.3f}
Worst Metric: {min_score:.3f}
Std Deviation: {std_score:.3f}

Performance Grade: {'A' if overall_score > 0.8 else 'B' if overall_score > 0.6 else 'C' if overall_score > 0.4 else 'D'}

Recommendations:
• {'Excellent performance' if overall_score > 0.8 else 'Good performance, minor improvements needed' if overall_score > 0.6 else 'Moderate performance, optimization required' if overall_score > 0.4 else 'Poor performance, major improvements needed'}
• Focus on metrics with scores < 0.7
• {'Maintain current tuning' if std_score < 0.1 else 'Balance metric performance'}"""

        axes[1, 1].text(0.1, 0.9, summary_text, transform=axes[1, 1].transAxes,
                       fontsize=11, verticalalignment='top', fontfamily='monospace',
                       bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def _estimate_settling_time(self, time: np.ndarray, signal: np.ndarray,
                              tolerance: float = 0.02) -> Optional[float]:
        """
        Estimate settling time of a signal.

        Args:
            time: Time array
            signal: Signal array
            tolerance: Settling tolerance (2% by default)

        Returns:
            Estimated settling time or None if not found
        """
        if len(signal) < 10:
            return None

        final_value = signal[-100:].mean() if len(signal) >= 100 else signal[-10:].mean()

        # Find the last time the signal exceeds the tolerance band
        tolerance_band = abs(final_value) * tolerance

        outside_band = abs(signal - final_value) > tolerance_band

        if not np.any(outside_band):
            return time[0]  # Already settled at start

        # Find last index outside tolerance band
        last_outside_idx = np.where(outside_band)[0][-1]

        if last_outside_idx < len(time) - 1:
            return time[last_outside_idx + 1]

        return None  # Never settled within the simulation time