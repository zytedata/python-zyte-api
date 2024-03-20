.. _`asyncio_api`:

===========
asyncio API
===========

Create an instance of the ``AsyncZyteAPI`` to use the asyncio client API. You
can use the method ``get`` to perform individual requests:

.. code-block:: python

    import asyncio
    from zyte_api import AsyncZyteAPI

    client = AsyncZyteAPI(api_key="YOUR_API_KEY")


    async def main():
        result = await client.get({"url": "https://toscrape.com", "httpResponseBody": True})


    asyncio.run(main())

.. tip:: You can skip the ``api_key`` parameter if you :ref:`use an environment
    variable instead <api-key>`.

There is also an ``iter`` method, which allows to process many URLs in
parallel, using multiple connections:

.. code-block:: python

    import asyncio

    from zyte_api import AsyncZyteAPI, RequestError, create_session


    async def main():
        client = AsyncZyteAPI(api_key="YOUR_API_KEY")
        queries = [
            {"url": "https://toscrape.com", "httpResponseBody": True},
            {"url": "https://books.toscrape.com", "httpResponseBody": True},
        ]
        for future in client.iter(queries):
            try:
                result = await future
            except RequestError as e:
                ...


    asyncio.run(main())


``iter`` yields results as they come, not necessarily in their original order.

``iter`` and ``get`` methods handle throttling (http 429 errors) and network
errors, retrying a request in these cases.

When using ``iter`` or multiple ``get`` calls, consider using a session:

.. code-block:: python

    import asyncio

    from zyte_api import AsyncZyteAPI, create_session


    async def main():
        client = AsyncZyteAPI(api_key="YOUR_API_KEY")
        async with create_session(client.n_conn) as session:
            queries = [
                {"url": "https://toscrape.com", "httpResponseBody": True},
                {"url": "https://books.toscrape.com", "httpResponseBody": True},
            ]
            for future in client.iter(queries, session=session):
                try:
                    result = await future
                except RequestError as e:
                    ...


    asyncio.run(main())

Sessions improve performance through a pool of reusable connections to the Zyte
API server.

To send many queries with a concurrency limit, set ``n_conn`` in your client:

.. code-block:: python

    client = AsyncZyteAPI(n_conn=15)

Then use ``iter`` to send your queries. ``n_conn`` is not enforced when using 
``get`` instead of ``iter``.
