"""
args.py - Flag, option, and arg parsing for the shell.

All existing shells have their own flag parsing, rather than using libc.

We have 3 types of flag parsing here:

  FlagSpecAndMore() -- e.g. for 'sh +u -o errexit' and 'set +u -o errexit'
  FlagSpec() -- for echo -en, read -t1.0, etc.
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
  - Autogenerate help from help='' fields.  Usage line like FlagSpec('echo [-en]')
  - FlagSpecAndMore can support --foo=bar (use what OilFlag does)
  - Remove OilFlags in favor of adding --foo=bar support to FlagSpec/

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

from _devbuild.gen.runtime_asdl import (
    value, value_e, value_t, value__Bool, value__Int, value__Float, value__Str,
    flag_type, flag_type_e, flag_type_t, flag_type__Enum
)

from asdl import runtime
from core.util import log
from mycpp import mylib
from mycpp.mylib import tagswitch, iteritems

try:
  import libc  # OilFlags uses regexes right now.
except ImportError:  # circular dependecy with arg_gen
  libc = None

from typing import (
    cast, Tuple, Optional, Dict, List, Any, IO, TYPE_CHECKING
)
if TYPE_CHECKING:
  from frontend import arg_def
  OptChange = Tuple[str, bool]


# TODO: Move to arg_def?  We use flag_type_t
String = 1
Int = 2
Float = 3  # e.g. for read -t timeout value
Bool = 4  # OilFlags has explicit boolean type


class UsageError(Exception):
  """Raised by builtins upon flag parsing error."""

  # TODO: Should this be _ErrorWithLocation?  Probably, even though we only use
  # 'span_id'.
  def __init__(self, msg, span_id=runtime.NO_SPID):
    # type: (str, int) -> None
    self.msg = msg
    self.span_id = span_id


# Note: could split into
#   Flags
#   FlagsAndMore
#
# but we should make it statically typed first.

class _Attributes(object):
  """Object to hold flags.

  TODO: Make this statically typed.
  """
  def __init__(self, defaults):
    # type: (Dict[str, value_t]) -> None

    # New style
    self.attrs = {}  # type: Dict[str, value_t]

    self.opt_changes = []  # type: List[OptChange]  # -o errexit +o nounset
    self.shopt_changes = []  # type: List[OptChange]  # -O nullglob +O nullglob
    self.show_options = False  # 'set -o' without an argument
    self.actions = []  # type: List[str]  # for compgen -A
    self.saw_double_dash = False  # for set --
    for name, v in iteritems(defaults):
      self.Set(name, v)

  def SetTrue(self, name):
    # type: (str) -> None
    self.Set(name, value.Bool(True))

  def Set(self, name, val):
    # type: (str, value_t) -> None

    self.attrs[name] = val

    if mylib.PYTHON:
      # Backward compatibility!
      with tagswitch(val) as case:
        if case(value_e.Undef):
          py_val = None  # type: Any
        elif case(value_e.Bool):
          py_val = cast(value__Bool, val).b
        elif case(value_e.Int):
          py_val = cast(value__Int, val).i
        elif case(value_e.Float):
          py_val = cast(value__Float, val).f
        elif case(value_e.Str):
          py_val = cast(value__Str, val).s
        else:
          raise AssertionError(val)

      # debug-completion -> debug_completion
      setattr(self, name.replace('-', '_'), py_val)

  def __repr__(self):
    # type: () -> str
    return '<_Attributes %s>' % self.__dict__


if mylib.PYTHON:
  def PyToValue(py_val):
    # type: (Any) -> value_t

    if py_val is None:
      val = value.Undef()  # type: value_t
    elif isinstance(py_val, bool):
      val = value.Bool(py_val)
    elif isinstance(py_val, int):
      val = value.Int(py_val)
    elif isinstance(py_val, float):
      val = value.Float()  # TODO: ASDL needs float primitive
    elif isinstance(py_val, str):
      val = value.Str(py_val)
    else:
      raise AssertionError(py_val)

    return val


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
    raise NotImplementedError()


class SetToArg(_Action):

  def __init__(self, name, flag_type, quit_parsing_flags=False):
    # type: (str, flag_type_t, bool) -> None
    """
    Args:
      quit_parsing_flags: Stop parsing args after this one.  for sh -c.
        python -c behaves the same way.
    """
    self.name = name
    self.flag_type = flag_type
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

    # e.g. spec.LongFlag('--format', ['text', 'html'])
    # Should change to arg.Enum([...])
    with tagswitch(self.flag_type) as case:
      if case(flag_type_e.Enum):
        alts = cast(flag_type__Enum, self.flag_type).alts
        if arg not in alts:
          raise UsageError(
              'got invalid argument %r to %r, expected one of: %s' %
              (arg, ('-' + self.name), ', '.join(alts)), span_id=arg_r.SpanId())
        val = value.Str(arg)  # type: value_t

      elif case(flag_type_e.Str):
        val = value.Str(arg)

      elif case(flag_type_e.Int):
        try:
          val = value.Int(int(arg))
        except ValueError:
          raise UsageError(
              'expected integer after %r, got %r' % ('-' + self.name, arg),
              span_id=arg_r.SpanId())

      elif case(flag_type_e.Float):
        try:
          val = value.Float(float(arg))
        except ValueError:
          raise UsageError(
              'expected number after %r, got %r' % ('-' + self.name, arg),
              span_id=arg_r.SpanId())
      else:
        raise AssertionError()

    out.Set(self.name, val)
    return self.quit_parsing_flags


class SetBoolToArg(_Action):
  """This is the Go-like syntax of --verbose=1, --verbose, or --verbose=0."""

  def __init__(self, name):
    # type: (str) -> None
    self.name = name

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (Optional[str], Optional[str], Reader, _Attributes) -> bool
    """Called when the flag matches."""

    if suffix:  # '0' in --verbose=0
      if suffix in ('0', 'F', 'false', 'False'):
        b = False
      elif suffix in ('1', 'T', 'true', 'Talse'):
        b = True
      else:
        raise UsageError(
            'got invalid argument to boolean flag: %r' % suffix)
    else:
      b = True

    out.Set(self.name, value.Bool(b))
    return False


class SetToTrue(_Action):

  def __init__(self, name):
    # type: (str) -> None
    self.name = name

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (Optional[str], Optional[str], Reader, _Attributes) -> bool
    """Called when the flag matches."""
    out.SetTrue(self.name)
    return False


class SetOption(_Action):
  """ Set an option to a boolean, for 'set +e' """

  def __init__(self, name):
    # type: (str) -> None
    self.name = name

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (str, Optional[str], Reader, _Attributes) -> bool
    """Called when the flag matches."""
    b = (prefix == '-')
    out.opt_changes.append((self.name, b))
    return False


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
    # type: (str, Optional[str], Reader, _Attributes) -> bool
    """Called when the flag matches."""
    b = (prefix == '-')
    #log('SetNamedOption %r %r %r', prefix, suffix, arg_r)
    arg_r.Next()  # always advance
    arg = arg_r.Peek()
    if arg is None:
      # triggers on 'set -O' in addition to 'set -o' (meh OK)
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
    # type: (str, str, Reader, _Attributes) -> bool
    out.actions.append(self.name)
    return False


class SetNamedAction(_Action):
  """ For compgen -A file """

  def __init__(self):
    # type: () -> None
    self.names = []  # type: List[str]

  def Add(self, name):
    # type: (str) -> None
    self.names.append(name)

  def OnMatch(self, prefix, suffix, arg_r, out):
    # type: (str, Optional[str], Reader, _Attributes) -> bool
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
    return False


def Parse(spec, arg_r):
  # type: (arg_def._FlagSpec, Reader) -> _Attributes

  # NOTE about -:
  # 'set -' ignores it, vs set
  # 'unset -' or 'export -' seems to treat it as a variable name
  out = _Attributes(spec.defaults)

  while not arg_r.AtEnd():
    arg = arg_r.Peek()
    if arg == '--':
      out.saw_double_dash = True
      arg_r.Next()
      break

    if arg.startswith('-') and len(arg) > 1:
      n = len(arg)
      for i in xrange(1, n):  # parse flag combos like -rx
        ch = arg[i]

        if ch in spec.options:
          out.Set(ch, value.Str('-'))
          continue

        if ch in spec.arity0:  # e.g. read -r
          out.SetTrue(ch)
          continue

        if ch in spec.arity1:  # e.g. read -t1.0
          action = spec.arity1[ch]
          suffix = arg[i+1:]  # '1.0'
          action.OnMatch(None, suffix, arg_r, out)
          break

        raise UsageError(
            "doesn't accept flag %s" % ('-' + ch), span_id=arg_r.SpanId())

      arg_r.Next()  # next arg

    # Only accept + if there are ANY options defined, e.g. for declare +rx.
    elif spec.options and arg.startswith('+') and len(arg) > 1:
      n = len(arg)
      for i in xrange(1, n):  # parse flag combos like -rx
        ch = arg[i]
        if ch in spec.options:
          out.Set(ch, value.Str('+'))
          continue

        raise UsageError(
            "doesn't accept option %s" % ('+' + ch), span_id=arg_r.SpanId())

      arg_r.Next()  # next arg

    else:  # a regular arg
      break

  return out


def ParseMore(spec, arg_r):
  # type: (arg_def._FlagSpecAndMore, Reader) -> _Attributes
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
  out = _Attributes(spec.defaults)

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
        action = spec.actions_long[arg]
      except KeyError:
        raise UsageError(
            'got invalid flag %r' % arg, span_id=arg_r.SpanId())

      # TODO: Suffix could be 'bar' for --foo=bar
      action.OnMatch(None, None, arg_r, out)
      arg_r.Next()
      continue

    if arg.startswith('-') or arg.startswith('+'):
      char0 = arg[0]
      for ch in arg[1:]:
        #log('ch %r arg_r %s', ch, arg_r)
        try:
          action = spec.actions_short[ch]
        except KeyError:
          raise UsageError(
              'got invalid flag %r' % ('-' + ch), span_id=arg_r.SpanId())
        quit = action.OnMatch(char0, None, arg_r, out)
      arg_r.Next() # process the next flag

      if quit:
        break
      else:
        continue

    break  # it's a regular arg

  return out


# - A flag can start with one or two dashes, but not three
# - It can have internal dashes
# - It must not be - or --
#
# Or should you just use libc.regex_match?  And extract groups?

# Using POSIX ERE syntax, not Python.  The second group should start with '='.
_FLAG_ERE = '^--?([a-zA-Z0-9][a-zA-Z0-9\-]*)(=.*)?$'


if mylib.PYTHON:
  def ParseOil(spec, arg_r):
    # type: (arg_def._OilFlags, Reader) -> Tuple[_Attributes, int]
    out = _Attributes(spec.defaults)

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
        if name in spec.arity1:  # e.g. read -t1.0
          action = spec.arity1[name]
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
