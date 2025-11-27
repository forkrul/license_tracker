from license_tracker.models import LicenseLink, PackageMetadata


def test_package_metadata_primary_license_with_licenses():
    """Test that primary_license returns the first license."""
    license_link = LicenseLink(spdx_id="MIT", name="MIT License", url="")
    metadata = PackageMetadata(name="test", version="1.0", licenses=[license_link])
    assert metadata.primary_license == license_link


def test_package_metadata_primary_license_with_no_licenses():
    """Test that primary_license returns None when no licenses exist."""
    metadata = PackageMetadata(name="test", version="1.0")
    assert metadata.primary_license is None
