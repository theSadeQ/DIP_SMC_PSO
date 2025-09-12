
import json
import re
import sys
import os
from typing import Any, Dict, List, Tuple

ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
)

ERROR_REQUIRED = "REQUIRED_MISSING"
ERROR_TYPE = "TYPE_MISMATCH"
ERROR_UNKNOWN = "UNKNOWN_FIELD"
ERROR_CARDINALITY = "CARDINALITY"
ERROR_CROSS = "CROSS_FIELD"
WARNING = "WARNING"

def report():
    return {"errors": [], "warnings": []}

def add_error(rep, field, code, message):
    rep["errors"].append({"field": field, "code": code, "message": message, "severity": "error"})

def add_warning(rep, field, code, message):
    rep["warnings"].append({"field": field, "code": code, "message": message, "severity": "warning"})

def is_string(x): return isinstance(x, str)
def is_array(x): return isinstance(x, list)
def is_object(x): return isinstance(x, dict)

def check_field_order(rep, obj, field_order, field_path):
    # Check that the relative order of present fields follows the declared order
    present = [k for k in obj.keys() if k in field_order]
    expected_rel = [k for k in field_order if k in obj]
    if present != expected_rel:
        add_warning(rep, field_path, WARNING, f"Field order deviates; expected relative order {expected_rel}")

def unknown_field_check(rep, obj, allowed, field_path, allow_unknown=False):
    if allow_unknown:
        return
    for k in obj.keys():
        if k not in allowed:
            add_error(rep, f"{field_path}.{k}" if field_path else k, ERROR_UNKNOWN, "Undeclared field not allowed")

def must_have(rep, obj, key, field_path):
    if key not in obj:
        add_error(rep, f"{field_path}.{key}" if field_path else key, ERROR_REQUIRED, "Required field missing")
        return False
    return True

def expect_type(rep, val, checker, field, typename):
    if not checker(val):
        add_error(rep, field, ERROR_TYPE, f"Expected {typename}")
        return False
    return True

def expect_iso(rep, s, field):
    if not is_string(s) or not ISO_RE.match(s):
        add_error(rep, field, ERROR_TYPE, "Expected ISO-8601 'YYYY-MM-DDThh:mm:ssZ'")
        return False
    return True

def validate_typespec(rep, obj, field_path):
    allowed = ["type", "description", "constraints"]
    unknown_field_check(rep, obj, allowed, field_path, allow_unknown=False)
    ok = True
    if not must_have(rep, obj, "type", field_path): ok = False
    else:
        if not expect_type(rep, obj["type"], is_string, f"{field_path}.type", "string"): ok = False
    if "description" in obj:
        expect_type(rep, obj["description"], is_string, f"{field_path}.description", "string")
    if "constraints" in obj:
        expect_type(rep, obj["constraints"], is_object, f"{field_path}.constraints", "object")
    return ok

