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
from _devbuild.gen.runtime_asdl import (
    scope_e, lvalue,
    value, value_e, value__Str, value__MaybeStrArray, value__AssocArray,
    value__Obj
)
from _devbuild.gen.syntax_asdl import command_e, BraceGroup
from _devbuild.gen.types_asdl import opt_group_i

from asdl import format as fmt
from asdl import runtime
from core import error
from core.pyerror import e_usage, e_die
from core import optview
from core import state
from core.pyerror import log
from core import ui
from core import vm
from frontend import args
from frontend import consts
from frontend import flag_spec
from frontend import lexer
from frontend import match
from frontend import typed_args
from qsn_ import qsn
from mycpp import mylib
from mycpp.mylib import iteritems, tagswitch, NewDict, print_stderr
from osh import word_compile

from typing import List, Dict, Tuple, Optional, Any, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from core.state import MutableOpts, Mem, SearchPath
  from osh.cmd_eval import CommandEvaluator

_ = log


class Boolean(vm._Builtin):
  """For :, true, false."""
  def __init__(self, status):
    # type: (int) -> None
    self.status = status

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    # These ignore regular args, but shouldn't accept typed args.
    typed_args.DoesNotAccept(cmd_val.typed_args)
    return self.status


class Alias(vm._Builtin):
  def __init__(self, aliases, errfmt):
    # type: (Dict[str, str], ui.ErrorFormatter) -> None
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
    # type: (Dict[str, str], ui.ErrorFormatter) -> None
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
      if name in self.aliases:
        mylib.dict_erase(self.aliases, name)
      else:
        self.errfmt.Print_('No alias named %r' % name,
                           span_id=cmd_val.arg_spids[i])
        status = 1
    return status


def SetOptionsFromFlags(exec_opts, opt_changes, shopt_changes):
  # type: (MutableOpts, List[Tuple[str, bool]], List[Tuple[str, bool]]) -> None
  """Used by core/shell.py"""

  # We can set ANY option with -o.  -O is too annoying to type.
  for opt_name, b in opt_changes:
    exec_opts.SetAnyOption(opt_name, b)

  for opt_name, b in shopt_changes:
    exec_opts.SetAnyOption(opt_name, b)


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

    # Note: set -o nullglob is not valid.  The 'shopt' builtin is preferred in
    # Oil, and we want code to be consistent.
    for opt_name, b in arg.opt_changes:
      self.exec_opts.SetOldOption(opt_name, b)

    for opt_name, b in arg.shopt_changes:
      self.exec_opts.SetAnyOption(opt_name, b)

    # Hm do we need saw_double_dash?
    if arg.saw_double_dash or not arg_r.AtEnd():
      self.mem.SetArgv(arg_r.Rest())
    return 0


class Shopt(vm._Builtin):
  def __init__(self, mutable_opts, cmd_ev):
    # type: (MutableOpts, CommandEvaluator) -> None
    self.mutable_opts = mutable_opts
    self.cmd_ev = cmd_ev

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('shopt', cmd_val,
                                         accept_typed_args=True)

    arg = arg_types.shopt(attrs.attrs)
    opt_names = arg_r.Rest()

    if arg.p:  # print values
      if arg.o:  # use set -o names
        self.mutable_opts.ShowOptions(opt_names)
      else:
        self.mutable_opts.ShowShoptOptions(opt_names)
      return 0

    if arg.q:  # query values
      for name in opt_names:
        index = consts.OptionNum(name)
        if index == 0:
          return 2  # bash gives 1 for invalid option; 2 is better
        if not self.mutable_opts.opt0_array[index]:
          return 1  # at least one option is not true
      return 0  # all options are true

    if arg.s:
      b = True
    elif arg.u:
      b = False
    else:
      # If no flags are passed, print the options.  bash prints uses a
      # different format for 'shopt', but we use the same format as 'shopt
      # -p'.
      self.mutable_opts.ShowShoptOptions(opt_names)
      return 0

    block = typed_args.GetOneBlock(cmd_val.typed_args)
    if block:
      opt_nums = []  # type: List[int]
      for opt_name in opt_names:
        # TODO: could consolidate with checks in core/state.py and option
        # lexer?
        opt_group = consts.OptionGroupNum(opt_name)
        if opt_group == opt_group_i.OilUpgrade:
          opt_nums.extend(consts.OIL_UPGRADE)
          continue

        if opt_group == opt_group_i.OilAll:
          opt_nums.extend(consts.OIL_ALL)
          continue

        if opt_group == opt_group_i.StrictAll:
          opt_nums.extend(consts.STRICT_ALL)
          continue

        index = consts.OptionNum(opt_name)
        if index == 0:
          # TODO: compute span_id
          e_usage('got invalid option %r' % opt_name)
        opt_nums.append(index)

      with state.ctx_Option(self.mutable_opts, opt_nums, b):
        unused = self.cmd_ev.EvalBlock(block)
      return 0  # cd also returns 0

    # Otherwise, set options.
    for opt_name in opt_names:
      # We allow set -o options here
      self.mutable_opts.SetAnyOption(opt_name, b)

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
          print_stderr('hash: %r not found' % cmd)
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
    ch = spec_str[i]
    spec[ch] = False
    i += 1
    if i >= n:
      break
    # If the next character is :, change the value to True.
    if spec_str[i] == ':':
      spec[ch] = True
      i += 1
  return spec


