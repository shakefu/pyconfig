import pytool
from nose import SkipTest
from nose.tools import ok_, eq_

import pyconfig


def setup():
    if not pyconfig.etcd().module:
        raise SkipTest("etcd not installed")

    if not pyconfig.etcd().configured:
        raise SkipTest("etcd not configured")

    pyconfig.set('pyconfig.etcd.prefix', '/pyconfig_test/test/')

    client = pyconfig.etcd().client
    client.set('pyconfig_test/test/pyconfig.number', pytool.json.as_json(1))
    client.set('pyconfig_test/test/pyconfig.boolean', pytool.json.as_json(True))
    client.set('pyconfig_test/test/pyconfig.string', pytool.json.as_json("Value"))
    client.set('pyconfig_test/test/pyconfig.json', pytool.json.as_json({"a": "b"}))
    client.set('pyconfig_test/test2/pyconfig.number', pytool.json.as_json(2))
    client.set('pyconfig_test/test2/config.inherit',
            pytool.json.as_json('/pyconfig_test/test/'))


def teardown():
    if not pyconfig.etcd().configured:
        return

    # Clean up the test namespace
    pyconfig.etcd().client.delete('pyconfig_test/test', dir=True, recursive=True)
    pyconfig.etcd().client.delete('pyconfig_test/test2', dir=True, recursive=True)
    pyconfig.etcd().client.delete('pyconfig_test/', dir=True, recursive=True)


def test_using_correct_prefix():
    eq_(pyconfig.etcd().prefix, '/pyconfig_test/test/')


def test_parse_hosts_single_host():
    host = pyconfig.etcd()._parse_hosts('127.0.0.1:2379')
    eq_(host, (('127.0.0.1', 2379),))


def test_parse_hosts_multiple_hosts():
    hosts = '10.0.0.1:2379,10.0.0.2:2379,10.0.0.3:2379'
    hosts = pyconfig.etcd()._parse_hosts(hosts)
    eq_(hosts, (('10.0.0.1', 2379), ('10.0.0.2', 2379), ('10.0.0.3', 2379)))


def test_load_works():
    conf = pyconfig.etcd().load()
    eq_(conf.get('pyconfig.json'), {"a": "b"})
    eq_(conf.get('pyconfig.string'), 'Value')
    eq_(conf.get('pyconfig.boolean'), True)
    eq_(conf.get('pyconfig.number'), 1)


def test_changing_prefix_works():
    pyconfig.etcd(prefix='pyconfig/other')
    eq_(pyconfig.etcd().prefix, '/pyconfig/other/')
    conf = pyconfig.etcd().load()
    eq_(conf, {})
    pyconfig.set('pyconfig.etcd.prefix', 'pyconfig_test/test')
    eq_(pyconfig.etcd().prefix, '/pyconfig_test/test/')


def test_inheritance_works():
    pyconfig.set('pyconfig.etcd.prefix', 'pyconfig_test/test2')
    conf = pyconfig.etcd().load()
    eq_(conf.get('pyconfig.json'), {"a": "b"})
    eq_(conf.get('pyconfig.string'), 'Value')
    eq_(conf.get('pyconfig.boolean'), True)
    eq_(conf.get('pyconfig.number'), 2)
    eq_(conf.get('config.inherit'), '/pyconfig_test/test/')
    pyconfig.set('pyconfig.etcd.prefix', 'pyconfig_test/test')


def test_reload_work_with_inheritance():
    pyconfig.set('pyconfig.etcd.prefix', 'pyconfig_test/test2')
    pyconfig.reload()


def test_autoloading_etcd_config_works():
    pyconfig.Config().clear()
    pyconfig.set('pyconfig.etcd.prefix', 'pyconfig_test/test2')
    pyconfig.reload()
    eq_(pyconfig.get('pyconfig.string'), 'Value')
    eq_(pyconfig.get('pyconfig.number'), 2)

