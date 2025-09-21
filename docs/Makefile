#==========================================================================================\\\
#======================================== docs/Makefile =================================\\\
#==========================================================================================\\\

# World-class documentation build system for DIP_SMC_PSO

# Configuration
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Build targets
.PHONY: help clean html pdf linkcheck livehtml live install-deps quality validate

# Default target
help:
	@echo "DIP_SMC_PSO Documentation Build System"
	@echo "======================================"
	@echo ""
	@echo "Available targets:"
	@echo "  html        Build HTML documentation (strict mode)"
	@echo "  live        Build and auto-reload on changes with browser"
	@echo "  livehtml    Build and auto-reload on changes"
	@echo "  pdf         Build PDF documentation (requires LaTeX)"
	@echo "  linkcheck   Check all external links"
	@echo "  clean       Clean build directory"
	@echo "  install-deps Install documentation dependencies"
	@echo "  quality     Run documentation quality checks"
	@echo "  validate    Validate I/O contracts (legacy)"
	@echo ""
	@echo "Examples:"
	@echo "  make html"
	@echo "  make livehtml"
	@echo "  make pdf"

# Install documentation dependencies
install-deps:
	@echo "Installing documentation dependencies..."
	pip install -r requirements.txt
	@echo "Dependencies installed successfully!"

# Clean build directory
clean:
	@echo "Cleaning build directory..."
	rm -rf $(BUILDDIR)/*
	@echo "Build directory cleaned!"

# Build HTML documentation (strict mode)
html: clean
	@echo "Building HTML documentation (strict mode)..."
	$(SPHINXBUILD) -nW -b html $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/html
	@echo ""
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."
	@echo "Open $(BUILDDIR)/html/index.html in your browser."

# Live build with auto-reload (template version)
live:
	@echo "Starting live documentation server..."
	sphinx-autobuild $(SOURCEDIR) $(BUILDDIR)/html --open-browser

# Build PDF documentation
pdf: clean
	@echo "Building PDF documentation..."
	$(SPHINXBUILD) -b latex $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/latex
	@echo "Running LaTeX files through pdflatex..."
	$(MAKE) -C $(BUILDDIR)/latex all-pdf
	@echo ""
	@echo "Build finished. The PDF file is in $(BUILDDIR)/latex."

# Check external links
linkcheck:
	@echo "Checking external links..."
	$(SPHINXBUILD) -b linkcheck $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/linkcheck
	@echo ""
	@echo "Link check complete. See $(BUILDDIR)/linkcheck/output.txt for results."

# Live HTML with auto-reload
livehtml:
	@echo "Starting live documentation server..."
	@echo "Documentation will auto-reload when files change."
	@echo "Press Ctrl+C to stop."
	sphinx-autobuild $(SOURCEDIR) $(BUILDDIR)/html \
		--host 0.0.0.0 \
		--port 8000 \
		--watch $(SOURCEDIR) \
		--ignore "$(BUILDDIR)" \
		--ignore "*.tmp" \
		--ignore "*~" \
		--delay 1

# Documentation quality checks
quality:
	@echo "Running documentation quality checks..."
	@echo ""
	@echo "1. Checking file structure..."
	@test -f index.md || (echo "❌ Missing index.md" && exit 1)
	@test -f conf.py || (echo "❌ Missing conf.py" && exit 1)
	@test -d theory || (echo "❌ Missing theory directory" && exit 1)
	@test -d implementation || (echo "❌ Missing implementation directory" && exit 1)
	@test -d visual || (echo "❌ Missing visual directory" && exit 1)
	@test -d references || (echo "❌ Missing references directory" && exit 1)
	@test -d results || (echo "❌ Missing results directory" && exit 1)
	@echo "✅ File structure check passed"
	@echo ""
	@echo "2. Checking critical files..."
	@test -f theory/index.md || (echo "❌ Missing theory/index.md" && exit 1)
	@test -f theory/notation_and_conventions.md || (echo "❌ Missing notation file" && exit 1)
	@test -f theory/mathematical_references.md || (echo "❌ Missing math references" && exit 1)
	@test -f implementation/index.md || (echo "❌ Missing implementation/index.md" && exit 1)
	@test -f visual/index.md || (echo "❌ Missing visual/index.md" && exit 1)
	@test -f references/index.md || (echo "❌ Missing references/index.md" && exit 1)
	@test -f references/refs.bib || (echo "❌ Missing bibliography" && exit 1)
	@test -f results/index.md || (echo "❌ Missing results/index.md" && exit 1)
	@echo "✅ Critical files check passed"
	@echo ""
	@echo "3. Checking configuration..."
	@python -c "exec(open('conf.py').read()); print('✅ Configuration syntax check passed')"
	@echo ""
	@echo "📚 Documentation quality check completed successfully!"

# Legacy validation (preserved for compatibility)
validate:
	python scripts/validate_io_contracts.py
