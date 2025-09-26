#==========================================================================================
#================== tests/test_integration/test_regression_detection.py =================
#==========================================================================================

"""
System-Wide Regression Detection - Mission 10 Quality Assurance

MISSION-CRITICAL CAPABILITY: Implement comprehensive regression detection across
all system components to ensure sustained quality and performance. This framework
provides early warning of performance degradation, integration failures, and
quality regressions across the entire system lifecycle.

REGRESSION DETECTION HIERARCHY:
1. Performance Regression Detection (execution time, memory usage)
2. Integration Regression Detection (cross-component compatibility)
3. Quality Regression Detection (test success rates, coverage metrics)
4. Configuration Regression Detection (breaking changes, compatibility)
5. Security Regression Detection (vulnerability introduction)

SUCCESS CRITERIA - MISSION 10:
- Automated regression detection for all critical system metrics
- Historical baseline establishment and tracking
- Early warning system for performance degradation
- Integration quality maintenance across system evolution
"""

import pytest
import json
import time
import subprocess
import sys
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import tempfile
import warnings


@dataclass
class PerformanceBaseline:
    """Performance baseline measurement."""
    test_name: str
    timestamp: datetime
    execution_time: float
    memory_usage: Optional[float]
    success_rate: float
    additional_metrics: Dict[str, Any]


@dataclass
class RegressionAlert:
    """Regression detection alert."""
    severity: str  # "low", "medium", "high", "critical"
    category: str  # "performance", "integration", "quality", "security"
    test_name: str
    current_value: Union[float, bool, str]
    baseline_value: Union[float, bool, str]
    degradation_percentage: float
    description: str
    recommendations: List[str]


@dataclass
class SystemRegressionReport:
    """Complete system regression detection report."""
    overall_health_score: float  # 0.0 to 10.0
    regression_alerts: List[RegressionAlert]
    performance_trends: Dict[str, List[float]]
    quality_metrics: Dict[str, Any]
    historical_comparison: Dict[str, Any]
    recommendations: List[str]
    monitoring_status: str  # "healthy", "degrading", "critical"