class GetOptsState(object):
  """State persisted across invocations.

  TODO: Handle arg smooshing behavior here too.
  """
  def __init__(self, mem, errfmt):
    # type: (Mem, ui.ErrorFormatter) -> None
    self.mem = mem
    self.errfmt = errfmt
    self._optind = -1
    self.flag_pos = 1  # position within the arg, public var

  def _OptInd(self):
    # type: () -> int
    """Returns OPTIND that's >= 1, or -1 if it's invalid."""
    # Note: OPTIND could be value.Int?
    try:
      result = state.GetInteger(self.mem, 'OPTIND')
    except error.Runtime as e:
      self.errfmt.Print_(e.UserErrorString())
      result = -1
    return result

  def GetArg(self, argv):
    # type: (List[str]) -> Optional[str]
    """Get the value of argv at OPTIND.  Returns None if it's out of range."""
    optind = self._OptInd()
    if optind == -1:
      return None
    self._optind = optind  # save for later

    i = optind - 1  # 1-based index
    #log('argv %s i %d', argv, i)
    if 0 <= i and i < len(argv):
      return argv[i]
    else:
      return None

  def IncIndex(self):
    # type: () -> None
    """Increment OPTIND."""
    # Note: bash-completion uses a *local* OPTIND !  Not global.
    assert self._optind != -1
    state.BuiltinSetString(self.mem, 'OPTIND', str(self._optind + 1))

  def SetArg(self, optarg):
    # type: (str) -> None
    """Set OPTARG."""
    state.BuiltinSetString(self.mem, 'OPTARG', optarg)

  def Fail(self):
    # type: () -> None
    """On failure, reset OPTARG."""
    state.BuiltinSetString(self.mem, 'OPTARG', '')


def _GetOpts(spec, argv, my_state, errfmt):
  # type: (Dict[str, bool], List[str], GetOptsState, ui.ErrorFormatter) -> Tuple[int, str]
  current = my_state.GetArg(argv)
  #log('current %s', current)

  if current is None:  # out of range, etc.
    my_state.Fail()
    return 1, '?'

  if not current.startswith('-') or current == '-':
    my_state.Fail()
    return 1, '?'

  flag_char = current[my_state.flag_pos]

  if my_state.flag_pos < len(current) - 1:
    my_state.flag_pos += 1  # don't move past this arg yet
    more_chars = True
  else:
    my_state.IncIndex()
    my_state.flag_pos = 1
    more_chars = False

  if flag_char not in spec:  # Invalid flag
    return 0, '?'

  if spec[flag_char]:  # does it need an argument?
    if more_chars:
      optarg = current[my_state.flag_pos:]
    else:
      optarg = my_state.GetArg(argv)
      if optarg is None:
        my_state.Fail()
        # TODO: Add location info
        errfmt.Print_('getopts: option %r requires an argument.' % current)
        tmp = [qsn.maybe_shell_encode(a) for a in argv]
        print_stderr('(getopts argv: %s)' % ' '.join(tmp))

        # Hm doesn't cause status 1?
        return 0, '?'
    my_state.IncIndex()
    my_state.SetArg(optarg)
  else:
    my_state.SetArg('')

  return 0, flag_char


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
    # type: (Mem, ui.ErrorFormatter) -> None
    self.mem = mem
    self.errfmt = errfmt

    self.my_state = GetOptsState(mem, errfmt)
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

    spec = self.spec_cache.get(spec_str)
    if spec is None:
      spec = _ParseOptSpec(spec_str)
      self.spec_cache[spec_str] = spec

    user_argv = self.mem.GetArgv() if arg_r.AtEnd() else arg_r.Rest()
    #util.log('user_argv %s', user_argv)
    status, flag_char = _GetOpts(spec, user_argv, self.my_state, self.errfmt)

    if match.IsValidVarName(var_name):
      state.BuiltinSetString(self.mem, var_name, flag_char)
    else:
      # NOTE: The builtin has PARTIALLY set state.  This happens in all shells
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
    #arg0_spid = cmd_val.arg_spids[0]

    if arg.e:
      new_argv = []  # type: List[str]
      for a in argv:
        parts = []  # type: List[str]
        lex = match.EchoLexer(a)
        while not backslash_c:
          id_, value = lex.Next()
          if id_ == Id.Eol_Tok:  # Note: This is really a NUL terminator
            break

          # Note: DummyToken is OK because EvalCStringToken() doesn't have any
          # syntax errors.
          tok = lexer.DummyToken(id_, value)
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

    if self.exec_opts.simple_echo():
      n = len(argv)
      if n == 0:
        pass
      elif n == 1:
        self.f.write(argv[0])
      else:
        # TODO: span_id could be more accurate
        e_usage(
            "takes at most one arg when simple_echo is on (hint: add quotes)")
    else:
      #log('echo argv %s', argv)
      for i, a in enumerate(argv):
        if i != 0:
          self.f.write(' ')  # arg separator
        self.f.write(a)

    if not arg.n and not backslash_c:
      self.f.write('\n')

    return 0


