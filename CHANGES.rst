Changes
=======

0.8.0 (2025-08-07)
------------------

* Added :ref:`x402 support <x402>`.

0.7.1 (2025-06-05)
------------------

* Restored and deprecated the ``temporary_download_error_stop()`` and
  ``temporary_download_error_wait()`` methods of :class:`~.RetryFactory` for
  backwards compatibility.

0.7.0 (2025-02-17)
------------------

* Dropped support for Python 3.8, added support for Python 3.12 and 3.13.

* Renamed some methods of :class:`~.RetryFactory` for consistency, since they
  now handle both temporary and permanent download errors:

  * ``temporary_download_error_stop()`` →
    :meth:`~.RetryFactory.download_error_stop`

  * ``temporary_download_error_wait()`` →
    :meth:`~.RetryFactory.download_error_wait`

* Made the :ref:`default retry policy <default-retry-policy>` behave like the
  :ref:`aggressive retry policy <aggressive-retry-policy>`, but with half the
  retry attempts:

  * :ref:`Permanent download errors <zapi-permanent-download-errors>` now also
    count towards the retry limit of :ref:`temporary download errors
    <zapi-temporary-download-errors>`.

  * Permanent download errors are now retried once.

  * Error responses with an HTTP status code in the 500-599 range (503, 520 and
    521 excluded) are now retried once.

* Fixed the session example of the :ref:`async API <asyncio_api>`.

0.6.0 (2024-05-29)
------------------

* Improved how the :ref:`default retry policy <default-retry-policy>` handles
  :ref:`temporary download errors <zapi-temporary-download-errors>`.
  Before, 3 HTTP 429 responses followed by a single HTTP 520 response would
  have prevented a retry. Now, unrelated responses and errors do not count
  towards the HTTP 520 retry limit.

* Improved how the :ref:`default retry policy <default-retry-policy>` handles
  network errors. Before, after 15 minutes of unsuccessful responses (e.g. HTTP
  429), any network error would prevent a retry. Now, network errors must happen
  15 minutes in a row, without different errors in between, to stop retries.

* Implemented an optional :ref:`aggressive retry policy
  <aggressive-retry-policy>`, which retries more errors more often, and could
  be useful for long crawls or websites with a low success rate.

* Improved the exception that is raised when passing an invalid retrying policy
  object to a :ref:`Python client <api>`.

0.5.2 (2024-05-10)
------------------

* :class:`~zyte_api.RequestError` now has a :data:`~zyte_api.RequestError.query`
  attribute with the Zyte API request parameters that caused the error.

0.5.1 (2024-04-16)
------------------

* :class:`~zyte_api.ZyteAPI` and :class:`~zyte_api.AsyncZyteAPI` sessions no
  longer need to be used as context managers, and can instead be closed with a
  ``close()`` method.

0.5.0 (2024-04-05)
------------------

* Removed Python 3.7 support.

* Added :class:`~zyte_api.ZyteAPI` and :class:`~zyte_api.AsyncZyteAPI` to
  provide both sync and async Python interfaces with a cleaner API.

* Deprecated ``zyte_api.aio``:

  * Replace ``zyte_api.aio.client.AsyncClient`` with the new
    :class:`~zyte_api.AsyncZyteAPI` class.

  * Replace ``zyte_api.aio.client.create_session`` with the new
    :meth:`AsyncZyteAPI.session <zyte_api.AsyncZyteAPI.session>` method.

  * Import ``zyte_api.aio.errors.RequestError``,
    ``zyte_api.aio.retry.RetryFactory`` and
    ``zyte_api.aio.retry.zyte_api_retrying`` directly from ``zyte_api`` now.

* When using the command-line interface, you can now use ``--store-errors`` to
  have error responses be stored alongside successful responses.

* Improved the documentation.

0.4.8 (2023-11-02)
------------------

* Include the Zyte API request ID value in a new ``.request_id`` attribute
  in ``zyte_api.aio.errors.RequestError``.

0.4.7 (2023-09-26)
------------------

* ``AsyncClient`` now lets you set a custom user agent to send to Zyte API.

0.4.6 (2023-09-26)
------------------

* Increased the client timeout to match the server’s.
* Mentioned the ``api_key`` parameter of ``AsyncClient`` in the docs example.

0.4.5 (2023-01-03)
------------------

* w3lib >= 2.1.1 is required in install_requires, to ensure that URLs
  are escaped properly.
* unnecessary ``requests`` library is removed from install_requires
* fixed tox 4 support

0.4.4 (2022-12-01)
------------------

* Fixed an issue with submitting URLs which contain unescaped symbols
* New "retrying" argument for AsyncClient.__init__, which allows to set
  custom retrying policy for the client
* ``--dont-retry-errors`` argument in the CLI tool

0.4.3 (2022-11-10)
------------------

* Connections are no longer reused between requests.
  This reduces the amount of ``ServerDisconnectedError`` exceptions.

0.4.2 (2022-10-28)
------------------
* Bump minimum ``aiohttp`` version to 3.8.0, as earlier versions don't support
  brotli decompression of responses
* Declared Python 3.11 support

0.4.1 (2022-10-16)
------------------

* Network errors, like server timeouts or disconnections, are now retried for
  up to 15 minutes, instead of 5 minutes.

0.4.0 (2022-09-20)
------------------

* Require to install ``Brotli`` as a dependency. This changes the requests to
  have ``Accept-Encoding: br`` and automatically decompress brotli responses.

0.3.0 (2022-07-29)
------------------

Internal AggStats class is cleaned up:

* ``AggStats.n_extracted_queries`` attribute is removed, as it was a duplicate
  of ``AggStats.n_results``
* ``AggStats.n_results`` is renamed to ``AggStats.n_success``
* ``AggStats.n_input_queries`` is removed as redundant and misleading;
  AggStats got a new ``AggStats.n_processed`` property instead.

This change is backwards incompatible if you used stats directly.

0.2.1 (2022-07-29)
------------------

* ``aiohttp.client_exceptions.ClientConnectorError`` is now treated as a
  network error and retried accordingly.
* Removed the unused ``zyte_api.sync`` module.

0.2.0 (2022-07-14)
------------------

* Temporary download errors are now retried 3 times by default.
  They were not retried in previous releases.

0.1.4 (2022-05-21)
------------------
This release contains usability improvements to the command-line script:

* Instead of ``python -m zyte_api`` you can now run it as ``zyte-api``;
* the type of the input file (``--intype`` argument) is guessed now,
  based on file extension and content; .jl, .jsonl and .txt
  files are supported.

0.1.3 (2022-02-03)
------------------

* Minor documenation fix
* Remove support for Python 3.6
* Added support for Python 3.10

0.1.2 (2021-11-10)
------------------

* Default timeouts changed


0.1.1 (2021-11-01)
------------------

* CHANGES.rst updated properly


0.1.0 (2021-11-01)
------------------

* Initial release.
