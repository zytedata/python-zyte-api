import contextlib
import importlib.util
from os import environ
from unittest import mock

import pytest

from zyte_api import AsyncZyteAPI
from zyte_api._errors import RequestError

from .mockserver import SCREENSHOT

BODY = "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg=="
HAS_X402 = importlib.util.find_spec("x402") is not None
HTML = "<html><body>Hello<h1>World!</h1></body></html>"
KEY = "c85ef7d79691fe79573b1a7064c5232332f53bb1b44a08f1a737f57a68a4706e"


def test_eth_key_param():
    if HAS_X402:
        client = AsyncZyteAPI(eth_key=KEY)
        assert client.auth.key == KEY
        assert client.auth.type == "eth"
        assert client.api_url == "https://api-x402.zyte.com/v1/"
    else:
        with pytest.raises(ImportError, match="No module named 'eth_account'"):
            AsyncZyteAPI(eth_key=KEY)


@mock.patch.dict(environ, {"ZYTE_API_ETH_KEY": KEY})
def test_eth_key_env_var():
    if HAS_X402:
        AsyncZyteAPI()
    else:
        with pytest.raises(ImportError, match="No module named 'eth_account'"):
            AsyncZyteAPI()


def test_eth_key_short():
    if HAS_X402:
        with pytest.raises(ValueError, match="must be exactly 32 bytes long"):
            AsyncZyteAPI(eth_key="a")
    else:
        with pytest.raises(ImportError, match="No module named 'eth_account'"):
            AsyncZyteAPI(eth_key="a")


@contextlib.contextmanager
def reset_x402_cache():
    from zyte_api import _x402

    try:
        yield _x402.CACHE
    finally:
        _x402.CACHE = {}


