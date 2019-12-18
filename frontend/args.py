"""
args.py - Flag, option, and arg parsing for the shell.

All existing shells have their own flag parsing, rather than using libc.

We have 3 types of flag parsing here:

  FlagsAndOptions() -- e.g. for 'sh +u -o errexit' and 'set +u -o errexit'
  BuiltinFlags() -- for echo -en, read -t1.0, etc.
  OilFlags() -- for oshc/opyc/oilc, and probably Oil builtins.

Examples:
  set -opipefail  # not allowed, space required
  read -t1.0  # allowed

Things that getopt/optparse don't support:

- accepts +o +n for 'set' and bin/osh
  - pushd and popd also uses +, although it's not an arg.
- parses args -- well argparse is supposed to do this
- maybe: integrate with usage
- maybe: integrate with flags

optparse:
  - has option groups (Go flag package has flagset)

NOTES about builtins:
- eval and echo implicitly join their args.  We don't want that.
  - option strict-eval and strict-echo
- bash is inconsistent about checking for extra args
  - exit 1 2 complains, but pushd /lib /bin just ignores second argument
  - it has a no_args() function that isn't called everywhere.  It's not
    declarative.

TODO:
  - add help text: spec.Flag(..., help='')
  - add usage line: BuiltinFlags('echo [-en]')
  - Do builtin flags need default values?  It doesn't look like it.

GNU notes:

- Consider adding GNU-style option to interleave flags and args?
  - Not sure I like this.
- GNU getopt has fuzzy matching for long flags.  I think we should rely
  on good completion instead.

Bash notes:

bashgetopt.c codes:
  leading +: allow options
  : requires argument
  ; argument may be missing
  # numeric argument

However I don't see these used anywhere!  I only see ':' used.
"""
from __future__ import print_function

from asdl import runtime
from core.util import log

import libc  # for regex support

from typing import Tuple, Optional, Dict, Union, List, Any, IO, TYPE_CHECKING
from _devbuild.gen.runtime_asdl import arg_vector, cmd_value__Argv

if TYPE_CHECKING:
  OptChange = Tuple[str, bool]


class UsageError(Exception):
  """Raised by builtins upon flag parsing error."""

  # TODO: Should this be _ErrorWithLocation?  Probably, even though we only use
  # 'span_id'.
  def __init__(self, msg, span_id=runtime.NO_SPID):
    # type: (str, int) -> None
    self.msg = msg
    self.span_id = span_id


class _Attributes(object):
  """Object to hold flags"""

  def __init__(self, defaults):
    # type: (Dict[str, Any]) -> None

    self.opt_changes = []  # type: List[OptChange]  # -o errexit +o nounset
    self.shopt_changes = []  # type: List[OptChange]  # -O nullglob +O nullglob
    self.show_options = False  # 'set -o' without an argument
    self.actions = []  # type: List[str]  # for compgen -A
    self.saw_double_dash = False  # for set --
    for name, v in defaults.iteritems():
      self.Set(name, v)

  def Set(self, name, value):
    # type: (str, Union[None, bool, str]) -> None
    # debug-completion -> debug_completion
    setattr(self, name.replace('-', '_'), value)

  def __repr__(self):
    # type: () -> str
    return '<_Attributes %s>' % self.__dict__


