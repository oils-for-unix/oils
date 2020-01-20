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

import sys  # for sys.sdtout

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import builtin_e, cmd_value, value_e

from asdl import pretty
from core.util import e_die
from core import ui
from frontend import args
from frontend import lex
from frontend import match
from osh.builtin import Resolve, ResolveSpecial, ResolveAssign
from osh.builtin import _Register  # TODO: Remove this
from osh import state
from osh import string_ops
from osh import word_compile

from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
  from osh.cmd_exec import Executor
  from osh.state import SearchPath
  from _devbuild.gen.syntax_asdl import command__ShFunction


ALIAS_SPEC = _Register('alias')


class Alias(object):
  def __init__(self, aliases, errfmt):
    self.aliases = aliases
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    if len(arg_vec.strs) == 1:
      for name in sorted(self.aliases):
        alias_exp = self.aliases[name]
        # This is somewhat like bash, except we use %r for ''.
        print('alias %s=%r' % (name, alias_exp))
      return 0

    status = 0
    for i in xrange(1, len(arg_vec.strs)):
      arg = arg_vec.strs[i]
      parts = arg.split('=', 1)
      if len(parts) == 1:  # if we get a plain word without, print alias
        name = parts[0]
        alias_exp = self.aliases.get(name)
        if alias_exp is None:
          self.errfmt.Print('No alias named %r', name, span_id=arg_vec.spids[i])
          status = 1
        else:
          print('alias %s=%r' % (name, alias_exp))
      else:
        name, alias_exp = parts
        self.aliases[name] = alias_exp

    #print(argv)
    #log('AFTER ALIAS %s', aliases)
    return status


UNALIAS_SPEC = _Register('unalias')


class UnAlias(object):
  def __init__(self, aliases, errfmt):
    self.aliases = aliases
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    if len(arg_vec.strs) == 1:
      raise args.UsageError('unalias NAME...')

    status = 0
    for i in xrange(1, len(arg_vec.strs)):
      name = arg_vec.strs[i]
      try:
        del self.aliases[name]
      except KeyError:
        self.errfmt.Print('No alias named %r', name, span_id=arg_vec.spids[i])
        status = 1
    return status

#
# set and shopt
#

def AddOptionsToArgSpec(spec):
  """Shared between 'set' builtin and the shell's own arg parser."""
  for short_flag, opt_name in state.SET_OPTIONS:
    spec.Option(short_flag, opt_name)

  for shopt_name in state.ALL_SHOPT_OPTIONS + state.META_OPTIONS:
    spec.ShoptOption(shopt_name)


SET_SPEC = args.FlagsAndOptions()
AddOptionsToArgSpec(SET_SPEC)


def SetExecOpts(exec_opts, opt_changes, shopt_changes):
  """Used by bin/oil.py too."""

  for opt_name, b in opt_changes:
    exec_opts.SetOption(opt_name, b)

  for opt_name, b in shopt_changes:
    exec_opts.SetShoptOption(opt_name, b)


class Set(object):
  def __init__(self, exec_opts, mem):
    self.exec_opts = exec_opts
    self.mem = mem

  def __call__(self, arg_vec):
    # TODO:
    # - How to integrate this with auto-completion?  Have to handle '+'.

    if len(arg_vec.strs) == 1:
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
        code_str = '%s=%s' % (name, string_ops.ShellQuoteOneLine(str_val))
        print(code_str)
      return 0

    arg_r = args.Reader(arg_vec.strs, spids=arg_vec.spids)
    arg_r.Next()  # skip 'set'
    arg = SET_SPEC.Parse(arg_r)

    # 'set -o' shows options.  This is actually used by autoconf-generated
    # scripts!
    if arg.show_options:
      self.exec_opts.ShowOptions([])
      return 0

    SetExecOpts(self.exec_opts, arg.opt_changes, arg.shopt_changes)
    # Hm do we need saw_double_dash?
    if arg.saw_double_dash or not arg_r.AtEnd():
      self.mem.SetArgv(arg_r.Rest())
    return 0


