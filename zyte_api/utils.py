import re
from os.path import splitext
from typing import Union
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from w3lib.url import RFC3986_RESERVED, RFC3986_UNRESERVED, RFC3986_USERINFO_SAFE_CHARS
from w3lib.util import to_unicode

from .__version__ import __version__

# https://github.com/scrapy/w3lib/blob/8e19741b6b004d6248fb70b525255a96a1eb1ee6/w3lib/url.py#L61-L63
_ascii_tab_newline_re = re.compile(
    r"[\t\n\r]"
)

_SAFE_CHARS = RFC3986_RESERVED + RFC3986_UNRESERVED + b"%"
_PATH_SAFE_CHARS = _SAFE_CHARS.replace(b"#", b"")


def _guess_intype(file_name, lines):
    _, dot_extension = splitext(file_name)
    extension = dot_extension[1:]
    if extension in {"jl", "jsonl"}:
        return "jl"
    if extension == "txt":
        return "txt"

    if re.search(r'^\s*\{', lines[0]):
        return "jl"

    return "txt"


def _process_query(query):
    """Given a query to be sent to Zyte API, return a functionally-equivalent
    query that fixes any known issue.

    Specifically, unsafe characters in the query URL are escaped.

    *query* is never modified in place, but the returned object is not
    guaranteed to be a copy of *query*: it could be *query* itself if no
    changes where needed, or a shallow copy of *query* with some common nested
    objects (e.g. shared ``actions`` list).
    """
    url = query.get("url", None)
    if url is None:
        return query
    if not isinstance(url, str):
        raise ValueError(f"Expected a str URL parameter, got {type(url)}")
    safe_url = _safe_url_string(url)
    if url == safe_url:
        return query
    return {**query, "url": safe_url}


def _safe_url_string(
    url: Union[bytes, str],
    encoding: str = "utf8",
    path_encoding: str = "utf8",
    quote_path: bool = True,
) -> str:
    """Fork of ``w3lib.url.safe_url_string`` that enforces `RFC-3986`_.

    ``w3lib.url.safe_url_string`` has an implementation closer to the
    `URL living standard`_ (e.g. does not encode “|”), while Zyte API expects
    RFC-3986-compliant URLs.

    Forked w3lib commit: 8e19741b6b004d6248fb70b525255a96a1eb1ee6

    .. _RFC-3986: https://datatracker.ietf.org/doc/html/rfc3986
    .. _URL living standard: https://url.spec.whatwg.org/
    """
    decoded = to_unicode(url, encoding=encoding, errors="percentencode")
    parts = urlsplit(_ascii_tab_newline_re.sub("", decoded))

    username, password, hostname, port = (
        parts.username,
        parts.password,
        parts.hostname,
        parts.port,
    )
    netloc_bytes = b""
    if username is not None or password is not None:
        if username is not None:
            safe_username = quote(unquote(username), RFC3986_USERINFO_SAFE_CHARS)
            netloc_bytes += safe_username.encode(encoding)
        if password is not None:
            netloc_bytes += b":"
            safe_password = quote(unquote(password), RFC3986_USERINFO_SAFE_CHARS)
            netloc_bytes += safe_password.encode(encoding)
        netloc_bytes += b"@"
    if hostname is not None:
        try:
            netloc_bytes += hostname.encode("idna")
        except UnicodeError:
            netloc_bytes += hostname.encode(encoding)
    if port is not None:
        netloc_bytes += b":"
        netloc_bytes += str(port).encode(encoding)

    netloc = netloc_bytes.decode()

    if quote_path:
        path = quote(parts.path.encode(path_encoding), _PATH_SAFE_CHARS)
    else:
        path = parts.path

    return urlunsplit(
        (
            parts.scheme,
            netloc,
            path,
            quote(parts.query.encode(encoding), _SAFE_CHARS),
            quote(parts.fragment.encode(encoding), _SAFE_CHARS),
        )
    )


def user_agent(library):
    return 'python-zyte-api/{} {}/{}'.format(
        __version__,
        library.__name__,
        library.__version__)
