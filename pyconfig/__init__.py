"""
Pyconfig
========

"""

from __future__ import print_function

import logging
import os
import runpy
import sys
import threading

import pytool
from pytool.lang import Namespace


def iter_entry_points(group, **kwargs):
    """Iterate over entry points for the given group using importlib.metadata."""
    from importlib.metadata import entry_points

    for entry_point in entry_points(group=group, **kwargs):
        yield entry_point


__version__ = "3.2.3"


log = logging.getLogger(__name__)


class Setting(object):
    """Setting descriptor. Allows class property style access of setting
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
        return Config().get(self.name, self.default, allow_default=self.allow_default)


class Config(object):
    """Singleton configuration object that ensures consistent and up to date
    setting values.

    """

    _self = dict(
        _init=False,
        settings={},
        reload_hooks=[],
        mut_lock=threading.RLock(),
    )

    def __init__(self):
        # Use a borg singleton
        self.__dict__ = self._self

        # Only load the first time
        if not self._init:
            self._init = True
            self.load()

    def set(self, name, value):
        """Changes a setting value.

        This implements a locking mechanism to ensure some level of thread
        safety.

        :param str name: Setting key name.
        :param value: Setting value.

        """
        if not self.settings.get("pyconfig.case_sensitive", False):
            name = name.lower()
        log.info("    %s = %s", name, repr(value))

        # Acquire our lock to change the config
        with self.mut_lock:
            self.settings[name] = value

    def _update(self, conf_dict, base_name=None):
        """Updates the current configuration with the values in `conf_dict`.

        :param dict conf_dict: Dictionary of key value settings.
        :param str base_name: Base namespace for setting keys.

        """
        for name in conf_dict:
            # Skip private names
            if name.startswith("_"):
                continue
            value = conf_dict[name]
            # Skip Namespace if it's imported
            if value is Namespace:
                continue
            # Use a base namespace
            if base_name:
                name = base_name + "." + name
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
        for conf in iter_entry_points("pyconfig"):
            if conf.attrs:
                raise RuntimeError("config must be a module")

            mod_name = conf.module_name
            base_name = conf.name if conf.name != "any" else None

            log.info("Loading module '%s'", mod_name)
            mod_dict = runpy.run_module(mod_name)

            # If this module wants to be deferred, save it for later
            if mod_dict.get("deferred", None) is deferred:
                log.info("Deferring module '%s'", mod_name)
                mod_dict.pop("deferred")
                defer.append((mod_name, base_name, mod_dict))
                continue

            self._update(mod_dict, base_name)

        # Load deferred modules
        for mod_name, base_name, mod_dict in defer:
            log.info("Loading deferred module '%s'", mod_name)
            self._update(mod_dict, base_name)

        if etcd().configured:
            # Load etcd stuff
            mod_dict = etcd().load()
            if mod_dict:
                self._update(mod_dict)

        # Allow localconfig overrides
        mod_dict = None
        try:
            mod_dict = runpy.run_module("localconfig")
        except ImportError:
            pass
        except ValueError as err:
            if getattr(err, "message") != "__package__ set to non-string":
                raise

            # This is a bad work-around to make this work transparently...
            # shouldn't really access core stuff like this, but Fuck It[tm]
            mod_name = "localconfig"
            if sys.version_info < (2, 7):
                loader, code, fname = runpy._get_module_details(mod_name)
            else:
                _, loader, code, fname = runpy._get_module_details(mod_name)
            mod_dict = runpy._run_code(
                code, {}, {}, mod_name, fname, loader, pkg_name=None
            )

        if mod_dict:
            log.info("Loading module 'localconfig'")
            self._update(mod_dict)

        self.call_reload_hooks()

    def call_reload_hooks(self):
        """Calls all the reload hooks that are registered."""
        # Call all registered reload hooks
        for hook in self.reload_hooks:
            hook()

    def get(self, name, default, allow_default=True):
        """Return a setting value.

        :param str name: Setting key name.
        :param default: Default value of setting if it's not explicitly
                        set.
        :param bool allow_default: If true, use the parameter default as
                        default if the key is not set, else raise
                        :exc:`LookupError`
        :raises: :exc:`LookupError` if allow_default is false and the setting is
                 not set.
        """
        if not self.settings.get("pyconfig.case_sensitive", False):
            name = name.lower()
        if name not in self.settings:
            if not allow_default:
                raise LookupError('No setting "{name}"'.format(name=name))
            self.settings[name] = default
        return self.settings[name]

    def reload(self, clear=False):
        """Reloads the configuration."""
        log.info("Reloading config.")
        self.load(clear)

    def add_reload_hook(self, hook):
        """Registers a reload hook that's called when :meth:`load` is called.

        :param function hook: Hook to register.

        """
        self.reload_hooks.append(hook)

    def clear(self):
        """Clears all the cached configuration."""
        self.settings = {}


def reload(clear=False):
    """Shortcut method for calling reload."""
    Config().reload(clear)


def setting(name, default=None, allow_default=True):
    """Shortcut method for getting a setting descriptor.

    See :class:`pyconfig.Setting` for details.
    """
    return Setting(name, default, allow_default)


def get(name, default=None, allow_default=True):
    """Shortcut method for getting a setting value.

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
    """Shortcut method to change a setting."""
    Config().set(name, value)


