"""
Unit tests for the etcd client setup and loading, using a fake etcd3 module so
they run without etcd (or etcd3) installed.

"""

import builtins
import logging
import sys
import types
from unittest import mock

import pytest

import pyconfig

ETCD_ENV = (
    "PYCONFIG_ETCD_HOSTS",
    "PYCONFIG_ETCD_PROTOCOL",
    "PYCONFIG_ETCD_CACERT",
    "PYCONFIG_ETCD_CERT",
    "PYCONFIG_ETCD_KEY",
    "PYCONFIG_ETCD_AUTH",
    "PYCONFIG_ETCD_WATCH",
    "JETCONFIG_ETCD",
)


class FakeRpcError(Exception):
    """Stands in for grpc.RpcError, which has a code() method."""

    def __init__(self, code_name, details=""):
        super().__init__(details)
        self._code_name = code_name

    def code(self):
        return types.SimpleNamespace(name=self._code_name)


def make_client(*args, **kwargs):
    client = mock.MagicMock(name="client")
    client.call_credentials = "call-credentials"
    client.watcher._credentials = "call-credentials"
    client.get_prefix.return_value = []
    return client


def kv(key, value):
    """Return a (value, metadata) pair like etcd3's get_prefix yields."""
    return (value.encode("utf-8"), types.SimpleNamespace(key=key.encode("utf-8")))


@pytest.fixture
def fake_etcd3(monkeypatch):
    """Install a fake etcd3 module and isolate the etcd singleton state."""
    for name in ETCD_ENV:
        monkeypatch.delenv(name, raising=False)

    module = types.ModuleType("etcd3")
    module.client = mock.MagicMock(name="etcd3.client", side_effect=make_client)
    monkeypatch.setitem(sys.modules, "etcd3", module)

    saved = dict(pyconfig.etcd._self)
    pyconfig.etcd._self.update(
        client=None, module=None, watcher=None, _client_args=None
    )
    try:
        yield module
    finally:
        pyconfig.etcd._self.clear()
        pyconfig.etcd._self.update(saved)


def init(**kwargs):
    e = pyconfig.etcd()
    e.init(**kwargs)
    return e


def client_kwargs(module):
    return module.client.call_args.kwargs


def test_import_failure_other_than_import_error_disables_etcd(
    fake_etcd3, monkeypatch, caplog
):
    real_import = builtins.__import__

    def broken_import(name, *args, **kwargs):
        if name == "etcd3":
            raise TypeError("Descriptors cannot be created directly.")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", broken_import)

    with caplog.at_level(logging.WARNING, logger="pyconfig"):
        e = init(hosts="127.0.0.1:2379")

    assert e.module is None
    assert not e.configured
    assert "failed to import" in caplog.text


def test_connects_to_first_host_without_tls(fake_etcd3):
    e = init(hosts="10.0.0.1:2379,10.0.0.2:2380")
    fake_etcd3.client.assert_called_once_with("10.0.0.1", 2379)
    assert e.configured


def test_cacert_and_client_cert(fake_etcd3):
    init(
        hosts="127.0.0.1:2379", cacert="ca.pem", client_cert="c.pem", client_key="k.pem"
    )
    kw = client_kwargs(fake_etcd3)
    assert kw["ca_cert"].endswith("ca.pem")
    assert kw["cert_cert"].endswith("c.pem")
    assert kw["cert_key"].endswith("k.pem")


def test_client_cert_without_cacert_warns(fake_etcd3, caplog):
    with caplog.at_level(logging.WARNING, logger="pyconfig"):
        init(hosts="127.0.0.1:2379", client_cert="c.pem", client_key="k.pem")
    assert client_kwargs(fake_etcd3) == {}
    assert "PYCONFIG_ETCD_CACERT" in caplog.text


def test_https_without_cacert_warns(fake_etcd3, monkeypatch, caplog):
    monkeypatch.setenv("PYCONFIG_ETCD_PROTOCOL", "https")
    with caplog.at_level(logging.WARNING, logger="pyconfig"):
        init(hosts="127.0.0.1:2379")
    assert "connecting without TLS" in caplog.text


