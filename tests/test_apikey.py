import os

import pytest

from zyte_api.apikey import (
    NoApiKey,
    get_apikey,
    read_apikey_from_dotenv,
    read_dotenv_auth,
)


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


def test_get_apikey_from_dotenv(tmp_path):
    # The autouse fixture already chdir'd into the empty tmp_path.
    (tmp_path / ".env").write_text("ZYTE_API_KEY=fromdotenv\n")

    assert get_apikey() == "fromdotenv"
    # An explicit key still wins.
    assert get_apikey("explicit") == "explicit"
    # Reading the file must not modify the environment.
    assert "ZYTE_API_KEY" not in os.environ


def test_get_apikey_from_dotenv_parent_dir(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("ZYTE_API_KEY=fromparent\n")
    subdir = tmp_path / "project" / "subdir"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)

    assert get_apikey() == "fromparent"


def test_get_apikey_env_takes_precedence_over_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("ZYTE_API_KEY=fromdotenv\n")
    monkeypatch.setenv("ZYTE_API_KEY", "fromenv")

    assert get_apikey() == "fromenv"


def test_read_apikey_from_dotenv(tmp_path):
    (tmp_path / ".env").write_text("ZYTE_API_KEY=fromdotenv\nOTHER=ignored\n")

    assert read_apikey_from_dotenv() == "fromdotenv"
    assert "ZYTE_API_KEY" not in os.environ
    assert "OTHER" not in os.environ


def test_read_apikey_from_dotenv_missing(tmp_path):
    # Empty working directory, no .env anywhere relevant.
    assert read_apikey_from_dotenv() is None


def test_read_apikey_from_dotenv_custom_path(tmp_path):
    env_file = tmp_path / "custom.env"
    env_file.write_text("ZYTE_API_KEY=fromcustom\n")

    assert read_apikey_from_dotenv(str(env_file)) == "fromcustom"


def test_read_dotenv_auth_reads_both_credentials(tmp_path):
    (tmp_path / ".env").write_text(
        "ZYTE_API_KEY=k\nZYTE_API_ETH_KEY=e\nOTHER=ignored\n"
    )

    assert read_dotenv_auth() == {"ZYTE_API_KEY": "k", "ZYTE_API_ETH_KEY": "e"}
    assert "ZYTE_API_KEY" not in os.environ
    assert "ZYTE_API_ETH_KEY" not in os.environ


def test_read_dotenv_auth_eth_key_not_read_from_parent(tmp_path, monkeypatch):
    # Both credentials live in a parent .env, but only the API key is read from
    # there; the Ethereum private key is never looked up in parent directories.
    (tmp_path / ".env").write_text(
        "ZYTE_API_KEY=fromparent\nZYTE_API_ETH_KEY=ethfromparent\n"
    )
    subdir = tmp_path / "project" / "subdir"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)

    assert read_dotenv_auth() == {"ZYTE_API_KEY": "fromparent"}


def test_read_dotenv_auth_explicit_path_reads_eth(tmp_path):
    # An explicit path is honored for both credentials (no walking involved).
    env_file = tmp_path / "custom.env"
    env_file.write_text("ZYTE_API_ETH_KEY=e\n")

    assert read_dotenv_auth(str(env_file)) == {"ZYTE_API_ETH_KEY": "e"}
