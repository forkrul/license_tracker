# Configuration file for the Sphinx documentation builder.

import os
import sys

# Add source directory to path for autodoc
sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------
project = "License Tracker"
copyright = "2025, License Tracker Contributors"
author = "License Tracker Contributors"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinxcontrib.mermaid",
]

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

# MyST settings for Markdown support
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Create static directory if it doesn't exist
os.makedirs("_static", exist_ok=True)

# -- Autodoc settings --------------------------------------------------------
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

autodoc_typehints = "description"

# Suppress duplicate object description warnings (common with dataclasses)
suppress_warnings = ["ref.python"]
