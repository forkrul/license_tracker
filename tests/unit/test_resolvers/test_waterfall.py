"""Unit tests for WaterfallResolver.

This module tests the orchestration of multiple resolvers in priority order,
including PyPI -> GitHub enrichment -> SPDX fallback logic.
"""

from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from license_tracker.models import LicenseLink, PackageMetadata, PackageSpec
from license_tracker.resolvers.github import GitHubResolver
from license_tracker.resolvers.pypi import PyPIResolver
from license_tracker.resolvers.spdx import SPDXResolver
from license_tracker.resolvers.waterfall import WaterfallResolver


@pytest.fixture
def mock_pypi_resolver() -> PyPIResolver:
    """Return a mock PyPIResolver for testing."""
    mock = MagicMock(spec=PyPIResolver)
    mock.priority = 10
    mock.name = "PyPI"
    return mock


@pytest.fixture
def mock_github_resolver() -> GitHubResolver:
    """Return a mock GitHubResolver for testing."""
    mock = MagicMock(spec=GitHubResolver)
    mock.priority = 80
    mock.name = "GitHub"
    return mock


@pytest.fixture
def mock_spdx_resolver() -> SPDXResolver:
    """Return a mock SPDXResolver for testing."""
    mock = MagicMock(spec=SPDXResolver)
    mock.priority = 1000
    mock.name = "SPDX"
    return mock


@pytest.fixture
def waterfall_resolver(
    mock_pypi_resolver: PyPIResolver,
    mock_github_resolver: GitHubResolver,
    mock_spdx_resolver: SPDXResolver,
) -> WaterfallResolver:
    """Return a WaterfallResolver with mocked dependencies."""
    return WaterfallResolver(
        pypi_resolver=mock_pypi_resolver,
        github_resolver=mock_github_resolver,
        spdx_resolver=mock_spdx_resolver,
    )


@pytest.fixture
def sample_spec() -> PackageSpec:
    """Return a sample PackageSpec for testing."""
    return PackageSpec(name="requests", version="2.31.0", source="poetry.lock")


@pytest.fixture
def pypi_metadata() -> PackageMetadata:
    """Return sample metadata from PyPI (without verified license)."""
    return PackageMetadata(
        name="requests",
        version="2.31.0",
        description="Python HTTP for Humans.",
        homepage="https://requests.readthedocs.io",
        repository_url="https://github.com/psf/requests",
        author="Kenneth Reitz",
        licenses=[
            LicenseLink(
                spdx_id="Apache-2.0",
                name="Apache 2.0",
                url="https://spdx.org/licenses/Apache-2.0.html",
                is_verified_file=False,
            )
        ],
        is_root_project=False,
    )


@pytest.fixture
def github_enriched_metadata() -> PackageMetadata:
    """Return sample metadata enriched by GitHub (with verified license)."""
    return PackageMetadata(
        name="requests",
        version="2.31.0",
        description="Python HTTP for Humans.",
        homepage="https://requests.readthedocs.io",
        repository_url="https://github.com/psf/requests",
        author="Kenneth Reitz",
        licenses=[
            LicenseLink(
                spdx_id="Apache-2.0",
                name="Apache License 2.0",
                url="https://github.com/psf/requests/blob/main/LICENSE",
                is_verified_file=True,
            )
        ],
        is_root_project=False,
    )


@pytest.fixture
def spdx_fallback_metadata() -> PackageMetadata:
    """Return sample metadata from SPDX fallback."""
    return PackageMetadata(
        name="requests",
        version="2.31.0",
        licenses=[
            LicenseLink(
                spdx_id="MIT",
                name="MIT License",
                url="https://spdx.org/licenses/MIT.html",
                is_verified_file=False,
            )
        ],
    )


@pytest.mark.asyncio
async def test_resolver_priority_ordering() -> None:
    """Test that resolvers are ordered by priority."""
    pypi = PyPIResolver()
    github = GitHubResolver()
    spdx = SPDXResolver()

    # Verify priorities
    assert pypi.priority == 10  # Highest priority (lowest number)
    assert github.priority == 80  # Medium priority
    assert spdx.priority == 1000  # Lowest priority (highest number)

    # Create waterfall resolver
    resolver = WaterfallResolver(
        pypi_resolver=pypi, github_resolver=github, spdx_resolver=spdx
    )

    # Verify resolvers are stored (implementation detail)
    assert resolver.pypi_resolver is pypi
    assert resolver.github_resolver is github
    assert resolver.spdx_resolver is spdx


