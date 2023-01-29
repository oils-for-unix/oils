"""
builtin_comp.py - Completion builtins
"""

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import value_e, value__MaybeStrArray
from core import completion
from core import error
from core import ui
from core import vm
#from core.pyerror import log
from frontend import flag_spec
from frontend import args
from frontend import consts
from core import state

from typing import Dict, List, Iterator, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv, Proc
  from core.completion import Lookup, OptionState, Api, UserSpec
  from core.ui import ErrorFormatter
  from core.state import Mem
  from frontend.args import _Attributes
  from frontend.parse_lib import ParseContext
  from osh.cmd_eval import CommandEvaluator
  from osh.split import SplitContext
  from osh.word_eval import NormalWordEvaluator


HELP_TOPICS = [] # type: List[str]

from mycpp import mylib
if mylib.PYTHON:
  # - Catch ImportEror because we don't want libcmark.so dependency for
  #   build/py.sh minimal
  # - For now, ignore a type error in minimal build.
  # - TODO: Rewrite help builtin and remove dep on CommonMark 
  try:
    from _devbuild.gen import help_  # type: ignore
    HELP_TOPICS = help_.TOPICS
  except ImportError:
    pass


class _FixedWordsAction(completion.CompletionAction):
  def __init__(self, d):
    # type: (List[str]) -> None
    self.d = d

  def Matches(self, comp):
    # type: (Api) -> Iterator[str]
    for name in sorted(self.d):
      if name.startswith(comp.to_complete):
        yield name


class _DynamicProcDictAction(completion.CompletionAction):
  """For completing from proc and aliases dicts, which are mutable.
  Note: this is the same as _FixedWordsAction now, but won't be when the code
  is statically typed!
  """
  def __init__(self, d):
    # type: (Dict[str, Proc]) -> None
    self.d = d

  def Matches(self, comp):
    # type: (Api) -> Iterator[str]
    for name in sorted(self.d):
      if name.startswith(comp.to_complete):
        yield name


class _DynamicStrDictAction(completion.CompletionAction):
  """For completing from proc and aliases dicts, which are mutable.
  Note: this is the same as _FixedWordsAction now, but won't be when the code
  is statically typed!
  """
  def __init__(self, d):
    # type: (Dict[str, str]) -> None
    self.d = d

  def Matches(self, comp):
    # type: (Api) -> Iterator[str]
    for name in sorted(self.d):
      if name.startswith(comp.to_complete):
        yield name


