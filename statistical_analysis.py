#==========================================================================================\\\
#============================== statistical_analysis.py ==============================\\\
#==========================================================================================\\\
"""
Statistical analysis framework for SMC controllers comparison.

This module implements rigorous statistical methods for comparing the performance
of Classical SMC, Adaptive SMC, STA SMC, and Hybrid SMC controllers, including
ANOVA, post-hoc tests, effect size calculations, and confidence intervals.
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import f_oneway, tukey_hsd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns
from experimental_design import ControllerType, PerformanceMetrics


@dataclass
class StatisticalResult:
    """Container for statistical analysis results."""
    metric_name: str
    f_statistic: float
    p_value: float
    effect_size: float
    significant: bool
    confidence_level: float
    post_hoc_results: Dict[str, float]
    summary_statistics: Dict[str, Dict[str, float]]


class StatisticalAnalyzer:
    """Comprehensive statistical analysis for SMC comparison study."""

    def __init__(self, alpha: float = 0.05, confidence_level: float = 0.95):
        """
        Initialize statistical analyzer.

        Parameters
        ----------
        alpha : float
            Significance level (default: 0.05)
        confidence_level : float
            Confidence level for intervals (default: 0.95)
        """
        self.alpha = alpha
        self.confidence_level = confidence_level
        self.controllers = [e.value for e in ControllerType]

    def analyze_metric_comparison(self,
                                results: Dict[str, List[PerformanceMetrics]],
                                metric_name: str) -> StatisticalResult:
        """
        Perform comprehensive statistical analysis for a single performance metric.

        Parameters
        ----------
        results : Dict[str, List[PerformanceMetrics]]
            Dictionary mapping controller names to lists of performance metrics
        metric_name : str
            Name of the metric to analyze (e.g., 'settling_time', 'chattering_index')

        Returns
        -------
        StatisticalResult
            Complete statistical analysis results
        """

        # Extract metric values for each controller
        controller_data = {}
        for controller_name, metrics_list in results.items():
            metric_values = [getattr(metric, metric_name) for metric in metrics_list]
            controller_data[controller_name] = np.array(metric_values)

        # Check assumptions
        self._check_assumptions(controller_data, metric_name)

        # Perform one-way ANOVA
        f_stat, p_value = f_oneway(*controller_data.values())

        # Calculate effect size (eta-squared)
        effect_size = self._calculate_eta_squared(controller_data, f_stat)

        # Determine significance
        significant = p_value < self.alpha

        # Post-hoc analysis if significant
        post_hoc_results = {}
        if significant:
            post_hoc_results = self._perform_tukey_hsd(controller_data)

        # Summary statistics
        summary_stats = self._calculate_summary_statistics(controller_data)

        return StatisticalResult(
            metric_name=metric_name,
            f_statistic=f_stat,
            p_value=p_value,
            effect_size=effect_size,
            significant=significant,
            confidence_level=self.confidence_level,
            post_hoc_results=post_hoc_results,
            summary_statistics=summary_stats
        )

    def power_analysis(self,
                      effect_size: float,
                      alpha: float = None,
                      n_per_group: int = 100) -> float:
        """
        Calculate statistical power for given effect size and sample size.

        Parameters
        ----------
        effect_size : float
            Expected effect size (Cohen's f)
        alpha : float, optional
            Significance level (uses instance default if None)
        n_per_group : int
            Sample size per group

        Returns
        -------
        float
            Statistical power (1 - β)
        """
        if alpha is None:
            alpha = self.alpha

        # Degrees of freedom
        df1 = len(self.controllers) - 1  # Between groups
        df2 = len(self.controllers) * (n_per_group - 1)  # Within groups

        # Non-centrality parameter
        ncp = effect_size**2 * len(self.controllers) * n_per_group

        # Critical F value
        f_critical = stats.f.ppf(1 - alpha, df1, df2)

        # Power calculation
        power = 1 - stats.ncf.cdf(f_critical, df1, df2, ncp)

        return power

    def sample_size_calculation(self,
                              effect_size: float,
                              power: float = 0.8,
                              alpha: float = None) -> int:
        """
        Calculate required sample size for desired power and effect size.

        Parameters
        ----------
        effect_size : float
            Expected effect size (Cohen's f)
        power : float
            Desired statistical power (default: 0.8)
        alpha : float, optional
            Significance level (uses instance default if None)

        Returns
        -------
        int
            Required sample size per group
        """
        if alpha is None:
            alpha = self.alpha

        # Binary search for sample size
        low, high = 5, 1000
        while low < high:
            mid = (low + high) // 2
            calculated_power = self.power_analysis(effect_size, alpha, mid)

            if calculated_power >= power:
                high = mid
            else:
                low = mid + 1

        return low

    def generate_comparison_report(self,
                                 all_results: Dict[str, StatisticalResult]) -> str:
        """
        Generate comprehensive comparison report.

        Parameters
        ----------
        all_results : Dict[str, StatisticalResult]
            Results for all analyzed metrics

        Returns
        -------
        str
            Formatted comparison report
        """

        report = []
        report.append("=" * 80)
        report.append("SMC CONTROLLERS STATISTICAL COMPARISON REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary table
        report.append("SUMMARY OF STATISTICAL TESTS")
        report.append("-" * 50)
        report.append(f"{'Metric':<25} {'F-stat':<10} {'p-value':<10} {'η²':<8} {'Significant':<12}")
        report.append("-" * 50)

        for metric_name, result in all_results.items():
            sig_indicator = "***" if result.p_value < 0.001 else "**" if result.p_value < 0.01 else "*" if result.p_value < 0.05 else "ns"
            report.append(f"{metric_name:<25} {result.f_statistic:<10.3f} {result.p_value:<10.3f} {result.effect_size:<8.3f} {sig_indicator:<12}")

        report.append("")
        report.append("*** p < 0.001, ** p < 0.01, * p < 0.05, ns = not significant")
        report.append("")

        # Detailed results for significant metrics
        significant_metrics = [name for name, result in all_results.items() if result.significant]

        if significant_metrics:
            report.append("DETAILED ANALYSIS FOR SIGNIFICANT METRICS")
            report.append("-" * 50)

            for metric_name in significant_metrics:
                result = all_results[metric_name]
                report.append(f"\n{metric_name.upper()}")
                report.append("-" * len(metric_name))

                # Best performing controller
                means = {controller: stats['mean'] for controller, stats in result.summary_statistics.items()}
                best_controller = min(means.keys(), key=lambda k: means[k])  # Assuming lower is better
                report.append(f"Best performing: {best_controller} (μ = {means[best_controller]:.4f})")

                # Effect size interpretation
                eta_squared = result.effect_size
                if eta_squared >= 0.14:
                    effect_interp = "Large effect"
                elif eta_squared >= 0.06:
                    effect_interp = "Medium effect"
                else:
                    effect_interp = "Small effect"

                report.append(f"Effect size: η² = {eta_squared:.3f} ({effect_interp})")

                # Post-hoc comparisons
                if result.post_hoc_results:
                    report.append("Pairwise comparisons (Tukey HSD):")
                    for comparison, p_val in result.post_hoc_results.items():
                        sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
                        report.append(f"  {comparison}: p = {p_val:.4f} {sig}")

        # Recommendations
        report.append("\nRECOMMENDATIONS")
        report.append("-" * 20)
        self._add_recommendations(report, all_results)

        return "\n".join(report)

    def _check_assumptions(self, controller_data: Dict[str, np.ndarray], metric_name: str):
        """Check ANOVA assumptions: normality and homogeneity of variance."""

        # Normality test (Shapiro-Wilk for each group)
        normality_results = {}
        for controller, data in controller_data.items():
            if len(data) >= 3:  # Minimum for Shapiro-Wilk
                stat, p_val = stats.shapiro(data)
                normality_results[controller] = p_val

        # Homogeneity of variance test (Levene's test)
        levene_stat, levene_p = stats.levene(*controller_data.values())

        # Print warnings if assumptions violated
        if any(p < 0.05 for p in normality_results.values()):
            print(f"WARNING: Normality assumption may be violated for {metric_name}")

        if levene_p < 0.05:
            print(f"WARNING: Homogeneity of variance assumption may be violated for {metric_name}")

    def _calculate_eta_squared(self, controller_data: Dict[str, np.ndarray], f_stat: float) -> float:
        """Calculate eta-squared effect size."""

        # Total sample size
        n_total = sum(len(data) for data in controller_data.values())

        # Number of groups
        k = len(controller_data)

        # Degrees of freedom
        df_between = k - 1
        df_total = n_total - 1

        # Eta-squared calculation
        eta_squared = (f_stat * df_between) / (f_stat * df_between + df_total - df_between)

        return eta_squared

    def _perform_tukey_hsd(self, controller_data: Dict[str, np.ndarray]) -> Dict[str, float]:
        """Perform Tukey HSD post-hoc test."""

        # Prepare data for tukey_hsd
        all_data = []
        all_labels = []

        for controller, data in controller_data.items():
            all_data.extend(data)
            all_labels.extend([controller] * len(data))

        # Perform Tukey HSD
        result = tukey_hsd(*controller_data.values())

        # Extract pairwise p-values
        controller_names = list(controller_data.keys())
        post_hoc_results = {}

        for i in range(len(controller_names)):
            for j in range(i + 1, len(controller_names)):
                comparison = f"{controller_names[i]} vs {controller_names[j]}"
                post_hoc_results[comparison] = result.pvalue[i, j]

        return post_hoc_results

    def _calculate_summary_statistics(self, controller_data: Dict[str, np.ndarray]) -> Dict[str, Dict[str, float]]:
        """Calculate summary statistics for each controller."""

        summary_stats = {}

        for controller, data in controller_data.items():
            stats_dict = {
                'mean': np.mean(data),
                'std': np.std(data, ddof=1),
                'median': np.median(data),
                'min': np.min(data),
                'max': np.max(data),
                'n': len(data),
                'se': np.std(data, ddof=1) / np.sqrt(len(data))  # Standard error
            }

            # Confidence interval for mean
            ci_margin = stats.t.ppf((1 + self.confidence_level) / 2, len(data) - 1) * stats_dict['se']
            stats_dict['ci_lower'] = stats_dict['mean'] - ci_margin
            stats_dict['ci_upper'] = stats_dict['mean'] + ci_margin

            summary_stats[controller] = stats_dict

        return summary_stats

    def _add_recommendations(self, report: List[str], all_results: Dict[str, StatisticalResult]):
        """Add practical recommendations based on statistical results."""

        # Identify best performing controller for each metric
        best_performers = {}
        for metric_name, result in all_results.items():
            if result.significant:
                means = {controller: stats['mean'] for controller, stats in result.summary_statistics.items()}
                best_controller = min(means.keys(), key=lambda k: means[k])  # Assuming lower is better
                best_performers[metric_name] = best_controller

        # Overall recommendation
        if best_performers:
            controller_counts = {}
            for controller in best_performers.values():
                controller_counts[controller] = controller_counts.get(controller, 0) + 1

            overall_best = max(controller_counts.keys(), key=lambda k: controller_counts[k])
            report.append(f"Overall best performer: {overall_best}")
            report.append(f"  - Outperforms in {controller_counts[overall_best]} out of {len(best_performers)} significant metrics")

        # Specific recommendations
        report.append("")
        report.append("Specific recommendations:")
        for metric, controller in best_performers.items():
            report.append(f"  - For {metric}: Use {controller}")


# Usage example
if __name__ == "__main__":
    # Example usage with mock data
    analyzer = StatisticalAnalyzer()

    # Calculate required sample size for medium effect
    medium_effect_size = 0.25  # Cohen's f for medium effect
    required_n = analyzer.sample_size_calculation(medium_effect_size, power=0.8)
    print(f"Required sample size per group for medium effect (f=0.25): {required_n}")

    # Calculate power for current design
    current_power = analyzer.power_analysis(medium_effect_size, n_per_group=100)
    print(f"Statistical power with n=100 per group: {current_power:.3f}")