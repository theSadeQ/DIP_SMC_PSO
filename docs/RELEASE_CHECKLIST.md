# Release Checklist

Use this checklist when preparing a new release of the ResearchPlan validation system.

## Pre-Release

### Code & Documentation
- [ ] All features implemented and tested
- [ ] Update CHANGELOG.md with release date and final entries
- [ ] Ensure fixtures and documentation examples reflect current validator outputs
- [ ] Run full test suite: `pytest -q`
- [ ] Run validation smoke tests on both fixtures:
  ```bash
  python repo_validate.py fixtures/valid_plan.json    # should exit 0
  python repo_validate.py fixtures/invalid_plan.json  # should exit 1
  ```
- [ ] Test property-based validation: `pytest tests/test_property_based.py -q`
- [ ] Test cross-field validation: `python tests/run_crossfield_tests.py`

### Version Compliance
- [ ] Verify version number follows SemVer (MAJOR.MINOR.PATCH)
- [ ] Check if any breaking changes require MAJOR version bump
- [ ] Confirm deprecation warnings have been in place for at least one MINOR version before upgrading to ERROR

### Performance & Limits
- [ ] Test CLI performance limits:
  ```bash
  python repo_validate.py --max-bytes 1000000 --timeout-s 5 fixtures/valid_plan.json
  ```
- [ ] Verify JSON Schema integration works correctly
- [ ] Test with and without jsonschema dependency

## Release Process

### Tagging & Publishing
- [ ] Create and push git tag: `git tag vX.Y.Z && git push --tags`
- [ ] Verify GitHub Actions CI runs successfully on the tag
- [ ] Check that validation workflow completes with green status
- [ ] Confirm artifacts are uploaded and accessible

### Validation
- [ ] Clone fresh repository and test basic validation workflow
- [ ] Verify status badge shows passing status
- [ ] Test make targets: `make validate FILE=fixtures/valid_plan.json`
- [ ] Check README examples work as documented

## Post-Release

### Communication
- [ ] Update project documentation if validation behavior changed
- [ ] Announce changes if breaking changes or important new features
- [ ] Document any policy upgrades (warnings → errors) with migration guidance

### Monitoring
- [ ] Monitor CI for any issues with new validation rules
- [ ] Check for user feedback on new error codes or message clarity
- [ ] Verify backward compatibility with existing plan files

## Emergency Rollback

If issues are discovered post-release:

- [ ] Document the issue and impact assessment
- [ ] Consider hotfix for critical bugs (PATCH release)
- [ ] For breaking issues: 
  - [ ] Revert problematic rules to WARNING
  - [ ] Release PATCH with temporary rollback
  - [ ] Plan proper fix for next MINOR/MAJOR

## Version-Specific Notes

### MAJOR Release (X.0.0)
- [ ] Review all WARNING → ERROR upgrades scheduled for this release
- [ ] Ensure migration documentation is comprehensive
- [ ] Test with real plan files if available
- [ ] Consider gradual rollout or feature flags for large policy changes

### MINOR Release (X.Y.0)  
- [ ] Verify new rules default to WARNING when appropriate
- [ ] Test new validation features extensively
- [ ] Update schema version patterns if needed

### PATCH Release (X.Y.Z)
- [ ] Focus on bug fixes and message improvements only
- [ ] No behavior changes that could break existing workflows
- [ ] Quick turnaround for critical fixes