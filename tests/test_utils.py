import pytest
from aiohttp import TCPConnector

from zyte_api._utils import create_session
from zyte_api.utils import _guess_intype, _process_query


@pytest.mark.asyncio
async def test_create_session_custom_connector():
    # Declare a connector with a random parameter to avoid it matching the
    # default one.
    custom_connector = TCPConnector(limit=1850)
    session = create_session(connector=custom_connector)
    assert session.connector == custom_connector


@pytest.mark.parametrize(
    ("file_name", "first_line", "expected"),
    (
        (
            "<stdin>",
            "https://toscrape.com",
            "txt",
        ),
        (
            "<stdin>",
            '{"url": "https://toscrape.com"}',
            "jl",
        ),
        (
            "<stdin>",
            ' {"url": "https://toscrape.com"}',
            "jl",
        ),
        (
            "urls.txt",
            "https://toscrape.com",
            "txt",
        ),
        (
            "urls.txt",
            '{"url": "https://toscrape.com"}',
            "txt",
        ),
        (
            "urls.jl",
            "https://toscrape.com",
            "jl",
        ),
        (
            "urls.jl",
            '{"url": "https://toscrape.com"}',
            "jl",
        ),
        (
            "urls.jsonl",
            "https://toscrape.com",
            "jl",
        ),
        (
            "urls.jsonl",
            '{"url": "https://toscrape.com"}',
            "jl",
        ),
    ),
)
def test_guess_intype(file_name, first_line, expected):
    assert _guess_intype(file_name, [first_line]) == expected


@pytest.mark.parametrize(
    ("input", "output"),
    (
        # Unsafe URLs in the url field are modified, while left untouched on
        # other fields.
        (
            {
                "a": {"b", "c"},
                "d": "https://example.com/ a",
                "url": "https://example.com/ a",
            },
            {
                "a": {"b", "c"},
                "d": "https://example.com/ a",
                "url": "https://example.com/%20a",
            },
        ),
        # Safe URLs are returned unmodified.
        (
            {"url": "https://example.com"},
            {"url": "https://example.com"},
        ),
        # URL fragments are kept.
        (
            {"url": "https://example.com#a"},
            {"url": "https://example.com#a"},
        ),
        # If no URL is passed, nothing is done.
        (
            {"a": "b"},
            {"a": "b"},
        ),
        # NOTE: We use w3lib.url.safe_url_string for escaping. Tests covering
        # the URL escaping logic exist upstream.
    ),
)
def test_process_query(input, output):
    assert _process_query(input) == output


def test_process_query_bytes():
    with pytest.raises(ValueError, match="Expected a str URL parameter"):
        _process_query({"url": b"https://example.com"})


@pytest.mark.asyncio  # https://github.com/aio-libs/aiohttp/pull/1468
async def test_deprecated_create_session():
    from zyte_api.aio.client import create_session as _create_session

    with pytest.warns(
        DeprecationWarning,
        match=r"^zyte_api\.aio\.client\.create_session is deprecated",
    ):
        _create_session()
