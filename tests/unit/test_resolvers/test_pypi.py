"""Unit tests for PyPI resolver."""

from typing import Any, AsyncGenerator

import pytest
from aiohttp import ClientError, ClientResponseError
from aioresponses import aioresponses

from license_tracker.models import PackageSpec
from license_tracker.resolvers.pypi import PyPIResolver


@pytest.fixture
async def pypi_resolver() -> AsyncGenerator[PyPIResolver, None]:
    """Return a PyPIResolver instance for testing."""
    resolver = PyPIResolver()
    yield resolver
    await resolver.close()


@pytest.fixture
def pypi_url() -> str:
    """Return the PyPI API URL for testing."""
    return "https://pypi.org/pypi/requests/2.31.0/json"


@pytest.mark.asyncio
async def test_resolve_successful(
    pypi_resolver: PyPIResolver,
    sample_package_spec: PackageSpec,
    sample_pypi_response: dict[str, Any],
    pypi_url: str,
) -> None:
    """Test successful resolution from PyPI API."""
    with aioresponses() as mock:
        mock.get(pypi_url, payload=sample_pypi_response)

        metadata = await pypi_resolver.resolve(sample_package_spec)

        assert metadata is not None
        assert metadata.name == "requests"
        assert metadata.version == "2.31.0"
        assert metadata.description == "Python HTTP for Humans."
        assert metadata.homepage == "https://requests.readthedocs.io"
        assert metadata.repository_url == "https://github.com/psf/requests"
        assert metadata.author == "Kenneth Reitz"
        assert len(metadata.licenses) == 1
        assert metadata.licenses[0].spdx_id == "Apache-2.0"
        assert metadata.licenses[0].name == "Apache 2.0"  # Preserves original PyPI text
        assert metadata.licenses[0].is_verified_file is False
        assert "spdx.org/licenses/Apache-2.0" in metadata.licenses[0].url


@pytest.mark.asyncio
async def test_resolve_with_classifier_fallback(
    pypi_resolver: PyPIResolver,
    sample_package_spec: PackageSpec,
    sample_pypi_response: dict[str, Any],
    pypi_url: str,
) -> None:
    """Test extracting license from classifiers when license field is empty."""
    # Modify response to have empty license field
    modified_response = sample_pypi_response.copy()
    modified_response["info"]["license"] = ""

    with aioresponses() as mock:
        mock.get(pypi_url, payload=modified_response)

        metadata = await pypi_resolver.resolve(sample_package_spec)

        assert metadata is not None
        assert len(metadata.licenses) == 1
        # Should extract from "License :: OSI Approved :: Apache Software License"
        assert metadata.licenses[0].spdx_id == "Apache-2.0"


@pytest.mark.asyncio
async def test_resolve_with_unknown_license(
    pypi_resolver: PyPIResolver,
    sample_package_spec: PackageSpec,
    sample_pypi_response: dict[str, Any],
    pypi_url: str,
) -> None:
    """Test handling of unknown license field."""
    # Modify response to have "UNKNOWN" license
    modified_response = sample_pypi_response.copy()
    modified_response["info"]["license"] = "UNKNOWN"
    modified_response["info"]["classifiers"] = [
        "Programming Language :: Python :: 3",
    ]

    with aioresponses() as mock:
        mock.get(pypi_url, payload=modified_response)

        metadata = await pypi_resolver.resolve(sample_package_spec)

        # Should still return metadata but with empty licenses list
        assert metadata is not None
        assert len(metadata.licenses) == 0


@pytest.mark.asyncio
async def test_resolve_with_missing_license(
    pypi_resolver: PyPIResolver,
    sample_package_spec: PackageSpec,
    sample_pypi_response: dict[str, Any],
    pypi_url: str,
) -> None:
    """Test handling of missing license information."""
    # Modify response to have no license field and no license classifiers
    modified_response = sample_pypi_response.copy()
    modified_response["info"].pop("license", None)
    modified_response["info"]["classifiers"] = [
        "Programming Language :: Python :: 3",
    ]

    with aioresponses() as mock:
        mock.get(pypi_url, payload=modified_response)

        metadata = await pypi_resolver.resolve(sample_package_spec)

        # Should still return metadata but with empty licenses list
        assert metadata is not None
        assert len(metadata.licenses) == 0


