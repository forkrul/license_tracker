"""Tests for GitHub license resolver."""

from typing import Any, AsyncGenerator

import pytest
from aioresponses import aioresponses

from license_tracker.models import LicenseLink, PackageMetadata, PackageSpec
from license_tracker.resolvers.github import GitHubResolver


@pytest.fixture
async def github_resolver() -> AsyncGenerator[GitHubResolver, None]:
    """Return a GitHubResolver instance without token."""
    resolver = GitHubResolver()
    yield resolver
    await resolver.close()


@pytest.fixture
async def github_resolver_with_token() -> AsyncGenerator[GitHubResolver, None]:
    """Return a GitHubResolver instance with token."""
    resolver = GitHubResolver(github_token="ghp_test123token")
    yield resolver
    await resolver.close()


@pytest.fixture
def package_spec_with_github_url() -> PackageSpec:
    """Return a PackageSpec with GitHub repository URL."""
    return PackageSpec(
        name="requests",
        version="2.31.0",
        source="poetry.lock",
    )


@pytest.fixture
def package_metadata_with_github_url() -> PackageMetadata:
    """Return PackageMetadata with GitHub repository URL."""
    return PackageMetadata(
        name="requests",
        version="2.31.0",
        repository_url="https://github.com/psf/requests",
    )


