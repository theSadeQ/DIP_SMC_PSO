#!/usr/bin/env python3

"""
Task 2 — Phase 2: Template Normalization

Systematically applies standardized RST templates to all API documentation files,
analyzing source code to fill placeholders with real values.

Usage:
    python3 scripts/task2_phase2_normalize.py [--dry-run]
"""

from __future__ import annotations
import argparse
import ast
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import importlib.util
import sys

# Find project root dynamically
current = Path(__file__).resolve()
repo_root = None
for parent in current.parents:
    if (parent / "dip_docs" / "docs" / "source" / "api").exists():
        repo_root = parent
        break
if not repo_root:
    raise SystemExit("ERROR: Could not locate DIP_SMC_PSO project root")

REPO_ROOT = repo_root
API_ROOT = REPO_ROOT / "dip_docs" / "docs" / "source" / "api"
SRC_ROOT = REPO_ROOT / "src"

# Add src to Python path for imports
sys.path.insert(0, str(SRC_ROOT))

TEMPLATE = """\
========================
{title}
========================
.. currentmodule:: {module_path}

Overview
--------
{overview}

Examples
--------
.. doctest::

{examples}

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   {module_path}

Detailed API
------------
.. automodule:: {module_path}
   :members:
   :undoc-members:
   :show-inheritance:
"""

def analyze_python_module(py_path: Path) -> Dict[str, any]:
    """Analyze a Python module to extract documentation metadata."""
    try:
        with open(py_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse AST to find functions, classes, and docstrings
        tree = ast.parse(content)

        # Extract module docstring
        module_docstring = ast.get_docstring(tree)

        # Find main functions and classes
        functions = []
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
                classes.append(node.name)

        return {
            'docstring': module_docstring or '',
            'functions': functions,
            'classes': classes,
            'all_exports': getattr(tree, '__all__', functions + classes)
        }
    except Exception as e:
        print(f"Warning: Could not analyze {py_path}: {e}")
        return {
            'docstring': '',
            'functions': [],
            'classes': [],
            'all_exports': []
        }

def generate_title(module_name: str) -> str:
    """Generate a readable title from module name."""
    # Convert snake_case to Title Case
    return ' '.join(word.capitalize() for word in module_name.split('_'))

def generate_overview(module_info: Dict[str, any], module_name: str) -> str:
    """Generate overview from module docstring or infer from analysis."""
    docstring = module_info['docstring']

    if docstring:
        # Extract first paragraph as overview
        lines = docstring.strip().split('\n\n')
        return lines[0].replace('\n', ' ').strip()

    # Fallback: infer from functions/classes
    functions = module_info['functions']
    classes = module_info['classes']

    if classes:
        return f"This module provides the {', '.join(classes)} class{'es' if len(classes) > 1 else ''} for {module_name.replace('_', ' ')} functionality."
    elif functions:
        return f"This module provides utilities for {module_name.replace('_', ' ')}, including the {', '.join(functions[:3])} function{'s' if len(functions) > 1 else ''}."
    else:
        return f"This module contains {module_name.replace('_', ' ')} implementation."

def generate_examples(module_info: Dict[str, any], module_path: str) -> str:
    """Generate working examples based on module analysis."""
    functions = module_info['functions']
    classes = module_info['classes']

    if not functions and not classes:
        return "   >>> # See module documentation for usage examples"

    examples = []
    examples.append(f"   >>> from {module_path} import *")

    # Add simple examples based on common patterns
    if 'factory' in module_path.lower():
        examples.append("   >>> # Create controller instances using factory methods")
        if 'create_controller' in functions:
            examples.append("   >>> controller = create_controller('classical_smc')")
    elif 'smc' in module_path.lower():
        examples.append("   >>> # Initialize SMC controller with default parameters")
        if classes:
            examples.append(f"   >>> controller = {classes[0]}()")
    elif 'dynamics' in module_path.lower():
        examples.append("   >>> import numpy as np")
        examples.append("   >>> # Example state vector for dynamics computation")
        examples.append("   >>> state = np.array([0.1, 0.0, 0.1, 0.0])  # [theta1, omega1, theta2, omega2]")
    elif 'utils' in module_path.lower():
        examples.append("   >>> # Utility functions for analysis and computation")

    return '\n'.join(examples)

def get_module_mapping() -> List[Tuple[Path, str]]:
    """Get mapping of RST files to their Python module paths."""
    mappings = []

    # Find all RST files (excluding index files)
    for rst_file in API_ROOT.rglob("*.rst"):
        if rst_file.name == "index.rst":
            continue

        # Determine module path from RST file location
        rel_path = rst_file.relative_to(API_ROOT)

        # Convert path to module path: core/adaptive_integrator.rst -> src.core.adaptive_integrator
        parts = list(rel_path.parts[:-1]) + [rel_path.stem]  # Remove .rst extension
        module_path = "src." + ".".join(parts)

        mappings.append((rst_file, module_path))

    return mappings

def normalize_rst_file(rst_path: Path, module_path: str, dry_run: bool) -> bool:
    """Normalize a single RST file using the standard template."""

    # Convert module path to Python file path
    py_parts = module_path.split('.')[1:]  # Remove 'src' prefix
    py_path = SRC_ROOT / '/'.join(py_parts[:-1]) / f"{py_parts[-1]}.py"

    # Special case for logging_config.py (in src root)
    if py_parts[-1] == "logging_config":
        py_path = SRC_ROOT / "logging_config.py"

    if not py_path.exists():
        print(f"Warning: Python file not found: {py_path}")
        return False

    # Analyze Python module
    module_info = analyze_python_module(py_path)

    # Generate template content
    title = generate_title(py_parts[-1])
    overview = generate_overview(module_info, py_parts[-1])
    examples = generate_examples(module_info, module_path)

    content = TEMPLATE.format(
        title=title,
        module_path=module_path,
        overview=overview,
        examples=examples
    )

    if dry_run:
        print(f"[dry] Would normalize {rst_path}")
        print(f"      Title: {title}")
        print(f"      Module: {module_path}")
        print(f"      Python: {py_path}")
        return True
    else:
        rst_path.write_text(content, encoding='utf-8')
        print(f"Normalized: {rst_path.relative_to(API_ROOT)}")
        return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without modifying files")
    args = parser.parse_args()

    print(f"Project root: {REPO_ROOT}")
    print(f"Source root: {SRC_ROOT}")
    print(f"API root: {API_ROOT}")

    # Get all RST to module mappings
    mappings = get_module_mapping()

    print(f"\nFound {len(mappings)} RST files to normalize:")

    success_count = 0
    for rst_path, module_path in mappings:
        if normalize_rst_file(rst_path, module_path, args.dry_run):
            success_count += 1

    print(f"\n== Phase 2 Summary ==")
    print(f"Templates processed: {success_count}/{len(mappings)}")

    if not args.dry_run:
        print("All RST files have been normalized with the standard template.")
        print("Next: Run 'sphinx-build' to test the documentation build.")

if __name__ == "__main__":
    main()