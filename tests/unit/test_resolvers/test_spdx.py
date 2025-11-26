"""Tests for the SPDX resolver.

Tests the fallback SPDX resolver that generates license page URLs
from SPDX identifiers when no direct license file is available.
"""

import pytest

from license_tracker.models import LicenseLink, PackageMetadata, PackageSpec
from license_tracker.resolvers.spdx import SPDXResolver


class TestSPDXResolver:
    """Test suite for SPDXResolver."""

    @pytest.fixture
    def resolver(self):
        """Create a SPDXResolver instance."""
        return SPDXResolver()

    def test_resolver_name(self, resolver):
        """Test that resolver returns correct name."""
        assert resolver.name == "SPDX"

    def test_resolver_priority(self, resolver):
        """Test that resolver has lowest priority (highest number)."""
        assert resolver.priority == 1000

    @pytest.mark.asyncio
    async def test_resolve_mit_license(self, resolver):
        """Test resolving MIT license to SPDX URL."""
        spec = PackageSpec(name="test-package", version="1.0.0")

        result = await resolver.resolve(spec, spdx_id="MIT")

        assert result is not None
        assert isinstance(result, PackageMetadata)
        assert result.name == "test-package"
        assert result.version == "1.0.0"
        assert len(result.licenses) == 1

        license_link = result.licenses[0]
        assert license_link.spdx_id == "MIT"
        assert license_link.name == "MIT License"
        assert license_link.url == "https://spdx.org/licenses/MIT.html"
        assert license_link.is_verified_file is False

    @pytest.mark.asyncio
    async def test_resolve_apache_license(self, resolver):
        """Test resolving Apache-2.0 license to SPDX URL."""
        spec = PackageSpec(name="apache-lib", version="2.0.0")

        result = await resolver.resolve(spec, spdx_id="Apache-2.0")

        assert result is not None
        assert len(result.licenses) == 1

        license_link = result.licenses[0]
        assert license_link.spdx_id == "Apache-2.0"
        assert license_link.name == "Apache License 2.0"
        assert license_link.url == "https://spdx.org/licenses/Apache-2.0.html"
        assert license_link.is_verified_file is False

    @pytest.mark.asyncio
    async def test_resolve_gpl_license(self, resolver):
        """Test resolving GPL-3.0-only license to SPDX URL."""
        spec = PackageSpec(name="gpl-package", version="3.0.0")

        result = await resolver.resolve(spec, spdx_id="GPL-3.0-only")

        assert result is not None
        assert len(result.licenses) == 1

        license_link = result.licenses[0]
        assert license_link.spdx_id == "GPL-3.0-only"
        assert license_link.name == "GNU General Public License v3.0 only"
        assert license_link.url == "https://spdx.org/licenses/GPL-3.0-only.html"
        assert license_link.is_verified_file is False

    @pytest.mark.asyncio
    async def test_resolve_bsd_3_clause_license(self, resolver):
        """Test resolving BSD-3-Clause license to SPDX URL."""
        spec = PackageSpec(name="bsd-lib", version="1.5.0")

        result = await resolver.resolve(spec, spdx_id="BSD-3-Clause")

        assert result is not None
        assert len(result.licenses) == 1

        license_link = result.licenses[0]
        assert license_link.spdx_id == "BSD-3-Clause"
        assert license_link.name == "BSD 3-Clause \"New\" or \"Revised\" License"
        assert license_link.url == "https://spdx.org/licenses/BSD-3-Clause.html"
        assert license_link.is_verified_file is False

    @pytest.mark.asyncio
    async def test_resolve_bsd_2_clause_license(self, resolver):
        """Test resolving BSD-2-Clause license to SPDX URL."""
        spec = PackageSpec(name="bsd-simple", version="1.0.0")

        result = await resolver.resolve(spec, spdx_id="BSD-2-Clause")

        assert result is not None
        license_link = result.licenses[0]
        assert license_link.spdx_id == "BSD-2-Clause"
        assert license_link.name == "BSD 2-Clause \"Simplified\" License"
        assert license_link.url == "https://spdx.org/licenses/BSD-2-Clause.html"

    @pytest.mark.asyncio
    async def test_resolve_isc_license(self, resolver):
        """Test resolving ISC license to SPDX URL."""
        spec = PackageSpec(name="isc-package", version="1.0.0")

        result = await resolver.resolve(spec, spdx_id="ISC")

        assert result is not None
        license_link = result.licenses[0]
        assert license_link.spdx_id == "ISC"
        assert license_link.name == "ISC License"
        assert license_link.url == "https://spdx.org/licenses/ISC.html"

    @pytest.mark.asyncio
    async def test_resolve_mpl_license(self, resolver):
        """Test resolving MPL-2.0 license to SPDX URL."""
        spec = PackageSpec(name="mozilla-lib", version="2.0.0")

        result = await resolver.resolve(spec, spdx_id="MPL-2.0")

        assert result is not None
        license_link = result.licenses[0]
        assert license_link.spdx_id == "MPL-2.0"
        assert license_link.name == "Mozilla Public License 2.0"
        assert license_link.url == "https://spdx.org/licenses/MPL-2.0.html"

    @pytest.mark.asyncio
    async def test_resolve_unknown_spdx_id(self, resolver):
        """Test resolving an unknown SPDX ID generates generic name."""
        spec = PackageSpec(name="unknown-pkg", version="1.0.0")

        result = await resolver.resolve(spec, spdx_id="Custom-License-1.0")

        assert result is not None
        assert len(result.licenses) == 1

        license_link = result.licenses[0]
        assert license_link.spdx_id == "Custom-License-1.0"
        assert license_link.name == "Custom-License-1.0"
        assert license_link.url == "https://spdx.org/licenses/Custom-License-1.0.html"
        assert license_link.is_verified_file is False

    @pytest.mark.asyncio
    async def test_resolve_without_spdx_id(self, resolver):
        """Test that resolver returns None when no SPDX ID is provided."""
        spec = PackageSpec(name="no-license", version="1.0.0")

        result = await resolver.resolve(spec)

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_with_empty_spdx_id(self, resolver):
        """Test that resolver returns None for empty SPDX ID."""
        spec = PackageSpec(name="empty-license", version="1.0.0")

        result = await resolver.resolve(spec, spdx_id="")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_with_whitespace_spdx_id(self, resolver):
        """Test that resolver returns None for whitespace-only SPDX ID."""
        spec = PackageSpec(name="whitespace-license", version="1.0.0")

        result = await resolver.resolve(spec, spdx_id="   ")

        assert result is None

    @pytest.mark.asyncio
    async def test_is_verified_file_always_false(self, resolver):
        """Test that all SPDX links are marked as not verified files."""
        spec = PackageSpec(name="test", version="1.0.0")

        # Test multiple licenses
        for spdx_id in ["MIT", "Apache-2.0", "GPL-3.0-only", "Custom-XYZ"]:
            result = await resolver.resolve(spec, spdx_id=spdx_id)
            assert result is not None
            assert result.licenses[0].is_verified_file is False

    @pytest.mark.asyncio
    async def test_preserves_package_metadata(self, resolver):
        """Test that resolver preserves package name and version."""
        spec = PackageSpec(name="my-package", version="2.3.4", source="pyproject.toml")

        result = await resolver.resolve(spec, spdx_id="MIT")

        assert result is not None
        assert result.name == "my-package"
        assert result.version == "2.3.4"
        # Source is not part of PackageMetadata, just PackageSpec

    @pytest.mark.asyncio
    async def test_gpl_or_later_variant(self, resolver):
        """Test resolving GPL-3.0-or-later variant."""
        spec = PackageSpec(name="gpl-or-later", version="1.0.0")

        result = await resolver.resolve(spec, spdx_id="GPL-3.0-or-later")

        assert result is not None
        license_link = result.licenses[0]
        assert license_link.spdx_id == "GPL-3.0-or-later"
        assert license_link.name == "GNU General Public License v3.0 or later"
        assert license_link.url == "https://spdx.org/licenses/GPL-3.0-or-later.html"
