
    import argparse
    import os
    from pathlib import Path
    import sys
    import urllib.request
    import urllib.error
    import json
    import zipfile
    import tempfile

    REPO = "theSadeQ/DIP_SMC_PSO"
    DEFAULT_REF = "main"
    FILES = [
  "src/config.py",
  "config.yaml",
  "src/controllers/factory.py",
  "app.py",
  "streamlit_app.py",
  "src/core/vector_sim.py",
  "tests/test_app/test_streamlit_app.py",
  "tests/test_benchmarks/test_performance.py",
  "tests/test_controllers/test_sta_smc.py",
  "run_tests.py"
]

    def fetch_file(raw_url: str) -> bytes:
        req = urllib.request.Request(raw_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()

    def main():
        parser = argparse.ArgumentParser(description="Download selected files from a GitHub repo into a zip")
        parser.add_argument("--ref", default=DEFAULT_REF, help="git ref (branch, tag, or commit SHA). Default: main")
        parser.add_argument("--out", default="c04_selected_files.zip", help="output zip filename")
        args = parser.parse_args()

        base = f"https://raw.githubusercontent.com/{REPO}/{args.ref}"
        errors = []
        with tempfile.TemporaryDirectory() as tmpd:
            root = Path(tmpd)
            for rel in FILES:
                raw_url = f"{base}/{rel}"
                dest = root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    data = fetch_file(raw_url)
                    dest.write_bytes(data)
                    print(f"✓ fetched {rel}")
                except urllib.error.HTTPError as e:
                    errors.append((rel, f"HTTP {e.code}"))
                    print(f"✗ failed {rel} (HTTP {e.code})")
                except Exception as e:
                    errors.append((rel, str(e)))
                    print(f"✗ failed {rel} ({e})")

            if errors:
                print("\nSome files failed to download:", file=sys.stderr)
                for rel, msg in errors:
                    print(f" - {rel}: {msg}", file=sys.stderr)
                if len(errors) == len(FILES):
                    sys.exit(2)  # nothing fetched

            # Create the zip with the files we did fetch
            outzip = Path(args.out)
            with zipfile.ZipFile(outzip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for rel in FILES:
                    p = root / rel
                    if p.exists():
                        zf.write(p, arcname=rel)
            print(f"\nWrote {outzip.resolve()}")
            if errors:
                print("\nNote: some files were missing/failed; see messages above.", file=sys.stderr)

    if __name__ == "__main__":
        main()
