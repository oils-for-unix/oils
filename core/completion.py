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


class NullCompleter(object):

  def Matches(self, comp):
    return []


_NULL_COMPLETER = NullCompleter()


class CompletionLookup(object):
  """Stores completion hooks registered by the user."""

  def __init__(self):
    # command name -> ChainedCompleter
    # There are pseudo commands __first and __fallback for -E and -D.
    self.lookup = {
        '__fallback': _NULL_COMPLETER,
        '__first': _NULL_COMPLETER,
        }

    # So you can register *.sh, unlike bash.  List of (glob, [actions]),
    # searched linearly.
    self.patterns = []

  def PrintSpecs(self):
    for name in sorted(self.lookup):
      print('%-15r %s' % (name, self.lookup[name]))
    print('---')
    for pat, chain in self.patterns:
      print('%s = %s' % (pat, chain))

  def RegisterName(self, name, chain):
    """Register a completion action with a name.
    Used by the 'complete' builtin.
    """
    self.lookup[name] = chain

  def RegisterGlob(self, glob_pat, chain):
    self.patterns.append((glob_pat, chain))

  def GetFirstCompleter(self):
    return self.lookup['__first']

  def GetCompleterForName(self, argv0):
    """
    Args:
      argv0: A finished argv0 to lookup
    """
    if not argv0:
      return self.GetFirstCompleter()

    chain = self.lookup.get(argv0)  # NOTE: Could be ''
    if chain:
      return chain

    key = os_path.basename(argv0)
    actions = self.lookup.get(key)
    if chain:
      return chain

    for glob_pat, chain in self.patterns:
      #log('Matching %r %r', key, glob_pat)
      if libc.fnmatch(glob_pat, key):
        return chain

    # Nothing matched
    return self.lookup['__fallback']


class CompletionApi(object):

  def __init__(self, line='', begin=0, end=0):
    """
    Args:
      index: if -1, then we're running through compgen
    """
    self.line = line
    self.begin = begin
    self.end = end

    # NOTE: COMP_WORDBREAKS is initliazed in Mem().

  def Update(self, words=None, index=0, to_complete=''):
    """Added after we've done parsing."""
    self.words = words or []  # COMP_WORDS
    self.index = index  # COMP_CWORD
    self.to_complete = to_complete  #

  def GetApiInput(self):
    """Returns argv and comp_words."""

    command = self.words[0]
    if self.index == -1:  # called directly by compgen, not by hitting TAB
      prev = ''
      comp_words = []  # not completing anything
    else:
      prev = '' if self.index == 0 else self.words[self.index - 1]
      comp_words = self.words

    return [command, self.to_complete, prev], comp_words

  def __repr__(self):
    """For testing"""
    return '<CompletionApi %r %d-%d>' % (self.line, self.begin, self.end)


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
  def __init__(self, dirs_only=False, exec_only=False):
    self.dirs_only = dirs_only
    self.exec_only = exec_only

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
        if self.dirs_only:
          if os_path.isdir(path):
            yield path
          continue

        if self.exec_only:
          # TODO: Handle exception if file gets deleted in between listing and
          # check?
          if not posix.access(path, posix.X_OK):
            continue

        if os_path.isdir(path):
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
    # TODO: Delete COMPREPLY here?  It doesn't seem to be defined in bash by
    # default.
    argv, comp_words = comp.GetApiInput()

    state.SetGlobalArray(self.ex.mem, 'COMP_WORDS', comp_words)
    state.SetGlobalString(self.ex.mem, 'COMP_CWORD', str(comp.index))
    state.SetGlobalString(self.ex.mem, 'COMP_LINE', comp.line)
    state.SetGlobalString(self.ex.mem, 'COMP_POINT', str(comp.end))

    self.log('Running completion function %r with arguments %s',
        self.func.name, argv)

    status = self.ex.RunFuncForCompletion(self.func, argv)
    if status == 124:
      self.log('Got status 124 from %r', self.func.name)
      raise _RetryCompletion()

    # Lame: COMP_REPLY would follow the naming convention!
    val = state.GetGlobal(self.ex.mem, 'COMPREPLY')
    if val.tag == value_e.Undef:
      util.error('Ran function %s but COMPREPLY was not defined', self.func.name)
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
  def __init__(self, glob_pat):
    self.glob_pat = glob_pat

  def __call__(self, match):
    return libc.fnmatch(self.glob_pat, match)


