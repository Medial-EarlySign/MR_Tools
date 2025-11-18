# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import sys, os
sys.path.insert(0, os.path.abspath('../..'))

project = 'MES Python API'
copyright = '2025, Medial Earlysign'
author = 'Alon Lanyado'
release = ''

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [ 'sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.autosummary', 'sphinx.ext.todo', 'sphinx.ext.napoleon', 'sphinx.ext.viewcode']

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'classic'
# html_static_path = ['_static']

autoclass_content = 'both'
autodoc_typehints = "description"