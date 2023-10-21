#!/usr/bin/env python2
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.syntax_asdl import loc
from _devbuild.gen.runtime_asdl import value, value_e
from core import completion
from core import error
from core.error import e_usage
from core import state
from core import ui
from core import vm
from mycpp import mylib
from mycpp.mylib import log, print_stderr
from frontend import flag_spec
from frontend import args
from frontend import consts

import yajl

_ = log

from typing import Dict, List, Iterator, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from core.completion import Lookup, OptionState, Api, UserSpec
    from core.ui import ErrorFormatter
    from frontend.args import _Attributes
    from frontend.parse_lib import ParseContext
    from osh.cmd_eval import CommandEvaluator
    from osh.split import SplitContext
    from osh.word_eval import NormalWordEvaluator


class _FixedWordsAction(completion.CompletionAction):

    def __init__(self, d):
        # type: (List[str]) -> None
        self.d = d

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]
        for name in sorted(self.d):
            if name.startswith(comp.to_complete):
                yield name

    def Print(self, f):
        # type: (mylib.BufWriter) -> None
        f.write('FixedWordsAction ')


class _DynamicProcDictAction(completion.CompletionAction):
    """For completing from proc and aliases dicts, which are mutable.

    Note: this is the same as _FixedWordsAction now, but won't be when the code
    is statically typed!
    """

    def __init__(self, d):
        # type: (Dict[str, value.Proc]) -> None
        self.d = d

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]
        for name in sorted(self.d):
            if name.startswith(comp.to_complete):
                yield name

    def Print(self, f):
        # type: (mylib.BufWriter) -> None
        f.write('DynamicProcDictAction ')


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

    def Print(self, f):
        # type: (mylib.BufWriter) -> None
        f.write('DynamicStrDictAction ')


