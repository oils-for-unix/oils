#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
completion.py - Tab completion.

Architecture:

Completion should run in threads?  For two reasons:

- Completion can be slow -- e.g. completion for distributed resources
- Because readline has a weird interface, and then you can implement
  "iterators" in C++ or oil.  They just push onto a PIPE.  Use a netstring
  protocol and self-pipe?
- completion can be in another process anyway?

Does that mean the user code gets run in an entirely separate interpreter?  The
whole lexer/parser/cmd_eval combo has to be thread-safe.  Does it get a copy of
the same startup state?

Features TODO:
  - complete flags after alias expansion
  - complete history expansions like zsh
  - complete flags for all builtins, using frontend/args.py?
    - might need a special error token

bash note: most of this stuff is in pcomplete.c and bashline.c (4K lines!).
Uses ITEMLIST with a bunch of flags.
"""
from __future__ import print_function

import time as time_

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import (CompoundWord, word_part_e, word_t,
                                       redir_param_e, Token)
from _devbuild.gen.runtime_asdl import (scope_e, comp_action_e, comp_action_t)
from _devbuild.gen.types_asdl import redir_arg_type_e
from _devbuild.gen.value_asdl import (value, value_e)
from core import error
from core import pyos
from core import state
from core import ui
from core import util
from frontend import consts
from frontend import lexer
from frontend import location
from frontend import reader
from mycpp import mylib
from mycpp.mylib import print_stderr, iteritems, log
from osh.string_ops import ShellQuoteB
from osh import word_
from pylib import os_path
from pylib import path_stat

import libc
import posix_ as posix
from posix_ import X_OK  # translated directly to C macro

from typing import (Dict, Tuple, List, Iterator, Optional, Any, cast,
                    TYPE_CHECKING)
if TYPE_CHECKING:
    from core.comp_ui import State
    from core.state import Mem
    from frontend.py_readline import Readline
    from core.util import _DebugFile
    from frontend.parse_lib import ParseContext
    from osh.cmd_eval import CommandEvaluator
    from osh.split import SplitContext
    from osh.word_eval import AbstractWordEvaluator

# To quote completion candidates.
#   !    is for history expansion, which only happens interactively, but
#        completion only does too.
#   *?[] are for globs
#   {}   are for brace expansion
#   ~    in filenames should be quoted
#
# TODO: Also escape tabs as \t and newlines at \n?
# SHELL_META_CHARS = r' ~`!$&|;()\"*?[]{}<>' + "'"


class _RetryCompletion(Exception):
    """For the 'exit 124' protocol."""

    def __init__(self):
        # type: () -> None
        pass


# mycpp: rewrite of multiple-assignment
# Character types
CH_Break = 0
CH_Other = 1

# mycpp: rewrite of multiple-assignment
# States
ST_Begin = 0
ST_Break = 1
ST_Other = 2


# State machine definition.
# (state, char) -> (new state, emit span)
# NOT: This would be less verbose as a dict, but a C++ compiler will turn this
# into a lookup table anyway.
def _TRANSITIONS(state, ch):
    # type: (int, int) -> Tuple[int, bool]
    if state == ST_Begin and ch == CH_Break:
        return (ST_Break, False)

    if state == ST_Begin and ch == CH_Other:
        return (ST_Other, False)

    if state == ST_Break and ch == CH_Break:
        return (ST_Break, False)

    if state == ST_Break and ch == CH_Other:
        return (ST_Other, True)

    if state == ST_Other and ch == CH_Break:
        return (ST_Break, True)

    if state == ST_Other and ch == CH_Other:
        return (ST_Other, False)

    raise ValueError("invalid (state, ch) pair")


def AdjustArg(arg, break_chars, argv_out):
    # type: (str, List[str], List[str]) -> None
    # stores the end of each span
    end_indices = []  # type: List[int]
    state = ST_Begin
    for i, c in enumerate(arg):
        ch = CH_Break if c in break_chars else CH_Other
        state, emit_span = _TRANSITIONS(state, ch)
        if emit_span:
            end_indices.append(i)

    # Always emit a span at the end (even for empty string)
    end_indices.append(len(arg))

    begin = 0
    for end in end_indices:
        argv_out.append(arg[begin:end])
        begin = end


# NOTE: How to create temporary options?  With copy.deepcopy()?
# We might want that as a test for OVM.  Copying is similar to garbage
# collection in that you walk a graph.

# These values should never be mutated.
_DEFAULT_OPTS = {}  # type: Dict[str, bool]


class OptionState(object):
    """Stores the compopt state of the CURRENT completion."""

    def __init__(self):
        # type: () -> None
        # For the IN-PROGRESS completion.
        self.currently_completing = False
        # should be SET to a COPY of the registration options by the completer.
        self.dynamic_opts = None  # type: Dict[str, bool]


class ctx_Completing(object):

    def __init__(self, compopt_state):
        # type: (OptionState) -> None
        compopt_state.currently_completing = True
        self.compopt_state = compopt_state

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.compopt_state.currently_completing = False


def _PrintOpts(opts, f):
    # type: (Dict[str, bool], mylib.BufWriter) -> None
    f.write('  (')
    for k, v in iteritems(opts):
        f.write(' %s=%s' % (k, '1' if v else '0'))
    f.write(' )\n')


class Lookup(object):
    """Stores completion hooks registered by the user."""

    def __init__(self):
        # type: () -> None

        # Pseudo-commands __first and __fallback are for -E and -D.
        empty_spec = UserSpec([], [], [], DefaultPredicate(), '', '')
        do_nothing = (_DEFAULT_OPTS, empty_spec)
        self.lookup = {
            '__fallback': do_nothing,
            '__first': do_nothing,
        }  # type: Dict[str, Tuple[Dict[str, bool], UserSpec]]

        # for the 124 protocol
        self.commands_with_spec_changes = []  # type: List[str]

        # So you can register *.sh, unlike bash.  List of (glob, [actions]),
        # searched linearly.
        self.patterns = []  # type: List[Tuple[str, Dict[str, bool], UserSpec]]

    def __str__(self):
        # type: () -> str
        return '<completion.Lookup %s>' % self.lookup

    def PrintSpecs(self):
        # type: () -> None
        """ For complete -p """

        # TODO: This format could be nicer / round-trippable?

        f = mylib.BufWriter()

        f.write('[Commands]\n')
        for name in sorted(self.lookup):
            base_opts, user_spec = self.lookup[name]

            f.write('%s:\n' % name)
            _PrintOpts(base_opts, f)

            user_spec.PrintSpec(f)

        f.write('[Patterns]\n')
        for pat, base_opts, spec in self.patterns:
            #print('%s %s %s' % (pat, base_opts, spec))
            f.write('%s:\n' % pat)
            _PrintOpts(base_opts, f)

            user_spec.PrintSpec(f)

        # Print to stderr since it's not parse-able
        print_stderr(f.getvalue())

    def ClearCommandsChanged(self):
        # type: () -> None
        del self.commands_with_spec_changes[:]

    def GetCommandsChanged(self):
        # type: () -> List[str]
        return self.commands_with_spec_changes

    def RegisterName(self, name, base_opts, user_spec):
        # type: (str, Dict[str, bool], UserSpec) -> None
        """Register a completion action with a name.

        Used by the 'complete' builtin.
        """
        self.lookup[name] = (base_opts, user_spec)

        if name not in ('__fallback', '__first'):
            self.commands_with_spec_changes.append(name)

    def RegisterGlob(self, glob_pat, base_opts, user_spec):
        # type: (str, Dict[str, bool], UserSpec) -> None
        self.patterns.append((glob_pat, base_opts, user_spec))

    def GetSpecForName(self, argv0):
        # type: (str) -> Tuple[Dict[str, bool], UserSpec]
        """
        Args:
          argv0: A finished argv0 to lookup
        """
        pair = self.lookup.get(argv0)  # NOTE: Could be ''
        if pair:
            # mycpp: rewrite of tuple return
            a, b = pair
            return (a, b)

        key = os_path.basename(argv0)
        pair = self.lookup.get(key)
        if pair:
            # mycpp: rewrite of tuple return
            a, b = pair
            return (a, b)

        for glob_pat, base_opts, user_spec in self.patterns:
            #log('Matching %r %r', key, glob_pat)
            if libc.fnmatch(glob_pat, key):
                return base_opts, user_spec

        return None, None

    def GetFirstSpec(self):
        # type: () -> Tuple[Dict[str, bool], UserSpec]
        # mycpp: rewrite of tuple return
        a, b = self.lookup['__first']
        return (a, b)

    def GetFallback(self):
        # type: () -> Tuple[Dict[str, bool], UserSpec]
        # mycpp: rewrite of tuple return
        a, b = self.lookup['__fallback']
        return (a, b)


class Api(object):

    def __init__(self, line, begin, end):
        # type: (str, int, int) -> None
        """
        Args:
          index: if -1, then we're running through compgen
        """
        self.line = line
        self.begin = begin
        self.end = end
        self.first = None  # type: str
        self.to_complete = None  # type: str
        self.prev = None  # type: str
        self.index = -1  # type: int
        self.partial_argv = []  # type: List[str]
        # NOTE: COMP_WORDBREAKS is initialized in Mem().

    # NOTE: to_complete could be 'cur'
    def Update(self, first, to_complete, prev, index, partial_argv):
        # type: (str, str, str, int, List[str]) -> None
        """Added after we've done parsing."""
        self.first = first
        self.to_complete = to_complete
        self.prev = prev
        self.index = index  # COMP_CWORD
        # COMP_ARGV and COMP_WORDS can be derived from this
        self.partial_argv = partial_argv
        if self.partial_argv is None:
            self.partial_argv = []

    def __repr__(self):
        # type: () -> str
        """For testing."""
        return '<Api %r %d-%d>' % (self.line, self.begin, self.end)


