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
whole lexer/parser/cmd_exec combo has to be thread-safe.  Does it get a copy of
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

import pwd
import time

from _devbuild.gen.syntax_asdl import word_part_e, redir_e, Id
from _devbuild.gen.runtime_asdl import value_e
from _devbuild.gen.types_asdl import redir_arg_type_e
from _devbuild.gen.id_tables import REDIR_ARG_TYPES

from core import error
from core import ui
from core import util
from core.util import log
from frontend import reader
from pylib import os_path
from pylib import path_stat
from osh import word_
from osh import state
from osh.string_ops import ShellQuoteB

import libc
import posix_ as posix


# To quote completion candidates.
#   !    is for history expansion, which only happens interactively, but
#        completion only does too.
#   *?[] are for globs
#   {}   are for brace expansion
#   ~    in filenames should be quoted
#
# TODO: Also escape tabs as \t and newlines at \n?
SHELL_META_CHARS = r' ~`!$&|;()\"*?[]{}<>' + "'"



class _RetryCompletion(Exception):
  """For the 'exit 124' protocol."""
  pass


CH_Break, CH_Other = xrange(2)  # Character types
ST_Begin, ST_Break, ST_Other = xrange(3)  # States

# State machine definition.
_TRANSITIONS = {
    # (state, char) -> (new state, emit span)
    (ST_Begin, CH_Break): (ST_Break, False),
    (ST_Begin, CH_Other): (ST_Other, False),

    (ST_Break, CH_Break): (ST_Break, False),
    (ST_Break, CH_Other): (ST_Other, True),

    (ST_Other, CH_Break): (ST_Break, True),
    (ST_Other, CH_Other): (ST_Other, False),
}

def AdjustArg(arg, break_chars, argv_out):
  end_indices = []  # stores the end of each span
  state = ST_Begin
  for i, c in enumerate(arg):
    ch = CH_Break if c in break_chars else CH_Other
    state, emit_span = _TRANSITIONS[state, ch]
    if emit_span:
      end_indices.append(i)

  # Always emit a span at the end (even for empty string)
  end_indices.append(len(arg))

  begin = 0
  for end in end_indices:
    argv_out.append(arg[begin:end])
    begin = end


class NullCompleter(object):

  def Matches(self, comp):
    return []


# NOTE: How to create temporary options?  With copy.deepcopy()?
# We might want that as a test for OVM.  Copying is similar to garbage
# collection in that you walk a graph.


# These values should never be mutated.
_DEFAULT_OPTS = {}
_DO_NOTHING = (_DEFAULT_OPTS, NullCompleter())


class OptionState(object):
  """Stores the compopt state of the CURRENT completion."""

  def __init__(self):
    # For the IN-PROGRESS completion.
    self.currently_completing = False
    # should be SET to a COPY of the registration options by the completer.
    self.dynamic_opts = None


class Lookup(object):
  """Stores completion hooks registered by the user."""

  def __init__(self):
    # command name -> UserSpec
    # Pseudo-commands __first and __fallback are for -E and -D.
    self.lookup = {
        '__fallback': _DO_NOTHING,
        '__first': _DO_NOTHING,
    }

    self.commands_with_spec_changes = []  # for the 124 protocol

    # So you can register *.sh, unlike bash.  List of (glob, [actions]),
    # searched linearly.
    self.patterns = []

  def __str__(self):
    return '<completion.Lookup %s>' % self.lookup

  def PrintSpecs(self):
    """For 'complete' without args."""
    for name in sorted(self.lookup):
      base_opts, user_spec = self.lookup[name]
      print('%-15s %s  %s' % (name, base_opts, user_spec))
    print('---')
    for pat, spec in self.patterns:
      print('%s = %s' % (pat, spec))

  def ClearCommandsChanged(self):
    del self.commands_with_spec_changes[:]

  def GetCommandsChanged(self):
    return self.commands_with_spec_changes

  def RegisterName(self, name, base_opts, user_spec):
    """Register a completion action with a name.
    Used by the 'complete' builtin.
    """
    self.lookup[name] = (base_opts, user_spec)

    if name not in ('__fallback', '__first'):
      self.commands_with_spec_changes.append(name)

  def RegisterGlob(self, glob_pat, base_opts, user_spec):
    self.patterns.append((glob_pat, base_opts, user_spec))

  def GetSpecForName(self, argv0):
    """
    Args:
      argv0: A finished argv0 to lookup
    """
    pair = self.lookup.get(argv0)  # NOTE: Could be ''
    if pair:
      return pair

    key = os_path.basename(argv0)
    pair = self.lookup.get(key)
    if pair:
      return pair

    for glob_pat, base_opts, user_spec in self.patterns:
      #log('Matching %r %r', key, glob_pat)
      if libc.fnmatch(glob_pat, key):
        return base_opts, user_spec

    return None, None

  def GetFirstSpec(self):
    return self.lookup['__first']

  def GetFallback(self):
    return self.lookup['__fallback']


