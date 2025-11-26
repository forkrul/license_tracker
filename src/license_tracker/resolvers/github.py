"""GitHub license resolver.

Fetches license information from GitHub's API to get direct links to LICENSE files.
"""

import asyncio
import re
from typing import Optional
from urllib.parse import urlparse

import aiohttp

from license_tracker.models import LicenseLink, PackageMetadata, PackageSpec
from license_tracker.resolvers.base import BaseResolver


class GitHubResolver(BaseResolver):
    """Resolver that fetches license information from GitHub's API.

    Uses GitHub's license API endpoint to get direct links to LICENSE files
    in repositories. Supports authentication via GitHub token for higher
    rate limits.

    Attributes:
        github_token: Optional GitHub personal access token for authentication.
    """

    def __init__(self, github_token: Optional[str] = None) -> None:
        """Initialize GitHubResolver.

        Args:
            github_token: Optional GitHub personal access token for API authentication.
                Increases rate limit from 60 to 5000 requests/hour.
        """
        self.github_token = github_token
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        """Return the resolver name.

        Returns:
            "GitHub"
        """
        return "GitHub"

    @property
    def priority(self) -> int:
        """Return resolver priority.

        Returns:
            80 (higher priority than generic SPDX, lower than PyPI)
        """
        return 80

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session.

        Returns:
            Shared aiohttp ClientSession instance.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _parse_github_url(self, url: str) -> Optional[tuple[str, str]]:
        """Parse GitHub URL to extract owner and repository name.

        Args:
            url: GitHub repository URL.

        Returns:
            Tuple of (owner, repo) if valid GitHub URL, None otherwise.
        """
        parsed = urlparse(url)

        # Check if it's a GitHub URL
        if parsed.netloc not in ("github.com", "www.github.com"):
            return None

        # Extract path components, removing leading/trailing slashes and .git suffix
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]

        parts = path.split("/")
        if len(parts) != 2:
            return None

        owner, repo = parts
        if not owner or not repo:
            return None

        return (owner, repo)

    async def _fetch_license(
        self, owner: str, repo: str, retry_count: int = 0, max_retries: int = 3
    ) -> Optional[dict]:
        """Fetch license information from GitHub API.

        Args:
            owner: Repository owner.
            repo: Repository name.
            retry_count: Current retry attempt.
            max_retries: Maximum number of retries for rate limiting.

        Returns:
            License data dictionary from GitHub API, or None if fetch failed.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/license"

        headers = {
            "Accept": "application/vnd.github+json",
        }

        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        session = await self._get_session()

        try:
            async with session.get(url, headers=headers) as response:
                # Handle rate limiting
                if response.status == 403:
                    if retry_count >= max_retries:
                        return None

                    # Check for Retry-After header
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        # Exponential backoff: 1s, 2s, 4s
                        wait_time = 2**retry_count

                    await asyncio.sleep(wait_time)
                    return await self._fetch_license(
                        owner, repo, retry_count + 1, max_retries
                    )

                # Handle successful response
                if response.status == 200:
                    return await response.json()

                # Handle other error responses (404, 500, etc.)
                return None

        except Exception:
            # Handle network errors and other exceptions
            return None

    async def resolve(self, spec: PackageSpec) -> Optional[PackageMetadata]:
        """Resolve license metadata from GitHub.

        Note: This resolver requires a repository URL to function. It's designed
        to be used in a waterfall chain after resolvers like PyPIResolver that
        can provide repository URLs. If no repository URL is available in the
        package spec's metadata, this resolver returns None.

        Args:
            spec: Package specification to resolve. The spec must have been
                enriched with repository_url metadata by a previous resolver.

        Returns:
            PackageMetadata with license information from GitHub, or None if
            resolution failed or no repository URL available.
        """
        # For now, return None since we can't get repository URL from spec alone
        # This resolver is meant to enrich existing metadata in a waterfall chain
        return None

    async def enrich(
        self, spec: PackageSpec, metadata: PackageMetadata
    ) -> Optional[PackageMetadata]:
        """Enrich existing metadata with GitHub license information.

        This is the primary method for GitHubResolver, designed to be called
        after another resolver (like PyPI) has provided repository_url.

        Args:
            spec: Package specification being resolved.
            metadata: Existing metadata with repository_url to enrich.

        Returns:
            Enriched PackageMetadata with GitHub license information, or None
            if resolution failed.
        """
        # Need metadata with repository URL
        if not metadata.repository_url:
            return None

        # Parse GitHub URL
        parsed = self._parse_github_url(metadata.repository_url)
        if parsed is None:
            return None

        owner, repo = parsed

        # Fetch license data from GitHub API
        license_data = await self._fetch_license(owner, repo)
        if license_data is None:
            return None

        # Extract license information
        license_info = license_data.get("license", {})
        spdx_id = license_info.get("spdx_id")
        name = license_info.get("name")
        html_url = license_data.get("html_url")

        if not spdx_id or not name or not html_url:
            return None

        # Create LicenseLink with verified file flag
        license_link = LicenseLink(
            spdx_id=spdx_id,
            name=name,
            url=html_url,
            is_verified_file=True,
        )

        # Return new metadata with license information
        return PackageMetadata(
            name=metadata.name,
            version=metadata.version,
            description=metadata.description,
            homepage=metadata.homepage,
            repository_url=metadata.repository_url,
            author=metadata.author,
            licenses=[license_link],
            is_root_project=metadata.is_root_project,
        )

    async def __aenter__(self) -> "GitHubResolver":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