class Module(vm._Builtin):
  """module builtin.

  module main || return
  """
  def __init__(self, modules, exec_opts, errfmt):
    # type: (Dict[str, bool], optview.Exec, ui.ErrorFormatter) -> None
    self.modules = modules
    self.exec_opts = exec_opts
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    _, arg_r = flag_spec.ParseCmdVal('module', cmd_val)
    name, _ = arg_r.ReadRequired2('requires a name')
    #log('modules %s', self.modules)
    if name in self.modules:
      # already defined
      if self.exec_opts.redefine_module():
        self.errfmt.PrintMessage('(interactive) Reloading module %r' % name)
        return 0
      else:
        return 1
    self.modules[name] = True
    return 0


class Use(vm._Builtin):
  """use bin, use dialect to control the 'first word'.

  Examples:
    use bin grep sed

    use dialect ninja   # I think it must be in a 'dialect' scope
    use dialect travis
  """
  def __init__(self, mem, errfmt):
    # type: (state.Mem, ui.ErrorFormatter) -> None
    self.mem = mem
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'use'

    arg, arg_spid = arg_r.Peek2()
    if arg is None:
      raise error.Usage("expected 'bin' or 'dialect'",
                        span_id=runtime.NO_SPID)
    arg_r.Next()

    if arg == 'dialect':
      expected, e_spid = arg_r.Peek2()
      if expected is None:
        raise error.Usage('expected dialect name',
                          span_id=runtime.NO_SPID)

      UP_actual = self.mem.GetValue('_DIALECT', scope_e.Dynamic)
      if UP_actual.tag_() == value_e.Str:
        actual = cast(value__Str, UP_actual).s
        if actual == expected:
          return 0  # OK
        else:
          self.errfmt.Print_(
              'Expected dialect %r, got %r' % (expected, actual),
              span_id=e_spid)

          return 1
      else:
        # Not printing expected value
        self.errfmt.Print_('Expected dialect %r' % expected, span_id=e_spid)
        return 1

    # 'use bin' can be used for static analysis.  Although could it also
    # simplify the SearchPath logic?  Maybe ensure that it is memoized?
    if arg == 'bin':
      rest = arg_r.Rest()
      for name in rest:
        log('bin %s', name)
      return 0

    raise error.Usage("expected 'bin' or 'dialect'",
                      span_id=arg_spid)


class Shvar(vm._Builtin):
  def __init__(self, mem, search_path, cmd_ev):
    # type: (state.Mem, SearchPath, CommandEvaluator) -> None
    self.mem = mem
    self.search_path = search_path  # to clear PATH
    self.cmd_ev = cmd_ev  # To run blocks

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    _, arg_r = flag_spec.ParseCmdVal('shvar', cmd_val, accept_typed_args=True)

    block = typed_args.GetOneBlock(cmd_val.typed_args)
    if not block:
      # TODO: I think shvar LANG=C should just mutate
      # But should there be a whitelist?
      raise error.Usage('expected a block', span_id=runtime.NO_SPID)

    pairs = []  # type: List[Tuple[str, str]]
    args, arg_spids = arg_r.Rest2()
    if len(args) == 0:
      raise error.Usage('Expected name=value', span_id=runtime.NO_SPID)

    for i, arg in enumerate(args):
      name, s = mylib.split_once(arg, '=')
      if s is None:
        raise error.Usage('Expected name=value', span_id=arg_spids[i])
      pairs.append((name, s))

      # Important fix: shvar PATH='' { } must make all binaries invisible
      if name == 'PATH': 
        self.search_path.ClearCache()

    with state.ctx_Shvar(self.mem, pairs):
      unused = self.cmd_ev.EvalBlock(block)

    return 0


