import os

import pytest

from quantdeck_backend.bridge.secrets import SecretStore


def make_store(tmp_path):
    return SecretStore(str(tmp_path / "secrets.enc"))


def test_unlock_initializes_empty(tmp_path):
    store = make_store(tmp_path)
    assert store.is_unlocked() is False
    store.unlock("pw123")
    assert store.is_unlocked() is True
    assert store.load() == {}


def test_set_get_roundtrip_persists_encrypted(tmp_path):
    store = make_store(tmp_path)
    store.unlock("pw123")
    store.set_credential("binance", {"api_key": "k", "api_secret": "s", "testnet": False})
    # 新实例、相同口令应能解出
    store2 = make_store(tmp_path)
    store2.unlock("pw123")
    assert store2.get_credential("binance") == {
        "api_key": "k",
        "api_secret": "s",
        "testnet": False,
    }
    # 落盘内容是密文，不含明文
    raw = open(tmp_path / "secrets.enc", "rb").read()
    assert b"api_secret" not in raw and b"\"s\"" not in raw


def test_wrong_passphrase_rejected(tmp_path):
    store = make_store(tmp_path)
    store.unlock("right")
    store.set_credential("binance", {"api_key": "k", "api_secret": "s", "testnet": False})
    store2 = make_store(tmp_path)
    with pytest.raises(ValueError):
        store2.unlock("wrong")


def test_delete_credential(tmp_path):
    store = make_store(tmp_path)
    store.unlock("pw")
    store.set_credential("binance", {"api_key": "k", "api_secret": "s", "testnet": False})
    store.delete_credential("binance")
    assert store.load() == {}


def test_operations_require_unlock(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(RuntimeError):
        store.load()
