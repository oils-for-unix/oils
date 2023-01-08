"""
runtime.py
"""
from __future__ import print_function

import cStringIO
import sys

from pylib import collections_
try:
  import posix_ as posix
except ImportError:
  # Hack for tangled dependencies.  Many tools import core.pyerror.log, which
  # ends up importing mylib.PYTHON
  import os
  posix = os

from typing import Tuple, Any

# For conditional translation
CPP = False
PYTHON = True

STDIN_FILENO = 0


def MaybeCollect():
  # type: () -> None
  pass


def StrFromC(s):
  """Hack to translate const char* s to Str * in C++."""
  return s


def NewDict():
  """Make dictionaries ordered in Python, e.g. for JSON.
  
  In C++, our Dict implementation should be ordered.
  """
  return collections_.OrderedDict()


def log(msg, *args):
  # type: (str, *Any) -> None
  """Only for test code"""
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def p_die(msg, *args):
  """Only for test code, like mycpp/examples/varargs"""
  # type: (str, *Any) -> None
  raise RuntimeError(msg % args)


BufWriter = cStringIO.StringIO

BufLineReader = cStringIO.StringIO


class File(object):
  """Custom file wrapper for Unix I/O like write() read()
  
  Not C I/O like fwrite() fread().  There should be no flush().
  """
  def __init__(self, fd):
    # type: (int) -> None
    self.fd = fd

  def write(self, s):
    # type: (str) -> None
    posix.write(self.fd, s)

  def writeln(self, s):
    # type: (str) -> None
    """
    Write a line.  The name is consistent with JavaScript writeln() and Rust.

    TODO: The Oil interpreter shouldn't use print() anywhere.  Instead it can
    use gStdout.writeln()
    """
    posix.write(self.fd, s)
    posix.write(self.fd, '\n')


# TODO: Can return File(1)
def Stdout():
  return sys.stdout


# TODO: Can return File(2)
def Stderr():
  return sys.stderr


def Stdin():
  return sys.stdin


# mylib.open is the builtin, but we have different static types mylib.pyi
open = open


class switch(object):
  """A ContextManager that translates to a C switch statement."""

  def __init__(self, value):
    # type: (int) -> None
    self.value = value

  def __enter__(self):
    # type: () -> switch
    return self

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> bool
    return False  # Allows a traceback to occur

  def __call__(self, *cases):
    # type: (*Any) -> bool
    return self.value in cases


class tagswitch(object):
  """A ContextManager that translates to switch statement over ASDL types."""

  def __init__(self, node):
    # type: (int) -> None
    self.tag = node.tag

  def __enter__(self):
    # type: () -> tagswitch
    return self

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> bool
    return False  # Allows a traceback to occur

  def __call__(self, *cases):
    # type: (*Any) -> bool
    return self.tag in cases


def iteritems(d):
  """Make translation a bit easier."""
  return d.iteritems()


def split_once(s, delim):
  # type: (str, str) -> Tuple[str, Optional[str]]
  """Easier to call than split(s, 1) because of tuple unpacking.
  """
  parts = s.split(delim, 1)
  if len(parts) == 1:
    no_str = None  # type: Optional[str]
    return s, no_str
  else:
    return parts[0], parts[1]


def hex_lower(i):
  # type: (int) -> str
  return '%x' % i


def hex_upper(i):
  # type: (int) -> str
  return '%X' % i


def octal(i):
  # type: (int) -> str
  return '%o' % i


def dict_erase(d, key):
  # type: (Dict[Any, Any], Any) -> None
  """
  Ensure that a key isn't in the Dict d.  This makes C++ translation easier.
  """
  try:
    del d[key]
  except KeyError:
    pass


def str_cmp(s1, s2):
  # type: (str, str) -> int
  """
  """
  if s1 == s2:
    return 0
  if s1 < s2:
    return -1
  else:
    return 1
