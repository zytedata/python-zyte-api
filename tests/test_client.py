import pytest
from unittest import mock

from zyte_api.aio.client import AsyncClient
from zyte_api.aio.errors import RequestError
from zyte_api.utils import USER_AGENT


@pytest.mark.parametrize(
    "user_agent,expected",
    (
        (
            None,
            USER_AGENT,
        ),
        (
            f'scrapy-zyte-api/0.11.1 {USER_AGENT}',
            f'scrapy-zyte-api/0.11.1 {USER_AGENT}',
        ),
    ),
)
def test_user_agent(user_agent, expected):
    client = AsyncClient(api_key='123', api_url='http:\\test', user_agent=user_agent)
    assert client.user_agent == expected


@pytest.mark.asyncio
@mock.patch("zyte_api.aio.client._post_func")
async def test_request_raw_error(mock_post):
    request_id = "abcd1234"
    content = b"some content"
    headers = {"request-id": request_id}
    status = 521
    reason = "Some failure somewhere"

    response = mock.AsyncMock()
    response.status = status
    response.read.return_value = content
    response.headers = headers
    response.reason = "reason"
    mock_post()().__aenter__.return_value = response
    client = AsyncClient(api_key='a')

    with pytest.raises(RequestError) as excinfo:
        await client.request_raw(query={})

    assert f"(request_id={request_id}) reason" in excinfo.value.message
    assert {"request-id": request_id} == excinfo.value.headers
    assert status == excinfo.value.status
    assert content == excinfo.value.response_content
    assert request_id == excinfo.value.request_id
