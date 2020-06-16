#!/usr/bin/env python2
"""
flag_spec.py -- Flag and arg defs for builtins.
"""
from __future__ import print_function

import sys

from _devbuild.gen.runtime_asdl import (
    cmd_value__Argv, flag_type, flag_type_t, value, value_t,
    FlagSpec_, FlagSpecAndMore_, SetToArg_,
)
from frontend import args
from mycpp import mylib

from typing import Union, List, Tuple, Dict, Any, Optional

# Similar to frontend/{option,builtin}_def.py
FLAG_SPEC = {}
FLAG_SPEC_AND_MORE = {}
OIL_SPEC = {}


def FlagSpec(builtin_name, typed=False):
  # type: (str, bool) -> _FlagSpec
  """
  """
  arg_spec = _FlagSpec(typed=typed)
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


def OilFlags(name):
  # type: (str) -> _OilFlags
  """
  For set, bin/oil.py ("main"), compgen -A, complete -A, etc.
  """
  arg_spec = _OilFlags()
  OIL_SPEC[name] = arg_spec
  return arg_spec


def Parse(spec_name, arg_r):
  # type: (str, args.Reader) -> args._Attributes
  """Parse argv using a given FlagSpec."""
  spec = FLAG_SPEC[spec_name]
  return args.Parse(spec.spec, arg_r)


def ParseCmdVal(spec_name, cmd_val):
  # type: (str, cmd_value__Argv) -> Tuple[args._Attributes, args.Reader]
  arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
  arg_r.Next()  # move past the builtin name

  spec = FLAG_SPEC[spec_name]
  return args.Parse(spec.spec, arg_r), arg_r


def ParseLikeEcho(spec_name, cmd_val):
  # type: (str, cmd_value__Argv) -> Tuple[args._Attributes, args.Reader]
  arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
  arg_r.Next()  # move past the builtin name

  spec = FLAG_SPEC[spec_name]
  return args.ParseLikeEcho(spec.spec, arg_r), arg_r


def ParseMore(spec_name, arg_r):
  # type: (str, args.Reader) -> args._Attributes
  """Parse argv using a given FlagSpecAndMore."""
  spec = FLAG_SPEC_AND_MORE[spec_name]
  return spec.Parse(arg_r)


def All():
  # type: () -> Dict[str, Any]
  return FLAG_SPEC


def _FlagType(arg_type):
  # type: (Union[None, int, List[str]]) -> flag_type_t

  if arg_type is None:
    typ = flag_type.Bool()  # type: flag_type_t
  elif arg_type == args.Int:
    typ = flag_type.Int()
  elif arg_type == args.Float:
    typ = flag_type.Float()
  elif arg_type == args.String:
    typ = flag_type.Str()
  elif isinstance(arg_type, list):
    typ = flag_type.Enum(arg_type)
  else:
    raise AssertionError(arg_type)

  return typ