class Reader(object):
  """Wrapper for argv.
  
  Modified by both the parsing loop and various actions.

  The caller of the flags parser can continue to use it after flag parsing is
  done to get args.
  """
  def __init__(self, argv, spids=None):
    # type: (List[str], Optional[List[int]]) -> None
    self.argv = argv
    self.spids = spids
    self.n = len(argv)
    self.i = 0

  def __repr__(self):
    # type: () -> str
    return '<args.Reader %r %d>' % (self.argv, self.i)

  def Next(self):
    # type: () -> None
    """Advance."""
    self.i += 1

  def Peek(self):
    # type: () -> Optional[str]
    """Return the next token, or None if there are no more.

    None is your SENTINEL for parsing.
    """
    if self.i >= self.n:
      return None
    else:
      return self.argv[self.i]

  def Peek2(self):
    # type: () -> Tuple[Optional[str], int]
    """Return the next token, or None if there are no more.

    None is your SENTINEL for parsing.
    """
    if self.i >= self.n:
      return None, -1
    else:
      return self.argv[self.i], self.spids[self.i]

  def ReadRequired(self, error_msg):
    # type: (str) -> str
    arg = self.Peek()
    if arg is None:
      # point at argv[0]
      raise UsageError(error_msg, span_id=self._FirstSpanId())
    self.Next()
    return arg

  def ReadRequired2(self, error_msg):
    # type: (str) -> Tuple[str, int]
    arg = self.Peek()
    if arg is None:
      # point at argv[0]
      raise UsageError(error_msg, span_id=self._FirstSpanId())
    spid = self.spids[self.i]
    self.Next()
    return arg, spid

  def Rest(self):
    # type: () -> List[str]
    """Return the rest of the arguments."""
    return self.argv[self.i:]

  def Rest2(self):
    # type: () -> Tuple[List[str], List[int]]
    """Return the rest of the arguments."""
    return self.argv[self.i:], self.spids[self.i:]

  def AtEnd(self):
    # type: () -> bool
    return self.i >= self.n  # must be >= and not ==

  def _FirstSpanId(self):
    # type: () -> int
    if self.spids:
      return self.spids[0]
    else:
      return runtime.NO_SPID  # TODO: remove this when all have spids

  def SpanId(self):
    # type: () -> int
    if self.spids:
      if self.i == self.n:
        i = self.n - 1  # if the last arg is missing, point at the one before
      else:
        i = self.i
      return self.spids[i]
    else:
      return runtime.NO_SPID  # TODO: remove this when all have spids


class _Action(object):
  """What is done when a flag or option is detected."""

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (str, str, Reader, _Attributes) -> bool
    """Called when the flag matches.

    Args:
      prefix: '-' or '+'
      suffix: ',' for -d,
      arg_r: Reader() (rename to Input or InputReader?)
      out: _Attributes() -- thet hing we want to set

    Returns:
      True if flag parsing should be aborted.
    """
    raise NotImplementedError


class SetToArg(_Action):

  def __init__(self, name, arg_type, quit_parsing_flags=False):
    # type: (str, Union[List[str], int], bool) -> None
    """
    Args:
      quit_parsing_flags: Stop parsing args after this one.  for sh -c.
        python -c behaves the same way.
    """
    self.name = name
    assert isinstance(arg_type, int) or isinstance(arg_type, list), arg_type
    self.arg_type = arg_type
    self.quit_parsing_flags = quit_parsing_flags

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (Optional[str], Optional[str], Reader, _Attributes) -> bool
    """Called when the flag matches."""

    if suffix:  # for the ',' in -d,
      arg = suffix
    else:
      arg_r.Next()
      arg = arg_r.Peek()
      if arg is None:
        raise UsageError(
            'expected argument to %r' % ('-' + self.name), span_id=arg_r.SpanId())

    typ = self.arg_type
    if isinstance(typ, list):
      if arg not in typ:
        raise UsageError(
            'got invalid argument %r to %r, expected one of: %s' %
            (arg, ('-' + self.name), ', '.join(typ)), span_id=arg_r.SpanId())
      value = arg  # type: Any
    else:
      if typ == Str:
        value = arg
      elif typ == Int:
        try:
          value = int(arg)
        except ValueError:
          raise UsageError(
              'expected integer after %r, got %r' % ('-' + self.name, arg),
              span_id=arg_r.SpanId())
      elif typ == Float:
        try:
          value = float(arg)
        except ValueError:
          raise UsageError(
              'expected number after %r, got %r' % ('-' + self.name, arg),
              span_id=arg_r.SpanId())
      else:
        raise AssertionError

    out.Set(self.name, value)
    return self.quit_parsing_flags


