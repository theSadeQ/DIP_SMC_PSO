#==========================================================================================\\\
#======================================== docs/conf.py ==================================\\\
#==========================================================================================\\\

"""Sphinx configuration for DIP_SMC_PSO documentation."""

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

# Dynamic versioning from git
def get_version():
    try:
        return subprocess.check_output(['git', 'describe', '--tags', '--always']).decode().strip()
    except:
        return 'unknown'

release = get_version()
version = release

# Extensions - Production-ready configuration
extensions = [
    # Core Sphinx extensions
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.linkcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx.ext.duration',        # Build performance monitoring
    'sphinx.ext.githubpages',     # GitHub Pages compatibility

    # Third-party extensions
    'sphinxcontrib.bibtex',       # Academic citations
    'myst_parser',                # Markdown support
    'sphinx_copybutton',          # Copy code buttons
    'sphinx_design',              # Design components
    'sphinx_togglebutton',        # Collapsible content
    'sphinxext.opengraph',        # Social media previews
    'sphinx_sitemap',             # SEO sitemap
    'sphinx_proof',               # Theorem/proof environments
]

# MyST Parser configuration
myst_enable_extensions = [
    'dollarmath',     # $x$ and $$x$$ for inline/display math
    'amsmath',        # LaTeX math environments
    'colon_fence',    # ::: fenced blocks
    'deflist',        # Definition lists
    'linkify',        # Auto-link URLs
    'tasklist',       # - [ ] Task lists
]
myst_heading_anchors = 3

# Bibliography configuration for academic citations
bibtex_bibfiles = ['refs.bib']
bibtex_default_style = 'author_year'  # Author-year style for research
bibtex_reference_style = 'author_year'
bibtex_tooltips = True
bibtex_bibliography_header = ".. rubric:: References"

# Autodoc configuration
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

# Mock imports for heavy dependencies to avoid import-time failures
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
]

# Napoleon configuration for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True

# Intersphinx mapping for cross-references
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
}
intersphinx_cache_limit = 5

# HTML output configuration
html_theme = 'furo'
html_title = f'{project} {release} Documentation'
html_theme_options = {
    'logo_only': False,
    'display_version': True,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'show_powered_by': False,
    'footer_icons': [
        {
            'name': 'GitHub',
            'url': 'https://github.com/yourusername/DIP_SMC_PSO',
            'html': '''
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.03 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            ''',
            'class': '',
        },
    ],
}

# Pygments configuration for code highlighting
pygments_style = 'tango'
pygments_dark_style = 'native'

# Quality gates - treat warnings as errors and be nitpicky
nitpicky = True
nitpick_ignore = [
    # Add common third-party references that can't be resolved
    ('py:class', 'numpy.ndarray'),
    ('py:class', 'scipy.optimize.OptimizeResult'),
    ('py:class', 'matplotlib.figure.Figure'),
]

# Suppress specific warnings
suppress_warnings = [
    'myst.header',  # Suppress duplicate header warnings in MyST
]

# Additional HTML options
html_show_sourcelink = True
html_copy_source = True
html_show_sphinx = False
html_static_path = ['_static']

# SEO and social media configuration
html_baseurl = 'https://theSadeQ.github.io/DIP_SMC_PSO/'
ogp_site_url = html_baseurl
ogp_site_name = project
ogp_description = 'Advanced sliding mode control for double-inverted pendulum with PSO optimization'
ogp_type = 'website'

# Sitemap configuration
sitemap_url_scheme = "{link}"

# Linkcheck configuration (used by nightly linkcheck builder)
linkcheck_timeout = 10
linkcheck_anchors = True
linkcheck_ignore = [
    r"https://doi\.org/.*",
    r"https://.*github\.com/.*#.*",
]

# Linkcode extension for durable source links
GITHUB_USER = "theSadeQ"
GITHUB_REPO = "DIP_SMC_PSO"

def _get_commit_sha():
    """Get commit SHA from environment or git."""
    # Try GitHub Actions first
    for env in ("GITHUB_SHA", "READTHEDOCS_GIT_IDENTIFIER"):
        v = os.getenv(env)
        if v and len(v) >= 7:
            return v

    # Fallback to git command
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "main"  # Ultimate fallback

def linkcode_resolve(domain, info):
    """Resolve a GitHub permalink to the object's source code.

    Enhanced version with comprehensive edge case handling based on expert recommendations.
    """
    if domain != "py":
        return None

    modname = info.get("module")
    fullname = info.get("fullname")
    if not modname or not fullname:
        return None

    try:
        # Import the module and get the object
        submod = __import__(modname, fromlist=["*"])
        obj = submod
        for part in fullname.split("."):
            obj = getattr(obj, part)

        # Handle various object types and decorators
        if isinstance(obj, property):
            obj = obj.fget
        elif isinstance(obj, (classmethod, staticmethod)):
            obj = obj.__func__
        elif hasattr(obj, '__wrapped__'):  # functools.wraps and similar
            obj = obj.__wrapped__
        elif hasattr(obj, 'func'):  # Other wrapped functions
            obj = obj.func

        # Get source file and line numbers
        fn = inspect.getsourcefile(inspect.unwrap(obj))
        if fn is None:
            # Fallback: try to get module-level link
            try:
                mod_file = inspect.getsourcefile(submod)
                if mod_file:
                    fn = mod_file
                    # Use module start for line numbers
                    source, lineno = ['# Module level'], 1
                else:
                    return None
            except Exception:
                return None
        else:
            source, lineno = inspect.getsourcelines(obj)

    except Exception as e:
        # Log warning in development but don't fail build
        if os.getenv('SPHINX_BUILD_MODE') != 'CI':
            print(f"Warning: linkcode_resolve failed for {modname}.{fullname}: {e}")
        return None

    # Compute relative path from repo root
    repo_root = Path(__file__).parent.parent.absolute()
    try:
        rel_fn = Path(fn).relative_to(repo_root)
    except ValueError:
        # File is outside repo, can't create relative path
        return None

    # Normalize path separators for URLs (critical for Windows)
    rel_fn = str(rel_fn).replace(os.sep, "/")

    # Calculate line range
    start_line = lineno
    end_line = lineno + len(source) - 1

    # Get commit SHA
    sha = _get_commit_sha()

    # Generate GitHub permalink
    return (
        f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/blob/{quote(sha)}/"
        f"{quote(rel_fn)}#L{start_line}-L{end_line}"
    )

# Build performance monitoring
def setup(app):
    """Custom setup for additional functionality."""
    pass