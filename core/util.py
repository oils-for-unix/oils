#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
util.py - Common infrastructure.
"""
from __future__ import print_function

import cStringIO
import posix
import pwd  # TODO: Move this dependency to Oil?
import sys
import zipimport  # NOT the zipfile module.

from _devbuild.gen.syntax_asdl import token, word_part_t, word_t
from asdl import const
from pylib import os_path

from typing import IO, NoReturn, Any

Buffer = cStringIO.StringIO  # used by asdl/format.py


# This was derived from bash --norc -c 'argv "$COMP_WORDBREAKS".
# Python overwrites this to something Python-specific in Modules/readline.c, so
# we have to set it back!
# Used in both core/competion.py and osh/state.py
READLINE_DELIMS = ' \t\n"\'><=;|&(:'


class HistoryError(Exception):

  def __init__(self, msg, *args):
    # type: (str, *Any) -> None
    Exception.__init__(self)
    self.msg = msg
    self.args = args

  def UserErrorString(self):
    # type: () -> str
    out = 'history: '
    if self.args:
      out += self.msg % self.args
    else:
      out += self.msg
    return out


class _ErrorWithLocation(Exception):
  """A parse error that can be formatted.

  Formatting is in ui.PrintError.
  """
  def __init__(self, msg, *args, **kwargs):
    # type: (str, *Any, **Any) -> None
    Exception.__init__(self)
    self.msg = msg
    self.args = args
    # NOTE: We use a kwargs dict because Python 2 doesn't have keyword-only
    # args.
    self.span_id = kwargs.pop('span_id', const.NO_INTEGER)  # type: int
    self.token = kwargs.pop('token', None)  # type: token
    self.part = kwargs.pop('part', None)  # type: word_part_t
    self.word = kwargs.pop('word', None)  # type: word_t
    self.exit_status = kwargs.pop('status', None)  # type: int
    if kwargs:
      raise AssertionError('Invalid keyword args %s' % kwargs)

  def __repr__(self):
    # type: () -> str
    return '<%s %s %r %r %s>' % (
        self.msg, self.args, self.token, self.word, self.exit_status)

  def __str__(self):
    # type: () -> str
    # The default doesn't work very well?
    return repr(self)

  def UserErrorString(self):
    # type: () -> str
    return self.msg % self.args


class ParseError(_ErrorWithLocation):
  """Used in the parsers.

  TODO:
  - This could just be FatalError?
  - You might want to catch this and add multiple locations?
    try:
      foo
    except ParseError as e:
      e.AddErrorInfo('hi', token=t)
      raise
  """
  pass


class FatalRuntimeError(_ErrorWithLocation):
  """Used in the evaluators.

  Also used in test builtin for invalid argument.
  """
  pass


class InvalidSlice(FatalRuntimeError):
  """Whether this is fatal depends on set -o strict-word-eval.
  """
  pass


class InvalidUtf8(FatalRuntimeError):
  """Whether this is fatal depends on set -o strict-word-eval.
  """
  pass


class ErrExitFailure(FatalRuntimeError):
  """For set -e.

  Travels between WordEvaluator and Executor.
  """
  pass


def p_die(msg, *args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for parse errors."""
  raise ParseError(msg, *args, **kwargs)


def e_die(msg, *args, **kwargs):
  # type: (str, *Any, **Any) -> NoReturn
  """Convenience wrapper for runtime errors."""
  raise FatalRuntimeError(msg, *args, **kwargs)


def log(msg, *args):
  # type: (str, *Any) -> None
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def warn(msg, *args):
  # type: (str, *Any) -> None
  if args:
    msg = msg % args
  print('osh warning: ' + msg, file=sys.stderr)


# NOTE: This should say 'oilc error' or 'oil error', instead of 'osh error' in
# some cases.
def error(msg, *args):
  # type: (str, *Any) -> None
  if args:
    msg = msg % args
  print('osh error: ' + msg, file=sys.stderr)


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


def GetHomeDir():
  # type: () -> str
  """Get the user's home directory from the /etc/passwd.

  Used by $HOME initialization in osh/state.py.  Tilde expansion and readline
  initialization use mem.GetVar('HOME').
  """
  uid = posix.getuid()
  try:
    e = pwd.getpwuid(uid)
  except KeyError:
    return None
  else:
    return e.pw_dir


class _ResourceLoader(object):

  def open(self, rel_path):
    # type: (str) -> IO[str]
    raise NotImplementedError


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
    # NOTE: This assumes all unit tests are one directory deep, e.g.
    # core/util_test.py.
    bin_dir = os_path.dirname(os_path.abspath(sys.argv[0]))  # ~/git/oil/bin
    root_dir = os_path.join(bin_dir, '..')  # ~/git/oil/osh
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


# This was useful for debugging.
def ShowFdState():
  # type: () -> None
  import subprocess
  subprocess.call(['ls', '-l', '/proc/%d/fd' % posix.getpid()])


class DebugFile(object):
  def __init__(self, f):
    # type: (IO[str]) -> None
    self.f = f

  def log(self, msg, *args):
    # type: (str, *Any) -> None
    if args:
      msg = msg % args
    self.f.write(msg)
    self.f.write('\n')
    self.f.flush()  # need to see it interacitvely

  # These two methods are for node.PrettyPrint()
  def write(self, s):
    # type: (str) -> None
    self.f.write(s)

  def isatty(self):
    # type: () -> bool
    return self.f.isatty()


class NullDebugFile(DebugFile):

  def __init__(self):
    # type: () -> None
    pass

  def log(self, msg, *args):
    # type: (str, *Any) -> None
    pass

  def write(self, s):
    # type: (str) -> None
    pass

  def isatty(self):
    # type: () -> bool
    return False
