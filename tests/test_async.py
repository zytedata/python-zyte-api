import pytest
from tenacity import AsyncRetrying

from zyte_api import AsyncZyteAPI, RequestError
from zyte_api.apikey import NoApiKey
from zyte_api.errors import ParsedError


def test_api_key():
    AsyncZyteAPI(api_key="a")
    with pytest.raises(NoApiKey):
        AsyncZyteAPI()


@pytest.mark.asyncio
async def test_get(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    expected_result = {
        "url": "https://a.example",
        "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
    }
    actual_result = await client.get(
        {"url": "https://a.example", "httpResponseBody": True}
    )
    assert actual_result == expected_result


UNSET = object()
RETRY_EXCEPTION = RuntimeError


@pytest.mark.parametrize(
    ("value", "exception"),
    (
        (UNSET, RETRY_EXCEPTION),
        (True, RETRY_EXCEPTION),
        (False, RequestError),
    ),
)
@pytest.mark.asyncio
async def test_get_handle_retries(value, exception, mockserver):
    kwargs = {}
    if value is not UNSET:
        kwargs["handle_retries"] = value

    def broken_stop(_):
        raise RETRY_EXCEPTION

    retrying = AsyncRetrying(stop=broken_stop)
    client = AsyncZyteAPI(
        api_key="a", api_url=mockserver.urljoin("/"), retrying=retrying
    )
    with pytest.raises(exception):
        await client.get(
            {"url": "https://exception.example", "browserHtml": True},
            **kwargs,
        )


@pytest.mark.asyncio
async def test_get_request_error(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    with pytest.raises(RequestError) as request_error_info:
        await client.get(
            {"url": "https://exception.example", "browserHtml": True},
        )
    parsed_error = request_error_info.value.parsed
    assert isinstance(parsed_error, ParsedError)
    assert parsed_error.data == {
        "detail": "The authentication key is not valid or can't be matched.",
        "status": 401,
        "title": "Authentication Key Not Found",
        "type": "/auth/key-not-found",
    }


@pytest.mark.asyncio
async def test_get_request_error_empty_body(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    with pytest.raises(RequestError) as request_error_info:
        await client.get(
            {"url": "https://empty-body-exception.example", "browserHtml": True},
        )
    parsed_error = request_error_info.value.parsed
    assert isinstance(parsed_error, ParsedError)
    assert parsed_error.data is None


@pytest.mark.asyncio
async def test_get_request_error_non_json(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    with pytest.raises(RequestError) as request_error_info:
        await client.get(
            {"url": "https://nonjson-exception.example", "browserHtml": True},
        )
    parsed_error = request_error_info.value.parsed
    assert isinstance(parsed_error, ParsedError)
    assert parsed_error.data is None


@pytest.mark.asyncio
async def test_get_request_error_unexpected_json(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    with pytest.raises(RequestError) as request_error_info:
        await client.get(
            {"url": "https://array-exception.example", "browserHtml": True},
        )
    parsed_error = request_error_info.value.parsed
    assert isinstance(parsed_error, ParsedError)
    assert parsed_error.data is None


@pytest.mark.asyncio
async def test_iter(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    queries = [
        {"url": "https://a.example", "httpResponseBody": True},
        {"url": "https://exception.example", "httpResponseBody": True},
        {"url": "https://b.example", "httpResponseBody": True},
    ]
    expected_results = [
        {
            "url": "https://a.example",
            "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
        },
        Exception,
        {
            "url": "https://b.example",
            "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
        },
    ]
    actual_results = []
    for future in client.iter(queries):
        try:
            actual_result = await future
        except Exception as exception:
            actual_result = exception
        actual_results.append(actual_result)
    assert len(actual_results) == len(expected_results)
    for actual_result in actual_results:
        if isinstance(actual_result, Exception):
            assert Exception in expected_results
        else:
            assert actual_result in expected_results
