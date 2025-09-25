#==========================================================================================\\\
#==================== src/interfaces/monitoring/diagnostics.py ========================\\\
#==========================================================================================\\\
"""
System diagnostics and troubleshooting tools for interface components.
This module provides comprehensive diagnostic capabilities including
system state analysis, performance profiling, error diagnosis,
resource utilization tracking, and automated troubleshooting
recommendations for all interface components.
"""

import asyncio
import logging
import threading
import time
import traceback
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
import psutil
import json


class DiagnosticLevel(Enum):
    """Diagnostic severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DiagnosticCategory(Enum):
    """Categories of diagnostic checks."""
    SYSTEM = "system"
    NETWORK = "network"
    HARDWARE = "hardware"
    PERFORMANCE = "performance"
    MEMORY = "memory"
    CONFIGURATION = "configuration"


@dataclass
class DiagnosticResult:
    """Result of a diagnostic check."""
    category: DiagnosticCategory
    level: DiagnosticLevel
    title: str
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    affected_components: Set[str] = field(default_factory=set)


@dataclass
class SystemProfile:
    """Comprehensive system profiling data."""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: Dict[str, float]
    network_io: Dict[str, int]
    process_count: int
    thread_count: int
    open_files: int
    network_connections: int
    system_load: Tuple[float, float, float]
    uptime: float


class DiagnosticCheck(ABC):
    """Base class for diagnostic checks."""

    def __init__(self, name: str, category: DiagnosticCategory):
        self.name = name
        self.category = category
        self.enabled = True
        self.last_run = None
        self.run_count = 0

    @abstractmethod
    async def run_check(self) -> List[DiagnosticResult]:
        """Run the diagnostic check."""
        pass


class SystemResourceCheck(DiagnosticCheck):
    """Check system resource utilization."""

    def __init__(self):
        super().__init__("System Resources", DiagnosticCategory.SYSTEM)
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        self.disk_threshold = 90.0

    async def run_check(self) -> List[DiagnosticResult]:
        results = []

        # CPU usage check
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > self.cpu_threshold:
            results.append(DiagnosticResult(
                category=self.category,
                level=DiagnosticLevel.WARNING if cpu_percent < 95 else DiagnosticLevel.CRITICAL,
                title="High CPU Usage",
                description=f"CPU usage is {cpu_percent:.1f}%",
                details={"cpu_percent": cpu_percent, "threshold": self.cpu_threshold},
                recommendations=[
                    "Check for high CPU processes",
                    "Consider reducing computational load",
                    "Monitor for infinite loops or blocking operations"
                ]
            ))

        # Memory usage check
        memory = psutil.virtual_memory()
        if memory.percent > self.memory_threshold:
            results.append(DiagnosticResult(
                category=self.category,
                level=DiagnosticLevel.WARNING if memory.percent < 95 else DiagnosticLevel.CRITICAL,
                title="High Memory Usage",
                description=f"Memory usage is {memory.percent:.1f}%",
                details={
                    "memory_percent": memory.percent,
                    "available_gb": memory.available / (1024**3),
                    "threshold": self.memory_threshold
                },
                recommendations=[
                    "Check for memory leaks",
                    "Review large data structures",
                    "Consider implementing memory pooling"
                ]
            ))

        # Disk usage check
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                percent_used = (usage.used / usage.total) * 100
                if percent_used > self.disk_threshold:
                    results.append(DiagnosticResult(
                        category=self.category,
                        level=DiagnosticLevel.WARNING,
                        title="High Disk Usage",
                        description=f"Disk {partition.device} usage is {percent_used:.1f}%",
                        details={
                            "device": partition.device,
                            "percent_used": percent_used,
                            "free_gb": usage.free / (1024**3),
                            "threshold": self.disk_threshold
                        },
                        recommendations=[
                            "Clean up temporary files",
                            "Archive old log files",
                            "Check for large unnecessary files"
                        ]
                    ))
            except PermissionError:
                continue

        return results


class NetworkDiagnosticCheck(DiagnosticCheck):
    """Check network connectivity and performance."""

    def __init__(self):
        super().__init__("Network Connectivity", DiagnosticCategory.NETWORK)
        self.timeout = 5.0

    async def run_check(self) -> List[DiagnosticResult]:
        results = []

        # Check network connections
        connections = psutil.net_connections()
        established_count = sum(1 for conn in connections if conn.status == 'ESTABLISHED')

        # Check for excessive connections
        if established_count > 1000:
            results.append(DiagnosticResult(
                category=self.category,
                level=DiagnosticLevel.WARNING,
                title="High Network Connection Count",
                description=f"Found {established_count} established connections",
                details={"connection_count": established_count},
                recommendations=[
                    "Check for connection leaks",
                    "Implement connection pooling",
                    "Review timeout settings"
                ]
            ))

        # Check network interface statistics
        net_io = psutil.net_io_counters()
        if net_io.errin > 100 or net_io.errout > 100:
            results.append(DiagnosticResult(
                category=self.category,
                level=DiagnosticLevel.WARNING,
                title="Network Errors Detected",
                description=f"Network errors: {net_io.errin} in, {net_io.errout} out",
                details={
                    "errors_in": net_io.errin,
                    "errors_out": net_io.errout,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                },
                recommendations=[
                    "Check network hardware",
                    "Review network configuration",
                    "Monitor for packet loss"
                ]
            ))

        return results


class PerformanceDiagnosticCheck(DiagnosticCheck):
    """Check system performance metrics."""

    def __init__(self):
        super().__init__("Performance Metrics", DiagnosticCategory.PERFORMANCE)
        self.response_time_threshold = 1.0  # seconds
        self.recent_metrics = deque(maxlen=100)

    async def run_check(self) -> List[DiagnosticResult]:
        results = []

        if len(self.recent_metrics) < 10:
            return results

        # Analyze response times
        avg_response_time = sum(self.recent_metrics) / len(self.recent_metrics)
        if avg_response_time > self.response_time_threshold:
            results.append(DiagnosticResult(
                category=self.category,
                level=DiagnosticLevel.WARNING,
                title="Slow Response Times",
                description=f"Average response time: {avg_response_time:.2f}s",
                details={
                    "avg_response_time": avg_response_time,
                    "threshold": self.response_time_threshold,
                    "sample_count": len(self.recent_metrics)
                },
                recommendations=[
                    "Profile application performance",
                    "Check for blocking operations",
                    "Optimize database queries"
                ]
            ))

        return results


class DiagnosticEngine:
    """Main diagnostic engine that coordinates all checks."""

    def __init__(self):
        self.checks: List[DiagnosticCheck] = []
        self.results_history: deque = deque(maxlen=1000)
        self.is_running = False
        self.check_interval = 60  # seconds
        self.logger = logging.getLogger(__name__)

        # Register default checks
        self.register_check(SystemResourceCheck())
        self.register_check(NetworkDiagnosticCheck())
        self.register_check(PerformanceDiagnosticCheck())

    def register_check(self, check: DiagnosticCheck):
        """Register a diagnostic check."""
        self.checks.append(check)
        self.logger.info(f"Registered diagnostic check: {check.name}")

    def unregister_check(self, check_name: str):
        """Unregister a diagnostic check."""
        self.checks = [c for c in self.checks if c.name != check_name]
        self.logger.info(f"Unregistered diagnostic check: {check_name}")

    async def run_all_checks(self) -> List[DiagnosticResult]:
        """Run all enabled diagnostic checks."""
        all_results = []

        for check in self.checks:
            if not check.enabled:
                continue

            try:
                start_time = time.time()
                results = await check.run_check()
                duration = time.time() - start_time

                check.last_run = datetime.now()
                check.run_count += 1

                all_results.extend(results)

                self.logger.debug(
                    f"Check '{check.name}' completed in {duration:.2f}s "
                    f"with {len(results)} results"
                )

            except Exception as e:
                error_result = DiagnosticResult(
                    category=DiagnosticCategory.SYSTEM,
                    level=DiagnosticLevel.ERROR,
                    title=f"Diagnostic Check Failed: {check.name}",
                    description=f"Error running check: {str(e)}",
                    details={
                        "check_name": check.name,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    },
                    recommendations=[
                        "Check diagnostic check implementation",
                        "Review system logs for errors"
                    ]
                )
                all_results.append(error_result)
                self.logger.error(f"Error running check '{check.name}': {e}")

        # Store results in history
        for result in all_results:
            self.results_history.append(result)

        return all_results

    async def run_check_by_name(self, check_name: str) -> List[DiagnosticResult]:
        """Run a specific diagnostic check by name."""
        for check in self.checks:
            if check.name == check_name and check.enabled:
                try:
                    return await check.run_check()
                except Exception as e:
                    self.logger.error(f"Error running check '{check_name}': {e}")
                    return []

        self.logger.warning(f"Check '{check_name}' not found or disabled")
        return []

    def get_system_profile(self) -> SystemProfile:
        """Get comprehensive system profiling data."""
        try:
            # Network I/O
            net_io = psutil.net_io_counters()
            network_io = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }

            # Disk usage
            disk_usage = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.device] = (usage.used / usage.total) * 100
                except PermissionError:
                    continue

            return SystemProfile(
                timestamp=datetime.now(),
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                disk_usage=disk_usage,
                network_io=network_io,
                process_count=len(psutil.pids()),
                thread_count=threading.active_count(),
                open_files=len(psutil.Process().open_files()),
                network_connections=len(psutil.net_connections()),
                system_load=psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0),
                uptime=time.time() - psutil.boot_time()
            )

        except Exception as e:
            self.logger.error(f"Error getting system profile: {e}")
            return SystemProfile(
                timestamp=datetime.now(),
                cpu_usage=0, memory_usage=0, disk_usage={}, network_io={},
                process_count=0, thread_count=0, open_files=0,
                network_connections=0, system_load=(0, 0, 0), uptime=0
            )

    def get_results_by_category(self, category: DiagnosticCategory) -> List[DiagnosticResult]:
        """Get diagnostic results filtered by category."""
        return [r for r in self.results_history if r.category == category]

    def get_results_by_level(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """Get diagnostic results filtered by severity level."""
        return [r for r in self.results_history if r.level == level]

    def get_recent_results(self, minutes: int = 60) -> List[DiagnosticResult]:
        """Get diagnostic results from the last N minutes."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [r for r in self.results_history if r.timestamp >= cutoff]

    def export_results(self, file_path: Path, format: str = "json"):
        """Export diagnostic results to file."""
        try:
            if format.lower() == "json":
                results_data = []
                for result in self.results_history:
                    results_data.append({
                        "category": result.category.value,
                        "level": result.level.value,
                        "title": result.title,
                        "description": result.description,
                        "timestamp": result.timestamp.isoformat(),
                        "details": result.details,
                        "recommendations": result.recommendations,
                        "affected_components": list(result.affected_components)
                    })

                with open(file_path, 'w') as f:
                    json.dump(results_data, f, indent=2)

            self.logger.info(f"Exported {len(self.results_history)} results to {file_path}")

        except Exception as e:
            self.logger.error(f"Error exporting results: {e}")

    async def start_continuous_monitoring(self):
        """Start continuous diagnostic monitoring."""
        self.is_running = True
        self.logger.info("Starting continuous diagnostic monitoring")

        while self.is_running:
            try:
                results = await self.run_all_checks()

                # Log critical and error results
                for result in results:
                    if result.level in [DiagnosticLevel.CRITICAL, DiagnosticLevel.ERROR]:
                        self.logger.warning(
                            f"Diagnostic issue: {result.title} - {result.description}"
                        )

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(self.check_interval)

    def stop_continuous_monitoring(self):
        """Stop continuous diagnostic monitoring."""
        self.is_running = False
        self.logger.info("Stopped continuous diagnostic monitoring")


