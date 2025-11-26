"""SPDX fallback resolver for license metadata.

This resolver generates SPDX license page URLs when no direct license file
can be found. It serves as a last-resort fallback in the waterfall resolution
chain, providing at least a reference to the license text even when the actual
file cannot be located.
"""

from typing import Optional

from license_tracker.models import LicenseLink, PackageMetadata, PackageSpec
from license_tracker.resolvers.base import BaseResolver


class SPDXResolver(BaseResolver):
    """Fallback resolver that generates SPDX license page URLs.

    This resolver does not perform any HTTP requests or external lookups.
    It simply constructs SPDX.org URLs from SPDX identifiers that have been
    determined by other resolvers or metadata sources.

    The generated URLs point to generic license information pages rather than
    actual license files, so they are marked as is_verified_file=False.

    Priority: 1000 (lowest, used as last resort)
    """

    # Common SPDX identifiers mapped to human-readable names
    # Based on https://spdx.org/licenses/
    SPDX_NAMES = {
        "MIT": "MIT License",
        "Apache-2.0": "Apache License 2.0",
        "GPL-3.0-only": "GNU General Public License v3.0 only",
        "GPL-3.0-or-later": "GNU General Public License v3.0 or later",
        "GPL-2.0-only": "GNU General Public License v2.0 only",
        "GPL-2.0-or-later": "GNU General Public License v2.0 or later",
        "LGPL-3.0-only": "GNU Lesser General Public License v3.0 only",
        "LGPL-3.0-or-later": "GNU Lesser General Public License v3.0 or later",
        "LGPL-2.1-only": "GNU Lesser General Public License v2.1 only",
        "LGPL-2.1-or-later": "GNU Lesser General Public License v2.1 or later",
        "BSD-3-Clause": 'BSD 3-Clause "New" or "Revised" License',
        "BSD-2-Clause": 'BSD 2-Clause "Simplified" License',
        "ISC": "ISC License",
        "MPL-2.0": "Mozilla Public License 2.0",
        "EPL-2.0": "Eclipse Public License 2.0",
        "AGPL-3.0-only": "GNU Affero General Public License v3.0 only",
        "AGPL-3.0-or-later": "GNU Affero General Public License v3.0 or later",
        "LGPL-2.0-only": "GNU Library General Public License v2 only",
        "LGPL-2.0-or-later": "GNU Library General Public License v2 or later",
        "CC0-1.0": "Creative Commons Zero v1.0 Universal",
        "Unlicense": "The Unlicense",
        "WTFPL": "Do What The F*ck You Want To Public License",
    }

    @property
    def name(self) -> str:
        """Return the resolver name.

        Returns:
            "SPDX"
        """
        return "SPDX"

    @property
    def priority(self) -> int:
        """Return lowest priority for fallback usage.

        Returns:
            1000 (highest number = lowest priority = tried last)
        """
        return 1000

    async def resolve(
        self, spec: PackageSpec, spdx_id: Optional[str] = None
    ) -> Optional[PackageMetadata]:
        """Generate SPDX license page URL from an SPDX identifier.

        This resolver requires an SPDX ID to be provided, typically from
        package metadata discovered by other resolvers. It does not perform
        any external lookups itself.

        Args:
            spec: Package specification to resolve.
            spdx_id: SPDX license identifier (e.g., "MIT", "Apache-2.0").

        Returns:
            PackageMetadata with a single LicenseLink pointing to the SPDX
            license page, or None if no valid SPDX ID was provided.
        """
        # Validate SPDX ID
        if not spdx_id or not spdx_id.strip():
            return None

        spdx_id = spdx_id.strip()

        # Generate SPDX.org URL
        url = f"https://spdx.org/licenses/{spdx_id}.html"

        # Get human-readable name, fallback to SPDX ID if not in mapping
        name = self.SPDX_NAMES.get(spdx_id, spdx_id)

        # Create license link (not a verified file, just a reference page)
        license_link = LicenseLink(
            spdx_id=spdx_id,
            name=name,
            url=url,
            is_verified_file=False,
        )

        # Return metadata with single license
        return PackageMetadata(
            name=spec.name,
            version=spec.version,
            licenses=[license_link],
        )
