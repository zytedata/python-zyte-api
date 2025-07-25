.. _api:

.. currentmodule:: zyte_api

=====================
Python client library
=====================

Once you have :ref:`installed python-zyte-api <install>` and configured your
:ref:`API key <api-key>` or :ref:`Ethereum private key <x402>`, you can use one
of its APIs from Python code:

-   The :ref:`sync API <sync>` can be used to build simple, proof-of-concept or
    debugging Python scripts.

-   The :ref:`async API <asyncio_api>` can be used from :ref:`coroutines
    <coroutine>`, and is meant for production usage, as well as for asyncio
    environments like `Jupyter notebooks`_.

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
    necessarily in their original order. Use :http:`request:echoData` to track
    the source request.

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

    from zyte_api import AsyncZyteAPI, RequestError


    async def main():
        client = AsyncZyteAPI()
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
    necessarily in their original order. Use :http:`request:echoData` to track
    the source request.


.. _api-optimize:

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
optimization tips, see :ref:`zapi-optimize`.


Errors and retries
==================

Methods of :class:`ZyteAPI` and :class:`AsyncZyteAPI` automatically handle
retries for :ref:`rate-limiting <zapi-rate-limit>` and :ref:`unsuccessful
<zapi-unsuccessful-responses>` responses, as well as network errors.

.. _retry-policy:
.. _default-retry-policy:

The default retry policy, :data:`~zyte_api.zyte_api_retrying`, does the
following for each request:

-   Retries :ref:`rate-limiting responses <zapi-rate-limit>` forever.

-   Retries :ref:`temporary download errors <zapi-temporary-download-errors>`
    up to 3 times. :ref:`Permanent download errors
    <zapi-permanent-download-errors>` also count towards this retry limit.

-   Retries permanent download errors once.

-   Retries network errors until they have happened for 15 minutes straight.

-   Retries error responses with an HTTP status code in the 500-599 range (503,
    520 and 521 excluded) once.

All retries are done with an exponential backoff algorithm.

.. _aggressive-retry-policy:

If some :ref:`unsuccessful responses <zapi-unsuccessful-responses>` exceed
maximum retries with the default retry policy, try using
:data:`~zyte_api.aggressive_retrying` instead, which doubles attempts for
all retry scenarios.

Alternatively, the reference documentation of :class:`~zyte_api.RetryFactory`
and :class:`~zyte_api.AggressiveRetryFactory` features some examples of custom
retry policies, and you can always build your own
:class:`~tenacity.AsyncRetrying` object from scratch.

To use :data:`~zyte_api.aggressive_retrying` or a custom retry policy, pass an
instance of your :class:`~tenacity.AsyncRetrying` subclass when creating your
client object:

.. code-block:: python

    from zyte_api import ZyteAPI, aggressive_retrying

    client = ZyteAPI(retrying=aggressive_retrying)

When retries are exceeded for a given request, an exception is raised. Except
for the :meth:`~ZyteAPI.iter` method of the :ref:`sync API <sync>`, which
yields exceptions instead of raising them, to prevent exceptions from
interrupting the entire iteration.

The type of exception depends on the issue that caused the final request
attempt to fail. Unsuccessful responses trigger a :exc:`RequestError` and
network errors trigger :ref:`aiohttp exceptions <aiohttp-client-reference>`.
Other exceptions could be raised; for example, from a custom retry policy.


.. seealso:: :ref:`api-ref`
