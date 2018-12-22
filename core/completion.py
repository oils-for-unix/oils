#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
completion.py - Tab completion.

TODO: Is this specific to osh/oil, or common?

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

bash note: most of this stuff is in pcomplete.c and bashline.c (4K lines!).
Uses ITEMLIST with a bunch of flags.
"""
from __future__ import print_function

import atexit
import posix
import pwd
import sys
import time

from core import alloc
from core import util
from core.meta import (
    Id, REDIR_ARG_TYPES, syntax_asdl, runtime_asdl, types_asdl)
from pylib import os_path
from osh import word
from osh import state

import libc

command_e = syntax_asdl.command_e
word_part_e = syntax_asdl.word_part_e
redir_e = syntax_asdl.redir_e
value_e = runtime_asdl.value_e
redir_arg_type_e = types_asdl.redir_arg_type_e

log = util.log


class _RetryCompletion(Exception):
  """For the 'exit 124' protocol."""
  pass


CH_Break, CH_Other = range(2)  # Character types
ST_Begin, ST_Break, ST_Other = range(3)  # States

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
  spans = []
  state = ST_Begin
  last_i = 0
  for i, c in enumerate(arg):
    ch = CH_Break if c in break_chars else CH_Other
    state, emit_span = _TRANSITIONS[state, ch]
    if emit_span:
      spans.append((last_i, i))
      last_i = i

  # Always emit a span at the end (even for empty string)
  n = len(arg)
  spans.append((last_i, n))

  for begin, end in spans:
    argv_out.append(arg[begin:end])


class NullCompleter(object):

  def Matches(self, comp):
    return []


class Options(object):
  def __init__(self, opt_changes):
    self.initial = dict(opt_changes)  # option name -> bool
    self.ephemeral = {}  # during one completion

  def Reset(self):
    self.ephemeral.clear()

  def Get(self, opt_name):
    try:
      return self.ephemeral[opt_name]
    except KeyError:
      return self.initial.get(opt_name, False)  # all default to False

  def Set(self, opt_name, b):
    self.ephemeral[opt_name] = b

# NOTE: How to create temporary options?  With copy.deepcopy()?
# We might want that as a test for OVM.  Copying is similar to garbage
# collection in that you walk a graph.


# These values should never be mutated.
_DEFAULT_OPTS = Options([])
_DO_NOTHING = (_DEFAULT_OPTS, NullCompleter())


class State(object):
  """Global completion state.
  
  It has two separate parts:
    
  1. Stores completion hooks registered by the user.
  2. Stores the state of the CURRENT completion.

  Both of them are needed in the RootCompleter and various builtins, so let's
  store them in the same object for convenience.
  """
  def __init__(self):
    # command name -> UserSpec
    # Pseudo-commands __first and __fallback are for -E and -D.
    self.lookup = {
        '__fallback': _DO_NOTHING,
        '__first': _DO_NOTHING,
    }

    # So you can register *.sh, unlike bash.  List of (glob, [actions]),
    # searched linearly.
    self.patterns = []

    # For the IN-PROGRESS completion.
    self.currently_completing = False
    # should be SET to a COPY of the registration options by the completer.
    self.current_opts = None

  def __str__(self):
    return '<completion.State %s>' % self.lookup

  def PrintSpecs(self):
    for name in sorted(self.lookup):
      print('%-15r %s' % (name, self.lookup[name]))
    print('---')
    for pat, spec in self.patterns:
      print('%s = %s' % (pat, spec))

  def RegisterName(self, name, comp_opts, user_spec):
    """Register a completion action with a name.
    Used by the 'complete' builtin.
    """
    self.lookup[name] = (comp_opts, user_spec)

  def RegisterGlob(self, glob_pat, comp_opts, user_spec):
    self.patterns.append((glob_pat, comp_opts, user_spec))

  def GetFirstSpec(self):
    return self.lookup['__first']

  def GetSpecForName(self, argv0):
    """
    Args:
      argv0: A finished argv0 to lookup
    """
    user_spec = self.lookup.get(argv0)  # NOTE: Could be ''
    if user_spec:
      return user_spec

    key = os_path.basename(argv0)
    actions = self.lookup.get(key)
    if user_spec:
      return user_spec

    for glob_pat, comp_opts, user_spec in self.patterns:
      #log('Matching %r %r', key, glob_pat)
      if libc.fnmatch(glob_pat, key):
        return user_spec

    # Nothing matched
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


class WordsAction(CompletionAction):
  # NOTE: Have to split the words passed to -W.  Using IFS or something else?
  def __init__(self, words, delay=None):
    self.words = words
    self.delay = delay

  def Matches(self, comp):
    for w in self.words:
      if w.startswith(comp.to_complete):
        if self.delay:
          time.sleep(self.delay)
        yield w


class FileSystemAction(CompletionAction):
  """Complete paths from the file system.

  Directories will have a / suffix.
  
  TODO: We need a variant that tests for an executable bit.
  """

  def __init__(self, dirs_only=False, exec_only=False, add_slash=False):
    self.dirs_only = dirs_only
    self.exec_only = exec_only

    # This is for redirects, not for UserSpec, which should respect compopt -o
    # filenames.
    self.add_slash = add_slash  # for directories

  def Matches(self, comp):
    to_complete = comp.to_complete
    i = to_complete.rfind('/')
    if i == -1:  # it looks like 'foo'
      to_list = '.'
      base = ''
    elif i == 0:  # it's an absolute path to_complete like / or /b
      to_list ='/'
      base = '/'
    else:
      to_list = to_complete[:i]
      base = to_list
      #log('to_list %r', to_list)

    try:
      names = posix.listdir(to_list)
    except OSError as e:
      return  # nothing

    for name in names:
      path = os_path.join(base, name)
      if path.startswith(to_complete):
        if self.dirs_only:  # add_slash not used here
          # NOTE: There is a duplicate isdir() check later to add a trailing
          # slash.  Consolidate the checks for fewer stat() ops.  This is hard
          # because all the completion actions must obey the same interface.
          # We could have another type like candidate = File | Dir |
          # OtherString ?
          if os_path.isdir(path):
            yield path
          continue

        if self.exec_only:
          # TODO: Handle exception if file gets deleted in between listing and
          # check?
          if not posix.access(path, posix.X_OK):
            continue

        if self.add_slash and os_path.isdir(path):
          yield path + '/'
        else:
          yield path


class ShellFuncAction(CompletionAction):
  """Call a user-defined function using bash's completion protocol."""

  def __init__(self, ex, func):
    self.ex = ex
    self.func = func

  def __repr__(self):
    # TODO: Add file and line number here!
    return '<ShellFuncAction %r>' % (self.func.name,)

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

    status = self.ex.RunFuncForCompletion(self.func, argv)
    if status == 124:
      self.log('Got status 124 from %r', self.func.name)
      raise _RetryCompletion()

    # Read the response.  We set it above, so this error would only happen if
    # the user unset it.
    # NOTE: 'COMP_REPLY' would follow the naming convention!
    val = state.GetGlobal(self.ex.mem, 'COMPREPLY')
    if val.tag == value_e.Undef:
      util.error('Ran function %s but COMPREPLY was not defined',
                 self.func.name)
      return []

    if val.tag != value_e.StrArray:
      log('ERROR: COMPREPLY should be an array, got %s', val)
      return []
    self.log('COMPREPLY %s', val)

    # Return this all at once so we don't have a generator.  COMPREPLY happens
    # all at once anyway.
    return val.strs


