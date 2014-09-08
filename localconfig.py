# This is for testing localconfig import bugs that happened with the Python 3
# compatibility patch. It'll be automatically included with tests and cause
# regressions if there are any.
from pyconfig import Namespace

conf = Namespace()
conf.local = True
