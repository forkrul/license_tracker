"""Scanner for Pipenv Pipfile.lock files.

This scanner extracts package specifications from Pipfile.lock files,
which are JSON-formatted lock files created by Pipenv.
"""

import json
from pathlib import Path

from license_tracker.models import PackageSpec
from license_tracker.scanners.base import BaseScanner


class PipenvScanner(BaseScanner):
    """Scanner for Pipenv Pipfile.lock files.

    Parses Pipfile.lock JSON format to extract package names and versions
    from both the "default" and "develop" sections.

    Example Pipfile.lock structure::

        {
            "_meta": {...},
            "default": {
                "requests": {"version": "==2.31.0", ...}
            },
            "develop": {
                "pytest": {"version": "==8.0.0", ...}
            }
        }
    """

    @classmethod
    def can_handle(cls, path: Path) -> bool:
        """Check if this scanner can handle the given file.

        Args:
            path: Path to check.

        Returns:
            True if the file is named "Pipfile.lock" (case-sensitive).
        """
        return path.name == "Pipfile.lock"

    @property
    def source_name(self) -> str:
        """Return the human-readable name for this scanner's source type.

        Returns:
            "Pipfile.lock"
        """
        return "Pipfile.lock"

    def scan(self) -> list[PackageSpec]:
        """Scan Pipfile.lock and extract package specifications.

        Parses the JSON file and extracts packages from both "default" and
        "develop" sections. Version strings are normalized by stripping the
        "==" prefix that Pipenv uses.

        Returns:
            List of PackageSpec objects with name, version, and source="Pipfile.lock".

        Raises:
            FileNotFoundError: If the Pipfile.lock file does not exist.
            ValueError: If source_path is not provided or JSON is invalid.
        """
        if self.source_path is None:
            raise ValueError("source_path must be provided")

        if not self.source_path.exists():
            raise FileNotFoundError(f"File not found: {self.source_path}")

        try:
            with open(self.source_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.source_path}: {e}") from e

        packages = []

        # Extract packages from default section
        default_packages = data.get("default", {})
        for package_name, package_info in default_packages.items():
            version = self._normalize_version(package_info.get("version", ""))
            if version:
                packages.append(
                    PackageSpec(
                        name=package_name,
                        version=version,
                        source=self.source_name,
                    )
                )

        # Extract packages from develop section
        develop_packages = data.get("develop", {})
        for package_name, package_info in develop_packages.items():
            version = self._normalize_version(package_info.get("version", ""))
            if version:
                packages.append(
                    PackageSpec(
                        name=package_name,
                        version=version,
                        source=self.source_name,
                    )
                )

        return packages

    def _normalize_version(self, version: str) -> str:
        """Normalize version string by stripping Pipenv's == prefix.

        Args:
            version: Version string from Pipfile.lock (e.g., "==2.31.0").

        Returns:
            Normalized version string (e.g., "2.31.0").
        """
        return version.lstrip("=").strip()