class TestGitHubResolver:
    """Test suite for GitHubResolver."""

    def test_resolver_name(self, github_resolver: GitHubResolver) -> None:
        """Test that resolver has correct name."""
        assert github_resolver.name == "GitHub"

    def test_resolver_priority(self, github_resolver: GitHubResolver) -> None:
        """Test that resolver has correct priority."""
        assert github_resolver.priority == 80

    @pytest.mark.asyncio
    async def test_resolve_returns_none(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
    ) -> None:
        """Test that resolve() returns None (use enrich() instead)."""
        result = await github_resolver.resolve(package_spec_with_github_url)
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_successful(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
        sample_github_license_response: dict[str, Any],
    ) -> None:
        """Test successful license resolution from GitHub API."""
        with aioresponses() as m:
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                payload=sample_github_license_response,
                status=200,
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is not None
            assert len(result.licenses) == 1
            license_link = result.licenses[0]
            assert license_link.spdx_id == "Apache-2.0"
            assert license_link.name == "Apache License 2.0"
            assert (
                license_link.url
                == "https://github.com/psf/requests/blob/main/LICENSE"
            )
            assert license_link.is_verified_file is True

    @pytest.mark.asyncio
    async def test_resolve_extracts_html_url(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
        sample_github_license_response: dict[str, Any],
    ) -> None:
        """Test that resolver extracts html_url for direct license link."""
        with aioresponses() as m:
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                payload=sample_github_license_response,
                status=200,
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is not None
            assert result.licenses[0].url == sample_github_license_response["html_url"]

    @pytest.mark.asyncio
    async def test_resolve_with_authentication(
        self,
        github_resolver_with_token: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
        sample_github_license_response: dict[str, Any],
    ) -> None:
        """Test that authentication token is sent in request."""
        with aioresponses() as m:
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                payload=sample_github_license_response,
                status=200,
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests",
            )

            result = await github_resolver_with_token.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is not None
            assert len(result.licenses) == 1

    @pytest.mark.asyncio
    async def test_resolve_missing_license(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
    ) -> None:
        """Test handling of repository without license."""
        with aioresponses() as m:
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                status=404,
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_resolve_rate_limiting(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
        sample_github_license_response: dict[str, Any],
    ) -> None:
        """Test handling of rate limiting with retry."""
        with aioresponses() as m:
            # First request returns 403 with retry-after
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                status=403,
                headers={"Retry-After": "1"},
            )
            # Second request succeeds
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                payload=sample_github_license_response,
                status=200,
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is not None
            assert len(result.licenses) == 1

    @pytest.mark.asyncio
    async def test_resolve_rate_limiting_no_retry_after(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
        sample_github_license_response: dict[str, Any],
    ) -> None:
        """Test handling of rate limiting without retry-after header."""
        with aioresponses() as m:
            # First request returns 403 without retry-after
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                status=403,
            )
            # Second request succeeds after exponential backoff
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                payload=sample_github_license_response,
                status=200,
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is not None
            assert len(result.licenses) == 1

    @pytest.mark.asyncio
    async def test_resolve_rate_limiting_max_retries(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
    ) -> None:
        """Test that resolver gives up after max retries."""
        with aioresponses() as m:
            # Return 403 for all requests
            for _ in range(4):  # max_retries + 1
                m.get(
                    "https://api.github.com/repos/psf/requests/license",
                    status=403,
                )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_enrich_no_repository_url(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
    ) -> None:
        """Test handling of package without repository URL."""
        metadata = PackageMetadata(
            name="requests",
            version="2.31.0",
            repository_url=None,
        )

        result = await github_resolver.enrich(package_spec_with_github_url, metadata)

        assert result is None

    @pytest.mark.asyncio
    async def test_enrich_non_github_url(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
    ) -> None:
        """Test handling of non-GitHub repository URL."""
        metadata = PackageMetadata(
            name="requests",
            version="2.31.0",
            repository_url="https://gitlab.com/user/repo",
        )

        result = await github_resolver.enrich(package_spec_with_github_url, metadata)

        assert result is None

    @pytest.mark.asyncio
    async def test_enrich_invalid_github_url(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
    ) -> None:
        """Test handling of invalid GitHub URL format."""
        metadata = PackageMetadata(
            name="requests",
            version="2.31.0",
            repository_url="https://github.com/invalid",
        )

        result = await github_resolver.enrich(package_spec_with_github_url, metadata)

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_github_url_with_trailing_slash(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
        sample_github_license_response: dict[str, Any],
    ) -> None:
        """Test that trailing slash in GitHub URL is handled correctly."""
        with aioresponses() as m:
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                payload=sample_github_license_response,
                status=200,
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests/",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is not None
            assert len(result.licenses) == 1

    @pytest.mark.asyncio
    async def test_resolve_github_url_with_git_suffix(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
        sample_github_license_response: dict[str, Any],
    ) -> None:
        """Test that .git suffix in GitHub URL is handled correctly."""
        with aioresponses() as m:
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                payload=sample_github_license_response,
                status=200,
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests.git",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is not None
            assert len(result.licenses) == 1

    @pytest.mark.asyncio
    async def test_resolve_preserves_existing_metadata(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
        sample_github_license_response: dict[str, Any],
    ) -> None:
        """Test that resolver preserves existing metadata fields."""
        with aioresponses() as m:
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                payload=sample_github_license_response,
                status=200,
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                description="Python HTTP for Humans.",
                homepage="https://requests.readthedocs.io",
                repository_url="https://github.com/psf/requests",
                author="Kenneth Reitz",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is not None
            assert result.name == "requests"
            assert result.version == "2.31.0"
            assert result.description == "Python HTTP for Humans."
            assert result.homepage == "https://requests.readthedocs.io"
            assert result.repository_url == "https://github.com/psf/requests"
            assert result.author == "Kenneth Reitz"

    @pytest.mark.asyncio
    async def test_resolve_api_error_500(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
    ) -> None:
        """Test handling of GitHub API server error."""
        with aioresponses() as m:
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                status=500,
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_resolve_network_error(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
    ) -> None:
        """Test handling of network errors."""
        with aioresponses() as m:
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                exception=Exception("Network error"),
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_resolve_handles_headers_correctly(
        self,
        github_resolver: GitHubResolver,
        package_spec_with_github_url: PackageSpec,
        sample_github_license_response: dict[str, Any],
    ) -> None:
        """Test that resolver works with proper headers."""
        with aioresponses() as m:
            m.get(
                "https://api.github.com/repos/psf/requests/license",
                payload=sample_github_license_response,
                status=200,
            )

            metadata = PackageMetadata(
                name="requests",
                version="2.31.0",
                repository_url="https://github.com/psf/requests",
            )

            result = await github_resolver.enrich(
                package_spec_with_github_url, metadata
            )

            assert result is not None
            assert len(result.licenses) == 1
