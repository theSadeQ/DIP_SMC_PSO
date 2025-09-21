#!/usr/bin/env python3
"""
Fix RST title formatting across all documentation files.

This script fixes overline/underline length mismatches in RST files
by making them exactly match the title length.
"""

import os
from pathlib import Path
from typing import List

def fix_rst_title_formatting(rst_file: Path) -> bool:
    """Fix title formatting in a single RST file.

    Returns True if file was modified, False otherwise.
    """
    try:
        content = rst_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        if len(lines) < 3:
            return False

        # Check for full format: overline + title + underline
        if (lines[0].strip() and all(c == '=' for c in lines[0].strip()) and
            lines[2].strip() and all(c == '=' for c in lines[2].strip())):

            title_line = lines[1]
            title_length = len(title_line)

            # Check if lengths already match
            if len(lines[0]) == title_length and len(lines[2]) == title_length:
                return False

            # Fix the overline and underline lengths
            lines[0] = '=' * title_length
            lines[2] = '=' * title_length

            # Write back the fixed content
            fixed_content = '\n'.join(lines)
            rst_file.write_text(fixed_content, encoding='utf-8')

            print(f"Fixed: {rst_file.relative_to(Path.cwd())}")
            print(f"  Title: '{title_line}' ({title_length} chars)")
            print(f"  Overline/Underline: {'=' * title_length}")
            return True

    except Exception as e:
        print(f"Error processing {rst_file}: {e}")

    return False

def main():
    """Fix RST formatting across all documentation files."""
    print("FIXING RST TITLE FORMATTING")
    print("=" * 50)

    api_dir = Path("dip_docs/docs/source/api")
    if not api_dir.exists():
        print(f"Error: API documentation directory not found: {api_dir}")
        return

    fixed_files = 0
    total_files = 0

    for rst_file in api_dir.rglob("*.rst"):
        if rst_file.name == "index.rst":
            continue

        total_files += 1
        if fix_rst_title_formatting(rst_file):
            fixed_files += 1

    print(f"\nSummary:")
    print(f"  Total RST files: {total_files}")
    print(f"  Fixed files: {fixed_files}")
    print(f"  Already correct: {total_files - fixed_files}")

if __name__ == "__main__":
    main()