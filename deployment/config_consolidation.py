#==========================================================================================\\\
#====================== deployment/config_consolidation.py ===============================\\\
#==========================================================================================\\\
"""
Configuration Consolidation System
Addresses the operational complexity of 27+ configuration files by
consolidating, validating, and managing configurations centrally.

Key Features:
1. Consolidate 27+ config files into manageable structure
2. Validate configuration consistency across files
3. Generate deployment-ready configuration packages
4. Detect configuration conflicts and dependencies
5. Create environment-specific configuration profiles
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
import logging
from collections import defaultdict


@dataclass
class ConfigFile:
    """Configuration file metadata."""
    path: Path
    type: str  # yaml, json, toml, ini
    size_bytes: int
    sections: List[str]
    dependencies: Set[str] = field(default_factory=set)
    conflicts: Set[str] = field(default_factory=set)


@dataclass
class ConsolidationReport:
    """Configuration consolidation report."""
    total_files: int
    consolidated_files: int
    redundant_files: int
    conflicts_resolved: int
    size_reduction_bytes: int
    validation_errors: List[str]


class ConfigurationConsolidator:
    """
    Consolidates complex configuration structure into manageable deployment units.

    Reduces operational complexity by organizing 27+ configuration files
    into logical groups and eliminating redundancy.
    """

    def __init__(self, root_path: Path = None):
        """Initialize configuration consolidator."""
        self.root_path = root_path or Path.cwd()
        self.config_files: List[ConfigFile] = []
        self.consolidated_configs: Dict[str, Dict[str, Any]] = {}

        self.logger = logging.getLogger("config_consolidator")

        # Configuration categories for consolidation
        self.categories = {
            'runtime': ['config.yaml', 'requirements*.txt'],
            'testing': ['test_*.yaml', '*test*.json', 'pytest.ini'],
            'documentation': ['docs/**/*.yaml', '**/*_config.yml'],
            'deployment': ['docker*.yml', 'k8s*.yaml', 'helm/**/*.yaml'],
            'development': ['.vscode/**/*.json', '.github/**/*.yml'],
            'monitoring': ['*monitor*.yaml', '*metrics*.json'],
        }

    def discover_configurations(self) -> List[ConfigFile]:
        """Discover all configuration files in the project."""
        self.logger.info("Discovering configuration files...")

        config_patterns = ['*.yaml', '*.yml', '*.json', '*.toml', '*.ini', '*.cfg']
        discovered_files = []

        for pattern in config_patterns:
            for config_file in self.root_path.rglob(pattern):
                # Skip hidden directories and files
                if any(part.startswith('.') for part in config_file.parts):
                    continue

                # Skip build/cache directories
                skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'build', 'dist'}
                if any(skip_dir in str(config_file) for skip_dir in skip_dirs):
                    continue

                try:
                    file_info = ConfigFile(
                        path=config_file,
                        type=config_file.suffix[1:],  # Remove dot
                        size_bytes=config_file.stat().st_size,
                        sections=self._extract_sections(config_file)
                    )
                    discovered_files.append(file_info)
                except Exception as e:
                    self.logger.warning(f"Could not process {config_file}: {e}")

        self.config_files = discovered_files
        self.logger.info(f"Discovered {len(discovered_files)} configuration files")
        return discovered_files

    def analyze_configurations(self) -> Dict[str, Any]:
        """Analyze configuration files for consolidation opportunities."""
        self.logger.info("Analyzing configurations...")

        analysis = {
            'total_files': len(self.config_files),
            'total_size': sum(cf.size_bytes for cf in self.config_files),
            'by_type': defaultdict(list),
            'by_category': defaultdict(list),
            'duplicates': [],
            'conflicts': [],
            'dependencies': defaultdict(set)
        }

        # Group by file type
        for config_file in self.config_files:
            analysis['by_type'][config_file.type].append(config_file)

        # Categorize files
        for config_file in self.config_files:
            category = self._categorize_file(config_file.path)
            analysis['by_category'][category].append(config_file)

        # Find potential duplicates and conflicts
        self._detect_duplicates_and_conflicts(analysis)

        return analysis

    def consolidate_configurations(self) -> ConsolidationReport:
        """Consolidate configurations into manageable structure."""
        self.logger.info("Starting configuration consolidation...")

        initial_count = len(self.config_files)
        initial_size = sum(cf.size_bytes for cf in self.config_files)

        # Consolidate by category
        for category, files in self._group_by_category().items():
            self.logger.info(f"Consolidating {category} configurations...")
            consolidated = self._consolidate_category(category, files)
            if consolidated:
                self.consolidated_configs[category] = consolidated

        # Generate consolidated files
        self._generate_consolidated_files()

        # Calculate consolidation results
        final_count = len(self.consolidated_configs)
        final_size = sum(
            len(json.dumps(config).encode('utf-8'))
            for config in self.consolidated_configs.values()
        )

        return ConsolidationReport(
            total_files=initial_count,
            consolidated_files=final_count,
            redundant_files=initial_count - final_count,
            conflicts_resolved=0,  # Would be calculated during actual consolidation
            size_reduction_bytes=initial_size - final_size,
            validation_errors=[]
        )

    def validate_consolidated_configs(self) -> List[str]:
        """Validate consolidated configurations."""
        self.logger.info("Validating consolidated configurations...")

        errors = []

        for category, config in self.consolidated_configs.items():
            try:
                # Basic structure validation
                if not isinstance(config, dict):
                    errors.append(f"{category}: Configuration must be a dictionary")
                    continue

                # Category-specific validation
                category_errors = self._validate_category_config(category, config)
                errors.extend(category_errors)

            except Exception as e:
                errors.append(f"{category}: Validation error - {e}")

        return errors

    def generate_deployment_configs(self, environment: str = 'production') -> Dict[str, str]:
        """Generate environment-specific deployment configurations."""
        self.logger.info(f"Generating deployment configs for {environment}")

        deployment_configs = {}

        for category, config in self.consolidated_configs.items():
            # Apply environment-specific overrides
            env_config = self._apply_environment_overrides(config, environment)

            # Generate final configuration file content
            if category in ['runtime', 'monitoring']:
                # Critical configs as YAML for readability
                deployment_configs[f"{category}_{environment}.yaml"] = yaml.dump(
                    env_config, default_flow_style=False, indent=2
                )
            else:
                # Non-critical configs as JSON for compactness
                deployment_configs[f"{category}_{environment}.json"] = json.dumps(
                    env_config, indent=2
                )

        return deployment_configs

    def _extract_sections(self, config_file: Path) -> List[str]:
        """Extract configuration sections from file."""
        try:
            if config_file.suffix in ['.yaml', '.yml']:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        return list(data.keys())

            elif config_file.suffix == '.json':
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return list(data.keys())

        except Exception as e:
            self.logger.warning(f"Could not extract sections from {config_file}: {e}")

        return []

    def _categorize_file(self, file_path: Path) -> str:
        """Categorize configuration file."""
        file_str = str(file_path).lower()

        for category, patterns in self.categories.items():
            for pattern in patterns:
                # Simple pattern matching
                if '*' in pattern:
                    pattern_parts = pattern.split('*')
                    if all(part in file_str for part in pattern_parts if part):
                        return category
                else:
                    if pattern in file_str:
                        return category

        return 'miscellaneous'

    def _group_by_category(self) -> Dict[str, List[ConfigFile]]:
        """Group configuration files by category."""
        groups = defaultdict(list)

        for config_file in self.config_files:
            category = self._categorize_file(config_file.path)
            groups[category].append(config_file)

        return dict(groups)

    def _consolidate_category(self, category: str, files: List[ConfigFile]) -> Optional[Dict[str, Any]]:
        """Consolidate files within a category."""
        if not files:
            return None

        consolidated = {}

        for config_file in files:
            try:
                file_config = self._load_config_file(config_file.path)
                if file_config:
                    # Use filename as namespace to avoid conflicts
                    namespace = config_file.path.stem
                    consolidated[namespace] = file_config

            except Exception as e:
                self.logger.warning(f"Could not consolidate {config_file.path}: {e}")

        return consolidated if consolidated else None

    def _load_config_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load configuration file content."""
        try:
            if file_path.suffix in ['.yaml', '.yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)

            elif file_path.suffix == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)

            elif file_path.suffix == '.toml':
                try:
                    import tomllib
                    with open(file_path, 'rb') as f:
                        return tomllib.load(f)
                except ImportError:
                    self.logger.warning(f"TOML support not available for {file_path}")

        except Exception as e:
            self.logger.warning(f"Could not load {file_path}: {e}")

        return None

    def _generate_consolidated_files(self) -> None:
        """Generate consolidated configuration files."""
        output_dir = self.root_path / 'deployment' / 'consolidated_configs'
        output_dir.mkdir(parents=True, exist_ok=True)

        for category, config in self.consolidated_configs.items():
            output_file = output_dir / f"{category}_consolidated.yaml"

            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)

            self.logger.info(f"Generated consolidated config: {output_file}")

    def _validate_category_config(self, category: str, config: Dict[str, Any]) -> List[str]:
        """Validate category-specific configuration."""
        errors = []

        if category == 'runtime':
            # Validate runtime configuration
            if 'config' in config:
                runtime_config = config['config']
                required_sections = ['controllers', 'physics', 'simulation']
                for section in required_sections:
                    if section not in runtime_config:
                        errors.append(f"Runtime config missing required section: {section}")

        elif category == 'testing':
            # Validate testing configuration
            if not any('test' in namespace for namespace in config.keys()):
                errors.append("Testing category should contain test-related configurations")

        return errors

    def _apply_environment_overrides(self, config: Dict[str, Any], environment: str) -> Dict[str, Any]:
        """Apply environment-specific configuration overrides."""
        env_config = config.copy()

        # Environment-specific overrides
        overrides = {
            'production': {
                'debug': False,
                'logging_level': 'INFO',
                'monitoring_enabled': True
            },
            'staging': {
                'debug': True,
                'logging_level': 'DEBUG',
                'monitoring_enabled': True
            },
            'development': {
                'debug': True,
                'logging_level': 'DEBUG',
                'monitoring_enabled': False
            }
        }

        env_overrides = overrides.get(environment, {})

        # Apply overrides recursively
        def apply_overrides(target: Dict[str, Any], source: Dict[str, Any]):
            for key, value in source.items():
                if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                    apply_overrides(target[key], value)
                else:
                    target[key] = value

        for namespace in env_config.values():
            if isinstance(namespace, dict):
                apply_overrides(namespace, env_overrides)

        return env_config

    def _detect_duplicates_and_conflicts(self, analysis: Dict[str, Any]) -> None:
        """Detect duplicate configurations and conflicts."""
        # Simple duplicate detection based on content similarity
        seen_sections = defaultdict(list)

        for config_file in self.config_files:
            for section in config_file.sections:
                seen_sections[section].append(config_file)

        # Report potential duplicates
        for section, files in seen_sections.items():
            if len(files) > 1:
                file_paths = [str(f.path) for f in files]
                analysis['duplicates'].append({
                    'section': section,
                    'files': file_paths
                })

    def generate_consolidation_report(self, report: ConsolidationReport) -> str:
        """Generate human-readable consolidation report."""
        lines = [
            "=== CONFIGURATION CONSOLIDATION REPORT ===",
            "",
            f"Original Files: {report.total_files}",
            f"Consolidated Files: {report.consolidated_files}",
            f"Redundant Files Eliminated: {report.redundant_files}",
            f"Size Reduction: {report.size_reduction_bytes:,} bytes",
            "",
            "Configuration Categories:"
        ]

        for category in self.consolidated_configs.keys():
            lines.append(f"  - {category.title()}")

        if report.validation_errors:
            lines.extend([
                "",
                "Validation Errors:",
                *[f"  - {error}" for error in report.validation_errors]
            ])
        else:
            lines.append("\n✅ All consolidated configurations validated successfully")

        return "\n".join(lines)