def reload_hook(func):
    """Decorator for registering a reload hook."""
    Config().add_reload_hook(func)
    return func


def clear():
    """Shortcut for clearing all settings."""
    Config().clear()


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


class etcd(object):
    """
    Singleton for the etcd client and helper methods.

    """

    _self = dict(
        _init=False,
        client=None,
        module=None,
        watcher=None,
        _client_args=None,
    )

    def __init__(self, *args, **kwargs):
        # Use a borg singleton
        self.__dict__ = self._self

        # Get config settings
        self.prefix = kwargs.pop("prefix", env("PYCONFIG_ETCD_PREFIX", None))
        self.case_sensitive = get("pyconfig.case_sensitive", False)
        # Get inheritance settings
        # XXX shakefu: These might need env vars at some point
        self.inherit = kwargs.pop("inherit", True)
        self.inherit_key = kwargs.pop("inherit_key", "config.inherit")
        self.inherit_depth = kwargs.pop(
            "inherit_depth", env("PYCONFIG_INHERIT_DEPTH", 2)
        )

        # See if we should watch for changes
        self.watching = kwargs.pop("watch", env("PYCONFIG_ETCD_WATCH", False))

        # Only load the client the first time
        if not self._init:
            self._init = True
            self.init(*args, **kwargs)

    @property
    def configured(self):
        if not self.module or not self.client:
            return False
        return True

    def init(self, hosts=None, cacert=None, client_cert=None, client_key=None):
        """
        Handle creating the new etcd client instance and other business.

        Note that the etcd3 client (etcd v3 API) only supports connecting to
        a single server, so if multiple hosts are given, only the first one
        is used.

        :param hosts: Host string or list of hosts (default: `'127.0.0.1:2379'`)
        :param cacert: CA cert filename (optional)
        :param client_cert: Client cert filename (optional)
        :param client_key: Client key filename (optional)
        :type ca: str
        :type cert: str
        :type key: str

        """
        # Try to get the etcd module. etcd3 is optional, and it can fail to
        # import with errors other than ImportError -- notably a TypeError
        # when it's installed alongside protobuf >= 4 -- which must not break
        # pyconfig for apps that aren't using etcd
        try:
            import etcd3

            self.module = etcd3
        except ImportError:
            pass
        except Exception as err:
            log.warning(
                "etcd3 is installed but failed to import, so etcd support is "
                "disabled (etcd3 0.12 requires protobuf < 3.21): %s",
                err,
            )

        if not self.module:
            return

        self._parse_jetconfig()

        # Check env for overriding configuration or pyconfig setting
        hosts = env("PYCONFIG_ETCD_HOSTS", hosts)
        protocol = env("PYCONFIG_ETCD_PROTOCOL", None)
        cacert = env("PYCONFIG_ETCD_CACERT", cacert)
        client_cert = env("PYCONFIG_ETCD_CERT", client_cert)
        client_key = env("PYCONFIG_ETCD_KEY", client_key)

        # Parse auth string if there is one
        username = None
        password = None
        auth = env("PYCONFIG_ETCD_AUTH", None)
        if auth:
            auth = auth.split(":")
            auth.append("")
            username = auth[0]
            password = auth[1]

        # Create new etcd instance
        hosts = self._parse_hosts(hosts)
        if hosts is None:
            return

        # The etcd3 client connects to a single server, so if we were given
        # multiple hosts, we can only use the first one
        host, port = hosts[0]

        kw = {}

        # Add auth to constructor if we got it
        if username and password:
            kw["user"] = username
            kw["password"] = password
        elif username or password:
            log.warning(
                "PYCONFIG_ETCD_AUTH must be of the form 'username:password'; "
                "ignoring the incomplete credentials"
            )

        # The etcd3 client has no protocol argument, and only uses TLS when
        # it's given a CA cert -- a client cert and key without one are
        # silently ignored and the connection is made in plaintext. Since we
        # can't use TLS without a CA cert, warn when it was asked for.
        if cacert:
            kw["ca_cert"] = os.path.abspath(cacert)
            if client_cert and client_key:
                kw["cert_cert"] = os.path.abspath(client_cert)
                kw["cert_key"] = os.path.abspath(client_key)
            elif client_cert or client_key:
                # The etcd3 client requires the client cert and key together
                log.warning(
                    "Both a client cert and client key are required for "
                    "client authentication with the etcd3 client; ignoring "
                    "the incomplete certificate arguments"
                )
        elif client_cert or client_key or protocol == "https":
            log.warning(
                "TLS was requested (via PYCONFIG_ETCD_PROTOCOL, "
                "PYCONFIG_ETCD_CERT or PYCONFIG_ETCD_KEY), but the etcd3 "
                "client only uses TLS when a CA cert (PYCONFIG_ETCD_CACERT) "
                "is given; connecting without TLS and ignoring any client "
                "certificate"
            )

        self._client_args = (host, port, kw)
        self._connect()

    def _connect(self):
        """
        Create (or re-create) the etcd3 client from the arguments that
        :meth:`init` worked out.

        """
        host, port, kw = self._client_args
        client = self.module.client(host, port, **kw)

        if "user" in kw and "ca_cert" not in kw:
            # The etcd3 client sends its auth token both as gRPC call
            # credentials and as plain request metadata. gRPC refuses to send
            # call credentials over a plaintext channel, failing every
            # request, so drop them and rely on the metadata, which works
            # without TLS (as python-etcd's basic auth over HTTP did).
            client.call_credentials = None
            client.watcher._credentials = None

        self.client = client

    def _auth_expired(self, err):
        """
        Return whether `err` is etcd rejecting our (expired) auth token.

        """
        if not self._client_args or "user" not in self._client_args[2]:
            return False
        # grpc.RpcError has a code() method returning a grpc.StatusCode
        code = getattr(err, "code", None)
        if not callable(code):
            return False
        return getattr(code(), "name", None) == "UNAUTHENTICATED"

    def _fetch_prefix(self, prefix):
        """
        Return all the (value, metadata) pairs under `prefix`, refreshing the
        auth token if it has expired.

        """
        try:
            return list(self.client.get_prefix(prefix))
        except Exception as err:
            # The etcd3 client authenticates once when it's created, and
            # never refreshes its token, which etcd expires (after 5 minutes
            # of inactivity by default), so reconnect and retry once
            if not self._auth_expired(err):
                raise
            log.info("etcd auth token expired, reconnecting")
            self._connect()
            return list(self.client.get_prefix(prefix))

    def load(self, prefix=None, depth=None):
        """
        Return a dictionary of settings loaded from etcd.

        """
        prefix = prefix or self.prefix
        prefix = "/" + prefix.strip("/") + "/"
        if depth is None:
            depth = self.inherit_depth

        if not self.configured:
            log.debug("etcd not available")
            return

        if self.watching:
            log.info("Starting watcher for %r", prefix)
            self.start_watching()

        log.info("Loading from etcd %r", prefix)
        # Get all the key/value pairs under the prefix. The etcd3 client
        # returns an empty result when there's nothing there (its v2
        # equivalent raised EtcdKeyNotFound).
        result = self._fetch_prefix(prefix)
        if not result:
            log.info("No configuration found")
            return {}

        # Iterate over the returned keys from etcd
        update = {}
        for item in result:
            # The etcd3 client returns keys and values as bytes
            value, metadata = item
            key = metadata.key.decode("utf-8")
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            # Try to parse them as JSON strings, just in case it works
            try:
                value = pytool.json.from_json(value)
            except Exception:
                pass

            # Strip off the prefix that we're using (before lower-casing, so a
            # prefix with upper-case characters still matches)
            if key.startswith(prefix):
                key = key[len(prefix) :]

            # get_prefix is recursive, but etcd v2's get returned only the
            # direct children of the prefix, so skip keys in nested
            # "directories" (e.g. other environments under this one)
            if "/" in key:
                continue

            # Make the key lower-case if we're not case-sensitive
            if not self.case_sensitive:
                key = key.lower()

            # Store the key/value to update the config
            update[key] = value

        # Access cached settings directly to avoid recursion
        inherited = Config().settings.get(
            self.inherit_key, update.get(self.inherit_key, None)
        )
        if depth > 0 and inherited:
            log.info("    ... inheriting ...")
            inherited = self.load(inherited, depth - 1) or {}
            inherited.update(update)
            update = inherited

        return update

    def get_watcher(self):
        """
        Return a etcd watching generator which yields events as they happen.

        """
        if not self.watching:
            raise StopIteration()
        # watch_prefix returns a tuple of the events iterator and a cancel
        # function. We never cancel the watch, matching the old python-etcd
        # eternal_watch behavior.
        events, _ = self.client.watch_prefix(self.prefix)
        return events

    def start_watching(self):
        """Begins watching etcd for changes."""
        # Don't create a new watcher thread if we already have one running
        if self.watcher and self.watcher.is_alive():
            return

        # Create a new watcher thread and start it
        self.watcher = Watcher()
        self.watcher.start()

    def _parse_hosts(self, hosts):
        """
        Return hosts parsed into a tuple of tuples.

        :param hosts: String or list of hosts

        """
        # Default host
        if hosts is None:
            return

        # If it's a string, we allow comma separated strings
        if isinstance(hosts, str):
            # Split comma-separated list
            hosts = [host.strip() for host in hosts.split(",")]
            # Split host and port
            hosts = [host.split(":") for host in hosts]
            # Coerce ports to int
            hosts = [(host[0], int(host[1])) for host in hosts]

        # The tests (and python-etcd before us) expect a tuple of tuples
        return tuple(hosts)

    def _parse_jetconfig(self):
        """
        Undocumented cross-compatability functionality with jetconfig
        (https://github.com/shakefu/jetconfig) that is very sloppy.

        """
        conf = env("JETCONFIG_ETCD", None)

        if not conf:
            return

        from urllib.parse import urlparse

        auth = None
        port = None
        conf = conf.split(",").pop()
        entry = urlparse(conf)
        scheme = entry.scheme
        host = entry.netloc or entry.path  # Path is where it goes if there's no
        # scheme on the URL

        if "@" in host:
            auth, host = host.split("@")

        if ":" in host:
            host, port = host.split(":")

        if not port and scheme == "https":
            port = "443"

        if scheme:
            os.environ["PYCONFIG_ETCD_PROTOCOL"] = scheme

        if auth:
            os.environ["PYCONFIG_ETCD_AUTH"] = auth

        if port:
            host = host + ":" + port

        os.environ["PYCONFIG_ETCD_HOSTS"] = host

    # Getter and setter for the prefix to ensure it stays sync'd with the
    # config and stays normalized
    def _set_prefix(self, prefix):
        if not prefix:
            return
        set("pyconfig.etcd.prefix", "/" + prefix.strip("/") + "/")

    def _get_prefix(self):
        return "/" + (get("pyconfig.etcd.prefix") or "/config/").strip("/") + "/"

    prefix = property(_get_prefix, _set_prefix)


