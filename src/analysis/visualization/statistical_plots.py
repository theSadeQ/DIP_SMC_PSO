#==========================================================================================\\\
#==================== src/analysis/visualization/statistical_plots.py ==================\\\
#==========================================================================================\\\

"""
Statistical visualization module for control system analysis.

This module provides specialized plotting capabilities for statistical analysis
of control system data, including distribution analysis, hypothesis test results,
and Monte Carlo simulation visualizations.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd
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
from typing import Dict, List, Optional, Tuple, Any, Union
import warnings

from ..core.interfaces import DataProtocol
from ..core.data_structures import MetricResult


class StatisticalPlotter:
    """Advanced statistical plotting for control system analysis."""

    def __init__(self, style: str = 'scientific', figsize: Tuple[int, int] = (12, 8)):
        """
        Initialize statistical plotter with scientific styling.

        Args:
            style: Plotting style ('scientific', 'minimal', 'publication')
            figsize: Default figure size
        """
        self.style = style
        self.figsize = figsize
        self._setup_style()

    def _setup_style(self) -> None:
        """Configure matplotlib style for scientific plots."""
        plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn' in plt.style.available else 'default')

        # Scientific plot parameters
        params = {
            'figure.figsize': self.figsize,
            'axes.labelsize': 12,
            'axes.titlesize': 14,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            'font.family': 'serif',
            'font.serif': ['Computer Modern Roman'],
            'text.usetex': False,  # Disable LaTeX for compatibility
            'axes.grid': True,
            'grid.alpha': 0.3
        }
        plt.rcParams.update(params)

    def plot_distribution_analysis(self,
                                 data: Union[np.ndarray, List[float]],
                                 title: str = "Distribution Analysis",
                                 theoretical_dist: Optional[str] = None,
                                 save_path: Optional[str] = None) -> plt.Figure:
        """
        Create comprehensive distribution analysis plot.

        Args:
            data: Data array to analyze
            title: Plot title
            theoretical_dist: Theoretical distribution to compare ('normal', 'uniform', etc.)
            save_path: Path to save the plot

        Returns:
            matplotlib Figure object
        """
        data = np.asarray(data)

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(title, fontsize=16, fontweight='bold')

        # Histogram with density estimation
        axes[0, 0].hist(data, bins=50, density=True, alpha=0.7, color='steelblue', edgecolor='black')

        # Kernel density estimation
        try:
            kde_x = np.linspace(data.min(), data.max(), 1000)
            kde = stats.gaussian_kde(data)
            axes[0, 0].plot(kde_x, kde(kde_x), 'r-', linewidth=2, label='KDE')
        except Exception:
            pass

        # Theoretical distribution overlay
        if theoretical_dist == 'normal':
            mu, sigma = stats.norm.fit(data)
            x_norm = np.linspace(data.min(), data.max(), 1000)
            axes[0, 0].plot(x_norm, stats.norm.pdf(x_norm, mu, sigma),
                          'g--', linewidth=2, label=f'Normal(μ={mu:.3f}, σ={sigma:.3f})')

        axes[0, 0].set_title('Distribution with Density Estimation')
        axes[0, 0].set_xlabel('Value')
        axes[0, 0].set_ylabel('Density')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # Q-Q plot
        if theoretical_dist == 'normal':
            stats.probplot(data, dist="norm", plot=axes[0, 1])
            axes[0, 1].set_title('Q-Q Plot (Normal)')
        else:
            # Generic Q-Q plot
            sorted_data = np.sort(data)
            n = len(data)
            theoretical_quantiles = np.linspace(0, 1, n)
            axes[0, 1].scatter(theoretical_quantiles, sorted_data, alpha=0.6)
            axes[0, 1].set_title('Q-Q Plot')
            axes[0, 1].set_xlabel('Theoretical Quantiles')
            axes[0, 1].set_ylabel('Sample Quantiles')
        axes[0, 1].grid(True, alpha=0.3)

        # Box plot with statistics
        box_plot = axes[1, 0].boxplot(data, patch_artist=True, notch=True)
        box_plot['boxes'][0].set_facecolor('lightblue')
        axes[1, 0].set_title('Box Plot with Statistics')
        axes[1, 0].set_ylabel('Value')

        # Add statistical annotations
        q1, median, q3 = np.percentile(data, [25, 50, 75])
        mean_val = np.mean(data)
        std_val = np.std(data)

        stats_text = f"""Statistics:
