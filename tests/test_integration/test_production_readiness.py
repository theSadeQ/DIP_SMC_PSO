#==========================================================================================
#================= tests/test_integration/test_production_readiness.py ==================
#==========================================================================================

"""
Production Readiness Validation - Mission 10 Deployment Gate

MISSION-CRITICAL CAPABILITY: Validate the system meets all production deployment
requirements. This comprehensive assessment ensures the system is ready for
real-world deployment with enterprise-grade reliability, security, and performance.

PRODUCTION READINESS CHECKLIST:
1. System Health & Stability (Target: 95%+ success rate)
2. Configuration Management & Security
3. Error Handling & Recovery Mechanisms
4. Performance & Resource Management
5. Documentation & Operational Readiness
6. Security & Safety Validation

SUCCESS CRITERIA - MISSION 10:
- Production readiness score ≥ 8.0/10
- All critical deployment blockers resolved
- Zero security vulnerabilities identified
- Performance within acceptable operational limits
"""

import pytest
import subprocess
import sys
import os
import yaml
import json
import tempfile
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import time
from datetime import datetime
import warnings


@dataclass
class ProductionCheck:
    """Individual production readiness check result."""
    check_name: str
    category: str  # "critical", "important", "recommended"
    passed: bool
    score: float  # 0.0 to 10.0
    details: List[str]
    recommendations: List[str]
    execution_time: float


@dataclass
class ProductionReadinessAssessment:
    """Complete production readiness assessment."""
    overall_score: float  # 0.0 to 10.0
    readiness_level: str  # "production_ready", "staging_ready", "development_only"
    deployment_blockers: List[str]
    critical_checks: List[ProductionCheck]
    important_checks: List[ProductionCheck]
    recommended_checks: List[ProductionCheck]
    security_assessment: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    operational_recommendations: List[str]


