pyconfig - Python-based singleton configuration
===============================================

This module provides python based configuration that is stored in a singleton
object to ensure consistency across your project.

Command Line
------------

Pyconfig has a command line utility that lets you inspect your project to find
all the configuration keys defined.

.. code-block::

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