class TroubleshootingAssistant:
    """AI-powered troubleshooting assistant."""

    def __init__(self, diagnostic_engine: DiagnosticEngine):
        self.engine = diagnostic_engine
        self.knowledge_base = self._build_knowledge_base()
        self.logger = logging.getLogger(__name__)

    def _build_knowledge_base(self) -> Dict[str, Dict[str, Any]]:
        """Build troubleshooting knowledge base."""
        return {
            "high_cpu": {
                "symptoms": ["CPU usage > 80%", "System slowdown", "High load average"],
                "causes": [
                    "Infinite loops in code",
                    "Inefficient algorithms",
                    "Blocking I/O operations",
                    "Too many concurrent processes"
                ],
                "solutions": [
                    "Profile CPU usage by process",
                    "Optimize algorithms and data structures",
                    "Implement async I/O where possible",
                    "Add process throttling"
                ]
            },
            "high_memory": {
                "symptoms": ["Memory usage > 85%", "OOM errors", "Swap usage"],
                "causes": [
                    "Memory leaks",
                    "Large data structures",
                    "Inefficient caching",
                    "Too many objects in memory"
                ],
                "solutions": [
                    "Use memory profilers",
                    "Implement object pooling",
                    "Add garbage collection tuning",
                    "Review caching strategies"
                ]
            },
            "network_errors": {
                "symptoms": ["Connection timeouts", "Packet loss", "High latency"],
                "causes": [
                    "Network congestion",
                    "Hardware issues",
                    "Firewall blocking",
                    "DNS problems"
                ],
                "solutions": [
                    "Check network hardware",
                    "Test with different DNS servers",
                    "Review firewall rules",
                    "Monitor bandwidth usage"
                ]
            }
        }

    def analyze_results(self, results: List[DiagnosticResult]) -> Dict[str, Any]:
        """Analyze diagnostic results and provide recommendations."""
        analysis = {
            "summary": self._generate_summary(results),
            "priority_issues": self._identify_priority_issues(results),
            "recommendations": self._generate_recommendations(results),
            "root_cause_analysis": self._perform_root_cause_analysis(results)
        }

        return analysis

    def _generate_summary(self, results: List[DiagnosticResult]) -> Dict[str, int]:
        """Generate summary of diagnostic results."""
        summary = defaultdict(int)

        for result in results:
            summary[result.level.value] += 1
            summary[f"{result.category.value}_issues"] += 1

        summary["total_issues"] = len(results)
        return dict(summary)

    def _identify_priority_issues(self, results: List[DiagnosticResult]) -> List[DiagnosticResult]:
        """Identify highest priority issues."""
        # Sort by severity level and impact
        priority_order = {
            DiagnosticLevel.CRITICAL: 4,
            DiagnosticLevel.ERROR: 3,
            DiagnosticLevel.WARNING: 2,
            DiagnosticLevel.INFO: 1
        }

        sorted_results = sorted(
            results,
            key=lambda x: priority_order.get(x.level, 0),
            reverse=True
        )

        return sorted_results[:5]  # Top 5 priority issues

    def _generate_recommendations(self, results: List[DiagnosticResult]) -> List[str]:
        """Generate comprehensive recommendations."""
        all_recommendations = []

        for result in results:
            all_recommendations.extend(result.recommendations)

        # Remove duplicates while preserving order
        unique_recommendations = []
        seen = set()
        for rec in all_recommendations:
            if rec not in seen:
                unique_recommendations.append(rec)
                seen.add(rec)

        return unique_recommendations[:10]  # Top 10 recommendations

    def _perform_root_cause_analysis(self, results: List[DiagnosticResult]) -> Dict[str, Any]:
        """Perform root cause analysis on diagnostic results."""
        causes = defaultdict(list)

        for result in results:
            # Map result to potential root causes
            if "CPU" in result.title:
                causes["performance"].append(result)
            elif "Memory" in result.title:
                causes["memory_management"].append(result)
            elif "Network" in result.title:
                causes["connectivity"].append(result)
            elif "Disk" in result.title:
                causes["storage"].append(result)
            else:
                causes["other"].append(result)

        analysis = {}
        for category, category_results in causes.items():
            if category_results:
                analysis[category] = {
                    "issue_count": len(category_results),
                    "severity": max(r.level.value for r in category_results),
                    "potential_causes": self._get_potential_causes(category, category_results)
                }

        return analysis

    def _get_potential_causes(self, category: str, results: List[DiagnosticResult]) -> List[str]:
        """Get potential root causes for a category of issues."""
        if category == "performance":
            return self.knowledge_base.get("high_cpu", {}).get("causes", [])
        elif category == "memory_management":
            return self.knowledge_base.get("high_memory", {}).get("causes", [])
        elif category == "connectivity":
            return self.knowledge_base.get("network_errors", {}).get("causes", [])
        else:
            return ["Unknown root cause - requires manual investigation"]