def validate_contract(rep, obj, field_path):
    allowed = ["inputs","outputs","errors","guards","tests","ci"]
    unknown_field_check(rep, obj, allowed, field_path, allow_unknown=False)
    # field order warning
    check_field_order(rep, obj, ["inputs","outputs","errors","guards","tests","ci"], field_path)

    ok = True
    if not must_have(rep, obj, "inputs", field_path): ok = False
    else:
        if not expect_type(rep, obj["inputs"], is_object, f"{field_path}.inputs", "object"): ok = False
        else:
            for k, v in obj["inputs"].items():
                if not expect_type(rep, v, is_object, f"{field_path}.inputs.{k}", "object"): ok = False
                else:
                    validate_typespec(rep, v, f"{field_path}.inputs.{k}")

    if not must_have(rep, obj, "outputs", field_path): ok = False
    else:
        if not expect_type(rep, obj["outputs"], is_object, f"{field_path}.outputs", "object"): ok = False
        else:
            for k, v in obj["outputs"].items():
                if not expect_type(rep, v, is_object, f"{field_path}.outputs.{k}", "object"): ok = False
                else:
                    validate_typespec(rep, v, f"{field_path}.outputs.{k}")

    if "errors" in obj:
        if not expect_type(rep, obj["errors"], is_array, f"{field_path}.errors", "array[string]"):
            ok = False
        else:
            for i, e in enumerate(obj["errors"]):
                if not expect_type(rep, e, is_string, f"{field_path}.errors[{i}]", "string"): ok = False

    if "guards" in obj:
        if not expect_type(rep, obj["guards"], is_object, f"{field_path}.guards", "object"):
            ok = False
        else:
            guards = obj["guards"]
            # additionalProperties: true, but check known fields when present
            if "shape_validation" in guards and not isinstance(guards["shape_validation"], bool):
                add_error(rep, f"{field_path}.guards.shape_validation", ERROR_TYPE, "Expected boolean")
                ok = False
            if "nan_policy" in guards:
                if guards["nan_policy"] not in ["allow","reject"]:
                    add_error(rep, f"{field_path}.guards.nan_policy", ERROR_TYPE, "Expected one of ['allow','reject']")
                    ok = False

    if "tests" in obj:
        if not expect_type(rep, obj["tests"], is_object, f"{field_path}.tests", "object"): ok = False
        else:
            # additionalProperties: false
            allowed_t = ["selector","coverage_target"]
            unknown_field_check(rep, obj["tests"], allowed_t, f"{field_path}.tests", allow_unknown=False)
            if "selector" not in obj["tests"]:
                add_error(rep, f"{field_path}.tests.selector", ERROR_REQUIRED, "Required field missing")
                ok = False
            else:
                expect_type(rep, obj["tests"]["selector"], is_string, f"{field_path}.tests.selector", "string")
            if "coverage_target" in obj["tests"]:
                if not isinstance(obj["tests"]["coverage_target"], (int,float)):
                    add_error(rep, f"{field_path}.tests.coverage_target", ERROR_TYPE, "Expected number")
                    ok = False

    if "ci" in obj:
        if not expect_type(rep, obj["ci"], is_object, f"{field_path}.ci", "object"): ok = False
        else:
            ci = obj["ci"]  # additionalProperties: true
            if "matrix" in ci:
                if not is_array(ci["matrix"]):
                    add_error(rep, f"{field_path}.ci.matrix", ERROR_TYPE, "Expected array[string]")
                    ok = False
                else:
                    for i, s in enumerate(ci["matrix"]):
                        if not is_string(s):
                            add_error(rep, f"{field_path}.ci.matrix[{i}]", ERROR_TYPE, "Expected string")
                            ok = False
            if "artifacts" in ci:
                if not is_string(ci["artifacts"]):
                    add_error(rep, f"{field_path}.ci.artifacts", ERROR_TYPE, "Expected string")
                    ok = False
    return ok

def validate_checklist(rep, obj, field_path):
    allowed = ["items"]
    unknown_field_check(rep, obj, allowed, field_path, allow_unknown=False)
    if not must_have(rep, obj, "items", field_path): return False
    if not is_array(obj["items"]):
        add_error(rep, f"{field_path}.items", ERROR_TYPE, "Expected array[string]")
        return False
    for i, s in enumerate(obj["items"]):
        if not is_string(s):
            add_error(rep, f"{field_path}.items[{i}]", ERROR_TYPE, "Expected string")
    return True

def validate_artifact(rep, obj, field_path):
    allowed = ["kind","name","location"]
    unknown_field_check(rep, obj, allowed, field_path, allow_unknown=False)
    ok = True
    if not must_have(rep, obj, "kind", field_path): ok = False
    else:
        expect_type(rep, obj["kind"], is_string, f"{field_path}.kind", "string")
    if not must_have(rep, obj, "name", field_path): ok = False
    else:
        expect_type(rep, obj["name"], is_string, f"{field_path}.name", "string")
    if "location" in obj:
        expect_type(rep, obj["location"], is_string, f"{field_path}.location", "string")
    return ok

