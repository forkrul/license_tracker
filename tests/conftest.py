"""Pytest configuration and shared fixtures for license_tracker tests."""

from pathlib import Path
from typing import Any

import pytest

from license_tracker.models import LicenseLink, PackageMetadata, PackageSpec

# Path to test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to the fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def sample_poetry_lock(fixtures_dir: Path) -> Path:
    """Return path to sample poetry.lock fixture."""
    return fixtures_dir / "poetry.lock"


@pytest.fixture
def sample_pipfile_lock(fixtures_dir: Path) -> Path:
    """Return path to sample Pipfile.lock fixture."""
    return fixtures_dir / "Pipfile.lock"


@pytest.fixture
def sample_requirements_txt(fixtures_dir: Path) -> Path:
    """Return path to sample requirements.txt fixture."""
    return fixtures_dir / "requirements.txt"


@pytest.fixture
def sample_package_spec() -> PackageSpec:
    """Return a sample PackageSpec for testing."""
    return PackageSpec(
        name="requests",
        version="2.31.0",
        source="poetry.lock",
    )


@pytest.fixture
def sample_license_link() -> LicenseLink:
    """Return a sample LicenseLink for testing."""
    return LicenseLink(
        spdx_id="Apache-2.0",
        name="Apache License 2.0",
        url="https://github.com/psf/requests/blob/main/LICENSE",
        is_verified_file=True,
    )


@pytest.fixture
def sample_package_metadata(sample_license_link: LicenseLink) -> PackageMetadata:
    """Return a sample PackageMetadata for testing."""
    return PackageMetadata(
        name="requests",
        version="2.31.0",
        description="Python HTTP for Humans.",
        homepage="https://requests.readthedocs.io",
        repository_url="https://github.com/psf/requests",
        author="Kenneth Reitz",
        licenses=[sample_license_link],
        is_root_project=False,
    )


@pytest.fixture
def sample_pypi_response() -> dict[str, Any]:
    """Return a sample PyPI JSON API response."""
    return {
        "info": {
            "name": "requests",
            "version": "2.31.0",
            "summary": "Python HTTP for Humans.",
            "author": "Kenneth Reitz",
            "author_email": "me@kennethreitz.org",
            "license": "Apache 2.0",
            "home_page": "https://requests.readthedocs.io",
            "project_urls": {
                "Homepage": "https://requests.readthedocs.io",
                "Source": "https://github.com/psf/requests",
            },
            "classifiers": [
                "License :: OSI Approved :: Apache Software License",
                "Programming Language :: Python :: 3",
            ],
        },
        "urls": [],
    }


@pytest.fixture
def sample_github_license_response() -> dict[str, Any]:
    """Return a sample GitHub license API response."""
    return {
        "name": "LICENSE",
        "path": "LICENSE",
        "sha": "abc123",
        "size": 10173,
        "url": "https://api.github.com/repos/psf/requests/contents/LICENSE",
        "html_url": "https://github.com/psf/requests/blob/main/LICENSE",
        "git_url": "https://api.github.com/repos/psf/requests/git/blobs/abc123",
        "download_url": "https://raw.githubusercontent.com/psf/requests/main/LICENSE",
        "type": "file",
        "license": {
            "key": "apache-2.0",
            "name": "Apache License 2.0",
            "spdx_id": "Apache-2.0",
            "url": "https://api.github.com/licenses/apache-2.0",
        },
    }


@pytest.fixture
def multiple_package_specs() -> list[PackageSpec]:
    """Return a list of sample PackageSpecs for batch testing."""
    return [
        PackageSpec(name="requests", version="2.31.0", source="poetry.lock"),
        PackageSpec(name="click", version="8.1.7", source="poetry.lock"),
        PackageSpec(name="aiohttp", version="3.9.0", source="poetry.lock"),
        PackageSpec(name="jinja2", version="3.1.2", source="poetry.lock"),
        PackageSpec(name="rich", version="13.7.0", source="poetry.lock"),
    ]
