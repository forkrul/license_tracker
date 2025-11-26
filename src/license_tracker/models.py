"""Core data models for license_tracker.

This module defines the fundamental data structures used throughout the
license tracking system, including package specifications, license links,
and enriched metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class PackageSpec:
    """Immutable specification of a package dependency.

    Represents a dependency extracted from a lock file or environment scan.
    Frozen for hashability to enable use as dictionary keys.

    Attributes:
        name: Package name (e.g., "requests").
        version: Exact version string (e.g., "2.31.0").
        source: Optional source identifier (e.g., "poetry.lock").
    """

    name: str
    version: str
    source: Optional[str] = None


@dataclass
class LicenseLink:
    """A resolved license reference with verification status.

    Represents a license that has been resolved to a specific URL,
    with metadata about how reliable that resolution is.

    Attributes:
        spdx_id: Normalized SPDX identifier (e.g., "MIT", "Apache-2.0").
        name: Human-readable license name (e.g., "MIT License").
        url: URL to the license text.
        is_verified_file: True if URL points to actual license file (e.g., GitHub),
            False if generic reference (e.g., SPDX page).
    """

    spdx_id: str
    name: str
    url: str
    is_verified_file: bool = False


@dataclass
class PackageMetadata:
    """Complete metadata for a package including resolved licenses.

    Enriched metadata gathered from various sources (PyPI, GitHub, etc.)
    after resolution.

    Attributes:
        name: Package name.
        version: Package version.
        description: Optional package description.
        homepage: Optional homepage URL.
        repository_url: Optional source repository URL.
        author: Optional author name or email.
        licenses: List of resolved license links (supports dual-licensing).
        is_root_project: True if this is the root project being scanned.
    """

    name: str
    version: str
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository_url: Optional[str] = None
    author: Optional[str] = None
    licenses: list[LicenseLink] = field(default_factory=list)
    is_root_project: bool = False

    @property
    def primary_license(self) -> Optional[LicenseLink]:
        """Return the first/primary license if available.

        Returns:
            The first LicenseLink in the licenses list, or None if empty.
        """
        return self.licenses[0] if self.licenses else None


@dataclass
class CacheEntry:
    """Cached license resolution result.

    Used for SQLite-based caching of resolved license data to avoid
    repeated API calls.

    Attributes:
        package_name: Name of the cached package.
        package_version: Version of the cached package.
        license_data: JSON-serialized list of LicenseLink objects.
        resolved_at: Timestamp when resolution occurred.
        expires_at: Timestamp when cache entry expires (default: 30 days from resolution).
    """

    package_name: str
    package_version: str
    license_data: str
    resolved_at: datetime
    expires_at: datetime
