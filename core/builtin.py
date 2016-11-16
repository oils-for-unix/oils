#!/usr/bin/env python3
"""
builtins.py

Metadata about builtins.

TODO:
  - used for lookup in cmd_exec.py
    - need a hash of builtin names for quick testing?
  - handle completion of builtin NAMES -- pass to completion.py
    - handle aliases : . and source, [ and test
  - handle flags they take
    - handle completion of builtin FLAGS
  - handle args?  And check number of args?  e.g. 'break 3 4' -- "too many
    arguments" though.
  - handle help text
  - Add the "help" builtin itself

- builtins are NOT tokens I think

- Write our own option parser?
  - Expose it to the user of the proc dialect?

- NOTE: If it's going to be exposed to the user, it can't be done in with C++
  code generation!  This compiler perhaps needs to be ported over to the func
  dialect later!

- options: name, arity/type, help, var to set
  - long option name, I guess GNU style, as our usability extension for
    builtins, and also to allow users to use it
- also + vs -  -- set +o vs -o, pushd +3 -3
  - +o vs -o means that there are two values?  bool and string name?
  - might also need code generation for opts, since it is in "set" as well as
    the "sh" arguments itself.

NOTE: The POSIX spec defines only boolean flags essentially.  All builtins seem
to have at most 3 flags.  But bash has some with tons of flags, and it also has
args, e.g. for compgen.

- option groups?  For help only.  Although you can just write a code gen check
  to see if help lists all the options defined in the spec.
- default values
- GNU getopt has fuzzy matching... might want an option to turn that on or off.

Why does every shell have its own getopt?  I think you can just generate the
getopt string from Python optparse-like spec.

Well you don't want to depend on the GNU libc for long options, etc.  The
language should be self contained and not affected by libc (except possibly for
the old ERE regex syntax -- that can be regcomp?)

Not sure if help should be auto-generated.  We may be able to format it better
in a custom manner.  Although perhaps help should take an arg like help --xml
or help --json

Also --line-number etc. is annoying to type in both the spec and the help.

NOTE: bash has help -d -m -s.  Default is -s, like a man page.

parsing issues:
  combining stuff  cd -LP .

NOTE: Port metadata for ALL bash builtins, but don't implement all of them yet?
e.g. caller, command

Whether it's special or not!  This affects the search path and a couple other
things.  Didn't realize this.

# http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_14
"A syntax error in a special built-in utility may cause a shell executing that
utility to abort, while a syntax error in a regular built-in utility shall not
cause a shell executing that utility to abort. (See Consequences of Shell
Errors for the consequences of errors on interactive and non-interactive
shells.) If a special built-in utility encountering a syntax error does not
abort the shell, its exit value shall be non-zero.

"Variable assignments specified with special built-in utilities remain in
effect after the built-in completes; this shall not be the case with a regular
built-in or other utility.

http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_09_01_01

"If the command name does not contain any <slash> characters, the first
successful step in the following sequence shall occur:

"If the command name matches the name of a special built-in utility, that
special built-in utility shall be invoked.

"If the command name matches the name of a function known to this shell, the
function shall be invoked as described in Function Definition Command. If the
implementation has provided a standard utility in the form of a function, it
shall not be recognized at this point. It shall be invoked in conjunction with
the path search in step 1d.

"""

import sys

from core import util

# NOTE: NONE is a special value.
# TODO:
# - Make a table of name to enum?  source, dot, etc.
# - So you can just add "complete" and have it work.

EBuiltin = util.Enum('EBuiltin', """
NONE BREAK CONTINUE RETURN READ ECHO EXIT SOURCE DOT TRAP EVAL EXEC SET COMPLETE
COMPGEN DEBUG_LINE
""".split())


# These can't be redefined by functions.
# http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_14
# On the other hand, 'cd' CAN be redefined.
# TODO:
# - use these
# - local and declare should be here, since export and readonly are.
SPECIAL_BUILTINS = [
    'break', ':', 'continue', '.', 'eval', 'exec', 'exit', 'export',
    'readonly', 'return', 'set', 'shift', 'times', 'trap', 'unset',
]


# Should we use python3 argparse?  It has stuff like nargs.
# choices, def
# But it doesn't handle '+' probably.

class ArgDef(object):
  """
  Either an flag or positional argument.

  Used for code gen.
  """
  def __init__(self,
      pos=0, letter='', long_name='', metavar='', type='str', default=None):
    """
    Args:
      pos: 1 for first argj, e.g. break 'n'
      letter: 'a' for -a
      long name: used for --force, and also var name to generate?
      metavar: the name of the arg placeholder when printing help

      type: default str, can be int or bool?  Bool means it doesn't take args.
        or can be a list of strings for choices?
      help_str: short help string.  Alignment is an issue (see grep --help)
        Also grouping.
      default: default value if none is specified

      required?  Not sure if anyone uses this.

      What about - vs +?  +o
    """
    pass


class ArgSpec(object):
  """
  Holds ArgDef instances in groups?  This helps usability, when reading long
  lists of options (ulimit, compopt, compgen, set)
  """
  def __init__(self, syntax_str, usage_str, end_str, arg_defs):
    """
    Args:
      arg_defs: maybe {section name: [ ArgDef, ... ]}
    """
    pass

  def GetOneLineHelp(self):
    """
    For "help" index
    """

  def GetHelp(self):
    """Return help as a big string.

    Usgae
    Sections of short opt, long opt, help
    end_str
    """
    # TODO: This could be compressed in the C++ binary somehow?  Count up the
    # size first.