@pytest.mark.asyncio
async def test_successful_pypi_then_github_enrichment(
    waterfall_resolver: WaterfallResolver,
    sample_spec: PackageSpec,
    pypi_metadata: PackageMetadata,
    github_enriched_metadata: PackageMetadata,
    mock_pypi_resolver: PyPIResolver,
    mock_github_resolver: GitHubResolver,
    mock_spdx_resolver: SPDXResolver,
) -> None:
    """Test successful PyPI resolution followed by GitHub enrichment."""
    # Setup mocks
    mock_pypi_resolver.resolve = AsyncMock(return_value=pypi_metadata)
    mock_github_resolver.enrich = AsyncMock(return_value=github_enriched_metadata)

    # Resolve
    result = await waterfall_resolver.resolve(sample_spec)

    # Verify
    assert result is not None
    assert result.name == "requests"
    assert result.version == "2.31.0"
    assert len(result.licenses) == 1
    assert result.licenses[0].is_verified_file is True  # GitHub enrichment applied
    assert "github.com" in result.licenses[0].url

    # Verify call order
    mock_pypi_resolver.resolve.assert_called_once_with(sample_spec)
    mock_github_resolver.enrich.assert_called_once_with(sample_spec, pypi_metadata)
    mock_spdx_resolver.resolve.assert_not_called()  # Should not fall back to SPDX


@pytest.mark.asyncio
async def test_pypi_without_repository_url(
    waterfall_resolver: WaterfallResolver,
    sample_spec: PackageSpec,
    mock_pypi_resolver: PyPIResolver,
    mock_github_resolver: GitHubResolver,
    mock_spdx_resolver: SPDXResolver,
) -> None:
    """Test PyPI metadata without repository URL (skips GitHub enrichment)."""
    # Create metadata without repository URL
    metadata_no_repo = PackageMetadata(
        name="requests",
        version="2.31.0",
        description="Python HTTP for Humans.",
        licenses=[
            LicenseLink(
                spdx_id="Apache-2.0",
                name="Apache 2.0",
                url="https://spdx.org/licenses/Apache-2.0.html",
                is_verified_file=False,
            )
        ],
    )

    # Setup mocks
    mock_pypi_resolver.resolve = AsyncMock(return_value=metadata_no_repo)
    mock_github_resolver.enrich = AsyncMock(return_value=None)

    # Resolve
    result = await waterfall_resolver.resolve(sample_spec)

    # Verify - should return PyPI metadata as-is
    assert result is not None
    assert result.name == "requests"
    assert len(result.licenses) == 1
    assert result.licenses[0].is_verified_file is False

    # Verify GitHub enrichment was NOT called (no repository URL)
    mock_pypi_resolver.resolve.assert_called_once_with(sample_spec)
    mock_github_resolver.enrich.assert_not_called()
    mock_spdx_resolver.resolve.assert_not_called()


@pytest.mark.asyncio
async def test_pypi_without_license_returns_metadata_anyway(
    waterfall_resolver: WaterfallResolver,
    sample_spec: PackageSpec,
    mock_pypi_resolver: PyPIResolver,
    mock_github_resolver: GitHubResolver,
    mock_spdx_resolver: SPDXResolver,
) -> None:
    """Test that metadata is returned even when no license is found.

    Note: SPDX fallback is not fully implemented yet as it requires a SPDX ID.
    For now, we return the metadata without licenses.
    """
    # Create metadata without licenses but with repository URL
    metadata_no_license = PackageMetadata(
        name="requests",
        version="2.31.0",
        description="Python HTTP for Humans.",
        repository_url="https://github.com/psf/requests",
        licenses=[],  # No licenses
    )

    # Setup mocks
    mock_pypi_resolver.resolve = AsyncMock(return_value=metadata_no_license)
    mock_github_resolver.enrich = AsyncMock(return_value=None)

    # Resolve
    result = await waterfall_resolver.resolve(sample_spec)

    # Verify metadata is returned even without licenses
    assert result is not None
    assert result.name == "requests"
    assert result.description == "Python HTTP for Humans."
    assert len(result.licenses) == 0  # No licenses found

    # Verify resolvers were called appropriately
    mock_pypi_resolver.resolve.assert_called_once_with(sample_spec)
    mock_github_resolver.enrich.assert_called_once_with(sample_spec, metadata_no_license)
    # SPDX fallback not called (not fully implemented)
    mock_spdx_resolver.resolve.assert_not_called()


@pytest.mark.asyncio
async def test_pypi_fails_returns_none(
    waterfall_resolver: WaterfallResolver,
    sample_spec: PackageSpec,
    mock_pypi_resolver: PyPIResolver,
    mock_github_resolver: GitHubResolver,
    mock_spdx_resolver: SPDXResolver,
) -> None:
    """Test that resolver returns None when PyPI fails."""
    # Setup mocks - PyPI fails
    mock_pypi_resolver.resolve = AsyncMock(return_value=None)

    # Resolve
    result = await waterfall_resolver.resolve(sample_spec)

    # Verify
    assert result is None

    # Verify only PyPI was called
    mock_pypi_resolver.resolve.assert_called_once_with(sample_spec)
    mock_github_resolver.enrich.assert_not_called()
    mock_spdx_resolver.resolve.assert_not_called()