class ChainedCompleter(object):
  """A completer that tries a bunch of them in order.

  NOTE: plus_dirs happens AFTER filtering with predicates?  We add BACK the
  dirs, e.g. -A file -X '!*.sh' -o plusdirs.

  NOTE: plusdirs can just create another chained completer.  I think you should
  probably get rid of the predicate.  That should just be a Filter().  prefix
  and suffix can be adhoc for now I guess, since they are trivial.
  """
  def __init__(self, actions, predicate=None, prefix='', suffix=''):
    self.actions = actions
    # TODO: predicate is for GlobPredicate, for -X
    self.predicate = predicate or (lambda word: True)
    self.prefix = prefix
    self.suffix = suffix

  def Matches(self, comp, filter_func_matches=True):
    # NOTE: This has to be evaluated eagerly so we get the _RetryCompletion
    # exception.
    for a in self.actions:
      for match in a.Matches(comp):
        # Special case hack to match bash for compgen -F.  It doesn't filter by
        # to_complete!
        show = (
            match.startswith(comp.to_complete) and self.predicate(match) or
            (isinstance(a, ShellFuncAction) and not filter_func_matches)
        )

        # There are two kinds of filters: changing the string, and filtering
        # the set of strings.  So maybe have modifiers AND filters?  A triple.
        if show:
          yield self.prefix + match + self.suffix

    # Prefix is the current one?

    # What if the cursor is not at the end of line?  See readline interface.
    # That's OK -- we just truncate the line at the cursor?
    # Hm actually zsh does something smarter, and which is probably preferable.
    # It completes the word that

  def __str__(self):
    return '<ChainedCompleter %s %s %r %r>' % (
        self.actions, self.predicate, self.prefix, self.suffix)


