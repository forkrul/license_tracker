CLI Reference
=============

License Tracker provides three main commands: ``gen``, ``check``, and ``cache``.

gen Command
-----------

Generate license attribution documentation.

.. code-block:: text

   license-tracker gen [OPTIONS]

Options
~~~~~~~

``-s, --scan PATH``
   Path to lock file (required). Supports ``poetry.lock``, ``Pipfile.lock``, and ``requirements.txt``.

``-o, --output PATH``
   Output file path. Default: ``licenses.md``

``--include-root``
   Include the root project's license in the output.

``-t, --template PATH``
   Custom Jinja2 template file for output formatting.

``--github-token TEXT``
   GitHub API token for higher rate limits. Can also be set via ``GITHUB_TOKEN`` environment variable.

``-v, --verbose``
   Enable verbose output for debugging.

Examples
~~~~~~~~

.. code-block:: bash

   # Basic usage
   license-tracker gen --scan poetry.lock

   # Custom output file
   license-tracker gen --scan poetry.lock --output THIRD_PARTY_LICENSES.md

   # With custom template
   license-tracker gen --scan poetry.lock --template my-template.j2

check Command
-------------

Check license compliance against allow/deny lists.

.. code-block:: text

   license-tracker check [OPTIONS]

Options
~~~~~~~

``-s, --scan PATH``
   Path to lock file (required).

``-f, --forbidden TEXT``
   Comma-separated list of forbidden SPDX license IDs (blacklist mode).

``-a, --allowed TEXT``
   Comma-separated list of allowed SPDX license IDs (whitelist mode).

``--github-token TEXT``
   GitHub API token.

``-v, --verbose``
   Enable verbose output.

Exit Codes
~~~~~~~~~~

- ``0``: All licenses compliant
- ``1``: Violations found
- ``2``: Error occurred (invalid arguments, scan failure, etc.)

Examples
~~~~~~~~

.. code-block:: bash

   # Deny GPL licenses
   license-tracker check --scan poetry.lock --forbidden "GPL-3.0,GPL-2.0,AGPL-3.0"

   # Allow only permissive licenses
   license-tracker check --scan poetry.lock --allowed "MIT,Apache-2.0,BSD-3-Clause,ISC"

cache Command
-------------

Manage the license resolution cache.

.. code-block:: text

   license-tracker cache <action> [package]

Actions
~~~~~~~

``show``
   Display cache location, entry count, and size.

``clear``
   Clear all cached entries, or a specific package if provided.

Examples
~~~~~~~~

.. code-block:: bash

   # View cache statistics
   license-tracker cache show

   # Clear entire cache
   license-tracker cache clear

   # Clear specific package
   license-tracker cache clear requests
