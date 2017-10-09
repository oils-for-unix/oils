#!/usr/bin/env python
"""
args.py - Flag, option, and arg parsing for the shell.

All existing shells have their own flag parsing, rather than using libc.

Differences from getopt/optparse:

- accepts +o +n for 'set' and bin/osh
  - pushd and popd also uses +, although it's not an arg.
- parses args -- well argparse is supposed to do this
- maybe: integrate with usage
- maybe: integrate with flags

optparse: 
  - has option groups

NOTES about builtins:
- eval implicitly joins it args, we don't want to do that
  - how about strict-builtin-syntax ?
- bash is inconsistent about checking for extra args
  - exit 1 2 complains, but pushd /lib /bin just ignores second argument
  - it has a no_args() function that isn't called everywhere.  It's not
    declarative.

We have TWO flag parsers, one for the 'sh' command line and 'set', and one for
builtins.  The reason is that these cases behave differently:

set -opipefail  # not allowed, space required

read -t1.0  # allowed

bashgetopt.c codes:
  leading +: allow options
  : requires argument
  ; argument may be missing
  # numeric argument

However I don't see these used anywhere!  I only see ':' used.

TODO:
  - add default values, e.g. ast_format='text'
  - add help text: spec.Flag(..., help='')
  - add usage line: BuiltinFlags('echo [-en]')
  - add --foo=bar syntax

  - add GNU-style option to interleave flags and args
    - NOTE: after doing this, you could probably statically parse a lot of
      scripts and analyze flag usage?

- NOTE: GNU getopt has fuzzy matching for long flags.  I think we should rely
  on good completion instead.

"""

from core import util

log = util.log


class UsageError(Exception):
  """Raised by builtins upon flag parsing error."""
  pass


class _Attributes(object):
  """Object to hold flags"""

  def __init__(self, defaults):
    self.opt_changes = []  # special name
    self.saw_double_dash = False  # for set --
    for name, v in defaults.iteritems():
      setattr(self, name, v)

  def __repr__(self):
    return '<_Attributes %s>' % self.__dict__


class _ArgState:
  """Modified by both the parsing loop and various actions."""

  def __init__(self, argv):
    self.argv = argv
    self.n = len(argv)
    self.i = 0

  def __repr__(self):
    return '<_ArgState %r %d>' % (self.argv, self.i)

  def Next(self):
    """Get the next arg."""
    self.i += 1
    #assert self.i <= self.n, self.i

  def Peek(self):
    return self.argv[self.i]

  def Done(self):
    return self.i == self.n


class _Action(object):
  """What is done when a flag or option is detected."""

  def OnMatch(self, prefix, suffix, state, out):
    """Called when the flag matches.

    Returns:
      True if flag parsing should be aborted.
    """
    raise NotImplementedError


class SetToArg(_Action):

  def __init__(self, name, arg_type, quit_parsing_flags=False):
    self.name = name
    assert isinstance(arg_type, int) or isinstance(arg_type, list), arg_type
    self.arg_type = arg_type
    self.quit_parsing_flags = quit_parsing_flags

  def OnMatch(self, prefix, suffix, state, out):
    """Called when the flag matches."""

    #log('SetToArg SUFFIX %r', suffix)
    if suffix:
      arg = suffix
    else:
      state.Next()
      try:
        arg = state.Peek()
      except IndexError:
        raise UsageError('Expected argument for %r' % self.name)

    #log('SetToArg Arg %r', arg)

    typ = self.arg_type
    if isinstance(typ, list):
      if arg not in typ:
        raise UsageError('Invalid argument %r, expected one of: %s' %
            (arg, ', '.join(typ)))
      value = arg
    else:
      if typ == Str:
        value = arg
      elif typ == Int:
        value = int(arg)  # TODO: check errors
      elif typ == Float:
        value = float(arg)  # TODO: check errors
      else:
        raise AssertionError

    setattr(out, self.name, value)
    return self.quit_parsing_flags


