
#!/usr/bin/env python3
import sys, json
from validator import validate_research_plan

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Validate ResearchPlan JSON")
    ap.add_argument("file", help="Path to JSON file")
    args = ap.parse_args()
    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)
    rep = validate_research_plan(data)
    print(json.dumps(rep, indent=2))
    if rep["errors"]:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
