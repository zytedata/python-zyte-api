"""
Asyncio client for Zyte Data API
"""

import asyncio
import time
from functools import partial
from typing import Optional, Iterator, List

import aiohttp
from aiohttp import TCPConnector
from tenacity import AsyncRetrying

from .errors import RequestError
from .retry import zyte_api_retrying
from ..apikey import get_apikey
from ..constants import API_URL, API_TIMEOUT
from ..stats import AggStats, ResponseStats
from ..utils import user_agent


# 120 seconds is probably too long, but we are concerned about the case with
# many concurrent requests and some processing logic running in the same reactor,
# thus, saturating the CPU. This will make timeouts more likely.
AIO_API_TIMEOUT = aiohttp.ClientTimeout(total=API_TIMEOUT + 120)


def create_session(connection_pool_size=100, **kwargs) -> aiohttp.ClientSession:
    """ Create a session with parameters suited for Zyte API """
    kwargs.setdefault('timeout', AIO_API_TIMEOUT)
    if "connector" not in kwargs:
        kwargs["connector"] = TCPConnector(limit=connection_pool_size)
    return aiohttp.ClientSession(**kwargs)


def _post_func(session):
    """ Return a function to send a POST request """
    if session is None:
        return partial(aiohttp.request,
                       method='POST',
                       timeout=AIO_API_TIMEOUT)
    else:
        return session.post


class AsyncClient:
    def __init__(self, *,
                 api_key=None,
                 api_url=API_URL,
                 n_conn=15,
                 ):
        self.api_key = get_apikey(api_key)
        self.api_url = api_url
        self.n_conn = n_conn
        self.agg_stats = AggStats()

    async def request_raw(self, query: dict, *,
                          endpoint: str = 'extract',
                          session=None,
                          handle_retries=True,
                          retrying: Optional[AsyncRetrying] = None,
                          ):
        retrying = retrying or zyte_api_retrying
        post = _post_func(session)
        auth = aiohttp.BasicAuth(self.api_key)
        headers = {'User-Agent': user_agent(aiohttp)}

        response_stats = []
        start_global = time.perf_counter()

        async def request():
            stats = ResponseStats.create(start_global)
            self.agg_stats.n_attempts += 1

            post_kwargs = dict(
                url=self.api_url + endpoint,
                json=query,
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
                            response_content=content
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
            self.agg_stats.n_extracted_queries += 1
        except Exception:
            self.agg_stats.n_fatal_errors += 1
            raise
        finally:
            self.agg_stats.n_input_queries += 1

        self.agg_stats.n_results += 1
        return result

    def request_parallel_as_completed(self,
                                      queries: List[dict],
                                      *,
                                      endpoint: str = 'extract',
                                      session: Optional[aiohttp.ClientSession] = None,
                                      ) -> Iterator[asyncio.Future]:
        """ Send multiple requests to Zyte Data API in parallel.
        Return an `asyncio.as_completed` iterator.

        ``queries`` is a list of requests to process (dicts).

        ``session`` is an optional aiohttp.ClientSession object;
        use it to enable HTTP Keep-Alive. Set the session TCPConnector
        limit to a value greater than the number of connections.
        """
        sem = asyncio.Semaphore(self.n_conn)

        async def _request(query):
            async with sem:
                return await self.request_raw(query,
                    endpoint=endpoint,
                    session=session)

        return asyncio.as_completed([_request(query) for query in queries])