class Api(object):

  def __init__(self, line='', begin=0, end=0):
    """
    Args:
      index: if -1, then we're running through compgen
    """
    self.line = line
    self.begin = begin
    self.end = end
    # NOTE: COMP_WORDBREAKS is initialized in Mem().

  # NOTE: to_complete could be 'cur'
  def Update(self, first='', to_complete='', prev='', index=0,
             partial_argv=None):
    """Added after we've done parsing."""
    self.first = first
    self.to_complete = to_complete
    self.prev = prev
    self.index = index  # COMP_CWORD
    # COMP_ARGV and COMP_WORDS can be derived from this
    self.partial_argv = partial_argv or []

  def __repr__(self):
    """For testing"""
    return '<Api %r %d-%d>' % (self.line, self.begin, self.end)


#
# Actions
#

class CompletionAction(object):
  """Returns a list of words.

  Function
  Literal words
  """
  def __init__(self):
    pass

  def Matches(self, comp):
    pass

  def __repr__(self):
    return self.__class__.__name__


class UsersAction(CompletionAction):
  """complete -A user"""

  def Matches(self, comp):
    for u in pwd.getpwall():
      name = u.pw_name
      if name.startswith(comp.to_complete):
        yield name


class TestAction(CompletionAction):
  def __init__(self, words, delay=None):
    self.words = words
    self.delay = delay

  def Matches(self, comp):
    for w in self.words:
      if w.startswith(comp.to_complete):
        if self.delay:
          time.sleep(self.delay)
        yield w


class DynamicWordsAction(CompletionAction):
  """ compgen -W '$(echo one two three)' """

  def __init__(self, word_ev, splitter, arg_word, arena):
    self.word_ev = word_ev
    self.splitter = splitter
    self.arg_word = arg_word
    self.arena = arena

  def Matches(self, comp):
    try:
      val = self.word_ev.EvalWordToString(self.arg_word)
    except error.FatalRuntime as e:
      ui.PrettyPrintError(e, self.arena)
      raise

    # SplitForWordEval() Allows \ escapes
    candidates = self.splitter.SplitForWordEval(val.s)
    for c in candidates:
      if c.startswith(comp.to_complete):
        yield c


class FileSystemAction(CompletionAction):
  """Complete paths from the file system.

  Directories will have a / suffix.
  """
  def __init__(self, dirs_only=False, exec_only=False, add_slash=False):
    self.dirs_only = dirs_only
    self.exec_only = exec_only

    # This is for redirects, not for UserSpec, which should respect compopt -o
    # filenames.
    self.add_slash = add_slash  # for directories

  def Matches(self, comp):
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
      log('basename %r', basename)
      log('to_list %r', to_list)
      log('dirname %r', dirname)

    try:
      names = posix.listdir(to_list)
    except OSError as e:
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
          if not posix.access(path, posix.X_OK):
            continue

        if self.add_slash and path_stat.isdir(path):
          yield path + '/'
        else:
          yield path