#
# Actions
#


class CompletionAction(object):

    def __init__(self):
        # type: () -> None
        pass

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]
        pass

    def ActionKind(self):
        # type: () -> comp_action_t
        return comp_action_e.Other

    def Print(self, f):
        # type: (mylib.BufWriter) -> None
        f.write('???CompletionAction ')

    def __repr__(self):
        # type: () -> str
        return self.__class__.__name__


class UsersAction(CompletionAction):
    """complete -A user."""

    def __init__(self):
        # type: () -> None
        pass

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]
        for u in pyos.GetAllUsers():
            name = u.pw_name
            if name.startswith(comp.to_complete):
                yield name

    def Print(self, f):
        # type: (mylib.BufWriter) -> None
        f.write('UserAction ')


class TestAction(CompletionAction):

    def __init__(self, words, delay=0.0):
        # type: (List[str], Optional[float]) -> None
        self.words = words
        self.delay = delay

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]
        for w in self.words:
            if w.startswith(comp.to_complete):
                if self.delay != 0.0:
                    time_.sleep(self.delay)
                yield w

    def Print(self, f):
        # type: (mylib.BufWriter) -> None
        f.write('TestAction ')


class DynamicWordsAction(CompletionAction):
    """compgen -W '$(echo one two three)'."""

    def __init__(
            self,
            word_ev,  # type: AbstractWordEvaluator
            splitter,  # type: SplitContext
            arg_word,  # type: CompoundWord
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.word_ev = word_ev
        self.splitter = splitter
        self.arg_word = arg_word
        self.errfmt = errfmt

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]
        try:
            val = self.word_ev.EvalWordToString(self.arg_word)
        except error.FatalRuntime as e:
            self.errfmt.PrettyPrintError(e)
            raise

        # SplitForWordEval() Allows \ escapes
        candidates = self.splitter.SplitForWordEval(val.s)
        for c in candidates:
            if c.startswith(comp.to_complete):
                yield c

    def Print(self, f):
        # type: (mylib.BufWriter) -> None
        f.write('DynamicWordsAction ')