SHOPT_SPEC = _Register('shopt')
SHOPT_SPEC.ShortFlag('-s')  # set
SHOPT_SPEC.ShortFlag('-u')  # unset
SHOPT_SPEC.ShortFlag('-o')  # use 'set -o' up names
SHOPT_SPEC.ShortFlag('-p')  # print
SHOPT_SPEC.ShortFlag('-q')  # query option settings


class Shopt(object):
  def __init__(self, exec_opts):
    self.exec_opts = exec_opts

  def __call__(self, arg_vec):
    arg, i = SHOPT_SPEC.ParseVec(arg_vec)
    opt_names = arg_vec.strs[i:]

    if arg.p:  # print values
      if arg.o:  # use set -o names
        self.exec_opts.ShowOptions(opt_names)
      else:
        self.exec_opts.ShowShoptOptions(opt_names)
      return 0

    if arg.q:  # query values
      for name in opt_names:
        if not hasattr(self.exec_opts, name):
          return 2  # bash gives 1 for invalid option; 2 is better
        if not getattr(self.exec_opts, name):
          return 1  # at least one option is not true
      return 0  # all options are true

    b = None
    if arg.s:
      b = True
    elif arg.u:
      b = False

    if b is None:  # Print options
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


def _ResolveNames(names, funcs, aliases, search_path):
  results = []
  for name in names:
    if name in funcs:
      kind = ('function', name)
    elif name in aliases:
      kind = ('alias', name)
    elif Resolve(name) != builtin_e.NONE:
      kind = ('builtin', name)
    elif ResolveSpecial(name) != builtin_e.NONE:
      kind = ('builtin', name)
    elif ResolveAssign(name) != builtin_e.NONE:
      kind = ('builtin', name)
    elif lex.IsOtherBuiltin(name):  # continue, etc.
      kind = ('builtin', name)
    elif lex.IsKeyword(name):
      kind = ('keyword', name)
    else:
      resolved = search_path.Lookup(name)
      if resolved is None:
        kind = (None, None)
      else:
        kind = ('file', resolved) 
    results.append(kind)

  return results


COMMAND_SPEC = _Register('command')
COMMAND_SPEC.ShortFlag('-v')
#COMMAND_SPEC.ShortFlag('-V')  # Another verbose mode.


class Command(object):
  def __init__(self, ex, funcs, aliases, search_path):
    # type: (Executor, Dict[str, command__ShFunction], Dict[str, str], SearchPath) -> None
    self.ex = ex
    self.funcs = funcs
    self.aliases = aliases
    self.search_path = search_path

  def __call__(self, arg_vec, fork_external):
    arg, arg_index = COMMAND_SPEC.ParseVec(arg_vec)
    if arg.v:
      status = 0
      names = arg_vec.strs[arg_index:]
      for kind, arg in _ResolveNames(names, self.funcs, self.aliases,
                                     self.search_path):
        if kind is None:
          status = 1  # nothing printed, but we fail
        else:
          # This is for -v, -V is more detailed.
          print(arg)
      return status

    # shift by one
    cmd_val = cmd_value.Argv(arg_vec.strs[1:], arg_vec.spids[1:])
    # 'command ls' suppresses function lookup.
    return self.ex.RunSimpleCommand(cmd_val, fork_external, funcs=False)


TYPE_SPEC = _Register('type')
TYPE_SPEC.ShortFlag('-f')
TYPE_SPEC.ShortFlag('-t')
TYPE_SPEC.ShortFlag('-p')
TYPE_SPEC.ShortFlag('-P')


class Type(object):
  def __init__(self, funcs, aliases, search_path):
    self.funcs = funcs
    self.aliases = aliases
    self.search_path = search_path

  def __call__(self, arg_vec):
    arg, i = TYPE_SPEC.ParseVec(arg_vec)

    if arg.f:
      funcs = []
    else:
      funcs = self.funcs

    status = 0
    r = _ResolveNames(arg_vec.strs[i:], funcs, self.aliases, self.search_path)
    for kind, name in r:
      if kind is None:
        status = 1  # nothing printed, but we fail
      else:
        if arg.t:
          print(kind)
        elif arg.p:
          if kind == 'file':
            print(name)
        elif arg.P:
          if kind == 'file':
            print(name)
          else:
            resolved = self.search_path.Lookup(name)
            if resolved is None:
              status = 1
            else:
              print(resolved)

        else:
          # Alpine's abuild relies on this text because busybox ash doesn't have
          # -t!
          # ash prints "is a shell function" instead of "is a function", but the
          # regex accouts for that.
          print('%s is a %s' % (name, kind))
          if kind == 'function':
            # bash prints the function body, busybox ash doesn't.
            pass

    return status