# Global diagnostic engine instance
diagnostic_engine = DiagnosticEngine()
troubleshooting_assistant = TroubleshootingAssistant(diagnostic_engine)


async def run_comprehensive_diagnostics() -> Dict[str, Any]:
    """Run comprehensive system diagnostics."""
    results = await diagnostic_engine.run_all_checks()
    analysis = troubleshooting_assistant.analyze_results(results)
    profile = diagnostic_engine.get_system_profile()

    return {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "analysis": analysis,
        "system_profile": profile,
        "summary": {
            "total_checks": len(diagnostic_engine.checks),
            "total_issues": len(results),
            "critical_issues": len([r for r in results if r.level == DiagnosticLevel.CRITICAL]),
            "error_issues": len([r for r in results if r.level == DiagnosticLevel.ERROR]),
            "warning_issues": len([r for r in results if r.level == DiagnosticLevel.WARNING])
        }
    }


def configure_diagnostics(
    cpu_threshold: float = 80.0,
    memory_threshold: float = 85.0,
    disk_threshold: float = 90.0,
    check_interval: int = 60
):
    """Configure diagnostic thresholds and parameters."""
    for check in diagnostic_engine.checks:
        if isinstance(check, SystemResourceCheck):
            check.cpu_threshold = cpu_threshold
            check.memory_threshold = memory_threshold
            check.disk_threshold = disk_threshold

    diagnostic_engine.check_interval = check_interval