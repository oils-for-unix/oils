#!/usr/bin/env python2
"""
builtin_def.py
"""
from __future__ import print_function

from typing import Dict, List, Optional, Any

# Special builtins can't be redefined by functions.  On the other hand, 'cd'
# CAN be redefined.
#
# http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_14
# https://www.gnu.org/software/bash/manual/html_node/Special-Builtins.html

_NORMAL_BUILTINS = [
    'read', 'echo', 'printf',

    'cd', 'pushd', 'popd', 'dirs', 'pwd',

    'source',  # note that . alias is special

    'umask', 'wait', 'jobs', 'fg', 'bg',

    'shopt',
    'complete', 'compgen', 'compopt', 'compadjust',

    'getopts',

    # introspection
    'command', 'type', 'hash', 'help', 'history',

    # Why are these duplicated?
    #'declare': builtin_e.DECLARE,
    #'typeset': builtin_e.TYPESET,

    'alias', 'unalias',

    # Oil only
    'push', 'append',
    'write', 'getline', 'json',
    'repr', 'use', 'opts',
]


class _Builtin(object):

  def __init__(self, index, name, enum_name=None, kind='normal'):
    # type: (int, str, Optional[str], str) -> None
    """
    kind: normal, special, assign
    """
    self.index = index
    self.name = name  # e.g. : or [
    self.enum_name = enum_name or name  # e.g. builtin_num::colon
    self.kind = kind


class _BuiltinDef(object):
  """
  NOTE: This isn't used anywhere!  We're registering nothing.

  We want to complete the flags to builtins.  So this is a mapping from name
  to arg spec.  There might not be any flags.
  """
  def __init__(self):
    # type: () -> None
    self.builtins = []  # type: List[_Builtin]
    self.index = 1  # start with 1

  def Add(self, *posargs, **kwargs):
    # type: (Any, Any) -> None
    # NOTE: *posargs works around flake8/pyflakes bug!
    self.builtins.append(_Builtin(self.index, *posargs, **kwargs))
    self.index += 1


def _Init(b):
  # type: (_BuiltinDef) -> None

  #
  # Special builtins
  #

  b.Add(':', enum_name='colon', kind='special')
  b.Add('.', enum_name='dot', kind='special')
  # Python keyword
  b.Add('exec', enum_name='exec_', kind='special')
  for name in [
      'eval', 'set', 'shift', 'times', 'trap', 'unset', 'builtin']:
    b.Add(name, kind='special')

  #
  # Assignment builtins.
  # Note: control flow aren't builtins in OSH: break continue return
  #

  for name in ["readonly", "local", "declare", "typeset"]:
    b.Add(name, kind='assign')
  b.Add('export', enum_name='export_', kind='assign')

  # Normal builtins

  # Slight variants
  b.Add('test')
  b.Add('[', enum_name='bracket')

  b.Add('true', enum_name='true_')
  b.Add('false', enum_name='false_')

  for name in _NORMAL_BUILTINS:
    b.Add(name)


_BUILTIN_DEF = _BuiltinDef()

_Init(_BUILTIN_DEF)


# Exposed in consts.py for completion
BUILTIN_NAMES = [b.name for b in _BUILTIN_DEF.builtins]


def All():
  # type: () -> List[_Builtin]
  return _BUILTIN_DEF.builtins


def BuiltinDict():
  # type: () -> Dict[str, _Builtin]
  """For the slow path in frontend/match.py."""
  return dict((b.name, b) for b in _BUILTIN_DEF.builtins)
