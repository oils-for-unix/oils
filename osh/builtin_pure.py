#!/usr/bin/env python2
"""
builtin_pure.py - Builtins that don't do any I/O.

If the OSH interpreter were embedded in another program, these builtins can be
safely used, e.g. without worrying about modifying the file system.

NOTE: There can be spew on stdout, e.g. for shopt -p and so forth.

builtin_printf.py and builtin_bracket.py also fall in this category.  And
arguably builtin_comp.py, though it's less useful without GNU readline.

Others to move here: help
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import Token

from core import error
from core.pyerror import e_usage
from core.pyutil import stderr_line
from core import optview
from core import state
from core.pyerror import log
from core import vm
from frontend import args
from frontend import flag_spec
from frontend import match
from qsn_ import qsn
from mycpp import mylib
from osh import word_compile

from typing import List, Dict, Tuple, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from core.ui import ErrorFormatter
  from core.state import MutableOpts, Mem, SearchPath

_ = log


class Boolean(vm._Builtin):
  """For :, true, false."""
  def __init__(self, status):
    # type: (int) -> None
    self.status = status

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    return self.status


class Alias(vm._Builtin):
  def __init__(self, aliases, errfmt):
    # type: (Dict[str, str], ErrorFormatter) -> None
    self.aliases = aliases
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    _, arg_r = flag_spec.ParseCmdVal('alias', cmd_val)
    argv = arg_r.Rest()

    if len(argv) == 0:
      for name in sorted(self.aliases):
        alias_exp = self.aliases[name]
        # This is somewhat like bash, except we use %r for ''.
        print('alias %s=%r' % (name, alias_exp))
      return 0

    status = 0
    for i, arg in enumerate(argv):
      name, alias_exp = mylib.split_once(arg, '=')
      if alias_exp is None:  # if we get a plain word without, print alias
        alias_exp = self.aliases.get(name)
        if alias_exp is None:
          self.errfmt.Print_('No alias named %r' % name,
                             span_id=cmd_val.arg_spids[i])
          status = 1
        else:
          print('alias %s=%r' % (name, alias_exp))
      else:
        self.aliases[name] = alias_exp

    #print(argv)
    #log('AFTER ALIAS %s', aliases)
    return status


class UnAlias(vm._Builtin):
  def __init__(self, aliases, errfmt):
    # type: (Dict[str, str], ErrorFormatter) -> None
    self.aliases = aliases
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    _, arg_r = flag_spec.ParseCmdVal('unalias', cmd_val)
    argv = arg_r.Rest()

    if len(argv) == 0:
      e_usage('requires an argument')

    status = 0
    for i, name in enumerate(argv):
      try:
        del self.aliases[name]
      except KeyError:
        self.errfmt.Print_('No alias named %r' % name,
                           span_id=cmd_val.arg_spids[i])
        status = 1
    return status


def SetShellOpts(exec_opts, opt_changes, shopt_changes):
  # type: (MutableOpts, List[Tuple[str, bool]], List[Tuple[str, bool]]) -> None
  """Used by bin/oil.py too."""

  for opt_name, b in opt_changes:
    exec_opts.SetOption(opt_name, b)

  for opt_name, b in shopt_changes:
    exec_opts.SetShoptOption(opt_name, b)


class Set(vm._Builtin):
  def __init__(self, exec_opts, mem):
    # type: (MutableOpts, Mem) -> None
    self.exec_opts = exec_opts
    self.mem = mem

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    # TODO:
    # - How to integrate this with auto-completion?  Have to handle '+'.

    if len(cmd_val.argv) == 1:
      # 'set' without args shows visible variable names and values.  According
      # to POSIX:
      # - the names should be sorted, and 
      # - the code should be suitable for re-input to the shell.  We have a
      #   spec test for this.
      # Also:
      # - autoconf also wants them to fit on ONE LINE.
      # http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#set
      mapping = self.mem.GetAllVars()
      for name in sorted(mapping):
        str_val = mapping[name]
        code_str = '%s=%s' % (name, qsn.maybe_shell_encode(str_val))
        print(code_str)
      return 0

    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'set'
    arg = flag_spec.ParseMore('set', arg_r)

    # 'set -o' shows options.  This is actually used by autoconf-generated
    # scripts!
    if arg.show_options:
      self.exec_opts.ShowOptions([])
      return 0

    SetShellOpts(self.exec_opts, arg.opt_changes, arg.shopt_changes)
    # Hm do we need saw_double_dash?
    if arg.saw_double_dash or not arg_r.AtEnd():
      self.mem.SetArgv(arg_r.Rest())
    return 0


class Shopt(vm._Builtin):
  def __init__(self, exec_opts):
    # type: (MutableOpts) -> None
    self.exec_opts = exec_opts

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('shopt', cmd_val)

    arg = arg_types.shopt(attrs.attrs)
    opt_names = arg_r.Rest()

    if arg.p:  # print values
      if arg.o:  # use set -o names
        self.exec_opts.ShowOptions(opt_names)
      else:
        self.exec_opts.ShowShoptOptions(opt_names)
      return 0

    if arg.q:  # query values
      for name in opt_names:
        index = match.MatchOption(name)
        if index == 0:
          return 2  # bash gives 1 for invalid option; 2 is better
        if not self.exec_opts.opt_array[index]:
          return 1  # at least one option is not true
      return 0  # all options are true

    if arg.s:
      b = True
    elif arg.u:
      b = False
    else:
      # bash prints uses a different format for 'shopt', but we use the
      # same format as 'shopt -p'.
      self.exec_opts.ShowShoptOptions(opt_names)
      return 0

    # Otherwise, set options.
    for name in opt_names:
      if arg.o:
        self.exec_opts.SetOption(name, b)
      else:
        self.exec_opts.SetShoptOption(name, b)

    return 0


class Hash(vm._Builtin):
  def __init__(self, search_path):
    # type: (SearchPath) -> None
    self.search_path = search_path

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('hash', cmd_val)
    arg = arg_types.hash(attrs.attrs)

    rest = arg_r.Rest()
    if arg.r:
      if len(rest):
        e_usage('got extra arguments after -r')
      self.search_path.ClearCache()
      return 0

    status = 0
    if len(rest):
      for cmd in rest:  # enter in cache
        full_path = self.search_path.CachedLookup(cmd)
        if full_path is None:
          stderr_line('hash: %r not found', cmd)
          status = 1
    else:  # print cache
      commands = self.search_path.CachedCommands()
      commands.sort()
      for cmd in commands:
        print(cmd)

    return status


def _ParseOptSpec(spec_str):
  # type: (str) -> Dict[str, bool]
  spec = {}  # type: Dict[str, bool]
  i = 0
  n = len(spec_str)
  while True:
    if i >= n:
      break
    c = spec_str[i]
    key = '-' + c
    spec[key] = False
    i += 1
    if i >= n:
      break
    # If the next character is :, change the value to True.
    if spec_str[i] == ':':
      spec[key] = True
      i += 1
  return spec


def _GetOpts(spec, argv, optind, errfmt):
  # type: (Dict[str, bool], List[str], int, ErrorFormatter) -> Tuple[int, str, str, int]
  optarg = ''  # not set by default

  try:
    current = argv[optind-1]  # 1-based indexing
  except IndexError:
    return 1, '?', optarg, optind

  if not current.startswith('-'):  # The next arg doesn't look like a flag.
    return 1, '?', optarg, optind

  # It looks like an argument.  Stop iteration by returning 1.
  if current not in spec:  # Invalid flag
    optind += 1
    return 0, '?', optarg, optind

  optind += 1
  opt_char = current[-1]

  needs_arg = spec[current]
  if needs_arg:
    try:
      optarg = argv[optind-1]  # 1-based indexing
    except IndexError:
      # TODO: Add location info
      errfmt.Print_('getopts: option %r requires an argument.' % current)
      tmp = [qsn.maybe_shell_encode(a) for a in argv]
      stderr_line('(getopts argv: %s)', ' '.join(tmp))
      # Hm doesn't cause status 1?
      return 0, '?', optarg, optind

    optind += 1

  return 0, opt_char, optarg, optind


class GetOpts(vm._Builtin):
  """
  Vars used:
    OPTERR: disable printing of error messages
  Vars set:
    The variable named by the second arg
    OPTIND - initialized to 1 at startup
    OPTARG - argument
  """

  def __init__(self, mem, errfmt):
    # type: (Mem, ErrorFormatter) -> None
    self.mem = mem
    self.errfmt = errfmt
    self.spec_cache = {}  # type: Dict[str, Dict[str, bool]]

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()

    # NOTE: If first char is a colon, error reporting is different.  Alpine
    # might not use that?
    spec_str = arg_r.ReadRequired('requires an argspec')

    var_name, var_spid = arg_r.ReadRequired2(
        'requires the name of a variable to set')

    try:
      spec = self.spec_cache[spec_str]
    except KeyError:
      spec = _ParseOptSpec(spec_str)
      self.spec_cache[spec_str] = spec

    # TODO: OPTIND could be value.Int?
    try:
      optind = state.GetInteger(self.mem, 'OPTIND')
    except error.Runtime as e:
      self.errfmt.Print_(e.UserErrorString())
      return 1

    user_argv = self.mem.GetArgv() if arg_r.AtEnd() else arg_r.Rest()
    #util.log('user_argv %s', user_argv)
    status, opt_char, optarg, optind = _GetOpts(spec, user_argv, optind,
                                                self.errfmt)

    # Bug fix: bash-completion uses a *local* OPTIND !  Not global.
    state.SetStringDynamic(self.mem, 'OPTARG', optarg)
    state.SetStringDynamic(self.mem, 'OPTIND', str(optind))
    if match.IsValidVarName(var_name):
      state.SetStringDynamic(self.mem, var_name, opt_char)
    else:
      # NOTE: The builtin has PARTIALLY filed.  This happens in all shells
      # except mksh.
      raise error.Usage('got invalid variable name %r' % var_name,
                        span_id=var_spid)
    return status


class Echo(vm._Builtin):
  """echo builtin.

  shopt -s simple-echo:
    -sep ''
    -end '\n'
    -n is a synonym for -end ''
    -e deprecated
    -- is accepted

  Issues:
  - Has to use Oil option parser.
  - How does this affect completion?

  NOTE: Python's getopt and optparse are both unsuitable for 'echo' because:
  - 'echo -c' should print '-c', not fail
  - echo '---' should print ---, not fail
  """
  def __init__(self, exec_opts):
    # type: (optview.Exec) -> None
    self.exec_opts = exec_opts
    self.f = mylib.Stdout()

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    argv = cmd_val.argv[1:]
    attrs, arg_r = flag_spec.ParseLikeEcho('echo', cmd_val)

    arg = arg_types.echo(attrs.attrs)
    argv = arg_r.Rest()

    backslash_c = False  # \c terminates input
    arg0_spid = cmd_val.arg_spids[0]

    if arg.e:
      new_argv = []  # type: List[str]
      for a in argv:
        parts = []  # type: List[str]
        lex = match.EchoLexer(a)
        while not backslash_c:
          id_, value = lex.Next()
          if id_ == Id.Eol_Tok:  # Note: This is really a NUL terminator
            break

          tok = Token(id_, arg0_spid, value)
          p = word_compile.EvalCStringToken(tok)

          # Unusual behavior: '\c' prints what is there and aborts processing!
          if p is None:
            backslash_c = True
            break

          parts.append(p)

        new_argv.append(''.join(parts))
        if backslash_c:  # no more args either
          break

      # Replace it
      argv = new_argv

    if self.exec_opts.strict_echo():
      n = len(argv)
      if n == 0:
        pass
      elif n == 1:
        self.f.write(argv[0])
      else:
        # TODO: span_id could be more accurate
        e_usage(
            "takes at most one arg when strict_echo is on (hint: add quotes)")
    else:
      #log('echo argv %s', argv)
      for i, a in enumerate(argv):
        if i != 0:
          self.f.write(' ')  # arg separator
        self.f.write(a)

    if not arg.n and not backslash_c:
      self.f.write('\n')

    return 0
