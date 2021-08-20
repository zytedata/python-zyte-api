import json
from typing import Optional

import attr


@attr.s(auto_attribs=True)
class ParsedError:
    """ Parsed error from Zyte Data API """
    response_body: bytes
    data: Optional[dict]
    parse_error: Optional[str]

    @classmethod
    def from_body(cls, response_body: bytes) -> 'ParsedError':
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

        return cls(
            response_body=response_body,
            data=data,
            parse_error=parse_error
        )

    @property
    def type(self) -> Optional[str]:
        return (self.data or {}).get('type', None)