class FileSystemAction(CompletionAction):
    """Complete paths from the file system.

    Directories will have a / suffix.
    """

    def __init__(self, dirs_only, exec_only, add_slash):
        # type: (bool, bool, bool) -> None
        self.dirs_only = dirs_only
        self.exec_only = exec_only

        # This is for redirects, not for UserSpec, which should respect compopt -o
        # filenames.
        self.add_slash = add_slash  # for directories

    def ActionKind(self):
        # type: () -> comp_action_t
        return comp_action_e.FileSystem

    def Print(self, f):
        # type: (mylib.BufWriter) -> None
        f.write('FileSystemAction ')

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]
        to_complete = comp.to_complete

        # Problem: .. and ../.. don't complete /.
        # TODO: Set display_pos before fixing this.

        #import os
        #to_complete = os.path.normpath(to_complete)

        dirname, basename = os_path.split(to_complete)
        if dirname == '':  # We're completing in this directory
            to_list = '.'
        else:  # We're completing in some other directory
            to_list = dirname

        if 0:
            log('basename %r' % basename)
            log('to_list %r' % to_list)
            log('dirname %r' % dirname)

        try:
            names = posix.listdir(to_list)
        except (IOError, OSError) as e:
            return  # nothing

        for name in names:
            path = os_path.join(dirname, name)

            if path.startswith(to_complete):
                if self.dirs_only:  # add_slash not used here
                    # NOTE: There is a duplicate isdir() check later to add a trailing
                    # slash.  Consolidate the checks for fewer stat() ops.  This is hard
                    # because all the completion actions must obey the same interface.
                    # We could have another type like candidate = File | Dir |
                    # OtherString ?
                    if path_stat.isdir(path):
                        yield path
                    continue

                if self.exec_only:
                    # TODO: Handle exception if file gets deleted in between listing and
                    # check?
                    if not posix.access(path, X_OK):
                        continue

                if self.add_slash and path_stat.isdir(path):
                    path = path + '/'
                    yield path
                else:
                    yield path


class CommandAction(CompletionAction):
    """ TODO: Implement complete -C """

    def __init__(self, cmd_ev, command_name):
        # type: (CommandEvaluator, str) -> None
        self.cmd_ev = cmd_ev
        self.command_name = command_name

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]
        for candidate in ['TODO-complete-C']:
            yield candidate


class ShellFuncAction(CompletionAction):
    """Call a user-defined function using bash's completion protocol."""

    def __init__(self, cmd_ev, func, comp_lookup):
        # type: (CommandEvaluator, value.Proc, Lookup) -> None
        """
        Args:
          comp_lookup: For the 124 protocol: test if the user-defined function
          registered a new UserSpec.
        """
        self.cmd_ev = cmd_ev
        self.func = func
        self.comp_lookup = comp_lookup

    def Print(self, f):
        # type: (mylib.BufWriter) -> None

        f.write('[ShellFuncAction %s] ' % self.func.name)

    def ActionKind(self):
        # type: () -> comp_action_t
        return comp_action_e.BashFunc

    def debug(self, msg):
        # type: (str) -> None
        self.cmd_ev.debug_f.writeln(msg)

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]

        # Have to clear the response every time.  TODO: Reuse the object?
        state.SetGlobalArray(self.cmd_ev.mem, 'COMPREPLY', [])

        # New completions should use COMP_ARGV, a construct specific to OSH>
        state.SetGlobalArray(self.cmd_ev.mem, 'COMP_ARGV', comp.partial_argv)

        # Old completions may use COMP_WORDS.  It is split by : and = to emulate
        # bash's behavior.
        # More commonly, they will call _init_completion and use the 'words' output
        # of that, ignoring COMP_WORDS.
        comp_words = []  # type: List[str]
        for a in comp.partial_argv:
            AdjustArg(a, [':', '='], comp_words)
        if comp.index == -1:  # compgen
            comp_cword = comp.index
        else:
            comp_cword = len(comp_words) - 1  # weird invariant

        state.SetGlobalArray(self.cmd_ev.mem, 'COMP_WORDS', comp_words)
        state.SetGlobalString(self.cmd_ev.mem, 'COMP_CWORD', str(comp_cword))
        state.SetGlobalString(self.cmd_ev.mem, 'COMP_LINE', comp.line)
        state.SetGlobalString(self.cmd_ev.mem, 'COMP_POINT', str(comp.end))

        argv = [comp.first, comp.to_complete, comp.prev]
        # TODO: log the arguments
        self.debug('Running completion function %r with %d arguments' %
                   (self.func.name, len(argv)))

        self.comp_lookup.ClearCommandsChanged()
        status = self.cmd_ev.RunFuncForCompletion(self.func, argv)
        commands_changed = self.comp_lookup.GetCommandsChanged()

        self.debug('comp.first %r, commands_changed: %s' %
                   (comp.first, ', '.join(commands_changed)))

        if status == 124:
            cmd = os_path.basename(comp.first)
            if cmd in commands_changed:
                #self.debug('Got status 124 from %r and %s commands changed' % (self.func.name, commands_changed))
                raise _RetryCompletion()
            else:
                # This happens with my own completion scripts.  bash doesn't show an
                # error.
                self.debug(
                    "Function %r returned 124, but the completion spec for %r wasn't "
                    "changed" % (self.func.name, cmd))
                return

        # Read the response.  (The name 'COMP_REPLY' would be more consistent with others.)
        val = self.cmd_ev.mem.GetValue('COMPREPLY', scope_e.GlobalOnly)

        if val.tag() == value_e.Undef:
            # We set it above, so this error would only happen if the user unset it.
            # Not changing it means there were no completions.
            # TODO: This writes over the command line; it would be better to use an
            # error object.
            print_stderr('osh error: Ran function %r but COMPREPLY was unset' %
                         self.func.name)
            return

        if val.tag() != value_e.BashArray:
            print_stderr('osh error: COMPREPLY should be an array, got %s' %
                         ui.ValType(val))
            return

        if 0:
            self.debug('> %r' % val)  # CRASHES in C++

        array_val = cast(value.BashArray, val)
        for s in array_val.strs:
            #self.debug('> %r' % s)
            yield s


