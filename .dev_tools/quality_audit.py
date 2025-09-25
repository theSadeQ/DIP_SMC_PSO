#!/usr/bin/env python3
"""
Documentation Quality Audit for Task 2
=======================================

Checks for template compliance, example quality, and import path validity.
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple

def check_example_quality(rst_file: Path) -> List[str]:
    """Check if examples demonstrate actual function usage."""
    issues = []
    try:
        content = rst_file.read_text(encoding='utf-8')

        # Look for the Examples section
        if ".. doctest::" in content:
            # Extract example code
            doctest_start = content.find(".. doctest::")
            if doctest_start != -1:
                example_section = content[doctest_start:content.find("\nAPI Summary", doctest_start)]

                # Check for weak examples
                if "from" in example_section and "import *" in example_section:
                    if "# " in example_section and not any(func in example_section
                        for func in ["(", "=", "return", "print"]):
                        issues.append("Weak example: only imports without actual function usage")

                # Check for importlib usage
                if "importlib.util.find_spec" in example_section:
                    issues.append("Low-quality example: uses importlib instead of actual functions")

    except Exception as e:
        issues.append(f"Error reading file: {e}")

    return issues

def check_template_compliance(rst_file: Path) -> List[str]:
    """Check if RST file follows the approved template."""
    issues = []
    try:
        content = rst_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Check for required sections
        required_sections = [
            "Overview",
            "Examples",
            "API Summary",
            "Detailed API"
        ]

        for section in required_sections:
            if section not in content:
                issues.append(f"Missing required section: {section}")

        # Check for currentmodule directive
        if ".. currentmodule::" not in content:
            issues.append("Missing .. currentmodule:: directive")

        # Check for autosummary directive
        if ".. autosummary::" not in content:
            issues.append("Missing .. autosummary:: directive")

        # Check for automodule directive
        if ".. automodule::" not in content:
            issues.append("Missing .. automodule:: directive")

        # Check title formatting - support both simple and full RST title formats
        if len(lines) >= 2:
            # Check for full format: overline + title + underline
            if (len(lines) >= 3 and
                lines[0].strip() and all(c == '=' for c in lines[0].strip()) and
                lines[2].strip() and all(c == '=' for c in lines[2].strip())):
                # Full format: check overline and underline match title length
                title_line = lines[1]
                overline = lines[0]
                underline = lines[2]
                if len(overline) != len(title_line) or len(underline) != len(title_line):
                    issues.append("Title overline/underline length doesn't match title")
            # Check for simple format: title + underline
            elif lines[1].strip() and all(c == '=' for c in lines[1].strip()):
                # Simple format: title on line 0, underline on line 1
                title_line = lines[0]
                underline = lines[1]
                if len(underline) != len(title_line):
                    issues.append("Title underline length doesn't match title")
            else:
                # Neither format detected
                issues.append("Invalid title formatting - should use RST title format with '=' characters")

    except Exception as e:
        issues.append(f"Error reading file: {e}")

    return issues

def check_module_paths(rst_file: Path) -> List[str]:
    """Check if module paths in RST files are valid."""
    issues = []
    try:
        content = rst_file.read_text(encoding='utf-8')

        # Extract module path from currentmodule directive
        for line in content.split('\n'):
            if line.startswith(".. currentmodule::"):
                module_path = line.split("::")[-1].strip()

                # Convert to file path and check if it exists
                file_path = Path(module_path.replace(".", "/") + ".py")
                if not file_path.exists():
                    issues.append(f"Module path does not exist: {module_path} -> {file_path}")
                break
        else:
            issues.append("No currentmodule directive found")

    except Exception as e:
        issues.append(f"Error reading file: {e}")

    return issues

def analyze_quality() -> Dict[str, List[Tuple[str, List[str]]]]:
    """Analyze documentation quality across all RST files."""
    api_dir = Path("dip_docs/docs/source/api")
    results = {
        "example_quality": [],
        "template_compliance": [],
        "module_paths": []
    }

    for rst_file in api_dir.rglob("*.rst"):
        if rst_file.name == "index.rst":
            continue

        rel_path = str(rst_file.relative_to(api_dir))

        # Check example quality
        example_issues = check_example_quality(rst_file)
        if example_issues:
            results["example_quality"].append((rel_path, example_issues))

        # Check template compliance
        template_issues = check_template_compliance(rst_file)
        if template_issues:
            results["template_compliance"].append((rel_path, template_issues))

        # Check module paths
        path_issues = check_module_paths(rst_file)
        if path_issues:
            results["module_paths"].append((rel_path, path_issues))

    return results

def main():
    """Run quality audit."""
    print("DOCUMENTATION QUALITY AUDIT")
    print("=" * 50)

    results = analyze_quality()

    total_issues = sum(len(category) for category in results.values())

    if total_issues == 0:
        print("\nPerfect documentation quality!")
        return results

    print(f"\nFound {total_issues} categories with issues:")

    # Report example quality issues
    if results["example_quality"]:
        print(f"\nExample Quality Issues ({len(results['example_quality'])} files):")
        for file_path, issues in results["example_quality"]:
            print(f"   {file_path}:")
            for issue in issues:
                print(f"     - {issue}")

    # Report template compliance issues
    if results["template_compliance"]:
        print(f"\nTemplate Compliance Issues ({len(results['template_compliance'])} files):")
        for file_path, issues in results["template_compliance"]:
            print(f"   {file_path}:")
            for issue in issues:
                print(f"     - {issue}")

    # Report module path issues
    if results["module_paths"]:
        print(f"\nModule Path Issues ({len(results['module_paths'])} files):")
        for file_path, issues in results["module_paths"]:
            print(f"   {file_path}:")
            for issue in issues:
                print(f"     - {issue}")

    return results

if __name__ == "__main__":
    main()