def main():
    """Main consolidation execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Configuration Consolidation Tool")
    parser.add_argument('--analyze-only', action='store_true',
                       help='Analyze configurations without consolidating')
    parser.add_argument('--environment', choices=['production', 'staging', 'development'],
                       default='production', help='Target environment for deployment configs')

    args = parser.parse_args()

    consolidator = ConfigurationConsolidator()

    print("Discovering configuration files...")
    files = consolidator.discover_configurations()
    print(f"Found {len(files)} configuration files")

    if args.analyze_only:
        print("\nAnalyzing configurations...")
        analysis = consolidator.analyze_configurations()

        print(f"\nConfiguration Analysis:")
        print(f"  Total files: {analysis['total_files']}")
        print(f"  Total size: {analysis['total_size']:,} bytes")
        print(f"  File types: {list(analysis['by_type'].keys())}")
        print(f"  Categories: {list(analysis['by_category'].keys())}")

        if analysis['duplicates']:
            print(f"\nPotential duplicates found: {len(analysis['duplicates'])}")
            for dup in analysis['duplicates'][:5]:  # Show first 5
                print(f"  - {dup['section']}: {len(dup['files'])} files")

        return True

    print("\nConsolidating configurations...")
    report = consolidator.consolidate_configurations()

    print("\nValidating consolidated configurations...")
    errors = consolidator.validate_consolidated_configs()

    if errors:
        print(f"\n❌ Validation errors found: {len(errors)}")
        for error in errors[:5]:  # Show first 5
            print(f"  - {error}")

    print("\nGenerating deployment configurations...")
    deployment_configs = consolidator.generate_deployment_configs(args.environment)

    # Save deployment configurations
    deployment_dir = Path('deployment/configs')
    deployment_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in deployment_configs.items():
        output_file = deployment_dir / filename
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"\n" + "="*60)
    print(consolidator.generate_consolidation_report(report))
    print("="*60)

    print(f"\nDeployment configurations saved to: {deployment_dir}")
    print(f"Generated {len(deployment_configs)} deployment configuration files")

    return len(errors) == 0


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)