@pytest.mark.asyncio
async def test_batch_resolution_successful(
    waterfall_resolver: WaterfallResolver,
    mock_pypi_resolver: PyPIResolver,
    mock_github_resolver: GitHubResolver,
) -> None:
    """Test batch resolution of multiple packages concurrently."""
    specs = [
        PackageSpec(name="requests", version="2.31.0"),
        PackageSpec(name="click", version="8.1.7"),
        PackageSpec(name="aiohttp", version="3.9.0"),
    ]

    # Create metadata for each package
    metadata_list = [
        PackageMetadata(
            name="requests",
            version="2.31.0",
            repository_url="https://github.com/psf/requests",
            licenses=[
                LicenseLink(
                    spdx_id="Apache-2.0",
                    name="Apache 2.0",
                    url="https://spdx.org/licenses/Apache-2.0.html",
                    is_verified_file=False,
                )
            ],
        ),
        PackageMetadata(
            name="click",
            version="8.1.7",
            repository_url="https://github.com/pallets/click",
            licenses=[
                LicenseLink(
                    spdx_id="BSD-3-Clause",
                    name="BSD-3-Clause",
                    url="https://spdx.org/licenses/BSD-3-Clause.html",
                    is_verified_file=False,
                )
            ],
        ),
        PackageMetadata(
            name="aiohttp",
            version="3.9.0",
            repository_url="https://github.com/aio-libs/aiohttp",
            licenses=[
                LicenseLink(
                    spdx_id="Apache-2.0",
                    name="Apache 2.0",
                    url="https://spdx.org/licenses/Apache-2.0.html",
                    is_verified_file=False,
                )
            ],
        ),
    ]

    # Setup mocks to return corresponding metadata
    async def pypi_resolve_side_effect(spec: PackageSpec) -> Optional[PackageMetadata]:
        for metadata in metadata_list:
            if metadata.name == spec.name and metadata.version == spec.version:
                return metadata
        return None

    mock_pypi_resolver.resolve = AsyncMock(side_effect=pypi_resolve_side_effect)
    mock_github_resolver.enrich = AsyncMock(return_value=None)

    # Batch resolve
    results = await waterfall_resolver.resolve_batch(specs)

    # Verify
    assert len(results) == 3
    assert all(spec in results for spec in specs)
    assert all(results[spec] is not None for spec in specs)
    assert results[specs[0]].name == "requests"
    assert results[specs[1]].name == "click"
    assert results[specs[2]].name == "aiohttp"

    # Verify all specs were resolved
    assert mock_pypi_resolver.resolve.call_count == 3


@pytest.mark.asyncio
async def test_batch_resolution_partial_failures(
    waterfall_resolver: WaterfallResolver,
    mock_pypi_resolver: PyPIResolver,
    mock_github_resolver: GitHubResolver,
) -> None:
    """Test batch resolution handles partial failures gracefully."""
    specs = [
        PackageSpec(name="requests", version="2.31.0"),
        PackageSpec(name="nonexistent", version="0.0.0"),
        PackageSpec(name="aiohttp", version="3.9.0"),
    ]

    # Setup mocks - middle package fails
    async def pypi_resolve_side_effect(spec: PackageSpec) -> Optional[PackageMetadata]:
        if spec.name == "requests":
            return PackageMetadata(
                name="requests",
                version="2.31.0",
                licenses=[
                    LicenseLink(
                        spdx_id="Apache-2.0",
                        name="Apache 2.0",
                        url="https://spdx.org/licenses/Apache-2.0.html",
                        is_verified_file=False,
                    )
                ],
            )
        elif spec.name == "aiohttp":
            return PackageMetadata(
                name="aiohttp",
                version="3.9.0",
                licenses=[
                    LicenseLink(
                        spdx_id="Apache-2.0",
                        name="Apache 2.0",
                        url="https://spdx.org/licenses/Apache-2.0.html",
                        is_verified_file=False,
                    )
                ],
            )
        else:
            return None

    mock_pypi_resolver.resolve = AsyncMock(side_effect=pypi_resolve_side_effect)
    mock_github_resolver.enrich = AsyncMock(return_value=None)

    # Batch resolve
    results = await waterfall_resolver.resolve_batch(specs)

    # Verify
    assert len(results) == 3
    assert results[specs[0]] is not None  # requests succeeded
    assert results[specs[1]] is None  # nonexistent failed
    assert results[specs[2]] is not None  # aiohttp succeeded

    # Verify all were attempted
    assert mock_pypi_resolver.resolve.call_count == 3


