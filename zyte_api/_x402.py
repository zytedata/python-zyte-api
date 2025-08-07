from __future__ import annotations

import json
from hashlib import md5
from os import environ
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from tenacity import stop_after_attempt

from zyte_api._errors import RequestError
from zyte_api._retry import RetryFactory

if TYPE_CHECKING:
    from asyncio import Semaphore
    from collections.abc import Callable
    from contextlib import AbstractAsyncContextManager

    from aiohttp import ClientResponse

    from zyte_api.stats import AggStats

CACHE: dict[bytes, tuple[Any, str]] = {}
EXTRACT_KEYS = {
    "article",
    "articleList",
    "articleNavigation",
    "forumThread",
    "jobPosting",
    "jobPostingNavigation",
    "product",
    "productList",
    "productNavigation",
    "serp",
}
MINIMIZE_REQUESTS = environ.get("ZYTE_API_ETH_MINIMIZE_REQUESTS") != "false"


def get_extract_from(query: dict[str, Any], data_type: str) -> str | Any:
    options = query.get(f"{data_type}Options", {})
    default_extract_from = "httpResponseBody" if data_type == "serp" else None
    return options.get("extractFrom", default_extract_from)


def get_extract_froms(query: dict[str, Any]) -> set[str]:
    result = set()
    for key in EXTRACT_KEYS:
        if not query.get(key, False):
            continue
        result.add(get_extract_from(query, key))
    return result


def may_use_browser(query: dict[str, Any]) -> bool:
    """Return ``False`` if *query* indicates with certainty that browser
    rendering will not be used, or ``True`` otherwise."""
    for key in ("browserHtml", "screenshot"):
        if query.get(key):
            return True
    extract_froms = get_extract_froms(query)
    if "browserHtml" in extract_froms:
        return True
    if "httpResponseBody" in extract_froms:
        return False
    return not query.get("httpResponseBody")


def get_max_cost_hash(query: dict[str, Any]) -> bytes:
    """Returns a hash based on *query* that should be the same for queries
    whose estimate costs are the same.

    For open-ended costs, like actions, network capture or custom attributes,
    we assume that Zyte API will not report a different cost based on e.g. the
    number of actions or their parameters, or similar details of network
    capture or custom attributes.

    See also: https://docs.zyte.com/zyte-api/pricing.html#request-costs
    """
    data = {
        "domain": urlparse(query["url"]).netloc,
        "type": "browser" if may_use_browser(query) else "http",
    }
    for key in (
        *(k for k in EXTRACT_KEYS if k != "serp"),  # serp does not affect cost
        "actions",
        "networkCapture",
        "screenshot",
    ):
        if query.get(key):
            data[key] = True
    if query.get("customAttributes"):
        data["customAttributesOptions.method"] = query.get(
            "customAttributesOptions", {}
        ).get("method", "generate")
    return md5(json.dumps(data, sort_keys=True).encode()).digest()  # noqa: S324


class X402RetryFactory(RetryFactory):
    # Disable ban response retries.
    download_error_stop = stop_after_attempt(1)  # type: ignore[assignment]


X402_RETRYING = X402RetryFactory().build()


class _x402Handler:
    def __init__(
        self,
        eth_key: str,
        semaphore: Semaphore,
        stats: AggStats,
    ):
        from eth_account import Account
        from x402.clients import x402Client
        from x402.types import x402PaymentRequiredResponse

        account = Account.from_key(eth_key)
        self.client = x402Client(account=account)
        self.semaphore = semaphore
        self.stats = stats
        self.x402PaymentRequiredResponse = x402PaymentRequiredResponse

    async def get_headers(
        self,
        url: str,
        query: dict[str, Any],
        headers: dict[str, str],
        post_fn: Callable[..., AbstractAsyncContextManager[ClientResponse]],
    ) -> dict[str, str]:
        requirement_data = await self.get_requirement_data(url, query, headers, post_fn)
        return self.get_headers_from_requirement_data(requirement_data)

    def get_headers_from_requirement_data(
        self, requirement_data: tuple[Any, str]
    ) -> dict[str, str]:
        payment_header = self.client.create_payment_header(*requirement_data)
        return {
            "Access-Control-Expose-Headers": "X-Payment-Response",
            "X-Payment": payment_header,
        }

    async def get_requirement_data(
        self,
        url: str,
        query: dict[str, Any],
        headers: dict[str, str],
        post_fn: Callable[..., AbstractAsyncContextManager[ClientResponse]],
    ) -> tuple[Any, str]:
        if not MINIMIZE_REQUESTS:
            return await self.fetch_requirements(url, query, headers, post_fn)
        max_cost_hash = get_max_cost_hash(query)
        if max_cost_hash not in CACHE:
            CACHE[max_cost_hash] = await self.fetch_requirements(
                url, query, headers, post_fn
            )
        return CACHE[max_cost_hash]

    async def fetch_requirements(
        self,
        url: str,
        query: dict[str, Any],
        headers: dict[str, str],
        post_fn: Callable[..., AbstractAsyncContextManager[ClientResponse]],
    ) -> tuple[Any, str]:
        post_kwargs = {"url": url, "json": query, "headers": headers}

        async def request():
            self.stats.n_402_req += 1
            async with self.semaphore, post_fn(**post_kwargs) as response:
                if response.status == 402:
                    return await response.json()
                content = await response.read()
                response.release()
                raise RequestError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=response.reason,
                    headers=response.headers,
                    response_content=content,
                    query=query,
                )

        request = X402_RETRYING.wraps(request)
        data = await request()
        return self.parse_requirements(data)

    def parse_requirements(self, data: dict[str, Any]) -> tuple[Any, str]:
        payment_response = self.x402PaymentRequiredResponse(**data)
        requirements = self.client.select_payment_requirements(payment_response.accepts)
        version = payment_response.x402_version
        return requirements, version

    def refresh_post_kwargs(
        self,
        post_kwargs: dict[str, Any],
        response_data: dict[str, Any],
    ) -> None:
        requirement_data = self.parse_requirements(response_data)
        if MINIMIZE_REQUESTS:
            max_cost_hash = get_max_cost_hash(post_kwargs["json"])
            CACHE[max_cost_hash] = requirement_data
        headers = self.get_headers_from_requirement_data(requirement_data)
        post_kwargs["headers"] = {**post_kwargs["headers"], **headers}