class ShellFuncAction(CompletionAction):
  """Call a user-defined function using bash's completion protocol."""

  def __init__(self, ex, func, comp_lookup):
    """
    Args:
      comp_lookup: For the 124 protocol: test if the user-defined function
      registered a new UserSpec.
    """
    self.ex = ex
    self.func = func
    self.comp_lookup = comp_lookup

  def __repr__(self):
    # TODO: Add file and line number here!
    return '<ShellFuncAction %s>' % (self.func.name,)

  def log(self, *args):
    self.ex.debug_f.log(*args)

  def Matches(self, comp):
    # Have to clear the response every time.  TODO: Reuse the object?
    state.SetGlobalArray(self.ex.mem, 'COMPREPLY', [])

    # New completions should use COMP_ARGV, a construct specific to OSH>
    state.SetGlobalArray(self.ex.mem, 'COMP_ARGV', comp.partial_argv)

    # Old completions may use COMP_WORDS.  It is split by : and = to emulate
    # bash's behavior. 
    # More commonly, they will call _init_completion and use the 'words' output
    # of that, ignoring COMP_WORDS.
    comp_words = []
    for a in comp.partial_argv:
      AdjustArg(a, [':', '='], comp_words)
    if comp.index == -1:  # cmopgen
      comp_cword = comp.index
    else:
      comp_cword = len(comp_words) - 1  # weird invariant

    state.SetGlobalArray(self.ex.mem, 'COMP_WORDS', comp_words)
    state.SetGlobalString(self.ex.mem, 'COMP_CWORD', str(comp_cword))
    state.SetGlobalString(self.ex.mem, 'COMP_LINE', comp.line)
    state.SetGlobalString(self.ex.mem, 'COMP_POINT', str(comp.end))

    argv = [comp.first, comp.to_complete, comp.prev]
    self.log('Running completion function %r with arguments %s',
             self.func.name, argv)

    self.comp_lookup.ClearCommandsChanged()
    status = self.ex.RunFuncForCompletion(self.func, argv)
    commands_changed = self.comp_lookup.GetCommandsChanged()

    self.log('comp.first %s, commands_changed: %s', comp.first,
             commands_changed)

    if status == 124:
      cmd = os_path.basename(comp.first) 
      if cmd in commands_changed:
        self.log('Got status 124 from %r and %s commands changed',
                 self.func.name, commands_changed)
        raise _RetryCompletion()
      else:
        # This happens with my own completion scripts.  bash doesn't show an
        # error.
        self.log(
            "Function %r returned 124, but the completion spec for %r wasn't "
            "changed", self.func.name, cmd)
        return []

    # Read the response.
    # NOTE: 'COMP_REPLY' would follow the naming convention!
    val = state.GetGlobal(self.ex.mem, 'COMPREPLY')
    if val.tag == value_e.Undef:
      # We set it above, so this error would only happen if the user unset it.
      # Not changing it means there were no completions.
      # TODO: This writes over the command line; it would be better to use an
      # error object.
      ui.Stderr('osh: Ran function %r but COMPREPLY was unset',
                self.func.name)
      return []

    if val.tag != value_e.MaybeStrArray:
      log('ERROR: COMPREPLY should be an array, got %s', val)
      return []
    self.log('COMPREPLY %s', val)

    # Return this all at once so we don't have a generator.  COMPREPLY happens
    # all at once anyway.
    return val.strs


class VariablesAction(CompletionAction):
  """compgen -A variable."""
  def __init__(self, mem):
    self.mem = mem

  def Matches(self, comp):
    for var_name in self.mem.VarNames():
      yield var_name