def validate_validation_step(rep, obj, field_path):
    allowed = ["action","expected","tolerance"]
    unknown_field_check(rep, obj, allowed, field_path, allow_unknown=False)
    ok = True
    if not must_have(rep, obj, "action", field_path): ok = False
    else:
        expect_type(rep, obj["action"], is_string, f"{field_path}.action", "string")
    if not must_have(rep, obj, "expected", field_path): ok = False
    else:
        expect_type(rep, obj["expected"], is_string, f"{field_path}.expected", "string")
    if "tolerance" in obj:
        expect_type(rep, obj["tolerance"], is_string, f"{field_path}.tolerance", "string")
    return ok

def validate_execution_prompt(rep, obj, field_path):
    allowed = ["title","constraints","inputs","tasks","validation_steps","artifacts"]
    unknown_field_check(rep, obj, allowed, field_path, allow_unknown=False)
    check_field_order(rep, obj, ["title","constraints","inputs","tasks","validation_steps","artifacts"], field_path)
    ok = True
    # required all
    for k in allowed:
        if not must_have(rep, obj, k, field_path): ok = False
    if "title" in obj:
        expect_type(rep, obj["title"], is_string, f"{field_path}.title", "string")
    for arrf in ["constraints","inputs","tasks","validation_steps","artifacts"]:
        if arrf in obj:
            if not is_array(obj[arrf]):
                add_error(rep, f"{field_path}.{arrf}", ERROR_TYPE, "Expected array[string]")
                ok = False
            else:
                for i, s in enumerate(obj[arrf]):
                    if not is_string(s):
                        add_error(rep, f"{field_path}.{arrf}[{i}]", ERROR_TYPE, "Expected string")
                        ok = False
    return ok

def validate_acceptance(rep, obj, field_path):
    allowed = ["statement","evidence"]
    unknown_field_check(rep, obj, allowed, field_path, allow_unknown=False)
    ok = True
    if not must_have(rep, obj, "statement", field_path): ok = False
    else:
        expect_type(rep, obj["statement"], is_string, f"{field_path}.statement", "string")
    if "evidence" in obj:
        expect_type(rep, obj["evidence"], is_string, f"{field_path}.evidence", "string")
    return ok

def validate_risk(rep, obj, field_path):
    allowed = ["description","mitigation"]
    unknown_field_check(rep, obj, allowed, field_path, allow_unknown=False)
    ok = True
    if not must_have(rep, obj, "description", field_path): ok = False
    else:
        expect_type(rep, obj["description"], is_string, f"{field_path}.description", "string")
    if not must_have(rep, obj, "mitigation", field_path): ok = False
    else:
        expect_type(rep, obj["mitigation"], is_string, f"{field_path}.mitigation", "string")
    return ok

def validate_task(rep, obj, field_path):
    allowed = ["id","title","contracts"]
    unknown_field_check(rep, obj, allowed, field_path, allow_unknown=False)
    ok = True
    if not must_have(rep, obj, "id", field_path): ok = False
    else:
        expect_type(rep, obj["id"], is_string, f"{field_path}.id", "string")
    if not must_have(rep, obj, "title", field_path): ok = False
    else:
        expect_type(rep, obj["title"], is_string, f"{field_path}.title", "string")
    if not must_have(rep, obj, "contracts", field_path): ok = False
    else:
        if not is_object(obj["contracts"]):
            add_error(rep, f"{field_path}.contracts", ERROR_TYPE, "Expected object")
            ok = False
        else:
            validate_contract(rep, obj["contracts"], f"{field_path}.contracts")
    return ok

