#==========================================================================================\\\
#================================== scripts/check_citations.py ===========================\\\
#==========================================================================================\\\

"""Citation health checker for Sphinx documentation.

This script validates that:
1. All cited keys exist in bibliography files
2. No duplicate keys exist across bibliography files
3. Citation formatting is consistent
"""

import argparse
import glob
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

try:
    import pybtex.database
except ImportError:
    print("Error: pybtex not installed. Run: pip install pybtex")
    sys.exit(1)


def find_bib_files(docs_dir: Path) -> List[Path]:
    """Find all .bib files in the documentation directory."""
    return list(docs_dir.glob("**/*.bib"))


def find_citation_keys_in_bib(bib_file: Path) -> Set[str]:
    """Extract all citation keys from a BibTeX file."""
    try:
        bib_data = pybtex.database.parse_file(str(bib_file))
        return set(bib_data.entries.keys())
    except Exception as e:
        print(f"Error parsing {bib_file}: {e}")
        return set()


def find_citations_in_markdown(md_file: Path) -> Set[str]:
    """Find all citation keys used in a Markdown file."""
    content = md_file.read_text(encoding='utf-8')

    # MyST citation patterns
    myst_citations = re.findall(r'\{cite[^}]*\}`([^`]+)`', content)

    # Extract individual keys (handle multiple keys like {cite}`key1,key2`)
    all_keys = set()
    for citation in myst_citations:
        keys = [key.strip() for key in citation.split(',')]
        all_keys.update(keys)

    return all_keys


def check_duplicate_keys(bib_files: List[Path]) -> Dict[str, List[Path]]:
    """Check for duplicate citation keys across bibliography files."""
    key_to_files = {}

    for bib_file in bib_files:
        keys = find_citation_keys_in_bib(bib_file)
        for key in keys:
            if key not in key_to_files:
                key_to_files[key] = []
            key_to_files[key].append(bib_file)

    # Return only duplicates
    return {key: files for key, files in key_to_files.items() if len(files) > 1}


def check_missing_citations(docs_dir: Path, bib_files: List[Path]) -> Dict[str, List[str]]:
    """Check for citations that don't exist in any bibliography file."""
    # Collect all available keys
    all_bib_keys = set()
    for bib_file in bib_files:
        all_bib_keys.update(find_citation_keys_in_bib(bib_file))

    # Find all citations in markdown files
    missing_citations = {}
    md_files = list(docs_dir.glob("**/*.md"))

    for md_file in md_files:
        cited_keys = find_citations_in_markdown(md_file)
        missing_keys = cited_keys - all_bib_keys

        if missing_keys:
            missing_citations[str(md_file.relative_to(docs_dir))] = sorted(missing_keys)

    return missing_citations


def validate_bib_format(bib_files: List[Path]) -> List[str]:
    """Validate BibTeX file formatting and required fields."""
    issues = []

    for bib_file in bib_files:
        try:
            bib_data = pybtex.database.parse_file(str(bib_file))

            for key, entry in bib_data.entries.items():
                # Check for required fields based on entry type
                if entry.type.lower() == 'article':
                    required_fields = {'author', 'title', 'journal', 'year'}
                elif entry.type.lower() == 'book':
                    required_fields = {'author', 'title', 'publisher', 'year'}
                elif entry.type.lower() == 'software':
                    required_fields = {'author', 'title', 'year', 'url'}
                else:
                    continue  # Skip unknown types

                missing_fields = required_fields - set(entry.fields.keys())
                if missing_fields:
                    issues.append(
                        f"{bib_file.name}: Entry '{key}' missing fields: {', '.join(missing_fields)}"
                    )

                # Check for recommended fields
                if 'doi' not in entry.fields and 'url' not in entry.fields:
                    issues.append(
                        f"{bib_file.name}: Entry '{key}' has no DOI or URL"
                    )

        except Exception as e:
            issues.append(f"{bib_file.name}: Parse error - {e}")

    return issues


def main():
    parser = argparse.ArgumentParser(description='Check citation health in Sphinx docs')
    parser.add_argument('docs_dir', nargs='?', default='docs',
                       help='Documentation directory (default: docs)')
    parser.add_argument('--fail-on-missing', action='store_true',
                       help='Exit with error code if missing citations found')
    parser.add_argument('--fail-on-duplicates', action='store_true',
                       help='Exit with error code if duplicate keys found')
    parser.add_argument('--fail-on-format', action='store_true',
                       help='Exit with error code if format issues found')

    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    if not docs_dir.exists():
        print(f"Error: Documentation directory '{docs_dir}' not found")
        sys.exit(1)

    print(f"Checking citations in {docs_dir}")

    # Find bibliography files
    bib_files = find_bib_files(docs_dir)
    if not bib_files:
        print("Warning: No .bib files found")
        return

    print(f"Found {len(bib_files)} bibliography files:")
    for bib_file in bib_files:
        print(f"  - {bib_file.relative_to(docs_dir)}")

    exit_code = 0

    # Check for duplicate keys
    print("\n=== Checking for duplicate citation keys ===")
    duplicates = check_duplicate_keys(bib_files)
    if duplicates:
        print(f"Found {len(duplicates)} duplicate keys:")
        for key, files in duplicates.items():
            file_names = [f.name for f in files]
            print(f"  - '{key}' in: {', '.join(file_names)}")
        if args.fail_on_duplicates:
            exit_code = 1
    else:
        print("✓ No duplicate keys found")

    # Check for missing citations
    print("\n=== Checking for missing citations ===")
    missing = check_missing_citations(docs_dir, bib_files)
    if missing:
        print(f"Found missing citations in {len(missing)} files:")
        for file_path, missing_keys in missing.items():
            print(f"  - {file_path}: {', '.join(missing_keys)}")
        if args.fail_on_missing:
            exit_code = 1
    else:
        print("✓ All citations have corresponding bibliography entries")

    # Check bibliography formatting
    print("\n=== Checking bibliography formatting ===")
    format_issues = validate_bib_format(bib_files)
    if format_issues:
        print(f"Found {len(format_issues)} formatting issues:")
        for issue in format_issues:
            print(f"  - {issue}")
        if args.fail_on_format:
            exit_code = 1
    else:
        print("✓ All bibliography entries are properly formatted")

    # Summary
    total_keys = sum(len(find_citation_keys_in_bib(bib)) for bib in bib_files)
    print(f"\n=== Summary ===")
    print(f"Total bibliography entries: {total_keys}")
    print(f"Duplicate keys: {len(duplicates)}")
    print(f"Files with missing citations: {len(missing)}")
    print(f"Format issues: {len(format_issues)}")

    if exit_code == 0:
        print("✓ Citation health check passed")
    else:
        print("✗ Citation health check failed")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()