class ExternalCommandAction(CompletionAction):
  """Complete commands in $PATH.

  This is PART of compge -A command.
  """
  def __init__(self, mem):
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
    self.ext = []

    # (dir, timestamp) -> list
    # NOTE: This cache assumes that listing a directory is slower than statting
    # it to get the mtime.  That may not be true on all systems?  Either way
    # you are reading blocks of metadata.  But I guess /bin on many systems is
    # huge, and will require lots of sys calls.
    self.cache = {}

  def Matches(self, comp):
    """
    TODO: Cache is never cleared.

    - When we get a newer timestamp, we should clear the old one.
    - When PATH is changed, we can remove old entries.
    """
    val = self.mem.GetVar('PATH')
    if val.tag != value_e.Str:
      # No matches if not a string
      return
    path_dirs = val.s.split(':')
    #log('path: %s', path_dirs)

    executables = []
    for d in path_dirs:
      try:
        st = posix.stat(d)
      except OSError as e:
        # There could be a directory that doesn't exist in the $PATH.
        continue
      key = (d, st.st_mtime)

      dir_exes = self.cache.get(key)
      if dir_exes is None:
        entries = posix.listdir(d)
        dir_exes = []
        for name in entries:
          path = os_path.join(d, name)
          # TODO: Handle exception if file gets deleted in between listing and
          # check?
          if not posix.access(path, posix.X_OK):
            continue
          dir_exes.append(name)  # append the name, not the path

        self.cache[key] = dir_exes

      executables.extend(dir_exes)

    # TODO: Shouldn't do the prefix / space thing ourselves.  readline does
    # that at the END of the line.
    for word in executables:
      if word.startswith(comp.to_complete):
        yield word


class GlobPredicate(object):
  """Expand into files that match a pattern.  !*.py filters them.

  Weird syntax:
  -X *.py or -X !*.py

  Also & is a placeholder for the string being completed?.  Yeah I probably
  want to get rid of this feature.
  """
  def __init__(self, include, glob_pat):
    self.include = include  # True for inclusion, False for exclusion
    self.glob_pat = glob_pat  # extended glob syntax supported

  def __call__(self, candidate):
    """Should we INCLUDE the candidate or not?"""
    matched = libc.fnmatch(self.glob_pat, candidate)
    # This is confusing because of bash's double-negative syntax
    if self.include:
      return not matched
    else:
      return matched

  def __repr__(self):
    return '<GlobPredicate %s %r>' % (self.include, self.glob_pat)


def DefaultPredicate(candidate):
  return True


class UserSpec(object):
  """The user configuration for completion.
  
  - The compgen builtin exposes this DIRECTLY.
  - Readline must call ReadlineCallback, which uses RootCompleter.
  """
  def __init__(self, actions, extra_actions, else_actions, predicate,
               prefix='', suffix=''):
    self.actions = actions
    self.extra_actions = extra_actions
    self.else_actions = else_actions
    self.predicate = predicate  # for -X
    self.prefix = prefix
    self.suffix = suffix

  def Matches(self, comp):
    """Yield completion candidates."""
    num_matches = 0

    for a in self.actions:
      is_fs_action = isinstance(a, FileSystemAction)
      for match in a.Matches(comp):
        # Special case hack to match bash for compgen -F.  It doesn't filter by
        # to_complete!
        show = (
            self.predicate(match) and
            # ShellFuncAction results are NOT filtered by prefix!
            (match.startswith(comp.to_complete) or
             isinstance(a, ShellFuncAction))
        )

        # There are two kinds of filters: changing the string, and filtering
        # the set of strings.  So maybe have modifiers AND filters?  A triple.
        if show:
          yield self.prefix + match + self.suffix, is_fs_action
          num_matches += 1

    # NOTE: extra_actions and else_actions don't respect -X, -P or -S, and we
    # don't have to filter by startswith(comp.to_complete).  They are all all
    # FileSystemActions, which do it already.

    # for -o plusdirs
    for a in self.extra_actions:
      for match in a.Matches(comp):
        yield match, True  # We know plusdirs is a file system action

    # for -o default and -o dirnames
    if num_matches == 0:
      for a in self.else_actions:
        for match in a.Matches(comp):
          yield match, True  # both are FileSystemAction

    # What if the cursor is not at the end of line?  See readline interface.
    # That's OK -- we just truncate the line at the cursor?
    # Hm actually zsh does something smarter, and which is probably preferable.
    # It completes the word that

  def __str__(self):
    parts = ['(UserSpec']
    if self.actions:
      parts.append(str(self.actions))
    if self.extra_actions:
      parts.append('extra=%s' % self.extra_actions)
    if self.else_actions:
      parts.append('else=%s' % self.else_actions)
    if self.predicate is not DefaultPredicate:
      parts.append('pred = %s' % self.predicate)
    if self.prefix:
      parts.append('prefix=%r' % self.prefix)
    if self.suffix:
      parts.append('suffix=%r' % self.suffix)
    return ' '.join(parts) + ')'


