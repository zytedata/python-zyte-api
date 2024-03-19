import json
import os
import subprocess
from json import JSONDecodeError
from tempfile import NamedTemporaryFile
from unittest.mock import AsyncMock, Mock, patch

import pytest

from zyte_api.__main__ import run
from zyte_api.aio.errors import RequestError


class MockRequestError(Exception):
    @property
    def parsed(self):
        mock = Mock(
            response_body=Mock(decode=Mock(return_value=forbidden_domain_response()))
        )
        return mock


def get_json_content(file_object):
    if not file_object:
        return

    file_path = file_object.name
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except JSONDecodeError:
        pass


def delete_file(file_path):
    try:
        os.remove(file_path)
        print(f"File '{file_path}' has been deleted successfully.")
    except FileNotFoundError:
        print(f"File '{file_path}' not found. Unable to delete.")


def forbidden_domain_response():
    response_str = {
        "type": "/download/temporary-error",
        "title": "Temporary Downloading Error",
        "status": 520,
        "detail": "There is a downloading problem which might be temporary. Retry in N seconds from 'Retry-After' header or open a support ticket from https://support.zyte.com/support/tickets/new if it fails consistently.",
    }
    return response_str


async def fake_exception(value=True):
    # Simulating an error condition
    if value:
        raise MockRequestError()

    create_session_mock = AsyncMock()
    return await create_session_mock.coroutine()


@pytest.mark.parametrize(
    "queries,expected_response,store_errors,exception",
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
    temporary_file = open("temporary_file.jsonl", "w")
    n_conn = 5
    api_url = "https://example.com"
    api_key = "fake_key"
    retry_errors = True

    # Create a mock for AsyncClient
    async_client_mock = Mock()

    # Create a mock for the request_parallel_as_completed method
    request_parallel_mock = Mock()
    async_client_mock.return_value.request_parallel_as_completed = request_parallel_mock

    # Patch the AsyncClient class in __main__ with the mock
    with patch("zyte_api.__main__.AsyncClient", async_client_mock), patch(
        "zyte_api.__main__.create_session"
    ) as create_session_mock:
        # Mock create_session to return an AsyncMock
        create_session_mock.return_value = AsyncMock()

        # Set up the AsyncClient instance to return the mocked iterator
        async_client_mock.return_value.request_parallel_as_completed.return_value = [
            exception(),
        ]

        # Call the run function with the mocked AsyncClient
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


@pytest.mark.asyncio
async def test_run_stop_on_errors_false(mockserver):
    queries = [{"url": "https://exception.example", "httpResponseBody": True}]
    with NamedTemporaryFile("w") as output_file:
        with pytest.warns(
            DeprecationWarning, match=r"^The stop_on_errors parameter is deprecated\.$"
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
    queries = [{"url": "https://exception.example", "httpResponseBody": True}]
    with NamedTemporaryFile("w") as output_file:
        with pytest.warns(
            DeprecationWarning, match=r"^The stop_on_errors parameter is deprecated\.$"
        ):
            with pytest.raises(RequestError):
                await run(
                    queries=queries,
                    out=output_file,
                    n_conn=1,
                    api_url=mockserver.urljoin("/"),
                    api_key="a",
                    stop_on_errors=True,
                )


def _run(*, input, mockserver, cli_params=None):
    cli_params = cli_params or tuple()
    with NamedTemporaryFile("w") as url_list:
        url_list.write(input)
        url_list.flush()
        # Note: Using “python -m zyte_api” instead of “zyte-api” enables
        # coverage tracking to work.
        result = subprocess.run(
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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    return result


def test_main(mockserver):
    result = _run(input="https://a.example", mockserver=mockserver)
    assert not result.returncode
    assert (
        result.stdout
        == b'{"url": "https://a.example", "browserHtml": "<html><body>Hello<h1>World!</h1></body></html>"}\n'
    )


def test_empty_input(mockserver):
    result = _run(input="", mockserver=mockserver)
    assert result.returncode
    assert result.stdout == b""
    assert result.stderr == b"No input queries found. Is the input file empty?\n"