class VariablesAction(CompletionAction):
    """compgen -A variable."""

    def __init__(self, mem):
        # type: (Mem) -> None
        self.mem = mem

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]
        for var_name in self.mem.VarNames():
            yield var_name

    def Print(self, f):
        # type: (mylib.BufWriter) -> None

        f.write('VariablesAction ')


class ExternalCommandAction(CompletionAction):
    """Complete commands in $PATH.

    This is PART of compgen -A command.
    """

    def __init__(self, mem):
        # type: (Mem) -> None
        """
        Args:
          mem: for looking up Path
        """
        self.mem = mem
        # Should we list everything executable in $PATH here?  And then whenever
        # $PATH is changed, regenerated it?
        # Or we can cache directory listings?  What if the contents of the dir
        # changed?
        # Can we look at the dir timestamp?
        #
        # (dir, timestamp) -> list of entries perhaps?  And then every time you hit
        # tab, do you have to check the timestamp?  It should be cached by the
        # kernel, so yes.
        # XXX(unused?) self.ext = []

        # (dir, timestamp) -> list
        # NOTE: This cache assumes that listing a directory is slower than statting
        # it to get the mtime.  That may not be true on all systems?  Either way
        # you are reading blocks of metadata.  But I guess /bin on many systems is
        # huge, and will require lots of sys calls.
        self.cache = {}  # type: Dict[Tuple[str, int], List[str]]

    def Print(self, f):
        # type: (mylib.BufWriter) -> None

        f.write('ExternalCommandAction ')

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]
        """TODO: Cache is never cleared.

        - When we get a newer timestamp, we should clear the old one.
        - When PATH is changed, we can remove old entries.
        """
        val = self.mem.GetValue('PATH')
        if val.tag() != value_e.Str:
            # No matches if not a string
            return

        val_s = cast(value.Str, val)
        path_dirs = val_s.s.split(':')
        #log('path: %s', path_dirs)

        executables = []  # type: List[str]
        for d in path_dirs:
            try:
                key = pyos.MakeDirCacheKey(d)
            except (IOError, OSError) as e:
                # There could be a directory that doesn't exist in the $PATH.
                continue

            dir_exes = self.cache.get(key)
            if dir_exes is None:
                entries = posix.listdir(d)
                dir_exes = []
                for name in entries:
                    path = os_path.join(d, name)
                    # TODO: Handle exception if file gets deleted in between listing and
                    # check?
                    if not posix.access(path, X_OK):
                        continue
                    dir_exes.append(name)  # append the name, not the path

                self.cache[key] = dir_exes

            executables.extend(dir_exes)

        # TODO: Shouldn't do the prefix / space thing ourselves.  readline does
        # that at the END of the line.
        for word in executables:
            if word.startswith(comp.to_complete):
                yield word


class _Predicate(object):

    def __init__(self):
        # type: () -> None
        pass

    def Evaluate(self, candidate):
        # type: (str) -> bool
        raise NotImplementedError()

    def Print(self, f):
        # type: (mylib.BufWriter) -> None

        f.write('???Predicate ')


class DefaultPredicate(_Predicate):

    def __init__(self):
        # type: () -> None
        pass

    def Evaluate(self, candidate):
        # type: (str) -> bool
        return True

    def Print(self, f):
        # type: (mylib.BufWriter) -> None

        f.write('DefaultPredicate ')


class GlobPredicate(_Predicate):
    """Expand into files that match a pattern.  !*.py filters them.

    Weird syntax:
    -X *.py or -X !*.py

    Also & is a placeholder for the string being completed?.  Yeah I probably
    want to get rid of this feature.
    """

    def __init__(self, include, glob_pat):
        # type: (bool, str) -> None
        self.include = include  # True for inclusion, False for exclusion
        self.glob_pat = glob_pat  # extended glob syntax supported

    def Evaluate(self, candidate):
        # type: (str) -> bool
        """Should we INCLUDE the candidate or not?"""
        matched = libc.fnmatch(self.glob_pat, candidate)
        # This is confusing because of bash's double-negative syntax
        if self.include:
            return not matched
        else:
            return matched

    def __repr__(self):
        # type: () -> str
        return '<GlobPredicate %s %r>' % (self.include, self.glob_pat)

    def Print(self, f):
        # type: (mylib.BufWriter) -> None
        f.write('GlobPredicate ')


class UserSpec(object):
    """Completion config for a set of commands (or complete -D -E)

    - The compgen builtin exposes this DIRECTLY.
    - Readline must call ReadlineCallback, which uses RootCompleter.
    """

    def __init__(
            self,
            actions,  # type: List[CompletionAction]
            extra_actions,  # type: List[CompletionAction]
            else_actions,  # type: List[CompletionAction]
            predicate,  # type: _Predicate
            prefix,  # type: str
            suffix,  # type: str
    ):
        # type: (...) -> None
        self.actions = actions
        self.extra_actions = extra_actions
        self.else_actions = else_actions
        self.predicate = predicate  # for -X
        self.prefix = prefix
        self.suffix = suffix

    def PrintSpec(self, f):
        # type: (mylib.BufWriter) -> None
        """ Print with indentation of 2 """
        f.write('  actions: ')
        for a in self.actions:
            a.Print(f)
        f.write('\n')

        f.write('  extra: ')
        for a in self.extra_actions:
            a.Print(f)
        f.write('\n')

        f.write('  else: ')
        for a in self.else_actions:
            a.Print(f)
        f.write('\n')

        f.write('  predicate: ')
        self.predicate.Print(f)
        f.write('\n')

        f.write('  prefix: %s\n' % self.prefix)
        f.write('  suffix: %s\n' % self.prefix)

    def AllMatches(self, comp):
        # type: (Api) -> Iterator[Tuple[str, comp_action_t]]
        """yield completion candidates."""
        num_matches = 0

        for a in self.actions:
            action_kind = a.ActionKind()
            for match in a.Matches(comp):
                # Special case hack to match bash for compgen -F.  It doesn't filter by
                # to_complete!
                show = (
                    self.predicate.Evaluate(match) and
                    # ShellFuncAction results are NOT filtered by prefix!
                    (match.startswith(comp.to_complete) or
                     action_kind == comp_action_e.BashFunc))

                # There are two kinds of filters: changing the string, and filtering
                # the set of strings.  So maybe have modifiers AND filters?  A triple.
                if show:
                    yield self.prefix + match + self.suffix, action_kind
                    num_matches += 1

        # NOTE: extra_actions and else_actions don't respect -X, -P or -S, and we
        # don't have to filter by startswith(comp.to_complete).  They are all all
        # FileSystemActions, which do it already.

        # for -o plusdirs
        for a in self.extra_actions:
            for match in a.Matches(comp):
                # We know plusdirs is a file system action
                yield match, comp_action_e.FileSystem

        # for -o default and -o dirnames
        if num_matches == 0:
            for a in self.else_actions:
                for match in a.Matches(comp):
                    # both are FileSystemAction
                    yield match, comp_action_e.FileSystem

        # What if the cursor is not at the end of line?  See readline interface.
        # That's OK -- we just truncate the line at the cursor?
        # Hm actually zsh does something smarter, and which is probably preferable.
        # It completes the word that


# Helpers for Matches()
def IsDollar(t):
    # type: (Token) -> bool

    # We have rules for Lit_Dollar in
    # lex_mode_e.{ShCommand,DQ,VSub_ArgUnquoted,VSub_ArgDQ}
    return t.id == Id.Lit_Dollar


def IsDummy(t):
    # type: (Token) -> bool
    return t.id == Id.Lit_CompDummy


def WordEndsWithCompDummy(w):
    # type: (CompoundWord) -> bool
    last_part = w.parts[-1]
    UP_part = last_part
    if last_part.tag() == word_part_e.Literal:
        last_part = cast(Token, UP_part)
        return last_part.id == Id.Lit_CompDummy
    else:
        return False


class RootCompleter(object):
    """Dispatch to various completers.

    - Complete the OSH language (variables, etc.), or
    - Statically evaluate argv and dispatch to a command completer.
    """

    def __init__(
            self,
            word_ev,  # type: AbstractWordEvaluator
            mem,  # type: Mem
            comp_lookup,  # type: Lookup
            compopt_state,  # type: OptionState
            comp_ui_state,  # type: State
            parse_ctx,  # type: ParseContext
            debug_f,  # type: _DebugFile
    ):
        # type: (...) -> None
        self.word_ev = word_ev  # for static evaluation of words
        self.mem = mem  # to complete variable names
        self.comp_lookup = comp_lookup
        self.compopt_state = compopt_state  # for compopt builtin
        self.comp_ui_state = comp_ui_state

        self.parse_ctx = parse_ctx
        self.debug_f = debug_f

    def Matches(self, comp):
        # type: (Api) -> Iterator[str]
        """
        Args:
          comp: Callback args from readline.  Readline uses
                set_completer_delims to tokenize the string.

        Returns a list of matches relative to readline's completion_delims.
        We have to post-process the output of various completers.
        """
        # Pass the original line "out of band" to the completion callback.
        line_until_tab = comp.line[:comp.end]
        self.comp_ui_state.line_until_tab = line_until_tab

        self.parse_ctx.trail.Clear()
        line_reader = reader.StringLineReader(line_until_tab,
                                              self.parse_ctx.arena)
        c_parser = self.parse_ctx.MakeOshParser(line_reader,
                                                emit_comp_dummy=True)

        # We want the output from parse_ctx, so we don't use the return value.
        try:
            c_parser.ParseLogicalLine()
        except error.Parse as e:
            # e.g. 'ls | ' will not parse.  Now inspect the parser state!
            pass

        debug_f = self.debug_f
        trail = self.parse_ctx.trail
        if mylib.PYTHON:
            trail.PrintDebugString(debug_f)

        #
        # First try completing the shell language itself.
        #

        # NOTE: We get Eof_Real in the command state, but not in the middle of a
        # BracedVarSub.  This is due to the difference between the CommandParser
        # and WordParser.
        tokens = trail.tokens
        last = -1
        if tokens[-1].id == Id.Eof_Real:
            last -= 1  # ignore it

        try:
            t1 = tokens[last]
        except IndexError:
            t1 = None
        try:
            t2 = tokens[last - 1]
        except IndexError:
            t2 = None

        debug_f.writeln('line: %r' % comp.line)
        debug_f.writeln('rl_slice from byte %d to %d: %r' %
                        (comp.begin, comp.end, comp.line[comp.begin:comp.end]))

        # Note: this logging crashes C++ because of type mismatch
        if t1:
            #debug_f.writeln('t1 %s' % t1)
            pass

        if t2:
            #debug_f.writeln('t2 %s' % t2)
            pass

        #debug_f.writeln('tokens %s', tokens)

        # Each of the 'yield' statements below returns a fully-completed line, to
        # appease the readline library.  The root cause of this dance: If there's
        # one candidate, readline is responsible for redrawing the input line.  OSH
        # only displays candidates and never redraws the input line.

        if t2:  # We always have t1?
            # echo $
            if IsDollar(t2) and IsDummy(t1):
                self.comp_ui_state.display_pos = t2.col + 1  # 1 for $
                for name in self.mem.VarNames():
                    yield line_until_tab + name  # no need to quote var names
                return

            # echo ${
            if t2.id == Id.Left_DollarBrace and IsDummy(t1):
                self.comp_ui_state.display_pos = t2.col + 2  # 2 for ${
                for name in self.mem.VarNames():
                    # no need to quote var names
                    yield line_until_tab + name
                return

            # echo $P
            if t2.id == Id.VSub_DollarName and IsDummy(t1):
                # Example: ${undef:-$P
                # readline splits at ':' so we have to prepend '-$' to every completed
                # variable name.
                self.comp_ui_state.display_pos = t2.col + 1  # 1 for $
                to_complete = t2.tval[1:]
                n = len(to_complete)
                for name in self.mem.VarNames():
                    if name.startswith(to_complete):
                        # no need to quote var names
                        yield line_until_tab + name[n:]
                return

            # echo ${P
            if t2.id == Id.VSub_Name and IsDummy(t1):
                self.comp_ui_state.display_pos = t2.col  # no offset
                to_complete = t2.tval
                n = len(to_complete)
                for name in self.mem.VarNames():
                    if name.startswith(to_complete):
                        # no need to quote var names
                        yield line_until_tab + name[n:]
                return

            # echo $(( VAR
            if t2.id == Id.Lit_ArithVarLike and IsDummy(t1):
                self.comp_ui_state.display_pos = t2.col  # no offset
                to_complete = t2.tval
                n = len(to_complete)
                for name in self.mem.VarNames():
                    if name.startswith(to_complete):
                        # no need to quote var names
                        yield line_until_tab + name[n:]
                return

        if len(trail.words) > 0:
            # echo ~<TAB>
            # echo ~a<TAB> $(home dirs)
            # This must be done at a word level, and TildeDetectAll() does NOT help
            # here, because they don't have trailing slashes yet!  We can't do it on
            # tokens, because otherwise f~a will complete.  Looking at word_part is
            # EXACTLY what we want.
            parts = trail.words[-1].parts
            if len(parts) > 0 and word_.LiteralId(parts[0]) == Id.Lit_Tilde:
                #log('TILDE parts %s', parts)

                if (len(parts) == 2 and
                        word_.LiteralId(parts[1]) == Id.Lit_CompDummy):
                    tilde_tok = cast(Token, parts[0])

                    # end of tilde
                    self.comp_ui_state.display_pos = tilde_tok.col + 1

                    to_complete = ''
                    for u in pyos.GetAllUsers():
                        name = u.pw_name
                        s = line_until_tab + ShellQuoteB(name) + '/'
                        yield s
                    return

                if (len(parts) == 3 and
                        word_.LiteralId(parts[1]) == Id.Lit_Chars and
                        word_.LiteralId(parts[2]) == Id.Lit_CompDummy):

                    chars_tok = cast(Token, parts[1])

                    self.comp_ui_state.display_pos = chars_tok.col

                    to_complete = lexer.TokenVal(chars_tok)
                    n = len(to_complete)
                    for u in pyos.GetAllUsers():  # catch errors?
                        name = u.pw_name
                        if name.startswith(to_complete):
                            s = line_until_tab + ShellQuoteB(name[n:]) + '/'
                            yield s
                    return

        # echo hi > f<TAB>   (complete redirect arg)
        if len(trail.redirects) > 0:
            r = trail.redirects[-1]
            # Only complete 'echo >', but not 'echo >&' or 'cat <<'
            # TODO: Don't complete <<< 'h'
            if (r.arg.tag() == redir_param_e.Word and
                    consts.RedirArgType(r.op.id) == redir_arg_type_e.Path):
                arg_word = r.arg
                UP_word = arg_word
                arg_word = cast(CompoundWord, UP_word)
                if WordEndsWithCompDummy(arg_word):
                    debug_f.writeln('Completing redirect arg')

                    try:
                        val = self.word_ev.EvalWordToString(arg_word)
                    except error.FatalRuntime as e:
                        debug_f.writeln('Error evaluating redirect word: %s' %
                                        e)
                        return
                    if val.tag() != value_e.Str:
                        debug_f.writeln("Didn't get a string from redir arg")
                        return

                    tok = location.LeftTokenForWord(arg_word)
                    self.comp_ui_state.display_pos = tok.col

                    comp.Update('', val.s, '', 0, [])
                    n = len(val.s)
                    action = FileSystemAction(False, False, True)
                    for name in action.Matches(comp):
                        yield line_until_tab + ShellQuoteB(name[n:])
                    return

        #
        # We're not completing the shell language.  Delegate to user-defined
        # completion for external tools.
        #

        # Set below, and set on retries.
        base_opts = None  # type: Dict[str, bool]
        user_spec = None  # type: Optional[UserSpec]

        # Used on retries.
        partial_argv = []  # type: List[str]
        num_partial = -1
        first = None  # type: str

        if len(trail.words) > 0:
            # Now check if we're completing a word!
            if WordEndsWithCompDummy(trail.words[-1]):
                debug_f.writeln('Completing words')
                #
                # It didn't look like we need to complete var names, tilde, redirects,
                # etc.  Now try partial_argv, which may involve invoking PLUGINS.

                # needed to complete paths with ~
                # mycpp: workaround list cast
                trail_words = [cast(word_t, w) for w in trail.words]
                words2 = word_.TildeDetectAll(trail_words)
                if 0:
                    debug_f.writeln('After tilde detection')
                    for w in words2:
                        print(w, file=debug_f)

                if 0:
                    debug_f.writeln('words2:')
                    for w2 in words2:
                        debug_f.writeln(' %s' % w2)

                for w in words2:
                    try:
                        # TODO:
                        # - Should we call EvalWordSequence?  But turn globbing off?  It
                        # can do splitting and such.
                        # - We could have a variant to eval TildeSub to ~ ?
                        val = self.word_ev.EvalWordToString(w)
                    except error.FatalRuntime:
                        # Why would it fail?
                        continue
                    if val.tag() == value_e.Str:
                        partial_argv.append(val.s)
                    else:
                        pass

                debug_f.writeln('partial_argv: [%s]' % ','.join(partial_argv))
                num_partial = len(partial_argv)

                first = partial_argv[0]
                alias_first = None  # type: str
                if mylib.PYTHON:
                    debug_f.writeln('alias_words: [%s]' % trail.alias_words)

                if len(trail.alias_words) > 0:
                    w = trail.alias_words[0]
                    try:
                        val = self.word_ev.EvalWordToString(w)
                    except error.FatalRuntime:
                        pass
                    alias_first = val.s
                    debug_f.writeln('alias_first: %s' % alias_first)

                if num_partial == 0:  # should never happen because of Lit_CompDummy
                    raise AssertionError()
                elif num_partial == 1:
                    base_opts, user_spec = self.comp_lookup.GetFirstSpec()

                    # Display/replace since the beginning of the first word.  Note: this
                    # is non-zero in the case of
                    # echo $(gr   and
                    # echo `gr

                    tok = location.LeftTokenForWord(trail.words[0])
                    self.comp_ui_state.display_pos = tok.col
                    self.debug_f.writeln('** DISPLAY_POS = %d' %
                                         self.comp_ui_state.display_pos)

                else:
                    base_opts, user_spec = self.comp_lookup.GetSpecForName(
                        first)
                    if not user_spec and alias_first is not None:
                        base_opts, user_spec = self.comp_lookup.GetSpecForName(
                            alias_first)
                        if user_spec:
                            # Pass the aliased command to the user-defined function, and use
                            # it for retries.
                            first = alias_first
                    if not user_spec:
                        base_opts, user_spec = self.comp_lookup.GetFallback()

                    # Display since the beginning
                    tok = location.LeftTokenForWord(trail.words[-1])
                    self.comp_ui_state.display_pos = tok.col
                    if mylib.PYTHON:
                        self.debug_f.writeln('words[-1]: [%s]' %
                                             trail.words[-1])

                    self.debug_f.writeln('display_pos %d' %
                                         self.comp_ui_state.display_pos)

                # Update the API for user-defined functions.
                index = len(
                    partial_argv) - 1  # COMP_CWORD is -1 when it's empty
                prev = '' if index == 0 else partial_argv[index - 1]
                comp.Update(first, partial_argv[-1], prev, index, partial_argv)

        # This happens in the case of [[ and ((, or a syntax error like 'echo < >'.
        if not user_spec:
            debug_f.writeln("Didn't find anything to complete")
            return

        # Reset it back to what was registered.  User-defined functions can mutate
        # it.
        dynamic_opts = {}  # type: Dict[str, bool]
        self.compopt_state.dynamic_opts = dynamic_opts
        with ctx_Completing(self.compopt_state):
            done = False
            while not done:
                done = True  # exhausted candidates without getting a retry
                try:
                    for candidate in self._PostProcess(base_opts, dynamic_opts,
                                                       user_spec, comp):
                        yield candidate
                except _RetryCompletion as e:
                    debug_f.writeln('Got 124, trying again ...')
                    done = False

                    # Get another user_spec.  The ShellFuncAction may have 'sourced' code
                    # and run 'complete' to mutate comp_lookup, and we want to get that
                    # new entry.
                    if num_partial == 0:
                        raise AssertionError()
                    elif num_partial == 1:
                        base_opts, user_spec = self.comp_lookup.GetFirstSpec()
                    else:
                        # (already processed alias_first)
                        base_opts, user_spec = self.comp_lookup.GetSpecForName(
                            first)
                        if not user_spec:
                            base_opts, user_spec = self.comp_lookup.GetFallback(
                            )

    def _PostProcess(
            self,
            base_opts,  # type: Dict[str, bool]
            dynamic_opts,  # type: Dict[str, bool]
            user_spec,  # type: UserSpec
            comp,  # type: Api
    ):
        # type: (...) -> Iterator[str]
        """Add trailing spaces / slashes to completion candidates, and time
        them.

        NOTE: This post-processing MUST go here, and not in UserSpec, because
        it's in READLINE in bash.  compgen doesn't see it.
        """
        self.debug_f.writeln('Completing %r ... (Ctrl-C to cancel)' %
                             comp.line)
        start_time = time_.time()

        # TODO: dedupe candidates?  You can get two 'echo' in bash, which is dumb.

        i = 0
        for candidate, action_kind in user_spec.AllMatches(comp):
            # SUBTLE: dynamic_opts is part of compopt_state, which ShellFuncAction
            # can mutate!  So we don't want to pull this out of the loop.
            #
            # TODO: The candidates from each actions shouldn't be flattened.
            # for action in user_spec.Actions():
            #   if action.IsFileSystem():  # this returns is_dir too
            #
            #   action.Run()  # might set dynamic opts
            #   opt_nospace = base_opts...
            #   if 'nospace' in dynamic_opts:
            #     opt_nosspace = dynamic_opts['nospace']
            #   for candidate in action.Matches():
            #     add space or /
            #     and do escaping too
            #
            # Or maybe you can request them on demand?  Most actions are EAGER.
            # While the ShellacAction is LAZY?  And you should be able to cancel it!

            # NOTE: User-defined plugins (and the -P flag) can REWRITE what the user
            # already typed.  So
            #
            # $ echo 'dir with spaces'/f<TAB>
            #
            # can be rewritten to:
            #
            # $ echo dir\ with\ spaces/foo
            line_until_tab = self.comp_ui_state.line_until_tab
            line_until_word = line_until_tab[:self.comp_ui_state.display_pos]

            opt_filenames = base_opts.get('filenames', False)
            if 'filenames' in dynamic_opts:
                opt_filenames = dynamic_opts['filenames']

            # compopt -o filenames is for user-defined actions.  Or any
            # FileSystemAction needs it.
            if action_kind == comp_action_e.FileSystem or opt_filenames:
                if path_stat.isdir(candidate):
                    s = line_until_word + ShellQuoteB(candidate) + '/'
                    yield s
                    continue

            opt_nospace = base_opts.get('nospace', False)
            if 'nospace' in dynamic_opts:
                opt_nospace = dynamic_opts['nospace']

            sp = '' if opt_nospace else ' '
            cand = (candidate if action_kind == comp_action_e.BashFunc else
                    ShellQuoteB(candidate))

            yield line_until_word + cand + sp

            # NOTE: Can't use %.2f in production build!
            i += 1
            elapsed_ms = (time_.time() - start_time) * 1000.0
            plural = '' if i == 1 else 'es'

            # TODO: Show this in the UI if it takes too long!
            if 0:
                self.debug_f.writeln(
                    '... %d match%s for %r in %d ms (Ctrl-C to cancel)' %
                    (i, plural, comp.line, elapsed_ms))

        elapsed_ms = (time_.time() - start_time) * 1000.0
        plural = '' if i == 1 else 'es'
        self.debug_f.writeln('Found %d match%s for %r in %d ms' %
                             (i, plural, comp.line, elapsed_ms))