class SetToTrue(_Action):

  def __init__(self, name):
    self.name = name

  def OnMatch(self, prefix, suffix, state, out):
    """Called when the flag matches."""
    setattr(out, self.name, True)


class SetOption(_Action):
  """ Set an option to a boolean, for 'set +e' """

  def __init__(self, name):
    self.name = name

  def OnMatch(self, prefix, suffix, state, out):
    """Called when the flag matches."""
    b = (prefix == '-')
    out.opt_changes.append((self.name, b))


class SetNamedOption(_Action):
  """Set a named option to a boolean, for 'set +o errexit' """

  def __init__(self):
    self.names = []

  def Add(self, name):
    self.names.append(name)

  def OnMatch(self, prefix, suffix, state, out):
    """Called when the flag matches."""
    b = (prefix == '-')
    #log('SetNamedOption %r %r %r', prefix, suffix, state)
    state.Next()  # always advance
    try:
      arg = state.Peek()
    except IndexError:
      raise UsageError('Expected argument for option')

    attr_name = arg.replace('-', '_')
    # Validate the option name against a list of valid names.
    if attr_name not in self.names:
      raise UsageError('Invalid option name %r' % arg)
    out.opt_changes.append((attr_name, b))


# Arg type:
Str = 1
Int = 2
Float = 3  # e.g. for read -t timeout value


class FlagsAndOptions(object):
  """
  Usage:

  spec.Option()
  spec.ShortFlag()
  spec.LongFlag()  # only for sh

  Members:
    actions

  Use cases:
    'set' and 'sh', and maybe 'shopt'
  """
  def __init__(self):
    self.actions_short = {}  # {'-c': _Action}
    self.actions_long = {}  # {'--rcfile': _Action}
    self.attr_names = {}  # attributes that name flags
    self.defaults = {}

    self.actions_short['o'] = SetNamedOption()  # -o and +o

  def ShortFlag(self, short_name, arg_type=None, default=None,
                quit_parsing_flags=False):
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

  def LongFlag(self, long_name, arg_type=None, default=None):
    """ --rcfile """
    assert long_name.startswith('--'), long_name

    name = long_name[2:].replace('-', '_')
    if arg_type is None:
      self.actions_long[long_name] = SetToTrue(name)
    else:
      self.actions_long[long_name] = SetToArg(name, arg_type)

    self.attr_names[name] = default

  def Option(self, short_flag, name):
    """
    Args:
      short_flag: 'e'
      name: errexit
    """
    attr_name = name.replace('-', '_')  # debug-completion -> debug_completion
    if short_flag:
      assert not short_flag.startswith('-'), short_flag
      self.actions_short[short_flag] = SetOption(attr_name)

    self.actions_short['o'].Add(attr_name)

  def Parse(self, argv):
    # Respect +
    # set -eu
    # set +eu
    #
    # Or should detect if OptionFlags is set?
    # Not true for -s though!
    #
    # We do NOT respect:
    #
    # WRONG: sh -cecho    OK: sh -c echo
    # WRONG: set -opipefail     OK: set -o pipefail
    #
    # But we do accept these
    #
    # set -euo pipefail
    # set -oeu pipefail
    # set -oo pipefail errexit
    #
    # LATER: Long flags for 'sh', but not for 'set'

    state = _ArgState(argv)
    out = _Attributes(self.attr_names)

    quit = False
    while not state.Done():
      arg = state.Peek()
      if arg == '--':
        out.saw_double_dash = True
        state.Next()
        break

      # NOTE: We don't yet support --rcfile=foo.  Only --rcfile foo.
      if arg.startswith('--'):
        try:
          action = self.actions_long[arg]
        except KeyError:
          raise UsageError('Invalid flag %r' % arg)
        # TODO: Suffix could be 'bar' for --foo=bar
        action.OnMatch(None, None, state, out)
        state.Next()
        continue

      if arg.startswith('-') or arg.startswith('+'):
        char0 = arg[0]
        for char in arg[1:]:
          #log('char %r state %s', char, state)
          try:
            action = self.actions_short[char]
          except KeyError:
            #print(self.actions_short)
            raise UsageError('Invalid flag %r' % char)
          quit = action.OnMatch(char0, None, state, out)
        state.Next() # process the next flag
        if quit:
          break
        else:
          continue

      break  # it's a regular arg

    return out, state.i


