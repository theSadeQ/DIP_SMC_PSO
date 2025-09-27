#==========================================================================================\\\
#================ validation/production_monitoring_framework.py =========================\\\
#==========================================================================================\\\

"""
Production Monitoring Framework for PSO & Dynamics.

Comprehensive monitoring system for production deployment of the DIP SMC PSO
optimization system. Provides health checks, performance monitoring, and
automated regression detection.
"""

import json
import time
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from pathlib import Path
import numpy as np

@dataclass
class HealthStatus:
    """System health status container."""
    component: str
    status: str  # "healthy", "degraded", "failed"
    score: float  # 0.0 to 100.0
    message: str
    timestamp: float
    details: Optional[Dict[str, Any]] = None

@dataclass
class PerformanceMetrics:
    """Performance metrics container."""
    operation: str
    execution_time: float
    memory_usage: Optional[float]
    success: bool
    timestamp: float
    details: Optional[Dict[str, Any]] = None

class ProductionMonitor:
    """
    Production monitoring framework for PSO and dynamics systems.

    Features:
    - Real-time health monitoring
    - Performance metrics collection
    - Automated alerting
    - Regression detection
    - Dashboard data export
    """

    def __init__(self, output_dir: str = "monitoring"):
        """Initialize production monitor."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Health tracking
        self.health_history: List[HealthStatus] = []
        self.performance_history: List[PerformanceMetrics] = []

        # Thresholds
        self.health_thresholds = {
            "dynamics_models": 80.0,
            "pso_optimization": 85.0,
            "controller_factory": 90.0,
            "overall_system": 85.0
        }

        self.performance_thresholds = {
            "optimization_time": 5.0,  # seconds
            "dynamics_computation": 0.01,  # seconds
            "controller_creation": 0.1  # seconds
        }

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup monitoring logging."""
        log_file = self.output_dir / "production_monitoring.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("ProductionMonitor")

    def check_dynamics_health(self) -> HealthStatus:
        """Check health of dynamics models."""
        try:
            # Import and test dynamics models
            from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
            from src.plant.models.full.dynamics import FullDIPDynamics
            from src.plant.models.lowrank.dynamics import LowRankDIPDynamics

            models = [
                ("SimplifiedDIPDynamics", SimplifiedDIPDynamics),
                ("FullDIPDynamics", FullDIPDynamics),
                ("LowRankDIPDynamics", LowRankDIPDynamics)
            ]

            working_models = 0
            total_models = len(models)
            model_details = {}

            for name, model_class in models:
                try:
                    # Test instantiation and basic computation
                    dynamics = model_class({})
                    test_state = np.array([0.1, 0.05, -0.03, 0.0, 0.0, 0.0])
                    test_control = np.array([10.0])

                    result = dynamics.compute_dynamics(test_state, test_control)
                    if result.success:
                        working_models += 1
                        model_details[name] = {
                            "status": "healthy",
                            "state_derivative_norm": float(np.linalg.norm(result.state_derivative))
                        }
                    else:
                        model_details[name] = {"status": "failed", "error": str(result.info)}

                except Exception as e:
                    model_details[name] = {"status": "failed", "error": str(e)}

            score = (working_models / total_models) * 100.0

            if score >= 100.0:
                status = "healthy"
                message = f"All {total_models} dynamics models operational"
            elif score >= 66.7:
                status = "degraded"
                message = f"{working_models}/{total_models} dynamics models operational"
            else:
                status = "failed"
                message = f"Only {working_models}/{total_models} dynamics models operational"

            return HealthStatus(
                component="dynamics_models",
                status=status,
                score=score,
                message=message,
                timestamp=time.time(),
                details=model_details
            )

        except Exception as e:
            return HealthStatus(
                component="dynamics_models",
                status="failed",
                score=0.0,
                message=f"Dynamics health check failed: {e}",
                timestamp=time.time()
            )

    def check_pso_health(self) -> HealthStatus:
        """Check health of PSO optimization system."""
        try:
            from src.config import load_config
            from src.controllers.factory import create_controller
            from src.optimizer.pso_optimizer import PSOTuner

            # Load configuration
            config = load_config('config.yaml')

            # Test controller factory
            def controller_factory(gains):
                return create_controller('classical_smc', config=config, gains=gains)
            controller_factory.n_gains = 6

            # Test PSO tuner initialization
            pso_tuner = PSOTuner(
                controller_factory=controller_factory,
                config=config,
                seed=42
            )

            # Test small optimization
            start_time = time.time()
            result = pso_tuner.optimise(iters_override=2, n_particles_override=3)
            execution_time = time.time() - start_time

            # Validate result
            is_valid = (
                'best_cost' in result and
                'best_pos' in result and
                isinstance(result['best_pos'], np.ndarray) and
                len(result['best_pos']) == 6 and
                np.all(np.isfinite(result['best_pos']))
            )

            if is_valid:
                score = 100.0
                status = "healthy"
                message = f"PSO optimization operational (execution time: {execution_time:.2f}s)"
            else:
                score = 0.0
                status = "failed"
                message = "PSO optimization result validation failed"

            details = {
                "execution_time": execution_time,
                "best_cost": float(result.get('best_cost', np.inf)),
                "best_position": result.get('best_pos', []).tolist() if isinstance(result.get('best_pos'), np.ndarray) else [],
                "result_valid": is_valid
            }

            return HealthStatus(
                component="pso_optimization",
                status=status,
                score=score,
                message=message,
                timestamp=time.time(),
                details=details
            )

        except Exception as e:
            return HealthStatus(
                component="pso_optimization",
                status="failed",
                score=0.0,
                message=f"PSO health check failed: {e}",
                timestamp=time.time()
            )

    def check_controller_factory_health(self) -> HealthStatus:
        """Check health of controller factory system."""
        try:
            from src.config import load_config
            from src.controllers.factory import create_controller

            config = load_config('config.yaml')

            # Test multiple controller types
            controller_types = ['classical_smc', 'sta_smc', 'adaptive_smc']
            working_controllers = 0
            controller_details = {}

            for ctrl_type in controller_types:
                try:
                    test_gains = [5.0, 5.0, 5.0, 0.5, 0.5, 0.5]
                    controller = create_controller(ctrl_type, config=config, gains=test_gains)

                    # Validate controller has required methods
                    has_compute = hasattr(controller, 'compute_control')

                    if has_compute:
                        working_controllers += 1
                        controller_details[ctrl_type] = {"status": "healthy"}
                    else:
                        controller_details[ctrl_type] = {"status": "failed", "reason": "missing compute_control method"}

                except Exception as e:
                    controller_details[ctrl_type] = {"status": "failed", "error": str(e)}

            score = (working_controllers / len(controller_types)) * 100.0

            if score >= 100.0:
                status = "healthy"
                message = f"All {len(controller_types)} controller types operational"
            elif score >= 75.0:
                status = "degraded"
                message = f"{working_controllers}/{len(controller_types)} controller types operational"
            else:
                status = "failed"
                message = f"Only {working_controllers}/{len(controller_types)} controller types operational"

            return HealthStatus(
                component="controller_factory",
                status=status,
                score=score,
                message=message,
                timestamp=time.time(),
                details=controller_details
            )

        except Exception as e:
            return HealthStatus(
                component="controller_factory",
                status="failed",
                score=0.0,
                message=f"Controller factory health check failed: {e}",
                timestamp=time.time()
            )

    def run_comprehensive_health_check(self) -> Dict[str, HealthStatus]:
        """Run comprehensive health check of all components."""
        self.logger.info("Starting comprehensive health check...")

        health_checks = {
            "dynamics_models": self.check_dynamics_health(),
            "pso_optimization": self.check_pso_health(),
            "controller_factory": self.check_controller_factory_health()
        }

        # Calculate overall system health
        total_score = sum(check.score for check in health_checks.values())
        avg_score = total_score / len(health_checks) if health_checks else 0.0

        # Determine overall status
        if avg_score >= 90.0:
            overall_status = "healthy"
        elif avg_score >= 70.0:
            overall_status = "degraded"
        else:
            overall_status = "failed"

        overall_health = HealthStatus(
            component="overall_system",
            status=overall_status,
            score=avg_score,
            message=f"System health: {avg_score:.1f}% ({overall_status})",
            timestamp=time.time(),
            details={name: check.score for name, check in health_checks.items()}
        )

        health_checks["overall_system"] = overall_health

        # Store health history
        for health_status in health_checks.values():
            self.health_history.append(health_status)

        # Save health report
        self._save_health_report(health_checks)

        self.logger.info(f"Health check complete. Overall score: {avg_score:.1f}%")

        return health_checks

    def record_performance_metric(self, operation: str, execution_time: float,
                                 success: bool = True, details: Dict[str, Any] = None):
        """Record a performance metric."""
        metric = PerformanceMetrics(
            operation=operation,
            execution_time=execution_time,
            memory_usage=None,  # Could be enhanced with psutil
            success=success,
            timestamp=time.time(),
            details=details
        )

        self.performance_history.append(metric)

        # Check performance thresholds
        threshold = self.performance_thresholds.get(operation)
        if threshold and execution_time > threshold:
            self.logger.warning(
                f"Performance alert: {operation} took {execution_time:.2f}s "
                f"(threshold: {threshold}s)"
            )

    def get_health_dashboard_data(self) -> Dict[str, Any]:
        """Get data for health monitoring dashboard."""
        recent_health = {}
        for component in ["dynamics_models", "pso_optimization", "controller_factory", "overall_system"]:
            component_history = [h for h in self.health_history if h.component == component]
            if component_history:
                recent_health[component] = {
                    "current_score": component_history[-1].score,
                    "current_status": component_history[-1].status,
                    "last_check": component_history[-1].timestamp,
                    "trend": self._calculate_trend(component_history)
                }

        recent_performance = {}
        for operation in self.performance_thresholds.keys():
            operation_history = [p for p in self.performance_history if p.operation == operation]
            if operation_history:
                recent_times = [p.execution_time for p in operation_history[-10:]]  # Last 10
                recent_performance[operation] = {
                    "avg_time": np.mean(recent_times),
                    "max_time": np.max(recent_times),
                    "threshold": self.performance_thresholds[operation],
                    "within_threshold": np.mean(recent_times) <= self.performance_thresholds[operation]
                }

        return {
            "health_status": recent_health,
            "performance_metrics": recent_performance,
            "total_health_checks": len(self.health_history),
            "total_performance_records": len(self.performance_history),
            "last_update": time.time()
        }

    def _calculate_trend(self, history: List[HealthStatus]) -> str:
        """Calculate trend from health history."""
        if len(history) < 2:
            return "stable"

        recent_scores = [h.score for h in history[-5:]]  # Last 5 checks
        if len(recent_scores) < 2:
            return "stable"

        trend_slope = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]

        if trend_slope > 5:
            return "improving"
        elif trend_slope < -5:
            return "degrading"
        else:
            return "stable"

    def _save_health_report(self, health_checks: Dict[str, HealthStatus]):
        """Save health report to file."""
        report = {
            "timestamp": time.time(),
            "health_checks": {name: asdict(status) for name, status in health_checks.items()}
        }

        report_file = self.output_dir / "latest_health_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

    def export_monitoring_data(self) -> str:
        """Export all monitoring data for external systems."""
        export_data = {
            "health_history": [asdict(h) for h in self.health_history],
            "performance_history": [asdict(p) for p in self.performance_history],
            "dashboard_data": self.get_health_dashboard_data(),
            "export_timestamp": time.time()
        }

        export_file = self.output_dir / f"monitoring_export_{int(time.time())}.json"
        with open(export_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        return str(export_file)

def main():
    """Run production monitoring check."""
    monitor = ProductionMonitor()

    print("="*80)
    print("PRODUCTION MONITORING HEALTH CHECK")
    print("="*80)

    # Run comprehensive health check
    health_results = monitor.run_comprehensive_health_check()

    # Print results
    for component, status in health_results.items():
        status_icon = {
            "healthy": "[HEALTHY]",
            "degraded": "[DEGRADED]",
            "failed": "[FAILED]"
        }.get(status.status, "[UNKNOWN]")

        print(f"\n{status_icon} {component.upper()}: {status.score:.1f}%")
        print(f"   Status: {status.status}")
        print(f"   Message: {status.message}")

    # Overall assessment
    overall = health_results["overall_system"]
    print(f"\n{'='*80}")
    print(f"OVERALL SYSTEM HEALTH: {overall.score:.1f}% ({overall.status.upper()})")
    print(f"{'='*80}")

    # Export data
    export_file = monitor.export_monitoring_data()
    print(f"\nMonitoring data exported to: {export_file}")

    return overall.score >= 70.0  # Return True if system is healthy enough

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)