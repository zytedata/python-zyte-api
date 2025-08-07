from __future__ import annotations

import asyncio
import time
from asyncio import Future
from functools import partial
from os import environ
from typing import TYPE_CHECKING, Any
from warnings import warn

import aiohttp
from tenacity import AsyncRetrying

from zyte_api._x402 import _x402Handler
from zyte_api.apikey import NoApiKey

from ._errors import RequestError
from ._retry import zyte_api_retrying
from ._utils import _AIO_API_TIMEOUT, create_session
from .constants import API_URL
from .constants import ENV_VARIABLE as API_KEY_ENV_VAR
from .stats import AggStats, ResponseStats
from .utils import USER_AGENT, _process_query

if TYPE_CHECKING:
    from collections.abc import Iterator

    _ResponseFuture = Future[dict[str, Any]]


def _post_func(session):
    """Return a function to send a POST request"""
    if session is None:
        return partial(aiohttp.request, method="POST", timeout=_AIO_API_TIMEOUT)
    return session.post


class _AsyncSession:
    def __init__(self, client, **session_kwargs):
        self._client = client
        self._session = create_session(client.n_conn, **session_kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        await self._session.close()

    async def close(self):
        await self._session.close()

    async def get(
        self,
        query: dict,
        *,
        endpoint: str = "extract",
        handle_retries=True,
        retrying: AsyncRetrying | None = None,
    ):
        return await self._client.get(
            query=query,
            endpoint=endpoint,
            handle_retries=handle_retries,
            retrying=retrying,
            session=self._session,
        )

    def iter(
        self,
        queries: list[dict],
        *,
        endpoint: str = "extract",
        handle_retries=True,
        retrying: AsyncRetrying | None = None,
    ) -> Iterator[Future]:
        return self._client.iter(
            queries=queries,
            endpoint=endpoint,
            session=self._session,
            handle_retries=handle_retries,
            retrying=retrying,
        )


class AuthInfo:
    def __init__(self, *, _auth):
        self._auth = _auth

    @property
    def key(self) -> str:
        if isinstance(self._auth, str):
            return self._auth
        assert isinstance(self._auth, _x402Handler)
        return self._auth.client.account.key.hex()

    @property
    def type(self) -> str:
        if isinstance(self._auth, str):
            return "zyte"
        assert isinstance(self._auth, _x402Handler)
        return "eth"


class AsyncZyteAPI:
    """:ref:`Asynchronous Zyte API client <asyncio_api>`.

    Parameters work the same as for :class:`ZyteAPI`.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_url: str | None = None,
        n_conn: int = 15,
        retrying: AsyncRetrying | None = None,
        user_agent: str | None = None,
        eth_key: str | None = None,
    ):
        if retrying is not None and not isinstance(retrying, AsyncRetrying):
            raise ValueError(
                "The retrying parameter, if defined, must be an instance of "
                "AsyncRetrying."
            )

        self.n_conn = n_conn
        self.agg_stats = AggStats()
        self.retrying = retrying or zyte_api_retrying
        self.user_agent = user_agent or USER_AGENT
        self._semaphore = asyncio.Semaphore(n_conn)
        self._auth: str | _x402Handler
        self.auth: AuthInfo
        self.api_url: str
        self._load_auth(api_key, eth_key, api_url)

    def _load_auth(self, api_key: str | None, eth_key: str | None, api_url: str | None):
        if api_key:
            self._auth = api_key
        elif eth_key:
            self._auth = _x402Handler(eth_key, self._semaphore, self.agg_stats)
        elif api_key := environ.get(API_KEY_ENV_VAR):
            self._auth = api_key
        elif eth_key := environ.get("ZYTE_API_ETH_KEY"):
            self._auth = _x402Handler(eth_key, self._semaphore, self.agg_stats)
        else:
            raise NoApiKey(
                "You must provide either a Zyte API key or an Ethereum "
                "private key. For the latter, you must also install "
                "zyte-api as zyte-api[x402]."
            )
        self.auth = AuthInfo(_auth=self._auth)
        self.api_url = (
            api_url
            if api_url is not None
            else "https://api-x402.zyte.com/v1/"
            if self.auth.type == "eth"
            else API_URL
        )

    @property
    def api_key(self) -> str:
        if isinstance(self._auth, str):
            warn(
                "The api_key property is deprecated, use auth.key instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return self._auth
        raise NotImplementedError(
            "api_key is not available when using an Ethereum private key, use auth.key instead."
        )

    async def get(
        self,
        query: dict,
        *,
        endpoint: str = "extract",
        session=None,
        handle_retries=True,
        retrying: AsyncRetrying | None = None,
    ) -> _ResponseFuture:
        """Asynchronous equivalent to :meth:`ZyteAPI.get`."""
        retrying = retrying or self.retrying
        post = _post_func(session)

        url = self.api_url + endpoint
        query = _process_query(query)
        headers = {"User-Agent": self.user_agent, "Accept-Encoding": "br"}

        auth_kwargs = {}
        if isinstance(self._auth, str):
            auth_kwargs["auth"] = aiohttp.BasicAuth(self._auth)
        else:
            x402_headers = await self._auth.get_headers(url, query, headers, post)
            headers.update(x402_headers)

        post_kwargs = {
            "url": url,
            "json": query,
            "headers": headers,
            **auth_kwargs,
        }

        response_stats = []
        start_global = time.perf_counter()

        async def request():
            stats = ResponseStats.create(start_global)
            self.agg_stats.n_attempts += 1

            try:
                async with self._semaphore, post(**post_kwargs) as resp:
                    stats.record_connected(resp.status, self.agg_stats)
                    if (
                        resp.status == 402
                        and isinstance(self._auth, _x402Handler)
                        and "X-Payment" in post_kwargs["headers"]
                    ):
                        self._auth.refresh_post_kwargs(post_kwargs, await resp.json())
                    if resp.status >= 400:
                        content = await resp.read()
                        resp.release()
                        stats.record_read()
                        stats.record_request_error(content, self.agg_stats)

                        raise RequestError(
                            request_info=resp.request_info,
                            history=resp.history,
                            status=resp.status,
                            message=resp.reason,
                            headers=resp.headers,
                            response_content=content,
                            query=query,
                        )

                    response = await resp.json()
                    stats.record_read(self.agg_stats)
                    return response
            except Exception as e:
                if not isinstance(e, RequestError):
                    self.agg_stats.n_errors += 1
                    stats.record_exception(e, agg_stats=self.agg_stats)
                raise
            finally:
                response_stats.append(stats)

        if handle_retries:
            request = retrying.wraps(request)

        try:
            # Try to make a request
            result = await request()
            self.agg_stats.n_success += 1
        except Exception:
            self.agg_stats.n_fatal_errors += 1
            raise

        return result

    def iter(
        self,
        queries: list[dict],
        *,
        endpoint: str = "extract",
        session: aiohttp.ClientSession | None = None,
        handle_retries=True,
        retrying: AsyncRetrying | None = None,
    ) -> Iterator[_ResponseFuture]:
        """Asynchronous equivalent to :meth:`ZyteAPI.iter`.

        .. note:: Yielded futures, when awaited, do raise their exceptions,
                  instead of only returning them.
        """

        def _request(query):
            return self.get(
                query,
                endpoint=endpoint,
                session=session,
                handle_retries=handle_retries,
                retrying=retrying,
            )

        return asyncio.as_completed([_request(query) for query in queries])

    def session(self, **kwargs):
        """Asynchronous equivalent to :meth:`ZyteAPI.session`.

        You do not need to use :meth:`~AsyncZyteAPI.session` as an async
        context manager as long as you await ``close()`` on the object it
        returns when you are done:

        .. code-block:: python

            session = client.session()
            try:
                ...
            finally:
                await session.close()
        """
        return _AsyncSession(client=self, **kwargs)
