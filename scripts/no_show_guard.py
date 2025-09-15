#==========================================================================================\\
#=============================== scripts/no_show_guard.py ===============================\\
#==========================================================================================\\
#!/usr/bin/env python3
"""
scripts/no_show_guard.py
Static guard to prevent any use of matplotlib.pyplot.show() or plt.show().
Exits non-zero if such calls are found outside of the allowed test.
"""
import sys, re, pathlib

ALLOWLIST = {
    "tests/test_mpl_enforcement.py",  # sentinel test that intentionally calls show()
    "scripts/no_show_guard.py",      # guard script itself mentions show() in docs
}

PATTERN = re.compile(r"^[^#]*(?:plt\.show\s*\(|matplotlib\.pyplot\.show\s*\()", re.IGNORECASE)

def scan(root: pathlib.Path) -> int:
    violations = []
    for p in root.rglob("*.py"):
        # Skip virtualenvs & build dirs
        parts = set(p.parts)
        if any(seg in parts for seg in {".venv", "venv", "build", "dist", ".git"}):
            continue
        rel = p.as_posix().split(root.as_posix()+"/")[-1]
        if rel in ALLOWLIST:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"::warning file={rel}::Could not read file: {e}")
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if PATTERN.search(line):
                violations.append(f"{rel}:{i}: found banned call to plt.show() / matplotlib.pyplot.show()")
    if violations:
        print("::error ::The following banned show() calls were found:")
        print("\\n".join(violations))
        return 1
    return 0

if __name__ == "__main__":
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    sys.exit(scan(root))
