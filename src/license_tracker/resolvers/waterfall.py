"""Waterfall resolver orchestrating multiple resolvers in priority order.

This module implements the waterfall resolution strategy, which chains
PyPI, GitHub, and SPDX resolvers to build complete package metadata
with the most accurate license information possible.
"""

import asyncio
import logging
from typing import Optional

from license_tracker.models import PackageMetadata, PackageSpec
from license_tracker.resolvers.base import WaterfallResolverBase
from license_tracker.resolvers.github import GitHubResolver
from license_tracker.resolvers.pypi import PyPIResolver
from license_tracker.resolvers.spdx import SPDXResolver

logger = logging.getLogger(__name__)


class WaterfallResolver(WaterfallResolverBase):
    """Orchestrates multiple resolvers to build complete package metadata.

    Resolution strategy:
    1. PyPI: Fetch base metadata (name, version, description, repository_url, initial license)
    2. GitHub: If repository_url exists, enrich with verified LICENSE file link
    3. SPDX: If no license found, use SPDX as fallback

    The waterfall stops early if a verified license is found, optimizing for
    the best quality license information with minimal API calls.

    Attributes:
        pypi_resolver: Resolver for fetching metadata from PyPI.
        github_resolver: Resolver for fetching verified license from GitHub.
        spdx_resolver: Fallback resolver for generic SPDX license pages.
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        pypi_resolver: Optional[PyPIResolver] = None,
        github_resolver: Optional[GitHubResolver] = None,
        spdx_resolver: Optional[SPDXResolver] = None,
    ) -> None:
        """Initialize WaterfallResolver with optional custom resolvers.

        Args:
            github_token: Optional GitHub personal access token for API authentication.
                If not provided, GitHub API rate limits apply (60 requests/hour).
            pypi_resolver: Optional custom PyPIResolver. If not provided, creates default.
            github_resolver: Optional custom GitHubResolver. If not provided, creates
                one with the provided github_token.
            spdx_resolver: Optional custom SPDXResolver. If not provided, creates default.
        """
        # Create default resolvers if not provided
        self.pypi_resolver = pypi_resolver or PyPIResolver()
        self.github_resolver = github_resolver or GitHubResolver(github_token)
        self.spdx_resolver = spdx_resolver or SPDXResolver()

        # Initialize base class with all resolvers for priority sorting
        super().__init__(
            resolvers=[self.pypi_resolver, self.github_resolver, self.spdx_resolver]
        )

    async def resolve(self, spec: PackageSpec) -> Optional[PackageMetadata]:
        """Resolve package metadata using waterfall strategy.

        Resolution flow:
        1. Call PyPIResolver.resolve() to get base metadata
        2. If metadata has repository_url, call GitHubResolver.enrich()
        3. If no license found, call SPDXResolver.resolve() as fallback
        4. Stop early if verified license is found

        Args:
            spec: Package specification to resolve.

        Returns:
            PackageMetadata with the most complete license information available,
            or None if all resolvers failed.
        """
        logger.debug("Starting waterfall resolution for %s %s", spec.name, spec.version)

        # Step 1: Get base metadata from PyPI
        metadata = await self.pypi_resolver.resolve(spec)
        if metadata is None:
            logger.warning(
                "PyPI resolution failed for %s %s, aborting waterfall",
                spec.name,
                spec.version,
            )
            return None

        logger.debug(
            "PyPI resolved %s %s with %d license(s)",
            spec.name,
            spec.version,
            len(metadata.licenses),
        )

        # Step 2: Try GitHub enrichment if repository URL exists
        # Always attempt enrichment if we have a repository URL, regardless of existing licenses
        enriched_metadata = metadata
        if metadata.repository_url:
            enriched = await self.github_resolver.enrich(spec, metadata)
            if enriched is not None:
                logger.debug(
                    "GitHub enrichment successful for %s %s", spec.name, spec.version
                )
                # Use enriched metadata if GitHub provided verified license
                if enriched.licenses and enriched.licenses[0].is_verified_file:
                    logger.debug(
                        "Using GitHub verified license for %s %s",
                        spec.name,
                        spec.version,
                    )
                    enriched_metadata = enriched
                else:
                    # GitHub enrichment didn't provide verified license
                    logger.debug(
                        "GitHub enrichment did not provide verified license, keeping PyPI data"
                    )
            else:
                logger.debug(
                    "GitHub enrichment failed for %s %s", spec.name, spec.version
                )

        # Step 3: Check if we have license information
        if enriched_metadata.licenses:
            # We have license info (from PyPI or GitHub)
            logger.debug(
                "Returning metadata with %d license(s) for %s %s",
                len(enriched_metadata.licenses),
                spec.name,
                spec.version,
            )
            return enriched_metadata

        # Step 4: No license found, try SPDX fallback
        # Note: Current SPDX resolver implementation requires a SPDX ID,
        # which we don't have at this point. In the future, this could be
        # enhanced to scan package metadata or files for license information.
        logger.debug(
            "No license found for %s %s, SPDX fallback not implemented yet",
            spec.name,
            spec.version,
        )

        # Return the metadata as-is even without licenses
        # This preserves other metadata like description, author, etc.
        return enriched_metadata

    async def resolve_batch(
        self, specs: list[PackageSpec]
    ) -> dict[PackageSpec, Optional[PackageMetadata]]:
        """Resolve multiple packages concurrently using waterfall strategy.

        Uses asyncio.gather to resolve packages in parallel, with exception
        handling to ensure partial failures don't stop the entire batch.

        Args:
            specs: List of package specifications to resolve.

        Returns:
            Dictionary mapping each PackageSpec to its resolved PackageMetadata
            (or None if resolution failed). All specs are guaranteed to have
            an entry in the result dictionary.
        """
        logger.info("Starting batch resolution of %d packages", len(specs))

        # Create resolution tasks for all specs
        tasks = [self.resolve(spec) for spec in specs]

        # Execute all tasks concurrently with exception handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build result dictionary, handling exceptions
        result_dict: dict[PackageSpec, Optional[PackageMetadata]] = {}
        for spec, result in zip(specs, results):
            if isinstance(result, Exception):
                # Log the exception but don't let it stop other resolutions
                logger.error(
                    "Exception resolving %s %s: %s",
                    spec.name,
                    spec.version,
                    result,
                )
                result_dict[spec] = None
            else:
                result_dict[spec] = result

        # Log summary
        successful = sum(1 for metadata in result_dict.values() if metadata is not None)
        logger.info(
            "Batch resolution complete: %d/%d successful", successful, len(specs)
        )

        return result_dict

    async def close(self) -> None:
        """Close any open resources (like HTTP sessions).

        Should be called when done using the resolver, especially if using
        the GitHub resolver which maintains an aiohttp session.
        """
        await self.github_resolver.close()

    async def __aenter__(self) -> "WaterfallResolver":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