# Helpers for Matches()

# NOTE: We could add Lit_Dollar, but it would affect many lexer modes.
def IsDollar(t):
  return t.id == Id.Lit_Other and t.val == '$'


def IsDummy(t):
  return t.id == Id.Lit_CompDummy


def WordEndsWithCompDummy(w):
  last_part = w.parts[-1]
  return (
      last_part.tag == word_part_e.Literal and
      last_part.id == Id.Lit_CompDummy
  )


class RootCompleter(object):
  """Dispatch to various completers.

  - Complete the OSH language (variables, etc.), or
  - Statically evaluate argv and dispatch to a command completer.
  """
  def __init__(self, word_ev, mem, comp_lookup, compopt_state, comp_ui_state,
               parse_ctx, debug_f):
    self.word_ev = word_ev  # for static evaluation of words
    self.mem = mem  # to complete variable names
    self.comp_lookup = comp_lookup
    self.compopt_state = compopt_state  # for compopt builtin
    self.comp_ui_state = comp_ui_state

    self.parse_ctx = parse_ctx
    self.debug_f = debug_f

  def Matches(self, comp):
    """
    Args:
      comp: Callback args from readline.  Readline uses set_completer_delims to
        tokenize the string.

    Returns a list of matches relative to readline's completion_delims.
    We have to post-process the output of various completers.
    """
    arena = self.parse_ctx.arena  # Used by inner functions

    # Pass the original line "out of band" to the completion callback.
    line_until_tab = comp.line[:comp.end]
    self.comp_ui_state.line_until_tab = line_until_tab

    self.parse_ctx.trail.Clear()
    line_reader = reader.StringLineReader(line_until_tab, self.parse_ctx.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader, emit_comp_dummy=True)

    # We want the output from parse_ctx, so we don't use the return value.
    try:
      c_parser.ParseLogicalLine()
    except error.Parse as e:
      # e.g. 'ls | ' will not parse.  Now inspect the parser state!
      pass

    debug_f = self.debug_f
    trail = self.parse_ctx.trail
    if 1:
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
      t2 = tokens[last-1]
    except IndexError:
      t2 = None

    debug_f.log('line: %r', comp.line)
    debug_f.log('rl_slice from byte %d to %d: %r', comp.begin, comp.end,
        comp.line[comp.begin:comp.end])

    debug_f.log('t1 %s', t1)
    debug_f.log('t2 %s', t2)

    # Each of the 'yield' statements below returns a fully-completed line, to
    # appease the readline library.  The root cause of this dance: If there's
    # one candidate, readline is responsible for redrawing the input line.  OSH
    # only displays candidates and never redraws the input line.

    def _TokenStart(tok):
      span = arena.GetLineSpan(tok.span_id)
      return span.col

    if t2:  # We always have t1?
      # echo $
      if IsDollar(t2) and IsDummy(t1):
        self.comp_ui_state.display_pos = _TokenStart(t2) + 1  # 1 for $
        for name in self.mem.VarNames():
          yield line_until_tab + name  # no need to quote var names
        return

      # echo ${
      if t2.id == Id.Left_DollarBrace and IsDummy(t1):
        self.comp_ui_state.display_pos = _TokenStart(t2) + 2  # 2 for ${
        for name in self.mem.VarNames():
          yield line_until_tab + name  # no need to quote var names
        return

      # echo $P
      if t2.id == Id.VSub_DollarName and IsDummy(t1):
        # Example: ${undef:-$P
        # readline splits at ':' so we have to prepend '-$' to every completed
        # variable name.
        self.comp_ui_state.display_pos = _TokenStart(t2) + 1  # 1 for $
        to_complete = t2.val[1:]
        n = len(to_complete)
        for name in self.mem.VarNames():
          if name.startswith(to_complete):
            yield line_until_tab + name[n:]  # no need to quote var names
        return

      # echo ${P
      if t2.id == Id.VSub_Name and IsDummy(t1):
        self.comp_ui_state.display_pos = _TokenStart(t2)  # no offset
        to_complete = t2.val
        n = len(to_complete)
        for name in self.mem.VarNames():
          if name.startswith(to_complete):
            yield line_until_tab + name[n:]  # no need to quote var names
        return

      # echo $(( VAR
      if t2.id == Id.Lit_ArithVarLike and IsDummy(t1):
        self.comp_ui_state.display_pos = _TokenStart(t2)  # no offset
        to_complete = t2.val
        n = len(to_complete)
        for name in self.mem.VarNames():
          if name.startswith(to_complete):
            yield line_until_tab + name[n:]  # no need to quote var names
        return

    if trail.words:
      # echo ~<TAB>
      # echo ~a<TAB> $(home dirs)
      # This must be done at a word level, and TildeDetectAll() does NOT help
      # here, because they don't have trailing slashes yet!  We can't do it on
      # tokens, because otherwise f~a will complete.  Looking at word_part is
      # EXACTLY what we want.
      parts = trail.words[-1].parts
      if (len(parts) == 2 and
          parts[0].tag == word_part_e.Literal and
          parts[1].tag == word_part_e.Literal and
          parts[0].id == Id.Lit_TildeLike and
          parts[1].id == Id.Lit_CompDummy):
        t2 = parts[0]

        # +1 for ~
        self.comp_ui_state.display_pos = _TokenStart(parts[0]) + 1

        to_complete = t2.val[1:]
        n = len(to_complete)
        for u in pwd.getpwall():  # catch errors?
          name = u.pw_name
          if name.startswith(to_complete):
            yield line_until_tab + ShellQuoteB(name[n:]) + '/'
        return

    # echo hi > f<TAB>   (complete redirect arg)
    if trail.redirects:
      r = trail.redirects[-1]
      # Only complete 'echo >', but not 'echo >&' or 'cat <<'
      if (r.tag == redir_e.Redir and
          REDIR_ARG_TYPES[r.op.id] == redir_arg_type_e.Path):
        if WordEndsWithCompDummy(r.arg_word):
          debug_f.log('Completing redirect arg')

          try:
            val = self.word_ev.EvalWordToString(r.arg_word)
          except error.FatalRuntime as e:
            debug_f.log('Error evaluating redirect word: %s', e)
            return
          if val.tag != value_e.Str:
            debug_f.log("Didn't get a string from redir arg")
            return

          span_id = word_.LeftMostSpanForWord(r.arg_word)
          span = arena.GetLineSpan(span_id)

          self.comp_ui_state.display_pos = span.col

          comp.Update(to_complete=val.s)  # FileSystemAction uses only this
          n = len(val.s)
          action = FileSystemAction(add_slash=True)
          for name in action.Matches(comp):
            yield line_until_tab + ShellQuoteB(name[n:])
          return

    #
    # We're not completing the shell language.  Delegate to user-defined
    # completion for external tools.
    #

    # Set below, and set on retries.
    base_opts = None
    user_spec = None

    # Used on retries.
    partial_argv = []
    num_partial = -1
    first = None

    if trail.words:
      # Now check if we're completing a word!
      if WordEndsWithCompDummy(trail.words[-1]):
        debug_f.log('Completing words')
        #
        # It didn't look like we need to complete var names, tilde, redirects,
        # etc.  Now try partial_argv, which may involve invoking PLUGINS.

        # needed to complete paths with ~
        words2 = word_.TildeDetectAll(trail.words)
        if 0:
          debug_f.log('After tilde detection')
          for w in words2:
            print(w, file=debug_f)

        if 0:
          debug_f.log('words2:')
          for w2 in words2:
            debug_f.log(' %s', w2)

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
          if val.tag == value_e.Str:
            partial_argv.append(val.s)
          else:
            pass

        debug_f.log('partial_argv: %s', partial_argv)
        num_partial = len(partial_argv)

        first = partial_argv[0]
        alias_first = None
        debug_f.log('alias_words: %s', trail.alias_words)

        if trail.alias_words:
          w = trail.alias_words[0]
          try:
            val = self.word_ev.EvalWordToString(w)
          except error.FatalRuntime:
            pass
          alias_first = val.s
          debug_f.log('alias_first: %s', alias_first)

        if num_partial == 0:  # should never happen because of Lit_CompDummy
          raise AssertionError
        elif num_partial == 1:
          base_opts, user_spec = self.comp_lookup.GetFirstSpec()

          # Display/replace since the beginning of the first word.  Note: this
          # is non-zero in the case of
          # echo $(gr   and
          # echo `gr

          span_id = word_.LeftMostSpanForWord(trail.words[0])
          span = arena.GetLineSpan(span_id)
          self.comp_ui_state.display_pos = span.col
          self.debug_f.log('** DISPLAY_POS = %d', self.comp_ui_state.display_pos)

        else:
          base_opts, user_spec = self.comp_lookup.GetSpecForName(first)
          if not user_spec and alias_first:
            base_opts, user_spec = self.comp_lookup.GetSpecForName(alias_first)
            if user_spec:
              # Pass the aliased command to the user-defined function, and use
              # it for retries.
              first = alias_first
          if not user_spec:
            base_opts, user_spec = self.comp_lookup.GetFallback()

          # Display since the beginning
          span_id = word_.LeftMostSpanForWord(trail.words[-1])
          span = arena.GetLineSpan(span_id)
          self.comp_ui_state.display_pos = span.col
          self.debug_f.log('words[-1]: %r', trail.words[-1])
          self.debug_f.log('display_pos %d', self.comp_ui_state.display_pos)

        # Update the API for user-defined functions.
        index = len(partial_argv) - 1  # COMP_CWORD is -1 when it's empty
        prev = '' if index == 0 else partial_argv[index-1]
        comp.Update(first=first, to_complete=partial_argv[-1],
                    prev=prev, index=index, partial_argv=partial_argv) 

    # This happens in the case of [[ and ((, or a syntax error like 'echo < >'.
    if not user_spec:
      debug_f.log("Didn't find anything to complete")
      return

    # Reset it back to what was registered.  User-defined functions can mutate
    # it.
    dynamic_opts = {}
    self.compopt_state.dynamic_opts = dynamic_opts
    self.compopt_state.currently_completing = True
    try:
      done = False
      while not done:
        try:
          for candidate in self._PostProcess(
              base_opts, dynamic_opts, user_spec, comp):
            yield candidate
        except _RetryCompletion as e:
          debug_f.log('Got 124, trying again ...')

          # Get another user_spec.  The ShellFuncAction may have 'sourced' code
          # and run 'complete' to mutate comp_lookup, and we want to get that
          # new entry.
          if num_partial == 0:
            raise AssertionError
          elif num_partial == 1:
            base_opts, user_spec = self.comp_lookup.GetFirstSpec()
          else:
            # (already processed alias_first)
            base_opts, user_spec = self.comp_lookup.GetSpecForName(first)
            if not user_spec:
              base_opts, user_spec = self.comp_lookup.GetFallback()
        else:
          done = True  # exhausted candidates without getting a retry
    finally:
      self.compopt_state.currently_completing = False

  def _PostProcess(self, base_opts, dynamic_opts, user_spec, comp):
    """
    Add trailing spaces / slashes to completion candidates, and time them.

    NOTE: This post-processing MUST go here, and not in UserSpec, because it's
    in READLINE in bash.  compgen doesn't see it.
    """
    self.debug_f.log('Completing %r ... (Ctrl-C to cancel)', comp.line)
    start_time = time.time()

    # TODO: dedupe candidates?  You can get two 'echo' in bash, which is dumb.

    i = 0
    for candidate, is_fs_action in user_spec.Matches(comp):
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
      if is_fs_action or opt_filenames:
        if path_stat.isdir(candidate):  # TODO: test coverage
          yield line_until_word + ShellQuoteB(candidate) + '/'
          continue

      opt_nospace = base_opts.get('nospace', False)
      if 'nospace' in dynamic_opts:
        opt_nospace = dynamic_opts['nospace']

      sp = '' if opt_nospace else ' '
      yield line_until_word + ShellQuoteB(candidate) + sp

      # NOTE: Can't use %.2f in production build!
      i += 1
      elapsed_ms = (time.time() - start_time) * 1000.0
      plural = '' if i == 1 else 'es'

      # TODO: Show this in the UI if it takes too long!
      if 0:
        self.debug_f.log(
            '... %d match%s for %r in %d ms (Ctrl-C to cancel)', i,
            plural, comp.line, elapsed_ms)

    elapsed_ms = (time.time() - start_time) * 1000.0
    plural = '' if i == 1 else 'es'
    self.debug_f.log(
        'Found %d match%s for %r in %d ms', i,
        plural, comp.line, elapsed_ms)

   
