import os
import ast
import sys
import _ast
import runpy
import argparse


def main():
    """
    Main script for `pyconfig` command.

    """
    parser = argparse.ArgumentParser(description="Helper for working with "
            "pyconfigs")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-f', '--filename',
            help="Parse an individual file or directory",
            metavar='F')
    group.add_argument('-m', '--module',
            help="Parse a package or module, recursively looking inside it",
            metavar='M')
    args = parser.parse_args()

    # We'll use this later since the module argument might load a filename
    filename = args.filename

    if args.module:
        module = _get_module_filename(args.module)
        if not module:
            _error("Could not load module or package: %r", args.module)
        elif isinstance(module, Unparseable):
            _error("Could not determine module source: %r", args.module)

        if os.path.isfile(module):
            filename = module
        elif os.path.isdir(module):
            # TODO(shakefu): Handle directory walking to find all subfiles
            print "Found package:", module
        else:
            # XXX(shakefu): This is an error of some sort, maybe symlinks?
            # Probably need some thorough testing
            _error("Could not determine file type: %r", args.module)

    if filename:
        if not os.path.isfile(filename):
            _error("Not a file: %r", filename)

        calls = _parse_file(filename)
        if not calls:
            # XXX(shakefu): Probably want to change this to not be an error and
            # just be a normal fail (e.g. command runs, no output).
            _error("No pyconfig calls.")

        # XXX(shakefu): This is temporary output for testing
        for method, key, default in sorted(calls, key=lambda c: c[1]):
            default = ', '.join(repr(v) for v in default)
            default = ', ' + default if default else ''
            print "pyconfig.%s(%r%s)" % (method, key, default)


def _error(msg, *args):
    """
    Print an error message and exit.

    :param msg: A message to print
    :type msg: str

    """
    print >>sys.stderr, msg % args
    sys.exit(1)


def _get_module_filename(module):
    """
    Return the filename of `module` if it can be imported.

    If `module` is a package, its directory will be returned.

    If it cannot be imported ``None`` is returned.

    If the ``__file__`` attribute is missing, or the module or package is a
    compiled egg, then an :class:`Unparsable` instance is returned, since the
    source can't be retrieved.

    :param module: A module name, such as ``'test.test_config'``
    :type module: str

    """
    # Split up the module and its containing package, if it has one
    module = module.split('.')
    package = '.'.join(module[:-1])
    module = module[-1]

    try:
        if not package:
            # We aren't accessing a module within a package, but rather a top
            # level package, so it's a straight up import
            module = __import__(module)
        else:
            # Import the package containing our desired module
            package = __import__(package, fromlist=[module])
            # Get the module from that package
            module = getattr(package, module, None)

        filename = getattr(module, '__file__', None)
        if not filename:
            # No filename? Nothing to do here
            return Unparseable()

        # If we get a .pyc, strip the c to get .py so we can parse the source
        if filename.endswith('.pyc'):
            filename = filename[:-1]
            if not os.path.exists(filename) and os.path.isfile(filename):
                # If there's only a .pyc and no .py it's a compile package or
                # egg and we can't get at the source for parsing
                return Unparseable()
        # If we have a package, we want the directory not the init file
        if filename.endswith('__init__.py'):
            filename = filename[:-11]

        # Yey, we found it
        return filename
    except ImportError:
        # Definitely not a valid module or package
        return


class Unparseable(object):
    """
    This class represents an argument to a pyconfig setting that couldn't be
    easily parsed - e.g. was not a basic type.

    """
    def __repr__(self):
        return '<unparsed>'


def _parse_file(filename):
    """
    Return XXX from parsing `filename`.

    :param filename: A file to parse
    :type filename: str

    """
    # This is a mapping of string names which are Python values
    name_map = {
            'True': True,
            'False': False,
            'None': None,
            }

    with open(filename, 'r') as source:
        source = source.read()

    pyconfig_calls = []
    nodes = ast.parse(source, filename=filename)
    for call in ast.walk(nodes):
        if not isinstance(call, _ast.Call):
            # Skip any node that isn't a Call
            continue

        func = call.func
        if not isinstance(call.func, _ast.Attribute):
            # We're looking for calls to pyconfig.*, so the function has to be
            # an Attribute node, otherwise skip it
            continue

        if getattr(func.value, 'id', None) != 'pyconfig':
            # If the Attribute value isn't a Name (doesn't have an `id`) or it
            # isn't 'pyconfig', then we skip
            continue

        if func.attr not in ['get', 'set', 'setting']:
            # If the Attribute attr isn't one of the pyconfig API methods, then
            # we skip
            continue

        # Now we parse the call arguments as best we can
        args = []
        for arg in call.args:
            # Grab the easy to parse values
            if isinstance(arg, _ast.Str):
                args.append(arg.s)
            elif isinstance(arg, _ast.Num):
                args.append(arg.n)
            elif isinstance(arg, _ast.Name):
                args.append(name_map.get(arg.id, arg.id))
            else:
                # Everything else we don't bother with
                args.append(Unparseable())

        # XXX(shakefu): We may want functionality from this that gives source
        # hinting especially for unparsable statements, but for now we return a
        # list of tuples
        pyconfig_calls.append((func.attr, args[0], args[1:]))

    return pyconfig_calls

