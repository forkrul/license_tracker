"""Scanner for requirements.txt files.

This module provides a scanner that parses requirements.txt files to extract
package specifications. It handles various version specifier formats and
skips git URLs, comments, and blank lines.
"""

import logging
import re
from pathlib import Path

from license_tracker.models import PackageSpec
from license_tracker.scanners.base import BaseScanner

logger = logging.getLogger(__name__)


class RequirementsScanner(BaseScanner):
    """Scanner for requirements.txt format files.

    Parses pip requirements files to extract package names and versions.
    Supports various version specifiers (==, >=, ~=, <, >, etc.) and handles
    comments, blank lines, and git URLs appropriately.

    The scanner extracts the base version from range specifiers. For example:
    - "package==1.0.0" -> version "1.0.0"
    - "package>=1.0.0" -> version "1.0.0"
    - "package>=1.0.0,<2.0.0" -> version "1.0.0"
    - "package~=1.0.0" -> version "1.0.0"
    """

    # Regex pattern to match package specifications
    # Matches: package_name [optional version specifier(s)]
    PACKAGE_PATTERN = re.compile(
        r'^([a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?)'  # Package name
        r'(?:\s*([><=~!]+)\s*([0-9][0-9a-zA-Z._-]*))?'  # Optional version specifier
    )

    # Pattern to detect git URLs
    GIT_URL_PATTERN = re.compile(r'(^git\+|\.git[@#]|^-e\s+git\+)')

    @classmethod
    def can_handle(cls, path: Path) -> bool:
        """Check if this scanner can handle the given file.

        Handles files with names matching ``requirements*.txt`` or
        ``*-requirements.txt`` or ``*_requirements.txt`` patterns.

        Args:
            path: Path to check.

        Returns:
            True if the filename matches a requirements file pattern, False otherwise.
        """
        filename = path.name.lower()
        return (
            filename == "requirements.txt"
            or filename.startswith("requirements")
            and filename.endswith(".txt")
            or "requirements" in filename
            and filename.endswith(".txt")
        )

    @property
    def source_name(self) -> str:
        """Return a human-readable name for this scanner's source type.

        Returns:
            "requirements.txt"
        """
        return "requirements.txt"

    def scan(self) -> list[PackageSpec]:
        """Scan the requirements.txt file and extract package specifications.

        Parses the file line by line, extracting package names and versions.
        Handles:
        - Various version specifiers (==, >=, ~=, <, >, etc.)
        - Multiple comma-separated version constraints (uses first version)
        - Comments (both full-line and inline)
        - Blank lines
        - Git URLs (skipped with warning)

        Returns:
            List of PackageSpec objects with source="requirements.txt".

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the source path was not provided.
        """
        if not self.source_path:
            raise ValueError("source_path must be provided")

        if not self.source_path.exists():
            raise FileNotFoundError(f"Requirements file not found: {self.source_path}")

        packages = []

        with open(self.source_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                # Strip whitespace
                line = line.strip()

                # Skip blank lines
                if not line:
                    continue

                # Skip comment lines
                if line.startswith('#'):
                    continue

                # Strip inline comments
                if '#' in line:
                    line = line.split('#', 1)[0].strip()

                # Skip git URLs
                if self.GIT_URL_PATTERN.search(line):
                    logger.warning(
                        f"Skipping git URL on line {line_num}: {line[:50]}..."
                        if len(line) > 50 else f"Skipping git URL on line {line_num}: {line}"
                    )
                    continue

                # Skip editable installs and options
                if line.startswith('-'):
                    continue

                # Parse the package specification
                package_spec = self._parse_line(line)
                if package_spec:
                    packages.append(package_spec)
                else:
                    logger.debug(f"Could not parse line {line_num}: {line}")

        return packages

    def _parse_line(self, line: str) -> PackageSpec | None:
        """Parse a single line from requirements.txt.

        Args:
            line: A cleaned line from the file (no comments, whitespace stripped).

        Returns:
            PackageSpec if the line contains a valid package specification,
            None otherwise.
        """
        # Handle multiple version constraints (e.g., "package>=1.0,<2.0")
        # Split by comma and process the first constraint
        parts = line.split(',')
        first_part = parts[0].strip()

        match = self.PACKAGE_PATTERN.match(first_part)
        if not match:
            return None

        package_name = match.group(1)
        version_op = match.group(3)  # The operator (==, >=, etc.)
        version_num = match.group(4)  # The version number

        # If no version specified, we can't create a PackageSpec
        # (it requires a version)
        if not version_num:
            logger.debug(f"No version specified for package: {package_name}")
            return None

        # Clean up version number (remove any trailing operators or whitespace)
        version_num = version_num.strip()

        return PackageSpec(
            name=package_name,
            version=version_num,
            source=self.source_name
        )
