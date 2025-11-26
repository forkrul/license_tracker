"""Tests for the RequirementsScanner."""

import logging
from pathlib import Path

import pytest

from license_tracker.models import PackageSpec
from license_tracker.scanners.requirements import RequirementsScanner


class TestRequirementsScanner:
    """Test suite for RequirementsScanner."""

    @pytest.fixture
    def fixture_path(self) -> Path:
        """Return path to the requirements.txt fixture."""
        return Path(__file__).parent.parent.parent / "fixtures" / "requirements.txt"

    @pytest.fixture
    def scanner(self, fixture_path: Path) -> RequirementsScanner:
        """Create a RequirementsScanner instance."""
        return RequirementsScanner(source_path=fixture_path)

    def test_can_handle_requirements_txt(self, fixture_path: Path):
        """Test that can_handle returns True for requirements.txt files."""
        assert RequirementsScanner.can_handle(fixture_path)

    def test_can_handle_other_names(self):
        """Test that can_handle returns True for various requirements file names."""
        assert RequirementsScanner.can_handle(Path("requirements.txt"))
        assert RequirementsScanner.can_handle(Path("requirements-dev.txt"))
        assert RequirementsScanner.can_handle(Path("requirements_test.txt"))
        assert RequirementsScanner.can_handle(Path("test-requirements.txt"))
        assert RequirementsScanner.can_handle(Path("dev-requirements.txt"))

    def test_can_handle_rejects_other_files(self):
        """Test that can_handle returns False for non-requirements files."""
        assert not RequirementsScanner.can_handle(Path("poetry.lock"))
        assert not RequirementsScanner.can_handle(Path("Pipfile.lock"))
        assert not RequirementsScanner.can_handle(Path("setup.py"))

    def test_source_name(self, scanner: RequirementsScanner):
        """Test that source_name returns the correct value."""
        assert scanner.source_name == "requirements.txt"

    def test_scan_exact_versions(self, scanner: RequirementsScanner):
        """Test parsing packages with exact version specifiers (==)."""
        packages = scanner.scan()

        # Find specific packages with exact versions
        requests_pkg = next((p for p in packages if p.name == "requests"), None)
        assert requests_pkg is not None
        assert requests_pkg.version == "2.31.0"
        assert requests_pkg.source == "requirements.txt"

        click_pkg = next((p for p in packages if p.name == "click"), None)
        assert click_pkg is not None
        assert click_pkg.version == "8.1.7"
        assert click_pkg.source == "requirements.txt"

    def test_scan_range_specifiers(self, scanner: RequirementsScanner):
        """Test parsing packages with range version specifiers (>=, ~=, etc.)."""
        packages = scanner.scan()

        # Test >= specifier
        aiohttp_pkg = next((p for p in packages if p.name == "aiohttp"), None)
        assert aiohttp_pkg is not None
        assert aiohttp_pkg.version == "3.9.0"

        # Test ~= specifier
        jinja2_pkg = next((p for p in packages if p.name == "jinja2"), None)
        assert jinja2_pkg is not None
        assert jinja2_pkg.version == "3.1.0"

        # Test >= with inline comment
        certifi_pkg = next((p for p in packages if p.name == "certifi"), None)
        assert certifi_pkg is not None
        assert certifi_pkg.version == "2024.0.0"

    def test_scan_multiple_specifiers(self, scanner: RequirementsScanner):
        """Test parsing packages with multiple version specifiers."""
        packages = scanner.scan()

        # Test >=1.21.1,<3 format - should extract first version
        urllib3_pkg = next((p for p in packages if p.name == "urllib3"), None)
        assert urllib3_pkg is not None
        assert urllib3_pkg.version == "1.21.1"

        # Test >=2.5,<4 format
        idna_pkg = next((p for p in packages if p.name == "idna"), None)
        assert idna_pkg is not None
        assert idna_pkg.version == "2.5"

        # Test >=2,<4 format (single digit)
        charset_pkg = next((p for p in packages if p.name == "charset-normalizer"), None)
        assert charset_pkg is not None
        assert charset_pkg.version == "2"

    def test_scan_ignores_comments(self, scanner: RequirementsScanner):
        """Test that comment lines are ignored."""
        packages = scanner.scan()

        # None of the packages should have names starting with '#'
        comment_packages = [p for p in packages if p.name.startswith("#")]
        assert len(comment_packages) == 0

    def test_scan_ignores_blank_lines(self, fixture_path: Path):
        """Test that blank lines are ignored."""
        # Create a temporary file with blank lines
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("requests==2.31.0\n")
            f.write("\n")
            f.write("\n")
            f.write("click==8.1.7\n")
            temp_path = Path(f.name)

        try:
            scanner = RequirementsScanner(source_path=temp_path)
            packages = scanner.scan()

            # Should only have 2 packages
            assert len(packages) == 2
            assert packages[0].name == "requests"
            assert packages[1].name == "click"
        finally:
            temp_path.unlink()

    def test_scan_strips_inline_comments(self, scanner: RequirementsScanner):
        """Test that inline comments are stripped."""
        packages = scanner.scan()

        # certifi has an inline comment in the fixture
        certifi_pkg = next((p for p in packages if p.name == "certifi"), None)
        assert certifi_pkg is not None
        # Version should not include the comment
        assert "#" not in certifi_pkg.version
        assert "inline" not in certifi_pkg.version.lower()

    def test_scan_skips_git_urls(self, caplog):
        """Test that git URLs are skipped with a warning."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("requests==2.31.0\n")
            f.write("git+https://github.com/psf/requests.git@main\n")
            f.write("-e git+https://github.com/user/repo.git#egg=package\n")
            f.write("click==8.1.7\n")
            temp_path = Path(f.name)

        try:
            scanner = RequirementsScanner(source_path=temp_path)

            with caplog.at_level(logging.WARNING):
                packages = scanner.scan()

            # Should only have 2 packages (git URLs skipped)
            assert len(packages) == 2
            assert packages[0].name == "requests"
            assert packages[1].name == "click"

            # Should have warning logs for git URLs
            warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
            assert len(warning_messages) >= 2
            assert any("git" in msg.lower() for msg in warning_messages)
        finally:
            temp_path.unlink()

    def test_scan_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        scanner = RequirementsScanner(source_path=Path("/nonexistent/requirements.txt"))

        with pytest.raises(FileNotFoundError):
            scanner.scan()

    def test_scan_total_package_count(self, scanner: RequirementsScanner):
        """Test that the correct total number of packages are extracted."""
        packages = scanner.scan()

        # Based on the fixture, we should have 8 packages:
        # requests, click, aiohttp, jinja2, certifi, urllib3, idna, charset-normalizer
        assert len(packages) == 8

    def test_scan_all_have_source(self, scanner: RequirementsScanner):
        """Test that all scanned packages have the correct source."""
        packages = scanner.scan()

        for package in packages:
            assert package.source == "requirements.txt"

    def test_scan_no_duplicates(self, scanner: RequirementsScanner):
        """Test that no duplicate packages are returned."""
        packages = scanner.scan()

        package_names = [p.name for p in packages]
        assert len(package_names) == len(set(package_names))
