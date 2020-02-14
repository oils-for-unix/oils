#!/usr/bin/env python2
"""
builtin_def.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import builtin_e, builtin_t

from typing import Dict, List, Any, TYPE_CHECKING
if TYPE_CHECKING:
  from frontend import args  # circular build dependency

# Special builtins can't be redefined by functions.  On the other hand, 'cd'
# CAN be redefined.
#
# http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_14
# https://www.gnu.org/software/bash/manual/html_node/Special-Builtins.html

_SPECIAL_BUILTINS = {
    ":": builtin_e.COLON,
    ".": builtin_e.DOT,
    "eval": builtin_e.EVAL,
    "exec": builtin_e.EXEC,

    "set": builtin_e.SET,
    "shift": builtin_e.SHIFT,
    "times": builtin_e.TIMES,
    "trap": builtin_e.TRAP,
    "unset": builtin_e.UNSET,

    "builtin": builtin_e.BUILTIN,

    # Not treated as builtins by OSH.  TODO: Need to auto-complete these
    # break continue return
}

_SPECIAL_ASSIGN_BUILTINS = {
    # May be a builtin or an assignment
    "readonly": builtin_e.READONLY,
    "local": builtin_e.LOCAL,
    "declare": builtin_e.DECLARE,
    "typeset": builtin_e.TYPESET,
    "export": builtin_e.EXPORT,
}

_NORMAL_BUILTINS = {
    "read": builtin_e.READ,
    "echo": builtin_e.ECHO,
    "printf": builtin_e.PRINTF,

    "cd": builtin_e.CD,
    "pushd": builtin_e.PUSHD,
    "popd": builtin_e.POPD,
    "dirs": builtin_e.DIRS,
    "pwd": builtin_e.PWD,

    "source": builtin_e.SOURCE,  # note that . alias is special

    "umask": builtin_e.UMASK,
    "wait": builtin_e.WAIT,
    "jobs": builtin_e.JOBS,
    "fg": builtin_e.FG,
    "bg": builtin_e.BG,

    "shopt": builtin_e.SHOPT,
    "complete": builtin_e.COMPLETE,
    "compgen": builtin_e.COMPGEN,
    "compopt": builtin_e.COMPOPT,
    "compadjust": builtin_e.COMPADJUST,

    "true": builtin_e.TRUE,
    "false": builtin_e.FALSE,

    "test": builtin_e.TEST,
    "[": builtin_e.BRACKET,

    "getopts": builtin_e.GETOPTS,

    "command": builtin_e.COMMAND,
    "type": builtin_e.TYPE,
    "hash": builtin_e.HASH,
    "help": builtin_e.HELP,
    "history": builtin_e.HISTORY,

    "declare": builtin_e.DECLARE,
    "typeset": builtin_e.TYPESET,

    "alias": builtin_e.ALIAS,
    "unalias": builtin_e.UNALIAS,

    # Oil only
    "push": builtin_e.PUSH,
    "append": builtin_e.APPEND,

    "write": builtin_e.WRITE,
    "getline": builtin_e.GETLINE,
    "json": builtin_e.JSON,

    "repr": builtin_e.REPR,
    "use": builtin_e.USE,
}

# This is used by completion.
BUILTIN_NAMES = (
    _SPECIAL_BUILTINS.keys() + _SPECIAL_ASSIGN_BUILTINS.keys() +
    _NORMAL_BUILTINS.keys()
)


class _Builtin(object):

  def __init__(self, index, name, kind='normal'):
    # type: (int, str, str) -> None
    self.index = index
    self.name = name
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

  def Add(self, *args, **kwargs):
    # type: (Any, Any) -> None
    self.builtins.append(_Builtin(self.index, *args, **kwargs))
    self.index += 1


def _Init(builtin_def):
  # type: (_BuiltinDef) -> None

  # TODO: Add special, assign, etc.
  pass


_BUILTIN_DEF = _BuiltinDef()

_Init(_BUILTIN_DEF)


def BuiltinDict():
  # type: () -> Dict[str, _Builtin]
  """For the slow path in frontend/match.py."""
  return dict((b.name, b) for b in _BUILTIN_DEF.builtins)


# TODO: Simplify
# This should just check that it's defined?
# We want to connect args
# But if args are going to generate code, they should be all in one file?
def _Register(name, help_topic=None):
  # type: (str, str) -> args.BuiltinFlags

  from frontend import args  # circular build dependency

  arg_spec = args.BuiltinFlags()
  return arg_spec


# TODO: Remove these
def ResolveSpecial(argv0):
  # type: (str) -> builtin_t
  """Is it a special builtin?"""
  return _SPECIAL_BUILTINS.get(argv0, builtin_e.NONE)


def ResolveAssign(argv0):
  # type: (str) -> builtin_t
  """Is it an assignment builtin?"""
  return _SPECIAL_ASSIGN_BUILTINS.get(argv0, builtin_e.NONE)


def Resolve(argv0):
  # type: (str) -> builtin_t
  """Is it any other builtin?"""
  return _NORMAL_BUILTINS.get(argv0, builtin_e.NONE)
