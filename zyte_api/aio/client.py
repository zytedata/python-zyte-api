"""
Asyncio client for Zyte API
"""

import asyncio
import time
from typing import Iterator, List, Optional

import aiohttp
from tenacity import AsyncRetrying

from .._async import _post_func
from .._utils import create_session  # noqa: F401
from ..apikey import get_apikey
from ..constants import API_URL
from ..stats import AggStats, ResponseStats
from ..utils import USER_AGENT, _process_query
from .errors import RequestError
from .retry import zyte_api_retrying


class AsyncClient:
    def __init__(
        self,
        *,
        api_key=None,
        api_url=API_URL,
        n_conn=15,
        retrying: Optional[AsyncRetrying] = None,
        user_agent: Optional[str] = None,
    ):
        self.api_key = get_apikey(api_key)
        self.api_url = api_url
        self.n_conn = n_conn
        self.agg_stats = AggStats()
        self.retrying = retrying or zyte_api_retrying
        self.user_agent = user_agent or USER_AGENT

    async def request_raw(
        self,
        query: dict,
        *,
        endpoint: str = "extract",
        session=None,
        handle_retries=True,
        retrying: Optional[AsyncRetrying] = None,
    ):
        retrying = retrying or self.retrying
        post = _post_func(session)
        auth = aiohttp.BasicAuth(self.api_key)
        headers = {"User-Agent": self.user_agent, "Accept-Encoding": "br"}

        response_stats = []
        start_global = time.perf_counter()

        async def request():
            stats = ResponseStats.create(start_global)
            self.agg_stats.n_attempts += 1

            post_kwargs = dict(
                url=self.api_url + endpoint,
                json=_process_query(query),
                auth=auth,
                headers=headers,
            )

            try:
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

    def request_parallel_as_completed(
        self,
        queries: List[dict],
        *,
        endpoint: str = "extract",
        session: Optional[aiohttp.ClientSession] = None,
        handle_retries=True,
        retrying: Optional[AsyncRetrying] = None,
    ) -> Iterator[asyncio.Future]:
        """Send multiple requests to Zyte API in parallel.
        Return an `asyncio.as_completed` iterator.

        ``queries`` is a list of requests to process (dicts).

        ``session`` is an optional aiohttp.ClientSession object.
        Set the session TCPConnector limit to a value greater than
        the number of connections.
        """
        sem = asyncio.Semaphore(self.n_conn)

        async def _request(query):
            async with sem:
                return await self.request_raw(
                    query,
                    endpoint=endpoint,
                    session=session,
                    handle_retries=handle_retries,
                    retrying=retrying,
                )

        return asyncio.as_completed([_request(query) for query in queries])
