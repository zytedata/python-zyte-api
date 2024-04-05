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
    """:ref:`Synchronous Zyte API client <sync>`.

    *api_key* is your Zyte API key. If not specified, it is read from the
    ``ZYTE_API_KEY`` environment variable. See :ref:`api-key`.

    *api_url* is the Zyte API base URL.

    *n_conn* is the maximum number of concurrent requests to use. See
    :ref:`api-optimize`.

    *retrying* is the retry policy for requests. Defaults to
    :data:`~zyte_api.zyte_api_retrying`.

    *user_agent* is the user agent string reported to Zyte API. Defaults to
    ``python-zyte-api/<VERSION>``.

    .. tip:: To change the ``User-Agent`` header sent to a target website, use
             :http:`request:customHttpRequestHeaders` instead.
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
        """Send *query* to Zyte API and return the result.

        *endpoint* is the Zyte API endpoint path relative to the client object
        *api_url*.

        *session* is the network session to use. Consider using
        :meth:`session` instead of this parameter.

        *handle_retries* determines whether or not a :ref:`retry policy
        <retry-policy>` should be used.

        *retrying* is the :ref:`retry policy <retry-policy>` to use, provided
        *handle_retries* is ``True``. If not specified, the :ref:`default retry
        policy <default-retry-policy>` is used.
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
        """Send multiple *queries* to Zyte API in parallel and iterate over
        their results as they come.

        The number of *queries* can exceed the *n_conn* parameter set on the
        client object. Extra queries will be queued, there will be only up to
        *n_conn* requests being processed in parallel at a time.

        Results may come an a different order from the original list of
        *queries*. You can use :http:`request:echoData` to attach metadata to
        queries, and later use that metadata to restore their original order.

        When exceptions occur, they are yielded, not raised.

        The remaining parameters work the same as in :meth:`get`.
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
        """:ref:`Context manager <context-managers>` to create a contextual
        session.

        A contextual session is an object that has the same API as the client
        object, except:

        -   :meth:`get` and :meth:`iter` do not have a *session* parameter,
            the contextual session creates an :class:`aiohttp.ClientSession`
            object and passes it to :meth:`get` and :meth:`iter` automatically.

        -   It does not have a :meth:`session` method.

        Using the same :class:`aiohttp.ClientSession` object for all Zyte API
        requests improves performance by keeping a pool of reusable connections
        to Zyte API.

        The :class:`aiohttp.ClientSession` object is created with sane defaults
        for Zyte API, but you can use *kwargs* to pass additional parameters to
        :class:`aiohttp.ClientSession` and even override those sane defaults.
        """
        return _Session(client=self, **kwargs)