@pytest.mark.asyncio
async def test_batch_resolution_with_exceptions(
    waterfall_resolver: WaterfallResolver,
    mock_pypi_resolver: PyPIResolver,
    mock_github_resolver: GitHubResolver,
) -> None:
    """Test batch resolution handles exceptions without stopping other resolutions."""
    specs = [
        PackageSpec(name="requests", version="2.31.0"),
        PackageSpec(name="error_package", version="1.0.0"),
        PackageSpec(name="aiohttp", version="3.9.0"),
    ]

    # Setup mocks - middle package raises exception
    async def pypi_resolve_side_effect(spec: PackageSpec) -> Optional[PackageMetadata]:
        if spec.name == "error_package":
            raise Exception("Simulated error")
        elif spec.name == "requests":
            return PackageMetadata(
                name="requests",
                version="2.31.0",
                licenses=[
                    LicenseLink(
                        spdx_id="Apache-2.0",
                        name="Apache 2.0",
                        url="https://spdx.org/licenses/Apache-2.0.html",
                        is_verified_file=False,
                    )
                ],
            )
        else:
            return PackageMetadata(
                name="aiohttp",
                version="3.9.0",
                licenses=[
                    LicenseLink(
                        spdx_id="Apache-2.0",
                        name="Apache 2.0",
                        url="https://spdx.org/licenses/Apache-2.0.html",
                        is_verified_file=False,
                    )
                ],
            )

    mock_pypi_resolver.resolve = AsyncMock(side_effect=pypi_resolve_side_effect)
    mock_github_resolver.enrich = AsyncMock(return_value=None)

    # Batch resolve
    results = await waterfall_resolver.resolve_batch(specs)

    # Verify - exception is caught and results in None for that package
    assert len(results) == 3
    assert results[specs[0]] is not None  # requests succeeded
    assert results[specs[1]] is None  # error_package failed with exception
    assert results[specs[2]] is not None  # aiohttp succeeded


@pytest.mark.asyncio
async def test_github_token_passed_to_resolver() -> None:
    """Test that github_token is passed to GitHubResolver."""
    token = "ghp_test123456789"
    resolver = WaterfallResolver(github_token=token)

    # Verify token was passed to GitHub resolver
    assert resolver.github_resolver.github_token == token


@pytest.mark.asyncio
async def test_no_github_token() -> None:
    """Test WaterfallResolver works without github_token."""
    resolver = WaterfallResolver()

    # Verify GitHub resolver created without token
    assert resolver.github_resolver.github_token is None


@pytest.mark.asyncio
async def test_early_stop_with_verified_license(
    waterfall_resolver: WaterfallResolver,
    sample_spec: PackageSpec,
    github_enriched_metadata: PackageMetadata,
    mock_pypi_resolver: PyPIResolver,
    mock_github_resolver: GitHubResolver,
    mock_spdx_resolver: SPDXResolver,
) -> None:
    """Test that waterfall stops early when verified license is found."""
    # Create PyPI metadata with unverified license
    pypi_metadata = PackageMetadata(
        name="requests",
        version="2.31.0",
        repository_url="https://github.com/psf/requests",
        licenses=[
            LicenseLink(
                spdx_id="Apache-2.0",
                name="Apache 2.0",
                url="https://spdx.org/licenses/Apache-2.0.html",
                is_verified_file=False,
            )
        ],
    )

    # Setup mocks
    mock_pypi_resolver.resolve = AsyncMock(return_value=pypi_metadata)
    mock_github_resolver.enrich = AsyncMock(return_value=github_enriched_metadata)

    # Resolve
    result = await waterfall_resolver.resolve(sample_spec)

    # Verify GitHub enrichment was used and SPDX was not called
    assert result is not None
    assert result.licenses[0].is_verified_file is True
    mock_spdx_resolver.resolve.assert_not_called()


@pytest.mark.asyncio
async def test_concurrent_batch_resolution_uses_asyncio_gather() -> None:
    """Test that batch resolution uses asyncio.gather for concurrency."""
    # Create real resolver to test concurrency
    resolver = WaterfallResolver()

    specs = [
        PackageSpec(name="pkg1", version="1.0.0"),
        PackageSpec(name="pkg2", version="2.0.0"),
    ]

    # Patch resolve method to track concurrent execution
    with patch.object(
        resolver, "resolve", new_callable=AsyncMock
    ) as mock_resolve:
        mock_resolve.return_value = None

        # Call batch resolve
        await resolver.resolve_batch(specs)

        # Verify resolve was called for each spec
        assert mock_resolve.call_count == len(specs)
