"""Dependency scanners for various lock file formats.

This module provides scanners for extracting package specifications from
different dependency sources.
"""

from pathlib import Path

from license_tracker.scanners.base import BaseScanner
from license_tracker.scanners.pipenv import PipenvScanner
from license_tracker.scanners.poetry import PoetryScanner
from license_tracker.scanners.requirements import RequirementsScanner

__all__ = [
    "BaseScanner",
    "PipenvScanner",
    "PoetryScanner",
    "RequirementsScanner",
    "get_scanner",
]

# Registry of available scanners in priority order
_SCANNERS: list[type[BaseScanner]] = [
    PoetryScanner,
    PipenvScanner,
    RequirementsScanner,
]


def get_scanner(path: Path) -> BaseScanner:
    """Get the appropriate scanner for a given file path.

    Auto-detects the file type based on filename and returns the
    appropriate scanner instance.

    Args:
        path: Path to the lock/requirements file.

    Returns:
        Scanner instance configured for the given file.

    Raises:
        ValueError: If no scanner can handle the given file.
    """
    for scanner_cls in _SCANNERS:
        if scanner_cls.can_handle(path):
            return scanner_cls(path)

    raise ValueError(
        f"No scanner available for '{path.name}'. "
        f"Supported files: poetry.lock, Pipfile.lock, requirements*.txt"
    )
