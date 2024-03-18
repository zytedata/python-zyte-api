.. _`asyncio_api`:

===========
asyncio API
===========

Create an instance of the ``AsyncZyteAPI`` to use the asyncio client API.
You can use the method ``request_raw`` to perform individual requests:

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

    from zyte_api import AsyncZyteAPI
    from zyte_api.aio.errors import RequestError

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
        async with create_session(n_conn=client.n_conn) as session:
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

Sessions allow enforcing a concurrency limit (``n_conn``) and improve
performance through a pool of reusable connections to the Zyte API server.