Mean: {mean_val:.4f}
Median: {median:.4f}
Std: {std_val:.4f}
Q1: {q1:.4f}
Q3: {q3:.4f}
IQR: {q3-q1:.4f}"""

        axes[1, 0].text(1.1, median, stats_text, transform=axes[1, 0].transData,
                       bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))

        # Empirical CDF
        sorted_data = np.sort(data)
        y_vals = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
        axes[1, 1].plot(sorted_data, y_vals, 'b-', linewidth=2, label='Empirical CDF')

        if theoretical_dist == 'normal':
            mu, sigma = stats.norm.fit(data)
            x_cdf = np.linspace(data.min(), data.max(), 1000)
            axes[1, 1].plot(x_cdf, stats.norm.cdf(x_cdf, mu, sigma),
                          'r--', linewidth=2, label='Theoretical CDF')

        axes[1, 1].set_title('Cumulative Distribution Function')
        axes[1, 1].set_xlabel('Value')
        axes[1, 1].set_ylabel('Cumulative Probability')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_hypothesis_test_results(self,
                                   test_results: Dict[str, Any],
                                   title: str = "Hypothesis Test Results",
                                   save_path: Optional[str] = None) -> plt.Figure:
        """
        Visualize hypothesis test results.

        Args:
            test_results: Dictionary containing test results
            title: Plot title
            save_path: Path to save the plot

        Returns:
            matplotlib Figure object
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(title, fontsize=16, fontweight='bold')

        # Extract test information
        test_names = list(test_results.keys())
        p_values = [result.get('p_value', 0) for result in test_results.values()]
        statistics = [result.get('statistic', 0) for result in test_results.values()]
        alpha = 0.05  # Common significance level

        # P-values bar plot
        colors = ['green' if p > alpha else 'red' for p in p_values]
        bars = axes[0, 0].bar(range(len(test_names)), p_values, color=colors, alpha=0.7)
        axes[0, 0].axhline(y=alpha, color='red', linestyle='--', linewidth=2, label=f'α = {alpha}')
        axes[0, 0].set_title('P-values by Test')
        axes[0, 0].set_ylabel('P-value')
        axes[0, 0].set_xticks(range(len(test_names)))
        axes[0, 0].set_xticklabels(test_names, rotation=45, ha='right')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # Add p-value labels on bars
        for i, (bar, p_val) in enumerate(zip(bars, p_values)):
            height = bar.get_height()
            axes[0, 0].text(bar.get_x() + bar.get_width()/2., height + 0.01,
                          f'{p_val:.4f}', ha='center', va='bottom', fontsize=9)

        # Test statistics
        axes[0, 1].bar(range(len(test_names)), statistics, color='steelblue', alpha=0.7)
        axes[0, 1].set_title('Test Statistics')
        axes[0, 1].set_ylabel('Statistic Value')
        axes[0, 1].set_xticks(range(len(test_names)))
        axes[0, 1].set_xticklabels(test_names, rotation=45, ha='right')
        axes[0, 1].grid(True, alpha=0.3)

        # Test results summary table
        axes[1, 0].axis('off')
        table_data = []
        for name, result in test_results.items():
            p_val = result.get('p_value', 0)
            stat = result.get('statistic', 0)
            decision = 'Reject H₀' if p_val < alpha else 'Fail to reject H₀'
            table_data.append([name, f'{stat:.4f}', f'{p_val:.4f}', decision])

        table = axes[1, 0].table(cellText=table_data,
                               colLabels=['Test', 'Statistic', 'P-value', 'Decision (α=0.05)'],
                               cellLoc='center',
                               loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.8)

        # Color code the decision column
        for i in range(len(table_data)):
            if 'Reject' in table_data[i][3]:
                table[(i+1, 3)].set_facecolor('lightcoral')
            else:
                table[(i+1, 3)].set_facecolor('lightgreen')

        axes[1, 0].set_title('Test Results Summary')

        # Power analysis visualization (if available)
        if any('power' in result for result in test_results.values()):
            powers = [result.get('power', 0) for result in test_results.values()]
            axes[1, 1].bar(range(len(test_names)), powers, color='orange', alpha=0.7)
            axes[1, 1].set_title('Statistical Power')
            axes[1, 1].set_ylabel('Power (1-β)')
            axes[1, 1].set_xticks(range(len(test_names)))
            axes[1, 1].set_xticklabels(test_names, rotation=45, ha='right')
            axes[1, 1].axhline(y=0.8, color='green', linestyle='--', linewidth=2, label='Power = 0.8')
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
        else:
            # Effect size plot if power not available
            axes[1, 1].text(0.5, 0.5, 'Effect size analysis\nnot available',
                          transform=axes[1, 1].transAxes, ha='center', va='center',
                          bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
            axes[1, 1].set_title('Effect Size Analysis')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_monte_carlo_results(self,
                               simulation_results: Dict[str, np.ndarray],
                               confidence_levels: List[float] = [0.95, 0.99],
                               title: str = "Monte Carlo Simulation Results",
                               save_path: Optional[str] = None) -> plt.Figure:
        """
        Visualize Monte Carlo simulation results.

        Args:
            simulation_results: Dictionary of simulation outputs
            confidence_levels: Confidence levels for intervals
            title: Plot title
            save_path: Path to save the plot

        Returns:
            matplotlib Figure object
        """
        n_metrics = len(simulation_results)
        n_cols = min(3, n_metrics)
        n_rows = (n_metrics + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))
        if n_metrics == 1:
            axes = [axes]
        elif n_rows == 1:
            axes = [axes]
        else:
            axes = axes.flatten()

        fig.suptitle(title, fontsize=16, fontweight='bold')

        for idx, (metric_name, results) in enumerate(simulation_results.items()):
            if idx >= len(axes):
                break

            ax = axes[idx]

            # Histogram of results
            n_bins = min(50, len(results) // 10)
            counts, bins, patches = ax.hist(results, bins=n_bins, density=True,
                                          alpha=0.7, color='steelblue', edgecolor='black')

            # Statistical measures
            mean_val = np.mean(results)
            median_val = np.median(results)
            std_val = np.std(results)

            # Confidence intervals
            for conf_level in confidence_levels:
                alpha_level = (1 - conf_level) / 2
                lower = np.percentile(results, 100 * alpha_level)
                upper = np.percentile(results, 100 * (1 - alpha_level))

                ax.axvline(lower, color='red', linestyle='--', alpha=0.8,
                          label=f'{conf_level*100:.0f}% CI')
                ax.axvline(upper, color='red', linestyle='--', alpha=0.8)

                # Shade confidence interval
                ax.axvspan(lower, upper, alpha=0.2, color='red')

            # Mean and median lines
            ax.axvline(mean_val, color='green', linewidth=2, label=f'Mean: {mean_val:.4f}')
            ax.axvline(median_val, color='orange', linewidth=2, label=f'Median: {median_val:.4f}')

            # Kernel density estimation
            try:
                kde_x = np.linspace(results.min(), results.max(), 1000)
                kde = stats.gaussian_kde(results)
                ax.plot(kde_x, kde(kde_x), 'purple', linewidth=2, label='KDE')
            except Exception:
                pass

            ax.set_title(f'{metric_name}\n(σ = {std_val:.4f})')
            ax.set_xlabel('Value')
            ax.set_ylabel('Density')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

            # Add statistics text box
            stats_text = f"""n = {len(results)}
CV = {std_val/abs(mean_val):.3f}
Skew = {stats.skew(results):.3f}
Kurt = {stats.kurtosis(results):.3f}"""

            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                   verticalalignment='top', fontsize=8,
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

        # Hide unused subplots
        for idx in range(n_metrics, len(axes)):
            axes[idx].axis('off')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_correlation_matrix(self,
                              data: Union[pd.DataFrame, np.ndarray],
                              labels: Optional[List[str]] = None,
                              method: str = 'pearson',
                              title: str = "Correlation Matrix",
                              save_path: Optional[str] = None) -> plt.Figure:
        """
        Create correlation matrix heatmap.

        Args:
            data: Data matrix or DataFrame
            labels: Variable labels
            method: Correlation method ('pearson', 'spearman', 'kendall')
            title: Plot title
            save_path: Path to save the plot

        Returns:
            matplotlib Figure object
        """
        if isinstance(data, np.ndarray):
            if labels is None:
                labels = [f'Var_{i+1}' for i in range(data.shape[1])]
            df = pd.DataFrame(data, columns=labels)
        else:
            df = data

        # Calculate correlation matrix
        corr_matrix = df.corr(method=method)

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))

        # Create heatmap
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))  # Mask upper triangle

        # Use matplotlib imshow instead of seaborn heatmap
        masked_corr = np.ma.masked_where(mask, corr_matrix)
        im = ax.imshow(masked_corr, cmap='RdBu_r', vmin=-1, vmax=1, aspect='equal')

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(f'{method.capitalize()} Correlation')

        # Add text annotations
        for i in range(len(corr_matrix)):
            for j in range(len(corr_matrix)):
                if not mask[i, j]:  # Only annotate unmasked values
                    ax.text(j, i, f'{corr_matrix[i, j]:.3f}',
                           ha='center', va='center', color='black')

        ax.set_title(f'{title} ({method.capitalize()})', fontsize=14, fontweight='bold')

        # Customize appearance
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        plt.setp(ax.get_yticklabels(), rotation=0)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_convergence_analysis(self,
                                convergence_data: Dict[str, List[float]],
                                title: str = "Convergence Analysis",
                                save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot convergence behavior of iterative algorithms.

        Args:
            convergence_data: Dictionary with metric names and convergence values
            title: Plot title
            save_path: Path to save the plot

        Returns:
            matplotlib Figure object
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(title, fontsize=16, fontweight='bold')

        # Main convergence plot
        for metric_name, values in convergence_data.items():
            iterations = range(1, len(values) + 1)
            axes[0, 0].plot(iterations, values, linewidth=2, label=metric_name, marker='o', markersize=3)

        axes[0, 0].set_title('Convergence Trajectories')
        axes[0, 0].set_xlabel('Iteration')
        axes[0, 0].set_ylabel('Value')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].set_yscale('log')  # Log scale often better for convergence

        # Convergence rate analysis
        if len(convergence_data) > 0:
            # Take first metric for detailed analysis
            first_metric = list(convergence_data.keys())[0]
            values = convergence_data[first_metric]

            if len(values) > 1:
                # Calculate convergence rate
                diff_values = np.abs(np.diff(values))
                iterations = range(1, len(diff_values) + 1)
                axes[0, 1].semilogy(iterations, diff_values, 'b-', linewidth=2, marker='o')
                axes[0, 1].set_title(f'Convergence Rate - {first_metric}')
                axes[0, 1].set_xlabel('Iteration')
                axes[0, 1].set_ylabel('|Δ Value|')
                axes[0, 1].grid(True, alpha=0.3)

        # Rolling statistics
        window_size = max(5, len(values) // 10) if 'values' in locals() else 5
        for i, (metric_name, values) in enumerate(convergence_data.items()):
            if len(values) > window_size:
                rolling_mean = pd.Series(values).rolling(window=window_size).mean()
                rolling_std = pd.Series(values).rolling(window=window_size).std()
                iterations = range(len(values))

                axes[1, 0].plot(iterations, rolling_mean, linewidth=2, label=f'{metric_name} (mean)')
                axes[1, 0].fill_between(iterations,
                                      rolling_mean - rolling_std,
                                      rolling_mean + rolling_std,
                                      alpha=0.3)

        axes[1, 0].set_title(f'Rolling Statistics (window={window_size})')
        axes[1, 0].set_xlabel('Iteration')
        axes[1, 0].set_ylabel('Value')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        # Final convergence statistics
        axes[1, 1].axis('off')
        stats_text = "Convergence Statistics:\n\n"

        for metric_name, values in convergence_data.items():
            if len(values) > 1:
                final_value = values[-1]
                initial_value = values[0]
                relative_change = abs((final_value - initial_value) / initial_value) if initial_value != 0 else 0

                # Estimate convergence rate (slope of log difference)
                if len(values) > 5:
                    diff_values = np.abs(np.diff(values[-10:]))  # Last 10 differences
                    if np.all(diff_values > 0):
                        log_diffs = np.log(diff_values)
                        slope = np.polyfit(range(len(log_diffs)), log_diffs, 1)[0]
                        conv_rate = f"{slope:.4f}"
                    else:
                        conv_rate = "Converged"
                else:
                    conv_rate = "N/A"

                stats_text += f"{metric_name}:\n"
                stats_text += f"  Final: {final_value:.6f}\n"
                stats_text += f"  Rel. Change: {relative_change:.2%}\n"
                stats_text += f"  Conv. Rate: {conv_rate}\n\n"

        axes[1, 1].text(0.1, 0.9, stats_text, transform=axes[1, 1].transAxes,
                       fontsize=10, verticalalignment='top',
                       bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray"))

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig