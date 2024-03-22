import logging
from typing import Optional

from aiohttp import ClientResponseError

from zyte_api.errors import ParsedError

logger = logging.getLogger("zyte_api")


class RequestError(ClientResponseError):
    """Exception raised upon receiving a :ref:`rate-limiting
    <zyte-api-rate-limit>` or :ref:`unsuccessful
    <zyte-api-unsuccessful-responses>` response from Zyte API."""

    def __init__(self, *args, **kwargs):
        #: Response body.
        self.response_content: Optional[bytes] = kwargs.pop("response_content")
        #: Request ID.
        self.request_id: Optional[str] = kwargs.get("headers", {}).get("request-id")
        super().__init__(*args, **kwargs)

    @property
    def parsed(self):
        """Response as a :class:`ParsedError` object."""
        return ParsedError.from_body(self.response_content)

    def __str__(self):
        return (
            f"RequestError: {self.status}, message={self.message}, "
            f"headers={self.headers}, body={self.response_content}, "
            f"request_id={self.request_id}"
        )
