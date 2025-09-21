#==========================================================================================\\\
#========================== src/utils/notebook_export.py ==============================\\\
#==========================================================================================\\\

"""
Export utilities for Jupyter notebooks.

This module provides convenient functions for exporting simulation results,
plots, and data from Jupyter notebooks in various formats.
"""

import json
import pickle
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class NotebookExporter:
    """
    Utility class for exporting data and plots from Jupyter notebooks.

    Provides methods to save simulation results, plots, and metadata
    in various formats with automatic timestamping and organization.
    """

    def __init__(self, base_dir: str = "exports"):
        """
        Initialize the exporter.

        Parameters
        ----------
        base_dir : str, optional
            Base directory for exports (default: "exports")
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def export_simulation_data(self, time: np.ndarray, states: np.ndarray,
                              controls: np.ndarray, metadata: Dict[str, Any] = None,
                              prefix: str = "simulation") -> Path:
        """
        Export simulation data in multiple formats.

        Parameters
        ----------
        time : np.ndarray
            Time vector
        states : np.ndarray
            State history [x, th1, th2, xdot, th1dot, th2dot]
        controls : np.ndarray
            Control history
        metadata : dict, optional
            Additional metadata to include
        prefix : str, optional
            Filename prefix (default: "simulation")

        Returns
        -------
        Path
            Path to the created ZIP file

        Examples
        --------
        >>> exporter = NotebookExporter()
        >>> zip_path = exporter.export_simulation_data(t, x, u,
        ...     metadata={"controller": "classical_smc", "gains": [1,2,3]})
        """
        filename_base = f"{prefix}_{self.timestamp}"
        export_dir = self.base_dir / filename_base
        export_dir.mkdir(exist_ok=True)

        # Create DataFrame for easy analysis
        df = pd.DataFrame({
            'time': time,
            'x': states[:, 0],
            'theta1': states[:, 1],
            'theta2': states[:, 2],
            'x_dot': states[:, 3],
            'theta1_dot': states[:, 4],
            'theta2_dot': states[:, 5]
        })

        # Add control data (pad if necessary)
        if len(controls) == len(time) - 1:
            df_controls = pd.DataFrame({
                'time': time[:-1],
                'control': controls
            })
        else:
            df_controls = pd.DataFrame({
                'time': time[:len(controls)],
                'control': controls
            })

        # Export as CSV
        df.to_csv(export_dir / "states.csv", index=False)
        df_controls.to_csv(export_dir / "controls.csv", index=False)

        # Export as NumPy arrays
        np.savez(export_dir / "simulation_data.npz",
                time=time, states=states, controls=controls)

        # Export metadata
        if metadata is None:
            metadata = {}

        metadata.update({
            'export_timestamp': datetime.now().isoformat(),
            'data_shapes': {
                'time': time.shape,
                'states': states.shape,
                'controls': controls.shape
            }
        })

        with open(export_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        # Create ZIP file
        zip_path = self.base_dir / f"{filename_base}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in export_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(export_dir))

        print(f"✅ Simulation data exported to: {zip_path}")
        return zip_path

    def export_plots(self, figures: List[plt.Figure], names: List[str] = None,
                    prefix: str = "plots", formats: List[str] = None) -> Path:
        """
        Export matplotlib figures in multiple formats.

        Parameters
        ----------
        figures : list of matplotlib.figure.Figure
            List of figures to export
        names : list of str, optional
            Names for each figure (default: "plot_1", "plot_2", etc.)
        prefix : str, optional
            Filename prefix (default: "plots")
        formats : list of str, optional
            Output formats (default: ["png", "pdf"])

        Returns
        -------
        Path
            Path to the created directory

        Examples
        --------
        >>> fig1, ax1 = plt.subplots()
        >>> ax1.plot([1,2,3], [1,4,9])
        >>> fig2, ax2 = plt.subplots()
        >>> ax2.plot([1,2,3], [3,2,1])
        >>> exporter.export_plots([fig1, fig2], ["quadratic", "linear"])
        """
        if formats is None:
            formats = ["png", "pdf"]

        if names is None:
            names = [f"plot_{i+1}" for i in range(len(figures))]

        filename_base = f"{prefix}_{self.timestamp}"
        export_dir = self.base_dir / filename_base
        export_dir.mkdir(exist_ok=True)

        for fig, name in zip(figures, names):
            for fmt in formats:
                filename = export_dir / f"{name}.{fmt}"

                # Set DPI based on format
                dpi = 300 if fmt in ["png", "jpg", "jpeg"] else None

                fig.savefig(filename, format=fmt, dpi=dpi,
                           bbox_inches='tight', facecolor='white')

        print(f"✅ {len(figures)} plots exported in {len(formats)} formats to: {export_dir}")
        return export_dir

    def export_optimization_results(self, best_params: np.ndarray,
                                   cost_history: np.ndarray,
                                   algorithm_info: Dict[str, Any] = None,
                                   prefix: str = "optimization") -> Path:
        """
        Export PSO or other optimization results.

        Parameters
        ----------
        best_params : np.ndarray
            Best parameters found
        cost_history : np.ndarray
            Cost function history over iterations
        algorithm_info : dict, optional
            Information about the optimization algorithm
        prefix : str, optional
            Filename prefix (default: "optimization")

        Returns
        -------
        Path
            Path to the created file

        Examples
        --------
        >>> exporter.export_optimization_results(
        ...     best_params=np.array([1.2, 3.4, 5.6]),
        ...     cost_history=cost_values,
        ...     algorithm_info={"algorithm": "PSO", "particles": 30}
        ... )
        """
        filename = self.base_dir / f"{prefix}_{self.timestamp}.json"

        results = {
            'best_parameters': best_params.tolist(),
            'cost_history': cost_history.tolist(),
            'final_cost': float(cost_history[-1]) if len(cost_history) > 0 else None,
            'convergence_iteration': int(np.argmin(cost_history)) + 1,
            'export_timestamp': datetime.now().isoformat()
        }

        if algorithm_info:
            results['algorithm_info'] = algorithm_info

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"✅ Optimization results exported to: {filename}")
        return filename

    def create_analysis_report(self, time: np.ndarray, states: np.ndarray,
                              controls: np.ndarray, metadata: Dict[str, Any] = None,
                              prefix: str = "analysis") -> Path:
        """
        Create a comprehensive analysis report with statistics and plots.

        Parameters
        ----------
        time : np.ndarray
            Time vector
        states : np.ndarray
            State history
        controls : np.ndarray
            Control history
        metadata : dict, optional
            Additional metadata
        prefix : str, optional
            Filename prefix (default: "analysis")

        Returns
        -------
        Path
            Path to the created HTML report

        Examples
        --------
        >>> report_path = exporter.create_analysis_report(t, x, u,
        ...     metadata={"controller": "adaptive_smc"})
        """
        # Calculate statistics
        stats = self._calculate_statistics(time, states, controls)

        # Create plots
        fig_states = self._create_state_plot(time, states)
        fig_control = self._create_control_plot(time, controls)
        fig_phase = self._create_phase_plot(states)

        # Export plots
        plot_dir = self.export_plots([fig_states, fig_control, fig_phase],
                                   ["states", "control", "phase_space"],
                                   prefix=f"{prefix}_plots")

        # Create HTML report
        html_content = self._generate_html_report(stats, plot_dir, metadata)

        report_path = self.base_dir / f"{prefix}_report_{self.timestamp}.html"
        with open(report_path, 'w') as f:
            f.write(html_content)

        print(f"✅ Analysis report created: {report_path}")
        return report_path

    def _calculate_statistics(self, time: np.ndarray, states: np.ndarray,
                            controls: np.ndarray) -> Dict[str, float]:
        """Calculate performance statistics."""
        dt = time[1] - time[0] if len(time) > 1 else 0.01

        # Position statistics
        x = states[:, 0]
        th1 = states[:, 1]
        th2 = states[:, 2]

        # Control statistics
        u = controls[:len(time)-1] if len(controls) == len(time)-1 else controls

        stats = {
            'simulation_duration': float(time[-1] - time[0]),
            'timestep': float(dt),
            'final_position': float(x[-1]),
            'max_position_error': float(np.max(np.abs(x))),
            'final_angle1': float(np.rad2deg(th1[-1])),
            'final_angle2': float(np.rad2deg(th2[-1])),
            'max_angle1': float(np.rad2deg(np.max(np.abs(th1)))),
            'max_angle2': float(np.rad2deg(np.max(np.abs(th2)))),
            'rms_control': float(np.sqrt(np.mean(u**2))),
            'max_control': float(np.max(np.abs(u))),
            'control_effort': float(np.sum(np.abs(u)) * dt)
        }

        # Settling time (within 5% of final value)
        final_pos = x[-1]
        settling_tolerance = 0.05 * max(1.0, abs(final_pos))
        settled_indices = np.where(np.abs(x - final_pos) <= settling_tolerance)[0]
        if len(settled_indices) > 0:
            stats['settling_time'] = float(time[settled_indices[0]])
        else:
            stats['settling_time'] = float(time[-1])

        return stats

    def _create_state_plot(self, time: np.ndarray, states: np.ndarray) -> plt.Figure:
        """Create state time series plot."""
        fig, axes = plt.subplots(3, 1, figsize=(10, 8))

        axes[0].plot(time, states[:, 0])
        axes[0].set_ylabel('Position (m)')
        axes[0].grid(True, alpha=0.3)
        axes[0].set_title('System States')

        axes[1].plot(time, np.rad2deg(states[:, 1]), label='θ₁')
        axes[1].plot(time, np.rad2deg(states[:, 2]), label='θ₂')
        axes[1].set_ylabel('Angle (degrees)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        axes[2].plot(time, states[:, 3])
        axes[2].set_ylabel('Velocity (m/s)')
        axes[2].set_xlabel('Time (s)')
        axes[2].grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def _create_control_plot(self, time: np.ndarray, controls: np.ndarray) -> plt.Figure:
        """Create control signal plot."""
        fig, ax = plt.subplots(figsize=(10, 4))

        t_control = time[:-1] if len(controls) == len(time)-1 else time[:len(controls)]
        ax.plot(t_control, controls)
        ax.set_ylabel('Control Force (N)')
        ax.set_xlabel('Time (s)')
        ax.grid(True, alpha=0.3)
        ax.set_title('Control Signal')

        plt.tight_layout()
        return fig

    def _create_phase_plot(self, states: np.ndarray) -> plt.Figure:
        """Create phase space plot."""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # Link 1 phase space
        axes[0].plot(np.rad2deg(states[:, 1]), np.rad2deg(states[:, 4]))
        axes[0].set_xlabel('θ₁ (degrees)')
        axes[0].set_ylabel('θ̇₁ (degrees/s)')
        axes[0].set_title('Link 1 Phase Space')
        axes[0].grid(True, alpha=0.3)

        # Link 2 phase space
        axes[1].plot(np.rad2deg(states[:, 2]), np.rad2deg(states[:, 5]))
        axes[1].set_xlabel('θ₂ (degrees)')
        axes[1].set_ylabel('θ̇₂ (degrees/s)')
        axes[1].set_title('Link 2 Phase Space')
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def _generate_html_report(self, stats: Dict[str, float], plot_dir: Path,
                            metadata: Dict[str, Any] = None) -> str:
        """Generate HTML report content."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DIP_SMC_PSO Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }}
                .stat-box {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
                .plot {{ text-align: center; margin: 20px 0; }}
                .plot img {{ max-width: 100%; height: auto; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>DIP_SMC_PSO Analysis Report</h1>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        """

        if metadata:
            html += "<h2>Configuration</h2><ul>"
            for key, value in metadata.items():
                html += f"<li><strong>{key}:</strong> {value}</li>"
            html += "</ul>"

        html += """
            <h2>Performance Statistics</h2>
            <div class="stats">
        """

        for key, value in stats.items():
            formatted_key = key.replace('_', ' ').title()
            if 'angle' in key.lower():
                html += f'<div class="stat-box"><strong>{formatted_key}:</strong> {value:.2f}°</div>'
            elif 'time' in key.lower():
                html += f'<div class="stat-box"><strong>{formatted_key}:</strong> {value:.3f} s</div>'
            elif 'control' in key.lower() or 'force' in key.lower():
                html += f'<div class="stat-box"><strong>{formatted_key}:</strong> {value:.2f} N</div>'
            elif 'position' in key.lower():
                html += f'<div class="stat-box"><strong>{formatted_key}:</strong> {value:.4f} m</div>'
            else:
                html += f'<div class="stat-box"><strong>{formatted_key}:</strong> {value:.4f}</div>'

        html += """
            </div>
            <h2>Plots</h2>
        """

        # Add plot images
        for plot_file in plot_dir.glob("*.png"):
            plot_name = plot_file.stem.replace('_', ' ').title()
            html += f"""
            <div class="plot">
                <h3>{plot_name}</h3>
                <img src="{plot_file.name}" alt="{plot_name}">
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html


# Convenience functions for quick exports
def quick_export_simulation(time: np.ndarray, states: np.ndarray,
                           controls: np.ndarray, **kwargs) -> Path:
    """Quick simulation data export with default settings."""
    exporter = NotebookExporter()
    return exporter.export_simulation_data(time, states, controls, **kwargs)


def quick_export_plots(*figures, **kwargs) -> Path:
    """Quick plot export with default settings."""
    exporter = NotebookExporter()
    return exporter.export_plots(list(figures), **kwargs)


def quick_analysis_report(time: np.ndarray, states: np.ndarray,
                         controls: np.ndarray, **kwargs) -> Path:
    """Quick analysis report generation."""
    exporter = NotebookExporter()
    return exporter.create_analysis_report(time, states, controls, **kwargs)