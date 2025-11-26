"""License Tracker - Automated open source license attribution tool.

This package provides tools for scanning Python dependencies and generating
license attribution documentation.
"""

__version__ = "0.1.0"
__author__ = "forkrul"

from license_tracker.models import (
    CacheEntry,
    LicenseLink,
    PackageMetadata,
    PackageSpec,
)

__all__ = [
    "__version__",
    "CacheEntry",
    "LicenseLink",
    "PackageMetadata",
    "PackageSpec",
]
