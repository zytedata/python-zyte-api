def test_deprecated_imports():
    from zyte_api import RetryFactory, zyte_api_retrying
    from zyte_api.aio.retry import RetryFactory as DeprecatedRetryFactory
    from zyte_api.aio.retry import zyte_api_retrying as deprecated_zyte_api_retrying

    assert RetryFactory is DeprecatedRetryFactory
    assert zyte_api_retrying is deprecated_zyte_api_retrying
