from appcommands import __version__

project = 'dpy-appcommands'
copyright = '2021, Rishiraj0100'
author = 'Rishiraj0100'

# The short X.Y version
version = __version__
# The full version, including alpha/beta/rc tags
release = version

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.extlinks',
    'sphinx.ext.githubpages',
    'sphinx.ext.ifconfig',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinxcontrib.asyncio',
    'extensions.attributeable'
]
branch = 'alpha' if version.endswith('a') else 'v' + version

templates_path = ['_templates']
master_doc = 'index'
language = None
autodoc_typehints = 'none'

extlinks = {
    'issue': ('https://github.com/Rishiraj0100/dpy-appcommands/issues/%s', 'GH-'),
}

exclude_patterns = ['_build']
pygments_style = 'friendly'

html_experimental_html5_writer = True

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'basic'
autodoc_member_order = "bysource"
html_static_path = ['_static']
html_context = {
  'discord_invite': 'https://discord.gg/zdrSUu98BP'
}

resource_links = {
  'discord': 'https://discord.gg/zdrSUu98BP',
  'issues': 'https://github.com/Rishiraj0100/dpy-appcommands/issues',
  'discussions': 'https://github.com/Rishiraj0100/dpy-appcommands/discussions',
  'examples': f'https://github.com/Rishiraj0100/dpy-appcommands/tree/{branch}/examples',
}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'discord': ('https://discordpy.readthedocs.io/en/master', None)
}
rst_prolog = """
.. |coro| replace:: This function is a |coroutine_link|_.
.. |maybecoro| replace:: This function *could be a* |coroutine_link|_.
.. |coroutine_link| replace:: *coroutine*
.. _coroutine_link: https://docs.python.org/3/library/asyncio-task.html#coroutine
"""
html_search_scorer = '_static/scorer.js'

html_js_files = [
  'custom.js',
  'settings.js',
  'copy.js',
  'sidebar.js'
]
