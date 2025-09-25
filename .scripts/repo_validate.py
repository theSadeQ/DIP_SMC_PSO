#==========================================================================================\\
#=============================== scripts/repo_validate.py ===============================\\
#==========================================================================================\\
#!/usr/bin/env python3
import sys, json, os, time
from pathlib import Path
from validator import validate_research_plan

# Optional jsonschema integration
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

def map_jsonschema_error(error):
    """Map jsonschema ValidationError to our report format"""
    # Build field path from error.absolute_path
    field_parts = []
    for part in error.absolute_path:
        if isinstance(part, int):
            field_parts[-1] = f"{field_parts[-1]}[{part}]"
        else:
            field_parts.append(str(part))
    field = ".".join(field_parts) if field_parts else ""
    
    # Map validator types to our codes
    if error.validator in ("required", "dependencies"):
        code = "REQUIRED_MISSING"
    elif error.validator in ("type", "format", "pattern"):
        code = "TYPE_MISMATCH" 
    elif error.validator == "additionalProperties":
        code = "UNKNOWN_FIELD"
    elif error.validator in ("minItems", "maxItems", "uniqueItems"):
        code = "CARDINALITY"
    else:
        code = "TYPE_MISMATCH"
        
    return {
        "field": field,
        "code": code,
        "message": error.message,
        "severity": "error"
    }

def validate_with_jsonschema(data):
    """Validate using JSON Schema and return errors in our format"""
    if not JSONSCHEMA_AVAILABLE:
        return [{
            "field": "",
            "code": "WARNING",
            "message": "jsonschema not available - install with: pip install jsonschema>=4.22",
            "severity": "warning"
        }]
    
    # Load schema
    schema_path = Path(__file__).parent / "researchplan.schema.json"
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except FileNotFoundError:
        return [{
            "field": "",
            "code": "WARNING", 
            "message": "researchplan.schema.json not found - skipping JSON Schema validation",
            "severity": "warning"
        }]
    
    # Validate
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in validator.iter_errors(data):
        errors.append(map_jsonschema_error(error))
    
    return errors

def merge_reports(custom_report, jsonschema_errors):
    """Merge custom validator report with jsonschema errors"""
    merged = {
        "errors": custom_report["errors"][:],  # copy
        "warnings": custom_report["warnings"][:]  # copy
    }
    
    for error in jsonschema_errors:
        if error["severity"] == "error":
            merged["errors"].append(error)
        else:
            merged["warnings"].append(error)
    
    return merged

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Validate ResearchPlan JSON")
    ap.add_argument("file", help="Path to JSON file")
    ap.add_argument("--schema-version-enforce", choices=["warn","error"], default="warn",
                    help="Treat non-1.x or missing schema_version as warning (default) or error")
    ap.add_argument("--with-jsonschema", action="store_true", default=True,
                    help="Enable JSON Schema validation (default: enabled)")
    ap.add_argument("--jsonschema-off", dest="with_jsonschema", action="store_false",
                    help="Disable JSON Schema validation")
    ap.add_argument("--max-bytes", type=int, default=2_000_000,
                    help="Maximum file size in bytes (default: 2000000)")
    ap.add_argument("--timeout-s", type=float, default=10.0,
                    help="Validation timeout in seconds (default: 10)")
    args = ap.parse_args()
    
    # Check file size before reading
    file_size = os.path.getsize(args.file)
    if file_size > args.max_bytes:
        error_report = {
            "errors": [{
                "field": "",
                "code": "CARDINALITY",
                "message": "Input exceeds max-bytes",
                "severity": "error"
            }],
            "warnings": []
        }
        print(json.dumps(error_report, indent=2))
        sys.exit(1)
    
    os.environ["SCHEMA_VERSION_ENFORCE"] = args.schema_version_enforce
    
    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Start timing for timeout check
    start_time = time.monotonic()
    
    # Run custom validation
    custom_report = validate_research_plan(data)
    
    # Check timeout after custom validation
    if time.monotonic() - start_time > args.timeout_s:
        timeout_report = {
            "errors": [{
                "field": "",
                "code": "CROSS_FIELD", 
                "message": "Validation timed out",
                "severity": "error"
            }],
            "warnings": []
        }
        print(json.dumps(timeout_report, indent=2))
        sys.exit(1)
    
    # Optionally run JSON Schema validation
    if args.with_jsonschema:
        jsonschema_errors = validate_with_jsonschema(data)
        
        # Check timeout after jsonschema validation  
        if time.monotonic() - start_time > args.timeout_s:
            timeout_report = {
                "errors": [{
                    "field": "",
                    "code": "CROSS_FIELD",
                    "message": "Validation timed out",
                    "severity": "error"
                }],
                "warnings": []
            }
            print(json.dumps(timeout_report, indent=2))
            sys.exit(1)
            
        final_report = merge_reports(custom_report, jsonschema_errors)
    else:
        final_report = custom_report
    
    print(json.dumps(final_report, indent=2))
    if final_report["errors"]:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