class SpecBuilder(object):

  def __init__(self,
               cmd_ev,  # type: CommandEvaluator
               parse_ctx,  # type: ParseContext
               word_ev,  # type: NormalWordEvaluator
               splitter,  # type: SplitContext
               comp_lookup,  # type: Lookup
               errfmt  # type: ui.ErrorFormatter
               ):
    # type: (...) -> None
    """
    Args:
      cmd_ev: CommandEvaluator for compgen -F
      parse_ctx, word_ev, splitter: for compgen -W
    """
    self.cmd_ev = cmd_ev
    self.parse_ctx = parse_ctx
    self.word_ev = word_ev
    self.splitter = splitter
    self.comp_lookup = comp_lookup
    self.errfmt = errfmt

  def Build(self, argv, attrs, base_opts):
    # type: (List[str], _Attributes, Dict[str, bool]) -> UserSpec
    """Given flags to complete/compgen, return a UserSpec."""
    cmd_ev = self.cmd_ev

    # arg_types.compgen is a subset of arg_types.complete (the two users of this
    # function), so we use the generate type for compgen here.
    arg = arg_types.compgen(attrs.attrs)
    actions = []  # type: List[completion.CompletionAction]

    # NOTE: bash doesn't actually check the name until completion time, but
    # obviously it's better to check here.
    if arg.F is not None:
      func_name = arg.F
      func = cmd_ev.procs.get(func_name)
      if func is None:
        raise error.Usage('Function %r not found' % func_name)
      actions.append(completion.ShellFuncAction(cmd_ev, func, self.comp_lookup))

    # NOTE: We need completion for -A action itself!!!  bash seems to have it.
    for name in attrs.actions:
      if name == 'alias':
        a = _DynamicStrDictAction(self.parse_ctx.aliases)  # type: completion.CompletionAction

      elif name == 'binding':
        # TODO: Where do we get this from?
        a = _FixedWordsAction(['vi-delete'])

      elif name == 'command':
        # compgen -A command in bash is SIX things: aliases, builtins,
        # functions, keywords, external commands relative to the current
        # directory, and external commands in $PATH.

        actions.append(_FixedWordsAction(consts.BUILTIN_NAMES))
        actions.append(_DynamicStrDictAction(self.parse_ctx.aliases))
        actions.append(_DynamicProcDictAction(cmd_ev.procs))
        actions.append(_FixedWordsAction(consts.OSH_KEYWORD_NAMES))
        actions.append(completion.FileSystemAction(False, True, False))

        # Look on the file system.
        a = completion.ExternalCommandAction(cmd_ev.mem)

      elif name == 'directory':
        a = completion.FileSystemAction(True, False, False)

      elif name == 'file':
        a = completion.FileSystemAction(False, False, False)

      elif name == 'function':
        a = _DynamicProcDictAction(cmd_ev.procs)

      elif name == 'job':
        a = _FixedWordsAction(['jobs-not-implemented'])

      elif name == 'user':
        a = completion.UsersAction()

      elif name == 'variable':
        a = completion.VariablesAction(cmd_ev.mem)

      elif name == 'helptopic':
        # Note: it would be nice to have 'helpgroup' for help -i too
        a = _FixedWordsAction(HELP_TOPICS)

      elif name == 'setopt':
        a = _FixedWordsAction(consts.SET_OPTION_NAMES)

      elif name == 'shopt':
        a = _FixedWordsAction(consts.SHOPT_OPTION_NAMES)

      elif name == 'signal':
        a = _FixedWordsAction(['TODO:signals'])

      elif name == 'stopped':
        a = _FixedWordsAction(['jobs-not-implemented'])

      else:
        raise NotImplementedError(name)

      actions.append(a)

    # e.g. -W comes after -A directory
    if arg.W is not None:  # could be ''
      # NOTES:
      # - Parsing is done at REGISTRATION time, but execution and splitting is
      #   done at COMPLETION time (when the user hits tab).  So parse errors
      #   happen early.
      w_parser = self.parse_ctx.MakeWordParserForPlugin(arg.W)

      try:
        arg_word = w_parser.ReadForPlugin()
      except error.Parse as e:
        self.errfmt.PrettyPrintError(e)
        raise  # Let 'complete' or 'compgen' return 2

      a = completion.DynamicWordsAction(
          self.word_ev, self.splitter, arg_word, self.errfmt)
      actions.append(a)

    extra_actions = []  # type: List[completion.CompletionAction]
    if base_opts.get('plusdirs', False):
      extra_actions.append(completion.FileSystemAction(True, False, False))

    # These only happen if there were zero shown.
    else_actions = []  # type: List[completion.CompletionAction]
    if base_opts.get('default', False):
      else_actions.append(completion.FileSystemAction(False, False, False))
    if base_opts.get('dirnames', False):
      else_actions.append(completion.FileSystemAction(True, False, False))

    if not actions and not else_actions:
      raise error.Usage('No actions defined in completion: %s' % argv)

    p = completion.DefaultPredicate()  # type: completion._Predicate
    if arg.X is not None:
      filter_pat = arg.X
      if filter_pat.startswith('!'):
        p = completion.GlobPredicate(False, filter_pat[1:])
      else:
        p = completion.GlobPredicate(True, filter_pat)

    # mycpp: rewrite of or
    prefix = arg.P
    if prefix is None:
      prefix = ''

    # mycpp: rewrite of or
    suffix = arg.S
    if suffix is None:
      suffix = ''

    return completion.UserSpec(actions, extra_actions, else_actions, p,
                               prefix, suffix)


class Complete(vm._Builtin):
  """complete builtin - register a completion function.

  NOTE: It's has an CommandEvaluator because it creates a ShellFuncAction, which
  needs an CommandEvaluator.
  """
  def __init__(self, spec_builder, comp_lookup):
    # type: (SpecBuilder, Lookup) -> None
    self.spec_builder = spec_builder
    self.comp_lookup = comp_lookup

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    arg_r = args.Reader(cmd_val.argv, cmd_val.arg_spids)
    arg_r.Next()

    attrs = flag_spec.ParseMore('complete', arg_r)
    arg = arg_types.complete(attrs.attrs)
    # TODO: process arg.opt_changes
    #log('arg %s', arg)

    commands = arg_r.Rest()

    if arg.D:
      commands.append('__fallback')  # if the command doesn't match anything
    if arg.E:
      commands.append('__first')  # empty line

    if len(commands) == 0:
      self.comp_lookup.PrintSpecs()
      return 0

    base_opts = dict(attrs.opt_changes)
    try:
      user_spec = self.spec_builder.Build(cmd_val.argv, attrs, base_opts)
    except error.Parse as e:
      # error printed above
      return 2
    for command in commands:
      self.comp_lookup.RegisterName(command, base_opts, user_spec)

    # TODO: Hook this up
    patterns = []  # type: List[str]
    for pat in patterns:
      self.comp_lookup.RegisterGlob(pat, base_opts, user_spec)

    return 0


