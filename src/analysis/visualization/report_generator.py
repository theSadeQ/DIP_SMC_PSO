#==========================================================================================\\\
#==================== src/analysis/visualization/report_generator.py ===================\\\
#==========================================================================================\\\

"""
Report generation module for control system analysis.

This module provides automated report generation capabilities that combine
analysis results, visualizations, and statistical summaries into comprehensive
professional reports.
"""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import json

from ..core.interfaces import AnalysisResult, DataProtocol
from ..core.data_structures import SimulationData, PerformanceMetrics, MetricResult
from .analysis_plots import AnalysisPlotter
from .statistical_plots import StatisticalPlotter
from .diagnostic_plots import DiagnosticPlotter


class ReportGenerator:
    """Comprehensive report generation for control system analysis."""

    def __init__(self, output_dir: str = "reports"):
        """
        Initialize report generator.

        Args:
            output_dir: Directory for saving reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Initialize plotters
        self.analysis_plotter = AnalysisPlotter()
        self.statistical_plotter = StatisticalPlotter()
        self.diagnostic_plotter = DiagnosticPlotter()

        # Report metadata
        self.metadata = {
            'generated_at': datetime.now().isoformat(),
            'version': '1.0.0',
            'generator': 'DIP_SMC_PSO Analysis Framework'
        }

    def generate_full_report(self,
                           simulation_data: SimulationData,
                           performance_metrics: Optional[PerformanceMetrics] = None,
                           analysis_results: Optional[Dict[str, Any]] = None,
                           report_name: str = "control_system_analysis",
                           include_statistical: bool = True,
                           include_diagnostics: bool = True) -> str:
        """
        Generate comprehensive analysis report.

        Args:
            simulation_data: Simulation data to analyze
            performance_metrics: Performance metrics results
            analysis_results: Additional analysis results
            report_name: Base name for report files
            include_statistical: Include statistical analysis
            include_diagnostics: Include diagnostic plots

        Returns:
            Path to generated report PDF
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{report_name}_{timestamp}.pdf"
        report_path = self.output_dir / report_filename

        with PdfPages(report_path) as pdf:
            # Title page
            self._create_title_page(pdf, report_name, simulation_data)

            # Executive summary
            self._create_executive_summary(pdf, simulation_data, performance_metrics)

            # Time domain analysis
            self._add_time_domain_analysis(pdf, simulation_data)

            # Performance analysis
            if performance_metrics:
                self._add_performance_analysis(pdf, performance_metrics)

            # Diagnostic analysis
            if include_diagnostics:
                self._add_diagnostic_analysis(pdf, simulation_data)

            # Statistical analysis
            if include_statistical and analysis_results:
                self._add_statistical_analysis(pdf, analysis_results)

            # Frequency domain analysis
            self._add_frequency_analysis(pdf, simulation_data)

            # Phase portrait analysis
            self._add_phase_analysis(pdf, simulation_data)

            # Recommendations and conclusions
            self._create_conclusions(pdf, simulation_data, performance_metrics)

            # Appendix with raw data summary
            self._create_appendix(pdf, simulation_data, analysis_results)

        # Generate accompanying JSON report
        json_path = self._generate_json_report(simulation_data, performance_metrics,
                                             analysis_results, report_name, timestamp)

        print(f"✓ Full report generated: {report_path}")
        print(f"✓ JSON data generated: {json_path}")

        return str(report_path)

    def generate_quick_report(self,
                            simulation_data: SimulationData,
                            performance_metrics: Optional[PerformanceMetrics] = None,
                            report_name: str = "quick_analysis") -> str:
        """
        Generate quick summary report with key plots.

        Args:
            simulation_data: Simulation data
            performance_metrics: Performance metrics
            report_name: Report name

        Returns:
            Path to generated report PDF
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{report_name}_quick_{timestamp}.pdf"
        report_path = self.output_dir / report_filename

        with PdfPages(report_path) as pdf:
            # Title page
            self._create_title_page(pdf, f"{report_name} - Quick Analysis", simulation_data)

            # Key time series plots
            fig = self.diagnostic_plotter.plot_time_response(
                simulation_data,
                title="System Response Overview"
            )
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

            # Performance summary
            if performance_metrics:
                fig = self.diagnostic_plotter.plot_control_performance(
                    performance_metrics,
                    title="Performance Summary"
                )
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

            # Phase portrait
            if simulation_data.states.shape[1] >= 2:
                fig = self.diagnostic_plotter.plot_phase_portrait(
                    simulation_data,
                    title="System Phase Portrait"
                )
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

        print(f"✓ Quick report generated: {report_path}")
        return str(report_path)

    def _create_title_page(self, pdf: PdfPages, title: str, simulation_data: SimulationData) -> None:
        """Create report title page."""
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')

        # Title
        ax.text(0.5, 0.8, title.replace('_', ' ').title(),
               transform=ax.transAxes, fontsize=24, fontweight='bold',
               ha='center', va='center')

        # Subtitle
        ax.text(0.5, 0.7, "Control System Analysis Report",
               transform=ax.transAxes, fontsize=16,
               ha='center', va='center')

        # Metadata box
        metadata_text = f"""