def validate_phase(rep, obj, idx, field_path):
    allowed = ["name","goals","success_criteria","tasks","artifacts","validation_steps","execution_prompt","non_goals","anti_patterns"]
    unknown_field_check(rep, obj, allowed, field_path, allow_unknown=False)
    check_field_order(rep, obj, ["name","goals","success_criteria","tasks","artifacts","validation_steps","execution_prompt","non_goals","anti_patterns"], field_path)

    ok = True
    for k in ["name","goals","success_criteria","tasks","artifacts","validation_steps","execution_prompt"]:
        if not must_have(rep, obj, k, field_path): ok = False
    if "name" in obj and not is_string(obj["name"]):
        add_error(rep, f"{field_path}.name", ERROR_TYPE, "Expected string")
        ok = False
    if "goals" in obj:
        if not is_array(obj["goals"]):
            add_error(rep, f"{field_path}.goals", ERROR_TYPE, "Expected array[string]")
            ok = False
        else:
            for i, s in enumerate(obj["goals"]):
                if not is_string(s):
                    add_error(rep, f"{field_path}.goals[{i}]", ERROR_TYPE, "Expected string")
                    ok = False
    if "success_criteria" in obj:
        if not is_array(obj["success_criteria"]):
            add_error(rep, f"{field_path}.success_criteria", ERROR_TYPE, "Expected array[string]")
            ok = False
        else:
            for i, s in enumerate(obj["success_criteria"]):
                if not is_string(s):
                    add_error(rep, f"{field_path}.success_criteria[{i}]", ERROR_TYPE, "Expected string")
                    ok = False
    if "tasks" in obj:
        if not is_array(obj["tasks"]):
            add_error(rep, f"{field_path}.tasks", ERROR_TYPE, "Expected array[Task]")
            ok = False
        else:
            ids = set()
            for i, t in enumerate(obj["tasks"]):
                if not is_object(t):
                    add_error(rep, f"{field_path}.tasks[{i}]", ERROR_TYPE, "Expected object Task")
                    ok = False
                else:
                    validate_task(rep, t, f"{field_path}.tasks[{i}]")
                    if "id" in t and is_string(t["id"]):
                        if t["id"] in ids:
                            add_error(rep, f"{field_path}.tasks[{i}].id", ERROR_CARDINALITY, "Duplicate task id in Phase")
                        ids.add(t["id"])
    if "artifacts" in obj:
        if not is_array(obj["artifacts"]):
            add_error(rep, f"{field_path}.artifacts", ERROR_TYPE, "Expected array[Artifact]")
            ok = False
        else:
            for i, a in enumerate(obj["artifacts"]):
                if not is_object(a):
                    add_error(rep, f"{field_path}.artifacts[{i}]", ERROR_TYPE, "Expected object Artifact")
                    ok = False
                else:
                    validate_artifact(rep, a, f"{field_path}.artifacts[{i}]")
    if "validation_steps" in obj:
        if not is_array(obj["validation_steps"]):
            add_error(rep, f"{field_path}.validation_steps", ERROR_TYPE, "Expected array[ValidationStep]")
            ok = False
        else:
            for i, vs in enumerate(obj["validation_steps"]):
                if not is_object(vs):
                    add_error(rep, f"{field_path}.validation_steps[{i}]", ERROR_TYPE, "Expected object ValidationStep")
                    ok = False
                else:
                    validate_validation_step(rep, vs, f"{field_path}.validation_steps[{i}]")
    if "execution_prompt" in obj:
        if not is_object(obj["execution_prompt"]):
            add_error(rep, f"{field_path}.execution_prompt", ERROR_TYPE, "Expected object ExecutionPrompt")
            ok = False
        else:
            validate_execution_prompt(rep, obj["execution_prompt"], f"{field_path}.execution_prompt")

    # Optional arrays
    if "non_goals" in obj and not (is_array(obj["non_goals"]) and all(isinstance(s, str) for s in obj["non_goals"])):
        add_error(rep, f"{field_path}.non_goals", ERROR_TYPE, "Expected array[string]")
    if "anti_patterns" in obj and not (is_array(obj["anti_patterns"]) and all(isinstance(s, str) for s in obj["anti_patterns"])):
        add_error(rep, f"{field_path}.anti_patterns", ERROR_TYPE, "Expected array[string]")
    return ok

