#!/usr/bin/python -S
"""
py_deps.py

Dynamically discover Python and C modules.  We import the main module and
inspect sys.modules before and after.  That is, we use the exact logic that the
Python interpreter does.

Usage:
  PYTHONPATH=... py_deps.py <main module>

IMPORTANT: Run this script with -S so that system libraries aren't found.
"""

import sys
OLD_MODULES = dict(sys.modules)  # Make a copy

import os  # Do it here so we don't mess up analysis


class Error(Exception):
  pass


def log(msg, *args):
  if args:
    msg = msg % args
  print >>sys.stderr, '\t', msg


def ImportMain(main_module, old_modules):
  """Yields (module name, absolute path) pairs."""

  log('Importing %r', main_module)
  try:
    __import__(main_module)
  except ImportError, e:
    log('Error importing %r with sys.path %r', main_module, sys.path)
    # TODO: print better error.
    raise

  new_modules = sys.modules
  log('After importing: %d modules', len(new_modules))

  for name in sorted(new_modules):
    if name in old_modules:
      continue  # exclude old modules

    module = new_modules[name]

    full_path = getattr(module, '__file__', None)

    # For some reason, there are entries like:
    # 'pan.core.os': None in sys.modules.  Here's a hack to get rid of them.
    if module is None:
      continue
    # Not sure why, but some stdlib modules don't have a __file__ attribute,
    # e.g. "gc", "marshal", "thread".  Doesn't matter for our purposes.
    if full_path is None:
      continue
    yield name, full_path


def PrintManifest(modules, py_out, c_out):
  """Print Python and C modules."""

  for module, full_path in modules:
    #print 'OLD', module, full_path
    num_parts = module.count('.') + 1
    i = len(full_path)
    # Do it once more in this case
    if full_path.endswith('/__init__.pyc') or \
       full_path.endswith('__init__.py'):
      i = full_path.rfind('/', 0, i)
    for _ in xrange(num_parts):
      i = full_path.rfind('/', 0, i)
    #print i, full_path[i+1:]
    rel_path = full_path[i + 1:]

    # Depending on whether it's cached, we get '.py' or '.pyc'.
    if full_path.endswith('.py'):
      print >>py_out, full_path, rel_path
      print >>py_out, full_path + 'c', rel_path + 'c'
    elif full_path.endswith('.pyc'):
      # .pyc file
      print >>py_out, full_path, rel_path
      print >>py_out, full_path[:-1], rel_path[:-1]
    else:
      # .so file
      print >>c_out, module, full_path


# TODO: Get rid of this?
def CreateOptionsParser():
  parser = optparse.OptionParser()
  return parser


def main(argv):
  """Returns an exit code."""

  #(opts, argv) = CreateOptionsParser().parse_args(argv)
  #if not argv:
  #  raise Error('No modules specified.')

  # Set an environment variable so dependencies in debug mode can be excluded.
  os.environ['_OVM_DEPS'] = '1'

  main_module = argv[0]
  prefix = argv[1]
  log('Before importing: %d modules', len(OLD_MODULES))

  py_out_path = prefix + '-py.txt'
  c_out_path = prefix + '-c.txt'

  modules = ImportMain(main_module, OLD_MODULES)

  with open(py_out_path, 'w') as py_out, open(c_out_path, 'w') as c_out:
    PrintManifest(modules, py_out, c_out)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv[1:]))
  except Error, e:
    print >> sys.stderr, 'py-deps:', e.args[0]
    sys.exit(1)
