# Data Model: License Tracker

**Feature**: 001-license-tracker
**Date**: 2025-11-26

## Core Entities

### PackageSpec

Represents a dependency extracted from a lock file or environment scan.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class PackageSpec:
    """Immutable specification of a package dependency."""
    name: str                          # Package name (e.g., "requests")
    version: str                       # Exact version (e.g., "2.31.0")
    source: Optional[str] = None       # Where discovered (e.g., "poetry.lock")
```

**Constraints**:
- `name` must be a valid PyPI package name
- `version` must be a specific version, not a range
- Used as dictionary key (frozen=True for hashability)

### LicenseLink

Represents a resolved license with its URL and verification status.

```python
from dataclasses import dataclass

@dataclass
class LicenseLink:
    """A resolved license reference."""
    spdx_id: str              # Normalized SPDX identifier (e.g., "MIT", "Apache-2.0")
    name: str                 # Human-readable name (e.g., "MIT License")
    url: str                  # URL to license text
    is_verified_file: bool    # True if URL points to actual file (GitHub), False if generic (SPDX)
```

**Constraints**:
- `spdx_id` should be a valid SPDX identifier when possible
- `url` must be a valid HTTP(S) URL
- `is_verified_file` helps users understand link quality

### PackageMetadata

Enriched metadata for a package after resolution.

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class PackageMetadata:
    """Complete metadata for a package including resolved licenses."""
    name: str
    version: str
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository_url: Optional[str] = None
    author: Optional[str] = None
    licenses: List[LicenseLink] = field(default_factory=list)
    is_root_project: bool = False

    @property
    def primary_license(self) -> Optional[LicenseLink]:
        """Returns the first/primary license if available."""
        return self.licenses[0] if self.licenses else None
```

**Constraints**:
- `licenses` list supports dual-licensing (MIT OR Apache-2.0)
- `is_root_project` marks the project containing the tracker

### CacheEntry

SQLite cache entry for resolved license URLs.

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CacheEntry:
    """Cached license resolution result."""
    package_name: str
    package_version: str
    license_data: str          # JSON-serialized LicenseLink list
    resolved_at: datetime
    expires_at: datetime       # Cache TTL (default: 30 days)
```

## Entity Relationships

```
PackageSpec (1) ---> (1) PackageMetadata
                          |
                          +---> (0..*) LicenseLink

CacheEntry (1) ---> (1) PackageSpec (logical key)
```

## Resolution Flow

```
Input (lock file)
    │
    ▼
┌─────────────┐
│ PackageSpec │  (name, version)
└─────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                 Waterfall Resolution                 │
│                                                      │
│  1. Check Cache → CacheEntry                        │
│  2. Local (importlib.metadata)                      │
│  3. PyPI JSON API                                   │
│  4. GitHub License API                              │
│  5. SPDX Fallback                                   │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────┐
│ PackageMetadata │  (enriched with LicenseLinks)
└─────────────────┘
    │
    ▼
┌─────────────────┐
│    Reporter     │  (Jinja2 → Markdown/HTML)
└─────────────────┘
```

## Database Schema (Cache)

```sql
CREATE TABLE IF NOT EXISTS license_cache (
    package_name TEXT NOT NULL,
    package_version TEXT NOT NULL,
    license_data TEXT NOT NULL,  -- JSON
    resolved_at TEXT NOT NULL,   -- ISO 8601
    expires_at TEXT NOT NULL,    -- ISO 8601
    PRIMARY KEY (package_name, package_version)
);

CREATE INDEX idx_expires ON license_cache(expires_at);
```

## Serialization

### JSON Format (for cache and export)

```json
{
  "packages": [
    {
      "name": "requests",
      "version": "2.31.0",
      "description": "Python HTTP for Humans.",
      "homepage": "https://requests.readthedocs.io",
      "repository_url": "https://github.com/psf/requests",
      "licenses": [
        {
          "spdx_id": "Apache-2.0",
          "name": "Apache License 2.0",
          "url": "https://github.com/psf/requests/blob/main/LICENSE",
          "is_verified_file": true
        }
      ],
      "is_root_project": false
    }
  ],
  "root_project": {
    "name": "my-app",
    "version": "1.0.0",
    "licenses": [
      {
        "spdx_id": "MIT",
        "name": "MIT License",
        "url": "https://github.com/me/my-app/blob/main/LICENSE",
        "is_verified_file": true
      }
    ],
    "is_root_project": true
  },
  "generated_at": "2025-11-26T12:00:00Z",
  "generator": "license_tracker/1.0.0"
}
```