@pytest.mark.skipif(not HAS_X402, reason="x402 not installed")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    (
        # Identical
        {
            "i1": {"url": "https://a.example", "httpResponseBody": True},
            "o1": {"url": "https://a.example", "httpResponseBody": BODY},
            "i2": {"url": "https://a.example", "httpResponseBody": True},
            "o2": {"url": "https://a.example", "httpResponseBody": BODY},
            "cache": "hit",
        },
        # Extra headers
        {
            "i1": {"url": "https://a.example", "httpResponseBody": True},
            "o1": {"url": "https://a.example", "httpResponseBody": BODY},
            "i2": {
                "url": "https://a.example",
                "httpResponseBody": True,
                "customHttpRequestHeaders": [{"name": "foo", "value": "bar"}],
            },
            "o2": {"url": "https://a.example", "httpResponseBody": BODY},
            "cache": "hit",
        },
        # Different domain
        {
            "i1": {"url": "https://a.example", "httpResponseBody": True},
            "o1": {"url": "https://a.example", "httpResponseBody": BODY},
            "i2": {"url": "https://b.example", "httpResponseBody": True},
            "o2": {"url": "https://b.example", "httpResponseBody": BODY},
            "cache": "miss",
        },
        # Different request type (HTTP vs browser)
        {
            "i1": {"url": "https://a.example", "httpResponseBody": True},
            "o1": {"url": "https://a.example", "httpResponseBody": BODY},
            "i2": {"url": "https://a.example", "browserHtml": True},
            "o2": {"url": "https://a.example", "browserHtml": HTML},
            "cache": "miss",
        },
        # Screenshot
        {
            "i1": {"url": "https://a.example", "browserHtml": True},
            "o1": {"url": "https://a.example", "browserHtml": HTML},
            "i2": {"url": "https://a.example", "screenshot": True},
            "o2": {"url": "https://a.example", "screenshot": SCREENSHOT},
            "cache": "miss",
        },
        # Actions: Empty actions count as no actions
        {
            "i1": {"url": "https://a.example", "browserHtml": True},
            "o1": {"url": "https://a.example", "browserHtml": HTML},
            "i2": {"url": "https://a.example", "browserHtml": True, "actions": []},
            "o2": {"url": "https://a.example", "browserHtml": HTML},
            "cache": "hit",
        },
        # Actions: Actions vs no actions
        {
            "i1": {"url": "https://a.example", "browserHtml": True},
            "o1": {"url": "https://a.example", "browserHtml": HTML},
            "i2": {
                "url": "https://a.example",
                "browserHtml": True,
                "actions": [{"action": "click", "selector": "button#submit"}],
            },
            "o2": {"url": "https://a.example", "browserHtml": HTML},
            "cache": "miss",
        },
        # Actions: Different action count does not prevent cache hit
        {
            "i1": {
                "url": "https://a.example",
                "browserHtml": True,
                "actions": [{"action": "click", "selector": "button#submit"}],
            },
            "o1": {"url": "https://a.example", "browserHtml": HTML},
            "i2": {
                "url": "https://a.example",
                "browserHtml": True,
                "actions": [
                    {"action": "click", "selector": "button#submit"},
                    {"action": "scrollBottom"},
                ],
            },
            "o2": {"url": "https://a.example", "browserHtml": HTML},
            "cache": "hit",
        },
        # Network capture: Empty network capture count as no network capture
        {
            "i1": {"url": "https://a.example", "browserHtml": True},
            "o1": {"url": "https://a.example", "browserHtml": HTML},
            "i2": {
                "url": "https://a.example",
                "browserHtml": True,
                "networkCapture": [],
            },
            "o2": {"url": "https://a.example", "browserHtml": HTML},
            "cache": "hit",
        },
        # Network capture: Network capture vs no network capture
        {
            "i1": {"url": "https://a.example", "browserHtml": True},
            "o1": {"url": "https://a.example", "browserHtml": HTML},
            "i2": {
                "url": "https://a.example",
                "browserHtml": True,
                "networkCapture": [
                    {
                        "filterType": "url",
                        "httpResponseBody": True,
                        "value": "/api/",
                        "matchType": "contains",
                    }
                ],
            },
            "o2": {"url": "https://a.example", "browserHtml": HTML},
            "cache": "miss",
        },
        # Network capture: Different network capture count does not prevent
        # cache hit
        {
            "i1": {
                "url": "https://a.example",
                "browserHtml": True,
                "networkCapture": [
                    {
                        "filterType": "url",
                        "httpResponseBody": True,
                        "value": "/api/",
                        "matchType": "contains",
                    }
                ],
            },
            "o1": {"url": "https://a.example", "browserHtml": HTML},
            "i2": {
                "url": "https://a.example",
                "browserHtml": True,
                "networkCapture": [
                    {
                        "filterType": "url",
                        "httpResponseBody": True,
                        "value": "/api/",
                        "matchType": "contains",
                    },
                    {
                        "filterType": "url",
                        "httpResponseBody": True,
                        "value": "/other/",
                        "matchType": "contains",
                    },
                ],
            },
            "o2": {"url": "https://a.example", "browserHtml": HTML},
            "cache": "hit",
        },
        # Extraction: serp does not affect cost
        {
            "i1": {"url": "https://a.example", "httpResponseBody": True},
            "o1": {"url": "https://a.example", "httpResponseBody": BODY},
            "i2": {"url": "https://a.example", "serp": True},
            "o2": {"url": "https://a.example"},
            "cache": "hit",
        },
        # Extraction: all other extraction types do affect cost
        {
            "i1": {"url": "https://a.example", "httpResponseBody": True},
            "o1": {"url": "https://a.example", "httpResponseBody": BODY},
            "i2": {"url": "https://a.example", "product": True},
            "o2": {"url": "https://a.example"},
            "cache": "miss",
        },
        # Extraction: customAttributes, same method
        {
            "i1": {
                "url": "https://a.example",
                "customAttributes": {
                    "summary": {
                        "type": "string",
                        "description": "A two sentence article summary",
                    },
                },
            },
            "o1": {"url": "https://a.example"},
            "i2": {
                "url": "https://a.example",
                "customAttributes": {
                    "summary": {
                        "type": "string",
                        "description": "A two sentence article summary",
                    },
                },
                "customAttributesOptions": {
                    "method": "generate",
                },
            },
            "o2": {"url": "https://a.example"},
            "cache": "hit",
        },
        # Extraction: customAttributes, same method
        {
            "i1": {
                "url": "https://a.example",
                "customAttributes": {
                    "summary": {
                        "type": "string",
                        "description": "A two sentence article summary",
                    },
                },
            },
            "o1": {"url": "https://a.example"},
            "i2": {
                "url": "https://a.example",
                "customAttributes": {
                    "summary": {
                        "type": "string",
                        "description": "A two sentence article summary",
                    },
                },
                "customAttributesOptions": {
                    "method": "extract",
                },
            },
            "o2": {"url": "https://a.example"},
            "cache": "miss",
        },
        # Extraction: the number of custom attributes does not affect cost
        {
            "i1": {
                "url": "https://a.example",
                "customAttributes": {
                    "summary": {
                        "type": "string",
                        "description": "A two sentence article summary",
                    },
                },
            },
            "o1": {"url": "https://a.example"},
            "i2": {
                "url": "https://a.example",
                "customAttributes": {
                    "summary": {
                        "type": "string",
                        "description": "A two sentence article summary",
                    },
                    "article_sentiment": {
                        "type": "string",
                        "enum": ["positive", "negative", "neutral"],
                    },
                },
            },
            "o2": {"url": "https://a.example"},
            "cache": "hit",
        },
        # Extraction: extractFrom is assumed to be browser by default
        {
            "i1": {
                "url": "https://a.example",
                "product": True,
            },
            "o1": {"url": "https://a.example"},
            "i2": {
                "url": "https://a.example",
                "product": True,
                "productOptions": {
                    "extractFrom": "browserHtml",
                },
            },
            "o2": {"url": "https://a.example"},
            "cache": "hit",
        },
        # Extraction: extractFrom affects cost
        {
            "i1": {
                "url": "https://a.example",
                "product": True,
                "productOptions": {
                    "extractFrom": "httpResponseBody",
                },
            },
            "o1": {"url": "https://a.example"},
            "i2": {
                "url": "https://a.example",
                "product": True,
                "productOptions": {
                    "extractFrom": "browserHtml",
                },
            },
            "o2": {"url": "https://a.example"},
            "cache": "miss",
        },
    ),
)
async def test_cache(scenario, mockserver):
    """Requests that are expected to have the same cost (or cost modifiers) as
    a preceding request should hit the cache.

    https://docs.zyte.com/zyte-api/pricing.html#request-costs
    """
    client = AsyncZyteAPI(eth_key=KEY, api_url=mockserver.urljoin("/"))
    with reset_x402_cache() as cache:
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 0

        # Request 1
        actual_result = await client.get(scenario["i1"])
        assert actual_result == scenario["o1"]
        assert len(cache) == 1
        assert client.agg_stats.n_402_req == 1

        # Request 2
        actual_result = await client.get(scenario["i2"])
        assert actual_result == scenario["o2"]
        assert len(cache) == 2 if scenario["cache"] == "miss" else 1
        assert client.agg_stats.n_402_req == len(cache)