class SetBoolToArg(_Action):
  """This is the Go-like syntax of --verbose=1, --verbose, or --verbose=0."""

  def __init__(self, name):
    # type: (str) -> None
    self.name = name

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (Optional[Any], Optional[str], Reader, _Attributes) -> None
    """Called when the flag matches."""

    if suffix:  # '0' in --verbose=0
      if suffix in ('0', 'F', 'false', 'False'):
        value = False
      elif suffix in ('1', 'T', 'true', 'Talse'):
        value = True
      else:
        raise UsageError(
            'got invalid argument to boolean flag: %r' % suffix)
    else:
      value = True

    out.Set(self.name, value)


class SetShortOption(_Action):

  def __init__(self, name):
    # type: (str) -> None
    self.name = name

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (Optional[Any], str, Reader, _Attributes) -> None
    """Called when the flag matches.

    Args:
      suffix: - or + (not really a suffix)
    """
    out.Set(self.name, suffix)


class SetToTrue(_Action):

  def __init__(self, name):
    # type: (str) -> None
    self.name = name

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (Optional[Any], Optional[Any], Reader, _Attributes) -> None
    """Called when the flag matches."""
    out.Set(self.name, True)


class SetOption(_Action):
  """ Set an option to a boolean, for 'set +e' """

  def __init__(self, name):
    # type: (str) -> None
    self.name = name

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (str, Optional[Any], Reader, _Attributes) -> None
    """Called when the flag matches."""
    b = (prefix == '-')
    out.opt_changes.append((self.name, b))


class SetNamedOption(_Action):
  """Set a named option to a boolean, for 'set +o errexit' """

  def __init__(self, shopt=False):
    # type: (bool) -> None
    self.names = []  # type: List[str]
    self.shopt = shopt

  def Add(self, name):
    # type: (str) -> None
    self.names.append(name)

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (str, Optional[Any], Reader, _Attributes) -> bool
    """Called when the flag matches."""
    b = (prefix == '-')
    #log('SetNamedOption %r %r %r', prefix, suffix, arg_r)
    arg_r.Next()  # always advance
    arg = arg_r.Peek()
    if arg is None:
      out.show_options = True
      return True  # quit parsing

    attr_name = arg
    # Validate the option name against a list of valid names.
    if attr_name not in self.names:
      raise UsageError('got invalid option %r' % arg, span_id=arg_r.SpanId())

    changes = out.shopt_changes if self.shopt else out.opt_changes
    changes.append((attr_name, b))
    return False


class SetAction(_Action):
  """ For compgen -f """

  def __init__(self, name):
    # type: (str) -> None
    self.name = name

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (str, str, Reader, _Attributes) -> None
    out.actions.append(self.name)


class SetNamedAction(_Action):
  """ For compgen -A file """

  def __init__(self):
    # type: () -> None
    self.names = []  # type: List[str]

  def Add(self, name):
    # type: (str) -> None
    self.names.append(name)

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (str, Optional[Any], Reader, _Attributes) -> None
    """Called when the flag matches."""
    #log('SetNamedOption %r %r %r', prefix, suffix, arg_r)
    arg_r.Next()  # always advance
    arg = arg_r.Peek()
    if arg is None:
      raise UsageError('Expected argument for action')

    attr_name = arg
    # Validate the option name against a list of valid names.
    if attr_name not in self.names:
      raise UsageError('Invalid action name %r' % arg)
    out.actions.append(attr_name)


# How to parse the value.  TODO: Use ASDL for this.
Str = 1
Int = 2
Float = 3  # e.g. for read -t timeout value
Bool = 4  # OilFlags has explicit boolean type


