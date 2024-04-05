Changes
=======

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
