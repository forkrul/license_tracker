# Research: License Tracker

**Feature**: 001-license-tracker
**Date**: 2025-11-26

## Technology Research

### 1. PyPI JSON API

**Endpoint**: `https://pypi.org/pypi/{package}/{version}/json`

**Response Structure** (relevant fields):
```json
{
  "info": {
    "name": "requests",
    "version": "2.31.0",
    "license": "Apache 2.0",
    "classifiers": [
      "License :: OSI Approved :: Apache Software License"
    ],
    "home_page": "https://requests.readthedocs.io",
    "project_urls": {
      "Source": "https://github.com/psf/requests"
    }
  }
}
```

**Key Findings**:
- `info.license` is free-text, often messy (e.g., "MIT", "MIT License", "MIT license")
- `info.classifiers` are more structured but use Python trove classifiers, not SPDX
- `project_urls.Source` often contains GitHub URL
- Rate limit: No documented limit, but be respectful (use caching)

### 2. GitHub License API

**Endpoint**: `GET https://api.github.com/repos/{owner}/{repo}/license`

**Response Structure**:
```json
{
  "name": "MIT License",
  "path": "LICENSE",
  "sha": "abc123...",
  "size": 1071,
  "url": "https://api.github.com/repos/owner/repo/contents/LICENSE",
  "html_url": "https://github.com/owner/repo/blob/main/LICENSE",
  "download_url": "https://raw.githubusercontent.com/owner/repo/main/LICENSE",
  "license": {
    "key": "mit",
    "name": "MIT License",
    "spdx_id": "MIT",
    "url": "https://api.github.com/licenses/mit"
  }
}
```

**Key Findings**:
- `html_url` provides direct browser-viewable link
- `license.spdx_id` provides standardized identifier
- Rate limit: 60/hour (unauthenticated), 5000/hour (with PAT)
- 404 returned if no LICENSE file found

**Version Pinning Strategy**:
To get license URL for specific version:
1. Get tags: `GET /repos/{owner}/{repo}/tags`
2. Find tag matching version (e.g., `v2.31.0`, `2.31.0`)
3. Construct URL: `https://github.com/{owner}/{repo}/blob/{tag}/LICENSE`

### 3. license-expression Library

**Installation**: `pip install license-expression`

**Usage**:
```python
from license_expression import get_spdx_licensing

licensing = get_spdx_licensing()

# Parse complex expressions
expr = licensing.parse("MIT OR Apache-2.0")
# Returns: LicenseExpression object

# Normalize messy strings
expr = licensing.parse("Apache License 2.0")
# Returns: Apache-2.0

# Handle WITH clauses
expr = licensing.parse("GPL-2.0-or-later WITH Classpath-exception-2.0")
```

**Key Findings**:
- Handles 400+ SPDX license identifiers
- Parses AND, OR, WITH expressions
- Throws `ExpressionError` for unknown licenses
- Can extract individual license symbols from expressions

### 4. Lock File Formats

#### poetry.lock (TOML)

```toml
[[package]]
name = "requests"
version = "2.31.0"
description = "Python HTTP for Humans."
python-versions = ">=3.7"

[package.dependencies]
charset-normalizer = ">=2,<4"
idna = ">=2.5,<4"
```

**Key Findings**:
- No license information in lock file
- Must query PyPI for license data
- Contains full dependency graph

#### Pipfile.lock (JSON)

```json
{
  "default": {
    "requests": {
      "hashes": ["sha256:..."],
      "version": "==2.31.0"
    }
  },
  "develop": {
    "pytest": {
      "version": "==7.4.0"
    }
  }
}
```

**Key Findings**:
- Separate `default` and `develop` sections
- Version prefixed with `==`
- No license information

#### requirements.txt

```text
requests==2.31.0
numpy>=1.20,<2.0
git+https://github.com/user/repo.git@v1.0.0
```

**Key Findings**:
- Various version specifiers (==, >=, etc.)
- Git URLs for direct dependencies
- Comments and -r includes possible

### 5. SPDX License URLs

**URL Pattern**: `https://spdx.org/licenses/{SPDX_ID}.html`

**Examples**:
- MIT: https://spdx.org/licenses/MIT.html
- Apache-2.0: https://spdx.org/licenses/Apache-2.0.html
- BSD-3-Clause: https://spdx.org/licenses/BSD-3-Clause.html

**Key Findings**:
- Reliable fallback for any valid SPDX ID
- Always available (no API rate limits)
- Provides legal text and metadata

### 6. Trove Classifier to SPDX Mapping

Common mappings needed:

| Trove Classifier | SPDX ID |
|-----------------|---------|
| License :: OSI Approved :: MIT License | MIT |
| License :: OSI Approved :: Apache Software License | Apache-2.0 |
| License :: OSI Approved :: BSD License | BSD-3-Clause |
| License :: OSI Approved :: GNU General Public License v3 (GPLv3) | GPL-3.0-only |
| License :: OSI Approved :: ISC License (ISCL) | ISC |
| License :: Public Domain | Unlicense |

### 7. async HTTP with aiohttp

```python
import aiohttp
import asyncio

async def fetch_license(session: aiohttp.ClientSession, package: str, version: str):
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.json()
            return data["info"]["license"]
        return None

async def fetch_all(packages: list[tuple[str, str]]):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_license(session, name, ver) for name, ver in packages]
        return await asyncio.gather(*tasks)
```

**Key Findings**:
- Significant speedup for 100+ packages
- Use semaphore to limit concurrent connections
- Handle connection pooling automatically

## Competitive Analysis Summary

| Tool | Strength | Weakness (vs our goal) |
|------|----------|----------------------|
| pip-licenses | Simple, fast | Requires installed packages, no links |
| pip-audit | Static analysis | Security-focused, no attribution output |
| scancode-toolkit | Comprehensive | Heavy, slow, audit-focused |
| license-expression | SPDX parsing | No scanning/resolution |

## Decisions Made

1. **Use aiohttp** for async HTTP (faster than httpx for our use case)
2. **Use tomli** for TOML parsing (stdlib in 3.11+, fallback for older)
3. **Cache for 30 days** (license URLs don't change per version)
4. **SPDX fallback always** (ensures every package has a link)
5. **Support dual licensing** with license-expression parsing
