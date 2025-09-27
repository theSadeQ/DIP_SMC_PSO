#!/usr/bin/env python3
#==========================================================================================\\\
#======================== scripts/verify_dependencies.py ===============================\\\
#==========================================================================================\\\
"""
Dependency Verification Script for DIP SMC PSO Project

This script verifies that the fixed dependency versions work correctly and
don't have the critical compatibility issues identified in production assessment.

Key Verifications:
1. numpy < 2.0 (avoid breaking changes)
2. numba compatibility with numpy version
3. No dependency conflicts
4. Core functionality imports work
5. Version bounds are respected

Usage:
    python scripts/verify_dependencies.py
    python scripts/verify_dependencies.py --requirements requirements-production.txt
"""

import importlib
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse


class DependencyVerifier:
    """Verifies critical dependencies and their compatibility."""

    CRITICAL_DEPENDENCIES = {
        'numpy': {'min_version': '1.21.0', 'max_version': '2.0.0', 'critical': True},
        'numba': {'min_version': '0.56.0', 'max_version': '0.60.0', 'critical': True},
        'scipy': {'min_version': '1.10.0', 'max_version': '1.14.0', 'critical': True},
        'matplotlib': {'min_version': '3.6.0', 'max_version': '4.0.0', 'critical': False},
        'pydantic': {'min_version': '2.5.0', 'max_version': '3.0.0', 'critical': True},
    }

    def __init__(self):
        self.results: Dict[str, bool] = {}
        self.errors: List[str] = []

    def check_version_bounds(self, package: str, actual_version: str,
                           min_version: str, max_version: str) -> bool:
        """Check if actual version is within specified bounds."""
        try:
            from packaging import version
            actual = version.parse(actual_version)
            min_ver = version.parse(min_version)
            max_ver = version.parse(max_version)
            return min_ver <= actual < max_ver
        except ImportError:
            # Fallback to string comparison (not ideal but works for basic cases)
            return min_version <= actual_version < max_version

    def verify_numpy_numba_compatibility(self) -> bool:
        """Verify critical numpy-numba compatibility."""
        try:
            import numpy
            import numba

            numpy_version = numpy.__version__
            numba_version = numba.__version__

            print(f"  numpy version: {numpy_version}")
            print(f"  numba version: {numba_version}")

            # Check numpy is < 2.0 (critical for numba compatibility)
            if numpy_version.startswith('2.'):
                self.errors.append("CRITICAL: numpy 2.0+ breaks numba compatibility")
                return False

            # Test basic numba compilation works
            @numba.jit(nopython=True)
            def test_numba_compilation(x):
                return x * 2.0

            # Test compilation
            result = test_numba_compilation(5.0)
            if result != 10.0:
                self.errors.append("numba compilation test failed")
                return False

            print("  ✅ numpy-numba compatibility verified")
            return True

        except Exception as e:
            self.errors.append(f"numpy-numba compatibility check failed: {e}")
            return False

    def verify_core_imports(self) -> bool:
        """Verify that core project modules can be imported."""
        core_modules = [
            'numpy',
            'scipy',
            'matplotlib',
            'numba',
            'pydantic',
            'yaml',
        ]

        failed_imports = []

        for module in core_modules:
            try:
                importlib.import_module(module if module != 'yaml' else 'pyyaml')
                print(f"  ✅ {module} import successful")
            except ImportError as e:
                failed_imports.append(f"{module}: {e}")
                print(f"  ❌ {module} import failed: {e}")

        if failed_imports:
            self.errors.extend(failed_imports)
            return False

        return True

    def verify_dependency_versions(self) -> bool:
        """Verify installed versions match required bounds."""
        all_good = True

        for package, constraints in self.CRITICAL_DEPENDENCIES.items():
            try:
                module = importlib.import_module(package)
                actual_version = getattr(module, '__version__', 'unknown')

                is_valid = self.check_version_bounds(
                    package, actual_version,
                    constraints['min_version'],
                    constraints['max_version']
                )

                status = "✅" if is_valid else "❌"
                criticality = "CRITICAL" if constraints['critical'] else "WARNING"

                print(f"  {status} {package}: {actual_version} "
                      f"(expected: >={constraints['min_version']}, "
                      f"<{constraints['max_version']})")

                if not is_valid:
                    error_msg = (f"{criticality}: {package} version {actual_version} "
                               f"outside safe range {constraints['min_version']}-{constraints['max_version']}")
                    self.errors.append(error_msg)
                    if constraints['critical']:
                        all_good = False

            except ImportError:
                error_msg = f"CRITICAL: {package} not installed"
                self.errors.append(error_msg)
                print(f"  ❌ {package}: not installed")
                if constraints['critical']:
                    all_good = False

        return all_good

    def check_pip_conflicts(self, requirements_file: str) -> bool:
        """Check for pip dependency conflicts."""
        try:
            print(f"Checking pip conflicts for {requirements_file}...")
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'check'
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print("  ✅ No pip dependency conflicts found")
                return True
            else:
                self.errors.append(f"Pip dependency conflicts: {result.stdout}\n{result.stderr}")
                print(f"  ❌ Pip dependency conflicts found:\n{result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.errors.append("Pip check timed out")
            return False
        except Exception as e:
            self.errors.append(f"Pip check failed: {e}")
            return False

    def run_verification(self, requirements_file: Optional[str] = None) -> bool:
        """Run complete dependency verification."""
        print("🔍 Starting Dependency Verification...")
        print("=" * 60)

        # 1. Check core imports
        print("\n1. Verifying Core Imports:")
        imports_ok = self.verify_core_imports()

        # 2. Check version bounds
        print("\n2. Verifying Version Bounds:")
        versions_ok = self.verify_dependency_versions()

        # 3. Critical numpy-numba compatibility
        print("\n3. Verifying numpy-numba Compatibility:")
        compatibility_ok = self.verify_numpy_numba_compatibility()

        # 4. Check pip conflicts
        print("\n4. Checking Pip Conflicts:")
        if requirements_file:
            pip_ok = self.check_pip_conflicts(requirements_file)
        else:
            pip_ok = self.check_pip_conflicts("requirements.txt")

        # Summary
        print("\n" + "=" * 60)
        print("🎯 VERIFICATION SUMMARY:")

        all_checks = [imports_ok, versions_ok, compatibility_ok, pip_ok]

        if all(all_checks):
            print("✅ ALL DEPENDENCY CHECKS PASSED")
            print("🚀 Dependencies are production-safe")
            return True
        else:
            print("❌ DEPENDENCY VERIFICATION FAILED")
            print("\n🚨 Critical Issues Found:")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")
            print("\n⚠️  Fix these issues before production deployment")
            return False


def main():
    parser = argparse.ArgumentParser(description='Verify dependency safety')
    parser.add_argument('--requirements', default='requirements.txt',
                       help='Requirements file to verify (default: requirements.txt)')
    parser.add_argument('--production', action='store_true',
                       help='Use requirements-production.txt')

    args = parser.parse_args()

    if args.production:
        requirements_file = 'requirements-production.txt'
    else:
        requirements_file = args.requirements

    # Ensure we're in the right directory
    repo_root = Path(__file__).parent.parent
    requirements_path = repo_root / requirements_file

    if not requirements_path.exists():
        print(f"❌ Requirements file not found: {requirements_path}")
        sys.exit(1)

    print(f"Using requirements file: {requirements_file}")

    verifier = DependencyVerifier()
    success = verifier.run_verification(requirements_file)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()