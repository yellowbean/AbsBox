# Configuration file for the Sphinx documentation builder.

import pathlib
import sys

# -- Project information

project = 'absbox'
copyright = '2025, Xiaoyu Zhang'
author = 'Xiaoyu Zhang'


def _absbox_version() -> str:
    """Return the absbox version from the repo's ``pyproject.toml``.

    The repository ``pyproject.toml`` is the single source of truth, so the
    published docs version can never drift from the library version. If the
    file is unavailable (e.g. building from an sdist), fall back to the
    installed package metadata.
    """
    pyproject = None
    try:
        pyproject = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"
    except IndexError:  # conf.py not at the expected depth
        pyproject = None
    if pyproject is not None and pyproject.exists():
        try:
            import tomllib  # Python 3.11+
        except ModuleNotFoundError:  # pragma: no cover - Python 3.10
            try:
                import tomli as tomllib
            except ModuleNotFoundError:
                tomllib = None
        if tomllib is not None:
            with pyproject.open("rb") as f:
                return tomllib.load(f)["project"]["version"]
    from importlib.metadata import version as _pkg_version

    return _pkg_version("absbox")


release = _absbox_version()
# Sphinx's ``version`` is the short X.Y form; keep it in lockstep with release.
version = ".".join(release.split(".")[:2])

# -- General configuration

sys.path.append(str(pathlib.Path(__file__).parent.parent))

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.duration',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosectionlabel',
    'sphinxemoji.sphinxemoji',
    'sphinx.ext.graphviz',
    'sphinx_changelog',
    'myst_nb',
    'sphinxcontrib.googleanalytics'
]

graphviz_output_format = 'svg'

# Serve files copied from ``docs/source/_static`` (e.g. marimo HTML exports).
html_static_path = ['_static']

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}

html_theme_options = {
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 5,
    'includehidden': True,
    'titles_only': False
}


nb_execution_excludepatterns = [
    # no stored outputs; would execute against the engine at build time
    "**/triggerRolling.ipynb",
]

## Autoapi Doc
#autoapi_dirs = ['../../../PyABS']



#def skip_submodules(app, what, name, obj, skip, options):
#    if what == "module":
#        skip = True
#    if name == "__init__" or name == 'absbox.tests':
#        skip = True
#    return skip
#
#
#def setup(sphinx):
#    sphinx.connect("autoapi-skip-member", skip_submodules)


intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'


googleanalytics_id = 'G-C0JWMTTLRN'
