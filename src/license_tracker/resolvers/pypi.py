"""PyPI resolver for fetching license metadata from the PyPI JSON API.

This resolver fetches package metadata from the PyPI JSON API and extracts
license information from the package metadata, falling back to classifiers
when necessary.
"""

import logging
from functools import lru_cache
from typing import Optional

import aiohttp
from license_expression import get_spdx_licensing

from license_tracker.models import LicenseLink, PackageMetadata, PackageSpec
from license_tracker.resolvers.base import BaseResolver

logger = logging.getLogger(__name__)

# Initialize SPDX licensing library for normalization
SPDX = get_spdx_licensing()

# Common license aliases and variations map
LICENSE_MAP = {
    "Apache 2.0": "Apache-2.0",
    "Apache License 2.0": "Apache-2.0",
    "Apache Software License": "Apache-2.0",
    "Apache License, Version 2.0": "Apache-2.0",
    "MIT License": "MIT",
    "BSD License": "BSD-3-Clause",
    "BSD 3-Clause License": "BSD-3-Clause",
    "BSD 2-Clause License": "BSD-2-Clause",
    "GNU General Public License v3": "GPL-3.0",
    "GNU General Public License v3 (GPLv3)": "GPL-3.0",
    "GNU General Public License v2": "GPL-2.0",
    "GNU Lesser General Public License v3": "LGPL-3.0",
    "Mozilla Public License 2.0": "MPL-2.0",
    "ISC License": "ISC",
    "Python Software Foundation License": "PSF-2.0",
}

# Common SPDX IDs for case-insensitive matching
COMMON_SPDX = [
    "MIT", "Apache-2.0", "GPL-3.0", "GPL-2.0", "LGPL-3.0",
    "BSD-3-Clause", "BSD-2-Clause", "ISC", "MPL-2.0", "PSF-2.0",
]


@lru_cache(maxsize=1024)
def _normalize_license_text(license_text: str) -> Optional[LicenseLink]:
    """Normalize a license string to SPDX identifier (cached helper).

    Uses the license-expression library to parse and normalize
    license strings to SPDX identifiers.

    Args:
        license_text: Raw license string from PyPI.

    Returns:
        LicenseLink with SPDX identifier and URL, or None if not recognized.
    """
    if not license_text or license_text.upper() == "UNKNOWN":
        return None

    try:
        # Clean up the license text
        license_text = license_text.strip()

        # Check if we have a direct mapping
        # Optimized: using module-level constant LICENSE_MAP
        if license_text in LICENSE_MAP:
            spdx_id = LICENSE_MAP[license_text]
            return LicenseLink(
                spdx_id=spdx_id,
                name=license_text,
                url=f"https://spdx.org/licenses/{spdx_id}.html",
                is_verified_file=False,
            )

        # Try to parse with license-expression library
        try:
            parsed = SPDX.parse(license_text, validate=True)
            if parsed:
                # Get the first license from the expression
                # For simple cases this will be the license itself
                spdx_id = str(parsed).strip()
                return LicenseLink(
                    spdx_id=spdx_id,
                    name=license_text,
                    url=f"https://spdx.org/licenses/{spdx_id}.html",
                    is_verified_file=False,
                )
        except Exception:
            # If parsing fails, try simple text matching
            pass

        # Try case-insensitive matching of common SPDX IDs
        # Optimized: using module-level constant COMMON_SPDX
        license_upper = license_text.upper()
        for spdx_id in COMMON_SPDX:
            if spdx_id.upper() in license_upper or spdx_id.upper().replace("-", "") in license_upper.replace("-", "").replace(" ", ""):
                return LicenseLink(
                    spdx_id=spdx_id,
                    name=license_text,
                    url=f"https://spdx.org/licenses/{spdx_id}.html",
                    is_verified_file=False,
                )

        logger.debug("Could not normalize license: %s", license_text)
        return None

    except Exception as e:
        logger.debug("Error normalizing license '%s': %s", license_text, e)
        return None


