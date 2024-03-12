import asyncio
from tenacity import AsyncRetrying
from typing import Generator, List, Optional, Union

from aiohttp import ClientSession

from .aio.client import AsyncClient
from .constants import API_URL


class ZyteAPI:
    """Synchronous Zyte API client.

    To create an instance, pass your API key:

    .. code-block:: python

        client = ZyteAPI(api_key="YOUR_API_KEY")

    Or :ref:`use an environment variable <api-key>` and omit your API key:

    .. code-block:: python

        client = ZyteAPI()

    Use :meth:`get` and :meth:`iter` to send queries to Zyte API.
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
        self._async_client = AsyncClient(
            api_key=api_key,
            api_url=api_url,
            n_conn=n_conn,
            retrying=retrying,
            user_agent=user_agent,
        )

    def get(
        self,
        query: dict,
        *,
        endpoint: str = 'extract',
        session: Optional[ClientSession] = None,
        handle_retries: bool = True,
        retrying: Optional[AsyncRetrying] = None,
    ) -> dict:
        """Send a query to Zyte API and get the result.

        .. code-block:: python

            result = client.get({"url": "https://toscrape.com", "httpResponseBody": True})
        """
        return asyncio.run(
            self._async_client.request_raw(
                query=query,
                endpoint=endpoint,
                session=session,
                handle_retries=handle_retries,
                retrying=retrying,
            )
        )


    def iter(
        self,
        queries: List[dict],
        *,
        endpoint: str = 'extract',
        session: Optional[ClientSession] = None,
        handle_retries: bool = True,
        retrying: Optional[AsyncRetrying] = None,
    ) -> Generator[dict, None, None]:
        """Send multiple queries to Zyte API in parallel and iterate over their
        results as they come.

        .. code-block:: python

            queries = [
                {"url": "https://books.toscrape.com", "httpResponseBody": True},
                {"url": "https://quotes.toscrape.com", "httpResponseBody": True},
            ]
            for result in client.iter(queries):
                print(result)

        Results may come an a different order from the original list of
        *queries*. You can use echoData_ to attach metadata to queries that you
        can later use to restore their original order.

        .. _echoData: https://docs.zyte.com/zyte-api/usage/reference.html#operation/extract/request/echoData
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        for future in self._async_client.request_parallel_as_completed(
            queries=queries,
            endpoint=endpoint,
            session=session,
            handle_retries=handle_retries,
            retrying=retrying,
        ):
            yield loop.run_until_complete(future)
