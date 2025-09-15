#==========================================================================================\\\
#========================= docs/scripts/validate_io_contracts.py =========================\\\
#==========================================================================================\\\
#!/usr/bin/env python3
# Validates docs/io_contracts.csv for required columns and basic sanity:
# - required headers present
# - update_rate_Hz numeric when provided
# - direction in {input, output, both}
# - unit non-empty

import csv, sys, pathlib

CSV_PATH = pathlib.Path("docs/io_contracts.csv")
REQUIRED = ["signal_name","direction","unit","update_rate_Hz","valid_range","description"]
VALID_DIR = {"input","output","both"}

def main():
    if not CSV_PATH.exists():
        print(f"[ERROR] {CSV_PATH} not found", file=sys.stderr)
        sys.exit(2)
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [h for h in REQUIRED if h not in reader.fieldnames]
        if missing:
            print(f"[ERROR] Missing columns: {missing}")
            sys.exit(2)
        ok = True
        for i,row in enumerate(reader, start=2):
            name = (row.get("signal_name") or "").strip()
            direction = (row.get("direction") or "").strip().lower()
            unit = (row.get("unit") or "").strip()
            rate = (row.get("update_rate_Hz") or "").strip()
            if not name:
                print(f"[ERROR] line {i}: empty signal_name"); ok=False
            if direction not in VALID_DIR:
                print(f"[ERROR] line {i}: invalid direction '{direction}'"); ok=False
            if not unit:
                print(f"[ERROR] line {i}: empty unit"); ok=False
            if rate:
                try:
                    float(rate)
                except ValueError:
                    print(f"[ERROR] line {i}: update_rate_Hz not numeric: '{rate}'"); ok=False
        if ok:
            print("[OK] io_contracts.csv basic checks passed.")
        sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
