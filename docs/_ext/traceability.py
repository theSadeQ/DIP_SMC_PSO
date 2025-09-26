"""Sphinx extension to generate a simple Requirements Traceability page.

Reads a CSV file at docs/traceability/requirements.csv and generates
docs/traceability/index.md with a Markdown table that links to code, tests,
and docs. Intended to stay fast and dependency-light.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Dict, List


def _csv_path(app) -> Path:
    return Path(app.confdir) / "traceability" / "requirements.csv"


def _output_path(app) -> Path:
    return Path(app.confdir) / "traceability" / "index.md"


def _get_commit_sha() -> str:
    # Reuse conf-provided helper when available
    try:
        from conf import _get_commit_sha as _g

        return _g()  # type: ignore[misc]
    except Exception:
        return os.getenv("GITHUB_SHA") or os.getenv("READTHEDOCS_GIT_IDENTIFIER") or "main"


def _github_base_url(app) -> str:
    user = getattr(app.config, "GITHUB_USER", None) or "theSadeQ"
    repo = getattr(app.config, "GITHUB_REPO", None) or "DIP_SMC_PSO"
    sha = _get_commit_sha()
    return f"https://github.com/{user}/{repo}/blob/{sha}/"


def _make_code_link(base: str, target: str) -> str:
    # Turn windows path separators into posix
    target = target.replace("\\", "/")
    return f"[{target}]({base}{target})"


def _read_rows(csv_path: Path) -> List[Dict[str, str]]:
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _render_table(rows: List[Dict[str, str]], base_url: str) -> str:
    headers = [
        "id",
        "description",
        "file",
        "symbol",
        "tests",
        "docs",
        "status",
        "owner",
        "verification",
        "last_verified",
    ]

    lines: List[str] = []
    lines.append("# Requirements Traceability")
    lines.append("")
    lines.append("This page is generated from `traceability/requirements.csv` during the Sphinx build.")
    lines.append("")
    # Markdown table header
    lines.append("| " + " | ".join(h.replace("_", " ").title() for h in headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in rows:
        file_cell = row.get("file", "").strip()
        symbol_cell = row.get("symbol", "").strip()

        link_cell = file_cell
        if file_cell:
            link_cell = _make_code_link(base_url, file_cell)
        tests_cell = row.get("tests", "").strip()
        docs_cell = row.get("docs", "").strip()

        values = [
            row.get("id", "").strip(),
            row.get("description", "").strip(),
            link_cell,
            symbol_cell,
            tests_cell,
            docs_cell,
            row.get("status", "").strip(),
            row.get("owner", "").strip(),
            row.get("verification", "").strip(),
            row.get("last_verified", "").strip(),
        ]
        lines.append("| " + " | ".join(values) + " |")

    lines.append("")
    return "\n".join(lines)


def _ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def on_builder_inited(app):
    csv_path = _csv_path(app)
    rows = _read_rows(csv_path)
    base_url = _github_base_url(app)
    content = _render_table(rows, base_url)

    out = _output_path(app)
    _ensure_dir(out)
    with out.open("w", encoding="utf-8") as f:
        f.write(content)


def setup(app):
    app.connect("builder-inited", on_builder_inited)
    # Expose config values used by this extension (optional)
    app.add_config_value("GITHUB_USER", default="theSadeQ", rebuild="env")
    app.add_config_value("GITHUB_REPO", default="DIP_SMC_PSO", rebuild="env")
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

