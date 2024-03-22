import asyncio
from typing import Generator, List, Optional, Union

from aiohttp import ClientSession
from tenacity import AsyncRetrying

from ._async import AsyncZyteAPI
from .constants import API_URL


def _get_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:  # pragma: no cover (tests always have a running loop)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


class _Session:
    def __init__(self, client, **session_kwargs):
        self._client = client
        self._session = client._async_client.session(**session_kwargs)
        self._context = None

    def __enter__(self):
        loop = _get_loop()
        self._context = loop.run_until_complete(self._session.__aenter__())._context
        return self

    def __exit__(self, *exc_info):
        loop = _get_loop()
        result = loop.run_until_complete(self._context.__aexit__(*exc_info))
        self._context = None
        return result

    def _check_context(self):
        if self._context is None:
            raise RuntimeError(
                "Attempt to use session method on a session either not opened "
                "or already closed."
            )

    def get(
        self,
        query: dict,
        *,
        endpoint: str = "extract",
        handle_retries=True,
        retrying: Optional[AsyncRetrying] = None,
    ):
        self._check_context()
        return self._client.get(
            query=query,
            endpoint=endpoint,
            handle_retries=handle_retries,
            retrying=retrying,
            session=self._context,
        )

    def iter(
        self,
        queries: List[dict],
        *,
        endpoint: str = "extract",
        handle_retries=True,
        retrying: Optional[AsyncRetrying] = None,
    ) -> Generator[Union[dict, Exception], None, None]:
        self._check_context()
        return self._client.iter(
            queries=queries,
            endpoint=endpoint,
            session=self._context,
            handle_retries=handle_retries,
            retrying=retrying,
        )


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
        self._async_client = AsyncZyteAPI(
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
        endpoint: str = "extract",
        session: Optional[ClientSession] = None,
        handle_retries: bool = True,
        retrying: Optional[AsyncRetrying] = None,
    ) -> dict:
        """Send a query to Zyte API and get the result.

        .. code-block:: python

            result = client.get({"url": "https://toscrape.com", "httpResponseBody": True})
        """
        loop = _get_loop()
        future = self._async_client.get(
            query=query,
            endpoint=endpoint,
            session=session,
            handle_retries=handle_retries,
            retrying=retrying,
        )
        return loop.run_until_complete(future)

    def iter(
        self,
        queries: List[dict],
        *,
        endpoint: str = "extract",
        session: Optional[ClientSession] = None,
        handle_retries: bool = True,
        retrying: Optional[AsyncRetrying] = None,
    ) -> Generator[Union[dict, Exception], None, None]:
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

        When exceptions occur, they are also yielded, not raised.
        """
        loop = _get_loop()
        for future in self._async_client.iter(
            queries=queries,
            endpoint=endpoint,
            session=session,
            handle_retries=handle_retries,
            retrying=retrying,
        ):
            try:
                yield loop.run_until_complete(future)
            except Exception as exception:
                yield exception

    def session(self, **kwargs):
        return _Session(client=self, **kwargs)