# TODO: Rename ShFlagsAndOptions
class FlagsAndOptions(object):
  """Parser for 'set' and 'sh', which both need to process shell options.

  Usage:
  spec = FlagsAndOptions()
  spec.ShortFlag(...)
  spec.Option('u', 'nounset')
  spec.Parse(argv)
  """

  def __init__(self):
    # type: () -> None
    self.actions_short = {}  # type: Dict[str, _Action]  # {'-c': _Action}
    self.actions_long = {}  # type: Dict[str, _Action]  # {'--rcfile': _Action}
    self.attr_names = {}  # type: Dict[str, str]  # attributes that name flags
    self.defaults = {}  # type: Dict[str, Any]

    self.actions_short['o'] = SetNamedOption()  # -o and +o
    self.actions_short['O'] = SetNamedOption(shopt=True)  # -O and +O

  def InitActions(self):
    # type: () -> None
    self.actions_short['A'] = SetNamedAction()  # -A

  def ShortFlag(self, short_name, arg_type=None, default=None,
                quit_parsing_flags=False, help=None):
    # type: (str, int, Optional[Any], bool, Optional[Any]) -> None
    """ -c """
    assert short_name.startswith('-'), short_name
    assert len(short_name) == 2, short_name

    char = short_name[1]
    if arg_type is None:
      assert quit_parsing_flags == False
      self.actions_short[char] = SetToTrue(char)
    else:
      self.actions_short[char] = SetToArg(char, arg_type,
                                          quit_parsing_flags=quit_parsing_flags)

    self.attr_names[char] = default

  def LongFlag(self,
               long_name,  # type: str
               arg_type=None,  # type: Union[List[str], None, int]
               default=None,  # type: Optional[Any]
               help=None,  # type: Optional[Any]
               ):
    # type: (...) -> None
    """ --rcfile """
    assert long_name.startswith('--'), long_name

    name = long_name[2:]
    if arg_type is None:
      self.actions_long[long_name] = SetToTrue(name)
    else:
      self.actions_long[long_name] = SetToArg(name, arg_type)

    self.attr_names[name] = default

  def Option(self, short_flag, name, help=None):
    # type: (Optional[str], str, Optional[Any]) -> None
    """Register an option that can be -e or -o errexit.

    Args:
      short_flag: 'e'
      name: errexit
    """
    attr_name = name
    if short_flag:
      assert not short_flag.startswith('-'), short_flag
      self.actions_short[short_flag] = SetOption(attr_name)

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
      self.actions_short[short_flag] = SetAction(attr_name)

    self.actions_short['A'].Add(attr_name)  # type: ignore

  def Parse(self, arg_r):
    # type: (Reader) -> _Attributes
    """Return attributes and an index.

    Respects +, like set +eu

    We do NOT respect:
    
    WRONG: sh -cecho    OK: sh -c echo
    WRONG: set -opipefail     OK: set -o pipefail
    
    But we do accept these
    
    set -euo pipefail
    set -oeu pipefail
    set -oo pipefail errexit
    """
    out = _Attributes(self.attr_names)

    quit = False
    while not arg_r.AtEnd():
      arg = arg_r.Peek()
      if arg == '--':
        out.saw_double_dash = True
        arg_r.Next()
        break

      # NOTE: We don't yet support --rcfile=foo.  Only --rcfile foo.
      if arg.startswith('--'):
        try:
          action = self.actions_long[arg]
        except KeyError:
          raise UsageError(
              'got invalid flag %r' % arg, span_id=arg_r.SpanId())

        # TODO: Suffix could be 'bar' for --foo=bar
        action.OnMatch(None, None, arg_r, out)
        arg_r.Next()
        continue

      if arg.startswith('-') or arg.startswith('+'):
        char0 = arg[0]
        for char in arg[1:]:
          #log('char %r arg_r %s', char, arg_r)
          try:
            action = self.actions_short[char]
          except KeyError:
            raise UsageError(
                'got invalid flag %r' % ('-' + char), span_id=arg_r.SpanId())
          quit = action.OnMatch(char0, None, arg_r, out)
        arg_r.Next() # process the next flag
        if quit:
          break
        else:
          continue

      break  # it's a regular arg

    return out


