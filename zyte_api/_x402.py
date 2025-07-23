from __future__ import annotations

from os import environ
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from asyncio import Semaphore
    from collections.abc import Callable
    from contextlib import AbstractAsyncContextManager

    from aiohttp import ClientResponse
    from x402.clients import x402Client

ENV_VARIABLE = "ZYTE_API_ETH_KEY"


def _get_eth_key(key: str | None = None) -> str:
    if key is not None:
        return key
    try:
        return environ[ENV_VARIABLE]
    except KeyError:
        raise ValueError from None


async def _get_x402_headers(
    client: x402Client,
    url: str,
    query: dict[str, Any],
    headers: dict[str, str],
    semaphore: Semaphore,
    post_fn: Callable[..., AbstractAsyncContextManager[ClientResponse]],
) -> dict[str, str]:
    from x402.types import x402PaymentRequiredResponse

    post_kwargs = {"url": url, "json": query, "headers": headers}
    async with semaphore, post_fn(**post_kwargs) as response:
        if response.status != 402:
            raise ValueError(
                "Expected 402 status code for X-402 authorization, got "
                f"{response.status}"
            )
        data = await response.json()

    payment_response = x402PaymentRequiredResponse(**data)
    selected_requirements = client.select_payment_requirements(payment_response.accepts)
    payment_header = client.create_payment_header(
        selected_requirements, payment_response.x402_version
    )
    return {
        "Access-Control-Expose-Headers": "X-Payment-Response",
        "X-Payment": payment_header,
    }
