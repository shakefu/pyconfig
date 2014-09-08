pyconfig - Python-based singleton configuration
===============================================

This module provides python based configuration that is stored in a singleton
object to ensure consistency across your project.

.. contents::
   :local:

Command Line
------------

Pyconfig has a command line utility that lets you inspect your project to find
all the configuration keys defined.

::

   $ pyconfig -h
   usage: pyconfig [-h] [-f F | -m M] [-v] [-l] [-a | -k] [-n] [-s] [-c]

   Helper for working with pyconfigs

   optional arguments:
     -h, --help          show this help message and exit
     -f F, --filename F  parse an individual file or directory
     -m M, --module M    parse a package or module, recursively looking inside it
     -v, --view-call     show the actual pyconfig call made (default: show namespace)
     -l, --load-configs  query the currently set value for each key found
     -a, --all           show keys which don't have defaults set
     -k, --only-keys     show a list of discovered keys without values
     -n, --natural-sort  sort by filename and line (default: alphabetical by key)
     -s, --source        show source annotations (implies --natural-sort)
     -c, --color         toggle output colors (default: True)

**Example output**

.. code-block:: python

   $ pyconfig --file .
   humbledb.allow_explicit_request = True
   humbledb.auto_start_request = True
   humbledb.connection_pool = 300
   humbledb.tz_aware = True
   humbledb.use_greenlets = False
   humbledb.write_concern = 1

   $ pyconfig --view-call --file .
   pyconfig.get('humbledb.allow_explicit_request', True)
   pyconfig.setting('humbledb.auto_start_request', True)
   pyconfig.setting('humbledb.connection_pool', 300)
   pyconfig.setting('humbledb.tz_aware', True)
   pyconfig.setting('humbledb.use_greenlets', False)
   pyconfig.setting('humbledb.write_concern', 1)

   $ pyconfig --source --file .
   # ./humbledb/mongo.py, line 98
   humbledb.allow_explicit_request = True
   # ./humbledb/mongo.py, line 178
   humbledb.connection_pool = 300
   # ./humbledb/mongo.py, line 181
   humbledb.auto_start_request = True
   # ./humbledb/mongo.py, line 185
   humbledb.use_greenlets = False
   # ./humbledb/mongo.py, line 188
   humbledb.tz_aware = True
   # ./humbledb/mongo.py, line 191
   humbledb.write_concern = 1


Code Examples
-------------

The most basic usage allows you to get, retrieve and modify values. Pyconfig's
singleton provides convenient accessor methods for these actions:

.. code-block:: python

    >>> import pyconfig
    >>> pyconfig.get('my.setting', 'default')
    'default'
    >>> pyconfig.set('my.setting', 'new')
    >>> pyconfig.get('my.setting', 'default')
    'new'
    >>> pyconfig.reload(clear=True)
    >>> pyconfig.get('my.setting', 'default')
    'default'

Pyconfig also provides shortcuts for giving classes property descriptors which
map to the current setting stored in the singleton:

.. code-block:: python

    >>> import pyconfig
    >>> class MyClass(object):
    ...     my_setting = pyconfig.setting('my.setting', 'default')
    ...
    >>> MyClass.my_setting
    'default'
    >>> MyClass().my_setting
    'default'
    >>> pyconfig.set('my.setting', "Hello World!")
    >>> MyClass.my_setting
    'Hello World!'
    >>> MyClass().my_setting
    'Hello World!'
    >>> pyconfig.reload(clear=True)
    >>> MyClass.my_setting
    'default'

Pyconfig allows you to override settings via a python configuration file, that
defines its configuration keys as a module namespace. By default, Pyconfig will
look on your ``PYTHONPATH`` for a module named ``localconfig``, and if it exists, it
will use this module namespace to update all configuration settings:

.. code-block:: python

    # __file__ = "$PYTHONPATH/localconfig.py"
    from pyconfig import Namespace

    # Namespace objects allow you to use attribute assignment to create setting
    # key names
    my = Namespace()
    my.setting = 'from_localconfig'
    # Namespace objects implicitly return new nested Namespaces when accessing
    # attributes that don't exist
    my.nested.setting = 'also_from_localconfig'

