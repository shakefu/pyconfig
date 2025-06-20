import os
import time

import pytest
import pytool

import pyconfig


@pytest.fixture(scope="module", autouse=True)
def etcd_setup():
    """Setup etcd test data and clean up after tests."""
    if not pyconfig.etcd().module:
        pytest.skip("etcd not installed")

    if not pyconfig.etcd().configured:
        pytest.skip("etcd not configured")

    pyconfig.set("pyconfig.etcd.prefix", "/pyconfig_test/test/")

    client = pyconfig.etcd().client
    client.set("pyconfig_test/test/pyconfig.number", pytool.json.as_json(1))
    client.set("pyconfig_test/test/pyconfig.boolean", pytool.json.as_json(True))
    client.set("pyconfig_test/test/pyconfig.string", pytool.json.as_json("Value"))
    client.set("pyconfig_test/test/pyconfig.json", pytool.json.as_json({"a": "b"}))
    client.set("pyconfig_test/test2/pyconfig.number", pytool.json.as_json(2))
    client.set(
        "pyconfig_test/test2/config.inherit",
        pytool.json.as_json("/pyconfig_test/test/"),
    )

    yield

    # Clean up the test namespace
    if pyconfig.etcd().configured:
        pyconfig.etcd().client.delete("pyconfig_test/test", dir=True, recursive=True)
        pyconfig.etcd().client.delete("pyconfig_test/test2", dir=True, recursive=True)
        pyconfig.etcd().client.delete(
            "pyconfig_test/watching", dir=True, recursive=True
        )
        pyconfig.etcd().client.delete("pyconfig_test/", dir=True, recursive=True)


@pytest.mark.skipif(
    not pyconfig.etcd().module or not pyconfig.etcd().configured,
    reason="etcd not installed or configured",
)
def test_using_correct_prefix():
    assert pyconfig.etcd().prefix == "/pyconfig_test/test/"


def test_parse_hosts_single_host():
    host = pyconfig.etcd()._parse_hosts("127.0.0.1:2379")
    assert host == (("127.0.0.1", 2379),)


def test_parse_hosts_multiple_hosts():
    hosts = "10.0.0.1:2379,10.0.0.2:2379,10.0.0.3:2379"
    hosts = pyconfig.etcd()._parse_hosts(hosts)
    assert hosts == (("10.0.0.1", 2379), ("10.0.0.2", 2379), ("10.0.0.3", 2379))


@pytest.mark.skipif(
    not pyconfig.etcd().module or not pyconfig.etcd().configured,
    reason="etcd not installed or configured",
)
def test_load_works():
    conf = pyconfig.etcd().load()
    assert conf.get("pyconfig.json") == {"a": "b"}
    assert conf.get("pyconfig.string") == "Value"
    assert conf.get("pyconfig.boolean") is True
    assert conf.get("pyconfig.number") == 1


@pytest.mark.skipif(
    not pyconfig.etcd().module or not pyconfig.etcd().configured,
    reason="etcd not installed or configured",
)
def test_changing_prefix_works():
    pyconfig.etcd(prefix="pyconfig/other")
    assert pyconfig.etcd().prefix == "/pyconfig/other/"
    conf = pyconfig.etcd().load()
    assert conf == {}
    pyconfig.set("pyconfig.etcd.prefix", "pyconfig_test/test")
    assert pyconfig.etcd().prefix == "/pyconfig_test/test/"


@pytest.mark.skipif(
    not pyconfig.etcd().module or not pyconfig.etcd().configured,
    reason="etcd not installed or configured",
)
def test_inheritance_works():
    pyconfig.set("pyconfig.etcd.prefix", "pyconfig_test/test2")
    conf = pyconfig.etcd().load()
    assert conf.get("pyconfig.json") == {"a": "b"}
    assert conf.get("pyconfig.string") == "Value"
    assert conf.get("pyconfig.boolean") is True
    assert conf.get("pyconfig.number") == 2
    assert conf.get("config.inherit") == "/pyconfig_test/test/"
    pyconfig.set("pyconfig.etcd.prefix", "pyconfig_test/test")


@pytest.mark.skipif(
    not pyconfig.etcd().module or not pyconfig.etcd().configured,
    reason="etcd not installed or configured",
)
def test_reload_work_with_inheritance():
    pyconfig.set("pyconfig.etcd.prefix", "pyconfig_test/test2")
    pyconfig.reload()


@pytest.mark.skipif(
    not pyconfig.etcd().module or not pyconfig.etcd().configured,
    reason="etcd not installed or configured",
)
def test_autoloading_etcd_config_works():
    pyconfig.Config().clear()
    pyconfig.set("pyconfig.etcd.prefix", "pyconfig_test/test2")
    pyconfig.reload()
    assert pyconfig.get("pyconfig.string") == "Value"
    assert pyconfig.get("pyconfig.number") == 2


@pytest.mark.skipif(
    not pyconfig.etcd().module or not pyconfig.etcd().configured,
    reason="etcd not installed or configured",
)
def test_watching():
    # Enable watching
    os.environ["PYCONFIG_ETCD_WATCH"] = "true"

    pyconfig.Config().clear()
    pyconfig.set("pyconfig.etcd.prefix", "pyconfig_test/watching")
    pyconfig.reload()

    # Wait for 20ms before writing to ensure the watcher thread is ready
    time.sleep(0.020)

    # Write a new value directly to etcd
    pyconfig.etcd().client.write(
        "pyconfig_test/watching/it.works", pytool.json.as_json(True)
    )

    # Try to get the value... this is a bit sloppy but good luck doing
    # something better
    retry = 50
    while retry:
        retry -= 1
        if pyconfig.get("it.works", None) is not None:
            break
        # Wait 20ms more for it to show up
        time.sleep(0.020)

    assert pyconfig.get("it.works", False) is True


# TODO:
# - Add tests for protocol environment variable
def test_protocol_is_picked_up_and_used():
    pytest.skip("TODO")


# - Add tests for auth environment variable
def test_auth_is_picked_up_and_used():
    pytest.skip("TODO")