class Watcher(threading.Thread):
    """
    This is the threaded watching functionality. We have to have this be
    threaded since watching in the etcd3 client blocks while waiting for
    changes.

    """

    # Ensure this thread doesn't keep the server from exiting
    daemon = True

    # Do the actual watching
    def run(self):
        # Just end the thread if etcd is not actually configured
        if not etcd().configured:
            return

        for event in etcd().get_watcher():
            # We ignore all the events except puts, which change values
            if not isinstance(event, etcd().module.events.PutEvent):
                continue

            # Strip the prefix off the key name (etcd3 returns the key as
            # bytes)
            key = event.key.decode("utf-8")
            key = key.replace(etcd().prefix, "", 1)

            # Ignore keys in nested "directories", matching load()
            if "/" in key:
                continue

            # Try to coerce the value from JSON (etcd3 returns the value as
            # bytes)
            value = event.value
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            try:
                value = pytool.json.from_json(value)
            except Exception:
                pass

            # Set the value back to the config
            Config().set(key, value)


def env(key, default):
    """
    Helper to try to get a setting from the environment, or pyconfig, or
    finally use a provided default.

    """
    value = os.environ.get(key, None)
    if value is not None:
        log.info("    %s = %r", key.lower().replace("_", "."), value)
        return value

    key = key.lower().replace("_", ".")
    value = get(key)
    if value is not None:
        return value

    return default


def env_key(key, default):
    """
    Try to get `key` from the environment.

    This mutates `key` to replace dots with underscores and makes it all
    uppercase.

        my.database.host => MY_DATABASE_HOST

    """
    env = key.upper().replace(".", "_")
    return os.environ.get(env, default)