With a ``localconfig`` on the ``PYTHONPATH``, it will be loaded before any settings
are read:

.. code-block:: python

    >>> import pyconfig
    >>> pyconfig.get('my.setting')
    'from_localconfig'
    >>> pyconfig.get('my.nested.setting')
    'also_from_localconfig'

Pyconfig also allows you to create distutils plugins that are automatically
loaded. An example ``setup.py``:

.. code-block:: python

    # __file__ = setup.py
    from setuptools import setup

    setup(
            name='pytest',
            version='0.1.0-dev',
            py_modules=['myconfig', 'anyconfig'],
            entry_points={
                # The "my" in "my =" indicates a base namespace to use for
                # the contained configuration. If you do not wish a base
                # namespace, use "any"
                'pyconfig':[
                      'my = myconfig',
                      'any = anyconfig',
                      ],
                },
            )

An example distutils plugin configuration file:

.. code-block:: python

    # __file__ = myconfig.py
    from pyconfig import Namespace

    def some_callable():
        print "This callable was called."
        print "You can execute any arbitrary code."

    setting = 'from_plugin'
    nested = Namespace()
    nested.setting = 'also_from_plugin'

Another example configuration file, without a base namespace:

.. code-block:: python

    # __file__ = anyconfig.py
    from pyconfig import Namespace
    other = Namespace()
    other.setting = 'anyconfig_value'

Showing the plugin-specified settings:

.. code-block:: python

    >>> import pyconfig
    >>> pyconfig.get('my.setting', 'default')
    This callable was called.
    You can execute any arbitrary code.
    'from_plugin'
    >>> pyconfig.get('my.nested.setting', 'default')
    'also_from_plugin'
    >>> pyconfig.get('other.setting', 'default')
    'anyconfig_value'

More fancy stuff:

.. code-block:: python

    >>> # Reloading changes re-calls functions...
    >>> pyconfig.reload()
    This callable was called.
    You can execute any arbitrary code.
    >>> # This can be used to inject arbitrary code by changing a
    >>> # localconfig.py or plugin and reloading a config... especially
    >>> # when pyconfig.reload() is attached to a signal
    >>> import signal
    >>> signal.signal(signal.SIGUSR1, pyconfig.reload)

Pyconfig provides a ``@reload_hook`` decorator that allows you to register
functions or methods to be called when the configuration is reloaded:

.. code-block:: python

      >>> import pyconfig
      >>> @pyconfig.reload_hook
      ... def reload():
      ...     print "Do something here."
      ...
      >>> pyconfig.reload()
      Do something here.

**Warning**: It should not be used to register large numbers of functions (e.g.
registering a bound method in a class's ``__init__`` method), since there is no
way to un-register a hook and it will cause a memory leak, since a bound method
maintains a strong reference to the bound instance.

**Note**: Because the reload hooks are called without arguments, it will not
work with unbound methods or classmethods.


Changes
-------

This section contains descriptions of changes in each new version.

2.1.2-2.1.3
^^^^^^^^^^^

* Package clean up and fixing README to work on PyPI again.

2.1.1
^^^^^

* Fix bug that would break on Python 2.6 and 2.7 when using a localconfig.py.

2.1.0
^^^^^

* Pyconfig now works on Python 3, thanks to
  `hfalcic <https://github.com/hfalcic>`_!

2.0.0
^^^^^
* Pyconfig now has the ability to show you what config keys are defined in a
  directory.

1.2.0
^^^^^

* No longer uses Python 2.7 ``format()``. Should work on 2.6 and maybe earlier.

1.1.2
^^^^^

* Move version string into ``pyconfig.__version__``

1.1.1
^^^^^

* Fix bug with setup.py that prevented installation

1.1.0
^^^^^

* Allow for implicitly nesting Namespaces when accessing attributes that are
  undefined

Contributors
------------

* `shakefu <http://github.com/shakefu>`_ - Creator and maintainer
* `hfalcic <https://github.com/hfalcic>`_ - Python 3 compatability