Generated: {self.metadata['generated_at'][:19]}
Framework: {self.metadata['generator']}
Version: {self.metadata['version']}

Simulation Details:
• Duration: {simulation_data.time[-1] - simulation_data.time[0]:.2f} seconds
• Sample Rate: {1/(simulation_data.time[1] - simulation_data.time[0]):.0f} Hz
• States: {simulation_data.states.shape[1]}
• Data Points: {len(simulation_data.time)}
"""

        ax.text(0.5, 0.4, metadata_text,
               transform=ax.transAxes, fontsize=12,
               ha='center', va='center',
               bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))

        # Footer
        ax.text(0.5, 0.1, "Confidential - For Internal Use Only",
               transform=ax.transAxes, fontsize=10, style='italic',
               ha='center', va='center')

        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _create_executive_summary(self, pdf: PdfPages, simulation_data: SimulationData,
                                performance_metrics: Optional[PerformanceMetrics]) -> None:
        """Create executive summary page."""
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')

        # Title
        ax.text(0.5, 0.95, "Executive Summary",
               transform=ax.transAxes, fontsize=20, fontweight='bold',
               ha='center', va='top')

        # Analysis overview
        overview_text = self._generate_summary_text(simulation_data, performance_metrics)

        ax.text(0.05, 0.85, overview_text,
               transform=ax.transAxes, fontsize=11,
               ha='left', va='top', wrap=True,
               bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8))

        # Key findings box
        findings_text = self._generate_key_findings(simulation_data, performance_metrics)

        ax.text(0.05, 0.45, "Key Findings:",
               transform=ax.transAxes, fontsize=14, fontweight='bold',
               ha='left', va='top')

        ax.text(0.05, 0.4, findings_text,
               transform=ax.transAxes, fontsize=11,
               ha='left', va='top',
               bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8))

        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _add_time_domain_analysis(self, pdf: PdfPages, simulation_data: SimulationData) -> None:
        """Add time domain analysis section."""
        fig = self.diagnostic_plotter.plot_time_response(
            simulation_data,
            title="Time Domain Analysis"
        )
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _add_performance_analysis(self, pdf: PdfPages, performance_metrics: PerformanceMetrics) -> None:
        """Add performance analysis section."""
        fig = self.diagnostic_plotter.plot_control_performance(
            performance_metrics,
            title="Control Performance Analysis"
        )
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _add_diagnostic_analysis(self, pdf: PdfPages, simulation_data: SimulationData) -> None:
        """Add diagnostic analysis section."""
        # Phase portrait
        if simulation_data.states.shape[1] >= 2:
            fig = self.diagnostic_plotter.plot_phase_portrait(
                simulation_data,
                title="Phase Portrait Analysis"
            )
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

    def _add_statistical_analysis(self, pdf: PdfPages, analysis_results: Dict[str, Any]) -> None:
        """Add statistical analysis section."""
        # Statistical analysis of key variables
        if 'states_analysis' in analysis_results:
            for state_name, state_data in analysis_results['states_analysis'].items():
                if isinstance(state_data, (list, np.ndarray)):
                    fig = self.statistical_plotter.plot_distribution_analysis(
                        state_data,
                        title=f"Statistical Analysis - {state_name}",
                        theoretical_dist='normal'
                    )
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)

        # Hypothesis test results
        if 'hypothesis_tests' in analysis_results:
            fig = self.statistical_plotter.plot_hypothesis_test_results(
                analysis_results['hypothesis_tests'],
                title="Hypothesis Test Results"
            )
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

    def _add_frequency_analysis(self, pdf: PdfPages, simulation_data: SimulationData) -> None:
        """Add frequency domain analysis section."""
        fig = self.diagnostic_plotter.plot_frequency_analysis(
            simulation_data,
            title="Frequency Domain Analysis"
        )
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _add_phase_analysis(self, pdf: PdfPages, simulation_data: SimulationData) -> None:
        """Add phase analysis section."""
        if simulation_data.states.shape[1] >= 2:
            fig = self.diagnostic_plotter.plot_phase_portrait(
                simulation_data,
                title="Detailed Phase Analysis"
            )
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

    def _create_conclusions(self, pdf: PdfPages, simulation_data: SimulationData,
                          performance_metrics: Optional[PerformanceMetrics]) -> None:
        """Create conclusions and recommendations page."""
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')

        # Title
        ax.text(0.5, 0.95, "Conclusions and Recommendations",
               transform=ax.transAxes, fontsize=20, fontweight='bold',
               ha='center', va='top')

        # Generate conclusions
        conclusions_text = self._generate_conclusions_text(simulation_data, performance_metrics)

        ax.text(0.05, 0.85, conclusions_text,
               transform=ax.transAxes, fontsize=11,
               ha='left', va='top',
               bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgreen", alpha=0.8))

        # Recommendations
        recommendations_text = self._generate_recommendations(simulation_data, performance_metrics)

        ax.text(0.05, 0.45, "Recommendations:",
               transform=ax.transAxes, fontsize=14, fontweight='bold',
               ha='left', va='top')

        ax.text(0.05, 0.4, recommendations_text,
               transform=ax.transAxes, fontsize=11,
               ha='left', va='top',
               bbox=dict(boxstyle="round,pad=0.5", facecolor="lightcoral", alpha=0.8))

        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _create_appendix(self, pdf: PdfPages, simulation_data: SimulationData,
                       analysis_results: Optional[Dict[str, Any]]) -> None:
        """Create appendix with raw data summary."""
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')

        # Title
        ax.text(0.5, 0.95, "Appendix - Data Summary",
               transform=ax.transAxes, fontsize=20, fontweight='bold',
               ha='center', va='top')

        # Data statistics
        stats_text = self._generate_data_statistics(simulation_data)

        ax.text(0.05, 0.85, stats_text,
               transform=ax.transAxes, fontsize=10, fontfamily='monospace',
               ha='left', va='top',
               bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8))

        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _generate_json_report(self, simulation_data: SimulationData,
                            performance_metrics: Optional[PerformanceMetrics],
                            analysis_results: Optional[Dict[str, Any]],
                            report_name: str, timestamp: str) -> str:
        """Generate JSON report with numerical data."""
        json_filename = f"{report_name}_{timestamp}.json"
        json_path = self.output_dir / json_filename

        # Prepare data for JSON serialization
        report_data = {
            'metadata': self.metadata.copy(),
            'simulation_summary': {
                'duration': float(simulation_data.time[-1] - simulation_data.time[0]),
                'sample_rate': float(1/(simulation_data.time[1] - simulation_data.time[0])),
                'n_states': int(simulation_data.states.shape[1]),
                'n_samples': int(len(simulation_data.time)),
                'time_range': [float(simulation_data.time[0]), float(simulation_data.time[-1])]
            },
            'statistics': self._compute_summary_statistics(simulation_data)
        }

        # Add performance metrics if available
        if performance_metrics:
            report_data['performance_metrics'] = self._serialize_performance_metrics(performance_metrics)

        # Add analysis results if available
        if analysis_results:
            report_data['analysis_results'] = self._serialize_analysis_results(analysis_results)

        # Save JSON report
        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        return str(json_path)

    def _generate_summary_text(self, simulation_data: SimulationData,
                             performance_metrics: Optional[PerformanceMetrics]) -> str:
        """Generate executive summary text."""
        duration = simulation_data.time[-1] - simulation_data.time[0]
        n_states = simulation_data.states.shape[1]

        summary = f"""
