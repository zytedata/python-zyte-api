from __future__ import annotations

import json
from typing import Optional

import attr


def _to_kebab_case(s: str) -> str:
    return s.strip().replace(" ", "-").replace("_", "-").lower()


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
    def from_body(cls, response_body: bytes) -> ParsedError:
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
            except (json.JSONDecodeError, UnicodeDecodeError) as _:
                parse_error = "bad_json"

        return cls(response_body=response_body, data=data, parse_error=parse_error)

    @property
    def type(self) -> Optional[str]:
        """ID of the error type, e.g. ``"/limits/over-user-limit"`` or
        ``"/download/temporary-error"``."""
        data = self.data or {}
        if "type" in data:
            return data["type"]
        if "error" in data and isinstance(data["error"], str):  # HTTP 402
            try:
                prefix, _ = data["error"].split(":", 1)
            except ValueError:
                prefix = data["error"]
            if len(prefix) > 32:
                return None
            return f"/x402/{_to_kebab_case(prefix)}"
        return None
