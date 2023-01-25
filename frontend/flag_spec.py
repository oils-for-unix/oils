#!/usr/bin/env python2
"""
flag_spec.py -- Flag and arg defs for builtins.
"""
from __future__ import print_function

import sys

from _devbuild.gen.runtime_asdl import (
    cmd_value__Argv, flag_type_e, flag_type_t, value, value_t,
)
from core.pyerror import log
from frontend import args
from mycpp import mylib

from typing import Union, List, Tuple, Dict, Any, Optional

_ = log

# Similar to frontend/{option,builtin}_def.py
FLAG_SPEC = {}
FLAG_SPEC_AND_MORE = {}


def FlagSpec(builtin_name):
  # type: (str) -> _FlagSpec
  """Define a flag language."""
  arg_spec = _FlagSpec()
  FLAG_SPEC[builtin_name] = arg_spec
  return arg_spec


def FlagSpecAndMore(name, typed=False):
  # type: (str, bool) -> _FlagSpecAndMore
  """
  For set, bin/oil.py ("main"), compgen -A, complete -A, etc.
  """
  arg_spec = _FlagSpecAndMore(typed=typed)
  FLAG_SPEC_AND_MORE[name] = arg_spec
  return arg_spec


def Parse(spec_name, arg_r):
  # type: (str, args.Reader) -> args._Attributes
  """Parse argv using a given FlagSpec."""
  spec = FLAG_SPEC[spec_name]
  return args.Parse(spec, arg_r)


def ParseCmdVal(spec_name, cmd_val, accept_typed_args=False):
  # type: (str, cmd_value__Argv, bool) -> Tuple[args._Attributes, args.Reader]

  from frontend import typed_args  # break circular dependency

  if not accept_typed_args:
    typed_args.DoesNotAccept(cmd_val.typed_args)

  arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
  arg_r.Next()  # move past the builtin name

  spec = FLAG_SPEC[spec_name]
  return args.Parse(spec, arg_r), arg_r


def ParseLikeEcho(spec_name, cmd_val):
  # type: (str, cmd_value__Argv) -> Tuple[args._Attributes, args.Reader]

  from frontend import typed_args  # break circular dependency

  typed_args.DoesNotAccept(cmd_val.typed_args)

  arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
  arg_r.Next()  # move past the builtin name

  spec = FLAG_SPEC[spec_name]
  return args.ParseLikeEcho(spec, arg_r), arg_r


def ParseMore(spec_name, arg_r):
  # type: (str, args.Reader) -> args._Attributes
  """Parse argv using a given FlagSpecAndMore."""
  spec = FLAG_SPEC_AND_MORE[spec_name]
  return args.ParseMore(spec, arg_r)


def All():
  # type: () -> Dict[str, Any]
  return FLAG_SPEC


def _FlagType(arg_type):
  # type: (Union[None, int, List[str]]) -> flag_type_t

  if arg_type is None:  # implicit _FlagSpec
    typ = flag_type_e.Bool
  elif arg_type == args.Bool:  # explicit _OilFlagSpec
    typ = flag_type_e.Bool

  elif arg_type == args.Int:
    typ = flag_type_e.Int
  elif arg_type == args.Float:
    typ = flag_type_e.Float
  elif arg_type == args.String:
    typ = flag_type_e.Str
  elif isinstance(arg_type, list):
    typ = flag_type_e.Str
  else:
    raise AssertionError(arg_type)

  return typ


def _MakeAction(arg_type, name, quit_parsing_flags=False):
  # type: (Union[None, int, List[str]], str, bool) -> args._Action

  if arg_type == args.Bool:
    assert not quit_parsing_flags
    action = args.SetAttachedBool(name)  # type: args._Action

  elif arg_type == args.Int:
    assert not quit_parsing_flags
    action = args.SetToInt(name)

  elif arg_type == args.Float:
    assert not quit_parsing_flags
    action = args.SetToFloat(name)

  elif arg_type == args.String:
    action = args.SetToString(name, quit_parsing_flags)

  elif isinstance(arg_type, list):
    action = args.SetToString(name, quit_parsing_flags, valid=arg_type)

  else:
    raise AssertionError(arg_type)

  return action


