from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientResponseError

from zyte_api.errors import ParsedError

logger = logging.getLogger("zyte_api")


class RequestError(ClientResponseError):
    """Exception raised upon receiving a :ref:`rate-limiting
    <zapi-rate-limit>` or :ref:`unsuccessful
    <zapi-unsuccessful-responses>` response from Zyte API."""

    def __init__(self, *args: Any, **kwargs: Any):
        #: Query sent to Zyte API.
        #:
        #: May be slightly different from the input query due to
        #: pre-processing logic on the client side.
        self.query: dict[str, Any] = kwargs.pop("query")

        #: Request ID.
        self.request_id: str | None = kwargs.get("headers", {}).get("request-id")

        #: Response body.
        self.response_content: bytes | None = kwargs.pop("response_content")

        super().__init__(*args, **kwargs)

    @property
    def parsed(self) -> ParsedError:
        """Response as a :class:`ParsedError` object."""
        # TODO: self.response_content can be None but ParsedError doesn't expect it
        return ParsedError.from_body(self.response_content)  # type: ignore[arg-type]

    def __str__(self) -> str:
        return (
            f"RequestError: {self.status}, message={self.message}, "
            f"headers={self.headers}, body={self.response_content!r}, "
            f"request_id={self.request_id}"
        )