class VariablesAction(object):
  """compgen -A variable."""
  def __init__(self, mem):
    self.mem = mem

  def Matches(self, comp):
    for var_name in self.mem.VarNames():
      yield var_name


class ExternalCommandAction(object):
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

    # TODO: plusdirs could be in here, and doesn't respect predicate.
    # Fix that?
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
    return '<UserSpec %s %s %s %s %r %r>' % (
        self.actions, self.extra_actions, self.else_actions, self.predicate,
        self.prefix, self.suffix)


def _ShowCompState(comp_state, debug_f):
  from osh import ast_lib
  #debug_f.log('comp_state = %s', comp_state)
  debug_f.log('  words:')
  for w in comp_state.words:
    ast_lib.PrettyPrint(w, f=debug_f)
  debug_f.log('')

  debug_f.log('  redirects:')
  for r in comp_state.redirects:
    ast_lib.PrettyPrint(r, f=debug_f)
  debug_f.log('')

  debug_f.log('  tokens:')
  for p in comp_state.tokens:
    ast_lib.PrettyPrint(p, f=debug_f)
  debug_f.log('')


# Helpers for Matches()

# NOTE: We could add Lit_Dollar, but it would affect many lexer modes.
def IsDollar(t):
  return t.id == Id.Lit_Other and t.val == '$'