def _Default(arg_type, arg_default=None):
  # type: (Union[None, int, List[str]], Optional[str]) -> value_t

  if arg_default is not None:
    if isinstance(arg_default, bool):
      return value.Bool(arg_default)
    elif isinstance(arg_default, int):
      return value.Int(arg_default)
    elif isinstance(arg_default, str):
      return value.Str(arg_default)
    else:
      raise AssertionError(arg_default)

  if arg_type is None:
    default = value.Bool(False)  # type: value_t
  elif arg_type == args.Bool:  # for _OilFlagSpec
    default = value.Bool(False)

  elif arg_type == args.Int:
    default = value.Int(-1)  # positive values aren't allowed now
  elif arg_type == args.Float:
    default = value.Float(-1.0)  # ditto
  elif arg_type == args.String:
    default = value.Undef()  # e.g. read -d '' is NOT the default
  elif isinstance(arg_type, list):
    default = value.Str('')  # This isn't valid
  else:
    raise AssertionError(arg_type)
  return default


class _FlagSpec(object):
  """Parser for sh builtins, like 'read' or 'echo' (which has a special case).

  Usage:
    spec = args.FlagSpec()
    spec.ShortFlag('-a')
    opts, i = spec.Parse(argv)
  """
  def __init__(self):
    # type: () -> None
    self.arity0 = []  # type: List[str]
    self.arity1 = {}  # type: Dict[str, args._Action]
    self.plus_flags = []  # type: List[str]

    # Oil extensions
    self.actions_long = {}  # type: Dict[str, args._Action]
    self.defaults = {}  # type: Dict[str, value_t]

    # For code generation.  Not used at runtime.
    self.fields = {}  # type: Dict[str, flag_type_t]  # for arg_types to use

  def PrintHelp(self, f):
    # type: (mylib.Writer) -> None
    if self.arity0:
      print('  arity 0:')
    for ch in self.arity0:
      print('    -%s' % ch)

    if self.arity1:
      print('  arity 1:')
    for ch in self.arity1:
      print('    -%s' % ch)

  def ShortFlag(self, short_name, arg_type=None, long_name=None, help=None):
    # type: (str, Optional[int], Optional[str], Optional[str]) -> None
    """
    This is very similar to ShortFlag for FlagSpecAndMore, except we have
    separate arity0 and arity1 dicts.
    """
    assert short_name.startswith('-'), short_name
    assert len(short_name) == 2, short_name

    typ = _FlagType(arg_type)
    char = short_name[1]

    # Hack for read -0.  Make it a valid variable name
    if char == '0':
      char = 'Z'

    if arg_type is None:
      self.arity0.append(char)
    else:
      self.arity1[char] = _MakeAction(arg_type, char)

    if long_name is not None:
      name = long_name[2:]  # key for parsing
      if arg_type is None:
        self.actions_long[name] = args.SetToTrue(char)
      else:
        self.actions_long[name] = _MakeAction(arg_type, char)

    self.defaults[char] = _Default(arg_type)
    self.fields[char] = typ

  def LongFlag(self,
      long_name,  # type: str
      arg_type=None,  # type: Union[None, int, List[str]]
      default=None,  # type: Optional[Any]
      help=None  # type: Optional[str]
      ):
    # type: (...) -> None
    """Define a long flag like --verbose or --validate=0"""
    assert long_name.startswith('--'), long_name
    typ = _FlagType(arg_type)

    name = long_name[2:]  # key for parsing
    if arg_type is None:
      self.actions_long[name] = args.SetToTrue(name)
    else:
      self.actions_long[name] = _MakeAction(arg_type, name)

    self.defaults[name] = _Default(arg_type, arg_default=default)
    self.fields[name] = typ

  def PlusFlag(self, char, help=None):
    # type: (str, Optional[str]) -> None
    """Define an option that can be turned off with + and on with -.

    It's actually a ternary value: plus, minus, or unset.

    For declare -x, etc.
    """
    assert len(char) == 1  # 'r' for -r +r
    self.plus_flags.append(char)

    self.defaults[char] = value.Undef()
    # '+' or '-'.  TODO: Should we make it a bool?
    self.fields[char] = flag_type_e.Str


