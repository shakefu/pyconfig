pyconfig - Python-based singleton configuration
===============================================

This module provides python based configuration that is stored in a singleton
object to ensure consistency across your project.

Code Examples
-------------

The most basic usage allows you to get, retrieve and modify values. Pyconfig's
singleton provides convenient accessor methods for these actions::

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
map to the current setting stored in the singleton::

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
will use this module namespace to update all configuration settings::

    # __file__ = "$PYTHONPATH/localconfig.py"
    from pyconfig import Namespace

    # Namespace objects allow you to use attribute assignment to create setting 
    # key names
    my = Namespace()
    my.setting = 'from_localconfig'
    my.nested = Namespace()
    my.nested.setting = 'also_from_localconfig'

With a ``localconfig`` on the ``PYTHONPATH``, it will be loaded before any settings
are read::

    >>> import pyconfig
    >>> pyconfig.get('my.setting')
    'from_localconfig'
    >>> pyconfig.get('my.nested.setting')
    'also_from_localconfig'

Pyconfig also allows you to create distutils plugins that are automatically
loaded. An example ``setup.py``::

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

An example distutils plugin configuration file::

    # __file__ = myconfig.py
    from pyconfig import Namespace

    def some_callable():
        print "This callable was called."
        print "You can execute any arbitrary code."

    setting = 'from_plugin'
    nested = Namespace()
    nested.setting = 'also_from_plugin'

Another example configuration file, without a base namespace::

    # __file__ = anyconfig.py
    from pyconfig import Namespace
    other = Namespace()
    other.setting = 'anyconfig_value'

Showing the plugin-specified settings::

    >>> import pyconfig
    >>> pyconfig.get('my.setting', 'default')
    This callable was called.
    You can execute any arbitrary code.
    'from_plugin'
    >>> pyconfig.get('my.nested.setting', 'default')
    'also_from_plugin'
    >>> pyconfig.get('other.setting', 'default')
    'anyconfig_value'

More fancy stuff::

    >>> # Reloading changes re-calls functions...
    >>> pyconfig.reload()
    This callable was called.
    You can execute any arbitrary code.
    >>> # This can be used to inject arbitrary code by changing a
    >>> # localconfig.py or plugin and reloading a config... especially
    >>> # when pyconfig.reload() is attached to a signal
    >>> import signal
    >>> signal.signal(signal.SIGUSR1, pyconfig.reload)


