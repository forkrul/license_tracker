import pytest
from typer.testing import CliRunner

from license_tracker.cli import app
from license_tracker.models import LicenseLink, PackageMetadata, PackageSpec

runner = CliRunner()


@pytest.fixture
def mock_scan_and_resolve(mocker):
    """Mock the _scan_and_resolve function."""
    mock_data = (
        [
            PackageSpec(name="test-package", version="1.0.0"),
        ],
        {
            PackageSpec(
                name="test-package", version="1.0.0"
            ): PackageMetadata(
                name="test-package",
                version="1.0.0",
                licenses=[
                    LicenseLink(
                        spdx_id="MIT", name="MIT License", url="https://mit.edu"
                    )
                ],
            )
        },
    )
    return mocker.patch(
        "license_tracker.cli._scan_and_resolve", return_value=mock_data
    )


def test_gen_command(tmp_path, mock_scan_and_resolve):
    """Test the gen command with mocked data."""
    output_file = tmp_path / "licenses.md"
    lock_file = tmp_path / "poetry.lock"
    lock_file.touch()

    result = runner.invoke(
        app, ["gen", "--scan", str(lock_file), "--output", str(output_file)]
    )

    assert result.exit_code == 0
    assert "Generated:" in result.stdout
    assert output_file.exists()

    content = output_file.read_text()
    assert "test-package" in content
    assert "MIT" in content


def test_check_command_with_forbidden_license(tmp_path, mock_scan_and_resolve):
    """Test the check command with a forbidden license."""
    lock_file = tmp_path / "poetry.lock"
    lock_file.touch()

    result = runner.invoke(
        app, ["check", "--scan", str(lock_file), "--forbidden", "MIT"]
    )

    assert result.exit_code == 1
    assert "Violations" in result.stdout
    assert "test-package==1.0.0: MIT" in result.stdout


def test_check_command_with_allowed_license(tmp_path, mock_scan_and_resolve):
    """Test the check command with an allowed license."""
    lock_file = tmp_path / "poetry.lock"
    lock_file.touch()

    result = runner.invoke(
        app, ["check", "--scan", str(lock_file), "--allowed", "MIT"]
    )

    assert result.exit_code == 0
    assert "All" in result.stdout
    assert "packages are compliant" in result.stdout


@pytest.fixture
def mock_license_cache(mocker):
    """Mock the LicenseCache class."""
    mock_cache_instance = mocker.MagicMock()
    # Ensure the context manager returns the mock instance itself
    mock_cache_instance.__enter__.return_value = mock_cache_instance
    mock_cache_instance.info.return_value = {
        "path": "/fake/path",
        "count": 10,
        "size_bytes": 1024,
    }
    mocker.patch("license_tracker.cli.LicenseCache", return_value=mock_cache_instance)
    return mock_cache_instance


def test_cache_command_show(mock_license_cache):
    """Test the cache show command."""
    result = runner.invoke(app, ["cache", "show"])

    assert result.exit_code == 0
    assert "Cache Location:" in result.stdout
    mock_license_cache.info.assert_called_once()


def test_cache_command_clear(mock_license_cache):
    """Test the cache clear command."""
    result = runner.invoke(app, ["cache", "clear"])

    assert result.exit_code == 0
    assert "Cache cleared" in result.stdout
    mock_license_cache.clear.assert_called_once_with()
