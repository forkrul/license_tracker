License Tracker Documentation
=============================

**Automated open source license attribution and compliance tool for Python projects.**

License Tracker scans your dependency lock files, resolves license metadata from PyPI and GitHub,
and generates hyperlinked attribution documents.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   cli
   architecture
   api/index

Features
--------

- **Multiple Input Formats**: Scan ``poetry.lock``, ``Pipfile.lock``, or ``requirements.txt``
- **Smart Resolution**: Waterfall lookup through PyPI → GitHub → SPDX fallback
- **Verified Links**: Direct links to actual LICENSE files on GitHub when available
- **Compliance Checking**: Validate against allow/deny license lists
- **Caching**: SQLite cache with 30-day TTL to minimize API calls
- **Custom Templates**: Jinja2 templates for custom output formats
- **Async Performance**: Concurrent resolution for 100+ dependencies

Quick Example
-------------

.. code-block:: bash

   # Generate licenses.md from poetry.lock
   license-tracker gen --scan poetry.lock

   # Check compliance
   license-tracker check --scan poetry.lock --forbidden "GPL-3.0"

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