class _FlagSpecAndMore(object):
  """Parser for 'set' and 'sh', which both need to process shell options.

  Usage:
    spec = FlagSpecAndMore()
    spec.ShortFlag(...)
    spec.Option('u', 'nounset')
    spec.Parse(...)
  """
  def __init__(self, typed=False):
    # type: (bool) -> None
    self.typed = typed

    self.actions_short = {}  # type: Dict[str, args._Action]  # {'-c': _Action}
    self.actions_long = {}  # type: Dict[str, args._Action]  # {'--rcfile': _Action}
    self.plus_flags = []  # type: List[str]
    self.defaults = {}  # type: Dict[str, value_t]

    # For code generation.  Not used at runtime.
    self.fields = {}  # type: Dict[str, flag_type_t]

  def InitActions(self):
    # type: () -> None
    self.actions_short['A'] = args.SetNamedAction()  # -A

  def InitOptions(self):
    # type: () -> None
    self.actions_short['o'] = args.SetNamedOption()  # -o and +o
    self.plus_flags.append('o')

  def InitShopt(self):
    # type: () -> None
    self.actions_short['O'] = args.SetNamedOption(shopt=True)  # -O and +O
    self.plus_flags.append('O')

  def ShortFlag(self, short_name, arg_type=None, default=None,
                quit_parsing_flags=False, help=None):
    # type: (str, int, Optional[Any], bool, Optional[str]) -> None
    """ -c """
    assert short_name.startswith('-'), short_name
    assert len(short_name) == 2, short_name

    char = short_name[1]
    typ = _FlagType(arg_type)
    if arg_type is None:
      assert quit_parsing_flags == False
      self.actions_short[char] = args.SetToTrue(char)
    else:
      self.actions_short[char] = _MakeAction(
          arg_type, char, quit_parsing_flags=quit_parsing_flags)

    if self.typed:
      self.defaults[char] = _Default(arg_type, arg_default=default)
    else:
      self.defaults[char] = args.PyToValue(default)
    self.fields[char] = typ

  def LongFlag(self,
               long_name,  # type: str
               arg_type=None,  # type: Union[List[str], None, int]
               default=None,  # type: Optional[Any]
               help=None,  # type: Optional[str]
               ):
    # type: (...) -> None
    """ --rcfile """
    assert long_name.startswith('--'), long_name

    name = long_name[2:]
    typ = _FlagType(arg_type)
    if arg_type is None:
      self.actions_long[name] = args.SetToTrue(name)
    else:
      self.actions_long[name] = _MakeAction(arg_type, name)

    attr_name = name.replace('-', '_')
    if self.typed:
      self.defaults[attr_name] = _Default(arg_type, arg_default=default)
      #log('%s DEFAULT %s', attr_name, self.defaults[attr_name])
    else:
      self.defaults[attr_name] = args.PyToValue(default)
    self.fields[attr_name] = typ

  def Option(self, short_flag, name, help=None):
    # type: (Optional[str], str, Optional[str]) -> None
    """Register an option; used for -e / -o errexit.

    Args:
      short_flag: 'e'
      name: errexit
    """
    attr_name = name
    if short_flag:
      assert not short_flag.startswith('-'), short_flag
      self.actions_short[short_flag] = args.SetOption(attr_name)
      self.plus_flags.append(short_flag)

    # Not validating with ArgName() for set -o.  It's done later

  def Option2(self, name, help=None):
    # type: (str, Optional[str]) -> None
    """Register an option; used for compopt -o plusdirs, etc."""
    # validate the arg name
    self.actions_short['o'].ArgName(name)  # type: ignore

  def Action(self, short_flag, name):
    # type: (str, str) -> None
    """Register an action that can be -f or -A file.

    For the compgen builtin.

    Args:
      short_flag: 'f'
      name: 'file'
    """
    attr_name = name
    if short_flag:
      assert not short_flag.startswith('-'), short_flag
      self.actions_short[short_flag] = args.SetAction(attr_name)

    self.actions_short['A'].ArgName(attr_name)  # type: ignore
