
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from dataclasses import asdict

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

class TestCacheBatchOperations:
    """Test batch operations for cache."""

    def test_get_batch_empty(self, cache):
        """Test get_batch with empty list."""
        assert cache.get_batch([]) == {}

    def test_set_batch_empty(self, cache):
        """Test set_batch with empty dict."""
        cache.set_batch({})
        assert cache.info()["count"] == 0

    def test_batch_operations(self, cache, sample_licenses):
        """Test set_batch and get_batch work together."""
        from license_tracker.models import PackageSpec

        packages = [
            PackageSpec(name=f"pkg-{i}", version="1.0.0")
            for i in range(10)
        ]

        # Prepare data to set
        items = {p: sample_licenses for p in packages}

        # Set batch
        cache.set_batch(items)

        # Check count
        assert cache.info()["count"] == 10

        # Get batch
        results = cache.get_batch(packages)
        assert len(results) == 10
        for p in packages:
            assert p in results
            assert len(results[p]) == 2

    def test_get_batch_partial_hits(self, cache, sample_licenses):
        """Test get_batch where only some items are in cache."""
        from license_tracker.models import PackageSpec

        cached_pkg = PackageSpec("cached", "1.0.0")
        uncached_pkg = PackageSpec("uncached", "1.0.0")

        cache.set(cached_pkg.name, cached_pkg.version, sample_licenses)

        results = cache.get_batch([cached_pkg, uncached_pkg])

        assert len(results) == 1
        assert cached_pkg in results
        assert uncached_pkg not in results

    def test_get_batch_expiration(self, cache, sample_licenses):
        """Test that get_batch filters expired items."""
        from license_tracker.models import PackageSpec
        import sqlite3

        p1 = PackageSpec("valid", "1.0.0")
        p2 = PackageSpec("expired", "1.0.0")

        # Add valid item
        cache.set(p1.name, p1.version, sample_licenses)

        # Add expired item manually
        resolved_at = datetime.now(UTC) - timedelta(days=31)
        expires_at = resolved_at + timedelta(days=30)

        conn = sqlite3.connect(cache.db_path)
        conn.execute(
            """
            INSERT INTO license_cache
            (package_name, package_version, license_data, resolved_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                p2.name,
                p2.version,
                json.dumps([asdict(l) for l in sample_licenses]),
                resolved_at.isoformat(),
                expires_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        results = cache.get_batch([p1, p2])
        assert len(results) == 1
        assert p1 in results
        assert p2 not in results
