#!/usr/bin/env python3
"""
Script to replace numbered citations with Sphinx bibtex citations.
This replaces patterns like [1] or [\[1\]](URL) with :cite:`key` format.
"""

import json
import re
import os
from pathlib import Path

def load_citation_mapping(mapping_file):
    """Load citation number to key mapping from JSON file."""
    with open(mapping_file, 'r') as f:
        return json.load(f)

def replace_citations_in_text(text, citation_map):
    """Replace numbered citations with Sphinx citation format."""
    # Pattern 1: [\[1\]](URL) format (markdown links)
    def replace_markdown_citation(match):
        num = match.group(1)
        if num in citation_map:
            return f":cite:`{citation_map[num]}`"
        else:
            return match.group(0)  # Keep original if no mapping

    # Pattern 2: [1] format (simple brackets)
    def replace_simple_citation(match):
        num = match.group(1)
        if num in citation_map:
            return f":cite:`{citation_map[num]}`"
        else:
            return match.group(0)  # Keep original if no mapping

    # First replace markdown-style citations with links
    text = re.sub(r'\[\\\[(\d+)\\\]\]\([^)]+\)', replace_markdown_citation, text)

    # Then replace simple bracket citations
    # Use a two-pass approach to avoid conflicts
    text = re.sub(r'\[(\d+)\]', replace_simple_citation, text)

    return text

def add_bibliography_section(text, file_path):
    """Add bibliography section to the end of the file if citations are present."""
    if ':cite:`' in text and '.. bibliography::' not in text and '## References' not in text:
        # For markdown files, add markdown-style references section
        if file_path.suffix == '.md':
            if not text.rstrip().endswith('\n'):
                text += '\n'
            text += '\n## References\n\n*Bibliography will be generated automatically by Sphinx.*\n'
        # For RST files, add proper bibliography directive
        elif file_path.suffix == '.rst':
            if not text.rstrip().endswith('\n'):
                text += '\n'
            text += '\n.. rubric:: References\n\n.. bibliography::\n'

    return text

def process_file(file_path, citation_map, dry_run=False):
    """Process a single file to replace citations."""
    print(f"Processing: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_text = f.read()
    except UnicodeDecodeError:
        print(f"  Skipping {file_path} (encoding issue)")
        return
    except Exception as e:
        print(f"  Error reading {file_path}: {e}")
        return

    # Replace citations
    modified_text = replace_citations_in_text(original_text, citation_map)

    # Add bibliography section if needed
    modified_text = add_bibliography_section(modified_text, file_path)

    # Check if changes were made
    if original_text != modified_text:
        print(f"  ✓ Citations found and replaced")

        if not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_text)
                print(f"  ✓ File updated")
            except Exception as e:
                print(f"  Error writing {file_path}: {e}")
        else:
            print(f"  ✓ Would update file (dry run)")
    else:
        # Check if there are any numbered patterns to help debug
        import re
        numbered_citations = re.findall(r'\[(\d+)\]', original_text)
        if numbered_citations:
            print(f"  - Found numbered patterns {numbered_citations} but no mappings")
        else:
            print(f"  - No citations to replace")

def main():
    """Main function to process all documentation files."""
    # Get script directory and project root
    script_dir = Path(__file__).parent
    citation_map_file = script_dir / 'citation_map.json'

    # Load citation mapping
    if not citation_map_file.exists():
        print(f"Error: Citation mapping file not found: {citation_map_file}")
        return

    citation_map = load_citation_mapping(citation_map_file)
    print(f"Loaded citation mapping with {len(citation_map)} entries")

    # Find all documentation files
    docs_dir = script_dir
    file_patterns = ['**/*.md', '**/*.rst']

    files_to_process = []
    for pattern in file_patterns:
        files_to_process.extend(docs_dir.glob(pattern))

    # Filter out build directories and other unwanted paths
    exclude_patterns = ['_build', '.git', '__pycache__', '.pytest_cache']
    files_to_process = [
        f for f in files_to_process
        if not any(exclude in str(f) for exclude in exclude_patterns)
    ]

    print(f"Found {len(files_to_process)} documentation files to process")

    # Process files
    for file_path in sorted(files_to_process):
        try:
            process_file(file_path, citation_map, dry_run=False)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    print("\nCitation replacement completed!")
    print("\nNext steps:")
    print("1. Review the changes with 'git diff'")
    print("2. Build documentation with 'sphinx-build -b html docs docs/_build/html'")
    print("3. Check that all citations resolve correctly")

if __name__ == '__main__':
    main()