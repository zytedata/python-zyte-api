import pytest
from pytest import raises

from zyte_api.utils import _guess_intype, _process_query


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
    "unaffected",
    (
        {},
        {"a": "b"},
        {"a": {"b": "c"}},
    ),
)
@pytest.mark.parametrize(
    "input,output",
    (
        (
            {"url": "https://example.com"},
            {"url": "https://example.com"},
        ),
        (
            {"url": "https://example.com/a b"},
            {"url": "https://example.com/a%20b"},
        ),
        (
            {"url": "https://example.com/a|b"},
            {"url": "https://example.com/a%7Cb"},
        ),
        (
            {"url": "https://example.com?a=b c"},
            {"url": "https://example.com?a=b%20c"},
        ),
        (
            {"url": "https://example.com?a=b|c"},
            {"url": "https://example.com?a=b%7Cc"},
        ),
    ),
)
def test_process_query(unaffected, input, output):
    assert _process_query({**unaffected, **input}) == {**unaffected, **output}


def test_process_query_bytes():
    with raises(ValueError):
        _process_query({"url": b"https://example.com"})
