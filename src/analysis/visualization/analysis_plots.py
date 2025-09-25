#==========================================================================================\\\
#==================== src/analysis/visualization/analysis_plots.py =====================\\\
#==========================================================================================\\\

"""Analysis visualization tools for control engineering applications.

This module provides comprehensive visualization capabilities for analysis results
including performance plots, comparison charts, and interactive visualizations.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Ellipse
# Use matplotlib directly instead of seaborn for minimal dependencies
# Set style to match common seaborn defaults
plt.style.use('default')
plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3
})
from scipy import stats
import warnings
from pathlib import Path

from ..core.interfaces import VisualizationGenerator, AnalysisResult
from ..core.data_structures import PerformanceMetrics, MetricResult


class AnalysisPlotter(VisualizationGenerator):
    """Professional analysis plotting framework."""

    def __init__(self, style: str = "scientific", figsize: Tuple[float, float] = (10, 6),
                 dpi: int = 300, color_palette: str = "viridis"):
        """Initialize analysis plotter.

        Parameters
        ----------
        style : str, optional
            Plot style ("scientific", "presentation", "publication")
        figsize : Tuple[float, float], optional
            Default figure size
        dpi : int, optional
            Figure DPI for high-quality output
        color_palette : str, optional
            Color palette name
        """
        self.style = style
        self.figsize = figsize
        self.dpi = dpi
        self.color_palette = color_palette
        self._setup_style()

    def _setup_style(self) -> None:
        """Setup matplotlib style for professional plots."""
        plt.style.use('seaborn-v0_8' if hasattr(plt.style, 'seaborn-v0_8') else 'default')

        # Professional styling
        params = {
            'figure.figsize': self.figsize,
            'figure.dpi': self.dpi,
            'font.size': 12,
            'axes.labelsize': 14,
            'axes.titlesize': 16,
            'xtick.labelsize': 12,
            'ytick.labelsize': 12,
            'legend.fontsize': 12,
            'lines.linewidth': 2,
            'axes.grid': True,
            'grid.alpha': 0.3,
            'axes.spines.top': False,
            'axes.spines.right': False
        }

        if self.style == "publication":
            params.update({
                'font.family': 'serif',
                'font.serif': ['Times New Roman'],
                'mathtext.fontset': 'stix',
                'axes.labelsize': 16,
                'axes.titlesize': 18,
                'xtick.labelsize': 14,
                'ytick.labelsize': 14,
                'legend.fontsize': 14
            })

        plt.rcParams.update(params)

    @property
    def supported_formats(self) -> List[str]:
        """List of supported output formats."""
        return ['png', 'pdf', 'svg', 'eps', 'jpg']

    def generate(self, analysis_result: AnalysisResult, **kwargs) -> str:
        """Generate visualization from analysis results.

        Parameters
        ----------
        analysis_result : AnalysisResult
            Analysis results to visualize
        **kwargs
            Additional parameters:
            - plot_type: Type of plot to generate
            - output_path: Path for saving plots
            - show_confidence_intervals: Include confidence intervals
            - compare_baselines: Baseline data for comparison

        Returns
        -------
        str
            Path to generated visualization file
        """
        plot_type = kwargs.get('plot_type', 'summary')
        output_path = kwargs.get('output_path', 'analysis_plot.png')

        if plot_type == 'summary':
            return self.create_summary_plot(analysis_result, output_path, **kwargs)
        elif plot_type == 'performance_comparison':
            return self.create_performance_comparison(analysis_result, output_path, **kwargs)
        elif plot_type == 'time_series':
            return self.create_time_series_plot(analysis_result, output_path, **kwargs)
        elif plot_type == 'distribution':
            return self.create_distribution_plot(analysis_result, output_path, **kwargs)
        elif plot_type == 'correlation_matrix':
            return self.create_correlation_matrix(analysis_result, output_path, **kwargs)
        elif plot_type == 'control_performance':
            return self.create_control_performance_plot(analysis_result, output_path, **kwargs)
        else:
            warnings.warn(f"Unknown plot type: {plot_type}")
            return self.create_summary_plot(analysis_result, output_path, **kwargs)

    def create_summary_plot(self, analysis_result: AnalysisResult, output_path: str, **kwargs) -> str:
        """Create comprehensive summary plot."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Analysis Summary Dashboard', fontsize=20, fontweight='bold')

        try:
            # Extract data from analysis result
            data = analysis_result.data

            # Plot 1: Key metrics bar chart
            self._plot_key_metrics(axes[0, 0], data, **kwargs)

            # Plot 2: Performance trends
            self._plot_performance_trends(axes[0, 1], data, **kwargs)

            # Plot 3: Distribution overview
            self._plot_distribution_overview(axes[1, 0], data, **kwargs)

            # Plot 4: Quality indicators
            self._plot_quality_indicators(axes[1, 1], data, **kwargs)

            plt.tight_layout()
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            plt.close()
            warnings.warn(f"Failed to create summary plot: {e}")
            return ""

    def create_performance_comparison(self, analysis_result: AnalysisResult, output_path: str, **kwargs) -> str:
        """Create performance comparison visualization."""
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        fig.suptitle('Performance Comparison Analysis', fontsize=18, fontweight='bold')

        try:
            data = analysis_result.data

            # Plot 1: Metric comparison
            self._plot_metric_comparison(axes[0], data, **kwargs)

            # Plot 2: Statistical significance
            self._plot_statistical_significance(axes[1], data, **kwargs)

            # Plot 3: Effect sizes
            self._plot_effect_sizes(axes[2], data, **kwargs)

            plt.tight_layout()
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            plt.close()
            warnings.warn(f"Failed to create performance comparison: {e}")
            return ""

    def create_time_series_plot(self, analysis_result: AnalysisResult, output_path: str, **kwargs) -> str:
        """Create time series analysis plot."""
        fig, axes = plt.subplots(3, 1, figsize=(14, 12))
        fig.suptitle('Time Series Analysis', fontsize=18, fontweight='bold')

        try:
            data = analysis_result.data

            # Plot 1: Original time series
            self._plot_time_series_data(axes[0], data, **kwargs)

            # Plot 2: Residuals analysis
            self._plot_residuals_analysis(axes[1], data, **kwargs)

            # Plot 3: Frequency domain analysis
            self._plot_frequency_analysis(axes[2], data, **kwargs)

            plt.tight_layout()
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            plt.close()
            warnings.warn(f"Failed to create time series plot: {e}")
            return ""

    def create_distribution_plot(self, analysis_result: AnalysisResult, output_path: str, **kwargs) -> str:
        """Create distribution analysis plot."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Distribution Analysis', fontsize=18, fontweight='bold')

        try:
            data = analysis_result.data

            # Plot 1: Histogram with fitted distribution
            self._plot_histogram_with_fit(axes[0, 0], data, **kwargs)

            # Plot 2: Q-Q plot
            self._plot_qq_plot(axes[0, 1], data, **kwargs)

            # Plot 3: Box plot with outliers
            self._plot_box_plot_analysis(axes[1, 0], data, **kwargs)

            # Plot 4: Probability density comparison
            self._plot_density_comparison(axes[1, 1], data, **kwargs)

            plt.tight_layout()
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            plt.close()
            warnings.warn(f"Failed to create distribution plot: {e}")
            return ""

    def create_correlation_matrix(self, analysis_result: AnalysisResult, output_path: str, **kwargs) -> str:
        """Create correlation matrix visualization."""
        fig, axes = plt.subplots(1, 2, figsize=(16, 7))
        fig.suptitle('Correlation Analysis', fontsize=18, fontweight='bold')

        try:
            data = analysis_result.data

            # Plot 1: Correlation heatmap
            self._plot_correlation_heatmap(axes[0], data, **kwargs)

            # Plot 2: Correlation network
            self._plot_correlation_network(axes[1], data, **kwargs)

            plt.tight_layout()
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            plt.close()
            warnings.warn(f"Failed to create correlation matrix: {e}")
            return ""

    def create_control_performance_plot(self, analysis_result: AnalysisResult, output_path: str, **kwargs) -> str:
        """Create control-specific performance visualization."""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Control Performance Analysis', fontsize=18, fontweight='bold')

        try:
            data = analysis_result.data

            # Plot 1: Step response analysis
            self._plot_step_response_analysis(axes[0, 0], data, **kwargs)

            # Plot 2: Frequency response
            self._plot_frequency_response(axes[0, 1], data, **kwargs)

            # Plot 3: Stability margins
            self._plot_stability_margins(axes[0, 2], data, **kwargs)

            # Plot 4: Control effort analysis
            self._plot_control_effort_analysis(axes[1, 0], data, **kwargs)

            # Plot 5: Robustness analysis
            self._plot_robustness_analysis(axes[1, 1], data, **kwargs)

            # Plot 6: Performance summary radar
            self._plot_performance_radar(axes[1, 2], data, **kwargs)

            plt.tight_layout()
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            plt.close()
            warnings.warn(f"Failed to create control performance plot: {e}")
            return ""

    # Helper methods for specific plot types

    def _plot_key_metrics(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot key metrics as bar chart."""
        # Extract metrics from data
        metrics = self._extract_metrics_from_data(data)

        if not metrics:
            ax.text(0.5, 0.5, 'No metrics available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Key Metrics')
            return

        metric_names = list(metrics.keys())
        metric_values = list(metrics.values())

        # Create bar plot
        bars = ax.bar(range(len(metric_names)), metric_values,
                     color=plt.cm.get_cmap(self.color_palette)(np.linspace(0, 1, len(metric_names))))

        ax.set_xlabel('Metrics')
        ax.set_ylabel('Values')
        ax.set_title('Key Performance Metrics')
        ax.set_xticks(range(len(metric_names)))
        ax.set_xticklabels(metric_names, rotation=45, ha='right')

        # Add value labels on bars
        for i, (bar, value) in enumerate(zip(bars, metric_values)):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01*max(metric_values),
                   f'{value:.3f}', ha='center', va='bottom')

    def _plot_performance_trends(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot performance trends over time or iterations."""
        # Look for time series data
        time_data = self._extract_time_series_from_data(data)

        if not time_data:
            ax.text(0.5, 0.5, 'No trend data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Performance Trends')
            return

        for series_name, (x_values, y_values) in time_data.items():
            ax.plot(x_values, y_values, label=series_name, linewidth=2)

        ax.set_xlabel('Time/Iteration')
        ax.set_ylabel('Performance')
        ax.set_title('Performance Trends')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_distribution_overview(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot distribution overview."""
        # Extract distribution data
        dist_data = self._extract_distribution_data(data)

        if not dist_data:
            ax.text(0.5, 0.5, 'No distribution data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Distribution Overview')
            return

        # Create histogram
        ax.hist(dist_data, bins=30, alpha=0.7, density=True, color='skyblue', edgecolor='black')

        # Overlay normal distribution fit
        try:
            mu, sigma = stats.norm.fit(dist_data)
            x = np.linspace(np.min(dist_data), np.max(dist_data), 100)
            y = stats.norm.pdf(x, mu, sigma)
            ax.plot(x, y, 'r-', linewidth=2, label=f'Normal fit (μ={mu:.3f}, σ={sigma:.3f})')
        except:
            pass

        ax.set_xlabel('Value')
        ax.set_ylabel('Density')
        ax.set_title('Data Distribution')
        ax.legend()

    def _plot_quality_indicators(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot quality indicators as gauge-style visualization."""
        # Extract quality metrics
        quality_metrics = self._extract_quality_metrics(data)

        if not quality_metrics:
            ax.text(0.5, 0.5, 'No quality metrics available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Quality Indicators')
            return

        # Create gauge plot
        n_metrics = len(quality_metrics)
        angles = np.linspace(0, 2*np.pi, n_metrics, endpoint=False)

        metric_names = list(quality_metrics.keys())
        metric_values = [quality_metrics[name] for name in metric_names]

        # Normalize values to 0-1 range
        max_val = max(metric_values) if metric_values else 1
        normalized_values = [v/max_val for v in metric_values]

        # Create polar plot
        ax.remove()
        ax = plt.subplot(2, 2, 4, projection='polar')

        ax.plot(angles, normalized_values, 'o-', linewidth=2, color='blue')
        ax.fill(angles, normalized_values, alpha=0.25, color='blue')

        ax.set_xticks(angles)
        ax.set_xticklabels(metric_names)
        ax.set_ylim(0, 1)
        ax.set_title('Quality Indicators', pad=20)

    def _plot_metric_comparison(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot metric comparison between methods."""
        comparison_data = self._extract_comparison_data(data)

        if not comparison_data:
            ax.text(0.5, 0.5, 'No comparison data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Metric Comparison')
            return

        methods = list(comparison_data.keys())
        metrics = list(comparison_data[methods[0]].keys()) if methods else []

        x = np.arange(len(metrics))
        width = 0.35

        for i, method in enumerate(methods):
            values = [comparison_data[method].get(metric, 0) for metric in metrics]
            ax.bar(x + i*width, values, width, label=method, alpha=0.8)

        ax.set_xlabel('Metrics')
        ax.set_ylabel('Values')
        ax.set_title('Method Comparison')
        ax.set_xticks(x + width/2)
        ax.set_xticklabels(metrics, rotation=45, ha='right')
        ax.legend()

    def _plot_statistical_significance(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot statistical significance results."""
        # Extract p-values and significance results
        significance_data = self._extract_significance_data(data)

        if not significance_data:
            ax.text(0.5, 0.5, 'No significance data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Statistical Significance')
            return

        comparisons = list(significance_data.keys())
        p_values = [significance_data[comp].get('p_value', 1.0) for comp in comparisons]

        # Create significance plot
        colors = ['red' if p < 0.05 else 'gray' for p in p_values]
        bars = ax.barh(range(len(comparisons)), [-np.log10(p) for p in p_values], color=colors, alpha=0.7)

        ax.axvline(x=-np.log10(0.05), color='red', linestyle='--', label='α = 0.05')
        ax.set_xlabel('-log₁₀(p-value)')
        ax.set_ylabel('Comparisons')
        ax.set_title('Statistical Significance')
        ax.set_yticks(range(len(comparisons)))
        ax.set_yticklabels(comparisons)
        ax.legend()

    def _plot_effect_sizes(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot effect sizes."""
        effect_size_data = self._extract_effect_size_data(data)

        if not effect_size_data:
            ax.text(0.5, 0.5, 'No effect size data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Effect Sizes')
            return

        comparisons = list(effect_size_data.keys())
        effect_sizes = [effect_size_data[comp] for comp in comparisons]

        # Create effect size plot with interpretation colors
        colors = []
        for es in effect_sizes:
            abs_es = abs(es)
            if abs_es < 0.2:
                colors.append('lightgray')  # Negligible
            elif abs_es < 0.5:
                colors.append('lightblue')  # Small
            elif abs_es < 0.8:
                colors.append('orange')     # Medium
            else:
                colors.append('red')        # Large

        bars = ax.barh(range(len(comparisons)), effect_sizes, color=colors, alpha=0.7)

        ax.axvline(x=0, color='black', linestyle='-', alpha=0.5)
        ax.axvline(x=0.2, color='blue', linestyle='--', alpha=0.5, label='Small')
        ax.axvline(x=0.5, color='orange', linestyle='--', alpha=0.5, label='Medium')
        ax.axvline(x=0.8, color='red', linestyle='--', alpha=0.5, label='Large')

        ax.set_xlabel("Cohen's d")
        ax.set_ylabel('Comparisons')
        ax.set_title('Effect Sizes')
        ax.set_yticks(range(len(comparisons)))
        ax.set_yticklabels(comparisons)
        ax.legend()

    def _plot_time_series_data(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot time series data."""
        time_series = self._extract_time_series_from_data(data)

        if not time_series:
            ax.text(0.5, 0.5, 'No time series data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Time Series Data')
            return

        for series_name, (times, values) in time_series.items():
            ax.plot(times, values, label=series_name, linewidth=1.5)

        ax.set_xlabel('Time')
        ax.set_ylabel('Value')
        ax.set_title('Time Series Data')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_residuals_analysis(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot residuals analysis."""
        residuals_data = self._extract_residuals_data(data)

        if not residuals_data:
            ax.text(0.5, 0.5, 'No residuals data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Residuals Analysis')
            return

        times, residuals = residuals_data

        ax.plot(times, residuals, 'b-', alpha=0.7, linewidth=1)
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.7)

        # Add confidence bands
        std_residuals = np.std(residuals)
        ax.fill_between(times, -2*std_residuals, 2*std_residuals, alpha=0.2, color='gray', label='±2σ')

        ax.set_xlabel('Time')
        ax.set_ylabel('Residuals')
        ax.set_title('Residuals Analysis')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_frequency_analysis(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot frequency domain analysis."""
        freq_data = self._extract_frequency_data(data)

        if not freq_data:
            ax.text(0.5, 0.5, 'No frequency data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Frequency Analysis')
            return

        frequencies, power_spectrum = freq_data

        ax.semilogy(frequencies, power_spectrum, 'b-', linewidth=2)
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Power Spectral Density')
        ax.set_title('Frequency Domain Analysis')
        ax.grid(True, alpha=0.3)

    def _plot_histogram_with_fit(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot histogram with distribution fit."""
        dist_data = self._extract_distribution_data(data)

        if not dist_data:
            ax.text(0.5, 0.5, 'No distribution data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Histogram with Fit')
            return

        # Histogram
        n, bins, patches = ax.hist(dist_data, bins=30, alpha=0.7, density=True, color='lightblue', edgecolor='black')

        # Fit multiple distributions and overlay
        distributions = [stats.norm, stats.lognorm, stats.gamma]
        colors = ['red', 'green', 'orange']

        x = np.linspace(np.min(dist_data), np.max(dist_data), 100)

        for dist, color in zip(distributions, colors):
            try:
                params = dist.fit(dist_data)
                y = dist.pdf(x, *params)
                ax.plot(x, y, color=color, linewidth=2, label=f'{dist.name} fit')
            except:
                continue

        ax.set_xlabel('Value')
        ax.set_ylabel('Density')
        ax.set_title('Distribution Fit Comparison')
        ax.legend()

    def _plot_qq_plot(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot Q-Q plot for normality assessment."""
        dist_data = self._extract_distribution_data(data)

        if not dist_data:
            ax.text(0.5, 0.5, 'No distribution data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Q-Q Plot')
            return

        stats.probplot(dist_data, dist="norm", plot=ax)
        ax.set_title('Q-Q Plot (Normal Distribution)')
        ax.grid(True, alpha=0.3)

    def _plot_box_plot_analysis(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot box plot with outlier analysis."""
        dist_data = self._extract_distribution_data(data)

        if not dist_data:
            ax.text(0.5, 0.5, 'No distribution data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Box Plot Analysis')
            return

        box_plot = ax.boxplot([dist_data], patch_artist=True, labels=['Data'])
        box_plot['boxes'][0].set_facecolor('lightblue')

        # Add mean marker
        mean_val = np.mean(dist_data)
        ax.scatter([1], [mean_val], color='red', s=50, marker='D', label=f'Mean: {mean_val:.3f}')

        ax.set_ylabel('Value')
        ax.set_title('Box Plot with Outliers')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_density_comparison(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot probability density comparison."""
        dist_data = self._extract_distribution_data(data)

        if not dist_data:
            ax.text(0.5, 0.5, 'No distribution data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Density Comparison')
            return

        # Kernel density estimation
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(dist_data)
        x = np.linspace(np.min(dist_data), np.max(dist_data), 100)
        kde_density = kde(x)

        ax.plot(x, kde_density, 'b-', linewidth=2, label='KDE')

        # Normal distribution overlay
        mu, sigma = stats.norm.fit(dist_data)
        normal_density = stats.norm.pdf(x, mu, sigma)
        ax.plot(x, normal_density, 'r--', linewidth=2, label='Normal fit')

        ax.set_xlabel('Value')
        ax.set_ylabel('Density')
        ax.set_title('Density Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_correlation_heatmap(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot correlation heatmap."""
        correlation_data = self._extract_correlation_data(data)

        if correlation_data is None:
            ax.text(0.5, 0.5, 'No correlation data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Correlation Heatmap')
            return

        im = ax.imshow(correlation_data, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

        # Add colorbar
        plt.colorbar(im, ax=ax)

        # Add correlation values as text
        n_vars = correlation_data.shape[0]
        for i in range(n_vars):
            for j in range(n_vars):
                text = ax.text(j, i, f'{correlation_data[i, j]:.2f}',
                             ha="center", va="center", color="black" if abs(correlation_data[i, j]) < 0.5 else "white")

        ax.set_title('Correlation Matrix')
        ax.set_xticks(range(n_vars))
        ax.set_yticks(range(n_vars))

    def _plot_correlation_network(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot correlation network diagram."""
        # Simplified network visualization
        ax.text(0.5, 0.5, 'Correlation Network\n(Implementation pending)', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Correlation Network')

    # Additional control-specific plotting methods

    def _plot_step_response_analysis(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot step response analysis."""
        ax.text(0.5, 0.5, 'Step Response Analysis\n(Implementation pending)', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Step Response')

    def _plot_frequency_response(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot frequency response."""
        ax.text(0.5, 0.5, 'Frequency Response\n(Implementation pending)', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Frequency Response')

    def _plot_stability_margins(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot stability margins."""
        ax.text(0.5, 0.5, 'Stability Margins\n(Implementation pending)', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Stability Margins')

    def _plot_control_effort_analysis(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot control effort analysis."""
        ax.text(0.5, 0.5, 'Control Effort Analysis\n(Implementation pending)', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Control Effort')

    def _plot_robustness_analysis(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot robustness analysis."""
        ax.text(0.5, 0.5, 'Robustness Analysis\n(Implementation pending)', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Robustness')

    def _plot_performance_radar(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Plot performance radar chart."""
        ax.text(0.5, 0.5, 'Performance Radar\n(Implementation pending)', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Performance Radar')

    # Data extraction helper methods

    def _extract_metrics_from_data(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract metrics from analysis data."""
        metrics = {}

        # Look for various metric structures
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (int, float)) and np.isfinite(value):
                    metrics[key] = value
                elif isinstance(value, dict):
                    if 'mean' in value and isinstance(value['mean'], (int, float)):
                        metrics[key] = value['mean']
                    elif 'value' in value and isinstance(value['value'], (int, float)):
                        metrics[key] = value['value']

        return metrics

    def _extract_time_series_from_data(self, data: Dict[str, Any]) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """Extract time series data."""
        time_series = {}

        # Look for time series patterns in data
        if 'time_series' in data:
            return data['time_series']

        # Look for arrays that could be time series
        for key, value in data.items():
            if isinstance(value, (list, np.ndarray)) and len(value) > 1:
                try:
                    y_values = np.array(value)
                    x_values = np.arange(len(y_values))
                    time_series[key] = (x_values, y_values)
                except:
                    continue

        return time_series

    def _extract_distribution_data(self, data: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract data for distribution analysis."""
        # Look for distribution data
        for key, value in data.items():
            if isinstance(value, (list, np.ndarray)):
                try:
                    dist_data = np.array(value).flatten()
                    if len(dist_data) > 10 and np.all(np.isfinite(dist_data)):
                        return dist_data
                except:
                    continue

        return None

    def _extract_quality_metrics(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract quality metrics."""
        quality_metrics = {}

        # Look for quality-related metrics
        quality_keywords = ['quality', 'score', 'index', 'rating', 'grade']

        for key, value in data.items():
            if any(keyword in key.lower() for keyword in quality_keywords):
                if isinstance(value, (int, float)) and np.isfinite(value):
                    quality_metrics[key] = value

        return quality_metrics

    def _extract_comparison_data(self, data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Extract comparison data between methods."""
        comparison_data = {}

        # Look for comparison structures
        if 'comparison' in data or 'methods' in data:
            comparison_section = data.get('comparison', data.get('methods', {}))
            if isinstance(comparison_section, dict):
                for method_name, method_data in comparison_section.items():
                    if isinstance(method_data, dict):
                        metrics = self._extract_metrics_from_data(method_data)
                        if metrics:
                            comparison_data[method_name] = metrics

        return comparison_data

    def _extract_significance_data(self, data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Extract statistical significance data."""
        significance_data = {}

        # Look for significance test results
        if 'statistical_tests' in data or 'significance' in data:
            test_data = data.get('statistical_tests', data.get('significance', {}))
            if isinstance(test_data, dict):
                for test_name, test_result in test_data.items():
                    if isinstance(test_result, dict) and 'p_value' in test_result:
                        significance_data[test_name] = test_result

        return significance_data

    def _extract_effect_size_data(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract effect size data."""
        effect_size_data = {}

        # Look for effect size information
        if 'effect_sizes' in data:
            effect_data = data['effect_sizes']
            if isinstance(effect_data, dict):
                for comparison, effect_info in effect_data.items():
                    if isinstance(effect_info, dict):
                        # Look for various effect size measures
                        for measure in ['cohens_d', 'effect_size', 'hedges_g']:
                            if measure in effect_info:
                                effect_size_data[comparison] = effect_info[measure]
                                break

        return effect_size_data

    def _extract_residuals_data(self, data: Dict[str, Any]) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Extract residuals data."""
        # Look for residuals in various forms
        for key in ['residuals', 'errors', 'residual_detection']:
            if key in data:
                residual_info = data[key]
                if isinstance(residual_info, dict) and 'residuals' in residual_info:
                    residuals = residual_info['residuals']
                    if isinstance(residuals, (list, np.ndarray)):
                        residuals_array = np.array(residuals)
                        times = np.arange(len(residuals_array))
                        return times, residuals_array

        return None

    def _extract_frequency_data(self, data: Dict[str, Any]) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Extract frequency domain data."""
        # Look for frequency domain analysis results
        for key in ['frequency_analysis', 'psd_analysis', 'spectral']:
            if key in data:
                freq_info = data[key]
                if isinstance(freq_info, dict):
                    if 'frequencies' in freq_info and 'power_spectral_density' in freq_info:
                        frequencies = np.array(freq_info['frequencies'])
                        psd = np.array(freq_info['power_spectral_density'])
                        return frequencies, psd

        return None

    def _extract_correlation_data(self, data: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract correlation matrix data."""
        # Look for correlation matrix
        if 'correlation_matrix' in data:
            corr_data = data['correlation_matrix']
            if isinstance(corr_data, (list, np.ndarray)):
                return np.array(corr_data)

        return None


def create_analysis_plotter(style: str = "scientific", **kwargs) -> AnalysisPlotter:
    """Factory function to create analysis plotter.

    Parameters
    ----------
    style : str, optional
        Plot style
    **kwargs
        Additional configuration parameters

    Returns
    -------
    AnalysisPlotter
        Configured analysis plotter
    """
    return AnalysisPlotter(style=style, **kwargs)