def IsDummy(t):
  return t.id == Id.Lit_CompDummy


class RootCompleter(object):
  """Dispatch to various completers.

  - Complete the OSH language (variables, etc.), or
  - Statically evaluate argv and dispatch to a command completer.
  """
  def __init__(self, word_ev, comp_state, mem, parse_ctx, progress_f,
               debug_f):
    self.word_ev = word_ev  # for static evaluation of words
    self.comp_state = comp_state  # to look up plugins
    self.mem = mem  # to complete variable names

    self.parse_ctx = parse_ctx
    self.progress_f = progress_f
    self.debug_f = debug_f

  def Matches(self, comp):
    """
    Args:
      comp: Callback args from readline.  Readline uses set_completer_delims to
        tokenize the string.

    Returns a list of matches relative to readline's completion_delims.
    We have to post-process the output of various completers.
    """
    # TODO: What is the point of this?  Can we manually reduce the amount of GC
    # time?
    arena = alloc.SideArena('<completion>')
    self.parse_ctx.PrepareForCompletion()
    c_parser = self.parse_ctx.MakeParserForCompletion(comp.line, arena)

    # We want the output from parse_ctx, so we don't use the return value.
    try:
      c_parser.ParseLogicalLine()
    except util.ParseError as e:
      # e.g. 'ls | ' will not parse.  Now inspect the parser state!
      pass

    debug_f = self.debug_f
    comp_state = c_parser.parse_ctx.comp_state
    if 1:
      _ShowCompState(comp_state, debug_f)

    # NOTE: We get Eof_Real in the command state, but not in the middle of a
    # BracedVarSub.  This is due to the difference between the CommandParser
    # and WordParser.
    tokens = comp_state.tokens
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

    def _MakePrefix(tok, offset=0):
      span = arena.GetLineSpan(tok.span_id)
      return comp.line[comp.begin : span.col+offset]

    if t2:  # We always have t1?
      if IsDollar(t2) and IsDummy(t1):
        prefix = _MakePrefix(t2, offset=1)
        for name in self.mem.VarNames():
          yield prefix + name
        return

      # echo ${
      if t2.id == Id.Left_VarSub and IsDummy(t1):
        prefix = _MakePrefix(t2, offset=2)  # 2 for ${
        for name in self.mem.VarNames():
          yield prefix + name
        return

      # echo $P
      if t2.id == Id.VSub_DollarName and IsDummy(t1):
        # Example: ${undef:-$P
        # readline splits at ':' so we have to prepend '-$' to every completed
        # variable name.
        prefix = _MakePrefix(t2, offset=1)  # 1 for $
        to_complete = t2.val[1:]
        for name in self.mem.VarNames():
          if name.startswith(to_complete):
            yield prefix + name
        return

      # echo ${P
      if t2.id == Id.VSub_Name and IsDummy(t1):
        prefix = _MakePrefix(t2)  # no offset
        to_complete = t2.val
        for name in self.mem.VarNames():
          if name.startswith(to_complete):
            yield prefix + name
        return

      if t2.id == Id.Lit_ArithVarLike and IsDummy(t1):
        prefix = _MakePrefix(t2)  # no offset
        to_complete = t2.val
        for name in self.mem.VarNames():
          if name.startswith(to_complete):
            yield prefix + name
        return

    # NOTE: Instead of looking at the column positions on line spans, we could
    # look for IsDummy() on the rightmost LiteralPart(token) of words.
    def LastColForWord(w):
      span_id = word.RightMostSpanForWord(w)
      span = arena.GetLineSpan(span_id)
      debug_f.log('span %s', span)
      debug_f.log('span col %d length %d', span.col, span.length)
      return span.col + span.length

    if comp_state.words:
      # First check if we're completing a path that begins with ~.
      #
      # Complete tilde like 'echo ~' and 'echo ~a'.  This must be done at a word
      # level, and TildeDetectAll() does NOT help here, because they don't have
      # trailing slashes yet!  We can't do it on tokens, because otherwise f~a
      # will complete.  Looking at word_part is EXACTLY what we want.
      parts = comp_state.words[-1].parts
      if (len(parts) == 2 and
          parts[0].tag == word_part_e.LiteralPart and
          parts[1].tag == word_part_e.LiteralPart and
          parts[0].token.id == Id.Lit_TildeLike and
          parts[1].token.id == Id.Lit_CompDummy):
        t2 = parts[0].token

        # NOTE: We're assuming readline does its job, and not bothering to
        # compute the prefix.  What are the incorrect corner cases?
        prefix = '~'
        to_complete = t2.val[1:]
        for u in pwd.getpwall():
          name = u.pw_name
          if name.startswith(to_complete):
            yield prefix + name + '/'
        return

    # Check if we should complete a redirect
    if comp_state.redirects:
      r = comp_state.redirects[-1]
      # Only complete 'echo >', but not 'echo >&' or 'cat <<'
      if (r.tag == redir_e.Redir and
          REDIR_ARG_TYPES[r.op.id] == redir_arg_type_e.Path):
        last_col = LastColForWord(r.arg_word)
        if last_col == comp.end:
          debug_f.log('Completing redirect arg')

          try:
            val = self.word_ev.EvalWordToString(r.arg_word)
          except util.FatalRuntimeError as e:
            debug_f.log('Error evaluating redirect word: %s', e)
            return
          if val.tag != value_e.Str:
            debug_f.log("Didn't get a string from redir arg")
            return

          comp.Update(to_complete=val.s)  # The FileSystemAction only uses one value
          action = FileSystemAction(add_slash=True)
          for name in action.Matches(comp):
            yield name
          return

    comp_opts = None
    user_spec = None   # Set below

    if comp_state.words:
      # Now check if we're completing a word!
      last_col = LastColForWord(comp_state.words[-1])
      debug_f.log('last_col for word: %d', last_col)
      if last_col == comp.end:  # We're not completing the last word!
        debug_f.log('Completing words')
        #
        # It didn't look like we need to complete var names, tilde, redirects,
        # etc.  Now try partial_argv, which may involve invoking PLUGINS.

        # needed to complete paths with ~
        words2 = word.TildeDetectAll(comp_state.words)
        if 0:
          debug_f.log('After tilde detection')
          for w in words2:
            print(w, file=debug_f)

        partial_argv = []
        for w in words2:
          try:
            # TODO:
            # - Should we call EvalWordSequence?  But turn globbing off?  It
            # can do splitting and such.
            # - We could have a variant to eval TildeSubPart to ~ ?
            val = self.word_ev.EvalWordToString(w)
          except util.FatalRuntimeError:
            # Why would it fail?
            continue
          if val.tag == value_e.Str:
            partial_argv.append(val.s)
          else:
            pass

        debug_f.log('partial_argv: %s', partial_argv)
        n = len(partial_argv)

        if n == 0:
          # should never get this because of Lit_CompDummy?
          raise AssertionError
        elif n == 1:
          # First
          comp_opts, user_spec = self.comp_state.GetFirstSpec()
        else:
          comp_opts, user_spec = self.comp_state.GetSpecForName(
              partial_argv[0])

        # Update the API for user-defined functions.
        index = len(partial_argv) - 1  # COMP_CWORD is -1 when it's empty
        prev = '' if index == 0 else partial_argv[index-1]
        comp.Update(first=partial_argv[0], to_complete=partial_argv[-1],
                    prev=prev, index=index, partial_argv=partial_argv) 

    # This happens in the case of [[ and ((, or a syntax error like 'echo < >'.
    if not user_spec:
      debug_f.log("Didn't find anything to complete")
      return

    # Reset it back to what was registered.  User-defined functions can mutate
    # it.
    comp_opts.Reset()
    self.comp_state.current_opts = comp_opts
    self.comp_state.currently_completing = True
    try:
      for entry in self._PostProcess(comp_opts, user_spec, comp):
        yield entry
    finally:
      self.comp_state.currently_completing = False

  def _PostProcess(self, comp_opts, user_spec, comp):
    """
    Add trailing spaces / slashes to completion candidates, and time them.
    """
    self.progress_f.Write('Completing %r ... (Ctrl-C to cancel)', comp.line)
    start_time = time.time()

    i = 0
    for m, is_fs_action in user_spec.Matches(comp):
      # TODO:
      # - dedupe these?  You can get two 'echo' in bash, which is dumb.
      # - Do shell QUOTING here for filenames?

      # NOTE: This post-processing MUST go here, and not in UserSpec, because
      # it's in READLINE in bash.  compgen doesn't see it.

      # compopt -o filenames is for user-defined actions.  Or any
      # FileSystemAction needs it.
      if is_fs_action or comp_opts.Get('filenames'):
        if os_path.isdir(m):  # TODO: test coverage
          yield m + '/'
          continue

      if comp_opts.Get('nospace'):
        yield m
      else:
        yield m + ' '

      # NOTE: Can't use %.2f in production build!
      i += 1
      elapsed_ms = (time.time() - start_time) * 1000.0
      plural = '' if i == 1 else 'es'
      self.progress_f.Write(
          '... %d match%s for %r in %d ms (Ctrl-C to cancel)', i,
          plural, comp.line, elapsed_ms)

    elapsed_ms = (time.time() - start_time) * 1000.0
    plural = '' if i == 1 else 'es'
    self.progress_f.Write(
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

    done = False
    while not done:
      #self.debug_f.log('comp_iter.next()')
      try:
        next_completion = self.comp_iter.next()
        done = True
      except _RetryCompletion:
        # TODO: Is it OK to retry here?  Shouldn't we retry in
        # RootCompleter, after we already know the words?  That seems to run
        # into some problems with Python generators and exceptions.
        # I kind of want the 'g.send()' pattern to "prime the generator",
        # revealing the first exception.
        pass
      except StopIteration:
        next_completion = None  # sentinel?
        done = True

    return next_completion

  def __call__(self, unused_word, state):
    """Return a single match."""
    try:
      return self._GetNextCompletion(state)
    except Exception as e:  # ESSENTIAL because readline swallows exceptions.
      import traceback
      traceback.print_exc()
      log('Unhandled exception while completing: %s', e)
      self.debug_f.log('Unhandled exception while completing: %s', e)
    except SystemExit as e:
      # Because readline ignores SystemExit!
      posix._exit(e.code)


def InitReadline(readline_mod, complete_cb):
  home_dir = posix.environ.get('HOME')
  if home_dir is None:
    home_dir = util.GetHomeDir()
    if home_dir is None:
      print("Couldn't find home dir in $HOME or /etc/passwd", file=sys.stderr)
      return
  # TODO: Put this in .config/oil/.
  history_filename = os_path.join(home_dir, 'oil_history')

  try:
    readline_mod.read_history_file(history_filename)
  except IOError:
    pass

  # The 'atexit' module is a small wrapper around sys.exitfunc.
  atexit.register(readline_mod.write_history_file, history_filename)
  readline_mod.parse_and_bind("tab: complete")

  # How does this map to C?
  # https://cnswww.cns.cwru.edu/php/chet/readline/readline.html#SEC45

  readline_mod.set_completer(complete_cb)

  # http://web.mit.edu/gnu/doc/html/rlman_2.html#SEC39
  # "The basic list of characters that signal a break between words for the
  # completer routine. The default value of this variable is the characters
  # which break words for completion in Bash, i.e., " \t\n\"\\'`@$><=;|&{(""

  # This determines the boundaries you get back from get_begidx() and
  # get_endidx() at completion time!
  # We could be more conservative and set it to ' ', but then cases like
  # 'ls|w<TAB>' would try to complete the whole thing, intead of just 'w'.
  #
  # Note that this should not affect the OSH completion algorithm.  It only
  # affects what we pass back to readline and what readline displays to the
  # user!
  readline_mod.set_completer_delims(util.READLINE_DELIMS)


def Init(readline_mod, root_comp, debug_f):
  complete_cb = ReadlineCallback(readline_mod, root_comp, debug_f)
  InitReadline(readline_mod, complete_cb)


if __name__ == '__main__':
  # This does basic filename copmletion
  import readline
  readline.parse_and_bind('tab: complete')
  while True:
    x = raw_input('$ ')
    print(x)
