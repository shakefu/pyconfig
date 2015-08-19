"""
Pyconfig
========

"""
from __future__ import print_function, unicode_literals
import sys
import runpy
import logging
import pkg_resources


from pytool.lang import Namespace


__version__ = '3.0.0-dev'


log = logging.getLogger(__name__)


'''
class Namespace(object):
    """
    Namespace object used for creating settings module. This can be used to
    create nested namespace objects.

    Example::

        from pyconfig import Namespace

        pyconfig = Namespace()
        pyconfig.example.setting = True

    """
    def __init__(self):
        # Using a regular assignment here breaks due to __setattr__ overriding
        object.__setattr__(self, '_config', {})

    def __setattr__(self, name, value):
        # Allow nested property access
        # XXX if isinstance(value, Namespace):
        object.__setattr__(self, name, value)
        self._config[name] = value

    def __getattr__(self, name):
        # Allow implicit nested namespaces by attribute access
        new_space = Namespace()
        setattr(self, name, new_space)
        return new_space

    def _get_config(self, base_name):
        """ Return iterator which returns ``(key, value)`` tuples.

            :param str base_name: Base namespace

        """
        for name, value in self._config.items():
            name = base_name + '.' + name
            # Allow for nested namespaces
            if isinstance(value, Namespace):
                for subkey in value._get_config(name):
                    yield subkey
            else:
                yield name, value
'''


class Setting(object):
    """ Setting descriptor. Allows class property style access of setting
        values that are always up to date.

        If it is set with `allow_default` as `False`, calling the
        attribute when its value is not set will raise a :exc:`LookupError`

        :param str name: Setting key name
        :param default: default value of setting.  Defaults to None.
        :param bool allow_default: If true, use the parameter default as
                        default if the key is not set, else raise
                        :exc:`LookupError`
    """
    def __init__(self, name, default=None, allow_default=True):
        self.name = name
        self.default = default
        self.allow_default = allow_default

    def __get__(self, instance, owner):
        return Config().get(self.name, self.default,
                            allow_default=self.allow_default)


