#==========================================================================================\\\
#======================================== docs/conf.py ==================================\\\
#==========================================================================================\\\

"""World-class Sphinx configuration for DIP_SMC_PSO documentation."""

import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join('..', 'src')))

# Project information
project = 'DIP_SMC_PSO'
author = 'Research Team'
copyright = '2024, Research Team'
release = '1.0.0'

# Extensions - comprehensive set for world-class docs
extensions = [
    # Core Sphinx extensions
    # 'sphinx.ext.autodoc',      # Temporarily disabled for testing
    # 'sphinx.ext.autosummary',  # Temporarily disabled for testing
    # 'sphinx.ext.napoleon',     # Temporarily disabled for testing
    # 'sphinx.ext.viewcode',     # Temporarily disabled for testing
    'sphinx.ext.mathjax',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosectionlabel',

    # External extensions
    'myst_parser',
    # 'sphinxcontrib.bibtex',    # Temporarily disabled for testing
    'sphinx_copybutton',
    'sphinx_design',
    'sphinxcontrib.mermaid',
]

# MyST Parser configuration - quality-of-life features
myst_enable_extensions = [
    'dollarmath',      # $...$ for inline math
    'amsmath',         # amsmath LaTeX extension
    'colon_fence',     # ::: fences for directives
    'deflist',         # definition lists
    'tasklist',        # GitHub-style task lists
    'fieldlist',       # field lists
    'linkify',         # auto-link URLs
]
myst_heading_anchors = 3

# MathJax configuration - globally numbered equations
mathjax3_config = {
    'tex': {
        'tags': 'all',           # Number all equations
        'tagSide': 'right',      # Put numbers on the right
        'macros': {
            'vec': ['\\boldsymbol{#1}', 1],
            'mat': ['\\boldsymbol{#1}', 1],
            'norm': ['\\left\\|#1\\right\\|', 1],
            'R': '\\mathbb{R}',
            'C': '\\mathbb{C}',
            'N': '\\mathbb{N}',
            'Z': '\\mathbb{Z}',
        }
    }
}

# Figure and table numbering for cross-references
numfig = True
numfig_secnum_depth = 2
numfig_format = {
    'figure': 'Figure %s',
    'table': 'Table %s',
    'code-block': 'Listing %s',
}

# Bibliography configuration
bibtex_bibfiles = [
    'refs.bib',           # Main bibliography file
    'bib/smc.bib',
    'bib/pso.bib',
    'bib/dip.bib',
    'bib/software.bib',
]
bibtex_default_style = 'unsrt'  # Basic unsorted style for compatibility

# Auto-section labeling for stable cross-references
autosectionlabel_prefix_document = True

# Autodoc configuration (temporarily disabled)
# autodoc_default_options = {
#     'members': True,
#     'member-order': 'bysource',
#     'special-members': '__init__',
#     'undoc-members': True,
#     'exclude-members': '__weakref__'
# }
# autodoc_typehints = 'description'
# autodoc_typehints_description_target = 'documented'

# Autosummary configuration (temporarily disabled)
# autosummary_generate = True
# autosummary_imported_members = True

# Intersphinx mapping for external documentation
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
}

# HTML theme configuration
html_theme = 'furo'  # Modern, responsive theme
html_title = f'{project} Documentation'
html_static_path = ['_static']

html_theme_options = {
    'sidebar_hide_name': False,
    'navigation_with_keys': True,
    'top_of_page_button': 'edit',
    'source_repository': 'https://github.com/your-org/DIP_SMC_PSO/',
    'source_branch': 'main',
    'source_directory': 'docs/',
}

# HTML output options
html_show_sourcelink = True
html_show_sphinx = True
html_show_copyright = True
html_last_updated_fmt = '%b %d, %Y'

# Copy button configuration
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True
copybutton_exclude = '.linenos, .gp, .go'

# Mermaid configuration
mermaid_output_format = 'svg'
mermaid_params = ['--theme', 'neutral', '--width', '800', '--backgroundColor', 'white']

# LaTeX output configuration (for PDF generation)
latex_engine = 'pdflatex'
latex_elements = {
    'papersize': 'letterpaper',
    'pointsize': '10pt',
    'preamble': r'''
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
''',
}

# Build configuration - strict mode for CI
if os.environ.get('READTHEDOCS'):
    # Suppress some warnings on RTD
    suppress_warnings = ['epub.unknown_project_files']
else:
    # Strict mode for local development
    suppress_warnings = []