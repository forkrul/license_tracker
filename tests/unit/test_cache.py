"""Unit tests for the SQLite cache layer."""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from license_tracker.cache import LicenseCache
from license_tracker.models import LicenseLink


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory for testing."""
    cache_dir = tmp_path / ".cache" / "license_tracker"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def cache(temp_cache_dir):
    """Create a LicenseCache instance with temporary storage."""
    db_path = temp_cache_dir / "cache.db"
    return LicenseCache(db_path=db_path)


@pytest.fixture
def sample_licenses():
    """Sample license data for testing."""
    return [
        LicenseLink(
            spdx_id="MIT",
            name="MIT License",
            url="https://github.com/example/repo/blob/main/LICENSE",
            is_verified_file=True,
        ),
        LicenseLink(
            spdx_id="Apache-2.0",
            name="Apache License 2.0",
            url="https://spdx.org/licenses/Apache-2.0.html",
            is_verified_file=False,
        ),
    ]


class TestCacheBasicOperations:
    """Test basic cache storage and retrieval."""

    def test_set_and_get_cache_entry(self, cache, sample_licenses):
        """Test storing and retrieving a cache entry."""
        # Store cache entry
        cache.set("requests", "2.31.0", sample_licenses)

        # Retrieve cache entry
        result = cache.get("requests", "2.31.0")

        # Verify result
        assert result is not None
        assert len(result) == 2
        assert result[0].spdx_id == "MIT"
        assert result[0].name == "MIT License"
        assert result[0].url == "https://github.com/example/repo/blob/main/LICENSE"
        assert result[0].is_verified_file is True
        assert result[1].spdx_id == "Apache-2.0"
        assert result[1].is_verified_file is False

    def test_get_nonexistent_entry(self, cache):
        """Test cache miss returns None."""
        result = cache.get("nonexistent", "1.0.0")
        assert result is None

    def test_update_existing_entry(self, cache, sample_licenses):
        """Test updating an existing cache entry."""
        # Store initial entry
        cache.set("requests", "2.31.0", sample_licenses)

        # Update with new license data
        new_licenses = [
            LicenseLink(
                spdx_id="BSD-3-Clause",
                name="BSD 3-Clause License",
                url="https://opensource.org/licenses/BSD-3-Clause",
                is_verified_file=False,
            )
        ]
        cache.set("requests", "2.31.0", new_licenses)

        # Verify update
        result = cache.get("requests", "2.31.0")
        assert result is not None
        assert len(result) == 1
        assert result[0].spdx_id == "BSD-3-Clause"

    def test_different_versions_stored_separately(self, cache, sample_licenses):
        """Test that different versions of the same package are cached separately."""
        license_v1 = [sample_licenses[0]]
        license_v2 = [sample_licenses[1]]

        cache.set("mypackage", "1.0.0", license_v1)
        cache.set("mypackage", "2.0.0", license_v2)

        result_v1 = cache.get("mypackage", "1.0.0")
        result_v2 = cache.get("mypackage", "2.0.0")

        assert result_v1 is not None
        assert result_v2 is not None
        assert result_v1[0].spdx_id == "MIT"
        assert result_v2[0].spdx_id == "Apache-2.0"


class TestCacheTTL:
    """Test cache TTL expiration."""

    def test_fresh_entry_is_valid(self, cache, sample_licenses):
        """Test that freshly stored entries are valid."""
        cache.set("requests", "2.31.0", sample_licenses)
        result = cache.get("requests", "2.31.0")
        assert result is not None

    def test_expired_entry_returns_none(self, cache, sample_licenses):
        """Test that expired entries are treated as cache miss."""
        # Store entry with manipulated timestamp (31 days ago)
        old_resolved_at = datetime.now(UTC) - timedelta(days=31)
        old_expires_at = old_resolved_at + timedelta(days=30)

        # Directly insert expired entry
        import sqlite3

        conn = sqlite3.connect(cache.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO license_cache
            (package_name, package_version, license_data, resolved_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "requests",
                "2.31.0",
                json.dumps([license.__dict__ for license in sample_licenses]),
                old_resolved_at.isoformat(),
                old_expires_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        # Attempt to retrieve expired entry
        result = cache.get("requests", "2.31.0")
        assert result is None

    def test_entry_expiring_today_is_valid(self, cache, sample_licenses):
        """Test that entries expiring today are still considered valid."""
        # Store entry that expires in 1 hour
        resolved_at = datetime.now(UTC) - timedelta(days=30) + timedelta(hours=1)
        expires_at = resolved_at + timedelta(days=30)

        import sqlite3

        conn = sqlite3.connect(cache.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO license_cache
            (package_name, package_version, license_data, resolved_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "requests",
                "2.31.0",
                json.dumps([license.__dict__ for license in sample_licenses]),
                resolved_at.isoformat(),
                expires_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        # Should still be valid
        result = cache.get("requests", "2.31.0")
        assert result is not None


class TestCacheClear:
    """Test cache clearing operations."""

    def test_clear_specific_package(self, cache, sample_licenses):
        """Test clearing a specific package from cache."""
        # Store multiple packages
        cache.set("requests", "2.31.0", sample_licenses)
        cache.set("flask", "2.3.0", sample_licenses)

        # Clear specific package
        cache.clear(package="requests")

        # Verify requests is cleared but flask remains
        assert cache.get("requests", "2.31.0") is None
        assert cache.get("flask", "2.3.0") is not None

    def test_clear_specific_package_version(self, cache, sample_licenses):
        """Test clearing a specific package version from cache."""
        # Store multiple versions
        cache.set("requests", "2.31.0", sample_licenses)
        cache.set("requests", "2.30.0", sample_licenses)

        # Clear specific version
        cache.clear(package="requests", version="2.31.0")

        # Verify only 2.31.0 is cleared
        assert cache.get("requests", "2.31.0") is None
        assert cache.get("requests", "2.30.0") is not None

    def test_clear_all_packages(self, cache, sample_licenses):
        """Test clearing all packages from cache."""
        # Store multiple packages
        cache.set("requests", "2.31.0", sample_licenses)
        cache.set("flask", "2.3.0", sample_licenses)
        cache.set("django", "4.2.0", sample_licenses)

        # Clear all
        cache.clear()

        # Verify all are cleared
        assert cache.get("requests", "2.31.0") is None
        assert cache.get("flask", "2.3.0") is None
        assert cache.get("django", "4.2.0") is None

    def test_clear_nonexistent_package(self, cache):
        """Test clearing a nonexistent package does not raise error."""
        # Should not raise any exception
        cache.clear(package="nonexistent")


class TestCacheInfo:
    """Test cache information retrieval."""

    def test_info_empty_cache(self, cache):
        """Test info() on empty cache."""
        info = cache.info()
        assert info["count"] == 0
        assert info["size_bytes"] > 0  # Database file exists with schema

    def test_info_with_entries(self, cache, sample_licenses):
        """Test info() with multiple entries."""
        # Store multiple entries
        cache.set("requests", "2.31.0", sample_licenses)
        cache.set("flask", "2.3.0", sample_licenses)
        cache.set("django", "4.2.0", sample_licenses)

        info = cache.info()
        assert info["count"] == 3
        assert info["size_bytes"] > 0
        assert isinstance(info["size_bytes"], int)

    def test_info_after_clear(self, cache, sample_licenses):
        """Test info() after clearing cache."""
        # Store and then clear
        cache.set("requests", "2.31.0", sample_licenses)
        cache.clear()

        info = cache.info()
        assert info["count"] == 0


class TestCacheInitialization:
    """Test cache initialization and database creation."""

    def test_database_created_on_init(self, temp_cache_dir):
        """Test that database file is created on initialization."""
        db_path = temp_cache_dir / "test_cache.db"
        assert not db_path.exists()

        cache = LicenseCache(db_path=db_path)

        assert db_path.exists()

    def test_table_schema_exists(self, cache):
        """Test that the expected table schema is created."""
        import sqlite3

        conn = sqlite3.connect(cache.db_path)
        cursor = conn.cursor()

        # Check table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='license_cache'"
        )
        assert cursor.fetchone() is not None

        # Check columns
        cursor.execute("PRAGMA table_info(license_cache)")
        columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {
            "package_name",
            "package_version",
            "license_data",
            "resolved_at",
            "expires_at",
        }
        assert columns == expected_columns

        conn.close()

    def test_purge_expired_on_init(self, temp_cache_dir, sample_licenses):
        """Test that expired entries are purged on cache initialization."""
        import sqlite3

        db_path = temp_cache_dir / "purge_test.db"
        cache = LicenseCache(db_path=db_path)

        # Manually insert fresh and expired entries
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Expired entry (31 days old)
        expired_resolved_at = datetime.now(UTC) - timedelta(days=31)
        expired_expires_at = expired_resolved_at + timedelta(days=30)
        cursor.execute(
            """
            INSERT INTO license_cache (package_name, package_version, license_data, resolved_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "expired-pkg",
                "1.0.0",
                "[]",
                expired_resolved_at.isoformat(),
                expired_expires_at.isoformat(),
            ),
        )

        # Fresh entry
        fresh_resolved_at = datetime.now(UTC)
        fresh_expires_at = fresh_resolved_at + timedelta(days=30)
        cursor.execute(
            """
            INSERT INTO license_cache (package_name, package_version, license_data, resolved_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "fresh-pkg",
                "1.0.0",
                "[]",
                fresh_resolved_at.isoformat(),
                fresh_expires_at.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        # Re-initialize cache to trigger purge
        reinitialized_cache = LicenseCache(db_path=db_path)
        info = reinitialized_cache.info()

        # Verify that only the fresh entry remains
        assert info["count"] == 1
        assert reinitialized_cache.get("fresh-pkg", "1.0.0") is not None
        assert reinitialized_cache.get("expired-pkg", "1.0.0") is None

    def test_index_on_expires_at(self, cache):
        """Test that index on expires_at is created."""
        import sqlite3

        conn = sqlite3.connect(cache.db_path)
        cursor = conn.cursor()

        # Check index exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_expires'"
        )
        result = cursor.fetchone()
        assert result is not None

        conn.close()


class TestCacheEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_license_list(self, cache):
        """Test storing an empty license list."""
        cache.set("mypackage", "1.0.0", [])
        result = cache.get("mypackage", "1.0.0")
        assert result is not None
        assert result == []

    def test_special_characters_in_package_name(self, cache, sample_licenses):
        """Test package names with special characters."""
        cache.set("my-package.name_v2", "1.0.0", sample_licenses)
        result = cache.get("my-package.name_v2", "1.0.0")
        assert result is not None
        assert len(result) == 2

    def test_version_with_special_format(self, cache, sample_licenses):
        """Test versions with complex formats."""
        versions = ["1.0.0a1", "2.3.4rc1", "1.2.3.post1", "0.0.1.dev456"]
        for version in versions:
            cache.set("mypackage", version, sample_licenses)
            result = cache.get("mypackage", version)
            assert result is not None

    def test_cache_persistence(self, temp_cache_dir, sample_licenses):
        """Test that cache persists across instances."""
        db_path = temp_cache_dir / "persistent_cache.db"

        # Create first cache instance and store data
        cache1 = LicenseCache(db_path=db_path)
        cache1.set("requests", "2.31.0", sample_licenses)

        # Create second cache instance with same path
        cache2 = LicenseCache(db_path=db_path)
        result = cache2.get("requests", "2.31.0")

        assert result is not None
        assert len(result) == 2
        assert result[0].spdx_id == "MIT"
