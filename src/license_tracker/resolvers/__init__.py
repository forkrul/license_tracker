"""License resolvers for fetching metadata from various sources.

This module provides resolvers for fetching license information from
PyPI, GitHub, SPDX, and other sources.
"""

from license_tracker.resolvers.base import BaseResolver, WaterfallResolverBase
from license_tracker.resolvers.github import GitHubResolver
from license_tracker.resolvers.pypi import PyPIResolver
from license_tracker.resolvers.spdx import SPDXResolver
from license_tracker.resolvers.waterfall import WaterfallResolver

__all__ = [
    "BaseResolver",
    "WaterfallResolverBase",
    "GitHubResolver",
    "PyPIResolver",
    "SPDXResolver",
    "WaterfallResolver",
]
