#!/usr/bin/env python3

"""
Task 2 — Phase 1: Structural Reorganization

Reorganize flat RST files under dip_docs/docs/source/api/ into a 6‑directory layout.

Usage:
    python3 scripts/task2_phase1_reorg.py [--dry-run]

What it does:
  - Creates: core/, controllers/, optimizer/, benchmarks/, fault_detection/, utils/
  - Moves *.rst files like "core.adaptive_integrator.rst" -> "core/adaptive_integrator.rst"
  - Updates top-level index.rst and per-subdir index.rst files
  - Leaves unknown files untouched, but reports them

This script is idempotent: running multiple times keeps the final structure intact.
"""

from __future__ import annotations
import argparse
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Find the DIP_SMC_PSO directory dynamically
current = Path(__file__).resolve()
repo_root = None
for parent in current.parents:
    if (parent / "dip_docs" / "docs" / "source" / "api").exists():
        repo_root = parent
        break
if not repo_root:
    raise SystemExit("ERROR: Could not locate DIP_SMC_PSO project root with dip_docs/docs/source/api/")

REPO_ROOT = repo_root
API_ROOT = REPO_ROOT / "dip_docs" / "docs" / "source" / "api"

SUBDIRS = ["core", "controllers", "optimizer", "benchmarks", "fault_detection", "utils"]
KNOWN_PREFIXES = {
    "core.": "core",
    "controllers.": "controllers",
    "optimizer.": "optimizer",
    "benchmarks.": "benchmarks",
    "fault_detection.": "fault_detection",
    "utils.": "utils",
}
SPECIAL_FILES = {
    "logging_config.rst": "utils",
}

TOP_INDEX_TEMPLATE = """\
=================
API Documentation
=================

.. toctree::
   :maxdepth: 2

   core/index
   controllers/index
   optimizer/index
   benchmarks/index
   fault_detection/index
   utils/index
"""

SUBDIR_INDEX_TEMPLATE = """\
=========================
{title}
=========================

.. toctree::
   :maxdepth: 1
{entries}
"""

def _title_for_dir(d: str) -> str:
    return {
        "core": "Core",
        "controllers": "Controllers",
        "optimizer": "Optimizer",
        "benchmarks": "Benchmarks",
        "fault_detection": "Fault Detection",
        "utils": "Utilities",
    }.get(d, d.capitalize())

def discover_flat_files(api_root: Path) -> List[Path]:
    return sorted([p for p in api_root.glob("*.rst") if p.name != "index.rst"])

def ensure_subdirs(api_root: Path, dry: bool) -> None:
    for d in SUBDIRS:
        p = api_root / d
        if not p.exists():
            if dry:
                print(f"[dry] mkdir -p {p}")
            else:
                p.mkdir(parents=True, exist_ok=True)

def move_file(src: Path, dest: Path, dry: bool) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dry:
        print(f"[dry] mv {src} -> {dest}")
    else:
        src.rename(dest)

def reorg_files(api_root: Path, dry: bool) -> Tuple[List[Path], List[Tuple[Path, Path]], List[Path]]:
    """
    Returns:
      - moved: list of destination paths actually moved
      - actions: list of (src, dest) planned
      - unknown: files left untouched
    """
    flat = discover_flat_files(api_root)
    actions: List[Tuple[Path, Path]] = []
    moved: List[Path] = []
    unknown: List[Path] = []

    for f in flat:
        # special cases
        if f.name in SPECIAL_FILES:
            sub = SPECIAL_FILES[f.name]
            dest = api_root / sub / f.name
            actions.append((f, dest))
            continue

        matched = False
        for prefix, sub in KNOWN_PREFIXES.items():
            if f.name.startswith(prefix) and f.suffix == ".rst":
                stem = f.stem[len(prefix):]  # remove e.g. "core." -> "adaptive_integrator"
                dest = api_root / sub / (stem + ".rst")
                actions.append((f, dest))
                matched = True
                break
        if not matched:
            unknown.append(f)

    # Execute
    for src, dest in actions:
        # If source and dest are same (already reorganized), skip
        if src.resolve() == dest.resolve():
            continue
        if not dest.exists():
            move_file(src, dest, dry)
            moved.append(dest)
        else:
            # If dest exists and src exists, prefer keeping dest; remove src if duplicate content
            try:
                if src.read_text(encoding="utf-8") == dest.read_text(encoding="utf-8"):
                    if dry:
                        print(f"[dry] rm (duplicate) {src}")
                    else:
                        src.unlink()
                else:
                    # Conflict: keep both by appending suffix
                    alt = dest.with_stem(dest.stem + "_DUPLICATE")
                    if dry:
                        print(f"[dry] mv (conflict) {src} -> {alt}")
                    else:
                        src.rename(alt)
                        moved.append(alt)
            except Exception:
                # Fallback: do a simple rename with suffix
                alt = dest.with_stem(dest.stem + "_MOVED")
                if dry:
                    print(f"[dry] mv (fallback) {src} -> {alt}")
                else:
                    src.rename(alt)
                    moved.append(alt)

    return moved, actions, unknown

def write_top_index(api_root: Path, dry: bool) -> None:
    idx = api_root / "index.rst"
    content = TOP_INDEX_TEMPLATE
    if dry:
        print(f"[dry] write {idx}")
    else:
        idx.write_text(content, encoding="utf-8")

def write_subdir_indexes(api_root: Path, dry: bool) -> Dict[str, List[str]]:
    summary: Dict[str, List[str]] = {}
    for sub in SUBDIRS:
        subdir = api_root / sub
        entries: List[str] = []
        for p in sorted(subdir.glob("*.rst")):
            if p.name == "index.rst":
                continue
            # strip extension and subdir; Sphinx expects relative paths
            rel = p.with_suffix("").name
            entries.append(f"   {rel}")
        summary[sub] = entries
        title = _title_for_dir(sub)
        content = SUBDIR_INDEX_TEMPLATE.format(title=title, entries="\n".join(entries) if entries else "   (none yet)")
        idx = subdir / "index.rst"
        if dry:
            print(f"[dry] write {idx} with {len(entries)} entries")
        else:
            idx.write_text(content, encoding="utf-8")
    return summary

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Preview actions without modifying files")
    args = ap.parse_args()

    print(f"Located project root: {REPO_ROOT}")
    print(f"API documentation root: {API_ROOT}")

    if not API_ROOT.exists():
        raise SystemExit(f"ERROR: expected path not found: {API_ROOT}")

    ensure_subdirs(API_ROOT, dry=args.dry_run)
    moved, actions, unknown = reorg_files(API_ROOT, dry=args.dry_run)
    write_top_index(API_ROOT, dry=args.dry_run)
    summary = write_subdir_indexes(API_ROOT, dry=args.dry_run)

    print("\n== Phase 1 Summary ==")
    print(f"API root: {API_ROOT}")
    print(f"Moved/renamed files: {len(actions)} planned; {len(moved)} applied")
    print(f"Unknown (left in place): {len(unknown)}")
    for u in unknown:
        print(f"  - {u.name}")
    print("\nSubdir inventories:")
    for sub, entries in summary.items():
        print(f"  {sub}/ ({len(entries)} files)")

if __name__ == "__main__":
    main()