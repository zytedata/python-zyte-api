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

Command-line utility, asyncio-based library and a simple synchronous wrapper
are provided by this package.

License is BSD 3-clause.

Installation
============

::

    pip install zyte-api

zyte-api requires Python 3.6+.

Usage
=====

First, make sure you have an API key. To avoid passing it in ``api_key``
argument with every call, you can set ``ZYTE_API_KEY``
environment variable with the key.

Synchronous API
---------------

Synchronous API provides an easy way to try Zyte Automatic Extraction.
For production usage asyncio API is strongly recommended.

To send a request, use ``request_raw`` function; consult with the
`API docs`_ to understand how to populate the query::

    from zyte_api.sync import request_raw
    results = request_raw({
        'url': 'http://example.com.foo',
        'browserHtml': True
    })

asyncio API
-----------
Basic usage is similar to the sync API (``request_raw``),
but asyncio event loop is used::

    from zyte_api.aio import request_raw

    async def foo():
        results = await request_raw({
            'url': 'http://example.com.foo',
            'browserHtml': True
        })
        # ...

There is also ``request_parallel_as_completed`` function, which allows
to process many URLs in parallel, using multiple connections::

    import sys
    from zyte_api.aio import request_parallel_as_completed, create_session

    async def extract_from(urls):
        requests = [
            {"url": url, "browserHtml": True}
            for url in urls
        ]
        async with create_session() as session:
            res_iter = request_parallel_as_completed(requests,
                                        n_conn=15, session=session)
            for fut in res_iter:
                try:
                    res = await fut
                    # do something with a result, e.g.
                    print(json.dumps(res))
                except RequestError as e:
                    print(e, file=sys.stderr)
                    raise

``request_parallel_as_completed`` is modelled after ``asyncio.as_completed``
(see https://docs.python.org/3/library/asyncio-task.html#asyncio.as_completed),
and actually uses it under the hood.

``request_parallel_as_completed`` and ``request_raw`` functions handle
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
