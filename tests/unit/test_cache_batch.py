"""Unit tests for the SQLite cache layer batch operations."""

import pytest
from pathlib import Path
from license_tracker.cache import LicenseCache
from license_tracker.models import LicenseLink, PackageSpec

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
        )
    ]

class TestCacheBatchOperations:
    """Test batch cache operations."""

    def test_get_batch_basic(self, cache, sample_licenses):
        """Test retrieving multiple packages in a batch."""
        # Store some packages
        packages = [
            PackageSpec(name=f"pkg{i}", version="1.0.0")
            for i in range(5)
        ]

        # Manually set them first
        for pkg in packages:
            cache.set(pkg.name, pkg.version, sample_licenses)

        # Get batch
        results = cache.get_batch(packages)

        assert len(results) == 5
        for pkg in packages:
            assert results[pkg] is not None
            assert results[pkg][0].spdx_id == "MIT"

    def test_get_batch_mixed_hits_misses(self, cache, sample_licenses):
        """Test batch retrieval with some cache hits and some misses."""
        pkg_hit = PackageSpec(name="hit", version="1.0.0")
        pkg_miss = PackageSpec(name="miss", version="1.0.0")

        cache.set(pkg_hit.name, pkg_hit.version, sample_licenses)

        results = cache.get_batch([pkg_hit, pkg_miss])

        assert results[pkg_hit] is not None
        assert results[pkg_miss] is None

    def test_get_batch_duplicates_different_sources(self, cache, sample_licenses):
        """Test batch retrieval with duplicate packages having different sources."""
        # Same package name/version, different source
        pkg1 = PackageSpec(name="pkg", version="1.0.0", source="poetry.lock")
        pkg2 = PackageSpec(name="pkg", version="1.0.0", source="requirements.txt")

        cache.set("pkg", "1.0.0", sample_licenses)

        results = cache.get_batch([pkg1, pkg2])

        # Both should get the same license data
        assert results[pkg1] is not None
        assert results[pkg2] is not None
        assert results[pkg1] == results[pkg2]

    def test_get_batch_empty(self, cache):
        """Test get_batch with empty list."""
        results = cache.get_batch([])
        assert results == {}

    def test_set_batch_basic(self, cache, sample_licenses):
        """Test setting multiple packages in a batch."""
        packages = [
            PackageSpec(name=f"pkg{i}", version="1.0.0")
            for i in range(5)
        ]

        items = {pkg: sample_licenses for pkg in packages}
        cache.set_batch(items)

        # Verify with get
        for pkg in packages:
            result = cache.get(pkg.name, pkg.version)
            assert result is not None
            assert result[0].spdx_id == "MIT"
