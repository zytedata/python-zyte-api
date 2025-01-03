from __future__ import annotations

import asyncio
import time
from asyncio import Future
from functools import partial
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional

import aiohttp
from tenacity import AsyncRetrying

from ._errors import RequestError
from ._retry import TooManyUndocumentedErrors, zyte_api_retrying
from ._utils import _AIO_API_TIMEOUT, create_session
from .apikey import get_apikey
from .constants import API_URL
from .stats import AggStats, ResponseStats
from .utils import USER_AGENT, _process_query

if TYPE_CHECKING:
    _ResponseFuture = Future[Dict[str, Any]]


def _post_func(session):
    """Return a function to send a POST request"""
    if session is None:
        return partial(aiohttp.request, method="POST", timeout=_AIO_API_TIMEOUT)
    else:
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
        retrying: Optional[AsyncRetrying] = None,
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
        queries: List[dict],
        *,
        endpoint: str = "extract",
        handle_retries=True,
        retrying: Optional[AsyncRetrying] = None,
    ) -> Iterator[Future]:
        return self._client.iter(
            queries=queries,
            endpoint=endpoint,
            session=self._session,
            handle_retries=handle_retries,
            retrying=retrying,
        )


class AsyncZyteAPI:
    """:ref:`Asynchronous Zyte API client <asyncio_api>`.

    Parameters work the same as for :class:`ZyteAPI`.
    """

    def __init__(
        self,
        *,
        api_key=None,
        api_url=API_URL,
        n_conn=15,
        retrying: Optional[AsyncRetrying] = None,
        user_agent: Optional[str] = None,
    ):
        if retrying is not None and not isinstance(retrying, AsyncRetrying):
            raise ValueError(
                "The retrying parameter, if defined, must be an instance of "
                "AsyncRetrying."
            )
        self.api_key = get_apikey(api_key)
        self.api_url = api_url
        self.n_conn = n_conn
        self.agg_stats = AggStats()
        self.retrying = retrying or zyte_api_retrying
        self.user_agent = user_agent or USER_AGENT
        self._semaphore = asyncio.Semaphore(n_conn)
        self._disabling_exception: TooManyUndocumentedErrors | None = None

    async def get(
        self,
        query: dict,
        *,
        endpoint: str = "extract",
        session=None,
        handle_retries=True,
        retrying: Optional[AsyncRetrying] = None,
    ) -> _ResponseFuture:
        """Asynchronous equivalent to :meth:`ZyteAPI.get`."""
        if self._disabling_exception is not None:
            raise self._disabling_exception

        retrying = retrying or self.retrying
        post = _post_func(session)
        auth = aiohttp.BasicAuth(self.api_key)
        headers = {"User-Agent": self.user_agent, "Accept-Encoding": "br"}

        response_stats = []
        start_global = time.perf_counter()

        async def request():
            stats = ResponseStats.create(start_global)
            self.agg_stats.n_attempts += 1

            safe_query = _process_query(query)
            post_kwargs = dict(
                url=self.api_url + endpoint,
                json=safe_query,
                auth=auth,
                headers=headers,
            )

            try:
                async with self._semaphore:
                    async with post(**post_kwargs) as resp:
                        stats.record_connected(resp.status, self.agg_stats)
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
                                query=safe_query,
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
        except Exception as exc:
            if isinstance(exc, TooManyUndocumentedErrors):
                self._disabling_exception = exc
            self.agg_stats.n_fatal_errors += 1
            raise

        return result

    def iter(
        self,
        queries: List[dict],
        *,
        endpoint: str = "extract",
        session: Optional[aiohttp.ClientSession] = None,
        handle_retries=True,
        retrying: Optional[AsyncRetrying] = None,
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
