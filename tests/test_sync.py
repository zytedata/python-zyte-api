from types import GeneratorType

import pytest

from zyte_api import ZyteAPI
from zyte_api.apikey import NoApiKey


def test_api_key():
    ZyteAPI(api_key="a")
    with pytest.raises(NoApiKey):
        ZyteAPI()


def test_get(mockserver):
    client = ZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    expected_result = {
        "url": "https://a.example",
        "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
    }
    actual_result = client.get({"url": "https://a.example", "httpResponseBody": True})
    assert actual_result == expected_result


def test_iter(mockserver):
    client = ZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
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
    actual_results = client.iter(queries)
    assert isinstance(actual_results, GeneratorType)
    actual_results_list = list(actual_results)
    assert len(actual_results_list) == len(expected_results)
    for actual_result in actual_results_list:
        if isinstance(actual_result, Exception):
            assert Exception in expected_results
        else:
            assert actual_result in expected_results