# TODO: Rename OshBuiltinFlags
class BuiltinFlags(object):
  """Parser for sh builtins, like 'read' or 'echo' (which has a special case).

  Usage:
    spec = args.BuiltinFlags()
    spec.ShortFlag('-a')
    opts, i = spec.Parse(argv)
  """
  def __init__(self):
    # type: () -> None
    self.arity0 = {}  # type: Dict[str, _Action]  # {'r': _Action} for read -r
    self.arity1 = {}  # type: Dict[str, _Action]  # {'t': _Action} for read -t 1.0
    self.options = {}  # type: Dict[str, _Action]

    self.attr_names = {}  # type: Dict[str, str]

  def PrintHelp(self, f):
    # type: (IO[bytes]) -> None
    if self.arity0:
      print('  arity 0:')
    for ch in self.arity0:
      print('    -%s' % ch)

    if self.arity1:
      print('  arity 1:')
    for ch in self.arity1:
      print('    -%s' % ch)

  def ShortFlag(self, short_name, arg_type=None, help=None):
    # type: (str, Optional[int], Optional[Any]) -> None
    """
    This is very similar to ShortFlag for FlagsAndOptions, except we have
    separate arity0 and arity1 dicts.
    """
    assert short_name.startswith('-'), short_name
    assert len(short_name) == 2, short_name

    char = short_name[1]
    if arg_type is None:
      self.arity0[char] = SetToTrue(char)
    else:
      self.arity1[char] = SetToArg(char, arg_type)

    self.attr_names[char] = None

  def ShortOption(self, char, help=None):
    # type: (str, Optional[Any]) -> None
    assert len(char) == 1  # 'r' for -r +r
    self.options[char] = SetShortOption(char)
    self.attr_names[char] = None

  def ParseLikeEcho(self, argv):
    # type: (List[str]) -> Tuple[_Attributes, int]
    """
    echo is a special case.  These work:
      echo -n
      echo -en
   
    - But don't respect --
    - doesn't fail when an invalid flag is passed
    """
    arg_r = Reader(argv)
    out = _Attributes(self.attr_names)

    while not arg_r.AtEnd():
      arg = arg_r.Peek()
      chars = arg[1:]
      if arg.startswith('-') and chars:
        # Check if it looks like -en or not.
        # NOTE: Changed to list comprehension to avoid
        # LOAD_CLOSURE/MAKE_CLOSURE.  TODO: Restore later?
        if not all([c in self.arity0 for c in arg[1:]]):
          break  # looks like args

        for char in chars:
          action = self.arity0[char]
          action.OnMatch(None, None, arg_r, out)

      else:
        break  # Looks like an arg

      arg_r.Next()  # next arg

    return out, arg_r.i

  def Parse(self, arg_r):
    # type: (Reader) -> Tuple[_Attributes, int]
    """
    For builtins that need both flags and args.
    """
    # NOTE about -:
    # 'set -' ignores it, vs set
    # 'unset -' or 'export -' seems to treat it as a variable name
    out = _Attributes(self.attr_names)

    while not arg_r.AtEnd():
      arg = arg_r.Peek()
      if arg == '--':
        out.saw_double_dash = True
        arg_r.Next()
        break

      if arg.startswith('-') and len(arg) > 1:
        n = len(arg)
        for i in xrange(1, n):  # parse flag combos like -rx
          char = arg[i]

          if char in self.options:
            action = self.options[char]
            action.OnMatch(None, '-', arg_r, out)
            continue

          if char in self.arity0:  # e.g. read -r
            action = self.arity0[char]
            action.OnMatch(None, None, arg_r, out)
            continue

          if char in self.arity1:  # e.g. read -t1.0
            action = self.arity1[char]
            suffix = arg[i+1:]  # '1.0'
            action.OnMatch(None, suffix, arg_r, out)
            break

          raise UsageError(
              "doesn't accept flag %s" % ('-' + char), span_id=arg_r.SpanId())

        arg_r.Next()  # next arg

      # Only accept + if there are ANY options defined, e.g. for declare +rx.
      elif self.options and arg.startswith('+') and len(arg) > 1:
        n = len(arg)
        for i in xrange(1, n):  # parse flag combos like -rx
          char = arg[i]
          if char in self.options:
            action = self.options[char]
            action.OnMatch(None, '+', arg_r, out)
            continue

          raise UsageError(
              "doesn't accept option %s" % ('+' + char), span_id=arg_r.SpanId())

        arg_r.Next()  # next arg

      else:  # a regular arg
        break

    return out, arg_r.i

  def ParseVec(self, arg_vec):
    # type: (arg_vector) -> Tuple[_Attributes, int]
    """For OSH builtins."""
    arg_r = Reader(arg_vec.strs, spids=arg_vec.spids)
    arg_r.Next()  # move past the builtin name
    return self.Parse(arg_r)

  def ParseCmdVal(self, cmd_val):
    # type: (cmd_value__Argv) -> Tuple[_Attributes, int]
    """Newer style for OSH builtins."""
    arg_r = Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # move past the builtin name
    return self.Parse(arg_r)

  def ParseArgv(self, argv):
    # type: (List[str]) -> Tuple[_Attributes, int]
    """For tools/readlink.py -- no location info available."""
    arg_r = Reader(argv)
    return self.Parse(arg_r)