class SpecBuilder(object):

    def __init__(
            self,
            cmd_ev,  # type: CommandEvaluator
            parse_ctx,  # type: ParseContext
            word_ev,  # type: NormalWordEvaluator
            splitter,  # type: SplitContext
            comp_lookup,  # type: Lookup
            help_data,  # type: Dict[str, str]
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

        self.help_data = help_data
        # lazily initialized
        self.topic_list = None  # type: List[str]

        self.errfmt = errfmt

    def Build(self, argv, attrs, base_opts):
        # type: (List[str], _Attributes, Dict[str, bool]) -> UserSpec
        """Given flags to complete/compgen, return a UserSpec.

        Args:
          argv: only used for error message
        """
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
                raise error.Usage('function %r not found' % func_name,
                                  loc.Missing)
            actions.append(
                completion.ShellFuncAction(cmd_ev, func, self.comp_lookup))

        if arg.C is not None:
            # this can be a shell FUNCTION too, not just an external command
            # Honestly seems better than -F?  Does it also get COMP_CWORD?
            command = arg.C
            actions.append(completion.CommandAction(cmd_ev, command))
            print_stderr('osh warning: complete -C not implemented')

        # NOTE: We need completion for -A action itself!!!  bash seems to have it.
        for name in attrs.actions:
            if name == 'alias':
                a = _DynamicStrDictAction(
                    self.parse_ctx.aliases
                )  # type: completion.CompletionAction

            elif name == 'binding':
                # TODO: Where do we get this from?
                a = _FixedWordsAction(['vi-delete'])

            elif name == 'builtin':
                a = _FixedWordsAction(consts.BUILTIN_NAMES)

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
                # Lazy initialization
                if self.topic_list is None:
                    self.topic_list = self.help_data.keys()
                a = _FixedWordsAction(self.topic_list)

            elif name == 'setopt':
                a = _FixedWordsAction(consts.SET_OPTION_NAMES)

            elif name == 'shopt':
                a = _FixedWordsAction(consts.SHOPT_OPTION_NAMES)

            elif name == 'signal':
                a = _FixedWordsAction(['TODO:signals'])

            elif name == 'stopped':
                a = _FixedWordsAction(['jobs-not-implemented'])

            else:
                raise AssertionError(name)

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

            a = completion.DynamicWordsAction(self.word_ev, self.splitter,
                                              arg_word, self.errfmt)
            actions.append(a)

        extra_actions = []  # type: List[completion.CompletionAction]
        if base_opts.get('plusdirs', False):
            extra_actions.append(
                completion.FileSystemAction(True, False, False))

        # These only happen if there were zero shown.
        else_actions = []  # type: List[completion.CompletionAction]
        if base_opts.get('default', False):
            else_actions.append(
                completion.FileSystemAction(False, False, False))
        if base_opts.get('dirnames', False):
            else_actions.append(completion.FileSystemAction(
                True, False, False))

        if len(actions) == 0 and len(else_actions) == 0:
            raise error.Usage(
                'No actions defined in completion: %s' % ' '.join(argv),
                loc.Missing)

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
        # type: (cmd_value.Argv) -> int
        arg_r = args.Reader(cmd_val.argv, cmd_val.arg_locs)
        arg_r.Next()

        attrs = flag_spec.ParseMore('complete', arg_r)
        arg = arg_types.complete(attrs.attrs)
        # TODO: process arg.opt_changes

        commands = arg_r.Rest()

        if arg.D:
            # if the command doesn't match anything
            commands.append('__fallback')
        if arg.E:
            commands.append('__first')  # empty line

        if len(commands) == 0:
            if len(cmd_val.argv) == 1:  # nothing passed at all
                assert cmd_val.argv[0] == 'complete'

                self.comp_lookup.PrintSpecs()
                return 0
            else:
                # complete -F f is an error
                raise error.Usage('expected 1 or more commands', loc.Missing)

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
        # type: (cmd_value.Argv) -> int
        arg_r = args.Reader(cmd_val.argv, cmd_val.arg_locs)
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

        # NOTE: Matching bash in passing dummy values for COMP_WORDS and
        # COMP_CWORD, and also showing ALL COMPREPLY results, not just the ones
        # that start
        # with the word to complete.
        matched = False
        comp = completion.Api('', 0, 0)  # empty string
        comp.Update('compgen', to_complete, '', -1, None)
        try:
            for m, _ in user_spec.AllMatches(comp):
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
        # type: (cmd_value.Argv) -> int
        arg_r = args.Reader(cmd_val.argv, cmd_val.arg_locs)
        arg_r.Next()

        arg = flag_spec.ParseMore('compopt', arg_r)

        if not self.comp_state.currently_completing:  # bash also checks this.
            self.errfmt.Print_(
                'compopt: not currently executing a completion function')
            return 1

        self.comp_state.dynamic_opts.update(arg.opt_changes)
        #log('compopt: %s', arg)
        #log('compopt %s', base_opts)
        return 0


class CompAdjust(vm._Builtin):
    """Uses COMP_ARGV and flags produce the 'words' array.  Also sets $cur,

    $prev,

    $cword, and $split.

    Note that we do not use COMP_WORDS, which already has splitting applied.
    bash-completion does a hack to undo or "reassemble" words after erroneous
    splitting.
    """

    def __init__(self, mem):
        # type: (state.Mem) -> None
        self.mem = mem

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg_r = args.Reader(cmd_val.argv, cmd_val.arg_locs)
        arg_r.Next()

        attrs = flag_spec.ParseMore('compadjust', arg_r)
        arg = arg_types.compadjust(attrs.attrs)
        var_names = arg_r.Rest()  # Output variables to set
        for name in var_names:
            # Ironically we could complete these
            if name not in ['cur', 'prev', 'words', 'cword']:
                raise error.Usage('Invalid output variable name %r' % name,
                                  loc.Missing)
        #print(arg)

        # TODO: How does the user test a completion function programmatically?  Set
        # COMP_ARGV?
        val = self.mem.GetValue('COMP_ARGV')
        if val.tag() != value_e.BashArray:
            raise error.Usage("COMP_ARGV should be an array", loc.Missing)
        comp_argv = cast(value.BashArray, val).strs

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
            if cur.startswith('--') and '=' in cur:
                # Split into flag name and value
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
            state.BuiltinSetString(self.mem, 'cword', str(n - 1))

        return 0


class CompExport(vm._Builtin):

    def __init__(self, root_comp):
        # type: (completion.RootCompleter) -> None
        self.root_comp = root_comp

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg_r = args.Reader(cmd_val.argv, cmd_val.arg_locs)
        arg_r.Next()

        attrs = flag_spec.ParseMore('compexport', arg_r)
        arg = arg_types.compexport(attrs.attrs)

        if arg.c is None:
            e_usage('expected a -c string, like sh -c', loc.Missing)

        begin = 0 if arg.begin == -1 else arg.begin
        end = len(arg.c) if arg.end == -1 else arg.end

        #log('%r begin %d end %d', arg.c, begin, end)

        # Copied from completion.ReadlineCallback
        comp = completion.Api(line=arg.c, begin=begin, end=end)
        it = self.root_comp.Matches(comp)

        #print(comp)
        #print(self.root_comp)

        comp_matches = list(it)
        comp_matches.reverse()

        if arg.format == 'jlines':
            for m in comp_matches:
                # TODO: change to J8 notation
                # - Since there are spaces, maybe_encode() always adds quotes.
                # - Could use a jlines=True J8 option to specify that newlines and
                #   non-UTF-8 unprintable bytes cause quotes.  But not spaces.
                #
                # Also, there's always a trailing space!  Gah.

                if mylib.PYTHON:
                    print(yajl.dumps(m, indent=-1))

        elif arg.format == 'tsv8':
            log('TSV8 format not implemented')
        else:
            raise AssertionError()

        return 0