class BuiltinDef(object):
  """Metadata for the builtin.  Not necessarily the implementation.

  Used for code gen."""
  def __init__(self, name, arg_spec, special=False):
    """
    Args:
      names: name to register
      arg_spec: argument parser.  Used to generate getopt() string, as well as
        completion?  And maybe type checking code.
      help_str: 72 or 79 width help string. 
        Need to document usage line, and also exit status.
        Bash has a man page thing, but we don't need that.

      special: Whether it's a special builtin.
      assign: Whether it's an assignment?  These are implemented inside the
      command Executor.
      Do we need
    """
    self.name = name
    self.arg_spec = arg_spec


NO_ARGS = ArgSpec("", "", "", [])

# TODO:
DECLARE_LOCAL_ARGS = ArgSpec("", "", "", [])

BUILTINS = [
    # local has options as 'declare'.
    BuiltinDef("declare", DECLARE_LOCAL_ARGS),
    BuiltinDef("local", DECLARE_LOCAL_ARGS),

    BuiltinDef("readonly",
      ArgSpec(
        """
        readonly [-aA] [name[=value] ...] 
        readonly -p
        """,
        """
        Mark shell variables as immutable.

        After executing 'readonly NAME', assignments to NAME result in an
        error.  If a VALUE is supplied, then the variable is bound before
        making it read-only.
        """,
        """Exit Status: Returns success unless an invalid flag or NAME is
        given.
        """,
        [])
      ),
    BuiltinDef("export", ArgSpec("", "", "", [])),
    
    # Control flow builtins.  No options, could have args
    BuiltinDef("break", NO_ARGS),
    BuiltinDef("continue", NO_ARGS),
    BuiltinDef("return", NO_ARGS),
    
    BuiltinDef("read", NO_ARGS),
    BuiltinDef("echo", NO_ARGS),
    BuiltinDef("exit", NO_ARGS),
    
    # These are aliases
    BuiltinDef("source", NO_ARGS),
    BuiltinDef(".", NO_ARGS),
    
    BuiltinDef("trap", NO_ARGS),
    BuiltinDef("eval", NO_ARGS),
    BuiltinDef("exec", NO_ARGS),
    
    BuiltinDef("set", NO_ARGS),
    BuiltinDef("complete", NO_ARGS),

    # TODO: compgen should instead be a config file?
    BuiltinDef("compgen", NO_ARGS),
    BuiltinDef("debug-line", NO_ARGS),
]


def HelpBuiltin():
  for b_def in BUILTINS:
    # TODO: GetOneLineHelp
    print(b_def.name)


class Builtins(object):
  """
  The executor resolves full names, and the completion system makes queries for
  prefixes of names.

  TODO: Should have a separate BuiltinMetadata and BuiltinImplementation things?
  Stuff outside the core should be here.

  """
  def __init__(self, status_line):
    self.status_line = status_line

    # Is this what we want?
    names = set()
    names.update(b.name for b in BUILTINS)
    names.update(SPECIAL_BUILTINS)
    # TODO: Also complete keywords first for, while, etc.  Bash/zsh/fish/yash
    # all do this.  Also do/done

    self.to_complete = sorted(names)

  def DebugLine(self, argv):
    # TODO: Maybe add a position flag?  Like debug-line -n 1 'foo'
    # And enforce that you get a single arg?
    self.status_line.Write('DEBUG: %s', ' '.join(argv[1:]))

  def GetNamesToComplete(self):
    """For completion of builtin names."""
    return self.to_complete

  def Resolve(self, argv0):
    # TODO: ResolveSpecialBuiltin first, then ResolveFunction, then
    # ResolveOtherBuiltin.  In other words, you can't redefine special builtins
    # with functions, but you can redefine other builtins.

    # For completion, this is a flat list of names.  Although coloring them
    # would be nice.

    if argv0 == "break":
      return EBuiltin.BREAK
    elif argv0 == "continue":
      return EBuiltin.CONTINUE
    elif argv0 == "return":
      return EBuiltin.RETURN

    elif argv0 == "read":
      return EBuiltin.READ
    elif argv0 == "echo":
      return EBuiltin.ECHO
    elif argv0 == "exit":
      return EBuiltin.EXIT

    elif argv0 == "source":
      return EBuiltin.SOURCE
    elif argv0 == ".":
      return EBuiltin.DOT

    elif argv0 == "trap":
      return EBuiltin.TRAP
    elif argv0 == "eval":
      return EBuiltin.EVAL
    elif argv0 == "exec":
      return EBuiltin.EXEC

    elif argv0 == "set":
      return EBuiltin.SET
    elif argv0 == "complete":
      return EBuiltin.COMPLETE
    elif argv0 == "compgen":
      return EBuiltin.COMPGEN

    elif argv0 == "debug-line":
      return EBuiltin.DEBUG_LINE

    return EBuiltin.NONE


def main(argv):
  # TODO: Print all help to static C++ strings?
  # Maybe just make it a single line.

  # Localization: Optionally  use GNU gettext()?  For help only.  Might be
  # useful in parser error messages too.  Good thing both kinds of code are
  # generated?  Because I don't want to deal with a C toolchain for it.

  HelpBuiltin()
  b = Builtins()
  print(b)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