# - A flag can start with one or two dashes, but not three
# - It can have internal dashes
# - It must not be - or --
#
# Or should you just use libc.regex_match?  And extract groups?

# Using POSIX ERE syntax, not Python.  The second group should start with '='.
_FLAG_ERE = '^--?([a-zA-Z0-9][a-zA-Z0-9\-]*)(=.*)?$'

class OilFlags(object):
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
    self.arity1 = {}  # type: Dict[str, _Action]
    self.attr_names = {}  # type: Dict[str, Any]  # attr name -> default value
    # (flag name, string) tuples, in order
    self.help_strings = []  # type: List[Tuple[str, str]]

  def Flag(self, name, arg_type, default=None, help=None):
    # type: (str, int, Optional[bool], Optional[Any]) -> None
    """
    Args:
      name: e.g. '-no-docstring'
      arg_type: e.g. Str
    """
    assert name.startswith('-') and not name.startswith('--'), name

    attr_name = name[1:].replace('-', '_')
    if arg_type == Bool:
      self.arity1[attr_name] = SetBoolToArg(attr_name)
    else:
      self.arity1[attr_name] = SetToArg(attr_name, arg_type)

    self.attr_names[attr_name] = default

  def Parse(self, arg_r):
    # type: (Reader) -> Tuple[_Attributes, int]
    out = _Attributes(self.attr_names)

    while not arg_r.AtEnd():
      arg = arg_r.Peek()
      if arg == '--':
        out.saw_double_dash = True
        arg_r.Next()
        break

      if arg == '-':  # a valid argument
        break

      # TODO: Use FLAG_RE above
      if arg.startswith('-'):
        m = libc.regex_match(_FLAG_ERE, arg)
        if m is None:
          raise UsageError('Invalid flag syntax: %r' % arg)
        _, flag, val = m  # group 0 is ignored; the whole match

        # TODO: we don't need arity 1 or 0?  Booleans are like --verbose=1,
        # --verbose (equivalent to turning it on) or --verbose=0.

        name = flag.replace('-', '_')
        if name in self.arity1:  # e.g. read -t1.0
          action = self.arity1[name]
          if val.startswith('='):
            suffix = val[1:]  # could be empty, but remove = if any
          else:
            suffix = None
          action.OnMatch(None, suffix, arg_r, out)
        else:
          raise UsageError('Unrecognized flag %r' % arg)

        arg_r.Next()  # next arg

      else:  # a regular arg
        break

    return out, arg_r.i

  def ParseArgv(self, argv):
    # type: (List[str]) -> Tuple[_Attributes, int]
    """For tools/readlink.py -- no location info available."""
    arg_r = Reader(argv)
    return self.Parse(arg_r)
