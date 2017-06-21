#!/usr/bin/python
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
"""

from core import util

log = util.log


class UsageError(Exception):
  """Raised by builtins upon flag parsing error."""
  pass


class _Attributes(object):
  """Object to hold flags"""

  def __init__(self, names):
    self.opt_changes = []  # special name
    for n in names:
      setattr(self, n, None)

  def __repr__(self):
    return '<_Attributes %s>' % self.__dict__


class _ArgState:
  """Modified by both the parsing loop and various actions."""

  def __init__(self, argv):
    self.argv = argv
    self.n = len(argv)
    self.i = 0

  def Next(self):
    """Get the next arg."""
    self.i += 1

  def Peek(self):
    return self.argv[self.i]

  def Done(self):
    return self.i == self.n


class _Action(object):
  """What is done when a flag or option is detected."""

  def OnMatch(self, prefix, state, out):
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

  def OnMatch(self, prefix, state, out):
    """Called when the flag matches."""
    try:
      arg = state.Peek()
    except IndexError:
      raise UsageError('Expected argument for %r' % self.name)

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
    state.Next()

    return self.quit_parsing_flags


class SetToBool(_Action):

  def __init__(self, name, b):
    self.name = name
    self.b = b

  def OnMatch(self, prefix, state, out):
    """Called when the flag matches."""
    setattr(out, self.name, self.b)


class SetOption(_Action):
  """ Set an option to a boolean, for 'set +e' """

  def __init__(self, name):
    self.name = name

  def OnMatch(self, prefix, state, out):
    """Called when the flag matches."""
    b = (prefix == '-')
    out.opt_changes.append((self.name, b))


class SetNamedOption(_Action):
  """Set a named option to a boolean, for 'set +o errexit' """

  def __init__(self):
    self.names = []

  def Add(self, name):
    self.names.append(name)

  def OnMatch(self, prefix, state, out):
    """Called when the flag matches."""
    b = (prefix == '-')
    try:
      arg = state.Peek()
    except IndexError:
      raise UsageError('Expected argument for option')

    # Validate the option name against a list of valid names.
    if arg not in self.names:
      raise UsageError('Invalid option name %r' % arg)
    out.opt_changes.append((arg, b))
    state.Next()


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
    self.attr_names = []  # attributes that name flags

    self.actions_short['o'] = SetNamedOption()  # -o and +o

  def ShortFlag(self, short_name, arg_type=None, quit_parsing_flags=False):
    """ -c """
    assert short_name.startswith('-'), short_name
    assert len(short_name) == 2, short_name

    char = short_name[1]
    if arg_type is None:
      assert quit_parsing_flags == False
      self.actions_short[char] = SetToBool(char, True)
    else:
      self.actions_short[char] = SetToArg(char, arg_type,
                                          quit_parsing_flags=quit_parsing_flags)

    self.attr_names.append(char)

  def LongFlag(self, long_name, arg_type=None):
    """ --rcfile """
    assert long_name.startswith('--'), long_name

    name = long_name[2:].replace('-', '_')
    if arg_type is None:
      self.actions_long[long_name] = SetToBool(name, True)
    else:
      self.actions_long[long_name] = SetToArg(name, arg_type)

    self.attr_names.append(name)

  def Option(self, short_flag, name):
    """
    Args:
      short_flag: 'e'
      name: errexit
    """
    if short_flag:
      assert not short_flag.startswith('-'), short_flag
      self.actions_short[short_flag] = SetOption(name)

    self.actions_short['o'].Add(name)

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
        state.Next()
        break

      # NOTE: We don't yet support --rcfile=foo.  Only --rcfile foo.
      if arg.startswith('--'):
        try:
          action = self.actions_long[arg]
        except KeyError:
          raise UsageError('Invalid flag %r' % arg)
        state.Next()
        action.OnMatch(None, state, out)
        continue

      if arg.startswith('-') or arg.startswith('+'):
        char0 = arg[0]
        state.Next()  # call BEFORE actions
        for char in arg[1:]:
          try:
            action = self.actions_short[char]
          except KeyError:
            print(self.actions_short)
            raise UsageError('Invalid flag %r' % char)
          quit = action.OnMatch(char0, state, out)
        if not quit:
          continue  # process the next flag

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
    self.arity0 = {}  # {'+e': _Action}  e.g. set -e
    self.arity1 = {}  # {'+o': _Action}  e.g. set -o errexit

    self.attr_names = []

    self.on_flag = None
    self.off_flag = None

  def ShortFlag(self, short_name, arg_type=None):
    """ -c """
    assert short_name.startswith('-'), short_flag
    assert len(short_name) == 2, short_flag

    attr_name = short_name[1]
    if arg_type is None:
      self.arity0[short_name] = SetToBool(attr_name, True)
    else:
      self.arity1[short_name] = SetToArg(attr_name, arg_type)

    self.attr_names.append(attr_name)

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
    pass

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
        state.Next()
        break

      if arg.startswith('-') or arg.startswith('+') and len(arg) > 1:
        char0 = arg[0]
        prefix = arg[:2]
        b = (char0 == '-')

        # So register by SINGLE LETTER.
        # And then pass to state.  You don't have to know.

        if prefix in self.arity0:
          for char in arg[1:]:  # e.g. set -eu
            try:
              action = self.arity0[char0 + char]
            except KeyError:
              raise UsageError('Unkown flag %r' % (char0 + char))
            action.OnMatch(letter, state, out)
          state.Next()
          continue

        if prefix in self.arity1:
          action = self.arity1[prefix]
          state.Next()  # skip the flag
          action.OnMatch(arg, state, out)
        continue

        try:
          arity = self.arity[arg]
        except KeyError:
          raise UsageError('Invalid flag %r' % arg)

      break

    return out, state.i