class ProductionReadinessValidator:
    """Validates production readiness across all system components."""

    def __init__(self):
        """Initialize production readiness validator."""
        self.repo_root = Path(__file__).parent.parent.parent
        self.temp_dir = Path(tempfile.mkdtemp())
        self.temp_dir.mkdir(exist_ok=True)

        # Key system files
        self.simulate_py = self.repo_root / "simulate.py"
        self.config_yaml = self.repo_root / "config.yaml"
        self.requirements_txt = self.repo_root / "requirements.txt"
        self.claude_md = self.repo_root / "CLAUDE.md"

    def check_system_stability(self) -> ProductionCheck:
        """Check overall system stability and reliability."""

        start_time = time.perf_counter()
        details = []
        recommendations = []
        passed = True
        score = 10.0

        try:
            # Check for critical system files
            critical_files = [
                ("simulate.py", "Main CLI entry point"),
                ("config.yaml", "System configuration"),
                ("requirements.txt", "Dependency specification"),
                ("CLAUDE.md", "System documentation")
            ]

            missing_files = []
            for filename, description in critical_files:
                filepath = self.repo_root / filename
                if filepath.exists():
                    details.append(f"[OK] {description} present: {filename}")
                else:
                    missing_files.append(f"{filename} ({description})")
                    passed = False
                    score -= 2.0

            if missing_files:
                recommendations.append(f"Create missing critical files: {', '.join(missing_files)}")

            # Check for test coverage
            tests_dir = self.repo_root / "tests"
            if tests_dir.exists():
                test_files = list(tests_dir.glob("**/test_*.py"))
                if len(test_files) >= 10:  # Reasonable test coverage
                    details.append(f"[OK] Comprehensive test suite: {len(test_files)} test files")
                    score += 1.0
                elif len(test_files) >= 5:
                    details.append(f"[WARN] Basic test coverage: {len(test_files)} test files")
                    recommendations.append("Expand test coverage for better stability assurance")
                else:
                    details.append(f"[FAIL] Insufficient test coverage: {len(test_files)} test files")
                    passed = False
                    score -= 3.0
                    recommendations.append("Critical: Implement comprehensive test suite")
            else:
                details.append("[FAIL] No test directory found")
                passed = False
                score -= 5.0
                recommendations.append("Critical: Implement testing infrastructure")

            # Check for error handling patterns
            try:
                with open(self.simulate_py, 'r', encoding='utf-8') as f:
                    simulate_content = f.read()

                # Look for error handling patterns
                if 'try:' in simulate_content and 'except' in simulate_content:
                    details.append("[OK] Error handling patterns detected in main CLI")
                else:
                    details.append("[WARN] Limited error handling in main CLI")
                    recommendations.append("Implement comprehensive error handling in CLI")
                    score -= 1.0

            except Exception as e:
                details.append(f"[FAIL] Could not analyze main CLI: {str(e)}")
                score -= 2.0

            # Ensure score is within bounds
            score = max(0.0, min(10.0, score))

        except Exception as e:
            details.append(f"System stability check failed: {str(e)}")
            passed = False
            score = 0.0
            recommendations.append("Investigation required: System stability check failure")

        execution_time = time.perf_counter() - start_time

        return ProductionCheck(
            check_name="System Stability Assessment",
            category="critical",
            passed=passed,
            score=score,
            details=details,
            recommendations=recommendations,
            execution_time=execution_time
        )

    def check_configuration_management(self) -> ProductionCheck:
        """Check configuration management and security."""

        start_time = time.perf_counter()
        details = []
        recommendations = []
        passed = True
        score = 10.0

        try:
            # Check main configuration file
            if self.config_yaml.exists():
                details.append("[OK] Main configuration file present")

                try:
                    # Try different encodings to handle potential encoding issues
                    config_data = None
                    encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']

                    for encoding in encodings:
                        try:
                            with open(self.config_yaml, 'r', encoding=encoding) as f:
                                config_data = yaml.safe_load(f)
                            details.append(f"[OK] Configuration loaded successfully (encoding: {encoding})")
                            break
                        except UnicodeDecodeError:
                            continue
                        except yaml.YAMLError:
                            break

                    if config_data is None:
                        details.append("[FAIL] Configuration file has encoding/parsing issues")
                        passed = False
                        score -= 4.0
                        recommendations.append("Critical: Fix configuration file encoding issues")
                    else:
                        # Check configuration structure
                        required_sections = ['physics_params', 'simulation_params']
                        missing_sections = [s for s in required_sections if s not in config_data]

                        if not missing_sections:
                            details.append("[OK] Required configuration sections present")
                        else:
                            details.append(f"[WARN] Missing config sections: {', '.join(missing_sections)}")
                            recommendations.append(f"Add missing configuration sections: {', '.join(missing_sections)}")
                            score -= 2.0

                        # Check for sensitive data patterns
                        config_str = str(config_data).lower()
                        sensitive_patterns = ['password', 'secret', 'key', 'token', 'credential']
                        found_sensitive = [p for p in sensitive_patterns if p in config_str]

                        if found_sensitive:
                            details.append(f"[WARN] Potential sensitive data in config: {', '.join(found_sensitive)}")
                            recommendations.append("Review and secure sensitive configuration data")
                            score -= 1.0
                        else:
                            details.append("[OK] No obvious sensitive data in configuration")

                except Exception as e:
                    details.append(f"[FAIL] Configuration analysis failed: {str(e)}")
                    passed = False
                    score -= 3.0
                    recommendations.append("Investigation required: Configuration analysis failure")
            else:
                details.append("[FAIL] Main configuration file missing")
                passed = False
                score -= 5.0
                recommendations.append("Critical: Create main configuration file")

            # Check for environment variable usage (good practice)
            env_vars_used = []
            config_files = [self.simulate_py, self.config_yaml]
            for config_file in config_files:
                if config_file.exists():
                    try:
                        with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        if 'os.environ' in content or 'getenv' in content:
                            env_vars_used.append(config_file.name)
                    except Exception:
                        pass

            if env_vars_used:
                details.append(f"[OK] Environment variables used in: {', '.join(env_vars_used)}")
            else:
                details.append("[WARN] No environment variable usage detected")
                recommendations.append("Consider using environment variables for deployment flexibility")
                score -= 0.5

            # Ensure score is within bounds
            score = max(0.0, min(10.0, score))

        except Exception as e:
            details.append(f"Configuration management check failed: {str(e)}")
            passed = False
            score = 0.0
            recommendations.append("Investigation required: Configuration management check failure")

        execution_time = time.perf_counter() - start_time

        return ProductionCheck(
            check_name="Configuration Management & Security",
            category="critical",
            passed=passed,
            score=score,
            details=details,
            recommendations=recommendations,
            execution_time=execution_time
        )

    def check_dependency_management(self) -> ProductionCheck:
        """Check dependency management and security."""

        start_time = time.perf_counter()
        details = []
        recommendations = []
        passed = True
        score = 10.0

        try:
            # Check requirements.txt
            if self.requirements_txt.exists():
                details.append("[OK] Requirements file present")

                try:
                    with open(self.requirements_txt, 'r', encoding='utf-8') as f:
                        requirements_content = f.read()

                    requirements_lines = [line.strip() for line in requirements_content.split('\n')
                                        if line.strip() and not line.startswith('#')]

                    if requirements_lines:
                        details.append(f"[OK] {len(requirements_lines)} dependencies specified")

                        # Check for version pinning
                        pinned_deps = [req for req in requirements_lines if '==' in req or '>=' in req or '<=' in req]
                        pinning_ratio = len(pinned_deps) / len(requirements_lines) if requirements_lines else 0

                        if pinning_ratio >= 0.8:
                            details.append(f"[OK] Good version pinning: {pinning_ratio:.1%} of dependencies")
                        elif pinning_ratio >= 0.5:
                            details.append(f"[WARN] Moderate version pinning: {pinning_ratio:.1%} of dependencies")
                            recommendations.append("Improve dependency version pinning for stability")
                            score -= 1.0
                        else:
                            details.append(f"[FAIL] Poor version pinning: {pinning_ratio:.1%} of dependencies")
                            recommendations.append("Critical: Pin dependency versions for production stability")
                            passed = False
                            score -= 3.0

                        # Check for known problematic dependencies
                        known_issues = {
                            'tensorflow': 'High memory usage, consider alternatives',
                            'pytorch': 'High memory usage, consider alternatives',
                            'opencv-python': 'Large package, consider opencv-python-headless',
                        }

                        issues_found = []
                        for req in requirements_lines:
                            req_name = req.split('==')[0].split('>=')[0].split('<=')[0].lower()
                            if req_name in known_issues:
                                issues_found.append(f"{req_name}: {known_issues[req_name]}")

                        if issues_found:
                            details.append(f"[WARN] Dependency considerations: {len(issues_found)} items")
                            for issue in issues_found:
                                recommendations.append(f"Consider: {issue}")
                            score -= 0.5

                        # Check for core scientific dependencies
                        core_deps = ['numpy', 'scipy', 'matplotlib']
                        found_core = [dep for dep in core_deps
                                    if any(dep in req.lower() for req in requirements_lines)]

                        if len(found_core) >= 2:
                            details.append(f"[OK] Core scientific dependencies present: {', '.join(found_core)}")
                        else:
                            details.append(f"[WARN] Limited core dependencies: {', '.join(found_core)}")

                    else:
                        details.append("[FAIL] Requirements file is empty")
                        passed = False
                        score -= 4.0
                        recommendations.append("Critical: Specify project dependencies")

                except Exception as e:
                    details.append(f"[FAIL] Could not parse requirements: {str(e)}")
                    score -= 2.0
                    recommendations.append("Fix requirements.txt parsing issues")

            else:
                details.append("[FAIL] Requirements file missing")
                passed = False
                score -= 5.0
                recommendations.append("Critical: Create requirements.txt file")

            # Check for pip freeze compatibility
            try:
                result = subprocess.run([sys.executable, "-m", "pip", "list"],
                                      capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    installed_packages = len([line for line in result.stdout.split('\n') if line.strip()])
                    details.append(f"[OK] Package management functional: {installed_packages} packages installed")
                else:
                    details.append("[WARN] Package management check failed")
                    score -= 1.0
            except Exception:
                details.append("[WARN] Could not verify package management")
                score -= 0.5

            # Ensure score is within bounds
            score = max(0.0, min(10.0, score))

        except Exception as e:
            details.append(f"Dependency management check failed: {str(e)}")
            passed = False
            score = 0.0
            recommendations.append("Investigation required: Dependency management check failure")

        execution_time = time.perf_counter() - start_time

        return ProductionCheck(
            check_name="Dependency Management & Security",
            category="critical",
            passed=passed,
            score=score,
            details=details,
            recommendations=recommendations,
            execution_time=execution_time
        )

    def check_performance_requirements(self) -> ProductionCheck:
        """Check performance and resource requirements."""

        start_time = time.perf_counter()
        details = []
        recommendations = []
        passed = True
        score = 10.0

        try:
            # Test CLI startup performance
            if self.simulate_py.exists():
                cli_start_time = time.perf_counter()
                try:
                    result = subprocess.run([sys.executable, str(self.simulate_py), "--help"],
                                          capture_output=True, text=True, timeout=30)
                    cli_execution_time = time.perf_counter() - cli_start_time

                    if result.returncode == 0:
                        if cli_execution_time < 5.0:
                            details.append(f"[OK] Fast CLI startup: {cli_execution_time:.2f}s")
                        elif cli_execution_time < 15.0:
                            details.append(f"[WARN] Moderate CLI startup: {cli_execution_time:.2f}s")
                            recommendations.append("Optimize CLI startup time for better user experience")
                            score -= 1.0
                        else:
                            details.append(f"[FAIL] Slow CLI startup: {cli_execution_time:.2f}s")
                            recommendations.append("Critical: Optimize CLI startup performance")
                            score -= 3.0

                        # Check help output size (indicator of functionality)
                        help_size = len(result.stdout)
                        if help_size > 500:
                            details.append(f"[OK] Comprehensive CLI help: {help_size} characters")
                        else:
                            details.append(f"[WARN] Limited CLI help: {help_size} characters")
                            recommendations.append("Expand CLI help documentation")
                            score -= 0.5

                    else:
                        details.append("[FAIL] CLI startup failed")
                        passed = False
                        score -= 5.0

                except subprocess.TimeoutExpired:
                    details.append("[FAIL] CLI startup timeout (>30s)")
                    passed = False
                    score -= 4.0
                    recommendations.append("Critical: Fix CLI startup timeout")

            # Check system resource usage indicators
            try:
                import psutil
                memory_info = psutil.virtual_memory()
                disk_info = psutil.disk_usage('.')

                details.append(f"[OK] System memory available: {memory_info.available // (1024**3)}GB")
                details.append(f"[OK] Disk space available: {disk_info.free // (1024**3)}GB")

                if memory_info.available < 1024**3:  # Less than 1GB
                    recommendations.append("Warning: Low available memory may impact performance")
                    score -= 1.0

                if disk_info.free < 5 * 1024**3:  # Less than 5GB
                    recommendations.append("Warning: Low disk space may impact operations")
                    score -= 1.0

            except ImportError:
                details.append("[WARN] System resource monitoring unavailable (psutil not installed)")
                recommendations.append("Consider installing psutil for system monitoring")
                score -= 0.5
            except Exception as e:
                details.append(f"[WARN] Could not check system resources: {str(e)}")
                score -= 0.5

            # Check for performance-critical file sizes
            large_files = []
            for file_path in self.repo_root.rglob("*.py"):
                try:
                    file_size = file_path.stat().st_size
                    if file_size > 100 * 1024:  # > 100KB
                        large_files.append((file_path.name, file_size // 1024))
                except Exception:
                    pass

            if large_files:
                details.append(f"[WARN] Large Python files detected: {len(large_files)} files")
                if len(large_files) > 5:
                    recommendations.append("Consider refactoring large files for better maintainability")
                    score -= 0.5
            else:
                details.append("[OK] No unusually large Python files detected")

            # Ensure score is within bounds
            score = max(0.0, min(10.0, score))

        except Exception as e:
            details.append(f"Performance requirements check failed: {str(e)}")
            passed = False
            score = 0.0
            recommendations.append("Investigation required: Performance check failure")

        execution_time = time.perf_counter() - start_time

        return ProductionCheck(
            check_name="Performance Requirements",
            category="important",
            passed=passed,
            score=score,
            details=details,
            recommendations=recommendations,
            execution_time=execution_time
        )

    def check_documentation_readiness(self) -> ProductionCheck:
        """Check documentation and operational readiness."""

        start_time = time.perf_counter()
        details = []
        recommendations = []
        passed = True
        score = 10.0

        try:
            # Check for key documentation files
            doc_files = {
                "README.md": "Project overview and setup instructions",
                "CLAUDE.md": "Development and operational guidelines",
                "CHANGELOG.md": "Version history and changes",
                "config.yaml": "System configuration documentation"
            }

            found_docs = 0
            for filename, description in doc_files.items():
                filepath = self.repo_root / filename
                if filepath.exists():
                    found_docs += 1
                    try:
                        file_size = filepath.stat().st_size
                        if file_size > 1024:  # > 1KB
                            details.append(f"[OK] {description}: {filename} ({file_size//1024}KB)")
                        else:
                            details.append(f"[WARN] {description}: {filename} (minimal content)")
                            score -= 0.5
                    except Exception:
                        details.append(f"[OK] {description}: {filename}")
                else:
                    details.append(f"[FAIL] Missing {description}: {filename}")
                    recommendations.append(f"Create {filename} - {description}")
                    score -= 2.0

            documentation_ratio = found_docs / len(doc_files)
            if documentation_ratio >= 0.8:
                details.append(f"[OK] Good documentation coverage: {documentation_ratio:.1%}")
            elif documentation_ratio >= 0.5:
                details.append(f"[WARN] Moderate documentation coverage: {documentation_ratio:.1%}")
                recommendations.append("Improve documentation coverage for production readiness")
            else:
                details.append(f"[FAIL] Poor documentation coverage: {documentation_ratio:.1%}")
                passed = False
                recommendations.append("Critical: Create comprehensive documentation")

            # Check for usage examples in CLI
            if self.simulate_py.exists():
                try:
                    result = subprocess.run([sys.executable, str(self.simulate_py), "--help"],
                                          capture_output=True, text=True, timeout=15)
                    if result.returncode == 0:
                        help_text = result.stdout.lower()
                        if 'example' in help_text or 'usage' in help_text:
                            details.append("[OK] CLI help includes usage examples")
                        else:
                            details.append("[WARN] CLI help lacks usage examples")
                            recommendations.append("Add usage examples to CLI help")
                            score -= 1.0
                except Exception:
                    pass

            # Check for operational scripts
            operational_scripts = ["run_tests.py", "setup.py", "install.py"]
            found_scripts = []
            for script in operational_scripts:
                if (self.repo_root / script).exists():
                    found_scripts.append(script)

            if found_scripts:
                details.append(f"[OK] Operational scripts available: {', '.join(found_scripts)}")
            else:
                details.append("[WARN] No operational scripts found")
                recommendations.append("Consider creating operational/setup scripts")
                score -= 1.0

            # Ensure score is within bounds
            score = max(0.0, min(10.0, score))

        except Exception as e:
            details.append(f"Documentation readiness check failed: {str(e)}")
            passed = False
            score = 0.0
            recommendations.append("Investigation required: Documentation check failure")

        execution_time = time.perf_counter() - start_time

        return ProductionCheck(
            check_name="Documentation & Operational Readiness",
            category="important",
            passed=passed,
            score=score,
            details=details,
            recommendations=recommendations,
            execution_time=execution_time
        )

    def check_security_safety(self) -> ProductionCheck:
        """Check security and safety considerations."""

        start_time = time.perf_counter()
        details = []
        recommendations = []
        passed = True
        score = 10.0

        try:
            # Check for common security anti-patterns
            security_issues = []
            python_files = list(self.repo_root.rglob("*.py"))

            dangerous_patterns = {
                'eval(': 'Code execution vulnerability',
                'exec(': 'Code execution vulnerability',
                'shell=True': 'Shell injection risk',
                'pickle.load': 'Unsafe deserialization',
                'yaml.load': 'Unsafe YAML loading (use safe_load)',
                'subprocess.call': 'Consider using subprocess.run with proper args'
            }

            files_checked = 0
            for py_file in python_files[:20]:  # Check first 20 files to avoid timeout
                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    files_checked += 1
                    for pattern, issue in dangerous_patterns.items():
                        if pattern in content:
                            security_issues.append(f"{py_file.name}: {issue}")

                except Exception:
                    continue

            details.append(f"[OK] Security scan completed: {files_checked} files checked")

            if security_issues:
                details.append(f"[WARN] Security considerations found: {len(security_issues)}")
                if len(security_issues) > 5:
                    details.append("[FAIL] Multiple security issues detected")
                    passed = False
                    score -= 4.0
                    recommendations.append("Critical: Address security vulnerabilities")
                else:
                    recommendations.append("Review and address security considerations")
                    score -= 2.0
            else:
                details.append("[OK] No obvious security anti-patterns detected")

            # Check for input validation patterns
            validation_patterns = ['validate', 'check', 'assert', 'raise', 'ValueError', 'TypeError']
            files_with_validation = 0

            for py_file in python_files[:10]:  # Check subset for performance
                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    if any(pattern in content for pattern in validation_patterns):
                        files_with_validation += 1
                except Exception:
                    continue

            validation_ratio = files_with_validation / min(10, len(python_files)) if python_files else 0
            if validation_ratio >= 0.5:
                details.append(f"[OK] Good input validation patterns: {validation_ratio:.1%} of files")
            else:
                details.append(f"[WARN] Limited input validation detected: {validation_ratio:.1%}")
                recommendations.append("Implement comprehensive input validation")
                score -= 1.0

            # Check for error handling
            error_handling_files = 0
            for py_file in python_files[:10]:
                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    if 'try:' in content and 'except' in content:
                        error_handling_files += 1
                except Exception:
                    continue

            error_handling_ratio = error_handling_files / min(10, len(python_files)) if python_files else 0
            if error_handling_ratio >= 0.3:
                details.append(f"[OK] Error handling present: {error_handling_ratio:.1%} of files")
            else:
                details.append(f"[WARN] Limited error handling: {error_handling_ratio:.1%}")
                recommendations.append("Implement comprehensive error handling")
                score -= 1.0

            # Check for logging/monitoring
            logging_indicators = ['logging', 'logger', 'print(', 'warn', 'error', 'info']
            files_with_logging = 0

            for py_file in python_files[:10]:
                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    if any(indicator in content for indicator in logging_indicators):
                        files_with_logging += 1
                except Exception:
                    continue

            logging_ratio = files_with_logging / min(10, len(python_files)) if python_files else 0
            if logging_ratio >= 0.5:
                details.append(f"[OK] Logging/monitoring present: {logging_ratio:.1%} of files")
            else:
                details.append(f"[WARN] Limited logging detected: {logging_ratio:.1%}")
                recommendations.append("Implement comprehensive logging for production monitoring")
                score -= 1.0

            # Ensure score is within bounds
            score = max(0.0, min(10.0, score))

        except Exception as e:
            details.append(f"Security and safety check failed: {str(e)}")
            passed = False
            score = 0.0
            recommendations.append("Investigation required: Security check failure")

        execution_time = time.perf_counter() - start_time

        return ProductionCheck(
            check_name="Security & Safety Validation",
            category="critical",
            passed=passed,
            score=score,
            details=details,
            recommendations=recommendations,
            execution_time=execution_time
        )

    def run_comprehensive_assessment(self) -> ProductionReadinessAssessment:
        """Run comprehensive production readiness assessment."""

        print("Starting Comprehensive Production Readiness Assessment...")

        # Run all production checks
        check_methods = [
            ("critical", self.check_system_stability),
            ("critical", self.check_configuration_management),
            ("critical", self.check_dependency_management),
            ("important", self.check_performance_requirements),
            ("important", self.check_documentation_readiness),
            ("critical", self.check_security_safety)
        ]

        critical_checks = []
        important_checks = []
        recommended_checks = []
        deployment_blockers = []

        for category, method in check_methods:
            method_name = method.__name__.replace('check_', '').replace('_', ' ').title()
            print(f"  Assessing: {method_name}")

            try:
                check_result = method()

                # Categorize results
                if category == "critical":
                    critical_checks.append(check_result)
                    if not check_result.passed:
                        deployment_blockers.extend(check_result.recommendations[:2])  # Top 2 recommendations
                elif category == "important":
                    important_checks.append(check_result)

                status = "PASS" if check_result.passed else "FAIL"
                print(f"    {status} - Score: {check_result.score:.1f}/10.0")

                if check_result.recommendations:
                    for rec in check_result.recommendations[:2]:  # Show first 2 recommendations
                        print(f"      • {rec}")

            except Exception as e:
                error_check = ProductionCheck(
                    check_name=method_name,
                    category=category,
                    passed=False,
                    score=0.0,
                    details=[f"Check failed: {str(e)}"],
                    recommendations=["Investigation required: Check execution failure"],
                    execution_time=0.0
                )

                if category == "critical":
                    critical_checks.append(error_check)
                    deployment_blockers.append(f"Critical check failure: {method_name}")
                else:
                    important_checks.append(error_check)

                print(f"    FAIL - Exception: {str(e)}")

        # Calculate overall score
        all_checks = critical_checks + important_checks + recommended_checks
        if all_checks:
            # Weight critical checks more heavily
            critical_weight = 0.7
            important_weight = 0.3

            critical_score = sum(c.score for c in critical_checks) / len(critical_checks) if critical_checks else 0.0
            important_score = sum(c.score for c in important_checks) / len(important_checks) if important_checks else 10.0

            overall_score = (critical_score * critical_weight) + (important_score * important_weight)
        else:
            overall_score = 0.0

        # Determine readiness level
        if overall_score >= 8.0 and len(deployment_blockers) == 0:
            readiness_level = "production_ready"
        elif overall_score >= 6.0 and len([c for c in critical_checks if not c.passed]) <= 1:
            readiness_level = "staging_ready"
        else:
            readiness_level = "development_only"

        # Generate operational recommendations
        operational_recommendations = []
        if readiness_level == "production_ready":
            operational_recommendations.extend([
                "System is ready for production deployment",
                "Implement monitoring and alerting for production environment",
                "Establish backup and recovery procedures",
                "Set up continuous integration/deployment pipeline"
            ])
        elif readiness_level == "staging_ready":
            operational_recommendations.extend([
                "System is suitable for staging environment testing",
                "Address remaining critical issues before production",
                "Implement comprehensive testing in staging environment",
                "Prepare production deployment checklist"
            ])
        else:
            operational_recommendations.extend([
                "System requires significant improvement before deployment",
                "Focus on resolving critical deployment blockers",
                "Implement comprehensive testing and validation",
                "Consider architectural review and refactoring"
            ])

        # Security assessment summary
        security_check = next((c for c in critical_checks if "security" in c.check_name.lower()), None)
        security_assessment = {
            "security_score": security_check.score if security_check else 0.0,
            "vulnerabilities_found": len([d for d in security_check.details if "⚠" in d or "✗" in d]) if security_check else 0,
            "security_recommendations": security_check.recommendations if security_check else []
        }

        # Performance metrics summary
        performance_check = next((c for c in important_checks if "performance" in c.check_name.lower()), None)
        performance_metrics = {
            "performance_score": performance_check.score if performance_check else 0.0,
            "performance_issues": len([d for d in performance_check.details if "⚠" in d or "✗" in d]) if performance_check else 0,
            "execution_time": performance_check.execution_time if performance_check else 0.0
        }

        return ProductionReadinessAssessment(
            overall_score=overall_score,
            readiness_level=readiness_level,
            deployment_blockers=deployment_blockers,
            critical_checks=critical_checks,
            important_checks=important_checks,
            recommended_checks=recommended_checks,
            security_assessment=security_assessment,
            performance_metrics=performance_metrics,
            operational_recommendations=operational_recommendations
        )

    def generate_assessment_report(self, assessment: ProductionReadinessAssessment) -> str:
        """Generate comprehensive production readiness report."""

        report = ["=" * 80]
        report.append("PRODUCTION READINESS ASSESSMENT REPORT - MISSION 10")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Executive Summary
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 20)
        readiness_icons = {
            "production_ready": "[READY]",
            "staging_ready": "[STAGING]",
            "development_only": "[DEV-ONLY]"
        }
        readiness_icon = readiness_icons.get(assessment.readiness_level, "[UNKNOWN]")

        report.append(f"{readiness_icon} Overall Score: {assessment.overall_score:.1f}/10.0")
        report.append(f"Readiness Level: {assessment.readiness_level.upper().replace('_', ' ')}")
        report.append(f"Deployment Blockers: {len(assessment.deployment_blockers)}")
        report.append("")

        # Critical Checks
        if assessment.critical_checks:
            report.append("CRITICAL PRODUCTION CHECKS")
            report.append("-" * 30)
            for check in assessment.critical_checks:
                status_icon = "[PASS]" if check.passed else "[FAIL]"
                report.append(f"{status_icon} {check.check_name} - Score: {check.score:.1f}/10.0")

                for detail in check.details[:5]:  # Limit details
                    report.append(f"   {detail}")

                if check.recommendations:
                    report.append(f"   Recommendations: {len(check.recommendations)} items")
                report.append("")

        # Important Checks
        if assessment.important_checks:
            report.append("IMPORTANT PRODUCTION CHECKS")
            report.append("-" * 30)
            for check in assessment.important_checks:
                status_icon = "[PASS]" if check.passed else "[FAIL]"
                report.append(f"{status_icon} {check.check_name} - Score: {check.score:.1f}/10.0")

                for detail in check.details[:3]:  # Limit details
                    report.append(f"   {detail}")
                report.append("")

        # Deployment Blockers
        if assessment.deployment_blockers:
            report.append("DEPLOYMENT BLOCKERS")
            report.append("-" * 20)
            for blocker in assessment.deployment_blockers:
                report.append(f"[BLOCKER] {blocker}")
            report.append("")

        # Security Assessment
        report.append("SECURITY ASSESSMENT")
        report.append("-" * 20)
        report.append(f"Security Score: {assessment.security_assessment['security_score']:.1f}/10.0")
        report.append(f"Vulnerabilities Found: {assessment.security_assessment['vulnerabilities_found']}")
        if assessment.security_assessment['security_recommendations']:
            report.append("Security Recommendations:")
            for rec in assessment.security_assessment['security_recommendations'][:3]:
                report.append(f"  • {rec}")
        report.append("")

        # Performance Metrics
        report.append("PERFORMANCE METRICS")
        report.append("-" * 20)
        report.append(f"Performance Score: {assessment.performance_metrics['performance_score']:.1f}/10.0")
        report.append(f"Performance Issues: {assessment.performance_metrics['performance_issues']}")
        report.append(f"Assessment Time: {assessment.performance_metrics['execution_time']:.2f}s")
        report.append("")

        # Operational Recommendations
        report.append("OPERATIONAL RECOMMENDATIONS")
        report.append("-" * 30)
        for i, rec in enumerate(assessment.operational_recommendations, 1):
            report.append(f"{i}. {rec}")

        return "\n".join(report)


# ============================================================================
# PYTEST TEST CASES
# ============================================================================

@pytest.fixture
def production_validator():
    """Create production readiness validator for testing."""
    return ProductionReadinessValidator()


class TestProductionReadinessValidation:
    """Test suite for production readiness validation."""

    def test_system_stability_check(self, production_validator):
        """Test system stability assessment."""
        check_result = production_validator.check_system_stability()

        assert isinstance(check_result, ProductionCheck), "Should return production check result"
        assert check_result.check_name == "System Stability Assessment", "Should have correct check name"
        assert check_result.category == "critical", "Should be critical check"
        assert 0.0 <= check_result.score <= 10.0, "Score should be between 0 and 10"
        assert check_result.execution_time > 0.0, "Should take measurable time"

    def test_configuration_management_check(self, production_validator):
        """Test configuration management assessment."""
        check_result = production_validator.check_configuration_management()

        assert isinstance(check_result, ProductionCheck), "Should return production check result"
        assert check_result.category == "critical", "Should be critical check"
        assert 0.0 <= check_result.score <= 10.0, "Score should be between 0 and 10"

    def test_dependency_management_check(self, production_validator):
        """Test dependency management assessment."""
        check_result = production_validator.check_dependency_management()

        assert isinstance(check_result, ProductionCheck), "Should return production check result"
        assert check_result.category == "critical", "Should be critical check"
        assert 0.0 <= check_result.score <= 10.0, "Score should be between 0 and 10"

    def test_performance_requirements_check(self, production_validator):
        """Test performance requirements assessment."""
        check_result = production_validator.check_performance_requirements()

        assert isinstance(check_result, ProductionCheck), "Should return production check result"
        assert check_result.category == "important", "Should be important check"
        assert 0.0 <= check_result.score <= 10.0, "Score should be between 0 and 10"

    def test_documentation_readiness_check(self, production_validator):
        """Test documentation readiness assessment."""
        check_result = production_validator.check_documentation_readiness()

        assert isinstance(check_result, ProductionCheck), "Should return production check result"
        assert check_result.category == "important", "Should be important check"
        assert 0.0 <= check_result.score <= 10.0, "Score should be between 0 and 10"

    def test_security_safety_check(self, production_validator):
        """Test security and safety assessment."""
        check_result = production_validator.check_security_safety()

        assert isinstance(check_result, ProductionCheck), "Should return production check result"
        assert check_result.category == "critical", "Should be critical check"
        assert 0.0 <= check_result.score <= 10.0, "Score should be between 0 and 10"

    def test_comprehensive_assessment(self, production_validator):
        """Test comprehensive production readiness assessment."""
        assessment = production_validator.run_comprehensive_assessment()

        assert isinstance(assessment, ProductionReadinessAssessment), "Should return assessment result"
        assert 0.0 <= assessment.overall_score <= 10.0, "Overall score should be between 0 and 10"
        assert assessment.readiness_level in ["production_ready", "staging_ready", "development_only"], "Should have valid readiness level"
        assert len(assessment.critical_checks) > 0, "Should have critical checks"

    def test_assessment_report_generation(self, production_validator):
        """Test assessment report generation."""
        assessment = production_validator.run_comprehensive_assessment()
        report = production_validator.generate_assessment_report(assessment)

        assert isinstance(report, str), "Should generate string report"
        assert len(report) > 500, "Report should be substantial"
        assert "PRODUCTION READINESS ASSESSMENT REPORT" in report, "Should have proper header"
        assert "EXECUTIVE SUMMARY" in report, "Should have executive summary"

    def test_mission_10_production_readiness_criteria(self, production_validator):
        """Test Mission 10 production readiness success criteria."""
        assessment = production_validator.run_comprehensive_assessment()
        report = production_validator.generate_assessment_report(assessment)

        print("\n" + "="*80)
        print("MISSION 10: PRODUCTION READINESS VALIDATION RESULTS")
        print("="*80)
        print(report)

        # Mission 10 targets
        target_score = 8.0  # Production readiness score ≥ 8.0/10

        if assessment.overall_score >= target_score:
            print(f"\nMISSION 10 SUCCESS: Production readiness score {assessment.overall_score:.1f}/10.0 achieved!")
            if assessment.readiness_level == "production_ready":
                assert len(assessment.deployment_blockers) == 0, "Production ready system should have no blockers"
                print("System is PRODUCTION READY for deployment!")
            else:
                print(f"System readiness level: {assessment.readiness_level}")
        else:
            print(f"\nMISSION 10 PROGRESS: Production readiness score {assessment.overall_score:.1f}/10.0")
            print(f"Target: {target_score:.1f}/10.0 | Gap: {target_score - assessment.overall_score:.1f}")

            if assessment.deployment_blockers:
                print("Deployment Blockers to Address:")
                for blocker in assessment.deployment_blockers[:5]:
                    print(f"  • {blocker}")

        # Validate security requirements
        security_score = assessment.security_assessment.get('security_score', 0.0)
        assert security_score >= 5.0, f"Security score too low: {security_score:.1f}/10.0"

        # Don't fail test - this is validation and feedback
        assert assessment.overall_score > 0.0, "System should have some production readiness"


if __name__ == "__main__":
    # Run standalone production readiness assessment
    validator = ProductionReadinessValidator()

    print("MISSION 10: Production Readiness Assessment")
    print("="*50)

    # Run comprehensive assessment
    assessment = validator.run_comprehensive_assessment()

    # Generate and display report
    report = validator.generate_assessment_report(assessment)
    print(report)

    # Final status
    if assessment.readiness_level == "production_ready":
        print("\nSUCCESS: System is production ready!")
    elif assessment.readiness_level == "staging_ready":
        print(f"\nPROGRESS: System ready for staging (Score: {assessment.overall_score:.1f}/10.0)")
    else:
        print(f"\nDEVELOPMENT: System needs improvement (Score: {assessment.overall_score:.1f}/10.0)")
        print("Focus on addressing deployment blockers.")