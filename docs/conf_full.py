#==========================================================================================\\\
#======================================== docs/conf.py ==================================\\\
#==========================================================================================\\\

"""World-class Sphinx configuration for DIP_SMC_PSO documentation."""

import os
import sys
import subprocess
import inspect
from pathlib import Path
from urllib.parse import quote

# Add project root to Python path for autodoc
sys.path.insert(0, os.path.abspath(os.path.join('..', 'src')))

# Project information
project = 'DIP_SMC_PSO'
author = 'Research Team'
copyright = '2024, Research Team'
release = '1.0.0'
version = '1.0'

# Complete extension set for world-class documentation
extensions = [
    # Core Sphinx extensions
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.mathjax',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.githubpages',
    'sphinx.ext.duration',
    'sphinx.ext.linkcode',

    # Third-party extensions for enhanced functionality
    'sphinx_copybutton',
    'sphinxcontrib.bibtex',
    'myst_parser',
    'sphinx_design',
    'sphinx_togglebutton',
]

# Auto-generate API documentation
autosummary_generate = True
autosummary_generate_overwrite = True

# Autodoc configuration for comprehensive API docs
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
    'show-inheritance': True,
}
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'
autodoc_member_order = 'bysource'

# Napoleon for Google/NumPy style docstrings
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_attr_annotations = True

# MyST Parser configuration for enhanced markdown support
myst_enable_extensions = [
    'dollarmath',      # Dollar math for LaTeX equations
    'amsmath',         # AMS math environments
    'colon_fence',     # ::: fenced directives
    'deflist',         # Definition lists
    'tasklist',        # Task lists with checkboxes
    'attrs_inline',    # Inline attributes
    'attrs_block',     # Block attributes
    'fieldlist',       # Field lists
    'linkify',         # Auto-link URLs
]
myst_heading_anchors = 3
myst_dmath_double_inline = True

# MathJax configuration for LaTeX-quality math rendering
mathjax3_config = {
    'tex': {
        'tags': 'all',              # Number all equations
        'tagSide': 'right',         # Equation numbers on right
        'tagIndent': '0.8em',       # Indentation for equation numbers
        'processEscapes': True,     # Process backslash escapes
        'processEnvironments': True, # Process LaTeX environments
        'macros': {
            'vec': ['\\boldsymbol{#1}', 1],
            'mat': ['\\boldsymbol{#1}', 1],
            'norm': ['\\left\\|#1\\right\\|', 1],
            'abs': ['\\left|#1\\right|', 1],
        }
    },
    'svg': {
        'fontCache': 'global'
    }
}

# Figure and table numbering for professional cross-referencing
numfig = True
numfig_format = {
    'figure': 'Figure %s',
    'table': 'Table %s',
    'code-block': 'Listing %s',
    'section': 'Section %s',
}
numfig_secnum_depth = 2

# Bibliography configuration for citations
bibtex_bibfiles = [
    'references/refs.bib',
    'bib/smc.bib',
    'bib/pso.bib',
    'bib/dip.bib',
    'bib/software.bib',
]
bibtex_default_style = 'ieee'
bibtex_reference_style = 'label'
bibtex_tooltips = True
bibtex_bibliography_header = ".. rubric:: References"

# Intersphinx mapping for external documentation links
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
    'sklearn': ('https://scikit-learn.org/stable/', None),
}

# Auto-section labeling for cross-references
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 3

# Copy button configuration for code blocks
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True
copybutton_line_continuation_character = "\\"
copybutton_here_doc_delimiter = "EOF"

# HTML theme configuration - RTD theme with customization
html_theme = 'sphinx_rtd_theme'
html_title = f'{project} Documentation'
html_short_title = project
html_static_path = ['_static']
html_css_files = ['custom.css']
html_js_files = []

# RTD theme options for professional appearance
html_theme_options = {
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False,
    'style_external_links': True,
    'vcs_pageview_mode': 'blob',
    'style_nav_header_background': '#2980B9',
}

# HTML context for GitHub integration
html_context = {
    'display_github': True,
    'github_user': 'theSadeQ',
    'github_repo': 'DIP_SMC_PSO',
    'github_version': 'main',
    'conf_py_path': '/docs/',
    'source_suffix': '.md',
}

# Additional HTML configuration
html_show_sourcelink = True
html_show_sphinx = False
html_show_copyright = True
html_last_updated_fmt = '%Y-%m-%d %H:%M:%S'
html_use_index = True
html_split_index = True
html_copy_source = True
html_show_navigation_summary = True

# GitHub permalinks configuration
GITHUB_USER = "theSadeQ"
GITHUB_REPO = "DIP_SMC_PSO"

def _get_commit_sha():
    """Get commit SHA from environment or git."""
    for env in ("GITHUB_SHA", "READTHEDOCS_GIT_IDENTIFIER"):
        v = os.getenv(env)
        if v and len(v) >= 7:
            return v
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "main"

def linkcode_resolve(domain, info):
    """Resolve GitHub permalink to source code."""
    if domain != "py":
        return None

    modname = info.get("module")
    fullname = info.get("fullname")
    if not modname or not fullname:
        return None

    try:
        submod = __import__(modname, fromlist=["*"])
        obj = submod
        for part in fullname.split("."):
            obj = getattr(obj, part)

        if isinstance(obj, property):
            obj = obj.fget
        elif isinstance(obj, (classmethod, staticmethod)):
            obj = obj.__func__
        elif hasattr(obj, '__wrapped__'):
            obj = obj.__wrapped__
        elif hasattr(obj, 'func'):
            obj = obj.func

        fn = inspect.getsourcefile(inspect.unwrap(obj))
        if fn is None:
            return None

        source, lineno = inspect.getsourcelines(obj)

    except Exception:
        return None

    repo_root = Path(__file__).parent.parent.absolute()
    try:
        rel_fn = Path(fn).relative_to(repo_root)
    except ValueError:
        return None

    rel_fn = str(rel_fn).replace(os.sep, "/")
    start_line = lineno
    end_line = lineno + len(source) - 1
    sha = _get_commit_sha()

    return (
        f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/blob/{quote(sha)}/"
        f"{quote(rel_fn)}#L{start_line}-L{end_line}"
    )

# Mock imports for dependencies not available during doc build
autodoc_mock_imports = [
    'numpy',
    'scipy',
    'matplotlib',
    'control',
    'pyswarms',
    'optuna',
    'numba',
    'streamlit',
    'pandas',
    'yaml',
    'pydantic',
]

# Quality and warning configuration
nitpicky = False  # Set to True for stricter warnings
nitpick_ignore = [
    ('py:class', 'numpy.ndarray'),
    ('py:class', 'scipy.optimize.OptimizeResult'),
    ('py:class', 'pydantic.BaseModel'),
]

# Suppress warnings for external links during build
suppress_warnings = ['epub.unknown_project_files']

# LaTeX output configuration (for PDF generation)
latex_engine = 'pdflatex'
latex_elements = {
    'papersize': 'letterpaper',
    'pointsize': '11pt',
    'preamble': r'''
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{bm}
''',
}

# EPUB configuration
epub_show_urls = 'footnote'
epub_use_index = True

# Configuration for different output formats
add_function_parentheses = True
add_module_names = True

# Custom roles and directives can be added here
def setup(app):
    """Custom Sphinx setup function."""
    app.add_css_file('custom.css')

    # Custom roles for mathematical notation
    from docutils.parsers.rst import roles
    from docutils import nodes

    def math_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
        """Custom role for inline math."""
        node = nodes.math(rawtext, text)
        return [node], []

    roles.register_local_role('math', math_role)