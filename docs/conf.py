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
]

templates_path = ['_templates']
master_doc = 'index'
language = None
exclude_patterns = ['_build']
html_theme = 'sphinx_rtd_theme'
autodoc_member_order = "bysource"
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
