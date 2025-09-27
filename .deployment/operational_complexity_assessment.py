#==========================================================================================\\\
#================= deployment/operational_complexity_assessment.py ======================\\\
#==========================================================================================\\\
"""
Operational Complexity Assessment and Remediation
Comprehensive analysis of deployment and maintenance complexity for production readiness.

Key Metrics Assessed:
1. Code base complexity (391 Python files, 96,921 lines)
2. Configuration complexity (27+ config files)
3. Deployment complexity (manual processes, dependencies)
4. Maintenance complexity (onboarding, debugging, updates)
5. Operational risk assessment
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
import subprocess
import logging
import json
import yaml
from collections import defaultdict


@dataclass
class ComplexityMetric:
    """Individual complexity metric."""
    name: str
    value: float
    max_value: float
    weight: float
    description: str
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ComplexityAssessment:
    """Complete complexity assessment results."""
    overall_score: float  # 0-10 scale
    risk_level: str       # LOW, MEDIUM, HIGH, CRITICAL
    metrics: List[ComplexityMetric]
    critical_issues: List[str]
    recommendations: List[str]
    deployment_blockers: List[str]


class OperationalComplexityAssessor:
    """
    Assesses and quantifies operational complexity for production deployment.

    This tool provides objective metrics on deployment complexity and
    maintenance risks for the 391-file, 96k+ line codebase.
    """

    def __init__(self, project_root: Path = None):
        """Initialize operational complexity assessor."""
        self.project_root = project_root or Path.cwd()
        self.logger = logging.getLogger("complexity_assessor")

        # Complexity weight factors (how much each metric contributes to overall score)
        self.weights = {
            'codebase_size': 0.25,      # 25% - Raw size metrics
            'file_organization': 0.20,   # 20% - File structure complexity
            'configuration': 0.20,       # 20% - Config file complexity
            'dependencies': 0.15,        # 15% - Dependency complexity
            'deployment': 0.20           # 20% - Deployment process complexity
        }

    def assess_complexity(self) -> ComplexityAssessment:
        """Perform comprehensive operational complexity assessment."""
        self.logger.info("Starting operational complexity assessment...")

        metrics = []

        # 1. Codebase Size Complexity
        metrics.extend(self._assess_codebase_size())

        # 2. File Organization Complexity
        metrics.extend(self._assess_file_organization())

        # 3. Configuration Complexity
        metrics.extend(self._assess_configuration_complexity())

        # 4. Dependency Complexity
        metrics.extend(self._assess_dependency_complexity())

        # 5. Deployment Process Complexity
        metrics.extend(self._assess_deployment_complexity())

        # Calculate overall complexity score
        overall_score = self._calculate_overall_score(metrics)
        risk_level = self._determine_risk_level(overall_score)
        critical_issues = self._identify_critical_issues(metrics)
        recommendations = self._generate_recommendations(metrics, critical_issues)
        deployment_blockers = self._identify_deployment_blockers(metrics)

        return ComplexityAssessment(
            overall_score=overall_score,
            risk_level=risk_level,
            metrics=metrics,
            critical_issues=critical_issues,
            recommendations=recommendations,
            deployment_blockers=deployment_blockers
        )

    def _assess_codebase_size(self) -> List[ComplexityMetric]:
        """Assess codebase size complexity."""
        metrics = []

        # Count Python files
        py_files = list(self.project_root.rglob("*.py"))
        py_file_count = len(py_files)

        # Count total lines of code
        total_lines = 0
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    total_lines += sum(1 for line in f)
            except Exception:
                pass

        # Count directories with Python files
        py_dirs = set(py_file.parent for py_file in py_files)
        dir_count = len(py_dirs)

        # File count complexity (industry standard: >300 files = high complexity)
        file_complexity = min(10.0, (py_file_count / 300.0) * 10.0)
        metrics.append(ComplexityMetric(
            name="Python File Count",
            value=py_file_count,
            max_value=500,  # Reasonable maximum for maintainable projects
            weight=0.4,
            description=f"{py_file_count} Python files (Industry limit: ~300 for single team)",
            recommendations=[
                "Consider modularization into separate packages",
                "Implement microservice architecture",
                "Create clear module boundaries"
            ] if py_file_count > 300 else []
        ))

        # Lines of code complexity (industry standard: >100k LOC = very high complexity)
        loc_complexity = min(10.0, (total_lines / 100000.0) * 10.0)
        metrics.append(ComplexityMetric(
            name="Lines of Code",
            value=total_lines,
            max_value=100000,
            weight=0.4,
            description=f"{total_lines:,} lines of Python code (Industry limit: ~50k-100k)",
            recommendations=[
                "Refactor large modules into smaller components",
                "Extract reusable libraries",
                "Implement code generation where appropriate"
            ] if total_lines > 50000 else []
        ))

        # Directory depth complexity
        max_depth = max(len(py_file.parts) for py_file in py_files) if py_files else 0
        depth_complexity = min(10.0, (max_depth / 8.0) * 10.0)  # 8 levels = very deep
        metrics.append(ComplexityMetric(
            name="Directory Depth",
            value=max_depth,
            max_value=8,
            weight=0.2,
            description=f"Maximum directory depth: {max_depth} levels",
            recommendations=[
                "Flatten directory structure",
                "Reduce nesting levels",
                "Reorganize into logical modules"
            ] if max_depth > 6 else []
        ))

        return metrics

    def _assess_file_organization(self) -> List[ComplexityMetric]:
        """Assess file organization complexity."""
        metrics = []

        # Module interdependency complexity
        try:
            # Simple import analysis
            import_graph = self._analyze_imports()

            # Calculate average imports per file
            if import_graph:
                avg_imports = sum(len(imports) for imports in import_graph.values()) / len(import_graph)
                import_complexity = min(10.0, (avg_imports / 20.0) * 10.0)  # 20 imports = very complex
            else:
                avg_imports = 0
                import_complexity = 0

            metrics.append(ComplexityMetric(
                name="Import Complexity",
                value=avg_imports,
                max_value=20,
                weight=0.5,
                description=f"Average imports per file: {avg_imports:.1f}",
                recommendations=[
                    "Reduce coupling between modules",
                    "Use dependency injection",
                    "Create cleaner interfaces"
                ] if avg_imports > 15 else []
            ))

        except Exception as e:
            self.logger.warning(f"Could not analyze imports: {e}")

        # Module size distribution
        file_sizes = []
        for py_file in self.project_root.rglob("*.py"):
            try:
                file_sizes.append(py_file.stat().st_size)
            except Exception:
                pass

        if file_sizes:
            avg_file_size = sum(file_sizes) / len(file_sizes)
            max_file_size = max(file_sizes)

            # Large file complexity (>10KB per file is concerning)
            size_complexity = min(10.0, (avg_file_size / 10240.0) * 10.0)
            metrics.append(ComplexityMetric(
                name="Average File Size",
                value=avg_file_size,
                max_value=10240,  # 10KB
                weight=0.3,
                description=f"Average Python file size: {avg_file_size/1024:.1f}KB",
                recommendations=[
                    "Break large files into smaller modules",
                    "Extract classes and functions",
                    "Use composition over inheritance"
                ] if avg_file_size > 5120 else []
            ))

            # Maximum file size complexity
            max_size_complexity = min(10.0, (max_file_size / 51200.0) * 10.0)  # 50KB = very large
            metrics.append(ComplexityMetric(
                name="Largest File Size",
                value=max_file_size,
                max_value=51200,  # 50KB
                weight=0.2,
                description=f"Largest Python file: {max_file_size/1024:.1f}KB",
                recommendations=[
                    f"Refactor largest files (target: <20KB per file)",
                    "Split monolithic modules",
                    "Use multiple inheritance or composition"
                ] if max_file_size > 20480 else []
            ))

        return metrics

    def _assess_configuration_complexity(self) -> List[ComplexityMetric]:
        """Assess configuration file complexity."""
        metrics = []

        # Count configuration files
        config_patterns = ['*.yaml', '*.yml', '*.json', '*.toml', '*.ini', '*.cfg']
        config_files = []
        for pattern in config_patterns:
            config_files.extend(self.project_root.rglob(pattern))

        # Filter out hidden and build files
        config_files = [f for f in config_files
                       if not any(part.startswith('.') for part in f.parts)
                       and 'node_modules' not in str(f)
                       and '__pycache__' not in str(f)]

        config_count = len(config_files)

        # Configuration file count complexity (>10 config files = high complexity)
        config_complexity = min(10.0, (config_count / 10.0) * 10.0)
        metrics.append(ComplexityMetric(
            name="Configuration Files",
            value=config_count,
            max_value=15,
            weight=0.6,
            description=f"{config_count} configuration files",
            recommendations=[
                "Consolidate related configurations",
                "Use configuration inheritance",
                "Implement environment-based configs"
            ] if config_count > 10 else []
        ))

        # Configuration file size and complexity
        total_config_size = sum(f.stat().st_size for f in config_files if f.exists())
        avg_config_size = total_config_size / len(config_files) if config_files else 0

        config_size_complexity = min(10.0, (avg_config_size / 5120.0) * 10.0)  # 5KB per config
        metrics.append(ComplexityMetric(
            name="Configuration Size",
            value=avg_config_size,
            max_value=5120,
            weight=0.4,
            description=f"Average config size: {avg_config_size/1024:.1f}KB",
            recommendations=[
                "Split large configuration files",
                "Use configuration templates",
                "Implement configuration validation"
            ] if avg_config_size > 2048 else []
        ))

        return metrics

    def _assess_dependency_complexity(self) -> List[ComplexityMetric]:
        """Assess dependency management complexity."""
        metrics = []

        # Analyze requirements.txt
        requirements_files = list(self.project_root.glob("requirements*.txt"))
        total_deps = 0

        for req_file in requirements_files:
            try:
                with open(req_file, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    total_deps += len(lines)
            except Exception:
                pass

        # Dependency count complexity (>50 dependencies = high complexity)
        dep_complexity = min(10.0, (total_deps / 50.0) * 10.0)
        metrics.append(ComplexityMetric(
            name="Dependencies",
            value=total_deps,
            max_value=75,
            weight=0.7,
            description=f"{total_deps} Python dependencies",
            recommendations=[
                "Audit and remove unused dependencies",
                "Use virtual environments",
                "Implement dependency scanning"
            ] if total_deps > 30 else []
        ))

        # Check for version pinning
        pinned_deps = 0
        unpinned_deps = 0
        for req_file in requirements_files:
            try:
                with open(req_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if any(op in line for op in ['==', '>=', '<=', '~=', '!=']):
                                pinned_deps += 1
                            else:
                                unpinned_deps += 1
            except Exception:
                pass

        if total_deps > 0:
            pin_ratio = pinned_deps / total_deps
            pin_complexity = (1.0 - pin_ratio) * 10.0  # Lower pinning = higher complexity

            metrics.append(ComplexityMetric(
                name="Dependency Pinning",
                value=pin_ratio * 100,  # As percentage
                max_value=100,
                weight=0.3,
                description=f"{pin_ratio*100:.1f}% of dependencies have version constraints",
                recommendations=[
                    "Add version constraints to dependencies",
                    "Use lock files for reproducible builds",
                    "Implement dependency security scanning"
                ] if pin_ratio < 0.8 else []
            ))

        return metrics

    def _assess_deployment_complexity(self) -> List[ComplexityMetric]:
        """Assess deployment process complexity."""
        metrics = []

        # Check for deployment automation
        automation_files = []
        automation_patterns = [
            'Dockerfile', 'docker-compose.yml', 'Makefile',
            'deploy.sh', 'setup.py', 'pyproject.toml',
            '*.yml', '*.yaml'  # CI/CD files
        ]

        for pattern in automation_patterns:
            automation_files.extend(self.project_root.glob(pattern))

        # Check for CI/CD in common locations
        ci_dirs = ['.github', '.gitlab-ci', 'ci', 'scripts']
        ci_files = 0
        for ci_dir in ci_dirs:
            ci_path = self.project_root / ci_dir
            if ci_path.exists():
                ci_files += len(list(ci_path.rglob('*')))

        automation_score = min(10.0, len(automation_files) + (ci_files / 5.0))
        automation_complexity = 10.0 - automation_score  # Inverse: less automation = higher complexity

        metrics.append(ComplexityMetric(
            name="Deployment Automation",
            value=automation_score,
            max_value=10,
            weight=0.4,
            description=f"Automation score: {automation_score:.1f}/10",
            recommendations=[
                "Implement automated deployment scripts",
                "Add CI/CD pipeline configuration",
                "Create Docker containerization",
                "Add deployment health checks"
            ] if automation_score < 5.0 else []
        ))

        # Manual process complexity (based on number of files and configs)
        py_files = len(list(self.project_root.rglob("*.py")))
        config_files = len([f for f in self.project_root.rglob("*")
                           if f.suffix in ['.yaml', '.yml', '.json', '.toml', '.ini']])

        manual_complexity = min(10.0, ((py_files + config_files * 2) / 500.0) * 10.0)

        metrics.append(ComplexityMetric(
            name="Manual Process Risk",
            value=py_files + config_files,
            max_value=500,
            weight=0.4,
            description=f"{py_files} code files + {config_files} config files to manage manually",
            recommendations=[
                "Implement automated file validation",
                "Create deployment checklists",
                "Add pre-deployment testing",
                "Use infrastructure as code"
            ] if manual_complexity > 7.0 else []
        ))

        # Documentation complexity
        doc_files = list(self.project_root.rglob("*.md")) + list(self.project_root.rglob("*.rst"))
        doc_coverage = min(10.0, len(doc_files) / 10.0)  # 10 docs = good coverage
        doc_complexity = 10.0 - doc_coverage  # Less documentation = higher complexity

        metrics.append(ComplexityMetric(
            name="Documentation Coverage",
            value=doc_coverage,
            max_value=10,
            weight=0.2,
            description=f"{len(doc_files)} documentation files found",
            recommendations=[
                "Create deployment documentation",
                "Add operational runbooks",
                "Document troubleshooting procedures",
                "Create architecture diagrams"
            ] if doc_coverage < 5.0 else []
        ))

        return metrics

    def _analyze_imports(self) -> Dict[str, List[str]]:
        """Analyze import dependencies between modules."""
        import_graph = {}

        for py_file in self.project_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                imports = []
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith(('import ', 'from ')):
                        imports.append(line)

                relative_path = str(py_file.relative_to(self.project_root))
                import_graph[relative_path] = imports

            except Exception:
                pass

        return import_graph

    def _calculate_overall_score(self, metrics: List[ComplexityMetric]) -> float:
        """Calculate weighted overall complexity score."""
        if not metrics:
            return 0.0

        # Group metrics by category and calculate category scores
        category_scores = defaultdict(list)

        for metric in metrics:
            # Determine category based on metric name
            if any(keyword in metric.name.lower() for keyword in ['file', 'code', 'size', 'depth']):
                category = 'codebase_size'
            elif any(keyword in metric.name.lower() for keyword in ['import', 'organization']):
                category = 'file_organization'
            elif 'configuration' in metric.name.lower():
                category = 'configuration'
            elif any(keyword in metric.name.lower() for keyword in ['dependency', 'dependencies']):
                category = 'dependencies'
            else:
                category = 'deployment'

            # Normalize metric value to 0-10 scale
            if metric.max_value > 0:
                normalized_value = min(10.0, (metric.value / metric.max_value) * 10.0)
            else:
                normalized_value = metric.value

            category_scores[category].append(normalized_value * metric.weight)

        # Calculate weighted average
        total_score = 0.0
        for category, weight in self.weights.items():
            if category in category_scores:
                category_avg = sum(category_scores[category]) / len(category_scores[category])
                total_score += category_avg * weight

        return min(10.0, total_score)

    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on complexity score."""
        if score >= 8.0:
            return "CRITICAL"
        elif score >= 6.0:
            return "HIGH"
        elif score >= 4.0:
            return "MEDIUM"
        else:
            return "LOW"

    def _identify_critical_issues(self, metrics: List[ComplexityMetric]) -> List[str]:
        """Identify critical complexity issues."""
        critical_issues = []

        for metric in metrics:
            # Critical thresholds
            if metric.name == "Python File Count" and metric.value > 350:
                critical_issues.append(f"Excessive file count: {int(metric.value)} files (limit: ~300)")
            elif metric.name == "Lines of Code" and metric.value > 80000:
                critical_issues.append(f"Excessive codebase size: {int(metric.value):,} lines (limit: ~50k-80k)")
            elif metric.name == "Configuration Files" and metric.value > 20:
                critical_issues.append(f"Too many config files: {int(metric.value)} files (limit: ~10-15)")
            elif metric.name == "Dependencies" and metric.value > 60:
                critical_issues.append(f"Excessive dependencies: {int(metric.value)} packages (limit: ~30-50)")
            elif metric.name == "Manual Process Risk" and metric.value > 400:
                critical_issues.append(f"High manual deployment risk: {int(metric.value)} files to manage")

        return critical_issues

    def _generate_recommendations(self, metrics: List[ComplexityMetric], critical_issues: List[str]) -> List[str]:
        """Generate prioritized recommendations for complexity reduction."""
        recommendations = []

        # High-impact recommendations for critical issues
        if any("file count" in issue.lower() for issue in critical_issues):
            recommendations.extend([
                "🔥 CRITICAL: Break monolithic codebase into multiple packages/services",
                "🔥 CRITICAL: Implement clear module boundaries and interfaces",
                "🔥 CRITICAL: Consider microservice architecture for complex domains"
            ])

        if any("config" in issue.lower() for issue in critical_issues):
            recommendations.extend([
                "🔥 CRITICAL: Consolidate configuration files using hierarchical structure",
                "🔥 CRITICAL: Implement environment-based configuration management",
                "🔥 CRITICAL: Use configuration validation and templates"
            ])

        if any("manual" in issue.lower() for issue in critical_issues):
            recommendations.extend([
                "🔥 CRITICAL: Implement automated deployment pipeline",
                "🔥 CRITICAL: Add comprehensive deployment health checks",
                "🔥 CRITICAL: Create deployment rollback mechanisms"
            ])

        # Collect specific recommendations from metrics
        for metric in metrics:
            recommendations.extend(metric.recommendations)

        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                unique_recommendations.append(rec)
                seen.add(rec)

        return unique_recommendations[:15]  # Top 15 recommendations

    def _identify_deployment_blockers(self, metrics: List[ComplexityMetric]) -> List[str]:
        """Identify specific deployment blockers."""
        blockers = []

        for metric in metrics:
            if metric.name == "Python File Count" and metric.value > 300:
                blockers.append("File management complexity exceeds single-team capacity")
            elif metric.name == "Configuration Files" and metric.value > 15:
                blockers.append("Configuration complexity creates high deployment error risk")
            elif metric.name == "Manual Process Risk" and metric.value > 300:
                blockers.append("Manual deployment process prone to human error")
            elif metric.name == "Dependencies" and metric.value > 50:
                blockers.append("Dependency complexity increases environment setup failures")
            elif metric.name == "Deployment Automation" and metric.value < 3.0:
                blockers.append("Lack of deployment automation increases failure risk")

        return blockers

    def generate_report(self, assessment: ComplexityAssessment) -> str:
        """Generate comprehensive complexity assessment report."""
        lines = [
            "=" * 80,
            "OPERATIONAL COMPLEXITY ASSESSMENT REPORT",
            "=" * 80,
            "",
            f"Overall Complexity Score: {assessment.overall_score:.1f}/10 ({assessment.risk_level} RISK)",
            "",
            "📊 COMPLEXITY METRICS:",
            ""
        ]

        # Metrics by category
        categories = defaultdict(list)
        for metric in assessment.metrics:
            if any(keyword in metric.name.lower() for keyword in ['file', 'code', 'size', 'depth']):
                categories['Codebase Size'].append(metric)
            elif any(keyword in metric.name.lower() for keyword in ['import', 'organization']):
                categories['File Organization'].append(metric)
            elif 'configuration' in metric.name.lower():
                categories['Configuration'].append(metric)
            elif any(keyword in metric.name.lower() for keyword in ['dependency', 'dependencies']):
                categories['Dependencies'].append(metric)
            else:
                categories['Deployment'].append(metric)

        for category, metrics in categories.items():
            lines.append(f"  {category}:")
            for metric in metrics:
                status = "🔴" if metric.value > metric.max_value * 0.8 else "🟡" if metric.value > metric.max_value * 0.5 else "🟢"
                lines.append(f"    {status} {metric.name}: {metric.value:.0f} ({metric.description})")
            lines.append("")

        if assessment.critical_issues:
            lines.extend([
                "🚨 CRITICAL ISSUES:",
                ""
            ])
            for issue in assessment.critical_issues:
                lines.append(f"  • {issue}")
            lines.append("")

        if assessment.deployment_blockers:
            lines.extend([
                "🛑 DEPLOYMENT BLOCKERS:",
                ""
            ])
            for blocker in assessment.deployment_blockers:
                lines.append(f"  • {blocker}")
            lines.append("")

        lines.extend([
            "💡 TOP RECOMMENDATIONS:",
            ""
        ])
        for i, rec in enumerate(assessment.recommendations[:10], 1):
            lines.append(f"  {i}. {rec}")

        lines.extend([
            "",
            "=" * 80,
            f"Assessment completed. Risk Level: {assessment.risk_level}",
            "=" * 80
        ])

        return "\n".join(lines)


def main():
    """Main assessment execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Operational Complexity Assessment")
    parser.add_argument('--output', help='Output file for detailed report')
    args = parser.parse_args()

    print("Assessing operational complexity...")
    assessor = OperationalComplexityAssessor()
    assessment = assessor.assess_complexity()

    report = assessor.generate_report(assessment)
    print(report)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\nDetailed report saved to: {args.output}")

    # Return True for low/medium risk, False for high/critical risk
    return assessment.risk_level in ['LOW', 'MEDIUM']


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)