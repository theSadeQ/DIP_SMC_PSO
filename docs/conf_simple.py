#==========================================================================================\\\
#===================================== docs/conf_simple.py ==============================\\\
#==========================================================================================\\\

"""Simplified Sphinx configuration for testing."""

import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join('..', 'src')))

# Project information
project = 'DIP_SMC_PSO'
author = 'Research Team'
copyright = '2024, Research Team'
release = '1.0.0'

# Minimal extensions for local testing (no autodoc to avoid import issues)
extensions = [
    'sphinx.ext.mathjax',
    'sphinx.ext.autosectionlabel',
    'sphinxcontrib.bibtex',
    'myst_parser',
    'sphinx_design',
    'sphinx_copybutton',
]

# MyST Parser configuration
myst_enable_extensions = [
    'dollarmath',
    'amsmath',
    'colon_fence',
    'deflist',
    'tasklist',
]
myst_heading_anchors = 3

# MathJax configuration
mathjax3_config = {
    'tex': {
        'tags': 'all',
        'tagSide': 'right',
        'macros': {
            'vec': ['\\boldsymbol{#1}', 1],
            'mat': ['\\boldsymbol{#1}', 1],
            'norm': ['\\left\\|#1\\right\\|', 1],
        }
    }
}

# Figure numbering
numfig = True
numfig_format = {
    'figure': 'Figure %s',
    'table': 'Table %s',
    'code-block': 'Listing %s',
}

# Bibliography
bibtex_bibfiles = [
    'references/refs.bib',
    'bib/smc.bib',
    'bib/pso.bib',
    'bib/dip.bib',
    'bib/software.bib',
]
bibtex_default_style = 'alpha'

# Auto-section labeling
autosectionlabel_prefix_document = True

# HTML theme
html_theme = 'sphinx_rtd_theme'
html_title = f'{project} Documentation'
html_static_path = ['_static']
html_css_files = ['custom.css']

html_theme_options = {
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'style_external_links': True,
}

# Copy button
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

# Suppress warnings for local testing
suppress_warnings = ['epub.unknown_project_files', 'autosectionlabel.*']