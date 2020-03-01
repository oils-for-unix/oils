"""
pyutil.py: Code that's only needed in Python.  C++ will use other mechanisms.
"""
from __future__ import print_function

import cStringIO
import sys
import zipimport  # NOT the zipfile module.

from pylib import os_path

import posix_ as posix

from typing import IO, NoReturn, Any


# TODO: Move log, p_die, and e_die here too.  They have different
# implementations in C++.

def e_usage(msg, *pos_args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for arg parsing / validation errors.

  Usually causes a builtin to fail with status 2, but the script can continue
  if 'set +o errexit'.  Main programs like bin/oil also use this.
  """
  from frontend import args
  # TODO: Should be error.Usage
  raise args.UsageError(msg, *pos_args, **kwargs)


# TODO: Remove ui.Stderr in favor of this
def stderr_line(msg, *args):
  # type: (str, *Any) -> None
  """Print a message to stderr for the user.

  This should be used sparingly, since it doesn't have any location info.
  Right now we use it to print fatal I/O errors that were only caught at the
  top level.
  """
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


# Note: we have to hide the 'errno' field under pyutil, because it doesn't
# translate well.  'errno' is a macro.
# Also Python 2 forces us to have both methods.

def strerror_IO(e):
  # type: (IOError) -> str
  return posix.strerror(e.errno)

def strerror_OS(e):
  # type: (OSError) -> str
  return posix.strerror(e.errno)


class _ResourceLoader(object):

  def open(self, rel_path):
    # type: (str) -> IO[str]
    raise NotImplementedError()


class _FileResourceLoader(_ResourceLoader):
  """Open resources relative to argv[0]."""

  def __init__(self, root_dir):
    # type: (str) -> None
    self.root_dir = root_dir

  def open(self, rel_path):
    # type: (str) -> IO[str]
    return open(os_path.join(self.root_dir, rel_path))


class _ZipResourceLoader(_ResourceLoader):
  """Open resources INSIDE argv[0] as a zip file."""

  def __init__(self, argv0):
    # type: (str) -> None
    self.z = zipimport.zipimporter(argv0)

  def open(self, rel_path):
    # type: (str) -> IO[str]
    contents = self.z.get_data(rel_path)
    return cStringIO.StringIO(contents)


_loader = None  # type: _ResourceLoader

def GetResourceLoader():
  # type: () -> _ResourceLoader
  global _loader
  if _loader:
    return _loader

  # Ovm_Main in main.c sets this.
  if posix.environ.get('_OVM_IS_BUNDLE') == '1':
    ovm_path = posix.environ.get('_OVM_PATH')
    _loader = _ZipResourceLoader(ovm_path)

    # Now clear them so we don't pollute the environment.  In Python, this
    # calls unsetenv().
    del posix.environ['_OVM_IS_BUNDLE']
    del posix.environ['_OVM_PATH']

  elif posix.environ.get('_OVM_RESOURCE_ROOT'):  # Unit tests set this
    root_dir = posix.environ.get('_OVM_RESOURCE_ROOT')
    _loader = _FileResourceLoader(root_dir)

  else:
    # Find resources relative to the binary, e.g.
    # ~/git/oilshell/oil/bin/oil.py.  But it also assumes that all unit tests
    # that use resources are are one directory deep, e.g. core/util_test.py.
    bin_dir = os_path.dirname(os_path.abspath(sys.argv[0]))
    root_dir = os_path.join(bin_dir, '..')  # ~/git/oilshell/oil
    _loader = _FileResourceLoader(root_dir)

  return _loader


def ShowAppVersion(app_name):
  # type: (str) -> None
  """For Oil and OPy."""
  loader = GetResourceLoader()
  f = loader.open('oil-version.txt')
  version = f.readline().strip()
  f.close()

  try:
    f = loader.open('release-date.txt')
  except IOError:
    release_date = '-'  # in dev tree
  else:
    release_date = f.readline().strip()
  finally:
    f.close()

  try:
    f = loader.open('pyc-version.txt')
  except IOError:
    pyc_version = '-'  # in dev tree
  else:
    pyc_version = f.readline().strip()
  finally:
    f.close()

  # node is like 'hostname'
  # release is the kernel version
  system, unused_node, unused_release, platform_version, machine = posix.uname()

  # The platform.py module has a big regex that parses sys.version, but we
  # don't want to depend on regular expressions.  So we will do our own parsing
  # here.
  version_line, py_compiler = sys.version.splitlines()

  # Pick off the first part of '2.7.12 (default, ...)'
  py_version = version_line.split()[0]

  assert py_compiler.startswith('['), py_compiler
  assert py_compiler.endswith(']'), py_compiler
  py_compiler = py_compiler[1:-1]

  # We removed sys.executable from sysmodule.c.
  py_impl = 'CPython' if hasattr(sys, 'executable') else 'OVM'

  # What C functions do these come from?
  print('%s version %s' % (app_name, version))
  print('Release Date: %s' % release_date)
  print('Arch: %s' % machine)
  print('OS: %s' % system)
  print('Platform: %s' % platform_version)
  print('Compiler: %s' % py_compiler)
  print('Interpreter: %s' % py_impl)
  print('Interpreter version: %s' % py_version)
  print('Bytecode: %s' % pyc_version)

