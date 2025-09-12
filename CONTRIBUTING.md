
# Contributing – ResearchPlanSpec Validation

## Policies
- **Field order = WARNING**: When the relative order of present fields deviates from the declared `field_order`, the validator emits a `WARNING` and accepts the output.
- **Unknown fields = ERROR**: When an undeclared field appears in a schema object where unknowns are disallowed, the validator emits `UNKNOWN_FIELD` (severity `error`) and rejects the output.

## Error Model
Machine-readable schema:
```json
{
  "errors": [ { "field": "string", "code": "string", "message": "string", "severity": "error" } ],
  "warnings": [ { "field": "string", "code": "string", "message": "string", "severity": "warning" } ]
}
```

Codes used:
- `REQUIRED_MISSING`: required field is absent
- `TYPE_MISMATCH`: type/format invalid (e.g., non-ISO timestamp, wrong array item types)
- `UNKNOWN_FIELD`: field not allowed by schema
- `CARDINALITY`: uniqueness or minItems violated
- `CROSS_FIELD`: cross-field/linkage rule violated
- `WARNING`: non-fatal advisory (e.g., field order)

## Examples

### Successful Validation (Valid Fixture)
```json
{
  "errors": [],
  "warnings": []
}
```

### Failed Validation with Field Order Warning
```json
{
  "errors": [
    {
      "field": "metadata.title",
      "code": "TYPE_MISMATCH",
      "message": "Expected string",
      "severity": "error"
    }
  ],
  "warnings": [
    {
      "field": "metadata",
      "code": "WARNING",
      "message": "Field order deviates; expected relative order ['title', 'version', 'created_at', 'tags']",
      "severity": "warning"
    }
  ]
}
```

### Cross-Field Validation Errors
```json
{
  "errors": [
    {
      "field": "phases[0].success_criteria[0]",
      "code": "CROSS_FIELD",
      "message": "No matching acceptance.statement covers this success criterion",
      "severity": "error"
    },
    {
      "field": "phases[0].tasks[0].contracts.errors[1]",
      "code": "CROSS_FIELD",
      "message": "No validation_step.expected covers this error",
      "severity": "error"
    }
  ],
  "warnings": []
}
```

## CLI Usage
```bash
python repo_validate.py fixtures/valid_plan.json
python repo_validate.py fixtures/invalid_plan.json
```

Exit code is `0` on success, `1` when any `errors` are present.

## Cross-Field Validation Rules
1. **Success Criteria Coverage**: Each `phases[*].success_criteria` item must be covered by at least one `acceptance[*].statement` (case-insensitive substring match)
2. **Error Handling Coverage**: Each `contracts.errors` item must be covered by a `validation_steps.expected` message in the same phase (case-insensitive substring match)

## Rule & Error Code Versioning

The validator follows **Semantic Versioning (SemVer)** for validation rules:

### Version Impact
- **MAJOR** (e.g., 1.x → 2.x): Adds new error conditions or reclassifies warnings to errors (breaking changes)
- **MINOR** (e.g., 1.1 → 1.2): Adds new warning codes or validation rules that default to WARNING (non-breaking)  
- **PATCH** (e.g., 1.1.1 → 1.1.2): Bug fixes, message improvements, no rule changes

### Deprecation Path
New validation rules follow a **warn-first deprecation path**:
1. **Introduce** new rule as **WARNING** in MINOR release
2. **Upgrade** to **ERROR** in next MAJOR release (with advance notice)
3. Schema version gating allows gradual migration

### Error Code Stability

| Code | Stability | Upgrade Path | Notes |
|------|-----------|--------------|--------|
| `REQUIRED_MISSING` | **Error** | Stable since 1.0 | Core schema violations |
| `TYPE_MISMATCH` | **Error** | Stable since 1.0 | Type/format violations |
| `UNKNOWN_FIELD` | **Error** | Configurable | Schema policy enforcement |
| `CARDINALITY` | **Error** | Stable since 1.0 | Uniqueness/count violations |
| `CROSS_FIELD` | **Error** | Stable since 1.0 | Cross-reference violations |
| `WARNING` | **Warning** | Policy-dependent | Field order, schema version |

### Schema Version Gating
- **Current policy**: `metadata.schema_version` must be `"1.x"` (WARNING if missing/invalid)
- **Future enforcement**: Can be upgraded to ERROR in MAJOR version with `--schema-version-enforce error`
- **Migration path**: Update plans to include valid schema version before upgrading validator

### Policy Changes
Major policy changes (e.g., field order becoming ERROR) will be:
1. **Announced** in CHANGELOG with timeline
2. **Available** via CLI flags for testing (`--strict-field-order`)  
3. **Enforced** in next MAJOR release with deprecation notice
