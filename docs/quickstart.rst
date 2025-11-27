Quickstart Guide
================

Installation
------------

Install from PyPI:

.. code-block:: bash

   pip install license-tracker

Or install from source:

.. code-block:: bash

   git clone https://github.com/forkrul/license_tracker
   cd license_tracker
   pip install -e .

Basic Usage
-----------

Generate License Attribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scan your lock file and generate a ``licenses.md`` file:

.. code-block:: bash

   # From poetry.lock
   license-tracker gen --scan poetry.lock --output licenses.md

   # From Pipfile.lock
   license-tracker gen --scan Pipfile.lock

   # From requirements.txt
   license-tracker gen --scan requirements.txt

Check License Compliance
~~~~~~~~~~~~~~~~~~~~~~~~

Validate your dependencies against a license policy:

.. code-block:: bash

   # Deny specific licenses (blacklist mode)
   license-tracker check --scan poetry.lock --forbidden "GPL-3.0,AGPL-3.0"

   # Allow only specific licenses (whitelist mode)
   license-tracker check --scan poetry.lock --allowed "MIT,Apache-2.0,BSD-3-Clause"

Exit codes:

- ``0``: All licenses compliant
- ``1``: Violations found
- ``2``: Error occurred

Using GitHub Token
------------------

For projects with many dependencies, provide a GitHub token to avoid rate limits:

.. code-block:: bash

   export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
   license-tracker gen --scan poetry.lock

Or pass it directly:

.. code-block:: bash

   license-tracker gen --scan poetry.lock --github-token ghp_xxxxxxxxxxxx

Managing Cache
--------------

License Tracker caches resolution results for 30 days:

.. code-block:: bash

   # View cache info
   license-tracker cache show

   # Clear all cached entries
   license-tracker cache clear

   # Clear specific package
   license-tracker cache clear requests