class PushRegisters(vm._Builtin):
  def __init__(self, mem, cmd_ev):
    # type: (state.Mem, CommandEvaluator) -> None
    self.mem = mem
    self.cmd_ev = cmd_ev  # To run blocks

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    _, arg_r = flag_spec.ParseCmdVal('push-registers', cmd_val,
                                     accept_typed_args=True)

    block = typed_args.GetOneBlock(cmd_val.typed_args)
    if not block:
      raise error.Usage('expected a block', span_id=runtime.NO_SPID)

    with state.ctx_Registers(self.mem):
      unused = self.cmd_ev.EvalBlock(block)

    # make it "SILENT" in terms of not mutating $?
    # TODO: Revisit this.  It might be better to provide the headless shell
    # with a way to SET $? instead.  Needs to be tested/prototyped.
    return self.mem.last_status[-1]


class Fopen(vm._Builtin):
  """
  This builtin does nothing but run a block.  It's used solely for its redirects

  fopen >out.txt {
    echo hi
  }
  """

  def __init__(self, mem, cmd_ev):
    # type: (state.Mem, CommandEvaluator) -> None
    self.mem = mem
    self.cmd_ev = cmd_ev  # To run blocks

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    _, arg_r = flag_spec.ParseCmdVal('fopen', cmd_val,
                                     accept_typed_args=True)

    block = typed_args.GetOneBlock(cmd_val.typed_args)
    if not block:
      raise error.Usage('expected a block', span_id=runtime.NO_SPID)

    unused = self.cmd_ev.EvalBlock(block)
    return 0


