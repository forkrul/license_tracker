"""SQLite-based cache layer for license resolution results.

This module provides a persistent cache to avoid repeated API calls when
resolving license information for the same package versions.
"""

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

from license_tracker.models import LicenseLink


class LicenseCache:
    """SQLite cache for storing resolved license metadata.

    This cache stores license resolution results with a 30-day TTL to
    minimize API calls to PyPI, GitHub, and other sources.

    Attributes:
        db_path: Path to the SQLite database file.
        ttl_days: Number of days before cache entries expire (default: 30).
    """

    DEFAULT_TTL_DAYS = 30

    def __init__(
        self,
        db_path: Optional[Path] = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ):
        """Initialize the license cache.

        Args:
            db_path: Path to SQLite database. If None, uses
                ~/.cache/license_tracker/cache.db.
            ttl_days: Number of days before cache entries expire.
        """
        if db_path is None:
            cache_dir = Path.home() / ".cache" / "license_tracker"
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = cache_dir / "cache.db"

        self.db_path = db_path
        self.ttl_days = ttl_days
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create the main cache table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS license_cache (
                package_name TEXT NOT NULL,
                package_version TEXT NOT NULL,
                license_data TEXT NOT NULL,
                resolved_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                PRIMARY KEY (package_name, package_version)
            )
            """
        )

        # Create index on expires_at for efficient TTL queries
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_expires
            ON license_cache(expires_at)
            """
        )

        conn.commit()
        conn.close()

    def get(self, name: str, version: str) -> Optional[list[LicenseLink]]:
        """Retrieve cached license data for a package.

        Args:
            name: Package name.
            version: Package version.

        Returns:
            List of LicenseLink objects if cache hit and not expired,
            None if cache miss or expired.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT license_data, expires_at
            FROM license_cache
            WHERE package_name = ? AND package_version = ?
            """,
            (name, version),
        )

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        license_data_json, expires_at_str = row

        # Check if entry has expired
        expires_at = datetime.fromisoformat(expires_at_str)
        if datetime.now(UTC) >= expires_at:
            return None

        # Deserialize license data
        try:
            license_dicts = json.loads(license_data_json)
            licenses = [LicenseLink(**lic_dict) for lic_dict in license_dicts]
            return licenses
        except (json.JSONDecodeError, TypeError, KeyError):
            # If data is corrupted, treat as cache miss
            return None

    def set(
        self,
        name: str,
        version: str,
        licenses: list[LicenseLink],
    ) -> None:
        """Store license data in the cache.

        Args:
            name: Package name.
            version: Package version.
            licenses: List of resolved LicenseLink objects.
        """
        resolved_at = datetime.now(UTC)
        expires_at = resolved_at + timedelta(days=self.ttl_days)

        # Serialize license data to JSON
        license_dicts = [
            {
                "spdx_id": lic.spdx_id,
                "name": lic.name,
                "url": lic.url,
                "is_verified_file": lic.is_verified_file,
            }
            for lic in licenses
        ]
        license_data_json = json.dumps(license_dicts)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Use REPLACE to handle both insert and update
        cursor.execute(
            """
            REPLACE INTO license_cache
            (package_name, package_version, license_data, resolved_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                version,
                license_data_json,
                resolved_at.isoformat(),
                expires_at.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

    def clear(
        self,
        package: Optional[str] = None,
        version: Optional[str] = None,
    ) -> None:
        """Clear cache entries.

        Args:
            package: If specified, clear only this package.
                If None, clear all entries.
            version: If specified (with package), clear only this
                specific version. Ignored if package is None.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if package is None:
            # Clear all entries
            cursor.execute("DELETE FROM license_cache")
        elif version is None:
            # Clear all versions of a specific package
            cursor.execute(
                "DELETE FROM license_cache WHERE package_name = ?",
                (package,),
            )
        else:
            # Clear specific package version
            cursor.execute(
                """
                DELETE FROM license_cache
                WHERE package_name = ? AND package_version = ?
                """,
                (package, version),
            )

        conn.commit()
        conn.close()

    def info(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache information:
                - path: Path to cache database file
                - count: Number of cached entries
                - size_bytes: Database file size in bytes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM license_cache")
        count = cursor.fetchone()[0]

        conn.close()

        # Get database file size
        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "path": str(self.db_path),
            "count": count,
            "size_bytes": size_bytes,
        }