@pytest.mark.skipif(not HAS_X402, reason="x402 not installed")
@pytest.mark.asyncio
@mock.patch("zyte_api._x402.MINIMIZE_REQUESTS", False)
async def test_no_cache(mockserver):
    client = AsyncZyteAPI(eth_key=KEY, api_url=mockserver.urljoin("/"))
    input = {"url": "https://a.example", "httpResponseBody": True}
    output = {
        "url": "https://a.example",
        "httpResponseBody": BODY,
    }

    with reset_x402_cache() as cache:
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 0

        # Initial request
        actual_result = await client.get(input)
        assert actual_result == output
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 1

        # Identical request
        actual_result = await client.get(input)
        assert actual_result == output
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 2

        # Request refresh
        input = {
            "url": "https://a.example",
            "httpResponseBody": True,
            "echoData": "402-payment-retry-2",
        }
        actual_result = await client.get(input)
        assert actual_result == output
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 3


@pytest.mark.skipif(not HAS_X402, reason="x402 not installed")
@pytest.mark.asyncio
async def test_4xx(mockserver):
    """An unexpected status code lower than 500 raises RequestError
    immediately."""
    client = AsyncZyteAPI(eth_key=KEY, api_url=mockserver.urljoin("/"))
    input = {"url": "https://e404.example", "httpResponseBody": True}

    with reset_x402_cache() as cache:
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 0
        with pytest.raises(RequestError):
            await client.get(input)
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 1


@pytest.mark.skipif(not HAS_X402, reason="x402 not installed")
@pytest.mark.asyncio
async def test_5xx(mockserver):
    """An unexpected status code ≥ 500 gets retried once."""
    client = AsyncZyteAPI(eth_key=KEY, api_url=mockserver.urljoin("/"))
    input = {"url": "https://e500.example", "httpResponseBody": True}

    with reset_x402_cache() as cache:
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 0
        with pytest.raises(RequestError):
            await client.get(input)
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 2


