===============
python-zyte-api
===============

.. image:: https://img.shields.io/pypi/v/zyte-api.svg
   :target: https://pypi.python.org/pypi/zyte-api
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/zyte-api.svg
   :target: https://pypi.python.org/pypi/zyte-api
   :alt: Supported Python Versions

.. image:: https://github.com/zytedata/python-zyte-api/actions/workflows/test.yml/badge.svg
   :target: https://github.com/zytedata/python-zyte-api/actions/workflows/test.yml
   :alt: Build Status

.. image:: https://codecov.io/github/zytedata/zyte-api/coverage.svg?branch=master
   :target: https://codecov.io/gh/zytedata/zyte-api
   :alt: Coverage report

.. description-start

Command-line client and Python client library for `Zyte API`_.

.. _Zyte API: https://docs.zyte.com/zyte-api/get-started.html

.. description-end

Installation
============

.. install-start

.. code-block:: shell

    pip install zyte-api

Or, to use x402_:

.. _x402: https://www.x402.org/

.. code-block:: shell

    pip install zyte-api[x402]

.. note:: Python 3.9+ is required; Python 3.10+ if using x402.

.. install-end

Basic usage
===========

.. basic-key-start

Set your API key
----------------

.. key-get-start

After you `sign up for a Zyte API account
<https://app.zyte.com/account/signup/zyteapi>`_, copy `your API key
<https://app.zyte.com/o/zyte-api/api-access>`_.

.. key-get-end
.. basic-key-end

.. basic-start


Use the command-line client
---------------------------

Then you can use the zyte-api command-line client to send Zyte API requests.
First create a text file with a list of URLs:

.. code-block:: none

    https://books.toscrape.com
    https://quotes.toscrape.com

And then call ``zyte-api`` from your shell:

.. code-block:: shell

    zyte-api url-list.txt --api-key YOUR_API_KEY --output results.jsonl


Use the Python sync API
-----------------------

For very basic Python scripts, use the sync API:

.. code-block:: python

    from zyte_api import ZyteAPI

    client = ZyteAPI(api_key="YOUR_API_KEY")
    response = client.get({"url": "https://toscrape.com", "httpResponseBody": True})


Use the Python async API
------------------------

For asyncio code, use the async API:

.. code-block:: python

    import asyncio

    from zyte_api import AsyncZyteAPI


    async def main():
        client = AsyncZyteAPI(api_key="YOUR_API_KEY")
        response = await client.get(
            {"url": "https://toscrape.com", "httpResponseBody": True}
        )


    asyncio.run(main())

.. basic-end

Read the `documentation <https://python-zyte-api.readthedocs.io>`_  for more
information.

* Documentation: https://python-zyte-api.readthedocs.io
* Source code: https://github.com/zytedata/python-zyte-api
* Issue tracker: https://github.com/zytedata/python-zyte-api/issues