if mylib.PYTHON:

  class HayNode(vm._Builtin):
    """
    The FIXED builtin that is run after 'hay define'

    It evaluates a SUBTREE

    Example:

      package cppunit {
        version = '1.0'
        user bob
      }

    is short for

      haynode package cppunit {
        version = '1.0'
        haynode user bob
      }
    """

    def __init__(self, hay_state, mem, cmd_ev):
      # type: (state.Hay, state.Mem, CommandEvaluator) -> None
      self.hay_state = hay_state
      self.mem = mem  # isolation with mem.PushTemp
      self.cmd_ev = cmd_ev  # To run blocks
      self.arena = cmd_ev.arena  # To extract code strings

    def Run(self, cmd_val):
      # type: (cmd_value__Argv) -> int

      arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)

      hay_name, arg0_spid = arg_r.Peek2()
      if hay_name == 'haynode':  # haynode package glib { ... }
        arg_r.Next()
        hay_name = None  # don't validate

      # Should we call hay_state.AddChild() so it can be mutated?
      result = NewDict()

      node_type, _ = arg_r.Peek2()
      result['type'] = node_type

      arg_r.Next()
      arguments = arg_r.Rest()

      block = typed_args.GetOneBlock(cmd_val.typed_args)

      # package { ... } is not valid
      if len(arguments) == 0 and block is None:
        e_usage('expected at least 1 arg, or a block', span_id=arg0_spid)

      result['args'] = arguments

      if node_type.isupper():  # TASK build { ... }
        if block is None:
          e_usage('command node requires a block argument')

        if 0:  # self.hay_state.to_expr ?
          result['expr'] = block  # UNEVALUATED block
        else:
          # We can only extract code if the block arg is literal like package
          # foo { ... }, not if it's like package foo (myblock)

          brace_group = None  # type: BraceGroup
          with tagswitch(block) as case:
            if case(command_e.BraceGroup):
              brace_group = cast(BraceGroup, block)

          if brace_group:
            # BraceGroup has spid for {
            line_id =brace_group.left.line_id
            src = self.arena.GetLineSource(line_id)
            line_num = self.arena.GetLineNumber(line_id)

            # for the user to pass back to --location-str
            result['location_str'] = ui.GetLineSourceString(self.arena, line_id)
            result['location_start_line'] = line_num

            # Between { and }
            code_str = self.arena.GetCodeString(brace_group.left.span_id,
                                                brace_group.right.span_id)
            result['code_str'] = code_str
          else:
            result['error'] = "Can't find code if block arg isn't literal like { }"

        # Append after validation
        self.hay_state.AppendResult(result)

      else:
        # Must be done before EvalBlock
        self.hay_state.AppendResult(result)

        if block:  # 'package foo' is OK
          result['children'] = []

          # Evaluate in its own stack frame.  TODO: Turn on dynamic scope?
          with state.ctx_Temp(self.mem):
            with state.ctx_HayNode(self.hay_state, hay_name):
              # Note: we want all haynode invocations in the block to appear as
              # our 'children', recursively
              block_attrs = self.cmd_ev.EvalBlock(block)

          attrs = NewDict()  # type: Dict[str, Any]
          for name, cell in iteritems(block_attrs):

            # User can hide variables with _ suffix
            # e.g. for i_ in foo bar { echo $i_ }
            if name.endswith('_'):
              continue

            val = cell.val
            UP_val = val
            with tagswitch(val) as case:
              # similar to LookupVar in oil_lang/expr_eval.py
              if case(value_e.Str):
                val = cast(value__Str, UP_val)
                obj = val.s  # type: Any
              elif case(value_e.MaybeStrArray):
                val = cast(value__MaybeStrArray, UP_val)
                obj = val.strs
              elif case(value_e.AssocArray):
                val = cast(value__AssocArray, UP_val)
                obj = val.d
              elif case(value_e.Obj):
                val = cast(value__Obj, UP_val)
                obj = val.obj
              else:
                e_die("Can't serialize value of type %d" % val.tag_())
            attrs[name] = obj

          result['attrs'] = attrs

      return 0


  _HAY_ACTION_ERROR = "builtin expects 'define', 'reset' or 'pp'"

  class Hay(vm._Builtin):
    """
    hay define -- package user
    hay define -- user/foo user/bar  # second level
    hay pp
    hay reset
    """
    def __init__(self, hay_state, mutable_opts, mem, cmd_ev):
      # type: (state.Hay, MutableOpts, state.Mem, CommandEvaluator) -> None
      self.hay_state = hay_state
      self.mutable_opts = mutable_opts
      self.mem = mem
      self.cmd_ev = cmd_ev  # To run blocks

    def Run(self, cmd_val):
      # type: (cmd_value__Argv) -> int
      arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
      arg_r.Next()  # skip 'hay'

      action, action_spid = arg_r.Peek2()
      if action is None:
        e_usage(_HAY_ACTION_ERROR, span_id=action_spid)
      arg_r.Next()

      if action == 'define':
        # TODO: accept --
        #arg, arg_r = flag_spec.ParseCmdVal('hay-define', cmd_val)

        # arg = args.Parse(JSON_WRITE_SPEC, arg_r)
        first, _ = arg_r.Peek2()
        if first is None:
          e_usage('define expected a name', span_id=action_spid)

        names, name_spids = arg_r.Rest2()
        for i, name in enumerate(names):
          path = name.split('/')
          for p in path:
            if len(p) == 0:
              e_usage("got invalid path %r.  Parts can't be empty." % name,
                      span_id=name_spids[i])
          self.hay_state.DefinePath(path)

      elif action == 'eval':
        # hay eval :myvar { ... }
        #
        # - turn on oil:all
        # - set _running_hay -- so that hay "first words" are visible
        # - then set the variable name to the result

        var_name, _ = arg_r.ReadRequired2("expected variable name")
        if var_name.startswith(':'):
          var_name = var_name[1:]
          # TODO: This could be fatal?

        block = typed_args.GetOneBlock(cmd_val.typed_args)
        if not block:  # 'package foo' is OK
          e_usage('eval expected a block')

        with state.ctx_HayEval(self.hay_state, self.mutable_opts, self.mem):
          # Note: we want all haynode invocations in the block to appear as
          # our 'children', recursively
          unused = self.cmd_ev.EvalBlock(block)

        result = self.hay_state.Result()

        self.mem.SetValue(
            lvalue.Named(var_name), value.Obj(result), scope_e.LocalOnly)

      elif action == 'reset':
        self.hay_state.Reset()

      elif action == 'pp':
        tree = self.hay_state.root_defs.PrettyTree()
        ast_f = fmt.DetectConsoleOutput(mylib.Stdout())
        fmt.PrintTree(tree, ast_f)
        ast_f.write('\n')

      else:
        e_usage(_HAY_ACTION_ERROR, span_id=action_spid)

      return 0