@pytest.mark.skipif(not HAS_X402, reason="x402 not installed")
@pytest.mark.asyncio
async def test_payment_retry(mockserver):
    client = AsyncZyteAPI(eth_key=KEY, api_url=mockserver.urljoin("/"))
    input = {
        "url": "https://a.example",
        "httpResponseBody": True,
        "echoData": "402-payment-retry",
    }

    with reset_x402_cache() as cache:
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 0
        data = await client.get(input)
        assert len(cache) == 1

    assert data == {"httpResponseBody": BODY, "url": "https://a.example"}
    assert client.agg_stats.n_success == 1
    assert client.agg_stats.n_fatal_errors == 0
    assert client.agg_stats.n_attempts == 2
    assert client.agg_stats.n_errors == 1
    assert client.agg_stats.n_402_req == 1
    assert client.agg_stats.status_codes == {402: 1, 200: 1}
    assert client.agg_stats.exception_types == {}
    assert client.agg_stats.api_error_types == {"/x402/use-basic-auth-or-x402": 1}


@pytest.mark.skipif(not HAS_X402, reason="x402 not installed")
@pytest.mark.asyncio
async def test_payment_retry_exceeded(mockserver):
    client = AsyncZyteAPI(eth_key=KEY, api_url=mockserver.urljoin("/"))
    input = {
        "url": "https://a.example",
        "httpResponseBody": True,
        "echoData": "402-payment-retry-exceeded",
    }

    with reset_x402_cache() as cache:
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 0
        with pytest.raises(RequestError):
            await client.get(input)
        assert len(cache) == 1

    assert client.agg_stats.n_success == 0
    assert client.agg_stats.n_fatal_errors == 1
    assert client.agg_stats.n_attempts == 2
    assert client.agg_stats.n_errors == 2
    assert client.agg_stats.n_402_req == 1
    assert client.agg_stats.status_codes == {402: 2}
    assert client.agg_stats.exception_types == {}
    assert client.agg_stats.api_error_types == {"/x402/use-basic-auth-or-x402": 2}


@pytest.mark.asyncio
async def test_no_payment_retry(mockserver):
    """An HTTP 402 response received out of the context of the x402 protocol,
    as a response to a regular request using basic auth."""
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    input = {
        "url": "https://a.example",
        "httpResponseBody": True,
        "echoData": "402-no-payment-retry",
    }

    with reset_x402_cache() as cache:
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 0
        data = await client.get(input)
        assert len(cache) == 0

    assert data == {"httpResponseBody": BODY, "url": "https://a.example"}
    assert client.agg_stats.n_success == 1
    assert client.agg_stats.n_fatal_errors == 0
    assert client.agg_stats.n_attempts == 2
    assert client.agg_stats.n_errors == 1
    assert client.agg_stats.n_402_req == 0
    assert client.agg_stats.status_codes == {402: 1, 200: 1}
    assert client.agg_stats.exception_types == {}
    assert client.agg_stats.api_error_types == {"/x402/use-basic-auth-or-x402": 1}


@pytest.mark.asyncio
async def test_no_payment_retry_exceeded(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    input = {
        "url": "https://a.example",
        "httpResponseBody": True,
        "echoData": "402-no-payment-retry-exceeded",
    }

    with reset_x402_cache() as cache:
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 0
        with pytest.raises(RequestError):
            await client.get(input)
        assert len(cache) == 0

    assert client.agg_stats.n_success == 0
    assert client.agg_stats.n_fatal_errors == 1
    assert client.agg_stats.n_attempts == 2
    assert client.agg_stats.n_errors == 2
    assert client.agg_stats.n_402_req == 0
    assert client.agg_stats.status_codes == {402: 2}
    assert client.agg_stats.exception_types == {}
    assert client.agg_stats.api_error_types == {"/x402/use-basic-auth-or-x402": 2}


@pytest.mark.asyncio
async def test_long_error(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    input = {
        "url": "https://a.example",
        "httpResponseBody": True,
        "echoData": "402-long-error",
    }

    with reset_x402_cache() as cache:
        assert len(cache) == 0
        assert client.agg_stats.n_402_req == 0
        with pytest.raises(RequestError):
            await client.get(input)
        assert len(cache) == 0

    assert client.agg_stats.n_success == 0
    assert client.agg_stats.n_fatal_errors == 1
    assert client.agg_stats.n_attempts == 2
    assert client.agg_stats.n_errors == 2
    assert client.agg_stats.n_402_req == 0
    assert client.agg_stats.status_codes == {402: 2}
    assert client.agg_stats.exception_types == {}
    assert client.agg_stats.api_error_types == {None: 2}
