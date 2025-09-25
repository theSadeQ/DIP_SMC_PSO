# Makefile for DIP_SMC_PSO Project

.PHONY: validate test lint help

# Default Python command (adjust path if needed)
PYTHON := python

# Default file for validation (can be overridden with FILE=path)
FILE := fixtures/valid_plan.json

# Validate ResearchPlan JSON file
validate:
	@echo "Validating ResearchPlan file: $(FILE)"
	@$(PYTHON) repo_validate.py "$(FILE)"
	@echo "✓ Validation completed successfully"

# Run all validation tests
test-validation:
	@echo "Running validation on all fixtures..."
	@echo "=== Testing valid fixture ==="
	@$(PYTHON) repo_validate.py fixtures/valid_plan.json
	@echo "\n=== Testing invalid fixture ==="
	@$(PYTHON) repo_validate.py fixtures/invalid_plan.json || true
	@echo "\n=== Running cross-field validation tests ==="
	@$(PYTHON) tests/run_crossfield_tests.py

# Run existing tests
test:
	@echo "Running project tests..."
	@$(PYTHON) -m pytest

# Basic help
help:
	@echo "Available make targets:"
	@echo "  validate       - Validate a ResearchPlan JSON file (default: fixtures/valid_plan.json)"
	@echo "                   Usage: make validate FILE=path/to/file.json"
	@echo "  test-validation - Run all validation tests (fixtures + cross-field tests)"
	@echo "  test           - Run all project tests"
	@echo "  help           - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make validate"
	@echo "  make validate FILE=fixtures/invalid_plan.json"
	@echo "  make test-validation"