def validate_research_plan(obj: Dict[str, Any]) -> Dict[str, Any]:
    rep = report()
    if not is_object(obj):
        add_error(rep, "", ERROR_TYPE, "Top-level must be object")
        return rep

    allowed_top = ["metadata","executive_summary","phases","risks","acceptance","checklists","manifests"]
    unknown_field_check(rep, obj, allowed_top, "", allow_unknown=False)
    check_field_order(rep, obj, allowed_top, "")

    # Required
    for k in allowed_top:
        if k in ["risks","manifests"]:  # these can be empty arrays (not required in spec? keep as present but optional? we mark as required per spec)
            pass
    for req in ["metadata","executive_summary","phases","risks","acceptance","checklists","manifests"]:
        if req not in obj:
            add_error(rep, req, ERROR_REQUIRED, "Required field missing")

    # Types and nested
    if "metadata" in obj:
        md = obj["metadata"]
        if not is_object(md):
            add_error(rep, "metadata", ERROR_TYPE, "Expected object")
        else:
            allowed = ["title","version","created_at","updated_at","tags","schema_version"]
            unknown_field_check(rep, md, allowed, "metadata", allow_unknown=False)
            check_field_order(rep, md, ["title","version","created_at","updated_at","tags","schema_version"], "metadata")
            if "title" not in md: add_error(rep, "metadata.title", ERROR_REQUIRED, "Required field missing")
            else:
                if not is_string(md["title"]): add_error(rep, "metadata.title", ERROR_TYPE, "Expected string")
            if "version" not in md: add_error(rep, "metadata.version", ERROR_REQUIRED, "Required field missing")
            else:
                if not is_string(md["version"]): add_error(rep, "metadata.version", ERROR_TYPE, "Expected string")
            if "created_at" not in md: add_error(rep, "metadata.created_at", ERROR_REQUIRED, "Required field missing")
            else:
                expect_iso(rep, md["created_at"], "metadata.created_at")
            if "updated_at" in md:
                expect_iso(rep, md["updated_at"], "metadata.updated_at")
            if "tags" in md:
                if not is_array(md["tags"]):
                    add_error(rep, "metadata.tags", ERROR_TYPE, "Expected array[string]")
                else:
                    for i, t in enumerate(md["tags"]):
                        if not is_string(t):
                            add_error(rep, f"metadata.tags[{i}]", ERROR_TYPE, "Expected string")
            # schema_version policy (warn now, error later)
            strict_schema = os.getenv("SCHEMA_VERSION_ENFORCE", "warn")
            if "schema_version" not in md:
                if strict_schema == "error":
                    add_error(rep, "metadata.schema_version", ERROR_REQUIRED, "schema_version required (expected '1.x')")
                else:
                    add_warning(rep, "metadata.schema_version", WARNING, "Recommended schema_version '1.x' missing")
            else:
                if not is_string(md["schema_version"]):
                    add_error(rep, "metadata.schema_version", ERROR_TYPE, "Expected string")
                else:
                    if not re.match(r"^1(\.[\d]+.*)?$", md["schema_version"]):
                        if strict_schema == "error":
                            add_error(rep, "metadata.schema_version", ERROR_TYPE, "Expected schema_version '1.x'")
                        else:
                            add_warning(rep, "metadata.schema_version", WARNING, "Expected schema_version '1.x'")

    if "executive_summary" in obj:
        es = obj["executive_summary"]
        if not is_object(es):
            add_error(rep, "executive_summary", ERROR_TYPE, "Expected object")
        else:
            allowed = ["context","intended_outcomes","phases_overview"]
            unknown_field_check(rep, es, allowed, "executive_summary", allow_unknown=False)
            check_field_order(rep, es, ["context","intended_outcomes","phases_overview"], "executive_summary")
            for req in allowed:
                if req not in es: add_error(rep, f"executive_summary.{req}", ERROR_REQUIRED, "Required field missing")
            if "context" in es and not is_string(es["context"]):
                add_error(rep, "executive_summary.context", ERROR_TYPE, "Expected string")
            if "intended_outcomes" in es:
                if not is_array(es["intended_outcomes"]):
                    add_error(rep, "executive_summary.intended_outcomes", ERROR_TYPE, "Expected array[string]")
                else:
                    for i, s in enumerate(es["intended_outcomes"]):
                        if not is_string(s):
                            add_error(rep, f"executive_summary.intended_outcomes[{i}]", ERROR_TYPE, "Expected string")
            if "phases_overview" in es:
                if not is_array(es["phases_overview"]):
                    add_error(rep, "executive_summary.phases_overview", ERROR_TYPE, "Expected array[string]")
                else:
                    for i, s in enumerate(es["phases_overview"]):
                        if not is_string(s):
                            add_error(rep, f"executive_summary.phases_overview[{i}]", ERROR_TYPE, "Expected string")

    # phases
    phase_names = []
    artifact_names = set()
    if "phases" in obj:
        ph = obj["phases"]
        if not is_array(ph):
            add_error(rep, "phases", ERROR_TYPE, "Expected array[Phase]")
        else:
            if len(ph) < 1:
                add_error(rep, "phases", ERROR_CARDINALITY, "At least one phase required")
            for i, p in enumerate(ph):
                if not is_object(p):
                    add_error(rep, f"phases[{i}]", ERROR_TYPE, "Expected object Phase")
                else:
                    validate_phase(rep, p, i, f"phases[{i}]")
                    if "name" in p and is_string(p["name"]):
                        phase_names.append(p["name"])
                    if "artifacts" in p and is_array(p["artifacts"]):
                        for a in p["artifacts"]:
                            if isinstance(a, dict) and "name" in a and is_string(a["name"]):
                                artifact_names.add(a["name"])

    # risks
    if "risks" in obj:
        rs = obj["risks"]
        if not is_array(rs):
            add_error(rep, "risks", ERROR_TYPE, "Expected array[Risk]")
        else:
            for i, r in enumerate(rs):
                if not is_object(r):
                    add_error(rep, f"risks[{i}]", ERROR_TYPE, "Expected object Risk")
                else:
                    validate_risk(rep, r, f"risks[{i}]")

    # acceptance
    acceptance_statements = []
    if "acceptance" in obj:
        ac = obj["acceptance"]
        if not is_array(ac):
            add_error(rep, "acceptance", ERROR_TYPE, "Expected array[AcceptanceCriterion]")
        else:
            for i, a in enumerate(ac):
                if not is_object(a):
                    add_error(rep, f"acceptance[{i}]", ERROR_TYPE, "Expected object AcceptanceCriterion")
                else:
                    validate_acceptance(rep, a, f"acceptance[{i}]")
                    if "statement" in a and is_string(a["statement"]):
                        acceptance_statements.append(a["statement"].lower())

    # checklists
    if "checklists" in obj:
        ch = obj["checklists"]
        if not is_object(ch):
            add_error(rep, "checklists", ERROR_TYPE, "Expected object")
        else:
            allowed = ["definition_of_done","review","ops"]
            unknown_field_check(rep, ch, allowed, "checklists", allow_unknown=False)
            for ck in allowed:
                if ck not in ch:
                    add_error(rep, f"checklists.{ck}", ERROR_REQUIRED, "Required field missing")
                else:
                    if not is_object(ch[ck]):
                        add_error(rep, f"checklists.{ck}", ERROR_TYPE, "Expected object Checklist")
                    else:
                        validate_checklist(rep, ch[ck], f"checklists.{ck}")

    # manifests
    if "manifests" in obj:
        mf = obj["manifests"]
        if not is_array(mf):
            add_error(rep, "manifests", ERROR_TYPE, "Expected array[Manifest]")
        else:
            for i, m in enumerate(mf):
                if not is_object(m):
                    add_error(rep, f"manifests[{i}]", ERROR_TYPE, "Expected object Manifest")
                else:
                    allowed = ["name","goals","acceptance","risks","artifacts"]
                    unknown_field_check(rep, m, allowed, f"manifests[{i}]", allow_unknown=False)
                    # required
                    for req in ["name","goals","acceptance"]:
                        if req not in m:
                            add_error(rep, f"manifests[{i}].{req}", ERROR_REQUIRED, "Required field missing")
                    # types
                    if "name" in m and not is_string(m["name"]):
                        add_error(rep, f"manifests[{i}].name", ERROR_TYPE, "Expected string")
                    for arr in ["goals","acceptance","risks","artifacts"]:
                        if arr in m:
                            if not is_array(m[arr]):
                                add_error(rep, f"manifests[{i}].{arr}", ERROR_TYPE, "Expected array[string]")
                            else:
                                for j, s in enumerate(m[arr]):
                                    if not is_string(s):
                                        add_error(rep, f"manifests[{i}].{arr}[{j}]", ERROR_TYPE, "Expected string")
                    # Cross: manifest name must match a phase or 'Plan'
                    if "name" in m and is_string(m["name"]):
                        nm = m["name"]
                        if nm != "Plan" and nm not in phase_names:
                            add_error(rep, f"manifests[{i}].name", ERROR_CROSS, "Manifest name must match a phase name or 'Plan'")
                    # Cross: artifacts listed must exist
                    if "artifacts" in m:
                        for s in m["artifacts"]:
                            if s not in artifact_names:
                                add_error(rep, f"manifests[{i}].artifacts", ERROR_CROSS, f"Artifact '{s}' not found in phases.artifacts[*].name")

    # Cross-field checks requiring phases + acceptance
    # For each phase success_criteria item, require acceptance statement that includes it (case-insensitive substring match)
    def get_success_criteria(obj):
        sc = []
        if "phases" in obj and isinstance(obj["phases"], list):
            for i, p in enumerate(obj["phases"]):
                if isinstance(p, dict) and "success_criteria" in p and isinstance(p["success_criteria"], list):
                    for j, s in enumerate(p["success_criteria"]):
                        if isinstance(s, str):
                            sc.append((i, j, s))
        return sc

    for (i, j, s) in get_success_criteria(obj):
        s_low = s.lower()
        if not any(s_low in a for a in acceptance_statements):
            add_error(rep, f"phases[{i}].success_criteria[{j}]", ERROR_CROSS, "No matching acceptance.statement covers this success criterion")

    # Cross: contracts.errors covered by validation_steps expected messages in same phase
    if "phases" in obj and isinstance(obj["phases"], list):
        for i, p in enumerate(obj["phases"]):
            # collect expected texts
            expected_texts = []
            if isinstance(p, dict) and "validation_steps" in p and isinstance(p["validation_steps"], list):
                for vs in p["validation_steps"]:
                    if isinstance(vs, dict) and "expected" in vs and isinstance(vs["expected"], str):
                        expected_texts.append(vs["expected"].lower())
            # scan tasks' contracts.errors
            if isinstance(p, dict) and "tasks" in p and isinstance(p["tasks"], list):
                for t_idx, t in enumerate(p["tasks"]):
                    if isinstance(t, dict) and "contracts" in t and isinstance(t["contracts"], dict):
                        errs = t["contracts"].get("errors", [])
                        if isinstance(errs, list):
                            for e_idx, e in enumerate(errs):
                                if isinstance(e, str):
                                    if not any(e.lower() in txt for txt in expected_texts):
                                        add_error(rep, f"phases[{i}].tasks[{t_idx}].contracts.errors[{e_idx}]", ERROR_CROSS, "No validation_step.expected covers this error")

    return rep

def main():
    if len(sys.argv) < 2:
        print("Usage: validator.py <json-file> [<json-file> ...]")
        sys.exit(2)
    merged = {"errors": [], "warnings": []}
    exit_code = 0
    for path in sys.argv[1:]:
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(json.dumps({
                    "errors": [ {"field": "", "code": "TYPE_MISMATCH", "message": f"Invalid JSON: {e}", "severity": "error"} ],
                    "warnings": []
                }, indent=2))
                sys.exit(1)
        rep = validate_research_plan(data)
        # print per-file report
        print(json.dumps(rep, indent=2))
        if rep["errors"]:
            exit_code = 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
