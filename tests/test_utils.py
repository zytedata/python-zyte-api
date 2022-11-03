from itertools import chain

import pytest
from pytest import raises
from w3lib.url import _path_safe_chars, _safe_chars

from zyte_api.utils import (
    _guess_intype,
    _process_query,
    RFC2396_FRAGMENT_SAFE_CHARS,
    RFC2396_PATH_SAFE_CHARS,
    RFC2396_QUERY_SAFE_CHARS,
)


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
        (
            {"url": "https://example.com"},
            {"url": "https://example.com"},
        ),
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
        *(
            (
                {"url": f"https://example.com/{bytes([char]).decode()}"},
                {"url": f"https://example.com/%{char:X}"},
            )
            for char in chain(
                (
                    ord(' '),
                ),
                # Characters that w3lib would not escape: []|%
                (
                    char
                    for char in _path_safe_chars
                    if (
                        char not in RFC2396_PATH_SAFE_CHARS
                        and char not in b"?#"
                    )
                )
            )
        ),
        (
            {"url": "https://example.com/ñ"},
            {"url": "https://example.com/%C3%B1"},
        ),
        *(
            (
                {"url": f"https://example.com?{bytes([char]).decode()}"},
                {"url": f"https://example.com?%{char:X}"},
            )
            for char in chain(
                (
                    ord(' '),
                ),
                # Characters that w3lib would not escape: []|%
                (
                    char
                    for char in _safe_chars
                    if (
                        char not in RFC2396_QUERY_SAFE_CHARS
                        and char not in b"#"
                    )
                )
            )
        ),
        (
            {"url": "https://example.com?ñ"},
            {"url": "https://example.com?%C3%B1"},
        ),
        *(
            (
                {"url": f"https://example.com#{bytes([char]).decode()}"},
                {"url": f"https://example.com#%{char:X}"},
            )
            for char in chain(
                (
                    ord(' '),
                ),
                # Characters that w3lib would not escape: #[]|%
                (
                    char
                    for char in _safe_chars
                    if char not in RFC2396_FRAGMENT_SAFE_CHARS
                )
            )
        ),
        (
            {"url": "https://example.com#ñ"},
            {"url": "https://example.com#%C3%B1"},
        ),
    ),
)
def test_process_query(input, output):
    assert _process_query(input) == output


def test_process_query_bytes():
    with raises(ValueError):
        _process_query({"url": b"https://example.com"})
