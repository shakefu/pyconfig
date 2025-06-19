"""
Tests for pyconfig
"""

from __future__ import print_function, unicode_literals

import os
from unittest import mock

import pytest

import pyconfig


def test_namespace_attr():
    ns = pyconfig.Namespace()
    ns.test = True
    assert ns.test is True


def test_namespace_get_config():
    ns = pyconfig.Namespace()
    ns.test = True
    assert ns.as_dict("ns") == {"ns.test": True}


def test_namespace_nested_attr():
    ns = pyconfig.Namespace()
    ns.nest = pyconfig.Namespace()
    ns.nest.test = True
    assert ns.nest.test is True


def test_namespace_nested_get_config():
    ns = pyconfig.Namespace()
    ns.nest = pyconfig.Namespace()
    ns.nest.test = True
    assert ns.as_dict("ns") == {"ns.nest.test": True}


def test_namespace_deep_nested():
    ns = pyconfig.Namespace()
    ns.test = True
    ns.nest = pyconfig.Namespace()
    ns.nest.test = True
    ns.nest.deep = pyconfig.Namespace()
    ns.nest.deep.test = True
    assert ns.as_dict("ns") == {
        "ns.nest.test": True,
        "ns.test": True,
        "ns.nest.deep.test": True,
    }


def test_namespace_implicit_nesting():
    ns = pyconfig.Namespace()
    ns.test = True
    ns.nest.test = True
    ns.nest.deep.test = True
    assert ns.as_dict("ns") == {
        "ns.nest.test": True,
        "ns.test": True,
        "ns.nest.deep.test": True,
    }


def test_set_and_get():
    pyconfig.set("set_and_get", "tested")
    assert pyconfig.get("set_and_get") == "tested"


def test_allow_default():
    assert pyconfig.get("test_allow_default1") is None
    assert pyconfig.get("test_allow_default2", default=None) is None
    assert (
        pyconfig.get("test_allow_default3", "default_value", allow_default=True)
        == "default_value"
    )


def test_get_no_default():
    with pytest.raises(LookupError):
        pyconfig.get("get_no_default1", allow_default=False)


def test_config_get_no_default():
    with pytest.raises(LookupError):
        pyconfig.Config().get("get_no_default2", None, allow_default=False)


def test_set_get_change():
    pyconfig.set("set_get_change", "testing")
    assert pyconfig.get("set_get_change") == "testing"
    pyconfig.set("set_get_change", "tested")
    assert pyconfig.get("set_get_change") == "tested"


def test_setting():
    class Test(object):
        setting = pyconfig.Setting("test", "value")

    assert Test.setting == "value"
    assert Test().setting == "value"


def test_setting_change():
    class Test(object):
        setting = pyconfig.Setting("test_setting_change", "value")

    assert Test.setting == "value"
    assert Test().setting == "value"
    pyconfig.set("test_setting_change", "value2")
    assert Test.setting == "value2"
    assert Test().setting == "value2"


def test_setting_no_default():
    class Test(object):
        setting_no_default = pyconfig.Setting(
            "test_setting_no_default", allow_default=False
        )

    with pytest.raises(LookupError):
        Test.setting_no_default
    pyconfig.set("test_setting_no_default", "new_value")
    assert Test.setting_no_default == "new_value"


def test_config_update():
    conf = pyconfig.Config()
    conf.settings = {}
    conf._update({"test_config_update": "test_value"}, "ns")
    assert conf.settings == {"ns.test_config_update": "test_value"}
    assert conf.get("ns.test_config_update", None) == "test_value"


def test_config_update_sans_private():
    conf = pyconfig.Config()
    conf.settings = {}
    conf._update({"_test_private": "private", "other": "nonprivate"}, "ns")
    assert conf.settings == {"ns.other": "nonprivate"}
    assert conf.get("ns.other", None) == "nonprivate"
    assert conf.get("ns._test_private", None) is None


def test_config_update_skip_namespace_class():
    conf = pyconfig.Config()
    conf.settings = {}
    conf._update({"Namespace": pyconfig.Namespace})
    assert conf.settings == {}


def test_config_update_nested_namespace():
    conf = pyconfig.Config()
    conf.settings = {}
    ns = pyconfig.Namespace()
    ns.value = "value"
    conf._update({"test": ns}, "ns")
    assert conf.get("ns.test.value", None) == "value"


def test_config_update_callable():
    conf = pyconfig.Config()
    conf.settings = {}

    def call():
        return "value"

    conf._update({"test_callable": call}, "ns")
    assert conf.get("ns.test_callable", None) == "value"


def test_reload_hook():
    hook = mock.MagicMock()
    pyconfig.reload_hook(hook)
    pyconfig.reload()
    hook.assert_called_with()


def test_setting_shortcut():
    class Test(object):
        setting = pyconfig.setting("test_setting_shortcut", "tested")
        setting_no_default = pyconfig.setting(
            "setting_shortcut_no_default", allow_default=False
        )

    assert Test.setting == "tested"
    assert Test().setting == "tested"
    with pytest.raises(LookupError):
        Test.setting_no_default


def test_get_default_with_various_values():
    assert pyconfig.get("default_num", 1) == 1
    assert pyconfig.get("default_num", 1.0) == 1.0
    assert pyconfig.get("default_none", None) is None
    assert pyconfig.get("default_true", True) is True
    assert pyconfig.get("default_false", False) is False
    assert pyconfig.get("default_unicode", "Test") == "Test"
    assert pyconfig.get("default_expr", 60 * 24) == 60 * 24
    assert pyconfig.get("ns.test_namespace", "pyconfig") == "pyconfig"


def test_localconfig_py_actually_works():
    assert pyconfig.get("conf.local", False) is True


def test_case_insensitivity():
    pyconfig.set("SomeSetting", True)
    assert pyconfig.get("SomeSetting") is True
    assert pyconfig.get("somesetting") is True


def test_case_sensitive():
    pyconfig.set("pyconfig.case_sensitive", True)
    pyconfig.set("CaseSensitive", True)
    assert pyconfig.get("CaseSensitive") is True
    assert pyconfig.get("casesensitive") is None
    pyconfig.reload(clear=True)


def test_env_key_should_return_default():
    assert pyconfig.env_key("testing.key", 1) == 1


def test_env_key_should_return_from_environ():
    os.environ["TESTING_KEY"] = "true"
    assert pyconfig.env_key("testing.key", 1) == "true"
