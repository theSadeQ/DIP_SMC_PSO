#!/usr/bin/env python3
"""
Documentation Coverage Audit for Task 2
=========================================

Analyzes Python modules vs RST documentation files to identify gaps.
"""

import os
from pathlib import Path
from typing import Set, Dict, List, Tuple

def get_python_modules(src_dir: Path) -> Set[str]:
    """Get all Python modules in src directory."""
    modules = set()
    for py_file in src_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        # Convert path to module notation
        rel_path = py_file.relative_to(src_dir)
        module_path = str(rel_path.with_suffix("")).replace(os.sep, ".")
        modules.add(f"src.{module_path}")
    return modules

def get_documented_modules(api_dir: Path) -> Set[str]:
    """Get all modules with RST documentation."""
    modules = set()
    for rst_file in api_dir.rglob("*.rst"):
        if rst_file.name == "index.rst":
            continue

        # Try to extract module path from RST file
        try:
            content = rst_file.read_text(encoding='utf-8')
            for line in content.split('\n'):
                if line.startswith(".. currentmodule::"):
                    module = line.split("::")[-1].strip()
                    modules.add(module)
                    break
        except Exception as e:
            print(f"Error reading {rst_file}: {e}")

    return modules

def analyze_coverage() -> Dict[str, List[str]]:
    """Analyze documentation coverage."""
    src_dir = Path("src")
    api_dir = Path("dip_docs/docs/source/api")

    python_modules = get_python_modules(src_dir)
    documented_modules = get_documented_modules(api_dir)

    # Find missing documentation
    missing_docs = python_modules - documented_modules

    # Find orphaned documentation
    orphaned_docs = documented_modules - python_modules

    # Get complete coverage
    total_modules = len(python_modules)
    documented_count = len(documented_modules & python_modules)
    coverage_percent = (documented_count / total_modules) * 100 if total_modules > 0 else 0

    return {
        "python_modules": sorted(list(python_modules)),
        "documented_modules": sorted(list(documented_modules)),
        "missing_docs": sorted(list(missing_docs)),
        "orphaned_docs": sorted(list(orphaned_docs)),
        "coverage_stats": {
            "total_modules": total_modules,
            "documented_modules": documented_count,
            "coverage_percent": coverage_percent
        }
    }

def main():
    """Run coverage audit."""
    print("DOCUMENTATION COVERAGE AUDIT")
    print("=" * 50)

    results = analyze_coverage()

    print(f"\nCoverage Statistics:")
    stats = results["coverage_stats"]
    print(f"   Total Python modules: {stats['total_modules']}")
    print(f"   Documented modules: {stats['documented_modules']}")
    print(f"   Coverage: {stats['coverage_percent']:.1f}%")

    if results["missing_docs"]:
        print(f"\nMissing Documentation ({len(results['missing_docs'])} modules):")
        for module in results["missing_docs"]:
            print(f"   - {module}")

    if results["orphaned_docs"]:
        print(f"\nOrphaned Documentation ({len(results['orphaned_docs'])} files):")
        for module in results["orphaned_docs"]:
            print(f"   - {module}")

    if not results["missing_docs"] and not results["orphaned_docs"]:
        print("\nPerfect documentation coverage!")

    return results

if __name__ == "__main__":
    main()