class ReadlineCallback(object):
    """A callable we pass to the readline module."""

    def __init__(self, readline, root_comp, debug_f):
        # type: (Optional[Readline], RootCompleter, util._DebugFile) -> None
        self.readline = readline
        self.root_comp = root_comp
        self.debug_f = debug_f

        # current completion being processed
        if mylib.PYTHON:
            self.comp_iter = None  # type: Iterator[str]
        else:
            self.comp_matches = None  # type: List[str]

    def _GetNextCompletion(self, state):
        # type: (int) -> Optional[str]
        if state == 0:
            # TODO: Tokenize it according to our language.  If this is $PS2, we also
            # need previous lines!  Could make a VirtualLineReader instead of
            # StringLineReader?
            buf = self.readline.get_line_buffer()

            # Readline parses "words" using characters provided by
            # set_completer_delims().
            # We have our own notion of words.  So let's call this a 'rl_slice'.
            begin = self.readline.get_begidx()
            end = self.readline.get_endidx()

            comp = Api(line=buf, begin=begin, end=end)
            self.debug_f.writeln('Api %r %d %d' % (buf, begin, end))

            if mylib.PYTHON:
                self.comp_iter = self.root_comp.Matches(comp)
            else:
                it = self.root_comp.Matches(comp)
                self.comp_matches = list(it)
                self.comp_matches.reverse()

        if mylib.PYTHON:
            assert self.comp_iter is not None, self.comp_iter
            try:
                next_completion = self.comp_iter.next()
            except StopIteration:
                next_completion = None  # signals the end
        else:
            assert self.comp_matches is not None, self.comp_matches
            try:
                next_completion = self.comp_matches.pop()
            except IndexError:
                next_completion = None  # signals the end

        return next_completion

    def __call__(self, unused_word, state):
        # type: (str, int) -> Optional[str]
        """Return a single match."""
        try:
            return self._GetNextCompletion(state)
        except util.UserExit as e:
            # TODO: Could use errfmt to show this
            print_stderr("osh: Ignoring 'exit' in completion plugin")
        except error.FatalRuntime as e:
            # From -W.  TODO: -F is swallowed now.
            # We should have a nicer UI for displaying errors.  Maybe they shouldn't
            # print it to stderr.  That messes up the completion display.  We could
            # print what WOULD have been COMPREPLY here.
            print_stderr('osh: Runtime error while completing: %s' %
                         e.UserErrorString())
            self.debug_f.writeln('Runtime error while completing: %s' %
                                 e.UserErrorString())
        except (IOError, OSError) as e:
            # test this with prlimit --nproc=1 --pid=$$
            print_stderr('osh: I/O error (completion): %s' %
                         posix.strerror(e.errno))
        except KeyboardInterrupt:
            # It appears GNU readline handles Ctrl-C to cancel a long completion.
            # So this may never happen?
            print_stderr('Ctrl-C in completion')
        except Exception as e:  # ESSENTIAL because readline swallows exceptions.
            if mylib.PYTHON:
                import traceback
                traceback.print_exc()
            print_stderr('osh: Unhandled exception while completing: %s' % e)
            self.debug_f.writeln('Unhandled exception while completing: %s' %
                                 e)
        except SystemExit as e:
            # I think this should no longer be called, because we don't use
            # sys.exit()?
            # But put it here in case Because readline ignores SystemExit!
            posix._exit(e.code)

        return None


def ExecuteReadlineCallback(cb, word, state):
    # type: (ReadlineCallback, str, int) -> Optional[str]
    return cb.__call__(word, state)


if __name__ == '__main__':
    # This does basic filename copmletion
    import readline
    readline.parse_and_bind('tab: complete')
    while True:
        x = raw_input('$ ')
        print(x)