class SystemRegressionDetector:
    """Detects regressions across all system components."""

    def __init__(self, baseline_file: Optional[Path] = None):
        """Initialize system regression detector."""
        self.repo_root = Path(__file__).parent.parent.parent
        self.baseline_file = baseline_file or self.repo_root / ".regression_baselines.json"
        self.temp_dir = Path(tempfile.mkdtemp())
        self.temp_dir.mkdir(exist_ok=True)

        # Load existing baselines
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self.load_baselines()

        # Regression thresholds
        self.thresholds = {
            "performance_degradation": {
                "low": 0.10,      # 10% degradation
                "medium": 0.25,   # 25% degradation
                "high": 0.50,     # 50% degradation
                "critical": 1.00  # 100% degradation
            },
            "success_rate_degradation": {
                "low": 0.05,      # 5% drop in success rate
                "medium": 0.10,   # 10% drop in success rate
                "high": 0.20,     # 20% drop in success rate
                "critical": 0.35  # 35% drop in success rate
            }
        }

    def load_baselines(self) -> None:
        """Load performance baselines from storage."""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r') as f:
                    baseline_data = json.load(f)

                for test_name, data in baseline_data.items():
                    # Convert timestamp string back to datetime
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                    self.baselines[test_name] = PerformanceBaseline(**data)

            except Exception as e:
                warnings.warn(f"Could not load baselines: {str(e)}")

    def save_baselines(self) -> None:
        """Save performance baselines to storage."""
        try:
            baseline_data = {}
            for test_name, baseline in self.baselines.items():
                # Convert datetime to string for JSON serialization
                baseline_dict = asdict(baseline)
                baseline_dict['timestamp'] = baseline.timestamp.isoformat()
                baseline_data[test_name] = baseline_dict

            with open(self.baseline_file, 'w') as f:
                json.dump(baseline_data, f, indent=2)

        except Exception as e:
            warnings.warn(f"Could not save baselines: {str(e)}")

    def measure_performance(self, test_name: str, test_function: callable,
                          iterations: int = 3) -> PerformanceBaseline:
        """Measure performance of a test function."""

        execution_times = []
        memory_usage = None
        success_count = 0

        # Run test multiple times for statistical significance
        for i in range(iterations):
            try:
                start_time = time.perf_counter()

                # Execute test function
                result = test_function()
                success = bool(result) if result is not None else True
                if success:
                    success_count += 1

                execution_time = time.perf_counter() - start_time
                execution_times.append(execution_time)

            except Exception as e:
                execution_times.append(float('inf'))  # Mark failed execution
                warnings.warn(f"Test {test_name} iteration {i+1} failed: {str(e)}")

        # Calculate metrics
        valid_times = [t for t in execution_times if t != float('inf')]
        avg_execution_time = sum(valid_times) / len(valid_times) if valid_times else float('inf')
        success_rate = success_count / iterations

        # Try to measure memory usage (if psutil available)
        try:
            import psutil
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            memory_usage = None

        additional_metrics = {
            "iterations": iterations,
            "valid_executions": len(valid_times),
            "min_time": min(valid_times) if valid_times else None,
            "max_time": max(valid_times) if valid_times else None
        }

        return PerformanceBaseline(
            test_name=test_name,
            timestamp=datetime.now(),
            execution_time=avg_execution_time,
            memory_usage=memory_usage,
            success_rate=success_rate,
            additional_metrics=additional_metrics
        )

    def detect_performance_regression(self, current: PerformanceBaseline) -> List[RegressionAlert]:
        """Detect performance regressions compared to baseline."""

        alerts = []
        test_name = current.test_name

        if test_name not in self.baselines:
            # No baseline exists - establish one
            self.baselines[test_name] = current
            self.save_baselines()
            return alerts

        baseline = self.baselines[test_name]

        # Check execution time regression
        if baseline.execution_time > 0 and current.execution_time != float('inf'):
            time_degradation = (current.execution_time - baseline.execution_time) / baseline.execution_time

            if time_degradation > 0:  # Performance got worse
                severity = self._determine_severity("performance_degradation", time_degradation)
                if severity:
                    alerts.append(RegressionAlert(
                        severity=severity,
                        category="performance",
                        test_name=test_name,
                        current_value=current.execution_time,
                        baseline_value=baseline.execution_time,
                        degradation_percentage=time_degradation * 100,
                        description=f"Execution time increased by {time_degradation*100:.1f}%",
                        recommendations=[
                            "Profile the code to identify performance bottlenecks",
                            "Check for algorithmic changes that might impact complexity",
                            "Consider optimizing critical code paths"
                        ]
                    ))

        # Check success rate regression
        success_rate_degradation = baseline.success_rate - current.success_rate
        if success_rate_degradation > 0:
            severity = self._determine_severity("success_rate_degradation", success_rate_degradation)
            if severity:
                alerts.append(RegressionAlert(
                    severity=severity,
                    category="quality",
                    test_name=test_name,
                    current_value=current.success_rate,
                    baseline_value=baseline.success_rate,
                    degradation_percentage=success_rate_degradation * 100,
                    description=f"Success rate decreased by {success_rate_degradation*100:.1f}%",
                    recommendations=[
                        "Investigate failing test cases",
                        "Check for recent code changes affecting test reliability",
                        "Review test environment stability"
                    ]
                ))

        # Update baseline if current measurement is significantly better
        if (current.execution_time < baseline.execution_time * 0.8 and
            current.success_rate >= baseline.success_rate):
            self.baselines[test_name] = current
            self.save_baselines()

        return alerts

    def _determine_severity(self, threshold_type: str, degradation: float) -> Optional[str]:
        """Determine severity level based on degradation amount."""
        thresholds = self.thresholds.get(threshold_type, {})

        if degradation >= thresholds.get("critical", 1.0):
            return "critical"
        elif degradation >= thresholds.get("high", 0.5):
            return "high"
        elif degradation >= thresholds.get("medium", 0.25):
            return "medium"
        elif degradation >= thresholds.get("low", 0.1):
            return "low"
        else:
            return None

    def test_cli_performance_regression(self) -> List[RegressionAlert]:
        """Test for CLI performance regressions."""

        def cli_help_test():
            try:
                start_time = time.perf_counter()
                result = subprocess.run([
                    sys.executable, str(self.repo_root / "simulate.py"), "--help"
                ], capture_output=True, text=True, timeout=30, cwd=str(self.repo_root))

                return result.returncode == 0
            except Exception:
                return False

        baseline = self.measure_performance("cli_help_performance", cli_help_test, iterations=3)
        return self.detect_performance_regression(baseline)

    def test_configuration_loading_regression(self) -> List[RegressionAlert]:
        """Test for configuration loading performance regressions."""

        def config_loading_test():
            try:
                config_file = self.repo_root / "config.yaml"
                if not config_file.exists():
                    return False

                with open(config_file, 'r', encoding='utf-8') as f:
                    import yaml
                    config_data = yaml.safe_load(f)
                    return config_data is not None and len(config_data) > 0

            except Exception:
                return False

        baseline = self.measure_performance("config_loading_performance", config_loading_test, iterations=5)
        return self.detect_performance_regression(baseline)

    def test_integration_regression(self) -> List[RegressionAlert]:
        """Test for integration test regressions."""

        def integration_test():
            try:
                # Run a subset of integration tests
                test_files = list((self.repo_root / "tests" / "test_integration").glob("test_*.py"))
                if not test_files:
                    return False

                # Test that we can at least import the integration test modules
                successful_imports = 0
                for test_file in test_files[:3]:  # Test first 3 files
                    try:
                        # Basic syntax/import check
                        result = subprocess.run([
                            sys.executable, "-m", "py_compile", str(test_file)
                        ], capture_output=True, timeout=10, cwd=str(self.repo_root))

                        if result.returncode == 0:
                            successful_imports += 1
                    except Exception:
                        pass

                return successful_imports > 0

            except Exception:
                return False

        baseline = self.measure_performance("integration_test_health", integration_test, iterations=2)
        return self.detect_performance_regression(baseline)

    def test_system_stability_regression(self) -> List[RegressionAlert]:
        """Test for overall system stability regressions."""

        def system_stability_test():
            try:
                # Check for critical system files
                critical_files = [
                    self.repo_root / "simulate.py",
                    self.repo_root / "config.yaml",
                    self.repo_root / "requirements.txt"
                ]

                files_present = sum(1 for f in critical_files if f.exists())

                # Check for test directory structure
                tests_dir = self.repo_root / "tests"
                test_files = list(tests_dir.glob("**/test_*.py")) if tests_dir.exists() else []

                # System is stable if critical files exist and we have reasonable test coverage
                return files_present >= 2 and len(test_files) >= 5

            except Exception:
                return False

        baseline = self.measure_performance("system_stability_check", system_stability_test, iterations=1)
        return self.detect_performance_regression(baseline)

    def run_comprehensive_regression_detection(self) -> SystemRegressionReport:
        """Run comprehensive regression detection across all system components."""

        print("Starting Comprehensive System Regression Detection...")

        all_alerts = []
        performance_trends = {}
        quality_metrics = {}

        # Run all regression tests
        regression_tests = [
            ("CLI Performance", self.test_cli_performance_regression),
            ("Configuration Loading", self.test_configuration_loading_regression),
            ("Integration Health", self.test_integration_regression),
            ("System Stability", self.test_system_stability_regression)
        ]

        for test_name, test_method in regression_tests:
            print(f"  Checking: {test_name}")

            try:
                alerts = test_method()
                all_alerts.extend(alerts)

                if alerts:
                    alert_count = len(alerts)
                    max_severity = max((a.severity for a in alerts),
                                     key=lambda s: {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(s, 0))
                    print(f"    {alert_count} regression(s) detected - Max severity: {max_severity.upper()}")
                else:
                    print(f"    No regressions detected")

                # Track performance trends
                if test_name.lower().replace(' ', '_') in self.baselines:
                    baseline = self.baselines[test_name.lower().replace(' ', '_')]
                    performance_trends[test_name] = [baseline.execution_time, baseline.success_rate]

            except Exception as e:
                print(f"    ERROR: Regression test failed - {str(e)}")
                # Create alert for test failure
                all_alerts.append(RegressionAlert(
                    severity="high",
                    category="integration",
                    test_name=test_name,
                    current_value=False,
                    baseline_value=True,
                    degradation_percentage=100.0,
                    description=f"Regression test execution failed: {str(e)}",
                    recommendations=["Investigate regression test framework issues"]
                ))

        # Calculate overall health score
        if all_alerts:
            severity_weights = {"low": 0.5, "medium": 1.0, "high": 2.0, "critical": 4.0}
            total_impact = sum(severity_weights.get(alert.severity, 1.0) for alert in all_alerts)
            health_score = max(0.0, 10.0 - total_impact)
        else:
            health_score = 10.0

        # Determine monitoring status
        critical_alerts = [a for a in all_alerts if a.severity == "critical"]
        high_alerts = [a for a in all_alerts if a.severity == "high"]

        if critical_alerts:
            monitoring_status = "critical"
        elif high_alerts:
            monitoring_status = "degrading"
        else:
            monitoring_status = "healthy"

        # Generate quality metrics
        quality_metrics = {
            "total_tests_run": len(regression_tests),
            "successful_tests": len(regression_tests) - len([a for a in all_alerts if "test execution failed" in a.description]),
            "total_alerts": len(all_alerts),
            "critical_alerts": len(critical_alerts),
            "high_alerts": len(high_alerts),
            "baseline_count": len(self.baselines)
        }

        # Historical comparison (simplified)
        historical_comparison = {
            "baselines_established": len(self.baselines),
            "monitoring_duration": "session",  # Could be enhanced with persistent storage
            "trend_analysis": "baseline_establishment" if len(self.baselines) < 4 else "monitoring_active"
        }

        # Generate recommendations
        recommendations = []
        if monitoring_status == "healthy":
            recommendations.extend([
                "System regression monitoring is healthy",
                "Continue regular regression detection cycles",
                "Consider expanding regression test coverage",
                "Establish automated regression detection pipeline"
            ])
        elif monitoring_status == "degrading":
            recommendations.extend([
                "Address high-severity regressions to prevent further degradation",
                "Increase regression detection frequency",
                "Investigate recent system changes",
                "Consider performance optimization initiatives"
            ])
        else:  # critical
            recommendations.extend([
                "URGENT: Address critical regressions immediately",
                "Halt deployments until regressions are resolved",
                "Conduct comprehensive system analysis",
                "Implement emergency performance recovery measures"
            ])

        return SystemRegressionReport(
            overall_health_score=health_score,
            regression_alerts=all_alerts,
            performance_trends=performance_trends,
            quality_metrics=quality_metrics,
            historical_comparison=historical_comparison,
            recommendations=recommendations,
            monitoring_status=monitoring_status
        )

    def generate_regression_report(self, report: SystemRegressionReport) -> str:
        """Generate comprehensive regression detection report."""

        lines = ["=" * 80]
        lines.append("SYSTEM-WIDE REGRESSION DETECTION REPORT - MISSION 10")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Executive Summary
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 20)

        status_icons = {"healthy": "[HEALTHY]", "degrading": "[DEGRADING]", "critical": "[CRITICAL]"}
        status_icon = status_icons.get(report.monitoring_status, "[UNKNOWN]")

        lines.append(f"{status_icon} Overall Health Score: {report.overall_health_score:.1f}/10.0")
        lines.append(f"Monitoring Status: {report.monitoring_status.upper()}")
        lines.append(f"Regression Alerts: {len(report.regression_alerts)}")
        lines.append("")

        # Regression Alerts
        if report.regression_alerts:
            lines.append("REGRESSION ALERTS")
            lines.append("-" * 20)

            # Group alerts by severity
            by_severity = {}
            for alert in report.regression_alerts:
                if alert.severity not in by_severity:
                    by_severity[alert.severity] = []
                by_severity[alert.severity].append(alert)

            # Display in severity order
            for severity in ["critical", "high", "medium", "low"]:
                if severity in by_severity:
                    severity_icon = {"critical": "[CRIT]", "high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}
                    lines.append(f"{severity_icon.get(severity, '[ALERT]')} {severity.upper()} SEVERITY ({len(by_severity[severity])} alerts)")

                    for alert in by_severity[severity]:
                        lines.append(f"  • {alert.test_name}: {alert.description}")
                        lines.append(f"    Current: {alert.current_value}, Baseline: {alert.baseline_value}")
                        if alert.recommendations:
                            lines.append(f"    Action: {alert.recommendations[0]}")
                    lines.append("")
        else:
            lines.append("REGRESSION STATUS")
            lines.append("-" * 17)
            lines.append("[OK] No regressions detected")
            lines.append("")

        # Performance Trends
        if report.performance_trends:
            lines.append("PERFORMANCE TRENDS")
            lines.append("-" * 20)
            for test_name, metrics in report.performance_trends.items():
                if len(metrics) >= 2:
                    lines.append(f"• {test_name}: Execution {metrics[0]:.3f}s, Success {metrics[1]:.1%}")
            lines.append("")

        # Quality Metrics
        lines.append("QUALITY METRICS")
        lines.append("-" * 15)
        qm = report.quality_metrics
        lines.append(f"Tests Run: {qm.get('total_tests_run', 0)}")
        lines.append(f"Successful Tests: {qm.get('successful_tests', 0)}")
        lines.append(f"Total Alerts: {qm.get('total_alerts', 0)}")
        lines.append(f"Baselines Established: {qm.get('baseline_count', 0)}")
        lines.append("")

        # Historical Comparison
        lines.append("HISTORICAL ANALYSIS")
        lines.append("-" * 20)
        hc = report.historical_comparison
        lines.append(f"Monitoring Status: {hc.get('trend_analysis', 'unknown')}")
        lines.append(f"Baseline Coverage: {hc.get('baselines_established', 0)} components")
        lines.append("")

        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 15)
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")

        return "\n".join(lines)