def _Default(arg_type, arg_default=None):
  # type: (Union[None, int, List[str]], Optional[str]) -> value_t

  # for enum or string
  # note: not using this for integers yet
  if arg_default is not None:
    return value.Str(arg_default)  # early return

  if arg_type is None:
    default = value.Bool(False)  # type: value_t
  elif arg_type == args.Int:
    default = value.Int(-1)  # positive values aren't allowed now
  elif arg_type == args.Float:
    default = value.Float(0.0)
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
  def __init__(self, typed=False):
    # type: (bool) -> None
    # New style: eventually everything should be typed
    self.typed = typed

    # ASDL definition.  To be serialized to C++.
    self.spec = FlagSpec_()

    # Convenience
    self.arity0 = self.spec.arity0
    self.arity1 = self.spec.arity1
    self.options = self.spec.options
    self.defaults = self.spec.defaults

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

  def ShortFlag(self, short_name, arg_type=None, help=None):
    # type: (str, Optional[int], Optional[str]) -> None
    """
    This is very similar to ShortFlag for FlagSpecAndMore, except we have
    separate arity0 and arity1 dicts.
    """
    assert short_name.startswith('-'), short_name
    assert len(short_name) == 2, short_name

    char = short_name[1]
    if arg_type is None:
      self.arity0.append(char)
    else:
      self.arity1[char] = SetToArg_(char, _FlagType(arg_type), False)

    typ = _FlagType(arg_type)
    default_val = _Default(arg_type)

    if self.typed:
      self.defaults[char] = default_val
    else:
      # TODO: remove when all builtins converted
      self.defaults[char] = value.Undef()

    self.fields[char] = typ

  def ShortOption(self, char, help=None):
    # type: (str, Optional[str]) -> None
    """Define an option that can be turned off with + and on with -."""

    assert len(char) == 1  # 'r' for -r +r
    self.options.append(char)

    self.defaults[char] = value.Undef()
    # '+' or '-'.  TODO: Should we make it a bool?
    self.fields[char] = flag_type.Str()

  # TODO: Remove this method -- args.Parse() instead
  def Parse(self, arg_r):
    # type: (args.Reader) -> args._Attributes
    """For builtins to read args after we parse flags."""
    return args.Parse(self.spec, arg_r)

  def ParseArgv(self, argv):
    # type: (List[str]) -> Tuple[args._Attributes, int]
    """For tools/readlink.py -- no location info available."""
    arg_r = args.Reader(argv)
    return self.Parse(arg_r), arg_r.i


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
    self.spec = FlagSpecAndMore_()
    self.typed = typed

    self.actions_short = {}  # type: Dict[str, args._Action]  # {'-c': _Action}
    self.actions_long = {}  # type: Dict[str, args._Action]  # {'--rcfile': _Action}
    self.defaults = self.spec.defaults

    self.actions_short['o'] = args.SetNamedOption()  # -o and +o
    self.actions_short['O'] = args.SetNamedOption(shopt=True)  # -O and +O

    # For code generation.  Not used at runtime.
    self.fields = {}  # type: Dict[str, flag_type_t]

  def InitActions(self):
    # type: () -> None
    self.actions_short['A'] = args.SetNamedAction()  # -A

  def ShortFlag(self, short_name, arg_type=None, default=None,
                quit_parsing_flags=False, help=None):
    # type: (str, int, Optional[Any], bool, Optional[str]) -> None
    """ -c """
    assert short_name.startswith('-'), short_name
    assert len(short_name) == 2, short_name

    char = short_name[1]
    if arg_type is None:
      assert quit_parsing_flags == False
      typ = flag_type.Bool()  # type: flag_type_t
      self.actions_short[char] = args.SetToTrue(char)
    else:
      typ = _FlagType(arg_type)
      self.actions_short[char] = args.SetToArgAction(
          char, typ, quit_parsing_flags=quit_parsing_flags)

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
    if arg_type is None:
      typ = flag_type.Bool()  # type: flag_type_t
      self.actions_long[long_name] = args.SetToTrue(name)
    else:
      typ = _FlagType(arg_type)
      self.actions_long[long_name] = args.SetToArgAction(name, typ)

    attr_name = name.replace('-', '_')
    if self.typed:
      self.defaults[attr_name] = _Default(arg_type, arg_default=default)
      #from core.pyerror import log
      #log('%s DEFAULT %s', attr_name, self.defaults[attr_name])
    else:
      self.defaults[attr_name] = args.PyToValue(default)
    self.fields[attr_name] = typ

  def Option(self, short_flag, name, help=None):
    # type: (Optional[str], str, Optional[str]) -> None
    """Register an option that can be -e or -o errexit.

    Args:
      short_flag: 'e'
      name: errexit
    """
    attr_name = name
    if short_flag:
      assert not short_flag.startswith('-'), short_flag
      self.actions_short[short_flag] = args.SetOption(attr_name)

    self.actions_short['o'].Add(attr_name)  # type: ignore

  def ShoptOption(self, name, help=None):
    # type: (str, Optional[str]) -> None
    """Register an option like shopt -s nullglob

    Args:
      name: 'nullglob'
    """
    attr_name = name
    self.actions_short['O'].Add(attr_name)  # type: ignore

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

    self.actions_short['A'].Add(attr_name)  # type: ignore

  # TODO: Remove this method -- args.ParseMore() instead
  def Parse(self, arg_r):
    # type: (args.Reader) -> args._Attributes
    return args.ParseMore(self, arg_r)


class _OilFlags(object):
  """Parser for oil command line tools and builtins.

  Tools:
    oshc ACTION [OPTION]... ARGS...
    oilc ACTION [OPTION]... ARG...
    opyc ACTION [OPTION]... ARG...

  Builtins:
    test -file /
    test -dir /
    Optionally accept test --file.

  Usage:
    spec = args.OilFlags()
    spec.Flag('-no-docstring')  # no short flag for simplicity?
    opts, i = spec.Parse(argv)

  Another idea:

    input = ArgInput(argv)
    action = input.ReadRequired(error='An action is required')

  The rest should be similar to Go flags.
  https://golang.org/pkg/flag/

  -flag
  -flag=x
  -flag x (non-boolean only)

  --flag
  --flag=x
  --flag x (non-boolean only)

  --flag=false  --flag=FALSE  --flag=0  --flag=f  --flag=F  --flag=False

  Disallow triple dashes though.

  FlagSet ?  That is just spec.

  spec.Arg('action') -- make it required!

  spec.Action()  # make it required, and set to 'action' or 'subaction'?

  if arg.action ==

    prefix= suffix= should be kwargs I think
    Or don't even share the actions?

  What about global options?  --verbose?

  You can just attach that to every spec, like DefineOshCommonOptions(spec).
  """
  def __init__(self):
    # type: () -> None
    self.arity1 = {}  # type: Dict[str, args._Action]
    self.defaults = {}  # type: Dict[str, value_t]  # attr name -> default value
    # (flag name, string) tuples, in order
    self.help_strings = []  # type: List[Tuple[str, str]]

  def Flag(self, name, arg_type, default=None, help=None):
    # type: (str, int, Optional[Any], Optional[str]) -> None
    """
    Args:
      name: e.g. '-no-docstring'
      arg_type: e.g. Str
    """
    assert name.startswith('-') and not name.startswith('--'), name

    attr_name = name[1:].replace('-', '_')
    if arg_type == args.Bool:
      self.arity1[attr_name] = args.SetBoolToArg(attr_name)
    else:
      self.arity1[attr_name] = args.SetToArgAction(attr_name, _FlagType(arg_type))

    self.defaults[attr_name] = args.PyToValue(default)

  def Parse(self, arg_r):
    # type: (args.Reader) -> Tuple[args._Attributes, int]
    return args.ParseOil(self, arg_r)

  def ParseArgv(self, argv):
    # type: (List[str]) -> Tuple[args._Attributes, int]
    """For tools/readlink.py -- no location info available."""
    arg_r = args.Reader(argv)
    return self.Parse(arg_r)
