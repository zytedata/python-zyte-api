"""
Asyncio client for Zyte API
"""

import asyncio
import time
from base64 import b64decode
from collections.abc import Mapping
from functools import partial
from typing import Awaitable, Iterator, List, Optional, Union

import aiohttp
from aiohttp import TCPConnector
from tenacity import AsyncRetrying

from .errors import RequestError
from .retry import zyte_api_retrying
from ..apikey import get_apikey
from ..constants import API_URL, API_TIMEOUT
from ..stats import AggStats, ResponseStats
from ..utils import _to_lower_camel_case, user_agent


class _NotLoaded:
    pass


_NOT_LOADED = _NotLoaded()

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


class ExtractResult(Mapping):
    """Result of a call to AsyncClient.extract.

    It can be used as a dictionary to access the raw API response.

    It also provides some helper properties for easier access to some of its
    underlying data.
    """

    def __init__(self, api_response: dict):
        self._api_response = api_response
        self._http_response_body: Union[bytes|_NotLoaded] = _NOT_LOADED

    def __getitem__(self, key):
        return self._api_response[key]

    def __iter__(self):
        yield from self._api_response

    def __len__(self):
        return len(self._api_response)

    @property
    def http_response_body(self) -> Union[bytes|_NotLoaded]:
        if self._http_response_body is _NOT_LOADED:
            base64_body = self._api_response.get("httpResponseBody", None)
            if base64_body is None:
                raise ValueError("API response has no httpResponseBody key.")
            self._http_response_body = b64decode(base64_body)
        return self._http_response_body


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
        headers = {'User-Agent': user_agent(aiohttp), 'Accept-Encoding': 'br'}

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
            self.agg_stats.n_success += 1
        except Exception:
            self.agg_stats.n_fatal_errors += 1
            raise

        return result

    def request_parallel_as_completed(self,
                                      queries: List[dict],
                                      *,
                                      endpoint: str = 'extract',
                                      session: Optional[aiohttp.ClientSession] = None,
                                      ) -> Iterator[asyncio.Future]:
        """ Send multiple requests to Zyte API in parallel.
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

    @staticmethod
    def _build_extract_query(raw_query):
        return {
            _to_lower_camel_case(k): v
            for k, v in raw_query.items()
        }

    async def extract(
        self,
        url: str,
        *,
        session: Optional[aiohttp.ClientSession] = None,
        handle_retries: bool = True,
        retrying: Optional[AsyncRetrying] = None,
        **kwargs,
    ) -> ExtractResult:
        """…"""
        query = self._build_extract_query({**kwargs, 'url': url})
        response = await self.request_raw(
            query=query,
            endpoint='extract',
            session=session,
            handle_retries=handle_retries,
            retrying=retrying,
        )
        return ExtractResult(response)

    def extract_in_parallel(
        self,
        queries: List[dict],
        *,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Iterator[asyncio.Future]:
        """…"""
        queries = [self._build_extract_query(query) for query in queries]
        return self.request_parallel_as_completed(
            queries,
            endpoint='extract',
            session=session,
        )
