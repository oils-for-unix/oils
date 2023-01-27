"""
pyutil.py: Code that's only needed in Python.  C++ will use other mechanisms.
"""
from __future__ import print_function

import sys
import zipimport  # NOT the zipfile module.

from mycpp import mylib
from pgen2 import grammar
from pylib import os_path

import posix_ as posix

from typing import List, Union, TYPE_CHECKING
if TYPE_CHECKING:
  from mycpp import mylib


# Copied from 'string' module
_PUNCT = """!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""


def IsValidCharEscape(ch):
  # type: (str) -> bool
  """Is this a valid character escape when unquoted?"""
  # These punctuation chars never needs to be escaped.  (Note that _ is a
  # keyword sometimes.)
  if ch == '/' or ch == '.' or ch == '-':
    return False

  if ch == ' ':  # foo\ bar is idiomatic
    return True

  # Borderline: ^ and %.  But ^ is used for history?
  # ! is an operator.  And used for history.

  # What about ^(...) or %(...) or /(...) .(1+2), etc.?  

  return ch in _PUNCT  # like ispunct() in C


def ChArrayToString(ch_array):
  # type: (List[int]) -> str
  """We avoid allocating 1 byte string objects in the C++ implementation.

  'ch' is short for an integer that represents a character.
  """
  return ''.join(chr(ch) for ch in ch_array)


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


def strerror(e):
  # type: (Union[IOError, OSError]) -> str
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


def IsAppBundle():
  # type: () -> bool
  """Are we running inside Oil's patched version of CPython?

  As opposed to a "stock" Python interpreter.
  """
  # Ovm_Main in main.c sets this.
  return posix.environ.get('_OVM_IS_BUNDLE') == '1'


_loader = None  # type: _ResourceLoader

def GetResourceLoader():
  # type: () -> _ResourceLoader
  global _loader
  if _loader:
    return _loader

  if IsAppBundle():
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


# This was useful for debugging.
def ShowFdState():
  # type: () -> None
  import subprocess
  import posix_ as posix
  subprocess.call(['ls', '-l', '/proc/%d/fd' % posix.getpid()])
