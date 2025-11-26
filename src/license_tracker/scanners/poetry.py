"""Scanner for Poetry lock files.

This module provides functionality to parse poetry.lock files and extract
package specifications for license tracking.
"""

import tomllib
from pathlib import Path
from typing import Any

from license_tracker.models import PackageSpec
from license_tracker.scanners.base import BaseScanner


class PoetryScanner(BaseScanner):
    """Scanner for Poetry lock files.

    Parses poetry.lock files (TOML format) to extract package names and versions
    from [[package]] sections.
    """

    def scan(self) -> list[PackageSpec]:
        """Scan poetry.lock file and extract package specifications.

        Returns:
            List of PackageSpec objects representing discovered dependencies.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the source format is invalid or source_path is not set.
        """
        if self.source_path is None:
            raise ValueError("source_path must be set before calling scan()")

        if not self.source_path.exists():
            raise FileNotFoundError(f"Poetry lock file not found: {self.source_path}")

        try:
            with open(self.source_path, "rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"Invalid TOML in {self.source_path}: {e}") from e

        packages: list[PackageSpec] = []

        # Extract packages from [[package]] sections
        package_list = data.get("package", [])

        for pkg in package_list:
            # Validate required fields
            if "name" not in pkg:
                raise ValueError(
                    f"Package missing required field 'name' in {self.source_path}"
                )
            if "version" not in pkg:
                raise ValueError(
                    f"Package missing required field 'version' in {self.source_path}"
                )

            packages.append(
                PackageSpec(
                    name=pkg["name"],
                    version=pkg["version"],
                    source="poetry.lock",
                )
            )

        return packages

    @classmethod
    def can_handle(cls, path: Path) -> bool:
        """Check if this scanner can handle the given file.

        Args:
            path: Path to check.

        Returns:
            True if the file is named "poetry.lock", False otherwise.
        """
        return path.name == "poetry.lock"

    @property
    def source_name(self) -> str:
        """Return a human-readable name for this scanner's source type.

        Returns:
            The string "poetry.lock".
        """
        return "poetry.lock"