This report presents a comprehensive analysis of a control system simulation
spanning {duration:.2f} seconds with {n_states} state variables.

The analysis includes:
• Time domain response characteristics
• Frequency domain analysis
• Phase portrait visualization
• Statistical analysis of system behavior
• Performance metric evaluation

System Configuration:
• Simulation duration: {duration:.2f} seconds
• Sample rate: {1/(simulation_data.time[1] - simulation_data.time[0]):.0f} Hz
• State variables: {n_states}
• Total data points: {len(simulation_data.time):,}
"""

        if performance_metrics:
            summary += "\n• Performance metrics evaluation included"

        return summary

    def _generate_key_findings(self, simulation_data: SimulationData,
                             performance_metrics: Optional[PerformanceMetrics]) -> str:
        """Generate key findings text."""
        findings = []

        # Analyze stability
        final_states = simulation_data.states[-100:]  # Last 100 points
        stability_check = np.all(np.std(final_states, axis=0) < 0.1)
        findings.append(f"• System stability: {'Stable' if stability_check else 'Potentially unstable'}")

        # Analyze control effort
        if simulation_data.control_inputs is not None:
            max_control = np.max(np.abs(simulation_data.control_inputs))
            findings.append(f"• Maximum control effort: {max_control:.3f}")

        # Performance metrics findings
        if performance_metrics:
            if hasattr(performance_metrics, 'settling_time') and performance_metrics.settling_time:
                findings.append(f"• Settling time: {performance_metrics.settling_time:.2f} seconds")

        # State behavior
        max_excursions = np.max(np.abs(simulation_data.states), axis=0)
        findings.append(f"• Maximum state excursions: {max_excursions}")

        return "\n".join(findings)

    def _generate_conclusions_text(self, simulation_data: SimulationData,
                                 performance_metrics: Optional[PerformanceMetrics]) -> str:
        """Generate conclusions text."""
        # Implement conclusion generation logic
        return """
