"""Unit tests for PipenvScanner."""

import json
from pathlib import Path

import pytest

from license_tracker.models import PackageSpec
from license_tracker.scanners.pipenv import PipenvScanner


@pytest.fixture
def pipfile_lock_path(tmp_path):
    """Create a temporary Pipfile.lock for testing."""
    pipfile_lock = tmp_path / "Pipfile.lock"
    data = {
        "_meta": {
            "hash": {"sha256": "abc123def456"},
            "pipfile-spec": 6,
            "requires": {"python_version": "3.11"},
            "sources": [
                {
                    "name": "pypi",
                    "url": "https://pypi.org/simple",
                    "verify_ssl": True,
                }
            ],
        },
        "default": {
            "requests": {
                "hashes": [
                    "sha256:58cd2187c01e70e6e26505bca751777aa9f2ee0b7f4300988b709f44e013003f"
                ],
                "index": "pypi",
                "version": "==2.31.0",
            },
            "click": {
                "hashes": [
                    "sha256:ae74fb96c20a0277a1d615f1e4d73c8414f5a98db8b799a7931d1582f3390c28"
                ],
                "index": "pypi",
                "version": "==8.1.7",
            },
        },
        "develop": {
            "pytest": {
                "hashes": [
                    "sha256:0000000000000000000000000000000000000000000000000000000000000000"
                ],
                "index": "pypi",
                "version": "==8.0.0",
            },
        },
    }
    pipfile_lock.write_text(json.dumps(data, indent=4))
    return pipfile_lock


@pytest.fixture
def real_fixture_path():
    """Use the actual test fixture."""
    return Path(__file__).parent.parent.parent / "fixtures" / "Pipfile.lock"


def test_can_handle_pipfile_lock():
    """Test that can_handle returns True for Pipfile.lock files."""
    assert PipenvScanner.can_handle(Path("Pipfile.lock"))
    assert PipenvScanner.can_handle(Path("/some/path/Pipfile.lock"))


def test_can_handle_other_files():
    """Test that can_handle returns False for non-Pipfile.lock files."""
    assert not PipenvScanner.can_handle(Path("requirements.txt"))
    assert not PipenvScanner.can_handle(Path("poetry.lock"))
    assert not PipenvScanner.can_handle(Path("Pipfile"))
    assert not PipenvScanner.can_handle(Path("pipfile.lock"))  # lowercase


def test_source_name():
    """Test that source_name property returns the correct value."""
    scanner = PipenvScanner()
    assert scanner.source_name == "Pipfile.lock"


def test_scan_parses_default_packages(pipfile_lock_path):
    """Test scanning packages from the default section."""
    scanner = PipenvScanner(source_path=pipfile_lock_path)
    packages = scanner.scan()

    # Filter packages from default section
    default_packages = [p for p in packages if p.name in ["requests", "click"]]

    assert len(default_packages) == 2
    assert PackageSpec(name="requests", version="2.31.0", source="Pipfile.lock") in packages
    assert PackageSpec(name="click", version="8.1.7", source="Pipfile.lock") in packages


def test_scan_parses_develop_packages(pipfile_lock_path):
    """Test scanning packages from the develop section."""
    scanner = PipenvScanner(source_path=pipfile_lock_path)
    packages = scanner.scan()

    # Filter packages from develop section
    develop_packages = [p for p in packages if p.name == "pytest"]

    assert len(develop_packages) == 1
    assert PackageSpec(name="pytest", version="8.0.0", source="Pipfile.lock") in packages


def test_scan_strips_version_prefix(pipfile_lock_path):
    """Test that version strings have == prefix stripped."""
    scanner = PipenvScanner(source_path=pipfile_lock_path)
    packages = scanner.scan()

    # All versions should not start with ==
    for package in packages:
        assert not package.version.startswith("==")
        assert package.version[0].isdigit()


def test_scan_combines_default_and_develop(pipfile_lock_path):
    """Test that scan returns packages from both sections."""
    scanner = PipenvScanner(source_path=pipfile_lock_path)
    packages = scanner.scan()

    assert len(packages) == 3  # 2 default + 1 develop
    package_names = {p.name for p in packages}
    assert package_names == {"requests", "click", "pytest"}


def test_scan_sets_source_field(pipfile_lock_path):
    """Test that all packages have source set to Pipfile.lock."""
    scanner = PipenvScanner(source_path=pipfile_lock_path)
    packages = scanner.scan()

    for package in packages:
        assert package.source == "Pipfile.lock"


def test_scan_missing_file():
    """Test that scan raises FileNotFoundError for missing files."""
    scanner = PipenvScanner(source_path=Path("/nonexistent/Pipfile.lock"))

    with pytest.raises(FileNotFoundError):
        scanner.scan()


def test_scan_invalid_json(tmp_path):
    """Test that scan raises ValueError for invalid JSON."""
    invalid_file = tmp_path / "Pipfile.lock"
    invalid_file.write_text("not valid json {")

    scanner = PipenvScanner(source_path=invalid_file)

    with pytest.raises(ValueError, match="Invalid JSON"):
        scanner.scan()


def test_scan_missing_sections(tmp_path):
    """Test that scan handles Pipfile.lock with missing default/develop sections."""
    pipfile_lock = tmp_path / "Pipfile.lock"
    data = {
        "_meta": {
            "hash": {"sha256": "abc123"},
            "pipfile-spec": 6,
        }
        # No default or develop sections
    }
    pipfile_lock.write_text(json.dumps(data))

    scanner = PipenvScanner(source_path=pipfile_lock)
    packages = scanner.scan()

    assert packages == []


def test_scan_empty_sections(tmp_path):
    """Test that scan handles empty default/develop sections."""
    pipfile_lock = tmp_path / "Pipfile.lock"
    data = {
        "_meta": {"hash": {"sha256": "abc123"}},
        "default": {},
        "develop": {},
    }
    pipfile_lock.write_text(json.dumps(data))

    scanner = PipenvScanner(source_path=pipfile_lock)
    packages = scanner.scan()

    assert packages == []


def test_scan_only_default_section(tmp_path):
    """Test scanning when only default section exists."""
    pipfile_lock = tmp_path / "Pipfile.lock"
    data = {
        "_meta": {"hash": {"sha256": "abc123"}},
        "default": {
            "requests": {
                "version": "==2.31.0",
            }
        },
    }
    pipfile_lock.write_text(json.dumps(data))

    scanner = PipenvScanner(source_path=pipfile_lock)
    packages = scanner.scan()

    assert len(packages) == 1
    assert packages[0].name == "requests"
    assert packages[0].version == "2.31.0"


def test_scan_with_real_fixture(real_fixture_path):
    """Test scanning with the real test fixture."""
    scanner = PipenvScanner(source_path=real_fixture_path)
    packages = scanner.scan()

    assert len(packages) == 5  # 3 default + 2 develop from fixture
    package_names = {p.name for p in packages}
    assert "requests" in package_names
    assert "click" in package_names
    assert "certifi" in package_names
    assert "pytest" in package_names
    assert "ruff" in package_names


def test_scan_without_source_path():
    """Test that scan raises ValueError when no source_path is provided."""
    scanner = PipenvScanner()

    with pytest.raises(ValueError, match="source_path must be provided"):
        scanner.scan()


def test_scan_package_ordering(pipfile_lock_path):
    """Test that packages maintain consistent ordering."""
    scanner = PipenvScanner(source_path=pipfile_lock_path)
    packages1 = scanner.scan()
    packages2 = scanner.scan()

    # Should return same packages in same order
    assert packages1 == packages2
