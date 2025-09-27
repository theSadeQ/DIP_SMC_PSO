"""Scan files for non-printable/undesired control characters.

Targets docs/*.md and docs/**/*.py by default (configurable via CLI args).
Fails with exit(1) if any offending characters are found.
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path


FORBIDDEN = {
    0x00,  # NUL
    0x0b,  # VT
    0x0c,  # FF
    0x7f,  # DEL
    0x200b,  # ZERO WIDTH SPACE
    0x200c,  # ZERO WIDTH NON-JOINER
    0x200d,  # ZERO WIDTH JOINER
    0xfeff,  # BOM
}


def scan_file(path: Path) -> list[tuple[int, int, str]]:
    issues: list[tuple[int, int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return [(0, 0, f"cannot decode: {e}")]
    for ln, line in enumerate(text.splitlines(), start=1):
        for col, ch in enumerate(line, start=1):
            cp = ord(ch)
            if cp in FORBIDDEN:
                issues.append((ln, col, f"U+{cp:04X}"))
            # flag other C0 controls except TAB (0x09) and LF/CR handled by splitlines
            if 0x00 <= cp < 0x20 and cp not in {0x09}:
                issues.append((ln, col, f"C0 U+{cp:04X}"))
    return issues


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=["docs"], help="paths to scan")
    args = ap.parse_args(argv)

    offenders = 0
    roots = [Path(p) for p in args.paths]
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if not any(path.suffix.lower() == s for s in (".md", ".py")):
                continue
            issues = scan_file(path)
            if issues:
                offenders += 1
                print(f"[encoding] {path} has {len(issues)} issue(s):")
                for ln, col, what in issues[:10]:
                    print(f"  - line {ln}, col {col}: {what}")
                if len(issues) > 10:
                    print(f"  ... and {len(issues) - 10} more")

    if offenders:
        print(f"Found {offenders} file(s) with encoding/control character issues.")
        return 1
    print("No encoding issues found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

