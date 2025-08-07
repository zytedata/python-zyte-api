import json
import subprocess
from json import JSONDecodeError
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import AsyncMock, Mock, patch

import pytest

from zyte_api.__main__ import run
from zyte_api.aio.errors import RequestError


class MockRequestError(RequestError):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            query={},
            response_content=b"",
            request_info=None,
            history=None,
            **kwargs,
        )

    @property
    def parsed(self):
        return Mock(
            response_body=Mock(decode=Mock(return_value=forbidden_domain_response()))
        )


def get_json_content(file_object):
    if not file_object:
        return None

    file_path = file_object.name
    try:
        with Path(file_path).open() as file:
            return json.load(file)
    except JSONDecodeError:
        pass


def forbidden_domain_response():
    return {
        "type": "/download/temporary-error",
        "title": "Temporary Downloading Error",
        "status": 520,
        "detail": "There is a downloading problem which might be temporary. Retry in N seconds from 'Retry-After' header or open a support ticket from https://support.zyte.com/support/tickets/new if it fails consistently.",
    }


async def fake_exception(value=True):
    # Simulating an error condition
    if value:
        raise MockRequestError

    create_session_mock = AsyncMock()
    return await create_session_mock.coroutine()


@pytest.mark.parametrize(
    ("queries", "expected_response", "store_errors", "exception"),
    (
        (
            # test if it stores the error(s) also by adding flag
            (
                [
                    {
                        "url": "https://forbidden.example",
                        "browserHtml": True,
                        "echoData": "https://forbidden.example",
                    }
                ],
                forbidden_domain_response(),
                True,
                fake_exception,
            ),
            # test with store_errors=False
            (
                [
                    {
                        "url": "https://forbidden.example",
                        "browserHtml": True,
                        "echoData": "https://forbidden.example",
                    }
                ],
                None,  # expected response should be None
                False,
                fake_exception,
            ),
        )
    ),
)
@pytest.mark.asyncio
async def test_run(queries, expected_response, store_errors, exception):
    tmp_path = Path("temporary_file.jsonl")
    temporary_file = tmp_path.open("w")
    n_conn = 5
    api_url = "https://example.com"
    api_key = "fake_key"
    retry_errors = True

    # Create a mock for AsyncZyteAPI
    async_client_mock = Mock()

    # Create a mock for the iter method
    request_parallel_mock = Mock()
    async_client_mock.return_value.iter = request_parallel_mock

    # Patch the AsyncZyteAPI class in __main__ with the mock
    with (
        patch("zyte_api.__main__.AsyncZyteAPI", async_client_mock),
        patch("zyte_api.__main__.create_session") as create_session_mock,
    ):
        # Mock create_session to return an AsyncMock
        create_session_mock.return_value = AsyncMock()

        # Set up the AsyncZyteAPI instance to return the mocked iterator
        async_client_mock.return_value.iter.return_value = [
            exception(),
        ]

        # Call the run function with the mocked AsyncZyteAPI
        await run(
            queries=queries,
            out=temporary_file,
            n_conn=n_conn,
            api_url=api_url,
            api_key=api_key,
            retry_errors=retry_errors,
            store_errors=store_errors,
        )

    assert get_json_content(temporary_file) == expected_response
    tmp_path.unlink()


@pytest.mark.asyncio
async def test_run_stop_on_errors_false(mockserver):
    queries = [{"url": "https://exception.example", "httpResponseBody": True}]
    with (
        NamedTemporaryFile("w") as output_file,
        pytest.warns(
            DeprecationWarning, match=r"^The stop_on_errors parameter is deprecated\.$"
        ),
    ):
        await run(
            queries=queries,
            out=output_file,
            n_conn=1,
            api_url=mockserver.urljoin("/"),
            api_key="a",
            stop_on_errors=False,
        )


@pytest.mark.asyncio
async def test_run_stop_on_errors_true(mockserver):
    query = {"url": "https://exception.example", "httpResponseBody": True}
    queries = [query]
    with (
        NamedTemporaryFile("w") as output_file,
        pytest.warns(
            DeprecationWarning, match=r"^The stop_on_errors parameter is deprecated\.$"
        ),
        pytest.raises(RequestError) as exc_info,
    ):
        await run(
            queries=queries,
            out=output_file,
            n_conn=1,
            api_url=mockserver.urljoin("/"),
            api_key="a",
            stop_on_errors=True,
        )
    assert exc_info.value.query == query


def _run(*, input, mockserver, cli_params=None):
    cli_params = cli_params or ()
    with NamedTemporaryFile("w") as url_list:
        url_list.write(input)
        url_list.flush()
        # Note: Using “python -m zyte_api” instead of “zyte-api” enables
        # coverage tracking to work.
        return subprocess.run(
            [
                "python",
                "-m",
                "zyte_api",
                "--api-key",
                "a",
                "--api-url",
                mockserver.urljoin("/"),
                url_list.name,
                *cli_params,
            ],
            capture_output=True,
            check=False,
        )


def test_empty_input(mockserver):
    result = _run(input="", mockserver=mockserver)
    assert result.returncode
    assert result.stdout == b""
    assert result.stderr == b"No input queries found. Is the input file empty?\n"


def test_intype_txt_implicit(mockserver):
    result = _run(input="https://a.example", mockserver=mockserver)
    assert not result.returncode
    assert (
        result.stdout
        == b'{"url": "https://a.example", "browserHtml": "<html><body>Hello<h1>World!</h1></body></html>"}\n'
    )


def test_intype_txt_explicit(mockserver):
    result = _run(
        input="https://a.example", mockserver=mockserver, cli_params=["--intype", "txt"]
    )
    assert not result.returncode
    assert (
        result.stdout
        == b'{"url": "https://a.example", "browserHtml": "<html><body>Hello<h1>World!</h1></body></html>"}\n'
    )


def test_intype_jsonl_implicit(mockserver):
    result = _run(
        input='{"url": "https://a.example", "browserHtml": true}', mockserver=mockserver
    )
    assert not result.returncode
    assert (
        result.stdout
        == b'{"url": "https://a.example", "browserHtml": "<html><body>Hello<h1>World!</h1></body></html>"}\n'
    )


def test_intype_jsonl_explicit(mockserver):
    result = _run(
        input='{"url": "https://a.example", "browserHtml": true}',
        mockserver=mockserver,
        cli_params=["--intype", "jl"],
    )
    assert not result.returncode
    assert (
        result.stdout
        == b'{"url": "https://a.example", "browserHtml": "<html><body>Hello<h1>World!</h1></body></html>"}\n'
    )


@pytest.mark.flaky(reruns=16)
def test_limit_and_shuffle(mockserver):
    result = _run(
        input="https://a.example\nhttps://b.example",
        mockserver=mockserver,
        cli_params=["--limit", "1", "--shuffle"],
    )
    assert not result.returncode
    assert (
        result.stdout
        == b'{"url": "https://b.example", "browserHtml": "<html><body>Hello<h1>World!</h1></body></html>"}\n'
    )


def test_run_non_json_response(mockserver):
    result = _run(
        input="https://nonjson.example",
        mockserver=mockserver,
    )
    assert not result.returncode
    assert result.stdout == b""
    assert b"json.decoder.JSONDecodeError" in result.stderr
