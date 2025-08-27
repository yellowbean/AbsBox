# Configuration file for the Sphinx documentation builder.

import pathlib
import sys

# -- Project information

project = 'absbox'
copyright = '2025, Xiaoyu Zhang'
author = 'Xiaoyu Zhang'

release = "0.51.6"

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
