import pytest

from zyte_api.apikey import NoApiKey, get_apikey


def test_get_apikey(monkeypatch):
    assert get_apikey("a") == "a"
    with pytest.raises(NoApiKey):
        get_apikey()
    with pytest.raises(NoApiKey):
        get_apikey(None)
    monkeypatch.setenv("ZYTE_API_KEY", "b")
    assert get_apikey("a") == "a"
    assert get_apikey() == "b"
    assert get_apikey(None) == "b"
