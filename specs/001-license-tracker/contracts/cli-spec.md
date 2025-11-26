# CLI Specification: License Tracker

**Version**: 1.0.0
**Date**: 2025-11-26

## Command Overview

```
license-tracker [OPTIONS] COMMAND [ARGS]
```

## Global Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--version` | flag | - | Show version and exit |
| `--help` | flag | - | Show help message |
| `--verbose` / `-v` | flag | False | Enable verbose logging |
| `--quiet` / `-q` | flag | False | Suppress non-error output |
| `--config` | path | `license_tracker.toml` | Path to config file |

## Commands

### `gen` - Generate Attribution Documentation

Generate a licenses.md file with hyperlinked attribution for all dependencies.

```
license-tracker gen [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--scan` / `-s` | path | - | Path to lock file (poetry.lock, Pipfile.lock, requirements.txt) |
| `--env` | flag | False | Scan installed environment instead of lock file |
| `--output` / `-o` | path | `licenses.md` | Output file path |
| `--format` / `-f` | choice | `md` | Output format: `md`, `json`, `html` |
| `--template` / `-t` | path | - | Custom Jinja2 template file |
| `--include-root` | flag | False | Include root project in output |
| `--download` | flag | False | Download license files to docs/licenses/ |
| `--github-token` | string | `$GITHUB_TOKEN` | GitHub API token for higher rate limits |
| `--no-cache` | flag | False | Bypass resolution cache |

**Examples**:
```bash
# Basic usage
license-tracker gen --scan poetry.lock

# Full example
license-tracker gen \
  --scan poetry.lock \
  --output docs/LICENSES.md \
  --include-root \
  --github-token ghp_xxxx
```

**Exit Codes**:
- `0`: Success
- `1`: Error (file not found, parse error, etc.)
- `2`: Partial success (some packages could not be resolved)

---

### `check` - License Compliance Check

Validate dependencies against a license policy (allow/deny list).

```
license-tracker check [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--scan` / `-s` | path | - | Path to lock file |
| `--env` | flag | False | Scan installed environment |
| `--forbidden` | string | - | Comma-separated forbidden SPDX IDs |
| `--allowed` | string | - | Comma-separated allowed SPDX IDs (whitelist mode) |
| `--github-token` | string | `$GITHUB_TOKEN` | GitHub API token |
| `--format` / `-f` | choice | `text` | Output format: `text`, `json` |

**Examples**:
```bash
# Deny-list mode
license-tracker check --scan poetry.lock --forbidden "GPL-3.0,AGPL-3.0"

# Allow-list mode
license-tracker check --scan poetry.lock --allowed "MIT,Apache-2.0,BSD-3-Clause"
```

**Exit Codes**:
- `0`: Compliant (no policy violations)
- `1`: Non-compliant (violations found)
- `2`: Error (scan failed)

**Output (violations)**:
```
License Policy Violations Found:

Package             Version    License      Policy
─────────────────────────────────────────────────
some-package        1.2.3      GPL-3.0      FORBIDDEN
another-package     4.5.6      LGPL-2.1     FORBIDDEN

2 violation(s) found. Deployment blocked.
```

---

### `scan` - Scan Only (No Resolution)

List dependencies from a lock file without resolving licenses.

```
license-tracker scan [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--scan` / `-s` | path | - | Path to lock file |
| `--env` | flag | False | Scan installed environment |
| `--format` / `-f` | choice | `table` | Output: `table`, `json`, `names` |

**Examples**:
```bash
# List as table
license-tracker scan --scan poetry.lock

# JSON output for scripting
license-tracker scan --scan poetry.lock --format json

# Just names (for piping)
license-tracker scan --scan poetry.lock --format names
```

---

### `cache` - Cache Management

Manage the local resolution cache.

```
license-tracker cache SUBCOMMAND
```

**Subcommands**:

| Subcommand | Description |
|------------|-------------|
| `show` | Show cache location and stats |
| `clear` | Clear all cached data |
| `clear PACKAGE` | Clear cache for specific package |

**Examples**:
```bash
# Show cache info
license-tracker cache show
# Output:
# Cache location: ~/.cache/license_tracker/cache.sqlite
# Entries: 142
# Size: 256 KB
# Oldest entry: 2025-10-01

# Clear all
license-tracker cache clear

# Clear specific package
license-tracker cache clear requests
```

---

## Configuration File

`license_tracker.toml` (optional)

```toml
[license_tracker]
# Default input source
default_scan = "poetry.lock"

# Default output
output = "docs/licenses.md"
format = "md"

# Include root project by default
include_root = true

# GitHub token (prefer env var for security)
# github_token = "ghp_xxxx"

# Custom template
# template = "templates/custom.j2"

[license_tracker.policy]
# Forbidden licenses (deny-list)
forbidden = ["GPL-3.0", "AGPL-3.0", "GPL-2.0"]

# Or use allowed (whitelist) - mutually exclusive with forbidden
# allowed = ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "Unlicense"]

[license_tracker.cache]
# Cache TTL in days
ttl_days = 30

# Cache location (default: ~/.cache/license_tracker/)
# location = "/custom/path"

# Vendorized/manual dependencies
[[license_tracker.vendorized]]
name = "internal-lib"
version = "1.0.0"
license = "MIT"
license_url = "https://internal.example.com/license"
homepage = "https://internal.example.com"

[[license_tracker.vendorized]]
name = "forked-package"
version = "2.3.4"
license = "Apache-2.0"
license_url = "https://github.com/us/forked/blob/main/LICENSE"
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub API token for higher rate limits |
| `LICENSE_TRACKER_CONFIG` | Path to config file |
| `LICENSE_TRACKER_CACHE_DIR` | Override cache directory |
| `NO_COLOR` | Disable colored output |

---

## Output Formats

### Markdown (default)

```markdown
# Open Source License Attribution

| Library | Version | License | Source |
|---------|---------|---------|--------|
| [requests](https://requests.readthedocs.io) | 2.31.0 | [Apache-2.0](https://github.com/psf/requests/blob/main/LICENSE) | [GitHub](https://github.com/psf/requests) |
```

### JSON

```json
{
  "generated_at": "2025-11-26T12:00:00Z",
  "generator": "license_tracker/1.0.0",
  "packages": [
    {
      "name": "requests",
      "version": "2.31.0",
      "license": "Apache-2.0",
      "license_url": "https://github.com/psf/requests/blob/main/LICENSE",
      "homepage": "https://requests.readthedocs.io",
      "verified": true
    }
  ]
}
```

### HTML

```html
<table class="license-table">
  <thead>
    <tr><th>Library</th><th>Version</th><th>License</th><th>Source</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="https://requests.readthedocs.io">requests</a></td>
      <td>2.31.0</td>
      <td><a href="https://github.com/psf/requests/blob/main/LICENSE">Apache-2.0</a></td>
      <td><a href="https://github.com/psf/requests">GitHub</a></td>
    </tr>
  </tbody>
</table>
```
