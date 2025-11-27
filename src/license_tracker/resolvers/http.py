from typing import Optional

import aiohttp

from license_tracker.resolvers.base import BaseResolver


class HttpResolver(BaseResolver):
    """Base class for resolvers that make HTTP requests.

    Manages a shared aiohttp.ClientSession for connection pooling and reuse.
    """

    def __init__(self) -> None:
        """Initialize the HttpResolver."""
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session.

        Returns:
            The shared aiohttp ClientSession.
        """
        if self._session is None or self._session.closed:
            self._session = self._create_session()
        return self._session

    def _create_session(self) -> aiohttp.ClientSession:
        """Create a new aiohttp.ClientSession.

        Subclasses can override this to provide custom session configuration.

        Returns:
            A new aiohttp.ClientSession instance.
        """
        return aiohttp.ClientSession()

    async def close(self) -> None:
        """Close the aiohttp session.

        Should be called when done using the resolver to release resources.
        """
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "HttpResolver":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
