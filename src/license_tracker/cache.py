"""SQLite-based cache layer for license resolution results.

This module provides a persistent cache to avoid repeated API calls when
resolving license information for the same package versions.
"""

import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

from license_tracker.models import LicenseLink, PackageSpec


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
        """Enter the runtime context related to this object."""
        self._conn = sqlite3.connect(self.db_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the runtime context related to this object."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _get_conn(self) -> tuple[sqlite3.Connection, bool]:
        """Get a database connection.

        Returns:
            Tuple containing (connection, should_close_flag).
            If should_close_flag is True, the caller is responsible for closing the connection.
        """
        if self._conn:
            return self._conn, False
        return sqlite3.connect(self.db_path), True

    def _init_database(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        conn, should_close = self._get_conn()
        try:
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
        finally:
            if should_close:
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
        conn, should_close = self._get_conn()
        try:
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
        finally:
            if should_close:
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

    def get_batch(
        self, packages: list[PackageSpec]
    ) -> dict[PackageSpec, Optional[list[LicenseLink]]]:
        """Retrieve cached license data for multiple packages.

        Args:
            packages: List of PackageSpec objects to look up.

        Returns:
            Dictionary mapping PackageSpec to list of LicenseLink objects (or None).
        """
        results: dict[PackageSpec, Optional[list[LicenseLink]]] = {
            pkg: None for pkg in packages
        }
        if not packages:
            return results

        conn, should_close = self._get_conn()
        try:
            cursor = conn.cursor()

            # Local cache for deserialized license data to avoid redundant json.loads
            # and object creation for identical license sets (e.g., many packages with MIT)
            json_cache: dict[str, list[LicenseLink]] = {}

            # SQLite limits variables (default 999 or 32766).
            # We use 2 variables per item (name, version).
            # Chunk size of 400 is safe (800 vars).
            chunk_size = 400
            for i in range(0, len(packages), chunk_size):
                chunk = packages[i : i + chunk_size]

                # Create O(1) lookup map for current chunk
                # Optimized: Map (name, version) -> list[PackageSpec]
                # This replaces the O(N^2) search in the result loop
                chunk_map: dict[tuple[str, str], list[PackageSpec]] = {}
                for pkg in chunk:
                    key = (pkg.name, pkg.version)
                    if key not in chunk_map:
                        chunk_map[key] = []
                    chunk_map[key].append(pkg)

                # Build query with proper placeholders
                # (package_name, package_version) IN ((?,?), (?,?), ...)
                placeholders = ",".join(["(?, ?)"] * len(chunk))
                query = f"""
                SELECT package_name, package_version, license_data, expires_at
                FROM license_cache
                WHERE (package_name, package_version) IN ({placeholders})
                """

                params = []
                for pkg in chunk:
                    params.extend((pkg.name, pkg.version))

                cursor.execute(query, params)
                rows = cursor.fetchall()

                # Process results
                now = datetime.now(UTC)
                for row in rows:
                    p_name, p_ver, license_data_json, expires_at_str = row

                    # Check expiry
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if now >= expires_at:
                        continue

                    if license_data_json in json_cache:
                        # Use cached object list if available
                        licenses = json_cache[license_data_json]
                        # Create a shallow copy of the list to prevent side effects
                        # if the consumer modifies the list, but keep shared LicenseLink objects
                        licenses = list(licenses)
                    else:
                        try:
                            license_dicts = json.loads(license_data_json)
                            licenses = [
                                LicenseLink(**lic_dict) for lic_dict in license_dicts
                            ]
                            # Cache the result
                            json_cache[license_data_json] = licenses
                        except (json.JSONDecodeError, TypeError, KeyError):
                            continue

                    # Map back to PackageSpec objects using O(1) lookup
                    key = (p_name, p_ver)
                    if key in chunk_map:
                        for pkg in chunk_map[key]:
                            results[pkg] = licenses

        finally:
            if should_close:
                conn.close()

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

        conn, should_close = self._get_conn()
        try:
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
        finally:
            if should_close:
                conn.close()

    def set_batch(
        self,
        items: dict[PackageSpec, list[LicenseLink]],
    ) -> None:
        """Store license data for multiple packages in the cache.

        Args:
            items: Dictionary mapping PackageSpec to list of LicenseLink objects.
        """
        if not items:
            return

        resolved_at = datetime.now(UTC)
        expires_at = resolved_at + timedelta(days=self.ttl_days)
        resolved_at_iso = resolved_at.isoformat()
        expires_at_iso = expires_at.isoformat()

        data_to_insert = []
        for spec, licenses in items.items():
            license_dicts = [asdict(lic) for lic in licenses]
            license_data_json = json.dumps(license_dicts)
            data_to_insert.append(
                (
                    spec.name,
                    spec.version,
                    license_data_json,
                    resolved_at_iso,
                    expires_at_iso,
                )
            )

        conn, should_close = self._get_conn()
        try:
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
        finally:
            if should_close:
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
        conn, should_close = self._get_conn()
        try:
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
        finally:
            if should_close:
                conn.close()

    def info(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache information:
                - path: Path to cache database file
                - count: Number of cached entries
                - size_bytes: Database file size in bytes
        """
        conn, should_close = self._get_conn()
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM license_cache")
            count = cursor.fetchone()[0]
        finally:
            if should_close:
                conn.close()

        # Get database file size
        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "path": str(self.db_path),
            "count": count,
            "size_bytes": size_bytes,
        }