class BuiltinFlags(object):
  """
  Usage:
    spec.ShortFlag()
    # Maybe for Oil:
    spec.LongFlag()

  Members:
    arity0
    arity1

  Use cases:
    All builtins
  """

  def __init__(self):
    self.arity0 = {}  # {'r': _Action}  e.g. read -r
    self.arity1 = {}  # {'t': _Action}  e.g. read -t 1.0

    self.attr_names = {}

    self.on_flag = None
    self.off_flag = None

  def PrintHelp(self, f):
    print('[0]')
    for ch in self.arity0:
      print ch
    print('[1]')
    for ch in self.arity1:
      print ch

  def ShortFlag(self, short_name, arg_type=None):
    """ 
    This is very similar to ShortFlag for FlagsAndOptions, except we have
    separate arity0 and arity1 dicts.
    """
    assert short_name.startswith('-'), short_flag
    assert len(short_name) == 2, short_flag

    char = short_name[1]
    if arg_type is None:
      self.arity0[char] = SetToTrue(char)
    else:
      self.arity1[char] = SetToArg(char, arg_type)

    self.attr_names[char] = None

  def LongFlag(self, long_name, arg_type=None):
    """ --ast-format """
    raise NotImplementedError

  def Arg(self, name):
    """The next arg should be given this name."""
    pass

  def Rest(self, name):
    """The rest of the args should be given this name.

    This suppresses errors about extra arguments.
    """
    pass

  def ParseLikeEcho(self, argv):
    # echo is a special case.  These work:
    #   echo -n
    #   echo -en
    #
    # - But don't respect --
    # - doesn't fail with invalid flag
    state = _ArgState(argv)
    out = _Attributes(self.attr_names)

    while not state.Done():
      arg = state.Peek()
      if arg.startswith('-') and len(arg) > 1:
        if not all(c in self.arity0 for c in arg[1:]):
          break  # looks like args

        n = len(arg)
        for i in xrange(1, n):
          char = arg[i]
          action = self.arity0[char]
          action.OnMatch(None, None, state, out)

      else:
        break  # Looks like an arg

      state.Next()  # next arg

    return out, state.i

  def Parse(self, argv):
    # TODO: Parse -en into separate actions
    # Also read -t1.0 is supposed to be an arg!
    # So you have to know which one it is.  Is it an arg with flag?
    # So look up the first one

    # NOTE about -:
    # 'set -' ignores it, vs set 
    # 'unset -' or 'export -' seems to treat it as a variable name

    state = _ArgState(argv)
    out = _Attributes(self.attr_names)

    while not state.Done():
      arg = state.Peek()
      if arg == '--':
        out.saw_double_dash = True
        state.Next()
        break

      if arg.startswith('-') and len(arg) > 1:
        n = len(arg)
        for i in xrange(1, n):
          char = arg[i]

          if char in self.arity0:  # e.g. read -r
            action = self.arity0[char]
            action.OnMatch(None, None, state, out)
            continue

          if char in self.arity1:  # e.g. read -t1.0
            action = self.arity1[char]
            suffix = arg[i+1:]
            #log('SUFFIX %r ARG %r', suffix, arg)
            action.OnMatch(None, suffix, state, out)
            break

          raise UsageError('Invalid flag %r' % char)

        state.Next()  # next arg

      else:  # a regular arg
        break

    return out, state.i

