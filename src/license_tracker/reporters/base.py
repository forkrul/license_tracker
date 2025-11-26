"""Base interface for output reporters.

Reporters generate formatted output (Markdown, HTML, JSON, etc.) from
resolved package metadata.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from license_tracker.models import PackageMetadata


class BaseReporter(ABC):
    """Abstract base class for output reporters.

    Reporters take resolved package metadata and generate formatted
    output documents.
    """

    @abstractmethod
    def render(
        self,
        packages: list[PackageMetadata],
        root_project: Optional[PackageMetadata] = None,
    ) -> str:
        """Render package metadata to formatted output.

        Args:
            packages: List of resolved package metadata.
            root_project: Optional root project metadata to include.

        Returns:
            Rendered output as a string.
        """
        ...

    def write(
        self,
        packages: list[PackageMetadata],
        output_path: Path,
        root_project: Optional[PackageMetadata] = None,
    ) -> None:
        """Render and write output to a file.

        Args:
            packages: List of resolved package metadata.
            output_path: Path to write the output file.
            root_project: Optional root project metadata to include.
        """
        content = self.render(packages, root_project)
        output_path.write_text(content, encoding="utf-8")

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Return the output format name.

        Returns:
            Format name like "markdown", "html", "json", etc.
        """
        ...

    @property
    @abstractmethod
    def default_extension(self) -> str:
        """Return the default file extension for this format.

        Returns:
            Extension like ".md", ".html", ".json", etc.
        """
        ...