class Config(object):
    """ Singleton configuration object that ensures consistent and up to date
        setting values.

    """
    _self = dict(
            _init=False,
            settings={},
            reload_hooks=[])

    def __init__(self):
        # Use a borg singleton
        self.__dict__ = self._self

        # Only load the first time
        if not self._init:
            self.load()
            self._init = True

    def set(self, name, value):
        """ Changes a setting value.

            :param str name: Setting key name.
            :param value: Setting value.

        """
        log.info("    %s = %s", name, repr(value))
        self.settings[name] = value

    def _update(self, conf_dict, base_name=None):
        """ Updates the current configuration with the values in `conf_dict`.

            :param dict conf_dict: Dictionary of key value settings.
            :param str base_name: Base namespace for setting keys.

        """
        for name in conf_dict:
            # Skip private names
            if name.startswith('_'):
                continue
            value = conf_dict[name]
            # Skip Namespace if it's imported
            if value is Namespace:
                continue
            # Use a base namespace
            if base_name:
                name = base_name + '.' + name
            if isinstance(value, Namespace):
                for name, value in value.iteritems(name):
                    self.set(name, value)
            # Automatically call any functions in the settings module, and if
            # they return a value other than None, that value becomes a setting
            elif callable(value):
                value = value()
                if value is not None:
                    self.set(name, value)
            else:
                self.set(name, value)

    def load(self, clear=False):
        """
        Loads all the config plugin modules to build a working configuration.

        If there is a ``localconfig`` module on the python path, it will be
        loaded last, overriding other settings.

        :param bool clear: Clear out the previous settings before loading

        """
        if clear:
            self.settings = {}

        defer = []

        # Load all config plugins
        for conf in pkg_resources.iter_entry_points('pyconfig'):
            if conf.attrs:
                raise RuntimeError("config must be a module")

            mod_name = conf.module_name
            base_name = conf.name if conf.name != 'any' else None

            log.info("Loading module '%s'", mod_name)
            mod_dict = runpy.run_module(mod_name)

            # If this module wants to be deferred, save it for later
            if mod_dict.get('deferred', None) is deferred:
                log.info("Deferring module '%s'", mod_name)
                mod_dict.pop('deferred')
                defer.append((mod_name, base_name, mod_dict))
                continue

            self._update(mod_dict, base_name)

        # Load deferred modules
        for mod_name, base_name, mod_dict in defer:
            log.info("Loading deferred module '%s'", mod_name)
            self._update(mod_dict, base_name)

        # Allow localconfig overrides
        mod_dict = None
        try:
            mod_dict = runpy.run_module('localconfig')
        except ImportError:
            pass
        except ValueError as err:
            if getattr(err, 'message') != '__package__ set to non-string':
                raise

            # This is a bad work-around to make this work transparently...
            # shouldn't really access core stuff like this, but Fuck It[tm]
            mod_name = 'localconfig'
            if sys.version_info < (2, 7):
                loader, code, fname = runpy._get_module_details(mod_name)
            else:
                _, loader, code, fname = runpy._get_module_details(mod_name)
            mod_dict = runpy._run_code(code, {}, {}, mod_name, fname, loader,
                    pkg_name=None)

        if mod_dict:
            log.info("Loading module 'localconfig'")
            self._update(mod_dict)

        self.call_reload_hooks()

    def call_reload_hooks(self):
        """ Calls all the reload hooks that are registered. """
        # Call all registered reload hooks
        for hook in self.reload_hooks:
            hook()

    def get(self, name, default, allow_default=True):
        """ Return a setting value.

            :param str name: Setting key name.
            :param default: Default value of setting if it's not explicitly
                            set.
            :param bool allow_default: If true, use the parameter default as
                            default if the key is not set, else raise
                            :exc:`LookupError`
            :raises: :exc:`LookupError` if allow_default is false and the setting is
                     not set.
        """
        if name not in self.settings:
            if not allow_default:
                raise LookupError('No setting "{name}"'.format(name=name))
            self.settings[name] = default
        return self.settings[name]

    def reload(self, clear=False):
        """ Reloads the configuration. """
        log.info("Reloading config.")
        self.load(clear)

    def add_reload_hook(self, hook):
        """ Registers a reload hook that's called when :meth:`load` is called.

            :param function hook: Hook to register.

        """
        self.reload_hooks.append(hook)


def reload(clear=False):
    """ Shortcut method for calling reload. """
    Config().reload(clear)


def setting(name, default=None, allow_default=True):
    """ Shortcut method for getting a setting descriptor.

        See :class:`pyconfig.Setting` for details.
    """
    return Setting(name, default, allow_default)


def get(name, default=None, allow_default=True):
    """ Shortcut method for getting a setting value.

        :param str name: Setting key name.
        :param default: Default value of setting if it's not explicitly
                        set. Defaults to `None`
        :param bool allow_default: If true, use the parameter default as
                        default if the key is not set, else raise
                        :exc:`KeyError`.  Defaults to `None`
        :raises: :exc:`KeyError` if allow_default is false and the setting is
                 not set.
    """
    return Config().get(name, default, allow_default=allow_default)


def set(name, value):
    """ Shortcut method to change a setting. """
    Config().set(name, value)


def reload_hook(func):
    """ Decorator for registering a reload hook. """
    Config().add_reload_hook(func)
    return func


def deferred():
    """
    Import this to indicate that a module should be deferred to load its
    settings last. This allows you to override some settings from a pyconfig
    plugin with another plugin in a reliable manner.

    This is a special instance that pyconfig looks for by name. You must use
    the import style ``from pyconfig import deferred`` for this to work.

    If you are not deferring a module, you may use ``deferred`` as a variable
    name without confusing or conflicting with pyconfig's behavior.

    Example::

        from pyconfig import Namespace, deferred

        my_settings = Namespace()
        my_settings.some_setting = 'overridden by deferred'

    """
    pass