class RootCompleter(object):
  """Dispatch to various completers.

  - Complete the OSH language (variables, etc.), or
  - Statically evaluate argv and dispatch to a command completer.
  """
  def __init__(self, word_ev, comp_lookup, mem, parse_ctx, progress_f,
               debug_f):
    self.word_ev = word_ev  # for static evaluation of words
    self.comp_lookup = comp_lookup  # to look up plugins
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
    _, c_parser = self.parse_ctx.MakeParserForCompletion(comp.line, arena)

    # NOTE Do we even use node?  We just want the output from parse_ctx.
    try:
      node = c_parser.ParseLogicalLine()
    except util.ParseError as e:
      # e.g. 'ls | ' will not parse.  Now inspect the parser state!
      node = None

    debug_f = self.debug_f
    comp_state = c_parser.parse_ctx.comp_state
    if 0:
      #log('command node = %s', com_node)
      #log('cur_token = %s', cur_token)
      #log('cur_word = %s', cur_word)
      log('comp_state = %s', comp_state)
    if 1:
      from osh import ast_lib
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

    toks = comp_state.tokens
    # NOTE: We get the EOF in the command state, but not in the middle of a
    # BracedVarSub.  Due to the way the WordParser works.

    last = -1
    if toks[-1].id == Id.Eof_Real:
      last -= 1  # ignore it

    try:
      t2 = toks[last]
    except IndexError:
      t2 = None
    try:
      t3 = toks[last-1]
    except IndexError:
      t3 = None

    # TODO: Add Lit_Dollar?
    def IsDollar(t):
      return t.id == Id.Lit_Other and t.val == '$'

    def IsDummy(t):
      return t.id == Id.Lit_CompDummy

    debug_f.log('line: %r', comp.line)
    debug_f.log('rl_slice from byte %d to %d: %r', comp.begin, comp.end,
        comp.line[comp.begin:comp.end])

    debug_f.log('t2 %s', t2)
    debug_f.log('t3 %s', t3)

    if t3:  # We always have t2?
      if IsDollar(t3) and IsDummy(t2):
        # TODO: share this with logic below.  Or use t2.
        span = arena.GetLineSpan(t3.span_id)
        t3_begin = span.col
        prefix = comp.line[comp.begin : t3_begin+1]  # +1 for the $

        for name in self.mem.VarNames():
          yield prefix + name
        return

      # echo ${
      if t3.id == Id.Left_VarSub and IsDummy(t2):
        for name in self.mem.VarNames():
          yield '${' + name
        return

      # echo $P
      if t3.id == Id.VSub_DollarName and IsDummy(t2):
        # Example: ${undef:-$P
        # readline splits at ':' so we have to prepend '-$' to every completed
        # variable name.
        span = arena.GetLineSpan(t3.span_id)
        t3_begin = span.col
        prefix = comp.line[comp.begin : t3_begin+1]  # +1 for the $
        to_complete = t3.val[1:]
        for name in self.mem.VarNames():
          if name.startswith(to_complete):
            yield prefix + name
        return

      # TODO: Remove duplication here!

      # echo ${P
      if t3.id == Id.VSub_Name and IsDummy(t2):
        # Example: ${undef:-$P
        # readline splits at ':' so we have to prepend '-$' to every completed
        # variable name.
        span = arena.GetLineSpan(t3.span_id)
        t3_begin = span.col
        prefix = comp.line[comp.begin : t3_begin]
        to_complete = t3.val
        for name in self.mem.VarNames():
          if name.startswith(to_complete):
            yield prefix + name
        return

      if t3.id == Id.Lit_ArithVarLike and IsDummy(t2):
        span = arena.GetLineSpan(t3.span_id)
        t3_begin = span.col
        prefix = comp.line[comp.begin : t3_begin]
        to_complete = t3.val
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
        t3 = parts[0].token

        # NOTE: Not bothering to compute prefix
        prefix = '~'
        to_complete = t3.val[1:]
        for u in pwd.getpwall():
          name = u.pw_name
          if name.startswith(to_complete):
            yield prefix + name + '/'
        return

    completer = None 

    # Check if we should complete a redirect
    if comp_state.redirects:
      r = comp_state.redirects[-1]
      debug_f.log('R: %s', r)
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
            debug_log.f("Didn't get a string from redir arg")
            return

          # TODO: Redirect path completion isn't user-definable, so we
          # shouldn't need Update() ?  That should be for API details.
          comp.Update(to_complete=val.s)
          completer = FileSystemAction()

    if comp_state.words:
      # Now check if we're completing a word!
      last_col = LastColForWord(comp_state.words[-1])
      debug_f.log('last_col for word: %d', last_col)
      if last_col == comp.end:  # We're not completing the last word!
        debug_f.log('Completing words')
        #
        # It didn't look like we need to complete var names, tilde, redirects, etc.
        # Now try partial_argv, which may involve invoking PLUGINS.

        # needed to complete paths with ~
        words2 = word.TildeDetectAll(comp_state.words)
        if 1:
          debug_f.log('After tilde detection')
          for w in words2:
            print(w, file=debug_f)

        partial_argv = []
        for w in words2:
          try:
            # TODO:
            # - Should we call EvalWordSequence?  But turn globbing off?  It can do
            # splitting and such.
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
          completer = self.comp_lookup.GetFirstCompleter()
        else:
          completer = self.comp_lookup.GetCompleterForName(partial_argv[0])

        # NOTE: GetFirstCompleter and GetCompleterForName can be user-defined
        # plugins.  So they both need this API options.

        index = len(partial_argv) - 1  # COMP_CWORD is -1 when it's empty
        # After parsing
        comp.Update(words=partial_argv, index=index, to_complete=partial_argv[-1])

    # This happens in the case of [[ and ((, or a syntax error like 'echo < >'.
    if not completer:
      debug_f.log("Didn't find anything to complete")
      return

    self.debug_f.log('Using %s', completer)

    self.progress_f.Write('Completing %r ... (Ctrl-C to cancel)', comp.line)
    start_time = time.time()

    i = 0
    for m in completer.Matches(comp):
      # TODO:
      # - dedupe these?  You can get two 'echo' in bash, which is dumb.
      # - Do shell QUOTING here for filenames?
      # - Add trailing slashes to directories?
      # - don't append space if 'nospace' is set?

      if m.endswith('/'):
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


class ReadlineCompleter(object):
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

      comp = CompletionApi(line=buf, begin=begin, end=end)

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
  complete_cb = ReadlineCompleter(readline_mod, root_comp, debug_f)
  InitReadline(readline_mod, complete_cb)


if __name__ == '__main__':
  # This does basic filename copmletion
  import readline
  readline.parse_and_bind('tab: complete')
  while True:
    x = raw_input('$ ')
    print(x)
