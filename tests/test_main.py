import os
from unittest.mock import Mock, patch, AsyncMock

import pytest

from zyte_api.__main__ import run


class RequestError(Exception):
    @property
    def parsed(self):
        mock = Mock(response_body=Mock(decode=Mock(return_value=linkedin_response())))
        return mock


def is_file_not_empty(file_path):
    try:
        with open(file_path, "r") as file:
            # Read the first character to check if the file is empty
            first_char = file.read(1)
            return bool(first_char)
    except FileNotFoundError:
        return False


def delete_file(file_path):
    try:
        os.remove(file_path)
        print(f"File '{file_path}' has been deleted successfully.")
    except FileNotFoundError:
        print(f"File '{file_path}' not found. Unable to delete.")


def linkedin_response():
    response_str = '{"blockedDomain":"linkedin.com","type":"/download/domain-forbidden","title":"Domain Forbidden","status":451,"detail":"Extraction for the domain linkedin.com is forbidden."}'
    return response_str


async def fake_exception(value=True):
    # Simulating an error condition
    if value:
        raise RequestError()

    create_session_mock = AsyncMock()
    return await create_session_mock.coroutine()


@pytest.mark.parametrize(
    "queries,out",
    (
        (
            # test if it stores the error(s) also by adding flag
            (
                [
                    {
                        "url": "https://linkedin.com",
                        "browserHtml": True,
                        "echoData": "https://linkedin.com",
                    }
                ],
                open("test_response.jsonl", "w"),
            ),
        )
    ),
)
@pytest.mark.asyncio
async def test_run(queries, out):
    n_conn = 5
    stop_on_errors = False
    api_url = "https://example.com"
    api_key = "fake_key"
    retry_errors = True
    store_errors = True

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
            fake_exception(),
        ]

        # Call the run function with the mocked AsyncClient
        await run(
            queries=queries,
            out=out,
            n_conn=n_conn,
            stop_on_errors=stop_on_errors,
            api_url=api_url,
            api_key=api_key,
            retry_errors=retry_errors,
            store_errors=store_errors,
        )

    assert is_file_not_empty(out.name)
