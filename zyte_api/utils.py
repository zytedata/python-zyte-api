import re
from os.path import splitext

from w3lib.url import safe_url_string

from .__version__ import __version__

USER_AGENT = f"python-zyte-api/{__version__}"


def _guess_intype(file_name, lines):
    _, dot_extension = splitext(file_name)
    extension = dot_extension[1:]
    if extension in {"jl", "jsonl"}:
        return "jl"
    if extension == "txt":
        return "txt"

    if re.search(r"^\s*\{", lines[0]):
        return "jl"

    return "txt"


def _process_query(query):
    """Given a query to be sent to Zyte API, return a functionally-equivalent
    query that fixes any known issue.

    Specifically, unsafe characters in the query URL are escaped to make sure
    they are safe not only for the end server, but also for Zyte API, which
    requires URLs compatible with RFC 2396.

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
    safe_url = safe_url_string(url)
    if url == safe_url:
        return query
    return {**query, "url": safe_url}
