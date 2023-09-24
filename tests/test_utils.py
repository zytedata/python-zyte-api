import pytest
from pytest import raises

from zyte_api.aio.client import AsyncClient
from zyte_api.utils import USER_AGENT, _guess_intype, _process_query


@pytest.mark.parametrize(
    "file_name,first_line,expected",
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
    "input,output",
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
        # NOTE: We use w3lib.url.safe_url_string for escaping. Tests covering
        # the URL escaping logic exist upstream.
    ),
)
def test_process_query(input, output):
    assert _process_query(input) == output


def test_process_query_bytes():
    with raises(ValueError):
        _process_query({"url": b"https://example.com"})


@pytest.mark.parametrize(
    "user_agent,expected",
    (
        (
            None,
            USER_AGENT,
        ),
        (
            f'{USER_AGENT}, scrapy-zyte-api/0.11.1',
            f'{USER_AGENT}, scrapy-zyte-api/0.11.1',
        ),
    ),
)
def test_user_agent(user_agent, expected):
    client = AsyncClient(api_key='123', api_url='http:\\test', user_agent=user_agent)
    assert client.user_agent == expected
