import pytest

from zyte_api.utils import _guess_intype


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