HASH_SPEC = _Register('hash')
HASH_SPEC.ShortFlag('-r')


class Hash(object):
  def __init__(self, search_path):
    self.search_path = search_path

  def __call__(self, arg_vec):
    arg_r = args.Reader(arg_vec.strs, spids=arg_vec.spids)
    arg_r.Next()  # skip 'hash'
    arg, i = HASH_SPEC.Parse(arg_r)

    rest = arg_r.Rest()
    if arg.r:
      if rest:
        raise args.UsageError('got extra arguments after -r')
      self.search_path.ClearCache()
      return 0

    status = 0
    if rest:
      for cmd in rest:  # enter in cache
        full_path = self.search_path.CachedLookup(cmd)
        if full_path is None:
          ui.Stderr('hash: %r not found', cmd)
          status = 1
    else:  # print cache
      for cmd in self.search_path.CachedCommands():
        print(cmd)

    return status


def _ParseOptSpec(spec_str):
  # type: (str) -> Dict[str, bool]
  spec = {}
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
      errfmt.Print('getopts: option %r requires an argument.', current)
      ui.Stderr('(getopts argv: %s)', ' '.join(pretty.String(a) for a in argv))
      # Hm doesn't cause status 1?
      return 0, '?', optarg, optind

    optind += 1

  return 0, opt_char, optarg, optind


class GetOpts(object):
  """
  Vars used:
    OPTERR: disable printing of error messages
  Vars set:
    The variable named by the second arg
    OPTIND - initialized to 1 at startup
    OPTARG - argument
  """

  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt
    self.spec_cache = {}  # type: Dict[str, Dict[str, bool]]

  def __call__(self, arg_vec):
    arg_r = args.Reader(arg_vec.strs, spids=arg_vec.spids)
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

    # These errors are fatal errors, not like the builtin exiting with code 1.
    # Because the invariants of the shell have been violated!
    v = self.mem.GetVar('OPTIND')
    if v.tag != value_e.Str:
      e_die('OPTIND should be a string, got %r', v)
    try:
      optind = int(v.s)
    except ValueError:
      e_die("OPTIND doesn't look like an integer, got %r", v.s)

    user_argv = arg_r.Rest() or self.mem.GetArgv()
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
      raise args.UsageError('got invalid variable name %r' % var_name,
                            span_id=var_spid)
    return status


ECHO_SPEC = _Register('echo')
ECHO_SPEC.ShortFlag('-e')  # no backslash escapes
ECHO_SPEC.ShortFlag('-n')

class Echo(object):
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
    self.exec_opts = exec_opts

  def __call__(self, arg_vec):
    argv = arg_vec.strs[1:]
    arg, arg_index = ECHO_SPEC.ParseLikeEcho(argv)
    argv = argv[arg_index:]
    if arg.e:
      new_argv = []
      for a in argv:
        parts = []
        lex = match.EchoLexer(a)
        while True:
          id_, value = lex.Next()
          if id_ == Id.Eol_Tok:  # Note: This is really a NUL terminator
            break

          p = word_compile.EvalCStringToken(id_, value)

          # Unusual behavior: '\c' prints what is there and aborts processing!
          if p is None:
            new_argv.append(''.join(parts))
            for i, a in enumerate(new_argv):
              if i != 0:
                sys.stdout.write(' ')  # arg separator
              sys.stdout.write(a)
            return 0  # EARLY RETURN

          parts.append(p)
        new_argv.append(''.join(parts))

      # Replace it
      argv = new_argv

    #log('echo argv %s', argv)
    for i, a in enumerate(argv):
      if i != 0:
        sys.stdout.write(' ')  # arg separator
      sys.stdout.write(a)
    if not arg.n:
      sys.stdout.write('\n')

    return 0