@pytest.mark.asyncio
async def test_resolve_extracts_repository_from_project_urls(
    pypi_resolver: PyPIResolver,
    sample_package_spec: PackageSpec,
    pypi_url: str,
) -> None:
    """Test extracting repository URL from project_urls."""
    response = {
        "info": {
            "name": "requests",
            "version": "2.31.0",
            "license": "Apache 2.0",
            "project_urls": {
                "Homepage": "https://example.com",
                "Source": "https://github.com/psf/requests",
                "Repository": "https://github.com/psf/requests",
            },
            "classifiers": [],
        },
    }

    with aioresponses() as mock:
        mock.get(pypi_url, payload=response)

        metadata = await pypi_resolver.resolve(sample_package_spec)

        assert metadata is not None
        assert metadata.repository_url == "https://github.com/psf/requests"


@pytest.mark.asyncio
async def test_resolve_handles_404_error(
    pypi_resolver: PyPIResolver,
    sample_package_spec: PackageSpec,
    pypi_url: str,
) -> None:
    """Test handling of 404 errors from PyPI API."""
    with aioresponses() as mock:
        mock.get(pypi_url, status=404)

        metadata = await pypi_resolver.resolve(sample_package_spec)

        assert metadata is None


@pytest.mark.asyncio
async def test_resolve_handles_network_error(
    pypi_resolver: PyPIResolver,
    sample_package_spec: PackageSpec,
    pypi_url: str,
) -> None:
    """Test handling of network errors."""
    with aioresponses() as mock:
        mock.get(pypi_url, exception=ClientError("Network error"))

        metadata = await pypi_resolver.resolve(sample_package_spec)

        assert metadata is None


@pytest.mark.asyncio
async def test_resolve_handles_server_error(
    pypi_resolver: PyPIResolver,
    sample_package_spec: PackageSpec,
    pypi_url: str,
) -> None:
    """Test handling of 500 server errors."""
    with aioresponses() as mock:
        mock.get(pypi_url, status=500)

        metadata = await pypi_resolver.resolve(sample_package_spec)

        assert metadata is None


@pytest.mark.asyncio
async def test_resolve_handles_malformed_json(
    pypi_resolver: PyPIResolver,
    sample_package_spec: PackageSpec,
    pypi_url: str,
) -> None:
    """Test handling of malformed JSON responses."""
    with aioresponses() as mock:
        # Return invalid JSON
        mock.get(pypi_url, body="not valid json", status=200)

        metadata = await pypi_resolver.resolve(sample_package_spec)

        assert metadata is None


@pytest.mark.asyncio
async def test_resolve_mit_license(
    pypi_resolver: PyPIResolver,
    pypi_url: str,
) -> None:
    """Test normalization of MIT license."""
    spec = PackageSpec(name="requests", version="2.31.0")
    response = {
        "info": {
            "name": "requests",
            "version": "2.31.0",
            "license": "MIT",
            "classifiers": [],
        },
    }

    with aioresponses() as mock:
        mock.get(pypi_url, payload=response)

        metadata = await pypi_resolver.resolve(spec)

        assert metadata is not None
        assert len(metadata.licenses) == 1
        assert metadata.licenses[0].spdx_id == "MIT"
        assert "spdx.org/licenses/MIT" in metadata.licenses[0].url


@pytest.mark.asyncio
async def test_resolve_bsd_license_from_classifier(
    pypi_resolver: PyPIResolver,
    pypi_url: str,
) -> None:
    """Test extracting BSD license from classifier."""
    spec = PackageSpec(name="requests", version="2.31.0")
    response = {
        "info": {
            "name": "requests",
            "version": "2.31.0",
            "license": "",
            "classifiers": [
                "License :: OSI Approved :: BSD License",
            ],
        },
    }

    with aioresponses() as mock:
        mock.get(pypi_url, payload=response)

        metadata = await pypi_resolver.resolve(spec)

        assert metadata is not None
        assert len(metadata.licenses) == 1
        # BSD License can normalize to different variants; we just check it's recognized
        assert "BSD" in metadata.licenses[0].spdx_id or "BSD" in metadata.licenses[0].name


def test_resolver_name() -> None:
    """Test that resolver has correct name."""
    resolver = PyPIResolver()
    assert resolver.name == "PyPI"


def test_resolver_priority() -> None:
    """Test that resolver has correct priority."""
    # PyPI should be high priority (low number)
    resolver = PyPIResolver()
    assert resolver.priority == 10
