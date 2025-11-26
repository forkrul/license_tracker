"""Base interface for license resolvers.

Resolvers are responsible for fetching license metadata from various
sources such as PyPI, GitHub, or SPDX databases.
"""

from abc import ABC, abstractmethod
from typing import Optional

from license_tracker.models import PackageMetadata, PackageSpec


class BaseResolver(ABC):
    """Abstract base class for license resolvers.

    Resolvers fetch license information for packages from external sources.
    They should be async-compatible for efficient concurrent resolution.
    """

    @abstractmethod
    async def resolve(self, spec: PackageSpec) -> Optional[PackageMetadata]:
        """Resolve license metadata for a package.

        Args:
            spec: Package specification to resolve.

        Returns:
            PackageMetadata with license information, or None if resolution failed.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the resolver name for logging/debugging.

        Returns:
            Name like "PyPI", "GitHub", "SPDX", etc.
        """
        ...

    @property
    def priority(self) -> int:
        """Return resolver priority for waterfall ordering.

        Lower numbers are tried first. Default is 100.

        Returns:
            Priority value.
        """
        return 100


class WaterfallResolverBase(ABC):
    """Abstract base for waterfall resolution strategy.

    Orchestrates multiple resolvers in priority order, stopping at the
    first successful resolution.
    """

    def __init__(self, resolvers: list[BaseResolver]) -> None:
        """Initialize with a list of resolvers.

        Args:
            resolvers: List of resolvers to try in order.
        """
        self.resolvers = sorted(resolvers, key=lambda r: r.priority)

    @abstractmethod
    async def resolve(self, spec: PackageSpec) -> Optional[PackageMetadata]:
        """Resolve using waterfall strategy.

        Tries each resolver in priority order until one succeeds.

        Args:
            spec: Package specification to resolve.

        Returns:
            PackageMetadata from first successful resolver, or None.
        """
        ...

    @abstractmethod
    async def resolve_batch(
        self, specs: list[PackageSpec]
    ) -> dict[PackageSpec, Optional[PackageMetadata]]:
        """Resolve multiple packages concurrently.

        Args:
            specs: List of package specifications to resolve.

        Returns:
            Dictionary mapping specs to their resolved metadata (or None).
        """
        ...
