"""Markdown reporter for generating license attribution files.

This module provides a reporter that generates Markdown-formatted license
attribution documents using Jinja2 templates.
"""

from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, Template

from license_tracker.models import PackageMetadata
from license_tracker.reporters.base import BaseReporter


class MarkdownReporter(BaseReporter):
    """Reporter that generates Markdown license attribution files.

    Uses Jinja2 templates to render package metadata into a formatted
    Markdown document suitable for inclusion in project documentation.

    Attributes:
        template: The Jinja2 template to use for rendering.
    """

    def __init__(self, template_path: Optional[Path] = None) -> None:
        """Initialize the Markdown reporter.

        Args:
            template_path: Optional path to a custom Jinja2 template.
                If not provided, uses the default bundled template.
        """
        if template_path:
            # Load custom template from file
            env = Environment(
                loader=FileSystemLoader(template_path.parent),
                autoescape=False,
            )
            self.template = env.get_template(template_path.name)
        else:
            # Load default template from package resources
            self.template = self._load_default_template()

    def _load_default_template(self) -> Template:
        """Load the default bundled Jinja2 template.

        Returns:
            The default template loaded from package resources.
        """
        template_content = (
            files("license_tracker.templates")
            .joinpath("licenses.md.j2")
            .read_text(encoding="utf-8")
        )
        env = Environment(autoescape=False)
        return env.from_string(template_content)

    def render(
        self,
        packages: list[PackageMetadata],
        root_project: Optional[PackageMetadata] = None,
    ) -> str:
        """Render package metadata to Markdown format.

        Args:
            packages: List of resolved package metadata.
            root_project: Optional root project metadata to include.

        Returns:
            Rendered Markdown document as a string.
        """
        return self.template.render(
            packages=packages,
            root_project=root_project,
            generated_at=datetime.now(),
        )

    @property
    def format_name(self) -> str:
        """Return the output format name.

        Returns:
            The string "markdown".
        """
        return "markdown"

    @property
    def default_extension(self) -> str:
        """Return the default file extension for Markdown files.

        Returns:
            The string ".md".
        """
        return ".md"
