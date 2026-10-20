from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientResponseError

from zyte_api.errors import ParsedError

logger = logging.getLogger("zyte_api")


def _is_undocumented_status(status: int) -> bool:
    # 503 is rate limiting, 520 and 521 are download errors.
    return status >= 500 and status not in {503, 520, 521}


class TooManyUndocumentedErrors(RuntimeError):
    """Exception raised by a client that has received :ref:`too many
    undocumented error responses <zapi-undocumented-error-limit>`.

    .. versionadded:: VERSION
    """

    def __init__(self, errors: int, total: int):
        super().__init__(
            f"Too many undocumented error responses received from Zyte API "
            f"({errors} out of {total}, {errors / total:.2%}). This client "
            f"will not send any more Zyte API requests. Please, check "
            f"https://status.zyte.com/ or contact support "
            f"(https://support.zyte.com/support/tickets/new) before sending "
            f"more requests like the ones causing these error responses."
        )


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
        return ParsedError.from_body(self.response_content or b"")

    def __str__(self) -> str:
        return (
            f"RequestError: {self.status}, url={self.query.get('url')!r}, "
            f"message={self.message}, headers={self.headers}, "
            f"body={self.response_content!r}, request_id={self.request_id}"
        )
