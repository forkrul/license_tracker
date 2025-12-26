"""SQLite-based cache layer for license resolution results.

This module provides a persistent cache to avoid repeated API calls when
resolving license information for the same package versions.
"""

import contextlib
import json
import sqlite3
from dataclasses import asdict
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
        self._conn: Optional[sqlite3.Connection] = None
        self._init_database()

    def __enter__(self) -> "LicenseCache":
        """Enter context manager, keeping connection open."""
        self._conn = sqlite3.connect(self.db_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, closing connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextlib.contextmanager
    def _connect(self):
        """Get a database connection.

        If used as a context manager (with statement), reuses the existing
        connection. Otherwise, creates a new one and closes it after use.
        """
        if self._conn:
            yield self._conn
        else:
            conn = sqlite3.connect(self.db_path)
            try:
                yield conn
            finally:
                conn.close()

    def _init_database(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        with self._connect() as conn:
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

    def get(self, name: str, version: str) -> Optional[list[LicenseLink]]:
        """Retrieve cached license data for a package.

        Args:
            name: Package name.
            version: Package version.

        Returns:
            List of LicenseLink objects if cache hit and not expired,
            None if cache miss or expired.
        """
        row = None
        with self._connect() as conn:
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

    def get_batch(
        self, specs: list[tuple[str, str]]
    ) -> dict[tuple[str, str], list[LicenseLink]]:
        """Retrieve cached license data for multiple packages.

        Args:
            specs: List of (name, version) tuples.

        Returns:
            Dictionary mapping (name, version) -> list of LicenseLink objects.
            Only hits are included in the result.
        """
        results = {}
        # Use set to avoid duplicate lookups
        specs_set = set(specs)
        names = list({name for name, _ in specs_set})

        if not names:
            return {}

        # Chunk to avoid SQLite limits
        chunk_size = 900
        for i in range(0, len(names), chunk_size):
            chunk_names = names[i : i + chunk_size]
            placeholders = ",".join(["?"] * len(chunk_names))

            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT package_name, package_version, license_data, expires_at
                    FROM license_cache
                    WHERE package_name IN ({placeholders})
                    """,
                    chunk_names,
                )
                rows = cursor.fetchall()

                for row in rows:
                    p_name, p_version, license_data, expires_at_str = row

                    if (p_name, p_version) not in specs_set:
                        continue

                    # Check expiration
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now(UTC) >= expires_at:
                        continue

                    try:
                        license_dicts = json.loads(license_data)
                        licenses = [
                            LicenseLink(**lic_dict) for lic_dict in license_dicts
                        ]
                        results[(p_name, p_version)] = licenses
                    except (json.JSONDecodeError, TypeError, KeyError):
                        continue

        return results

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

        # Serialize license data to JSON using dataclasses.asdict
        license_dicts = [asdict(lic) for lic in licenses]
        license_data_json = json.dumps(license_dicts)

        with self._connect() as conn:
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

    def set_batch(
        self,
        items: dict[tuple[str, str], list[LicenseLink]],
    ) -> None:
        """Store license data for multiple packages in the cache.

        Args:
            items: Dictionary mapping (name, version) -> list of LicenseLink objects.
        """
        if not items:
            return

        resolved_at = datetime.now(UTC)
        expires_at = resolved_at + timedelta(days=self.ttl_days)
        resolved_at_str = resolved_at.isoformat()
        expires_at_str = expires_at.isoformat()

        data_to_insert = []
        for (name, version), licenses in items.items():
            license_dicts = [asdict(lic) for lic in licenses]
            license_data_json = json.dumps(license_dicts)
            data_to_insert.append(
                (name, version, license_data_json, resolved_at_str, expires_at_str)
            )

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.executemany(
                """
                REPLACE INTO license_cache
                (package_name, package_version, license_data, resolved_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                data_to_insert,
            )
            conn.commit()

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
        with self._connect() as conn:
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

    def info(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache information:
                - path: Path to cache database file
                - count: Number of cached entries
                - size_bytes: Database file size in bytes
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM license_cache")
            count = cursor.fetchone()[0]

        # Get database file size
        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "path": str(self.db_path),
            "count": count,
            "size_bytes": size_bytes,
        }
