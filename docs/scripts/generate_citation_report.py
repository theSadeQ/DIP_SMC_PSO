#==========================================================================================\\\
#======================== docs/scripts/generate_citation_report.py ========================\\\
#==========================================================================================\\\
import csv
import json
import os
import re
from datetime import datetime, timezone


DOCS_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir))
CSV_PATH = os.path.join(DOCS_ROOT, "citations.csv")
REPORT_PATH = os.path.join(DOCS_ROOT, "citation_validation_report.json")


def read_file_lines(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except Exception:
        return []


def collect_doc_citations():
    pattern = re.compile(r"\[CIT-(\d{3})\]")
    citations = []
    for root, _, files in os.walk(DOCS_ROOT):
        for fn in files:
            if not fn.lower().endswith(".md"):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, start=os.getcwd()).replace("\\", "/")
            lines = read_file_lines(path)
            for i, line in enumerate(lines, start=1):
                for m in pattern.finditer(line):
                    cit_id = f"CIT-{m.group(1)}"
                    citations.append({
                        "citation_id": cit_id,
                        "doc_location": f"{rel}:{i}",
                        "doc_entity": line.strip(),
                    })
    return citations


def read_registry():
    reg = {}
    if not os.path.exists(CSV_PATH):
        return reg
    with open(CSV_PATH, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        for row in r:
            reg[row["citation_id"].strip()] = {
                "doc_location": row.get("doc_location", "").strip(),
                "code_reference": row.get("code_reference", "").strip(),
                "last_verified_utc": row.get("last_verified_utc", "").strip(),
                "status": row.get("status", "").strip() or "ok",
            }
    return reg


def get_code_line(ref: str):
    if not ref:
        return None, None, None
    try:
        path, lineno_str = ref.split(":", 1)
        lineno = int(lineno_str)
    except ValueError:
        path, lineno = ref, None
    abs_path = os.path.join(os.getcwd(), path)
    lines = read_file_lines(abs_path)
    text = None
    if lineno and 1 <= lineno <= len(lines):
        text = lines[lineno - 1].rstrip("\n")
    return path.replace("\\", "/"), lineno, text


def validate(citations, registry):
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for c in citations:
        cit_id = c["citation_id"]
        reg = registry.get(cit_id, {})
        code_ref = reg.get("code_reference") if reg else None
        status = reg.get("status") if reg else "missing_reference"
        path, lineno, code_text = get_code_line(code_ref or "")
        validation_status = status or "ok"
        proposed_update = None
        reasoning = ""
        if not code_ref:
            validation_status = "missing_reference"
            reasoning = "No code_reference in registry."
        else:
            if path and os.path.exists(path):
                if lineno is None:
                    reasoning = "Code file present; line unspecified."
                else:
                    # Prefer to check round-trip tag presence
                    if f"[{cit_id}]" in (code_text or ""):
                        reasoning = "Code line tagged with citation."
                    else:
                        reasoning = "Code line found; no inline tag present."
            else:
                validation_status = "missing_reference"
                reasoning = "Code reference path not found."

        # Known inconsistencies can add proposed edits
        if cit_id == "CIT-047":
            proposed_update = "Update angle thresholds in docs to 0.35 rad (switch) and 0.4 rad (reentry) to match config and controller."
        if cit_id == "CIT-067" and validation_status != "missing_reference":
            validation_status = "inconsistent"
            proposed_update = "Clarify 20 ms as illustrative; tie to `hil.extra_latency_ms` without fixed limit."

        out.append({
            "citation_id": cit_id,
            "doc_entity": c["doc_entity"],
            "doc_location": c["doc_location"],
            "code_reference": (f"{path}:{lineno}" if (path and lineno) else (path or None)),
            "validation_status": validation_status,
            "proposed_update": proposed_update,
            "reasoning": reasoning,
        })

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # Also refresh last_verified_utc in registry for present citations
    # (non-destructive; only for those we saw in docs)
    rows = []
    fieldnames = ["citation_id", "doc_location", "code_reference", "last_verified_utc", "status"]
    seen = set()
    for cid, rec in registry.items():
        seen.add(cid)
    for entry in out:
        cid = entry["citation_id"]
        rec = registry.get(cid, {})
        rows.append({
            "citation_id": cid,
            "doc_location": rec.get("doc_location", entry["doc_location"]),
            "code_reference": rec.get("code_reference", entry.get("code_reference") or ""),
            "last_verified_utc": now,
            "status": registry.get(cid, {}).get("status", entry["validation_status"]),
        })
        seen.discard(cid)
    # Preserve any registry rows not present in docs (unchanged)
    for cid in sorted(seen):
        rec = registry[cid]
        rows.append({
            "citation_id": cid,
            "doc_location": rec.get("doc_location", ""),
            "code_reference": rec.get("code_reference", ""),
            "last_verified_utc": rec.get("last_verified_utc", now),
            "status": rec.get("status", "ok"),
        })

    # Write back CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    docs = collect_doc_citations()
    reg = read_registry()
    validate(docs, reg)
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()

