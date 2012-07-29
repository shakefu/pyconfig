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
look on your `PYTHONPATH` for a module named `localconfig`, and if it exists, it
will use this module namespace to update all configuration settings::

    # __file__ = "$PYTHONPATH/localconfig.py"
    from pyconfig import Namespace

    # Namespace objects allow you to use attribute assignment to create setting 
    # key names
    my = Namespace()
    my.setting = 'from_localconfig'
    my.nested = Namespace()
    my.nested.setting = 'also_from_localconfig'

With a `localconfig` on the `PYTHONPATH`, it will be loaded before any settings
are read::

    >>> import pyconfig
    >>> pyconfig.get('my.setting')
    'from_localconfig'
    >>> pyconfig.get('my.nested.setting')
    'also_from_localconfig'

