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

# Ensure repository root and `src` are importable for autodoc/linkcode
REPO_ROOT = Path(__file__).parent.parent.resolve()
SRC_PATH = REPO_ROOT / "src"
EXT_PATH = Path(__file__).parent / "_ext"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(EXT_PATH))

# Project information
project = 'DIP_SMC_PSO'
author = 'Research Team'
copyright = '2024, Research Team'
release = '1.0.0'

# Exclude patterns - files/directories to ignore during build
exclude_patterns = [
    '_build',                    # Build output directory
    'Thumbs.db',                # Windows thumbnail cache
    '.DS_Store',                # macOS folder metadata
    '.github/**',               # GitHub templates and workflows
    '**.ipynb_checkpoints',     # Jupyter notebook checkpoints
]

# Extensions - comprehensive set for world-class docs
extensions = [
    # Core Sphinx extensions
    'sphinx.ext.autodoc',         # Auto-generate docs from docstrings
    'sphinx.ext.autosummary',     # Generate summary tables
    'sphinx.ext.napoleon',        # Google/NumPy style docstrings
    'sphinx.ext.viewcode',        # Add source code links
    'sphinx.ext.linkcode',        # Permalinks to GitHub
    'sphinx.ext.githubpages',     # Emit .nojekyll for GitHub Pages
    'sphinx.ext.mathjax',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosectionlabel',

    # External extensions
    'myst_parser',
    'sphinxcontrib.bibtex',       # Bibliography support
    'sphinx_copybutton',
    'sphinx_design',
    'sphinxcontrib.mermaid',
    'sphinx_reredirects',
    'sphinx.ext.doctest',         # Test code blocks
    'sphinx.ext.duration',
    'sphinx_gallery.gen_gallery', # Executable examples
    'traceability',               # Requirements traceability generator
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
    'source_repository': 'https://github.com/theSadeQ/DIP_SMC_PSO/',
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

# Redirects for moved pages
redirects = {
    # Legacy landing pages moved to new Reference IA
    'controllers/index': 'reference/controllers/index',
    'optimization/index': 'reference/optimizer/index',
    'implementation/index': 'reference/index',
    'implementation/code_documentation_index': 'reference/index',
    # Controllers detail pages
    'controllers/classical-smc': 'reference/controllers/classical-smc',
    'controllers/super-twisting-smc': 'reference/controllers/super-twisting-smc',
    'controllers/adaptive-smc': 'reference/controllers/adaptive-smc',
    'controllers/hybrid-adaptive-smc': 'reference/controllers/hybrid-adaptive-smc',
}

# ----------------------------- GitHub linkcode ------------------------------
GITHUB_USER = "theSadeQ"
GITHUB_REPO = "DIP_SMC_PSO"

def _get_commit_sha():
    """Return a commit SHA for permalinks or 'main' as fallback.

    Order of preference: GITHUB_SHA -> READTHEDOCS_GIT_IDENTIFIER -> git HEAD -> 'main'
    """
    for env in ("GITHUB_SHA", "READTHEDOCS_GIT_IDENTIFIER"):
        v = os.getenv(env)
        if v and len(v) >= 7:
            return v
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "main"


def linkcode_resolve(domain, info):
    """Resolve GitHub permalink to source code with line anchors.

    Returns None for unsupported or missing info, otherwise a URL like:
    https://github.com/<user>/<repo>/blob/<sha>/<path>#L<start>-L<end>
    """
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

        # Unwrap common wrappers
        if isinstance(obj, property):
            obj = obj.fget
        elif isinstance(obj, (classmethod, staticmethod)):
            obj = obj.__func__
        elif hasattr(obj, "__wrapped__"):
            obj = obj.__wrapped__
        elif hasattr(obj, "func"):
            obj = obj.func

        fn = inspect.getsourcefile(inspect.unwrap(obj))
        if fn is None:
            return None
        source, lineno = inspect.getsourcelines(obj)
    except Exception:
        return None

    try:
        rel_fn = Path(fn).resolve().relative_to(REPO_ROOT)
    except Exception:
        return None

    rel_fn_posix = str(rel_fn).replace(os.sep, "/")
    start_line = lineno
    end_line = lineno + len(source) - 1
    sha = _get_commit_sha()

    return (
        f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/blob/{quote(sha)}/"
        f"{quote(rel_fn_posix)}#L{start_line}-L{end_line}"
    )


# Mock heavy dependencies to keep doc builds lightweight
autodoc_mock_imports = [
    'numpy', 'scipy', 'matplotlib', 'control', 'pyswarms', 'optuna', 'numba',
    'streamlit', 'pandas', 'yaml', 'pydantic'
]


# ----------------------------- Sphinx-Gallery -------------------------------
# Run only fast examples in CI when DOCS_FAST=1 is set
_fast_mode = os.environ.get("DOCS_FAST")
_filename_pattern = r"^plot_fast_" if _fast_mode else r"^plot_"

sphinx_gallery_conf = {
    'examples_dirs': ['examples'],      # relative to docs/
    'gallery_dirs': ['auto_examples'],  # built gallery target
    'filename_pattern': _filename_pattern,
    'ignore_pattern': r"_heavy|_skip",
    'min_reported_time': 0,
    'remove_config_comments': True,
}