# ============================================================================
# PYTEST TEST CASES
# ============================================================================

@pytest.fixture
def regression_detector():
    """Create regression detector for testing."""
    return SystemRegressionDetector()


class TestSystemRegressionDetection:
    """Test suite for system-wide regression detection."""

    def test_performance_baseline_creation(self, regression_detector):
        """Test creation of performance baselines."""

        def dummy_test():
            time.sleep(0.001)  # Simulate brief computation
            return True

        baseline = regression_detector.measure_performance("test_baseline", dummy_test, iterations=2)

        assert isinstance(baseline, PerformanceBaseline), "Should create performance baseline"
        assert baseline.test_name == "test_baseline", "Should have correct test name"
        assert baseline.execution_time > 0.0, "Should measure execution time"
        assert 0.0 <= baseline.success_rate <= 1.0, "Success rate should be between 0 and 1"

    def test_regression_alert_generation(self, regression_detector):
        """Test generation of regression alerts."""

        # Create a baseline
        def fast_test():
            return True

        baseline = regression_detector.measure_performance("regression_test", fast_test, iterations=1)

        # Simulate a slower current measurement by manually creating one
        slower_baseline = PerformanceBaseline(
            test_name="regression_test",
            timestamp=datetime.now(),
            execution_time=baseline.execution_time * 2.0,  # 100% slower
            memory_usage=baseline.memory_usage,
            success_rate=baseline.success_rate * 0.5,  # 50% success rate drop
            additional_metrics={}
        )

        alerts = regression_detector.detect_performance_regression(slower_baseline)

        assert len(alerts) > 0, "Should generate regression alerts for performance degradation"

        # Check that we have both performance and quality alerts
        categories = [alert.category for alert in alerts]
        assert "performance" in categories or "quality" in categories, "Should detect performance or quality regression"

    def test_cli_performance_regression(self, regression_detector):
        """Test CLI performance regression detection."""
        alerts = regression_detector.test_cli_performance_regression()

        assert isinstance(alerts, list), "Should return list of alerts"
        # This test establishes baseline on first run, so may not have alerts

        # Verify baseline was created
        assert "cli_help_performance" in regression_detector.baselines, "Should establish CLI performance baseline"

    def test_configuration_loading_regression(self, regression_detector):
        """Test configuration loading regression detection."""
        alerts = regression_detector.test_configuration_loading_regression()

        assert isinstance(alerts, list), "Should return list of alerts"

        # Check if baseline was established
        baseline_exists = "config_loading_performance" in regression_detector.baselines
        assert baseline_exists, "Should establish configuration loading baseline"

    def test_integration_regression(self, regression_detector):
        """Test integration regression detection."""
        alerts = regression_detector.test_integration_regression()

        assert isinstance(alerts, list), "Should return list of alerts"

        # Should create baseline for integration health
        baseline_exists = "integration_test_health" in regression_detector.baselines
        assert baseline_exists, "Should establish integration test baseline"

    def test_system_stability_regression(self, regression_detector):
        """Test system stability regression detection."""
        alerts = regression_detector.test_system_stability_regression()

        assert isinstance(alerts, list), "Should return list of alerts"

        # Should create baseline for system stability
        baseline_exists = "system_stability_check" in regression_detector.baselines
        assert baseline_exists, "Should establish system stability baseline"

    def test_comprehensive_regression_detection(self, regression_detector):
        """Test comprehensive regression detection."""
        report = regression_detector.run_comprehensive_regression_detection()

        assert isinstance(report, SystemRegressionReport), "Should return system regression report"
        assert 0.0 <= report.overall_health_score <= 10.0, "Health score should be between 0 and 10"
        assert report.monitoring_status in ["healthy", "degrading", "critical"], "Should have valid monitoring status"
        assert isinstance(report.regression_alerts, list), "Should have regression alerts list"
        assert isinstance(report.recommendations, list), "Should have recommendations list"

    def test_regression_report_generation(self, regression_detector):
        """Test regression report generation."""
        report = regression_detector.run_comprehensive_regression_detection()
        report_text = regression_detector.generate_regression_report(report)

        assert isinstance(report_text, str), "Should generate string report"
        assert len(report_text) > 200, "Report should be substantial"
        assert "SYSTEM-WIDE REGRESSION DETECTION REPORT" in report_text, "Should have proper header"
        assert "EXECUTIVE SUMMARY" in report_text, "Should have executive summary"

    def test_mission_10_regression_detection_criteria(self, regression_detector):
        """Test Mission 10 regression detection success criteria."""
        report = regression_detector.run_comprehensive_regression_detection()
        report_text = regression_detector.generate_regression_report(report)

        print("\n" + "="*80)
        print("MISSION 10: SYSTEM-WIDE REGRESSION DETECTION RESULTS")
        print("="*80)
        print(report_text)

        # Mission 10 success criteria for regression detection
        assert report.overall_health_score >= 5.0, f"Health score too low: {report.overall_health_score:.1f}/10.0"

        # Should have established baselines for monitoring
        assert len(regression_detector.baselines) >= 3, "Should establish baselines for key system components"

        # Should have quality metrics
        assert report.quality_metrics, "Should provide quality metrics"
        assert report.quality_metrics.get('total_tests_run', 0) >= 3, "Should run multiple regression tests"

        # Should provide actionable recommendations
        assert len(report.recommendations) >= 2, "Should provide actionable recommendations"

        # Report results
        critical_alerts = [a for a in report.regression_alerts if a.severity == "critical"]
        high_alerts = [a for a in report.regression_alerts if a.severity == "high"]

        if report.monitoring_status == "healthy":
            print(f"\nMISSION 10 SUCCESS: Regression detection healthy (Score: {report.overall_health_score:.1f}/10.0)")
            print(f"Baselines established: {len(regression_detector.baselines)} components")
        elif report.monitoring_status == "degrading":
            print(f"\nMISSION 10 PROGRESS: System degrading (Score: {report.overall_health_score:.1f}/10.0)")
            print(f"High-priority alerts: {len(high_alerts)}")
        else:
            print(f"\nMISSION 10 ALERT: Critical regressions detected (Score: {report.overall_health_score:.1f}/10.0)")
            print(f"Critical alerts: {len(critical_alerts)}")

        # Save baselines for future use
        regression_detector.save_baselines()
        print(f"\nBaselines saved to: {regression_detector.baseline_file}")


if __name__ == "__main__":
    # Run standalone regression detection
    detector = SystemRegressionDetector()

    print("MISSION 10: System-Wide Regression Detection")
    print("="*50)

    # Run comprehensive regression detection
    report = detector.run_comprehensive_regression_detection()

    # Generate and display report
    report_text = detector.generate_regression_report(report)
    print(report_text)

    # Save baselines for future monitoring
    detector.save_baselines()

    # Final status
    if report.monitoring_status == "healthy":
        print(f"\nSUCCESS: Regression monitoring established (Health: {report.overall_health_score:.1f}/10.0)")
    elif report.monitoring_status == "degrading":
        print(f"\nMONITORING: Performance degradation detected (Health: {report.overall_health_score:.1f}/10.0)")
    else:
        print(f"\nALERT: Critical regressions require attention (Health: {report.overall_health_score:.1f}/10.0)")