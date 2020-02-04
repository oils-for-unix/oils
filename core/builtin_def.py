#!/usr/bin/env python2
"""
builtin_def.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import builtin_e, builtin_t
from frontend import args

from typing import Dict

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


class BuiltinDef(object):
  """
  NOTE: This isn't used anywhere!  We're registering nothing.

  We want to complete the flags to builtins.  So this is a mapping from name
  to arg spec.  There might not be any flags.
  """
  def __init__(self):
    # type: () -> None
    # Is this what we want?
    names = set()
    names.update(_NORMAL_BUILTINS.keys())
    names.update(_SPECIAL_BUILTINS.keys())
    names.update(_SPECIAL_ASSIGN_BUILTINS.keys())
    # TODO: Also complete keywords first for, while, etc.  Bash/zsh/fish/yash
    # all do this.  See osh/lex/{_KEYWORDS, _MORE_KEYWORDS}.

    self.arg_specs = {}  # type: Dict[str, args.BuiltinFlags]
    self.to_complete = sorted(names)

  def Register(self, name, help_topic=None):
    # type: (str, str) -> args.BuiltinFlags
    # The help topics are in the quick ref.  TODO: We should match them up?
    #help_topic = help_topic or name
    arg_spec = args.BuiltinFlags()
    self.arg_specs[name] = arg_spec
    return arg_spec


# Global instance for "metaprogramming" before main().
BUILTIN_DEF = BuiltinDef()


# TODO: Are we using this?
def _Register(name, help_topic=None):
  # type: (str, str) -> args.BuiltinFlags
  return BUILTIN_DEF.Register(name, help_topic=help_topic)


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
