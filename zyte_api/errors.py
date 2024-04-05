import json
from typing import Optional

import attr


@attr.s(auto_attribs=True)
class ParsedError:
    """Parsed error response body from Zyte API."""

    #: Raw response body from Zyte API.
    response_body: bytes

    #: JSON-decoded response body.
    #:
    #: If ``None``, :data:`parse_error` indicates the reason.
    data: Optional[dict]

    #: If :data:`data` is ``None``, this indicates whether the reason is that
    #: :data:`response_body` is not valid JSON (``"bad_json"``) or that it is
    #: not a JSON object (``"bad_format"``).
    parse_error: Optional[str]

    @classmethod
    def from_body(cls, response_body: bytes) -> "ParsedError":
        """Return a :class:`ParsedError` object built out of the specified
        error response body."""
        data = None
        parse_error = None

        if response_body:
            try:
                data = json.loads(response_body.decode("utf-8"))
                if not isinstance(data, dict):
                    parse_error = "bad_format"
                    data = None
            except (json.JSONDecodeError, UnicodeDecodeError) as _:  # noqa: F841
                parse_error = "bad_json"

        return cls(response_body=response_body, data=data, parse_error=parse_error)

    @property
    def type(self) -> Optional[str]:
        """ID of the error type, e.g. ``"/limits/over-user-limit"`` or
        ``"/download/temporary-error"``."""
        return (self.data or {}).get("type", None)
