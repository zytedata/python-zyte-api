import json
import os
from json import JSONDecodeError
from unittest.mock import AsyncMock, Mock, patch

import pytest

from zyte_api.__main__ import run


class RequestError(Exception):
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
        raise RequestError()

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
    stop_on_errors = False
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
            stop_on_errors=stop_on_errors,
            api_url=api_url,
            api_key=api_key,
            retry_errors=retry_errors,
            store_errors=store_errors,
        )

    assert get_json_content(temporary_file) == expected_response
