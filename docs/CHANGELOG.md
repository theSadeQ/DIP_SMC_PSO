# Changelog

All notable changes to the ResearchPlan validation system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - Unreleased

### Added {#changelog-110-added}
- JSON Schema validation integration with `researchplan.schema.json`
- Property-based testing with Hypothesis for cross-field validation
- CLI performance limits: `--max-bytes` and `--timeout-s` flags
- Diff-aware CI validation (only validates changed plan files)
- Rule versioning documentation and deprecation policy
- Enhanced error reporting with JSON Schema and custom validator merged results
- `--with-jsonschema` and `--jsonschema-off` flags for controlling schema validation

### Changed
- CI workflow now installs dependencies from `requirements.txt`
- CI workflow runs pytest after validation
- Enhanced error messages with both custom validator and JSON Schema details

### Dependencies
- Added `jsonschema>=4.22` for JSON Schema validation
- Added `hypothesis>=6` for property-based testing
- Updated `pytest>=8` requirement

## [1.0.0] - 2025-09-12

### Added {#changelog-100-added}
- Initial release of ResearchPlan JSON validation system
- Comprehensive custom validator with error codes:
  - `REQUIRED_MISSING`: Required fields missing
  - `TYPE_MISMATCH`: Type/format validation errors
  - `UNKNOWN_FIELD`: Undeclared fields (policy: ERROR)
  - `CARDINALITY`: Uniqueness and count violations
  - `CROSS_FIELD`: Cross-reference validation errors
  - `WARNING`: Non-fatal advisories (field order, schema version)
- Cross-field validation rules:
  - Success criteria ↔ acceptance statements coverage
  - Contract errors ↔ validation steps coverage
- Schema version support (`metadata.schema_version` with `1.x` validation)
- CLI tool `repo_validate.py` with JSON reports and proper exit codes
- GitHub Actions CI workflow with fixture validation and artifact upload
- Unit tests for cross-field validation scenarios
- Field order warnings (accepted but warned)
- Unknown field rejection (strict policy)

### Documentation
- `CONTRIBUTING.md` with validation rules and examples
- `README.md` with validation usage instructions
- `.github/CODEOWNERS` for validation system ownership

### Infrastructure
- Test fixtures: `fixtures/valid_plan.json` and `fixtures/invalid_plan.json`
- Make target: `make validate FILE=path/to/file.json`
- Status badge for CI validation workflow