def test_incomplete_client_cert_with_cacert_warns(fake_etcd3, caplog):
    with caplog.at_level(logging.WARNING, logger="pyconfig"):
        init(hosts="127.0.0.1:2379", cacert="ca.pem", client_cert="c.pem")
    kw = client_kwargs(fake_etcd3)
    assert "cert_cert" not in kw
    assert "client key are required" in caplog.text


def test_auth_without_tls_drops_call_credentials(fake_etcd3, monkeypatch):
    monkeypatch.setenv("PYCONFIG_ETCD_AUTH", "user:secret")
    e = init(hosts="127.0.0.1:2379")
    kw = client_kwargs(fake_etcd3)
    assert kw["user"] == "user"
    assert kw["password"] == "secret"
    # gRPC won't send call credentials over plaintext, so they're dropped in
    # favor of the token metadata
    assert e.client.call_credentials is None
    assert e.client.watcher._credentials is None


def test_auth_with_tls_keeps_call_credentials(fake_etcd3, monkeypatch):
    monkeypatch.setenv("PYCONFIG_ETCD_AUTH", "user:secret")
    e = init(hosts="127.0.0.1:2379", cacert="ca.pem")
    assert e.client.call_credentials == "call-credentials"
    assert e.client.watcher._credentials == "call-credentials"


def test_incomplete_auth_warns(fake_etcd3, monkeypatch, caplog):
    monkeypatch.setenv("PYCONFIG_ETCD_AUTH", "user")
    with caplog.at_level(logging.WARNING, logger="pyconfig"):
        init(hosts="127.0.0.1:2379")
    assert "user" not in client_kwargs(fake_etcd3)
    assert "incomplete credentials" in caplog.text


def test_load_skips_nested_keys(fake_etcd3):
    e = init(hosts="127.0.0.1:2379")
    e.client.get_prefix.return_value = [
        kv("/config/app/my.name", "top"),
        kv("/config/app/dev/my.name", "nested"),
    ]
    assert e.load("/config/app/", depth=0) == {"my.name": "top"}


def test_load_strips_mixed_case_prefix(fake_etcd3):
    e = init(hosts="127.0.0.1:2379")
    e.client.get_prefix.return_value = [kv("/Config/App/My.Name", "top")]
    assert e.load("/Config/App/", depth=0) == {"my.name": "top"}


def test_load_reconnects_when_auth_token_expires(fake_etcd3, monkeypatch):
    monkeypatch.setenv("PYCONFIG_ETCD_AUTH", "user:secret")
    e = init(hosts="127.0.0.1:2379")
    expired = e.client
    expired.get_prefix.side_effect = FakeRpcError(
        "UNAUTHENTICATED", "etcdserver: invalid auth token"
    )

    def fresh_client(*args, **kwargs):
        client = make_client()
        client.get_prefix.return_value = [kv("/config/my.name", "value")]
        return client

    fake_etcd3.client.side_effect = fresh_client

    assert e.load("/config/", depth=0) == {"my.name": "value"}
    assert e.client is not expired
    assert fake_etcd3.client.call_count == 2


def test_load_does_not_reconnect_without_auth(fake_etcd3):
    e = init(hosts="127.0.0.1:2379")
    e.client.get_prefix.side_effect = FakeRpcError("UNAUTHENTICATED")
    with pytest.raises(FakeRpcError):
        e.load("/config/", depth=0)
    assert fake_etcd3.client.call_count == 1


def test_load_does_not_reconnect_on_other_errors(fake_etcd3, monkeypatch):
    monkeypatch.setenv("PYCONFIG_ETCD_AUTH", "user:secret")
    e = init(hosts="127.0.0.1:2379")
    e.client.get_prefix.side_effect = FakeRpcError("UNAVAILABLE")
    with pytest.raises(FakeRpcError):
        e.load("/config/", depth=0)
    assert fake_etcd3.client.call_count == 1