class CompGen(vm._Builtin):
  """Print completions on stdout."""

  def __init__(self, spec_builder):
    # type: (SpecBuilder) -> None
    self.spec_builder = spec_builder

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    arg_r = args.Reader(cmd_val.argv, cmd_val.arg_spids)
    arg_r.Next()

    arg = flag_spec.ParseMore('compgen', arg_r)

    if arg_r.AtEnd():
      to_complete = ''
    else:
      to_complete = arg_r.Peek()
      arg_r.Next()
      # bash allows extra arguments here.
      #if not arg_r.AtEnd():
      #  raise error.Usage('Extra arguments')

    matched = False

    base_opts = dict(arg.opt_changes)
    try:
      user_spec = self.spec_builder.Build(cmd_val.argv, arg, base_opts)
    except error.Parse as e:
      # error printed above
      return 2

    # NOTE: Matching bash in passing dummy values for COMP_WORDS and COMP_CWORD,
    # and also showing ALL COMPREPLY reuslts, not just the ones that start with
    # the word to complete.
    matched = False 
    comp = completion.Api('', 0, 0)
    comp.Update('compgen', to_complete, '', -1, None)
    try:
      for m, _ in user_spec.Matches(comp):
        matched = True
        print(m)
    except error.FatalRuntime:
      # - DynamicWordsAction: We already printed an error, so return failure.
      return 1

    # - ShellFuncAction: We do NOT get FatalRuntimeError.  We printed an error
    # in the executor, but RunFuncForCompletion swallows failures.  See test
    # case in builtin-completion.test.sh.

    # TODO:
    # - need to dedupe results.

    return 0 if matched else 1


class CompOpt(vm._Builtin):
  """Adjust options inside user-defined completion functions."""

  def __init__(self, comp_state, errfmt):
    # type: (OptionState, ErrorFormatter) -> None
    self.comp_state = comp_state
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    arg_r = args.Reader(cmd_val.argv, cmd_val.arg_spids)
    arg_r.Next()

    arg = flag_spec.ParseMore('compopt', arg_r)

    if not self.comp_state.currently_completing:  # bash also checks this.
      self.errfmt.Print_('compopt: not currently executing a completion function')
      return 1

    self.comp_state.dynamic_opts.update(arg.opt_changes)
    #log('compopt: %s', arg)
    #log('compopt %s', base_opts)
    return 0


class CompAdjust(vm._Builtin):
  """
  Uses COMP_ARGV and flags produce the 'words' array.  Also sets $cur, $prev,
  $cword, and $split.

  Note that we do not use COMP_WORDS, which already has splitting applied.
  bash-completion does a hack to undo or "reassemble" words after erroneous
  splitting.
  """
  def __init__(self, mem):
    # type: (Mem) -> None
    self.mem = mem

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    arg_r = args.Reader(cmd_val.argv, cmd_val.arg_spids)
    arg_r.Next()

    attrs = flag_spec.ParseMore('compadjust', arg_r)
    arg = arg_types.compadjust(attrs.attrs)
    var_names = arg_r.Rest()  # Output variables to set
    for name in var_names:
      # Ironically we could complete these
      if name not in ['cur', 'prev', 'words', 'cword']:
        raise error.Usage('Invalid output variable name %r' % name)
    #print(arg)

    # TODO: How does the user test a completion function programmatically?  Set
    # COMP_ARGV?
    val = self.mem.GetValue('COMP_ARGV')
    if val.tag_() != value_e.MaybeStrArray:
      raise error.Usage("COMP_ARGV should be an array")
    comp_argv = cast(value__MaybeStrArray, val).strs

    # These are the ones from COMP_WORDBREAKS that we care about.  The rest occur
    # "outside" of words.
    break_chars = [':', '=']
    if arg.s:  # implied
      break_chars.remove('=')
    # NOTE: The syntax is -n := and not -n : -n =.
    # mycpp: rewrite of or
    omit_chars = arg.n
    if omit_chars is None:
      omit_chars = ''

    for c in omit_chars:
      if c in break_chars:
        break_chars.remove(c)

    # argv adjusted according to 'break_chars'.
    adjusted_argv = []  # type: List[str]
    for a in comp_argv:
      completion.AdjustArg(a, break_chars, adjusted_argv)

    if 'words' in var_names:
      state.BuiltinSetArray(self.mem, 'words', adjusted_argv)

    n = len(adjusted_argv)
    cur = adjusted_argv[-1]
    prev = '' if n < 2 else adjusted_argv[-2]

    if arg.s:
      if cur.startswith('--') and '=' in cur:  # Split into flag name and value
        # mycpp: rewrite of multiple-assignment
        prev, cur = mylib.split_once(cur, '=')
        split = 'true'
      else:
        split = 'false'
      # Do NOT set 'split' without -s.  Caller might not have declared it.
      # Also does not respect var_names, because we don't need it.
      state.BuiltinSetString(self.mem, 'split', split)

    if 'cur' in var_names:
      state.BuiltinSetString(self.mem, 'cur', cur)
    if 'prev' in var_names:
      state.BuiltinSetString(self.mem, 'prev', prev)
    if 'cword' in var_names:
      # Same weird invariant after adjustment
      state.BuiltinSetString(self.mem, 'cword', str(n-1))

    return 0
