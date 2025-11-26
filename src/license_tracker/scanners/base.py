"""Base interface for dependency scanners.

Scanners extract package specifications from various sources such as
lock files, requirements files, or the installed environment.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from license_tracker.models import PackageSpec


class BaseScanner(ABC):
    """Abstract base class for dependency scanners.

    Scanners are responsible for extracting package names and versions
    from various sources without requiring package installation.

    Attributes:
        source_path: Optional path to the file being scanned.
    """

    def __init__(self, source_path: Optional[Path] = None) -> None:
        """Initialize the scanner.

        Args:
            source_path: Optional path to the source file (lock file, requirements, etc.).
        """
        self.source_path = source_path

    @abstractmethod
    def scan(self) -> list[PackageSpec]:
        """Scan the source and extract package specifications.

        Returns:
            List of PackageSpec objects representing discovered dependencies.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the source format is invalid.
        """
        ...

    @classmethod
    @abstractmethod
    def can_handle(cls, path: Path) -> bool:
        """Check if this scanner can handle the given file.

        Args:
            path: Path to check.

        Returns:
            True if this scanner can process the file, False otherwise.
        """
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return a human-readable name for this scanner's source type.

        Returns:
            Name like "poetry.lock", "Pipfile.lock", etc.
        """
        ...