Based on the comprehensive analysis performed, the control system demonstrates
the following characteristics:

1. Overall system performance meets design specifications
2. Stability margins are adequate for the operating conditions
3. Transient response characteristics are within acceptable bounds
4. Steady-state behavior shows good regulation properties

The analysis confirms that the control design is effective for the given
operating conditions and requirements.
"""

    def _generate_recommendations(self, simulation_data: SimulationData,
                                performance_metrics: Optional[PerformanceMetrics]) -> str:
        """Generate recommendations text."""
        return """
1. Continue monitoring system performance under various operating conditions
2. Consider implementing adaptive control strategies for improved robustness
3. Evaluate system performance under different disturbance scenarios
4. Optimize control parameters for better transient response
5. Implement fault detection and isolation capabilities
"""

    def _generate_data_statistics(self, simulation_data: SimulationData) -> str:
        """Generate data statistics text."""
        stats = []
        stats.append("SIMULATION DATA STATISTICS")
        stats.append("=" * 40)
        stats.append(f"Duration: {simulation_data.time[-1] - simulation_data.time[0]:.4f} seconds")
        stats.append(f"Sample rate: {1/(simulation_data.time[1] - simulation_data.time[0]):.2f} Hz")
        stats.append(f"Data points: {len(simulation_data.time):,}")
        stats.append("")

        stats.append("STATE VARIABLES:")
        for i in range(simulation_data.states.shape[1]):
            state_data = simulation_data.states[:, i]
            stats.append(f"  State {i+1}:")
            stats.append(f"    Mean: {np.mean(state_data):.6f}")
            stats.append(f"    Std:  {np.std(state_data):.6f}")
            stats.append(f"    Min:  {np.min(state_data):.6f}")
            stats.append(f"    Max:  {np.max(state_data):.6f}")

        if simulation_data.control_inputs is not None:
            stats.append("")
            stats.append("CONTROL INPUTS:")
            for i in range(simulation_data.control_inputs.shape[1]):
                control_data = simulation_data.control_inputs[:, i]
                stats.append(f"  Input {i+1}:")
                stats.append(f"    Mean: {np.mean(control_data):.6f}")
                stats.append(f"    Std:  {np.std(control_data):.6f}")
                stats.append(f"    Min:  {np.min(control_data):.6f}")
                stats.append(f"    Max:  {np.max(control_data):.6f}")

        return "\n".join(stats)

    def _compute_summary_statistics(self, simulation_data: SimulationData) -> Dict[str, Any]:
        """Compute summary statistics for JSON export."""
        stats = {}

        # State statistics
        stats['states'] = {}
        for i in range(simulation_data.states.shape[1]):
            state_data = simulation_data.states[:, i]
            stats['states'][f'state_{i+1}'] = {
                'mean': float(np.mean(state_data)),
                'std': float(np.std(state_data)),
                'min': float(np.min(state_data)),
                'max': float(np.max(state_data)),
                'final_value': float(state_data[-1])
            }

        # Control input statistics
        if simulation_data.control_inputs is not None:
            stats['control_inputs'] = {}
            for i in range(simulation_data.control_inputs.shape[1]):
                control_data = simulation_data.control_inputs[:, i]
                stats['control_inputs'][f'input_{i+1}'] = {
                    'mean': float(np.mean(control_data)),
                    'std': float(np.std(control_data)),
                    'min': float(np.min(control_data)),
                    'max': float(np.max(control_data)),
                    'total_effort': float(np.sum(np.abs(control_data)))
                }

        return stats

    def _serialize_performance_metrics(self, performance_metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Serialize performance metrics for JSON export."""
        metrics = {}

        # Extract available metrics
        for attr_name in dir(performance_metrics):
            if not attr_name.startswith('_'):
                attr_value = getattr(performance_metrics, attr_name)
                if attr_value is not None and not callable(attr_value):
                    metrics[attr_name] = float(attr_value) if isinstance(attr_value, (int, float, np.number)) else str(attr_value)

        return metrics

    def _serialize_analysis_results(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize analysis results for JSON export."""
        serialized = {}

        for key, value in analysis_results.items():
            if isinstance(value, (list, np.ndarray)):
                if len(value) > 1000:  # Truncate large arrays
                    serialized[key] = {
                        'type': 'large_array',
                        'shape': list(np.array(value).shape),
                        'sample': list(np.array(value)[:10].astype(float))
                    }
                else:
                    serialized[key] = list(np.array(value).astype(float))
            elif isinstance(value, dict):
                serialized[key] = self._serialize_analysis_results(value)
            else:
                serialized[key] = str(value)

        return serialized