class PyPIResolver(BaseResolver):
    """Resolver for fetching license metadata from PyPI.

    Fetches package information from the PyPI JSON API and extracts
    license information from the package metadata. Falls back to
    extracting licenses from classifiers if the license field is
    empty or contains "UNKNOWN".

    The resolver returns LicenseLink objects with SPDX-normalized
    identifiers and URLs pointing to the SPDX license pages
    (is_verified_file=False).

    This resolver manages an aiohttp session for efficient connection
    reuse across multiple resolve calls. Use as an async context manager
    or call close() when done.
    """

    def __init__(self) -> None:
        """Initialize the PyPI resolver."""
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session.

        Returns:
            The shared aiohttp ClientSession.
        """
        if self._session is None or self._session.closed:
            # Optimized: Enable DNS cache to reduce latency for repeated host lookups
            connector = aiohttp.TCPConnector(ttl_dns_cache=300)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session.

        Should be called when done using the resolver to release resources.
        """
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "PyPIResolver":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    @property
    def name(self) -> str:
        """Return the resolver name.

        Returns:
            The string "PyPI".
        """
        return "PyPI"

    @property
    def priority(self) -> int:
        """Return the resolver priority.

        PyPI is a high-priority source (priority 10) as it's the
        authoritative source for Python packages.

        Returns:
            Priority value of 10.
        """
        return 10

    async def resolve(self, spec: PackageSpec) -> Optional[PackageMetadata]:
        """Resolve license metadata from PyPI.

        Fetches package information from PyPI's JSON API and extracts
        license information, homepage, repository URL, and other metadata.

        Args:
            spec: Package specification to resolve.

        Returns:
            PackageMetadata with license information, or None if resolution failed.
        """
        url = f"https://pypi.org/pypi/{spec.name}/{spec.version}/json"
        logger.debug("Fetching PyPI metadata from %s", url)

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 404:
                    logger.warning(
                        "Package %s %s not found on PyPI", spec.name, spec.version
                    )
                    return None

                if response.status != 200:
                    logger.error(
                        "PyPI API returned status %d for %s %s",
                        response.status,
                        spec.name,
                        spec.version,
                    )
                    return None

                try:
                    data = await response.json()
                except Exception as e:
                    logger.error(
                        "Failed to parse JSON response for %s %s: %s",
                        spec.name,
                        spec.version,
                        e,
                    )
                    return None

        except aiohttp.ClientError as e:
            logger.error(
                "Network error fetching PyPI metadata for %s %s: %s",
                spec.name,
                spec.version,
                e,
            )
            return None
        except Exception as e:
            logger.error(
                "Unexpected error fetching PyPI metadata for %s %s: %s",
                spec.name,
                spec.version,
                e,
            )
            return None

        return self._parse_pypi_response(data, spec)

    def _parse_pypi_response(
        self, data: dict, spec: PackageSpec
    ) -> Optional[PackageMetadata]:
        """Parse PyPI JSON response into PackageMetadata.

        Args:
            data: PyPI JSON API response.
            spec: Original package specification.

        Returns:
            Parsed PackageMetadata or None if parsing failed.
        """
        try:
            info = data.get("info", {})

            # Extract basic metadata
            name = info.get("name", spec.name)
            version = info.get("version", spec.version)
            description = info.get("summary")
            author = info.get("author")
            homepage = info.get("home_page")

            # Extract repository URL from project_urls
            repository_url = self._extract_repository_url(info.get("project_urls", {}))

            # Extract licenses
            licenses = self._extract_licenses(info)

            return PackageMetadata(
                name=name,
                version=version,
                description=description,
                homepage=homepage,
                repository_url=repository_url,
                author=author,
                licenses=licenses,
                is_root_project=False,
            )

        except Exception as e:
            logger.error(
                "Failed to parse PyPI response for %s %s: %s",
                spec.name,
                spec.version,
                e,
            )
            return None

    def _extract_repository_url(self, project_urls: dict) -> Optional[str]:
        """Extract repository URL from project_urls.

        Tries common keys like "Source", "Repository", "Source Code", etc.

        Args:
            project_urls: Dictionary of project URLs from PyPI metadata.

        Returns:
            Repository URL if found, None otherwise.
        """
        if not project_urls:
            return None

        # Try common repository URL keys in order of preference
        repo_keys = [
            "Source",
            "Repository",
            "Source Code",
            "source",
            "repository",
            "Code",
            "GitHub",
            "GitLab",
        ]

        for key in repo_keys:
            if key in project_urls:
                url = project_urls[key]
                # Basic validation that it's a Git hosting URL
                if any(
                    host in url.lower()
                    for host in ["github.com", "gitlab.com", "bitbucket.org"]
                ):
                    return url

        return None

    def _extract_licenses(self, info: dict) -> list[LicenseLink]:
        """Extract and normalize licenses from PyPI metadata.

        First tries the license field, then falls back to classifiers.
        Normalizes license names to SPDX identifiers.

        Args:
            info: The "info" section from PyPI JSON API response.

        Returns:
            List of LicenseLink objects (may be empty).
        """
        licenses = []

        # Try the license field first
        license_field = info.get("license", "").strip()
        if license_field and license_field.upper() != "UNKNOWN":
            license_link = self._normalize_license(license_field)
            if license_link:
                licenses.append(license_link)
                return licenses

        # Fall back to extracting from classifiers
        classifiers = info.get("classifiers", [])
        for classifier in classifiers:
            if classifier.startswith("License :: "):
                license_link = self._extract_license_from_classifier(classifier)
                if license_link:
                    licenses.append(license_link)
                    break  # Use the first license classifier found

        return licenses

    def _extract_license_from_classifier(
        self, classifier: str
    ) -> Optional[LicenseLink]:
        """Extract license from a PyPI classifier string.

        Args:
            classifier: License classifier like "License :: OSI Approved :: MIT License".

        Returns:
            LicenseLink if extraction successful, None otherwise.
        """
        # Extract the last part of the classifier which is typically the license name
        # Example: "License :: OSI Approved :: MIT License" -> "MIT License"
        parts = classifier.split(" :: ")
        if len(parts) < 2:
            return None

        license_name = parts[-1].strip()

        # Try to normalize it
        return self._normalize_license(license_name)

    def _normalize_license(self, license_text: str) -> Optional[LicenseLink]:
        """Normalize a license string to SPDX identifier.

        Delegates to cached helper _normalize_license_text.

        Args:
            license_text: Raw license string from PyPI.

        Returns:
            LicenseLink with SPDX identifier and URL, or None if not recognized.
        """
        return _normalize_license_text(license_text)
