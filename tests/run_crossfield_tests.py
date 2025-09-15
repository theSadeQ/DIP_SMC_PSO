
#==========================================================================================\\\
#============================ tests/run_crossfield_tests.py ============================\\\
#==========================================================================================\\\

import json, sys
import sys, os; sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from validator import validate_research_plan

def run_case(name, payload, want_codes_prefixes):
    rep = validate_research_plan(payload)
    codes = sorted({e["code"] for e in rep["errors"]} | {w["code"] for w in rep["warnings"]})
    ok = all(any(c.startswith(prefix) or c==prefix for c in codes) for prefix in want_codes_prefixes)
    return ok, rep

def main():
    cases = []

    # Case 1: success_criteria must be covered by acceptance
    payload1 = {
      "metadata": {"title":"X","version":"1","created_at":"2025-09-11T00:00:00Z"},
      "executive_summary": {"context":"c","intended_outcomes":["o"],"phases_overview":["p"]},
      "phases": [{
         "name":"P1","goals":["g"],
         "success_criteria":["Must map"],
         "tasks":[{"id":"t1","title":"T","contracts":{"inputs":{"x":{"type":"object"}},"outputs":{"y":{"type":"object"}}}}],
         "artifacts":[{"kind":"document","name":"A"}],
         "validation_steps":[{"action":"a","expected":"something"}],
         "execution_prompt":{"title":"t","constraints":[],"inputs":[],"tasks":[],"validation_steps":[],"artifacts":[]}
      }],
      "risks": [],
      "acceptance": [{"statement":"Different text"}],
      "checklists": {"definition_of_done":{"items":[]}, "review":{"items":[]}, "ops":{"items":[]}},
      "manifests": [{"name":"P1","goals":["g"],"acceptance":["a"]}]
    }
    cases.append(("acceptance_mapping", payload1, ["CROSS_FIELD"]))

    # Case 2: contracts.errors must be covered by validation_steps
    payload2 = {
      "metadata": {"title":"X","version":"1","created_at":"2025-09-11T00:00:00Z"},
      "executive_summary": {"context":"c","intended_outcomes":["o"],"phases_overview":["p"]},
      "phases": [{
         "name":"P1","goals":["g"],
         "success_criteria":[],
         "tasks":[{"id":"t1","title":"T","contracts":{"inputs":{"x":{"type":"object"}},"outputs":{"y":{"type":"object"}},"errors":["E2"]}}],
         "artifacts":[{"kind":"document","name":"A"}],
         "validation_steps":[{"action":"a","expected":"covers e1 only"}],
         "execution_prompt":{"title":"t","constraints":[],"inputs":[],"tasks":[],"validation_steps":[],"artifacts":[]}
      }],
      "risks": [],
      "acceptance": [{"statement":"ok"}],
      "checklists": {"definition_of_done":{"items":[]}, "review":{"items":[]}, "ops":{"items":[]}},
      "manifests": [{"name":"P1","goals":["g"],"acceptance":["a"]}]
    }
    cases.append(("contracts_errors_coverage", payload2, ["CROSS_FIELD"]))

    all_ok = True
    for name, payload, want in cases:
        ok, rep = run_case(name, payload, want)
        print(json.dumps({"case": name, "ok": ok, "report": rep}, indent=2))
        if not ok:
            all_ok = False

    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
