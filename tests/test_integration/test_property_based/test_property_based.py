import json, re
import sys
from pathlib import Path
from hypothesis import given, settings, strategies as st

# Add project root to path to find validator
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".scripts"))
from validator import validate_research_plan

def minimal_plan(success_criteria, acceptance):
    return {
        "metadata": {"title":"X","version":"1","created_at":"2025-09-11T00:00:00Z","schema_version":"1.0"},
        "executive_summary": {"context":"c","intended_outcomes":["o"],"phases_overview":["p"]},
        "phases": [{
            "name":"P1","goals":["g"],
            "success_criteria": success_criteria,
            "tasks":[{"id":"t1","title":"T","contracts":{"inputs":{"x":{"type":"object"}},"outputs":{"y":{"type":"object"}}}}],
            "artifacts":[{"kind":"document","name":"A"}],
            "validation_steps":[{"action":"a","expected":"covers: " + " | ".join([s.lower() for s in success_criteria])}],
            "execution_prompt":{"title":"t","constraints":[],"inputs":[],"tasks":[],"validation_steps":[],"artifacts":[]}
        }],
        "risks": [],
        "acceptance": [{"statement": s} for s in acceptance],
        "checklists": {"definition_of_done":{"items":[]}, "review":{"items":[]}, "ops":{"items":[]}},
        "manifests": [{"name":"P1","goals":["g"],"acceptance":["a"],"artifacts":["A"]}]
    }

alpha = st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=0x10FFFF, blacklist_categories=("Cs",)), min_size=1, max_size=40)

@given(sc=st.lists(alpha, min_size=1, max_size=5))
@settings(deadline=None, max_examples=50)
def test_cross_field_acceptance_covered(sc):
    # acceptance statements include each success_criterion as substring (lowercased)
    acceptance = [f"OK: {s.lower()}" for s in sc]
    rep = validate_research_plan(minimal_plan(sc, acceptance))
    assert not rep["errors"], f"unexpected errors: {rep}"

@given(sc=st.lists(alpha, min_size=1, max_size=3))
@settings(deadline=None, max_examples=50)
def test_cross_field_acceptance_missing_trips_error(sc):
    # acceptance statements do not include success_criteria => expect CROSS_FIELD
    acceptance = ["unrelated"]
    rep = validate_research_plan(minimal_plan(sc, acceptance))
    assert any(e["code"]=="CROSS_FIELD" for e in rep["errors"]), f"expected CROSS_FIELD, got: {rep}"

def test_unknown_field_injection_detected():
    plan = minimal_plan(["x"], ["x"])
    plan["__junk__"] = True
    rep = validate_research_plan(plan)
    assert any(e["code"]=="UNKNOWN_FIELD" for e in rep["errors"])