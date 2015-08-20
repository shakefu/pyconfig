import pytool
from nose import SkipTest
from nose.tools import ok_, eq_

import pyconfig


def setup():
    if pyconfig.etcd is None:
        raise SkipTest("etcd not installed")

    client = pyconfig.Config().etcd
    client.set('pyconfig/test/pyconfig.number', pytool.json.as_json(1))
    client.set('pyconfig/test/pyconfig.boolean', pytool.json.as_json(True))
    client.set('pyconfig/test/pyconfig.string', pytool.json.as_json("Value"))
    client.set('pyconfig/test/pyconfig.json', pytool.json.as_json({"a": "b"}))


def test_load_from_etcd_works():
    update = pyconfig.Config().load_from_etcd('/pyconfig/test/')
    eq_(update.get('pyconfig.json'), {"a": "b"})
    eq_(update.get('pyconfig.string'), 'Value')
    eq_(update.get('pyconfig.boolean'), True)
    eq_(update.get('pyconfig.number'), 1)
