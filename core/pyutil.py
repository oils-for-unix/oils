"""
pyutil.py: Code that's only needed in Python.  C++ will use other mechanisms.
"""
from __future__ import print_function

import sys
import time
import zipimport  # NOT the zipfile module.

from mycpp import mylib
from pgen2 import grammar
from pylib import os_path

import posix_ as posix

from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
  from mycpp import mylib


def BackslashEscape(s, meta_chars):
  # type: (str, str) -> str
  """Escaped certain characters with backslashes.

  Used for shell syntax (i.e. quoting completed filenames), globs, and EREs.
  """
  escaped = []
  for c in s:
    if c in meta_chars:
      escaped.append('\\')
    escaped.append(c)
  return ''.join(escaped)


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


def LoadOilGrammar(loader):
  # type: (_ResourceLoader) -> grammar.Grammar
  oil_grammar = grammar.Grammar()
  contents = loader.Get('_devbuild/gen/grammar.marshal')
  oil_grammar.loads(contents)
  return oil_grammar


class _ResourceLoader(object):

  def Get(self, rel_path):
    # type: (str) -> str
    raise NotImplementedError()


class _FileResourceLoader(_ResourceLoader):
  """Open resources relative to argv[0]."""

  def __init__(self, root_dir):
    # type: (str) -> None
    self.root_dir = root_dir

  def Get(self, rel_path):
    # type: (str) -> str
    with open(os_path.join(self.root_dir, rel_path)) as f:
      contents = f.read()
    return contents


class _ZipResourceLoader(_ResourceLoader):
  """Open resources INSIDE argv[0] as a zip file."""

  def __init__(self, argv0):
    # type: (str) -> None
    self.z = zipimport.zipimporter(argv0)

  def Get(self, rel_path):
    # type: (str) -> str
    return self.z.get_data(rel_path)


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


def GetVersion(loader):
  # type: (_ResourceLoader) -> str
  contents = loader.Get('oil-version.txt')
  version_str, _ = mylib.split_once(contents, '\n')
  return version_str


def ShowAppVersion(app_name, loader):
  # type: (str, _ResourceLoader) -> None
  """Show version and platform information."""
  try:
    contents = loader.Get('release-date.txt')
    release_date, _ = mylib.split_once(contents, '\n')
  except IOError:
    release_date = '-'  # in dev tree

  try:
    contents = loader.Get('pyc-version.txt')
    pyc_version, _ = mylib.split_once(contents, '\n')
  except IOError:
    pyc_version = '-'  # in dev tree

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

  version_str = GetVersion(loader)

  # What C functions do these come from?
  print('%s version %s' % (app_name, version_str))
  print('Release Date: %s' % release_date)
  print('Arch: %s' % machine)
  print('OS: %s' % system)
  print('Platform: %s' % platform_version)
  print('Compiler: %s' % py_compiler)
  print('Interpreter: %s' % py_impl)
  print('Interpreter version: %s' % py_version)
  print('Bytecode: %s' % pyc_version)


def CopyFile(in_path, out_path):
  # type: (str, str) -> None

  # This might be superstition, but we want to let the value stabilize
  # after parsing.  bash -c 'cat /proc/$$/status' gives different results
  # with a sleep.
  time.sleep(0.001)

  with open(in_path) as f2, open(out_path, 'w') as f3:
    contents = f2.read()
    f3.write(contents)
    stderr_line('Wrote %s to %s', in_path, out_path)


# This was useful for debugging.
def ShowFdState():
  # type: () -> None
  import subprocess
  import posix_ as posix
  subprocess.call(['ls', '-l', '/proc/%d/fd' % posix.getpid()])
