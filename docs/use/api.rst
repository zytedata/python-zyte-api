.. _api:

.. currentmodule:: zyte_api

=====================
Python client library
=====================

Once you have :ref:`installed python-zyte-api <install>` and :ref:`configured
your API key <api-key>`, you can use one of its APIs from Python code:

-   The :ref:`sync API <sync>` can be used to build simple, proof-of-concept or
    debugging Python scripts.

-   The :ref:`async API <asyncio_api>` can be used from `asyncio coroutines`_,
    and is meant for production usage, as well as for asyncio environments like
    `Jupyter notebooks`_.

    .. _asyncio coroutines: https://docs.python.org/3/library/asyncio-task.html
    .. _Jupyter notebooks: https://jupyter.org/

.. _sync:

Sync API
========

Create a :class:`ZyteAPI` object, and use its
:meth:`~ZyteAPI.get` method to perform a single request:

.. code-block:: python

    from zyte_api import ZyteAPI

    client = ZyteAPI()
    result = client.get({"url": "https://toscrape.com", "httpResponseBody": True})

To perform multiple requests, use a :meth:`~ZyteAPI.session` for
better performance, and use :meth:`~ZyteAPI.iter` to send multiple
requests in parallel:

.. code-block:: python

    from zyte_api import ZyteAPI, RequestError

    client = ZyteAPI()
    with client.session() as session:
        queries = [
            {"url": "https://toscrape.com", "httpResponseBody": True},
            {"url": "https://books.toscrape.com", "httpResponseBody": True},
        ]
        for result_or_exception in session.iter(queries):
            if isinstance(result_or_exception, dict):
                ...
            elif isinstance(result_or_exception, RequestError):
                ...
            else:
                assert isinstance(result_or_exception, Exception)
                ...

.. tip:: :meth:`~ZyteAPI.iter` yields results as they come, not
    necessarily in their original order. Use `echoData`_ to track the source
    request.

    .. _echoData: https://docs.zyte.com/zyte-api/usage/reference.html#operation/extract/request/echoData

.. _asyncio_api:

Async API
=========

Create an :class:`AsyncZyteAPI` object, and use its
:meth:`~AsyncZyteAPI.get` method to perform a single request:

.. code-block:: python

    import asyncio

    from zyte_api import AsyncZyteAPI


    async def main():
        client = AsyncZyteAPI()
        result = await client.get({"url": "https://toscrape.com", "httpResponseBody": True})


    asyncio.run(main())

To perform multiple requests, use a :meth:`~AsyncZyteAPI.session` for
better performance, and use :meth:`~AsyncZyteAPI.iter` to send
multiple requests in parallel:

.. code-block:: python

    import asyncio

    from zyte_api import ZyteAPI, RequestError


    async def main():
        client = ZyteAPI()
        async with client.session() as session:
            queries = [
                {"url": "https://toscrape.com", "httpResponseBody": True},
                {"url": "https://books.toscrape.com", "httpResponseBody": True},
            ]
            for future in session.iter(queries):
                try:
                    result = await future
                except RequestError as e:
                    ...
                except Exception as e:
                    ...


    asyncio.run(main())

.. tip:: :meth:`~AsyncZyteAPI.iter` yields results as they come, not
    necessarily in their original order. Use `echoData`_ to track the source
    request.


Optimization
============

:class:`ZyteAPI` and :class:`AsyncZyteAPI` use 15
concurrent connections by default.

To change that, use the ``n_conn`` parameter when creating your client object:

.. code-block:: python

    client = ZyteAPI(n_conn=30)

The number of concurrent connections if enforced across all method calls,
including different sessions of the same client.

For guidelines on how to choose the optimal value for you, and other
optimization tips, see `Optimizing Zyte API usage`_.

.. _Optimizing Zyte API usage: https://docs.zyte.com/zyte-api/usage/optimize.html


Errors and retries
==================

Methods of :class:`ZyteAPI` and :class:`AsyncZyteAPI`
automatically handle retries for `rate-limiting`_ and unsuccessful_ responses,
as well as network errors.

.. _rate-limiting: https://docs.zyte.com/zyte-api/usage/errors.html#rate-limiting-responses
.. _unsuccessful: https://docs.zyte.com/zyte-api/usage/errors.html#unsuccessful-responses

.. _default-retry-policy:

The default retry policy, :data:`~zyte_api.zyte_api_retrying`, does the
following:

-   Retries `rate-limiting`_ responses forever.

-   Retries unsuccessful_ responses up to 3 times.

-   Retries network errors for up to 15 minutes.

All retries are done with an exponential backoff algorithm.

To customize the retry policy, create your own :class:`~tenacity.AsyncRetrying`
object, e.g. using a custom subclass of :data:`~zyte_api.RetryFactory`, and
pass it when creating your client object:

.. code-block:: python

    client = ZyteAPI(retrying=custom_retry_policy)

When retries are exceeded for a given request, an exception is raised. Except
for the :meth:`~ZyteAPI.iter` method of the :ref:`sync API <sync>`, which
yields exceptions instead of raising them, to prevent exceptions from
interrupting the entire iteration.

The type of exception depends on the issue that caused the final request
attempt to fail. Unsuccessful responses trigger a
:exc:`~zyte_api.RequestError` and network errors trigger `aiohttp exceptions`_.
Other exceptions could be raised; for example, from a custom retry policy.

.. _aiohttp exceptions: https://docs.aiohttp.org/en/stable/client_reference.html#client-exceptions


.. seealso:: :ref:`api-ref`
