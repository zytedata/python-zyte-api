import asyncio
import os

import pytest

from zyte_api.__main__ import run
from zyte_api.apikey import get_apikey
from zyte_api.constants import API_URL


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


@pytest.mark.parametrize(
    "queries,out,n_conn,stop_on_errors,retry_errors,store_errors",
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
            20,
            False,
            True,
            True,
        ),
    ),
)
def test_run_stores_error(
    queries, out, n_conn, stop_on_errors, retry_errors, store_errors
):
    coro = run(
        queries,
        out=out,
        n_conn=n_conn,
        stop_on_errors=stop_on_errors,
        api_url=API_URL,
        api_key=get_apikey(),
        retry_errors=retry_errors,
        store_errors=store_errors,
    )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(coro)
    assert is_file_not_empty(out.name) is True
    delete_file(out.name)


@pytest.mark.parametrize(
    "queries,out,n_conn,stop_on_errors,retry_errors,store_errors",
    (
        # test if it doesn't store the error(s)
        (
            [
                {
                    "url": "https://linkedin.com",
                    "browserHtml": True,
                    "echoData": "https://linkedin.com",
                }
            ],
            open("test_response.jsonl", "w"),
            20,
            False,
            True,
            False,
        ),
    ),
)
def test_run_dont_stores_error(
    queries, out, n_conn, stop_on_errors, retry_errors, store_errors
):
    coro = run(
        queries,
        out=out,
        n_conn=n_conn,
        stop_on_errors=stop_on_errors,
        api_url=API_URL,
        api_key=get_apikey(),
        retry_errors=retry_errors,
        store_errors=store_errors,
    )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(coro)
    assert not is_file_not_empty(out.name)
