# ====================================================================
# World-Class Documentation Makefile for DIP_SMC_PSO
# Professional development workflow with quality checks
# ====================================================================

# Configuration
SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help install build clean serve test quality deploy-prep full-build

# Directories
DOCS_SOURCE_DIR := dip_docs/docs/source
DOCS_BUILD_DIR := dip_docs/docs/_build
HTML_DIR := $(DOCS_BUILD_DIR)/html
VENV_DIR := .venv
REQUIREMENTS_FILE := dip_docs/docs/requirements-enhanced.txt

# Python and Sphinx
PYTHON := python
PIP := pip
SPHINX_BUILD := sphinx-build
SPHINX_AUTOBUILD := sphinx-autobuild

# Build options
SPHINX_OPTS := -W --keep-going -T -E -a -j auto
SPHINX_OPTS_QUIET := -q
SPHINX_OPTS_VERBOSE := -v

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
RESET := \033[0m

help: ## 📚 Show help message
	@echo ""
	@echo "$(CYAN)════════════════════════════════════════════════════════════════$(RESET)"
	@echo "$(CYAN)  DIP_SMC_PSO Documentation Build System$(RESET)"
	@echo "$(CYAN)  World-Class Technical Documentation Workflow$(RESET)"
	@echo "$(CYAN)════════════════════════════════════════════════════════════════$(RESET)"
	@echo ""
	@echo "$(YELLOW)🚀 Quick Start:$(RESET)"
	@echo "  make -f docs.mk install     # Install all dependencies"
	@echo "  make -f docs.mk build       # Build documentation"
	@echo "  make -f docs.mk serve       # Serve documentation locally"
	@echo ""
	@echo "$(YELLOW)📋 Available targets:$(RESET)"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  $(GREEN)%-16s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## 🚀 Install documentation dependencies
	@echo "$(BLUE)📦 Installing dependencies...$(RESET)"
	@$(PIP) install --upgrade pip setuptools wheel
	@if [ -f "$(REQUIREMENTS_FILE)" ]; then \
		$(PIP) install -r $(REQUIREMENTS_FILE); \
	else \
		$(PIP) install sphinx sphinx-rtd-theme myst-parser sphinxcontrib-bibtex sphinx-copybutton; \
	fi
	@echo "$(GREEN)✅ Dependencies installed$(RESET)"

clean: ## 🧹 Clean build artifacts
	@echo "$(BLUE)🧹 Cleaning build directory...$(RESET)"
	@rm -rf $(DOCS_BUILD_DIR)
	@echo "$(GREEN)✅ Build directory cleaned$(RESET)"

build: ## 🏗️  Build documentation
	@echo "$(BLUE)🏗️ Building documentation...$(RESET)"
	@mkdir -p $(DOCS_BUILD_DIR)
	@$(SPHINX_BUILD) -b html $(SPHINX_OPTS) $(DOCS_SOURCE_DIR) $(HTML_DIR)
	@echo "$(GREEN)✅ Documentation built successfully$(RESET)"
	@echo "$(CYAN)📖 Open: $(HTML_DIR)/index.html$(RESET)"

build-enhanced: ## ⚡ Build with enhanced configuration
	@echo "$(BLUE)⚡ Building with enhanced configuration...$(RESET)"
	@mkdir -p $(DOCS_BUILD_DIR)
	@cd $(DOCS_SOURCE_DIR) && cp conf_enhanced.py conf.py
	@$(SPHINX_BUILD) -b html $(SPHINX_OPTS) $(DOCS_SOURCE_DIR) $(HTML_DIR)
	@echo "$(GREEN)✅ Enhanced documentation built$(RESET)"

serve: ## 🌐 Serve documentation locally
	@echo "$(BLUE)🌐 Starting documentation server...$(RESET)"
	@echo "$(CYAN)📖 Opening http://localhost:8000$(RESET)"
	@$(SPHINX_AUTOBUILD) --host 0.0.0.0 --port 8000 --open-browser $(DOCS_SOURCE_DIR) $(HTML_DIR)

test-links: ## 🔗 Check for broken links
	@echo "$(BLUE)🔗 Checking for broken links...$(RESET)"
	@$(SPHINX_BUILD) -b linkcheck $(DOCS_SOURCE_DIR) $(DOCS_BUILD_DIR)/linkcheck
	@echo "$(GREEN)✅ Link check complete$(RESET)"

test-doctest: ## 🧪 Run doctests
	@echo "$(BLUE)🧪 Running doctests...$(RESET)"
	@$(SPHINX_BUILD) -b doctest $(DOCS_SOURCE_DIR) $(DOCS_BUILD_DIR)/doctest
	@echo "$(GREEN)✅ Doctests complete$(RESET)"

quality: build test-links ## 🎯 Run quality checks
	@echo "$(GREEN)🎉 All quality checks passed!$(RESET)"

deploy-prep: build-enhanced test-links ## 🚀 Prepare for deployment
	@echo "$(BLUE)🚀 Preparing for deployment...$(RESET)"
	@touch $(HTML_DIR)/.nojekyll
	@echo "$(GREEN)✅ Deployment ready$(RESET)"

full-build: clean install build-enhanced quality ## 🎯 Complete workflow
	@echo "$(GREEN)🎉 Full build workflow complete!$(RESET)"

dev: install build-enhanced serve ## 🛠️  Development workflow