class ReadlineCallback(object):
  """A callable we pass to the readline module."""

  def __init__(self, readline_mod, root_comp, debug_f):
    self.readline_mod = readline_mod
    self.root_comp = root_comp
    self.debug_f = debug_f

    self.comp_iter = None  # current completion being processed

  def _GetNextCompletion(self, state):
    if state == 0:
      # TODO: Tokenize it according to our language.  If this is $PS2, we also
      # need previous lines!  Could make a VirtualLineReader instead of
      # StringLineReader?
      buf = self.readline_mod.get_line_buffer()

      # Readline parses "words" using characters provided by
      # set_completer_delims().
      # We have our own notion of words.  So let's call this a 'rl_slice'.
      begin = self.readline_mod.get_begidx()
      end = self.readline_mod.get_endidx()

      comp = Api(line=buf, begin=begin, end=end)

      self.comp_iter = self.root_comp.Matches(comp)

    assert self.comp_iter is not None, self.comp_iter

    try:
      next_completion = self.comp_iter.next()
    except StopIteration:
      next_completion = None  # signals the end

    return next_completion

  def __call__(self, unused_word, state):
    """Return a single match."""
    try:
      return self._GetNextCompletion(state)
    except util.UserExit as e:
      # TODO: Could use errfmt to show this
      ui.Stderr("osh: Ignoring 'exit' in completion plugin")
    except error.FatalRuntime as e:
      # From -W.  TODO: -F is swallowed now.
      # We should have a nicer UI for displaying errors.  Maybe they shouldn't
      # print it to stderr.  That messes up the completion display.  We could
      # print what WOULD have been COMPREPLY here.
      ui.Stderr('osh: Runtime error while completing: %s', e)
      self.debug_f.log('Runtime error while completing: %s', e)
    except (IOError, OSError) as e:
      # test this with prlimit --nproc=1 --pid=$$
      ui.Stderr('osh: I/O error in completion: %s', posix.strerror(e.errno))
    except KeyboardInterrupt:
      # It appears GNU readline handles Ctrl-C to cancel a long completion.
      # So this may never happen?
      ui.Stderr('Ctrl-C in completion')
    except Exception as e:  # ESSENTIAL because readline swallows exceptions.
      if 0:
        import traceback
        traceback.print_exc()
      ui.Stderr('osh: Unhandled exception while completing: %s', e)
      self.debug_f.log('Unhandled exception while completing: %s', e)
    except SystemExit as e:
      # Because readline ignores SystemExit!
      posix._exit(e.code)


if __name__ == '__main__':
  # This does basic filename copmletion
  import readline
  readline.parse_and_bind('tab: complete')
  while True:
    x = raw_input('$ ')
    print(x)
