===============
python-zyte-api
===============

.. image:: https://img.shields.io/pypi/v/zyte-api.svg
   :target: https://pypi.python.org/pypi/zyte-api
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/zyte-api.svg
   :target: https://pypi.python.org/pypi/zyte-api
   :alt: Supported Python Versions

.. image:: https://github.com/zytedata/zyte-api/workflows/tox/badge.svg
   :target: https://github.com/zytedata/zyte-api/actions
   :alt: Build Status

.. image:: https://codecov.io/github/zytedata/zyte-api/coverage.svg?branch=master
   :target: https://codecov.io/gh/zytedata/zyte-api
   :alt: Coverage report

Python client libraries for Zyte Data API.

Command-line utility and asyncio-based library are provided by this package.

License is BSD 3-clause.

Installation
============

::

    pip install zyte-api

zyte-api requires Python 3.6+.

Usage
=====

First, make sure you have an API key. You can set ``ZYTE_API_KEY`` environment
variable with the key to avoid passing it around explicitly.

Command-line interface
----------------------

The most basic way to use the client is from a command line.
First, create a file with urls, an URL per line (e.g. ``urls.txt``).

Second, set ``ZYTE_API_KEY`` env variable with your
API key (you can also pass API key as ``--api-key`` script
argument).

Then run a script, to get the results::

    python -m zyte_api urls.txt --output res.jl

.. note::
    The results can be stored in an order which is different from the input
    order. If you need to match the output results to the input URLs, the
    best way is to use the ``echoData`` field (see below); it is passed through,
    and returned as-is in the ``echoData`` attribute. By default it will
    contain the input URL the content belongs to.

If you need more flexibility, you can customize the requests by creating
a JsonLines file with queries: a JSON object per line. You can pass any
Zyte Automatic Extraction options there. Example - store it in ``requests.jl`` file::

    {"url": "http://example.com", "geolocation": "GB", "echoData": "homepage"}
    {"url": "http://example.com/foo", "javascript": "off"}
    {"url": "http://example.com/bar", "geolocation": "US"}

See `API docs`_ for a description of all supported parameters.

.. _API docs: https://docs.zyte.com/zyte-api/openapi.html

To get results for this ``requests.jl`` file, run::

    python -m zyte-api --intype jl requests.jl --output res.jl

Processing speed
~~~~~~~~~~~~~~~~

Each API key has a limit on RPS. To get your URLs processed faster you can
increase the number concurrent connections.

Best options depend on the RPS limit and on websites you're extracting
data from. For example, if your API key has a limit of 3RPS, and average
response time you observe for your websites is 10s, then to get to these
3RPS you may set the number of concurrent connections to 30.

To set these options in the CLI, use the ``--n-conn`` argument::

    python -m zyte-api urls.txt --n-conn 30 --output res.jl

If too many requests are being processed in parallel, you'll be getting
throttling errors. They are handled by CLI automatically, but they make
extraction less efficient; please tune the concurrency options to
not hit the throttling errors (HTTP 429) often.

You may be also limited by the website speed. The Zyte API tries not to hit
any individual website too hard, but it could be better to limit this on
a client side as well. If you're extracting data from a single website,
it could make sense to decrease the amount of parallel requests; it can ensure
higher success ratio overall.

If you're extracting data from multiple websites, it makes sense to spread the
load across time: if you have websites A, B and C, don't send requests in
AAAABBBBCCCC order, send them in ABCABCABCABC order instead.

To do so, you can change the order of the queries in your input file.
Alternatively, you can pass ``--shuffle`` options; it randomly shuffles
input queries before sending them to the API:

    python -m zyte-api urls.txt --shuffle --output res.jl

Run ``python -m zyte-api --help`` to get description of all supported
options.

asyncio API
-----------

Create an instance of the ``AsyncClient`` to use the asyncio client API.
You can use the method ``request_raw`` to perform individual requests::

    import asyncio
    from zyte_api.aio.client import AsyncClient

    client = AsyncClient()

    async def single_request(url):
        return await client.request_raw({
            'url': url,
            'browserHtml': True
        })

    response = asyncio.run(single_request("http://books.toscrape.com"))
    # Do something with the response ..

There is also ``request_parallel_as_completed`` method, which allows
to process many URLs in parallel, using multiple connections::

    import asyncio
    import json
    import sys

    from zyte_api.aio.client import AsyncClient, create_session
    from zyte_api.aio.errors import RequestError

    async def extract_from(urls, n_conn):
        client = AsyncClient(n_conn=n_conn)
        requests = [
            {"url": url, "browserHtml": True}
            for url in urls
        ]
        async with create_session(n_conn) as session:
            res_iter = client.request_parallel_as_completed(requests, session=session)
            for fut in res_iter:
                try:
                    res = await fut
                    # do something with a result, e.g.
                    print(json.dumps(res))
                except RequestError as e:
                    print(e, file=sys.stderr)
                    raise

    urls = ["http://toscrape.com", "http://books.toscrape.com"]
    asyncio.run(extract_from(urls, n_conn=15))

``request_parallel_as_completed`` is modelled after ``asyncio.as_completed``
(see https://docs.python.org/3/library/asyncio-task.html#asyncio.as_completed),
and actually uses it under the hood.

``request_parallel_as_completed`` and ``request_raw`` methods handle
throttling (http 429 errors) and network errors, retrying a request in
these cases.

CLI interface implementation (``zyte_api/__main__.py``) can serve
as an usage example.

Contributing
============

* Source code: https://github.com/zytedata/python-zyte-api
* Issue tracker: https://github.com/zytedata/python-zyte-api/issues

Use tox_ to run tests with different Python versions::

    tox

The command above also runs type checks; we use mypy.

.. _tox: https://tox.readthedocs.io
