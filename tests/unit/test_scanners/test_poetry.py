"""Tests for Poetry lock file scanner."""

from pathlib import Path

import pytest

from license_tracker.models import PackageSpec
from license_tracker.scanners.poetry import PoetryScanner


class TestPoetryScanner:
    """Test suite for PoetryScanner."""

    @pytest.fixture
    def poetry_lock_path(self) -> Path:
        """Return path to test poetry.lock fixture."""
        return Path(__file__).parent.parent.parent / "fixtures" / "poetry.lock"

    @pytest.fixture
    def scanner(self, poetry_lock_path: Path) -> PoetryScanner:
        """Create a PoetryScanner instance for testing."""
        return PoetryScanner(source_path=poetry_lock_path)

    def test_can_handle_poetry_lock(self, poetry_lock_path: Path) -> None:
        """Test that can_handle returns True for poetry.lock files."""
        assert PoetryScanner.can_handle(poetry_lock_path)

    def test_can_handle_poetry_lock_name_only(self, tmp_path: Path) -> None:
        """Test that can_handle works with filename alone."""
        poetry_file = tmp_path / "poetry.lock"
        poetry_file.write_text("")
        assert PoetryScanner.can_handle(poetry_file)

    def test_can_handle_other_files(self, tmp_path: Path) -> None:
        """Test that can_handle returns False for non-poetry.lock files."""
        other_file = tmp_path / "requirements.txt"
        other_file.write_text("")
        assert not PoetryScanner.can_handle(other_file)

    def test_can_handle_case_sensitive(self, tmp_path: Path) -> None:
        """Test that can_handle is case-sensitive."""
        wrong_case = tmp_path / "Poetry.lock"
        wrong_case.write_text("")
        assert not PoetryScanner.can_handle(wrong_case)

    def test_source_name(self, scanner: PoetryScanner) -> None:
        """Test that source_name returns correct value."""
        assert scanner.source_name == "poetry.lock"

    def test_scan_extracts_packages(self, scanner: PoetryScanner) -> None:
        """Test that scan extracts all packages from poetry.lock."""
        packages = scanner.scan()

        # Verify we got the expected packages
        assert len(packages) == 7

        # Check that all packages are PackageSpec instances
        assert all(isinstance(pkg, PackageSpec) for pkg in packages)

        # Verify source is set correctly
        assert all(pkg.source == "poetry.lock" for pkg in packages)

    def test_scan_package_names(self, scanner: PoetryScanner) -> None:
        """Test that scan extracts correct package names."""
        packages = scanner.scan()
        package_names = {pkg.name for pkg in packages}

        expected_names = {
            "requests",
            "click",
            "aiohttp",
            "certifi",
            "charset-normalizer",
            "idna",
            "urllib3",
        }

        assert package_names == expected_names

    def test_scan_package_versions(self, scanner: PoetryScanner) -> None:
        """Test that scan extracts correct versions."""
        packages = scanner.scan()
        package_dict = {pkg.name: pkg.version for pkg in packages}

        assert package_dict["requests"] == "2.31.0"
        assert package_dict["click"] == "8.1.7"
        assert package_dict["aiohttp"] == "3.9.0"
        assert package_dict["certifi"] == "2024.2.2"
        assert package_dict["charset-normalizer"] == "3.3.2"
        assert package_dict["idna"] == "3.6"
        assert package_dict["urllib3"] == "2.1.0"

    def test_scan_missing_file(self, tmp_path: Path) -> None:
        """Test that scan raises FileNotFoundError for missing file."""
        missing_file = tmp_path / "nonexistent.lock"
        scanner = PoetryScanner(source_path=missing_file)

        with pytest.raises(FileNotFoundError):
            scanner.scan()

    def test_scan_invalid_toml(self, tmp_path: Path) -> None:
        """Test that scan raises ValueError for invalid TOML."""
        invalid_file = tmp_path / "poetry.lock"
        invalid_file.write_text("this is not valid toml [[")
        scanner = PoetryScanner(source_path=invalid_file)

        with pytest.raises(ValueError, match="Invalid TOML"):
            scanner.scan()

    def test_scan_empty_file(self, tmp_path: Path) -> None:
        """Test that scan handles empty poetry.lock gracefully."""
        empty_file = tmp_path / "poetry.lock"
        empty_file.write_text("")
        scanner = PoetryScanner(source_path=empty_file)

        packages = scanner.scan()
        assert packages == []

    def test_scan_no_packages(self, tmp_path: Path) -> None:
        """Test that scan handles poetry.lock with no packages."""
        no_packages = tmp_path / "poetry.lock"
        no_packages.write_text("""
[metadata]
lock-version = "2.0"
python-versions = ">=3.11"
""")
        scanner = PoetryScanner(source_path=no_packages)

        packages = scanner.scan()
        assert packages == []

    def test_scan_package_missing_name(self, tmp_path: Path) -> None:
        """Test that scan raises ValueError for package missing name."""
        invalid_file = tmp_path / "poetry.lock"
        invalid_file.write_text("""
[[package]]
version = "1.0.0"
""")
        scanner = PoetryScanner(source_path=invalid_file)

        with pytest.raises(ValueError, match="Package missing required field"):
            scanner.scan()

    def test_scan_package_missing_version(self, tmp_path: Path) -> None:
        """Test that scan raises ValueError for package missing version."""
        invalid_file = tmp_path / "poetry.lock"
        invalid_file.write_text("""
[[package]]
name = "test-package"
""")
        scanner = PoetryScanner(source_path=invalid_file)

        with pytest.raises(ValueError, match="Package missing required field"):
            scanner.scan()

    def test_scan_no_source_path(self) -> None:
        """Test that scan raises ValueError when source_path is None."""
        scanner = PoetryScanner()

        with pytest.raises(ValueError, match="source_path must be set"):
            scanner.scan()

    def test_package_spec_immutability(self, scanner: PoetryScanner) -> None:
        """Test that returned PackageSpec objects are immutable."""
        packages = scanner.scan()

        # PackageSpec is frozen, so this should raise an error
        with pytest.raises(AttributeError):
            packages[0].name = "modified"  # type: ignore
