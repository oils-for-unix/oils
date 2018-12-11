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
import sys
import time
#import traceback

from core import alloc
from core import util
from core.meta import syntax_asdl, runtime_asdl
from pylib import os_path
from osh import state

import libc

command_e = syntax_asdl.command_e
value_e = runtime_asdl.value_e
comp_kind_e = runtime_asdl.comp_kind_e

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


class VariablesActionInternal(object):
  """When we parse $VAR ourselves.

  TODO: Also need to complete ${P (BracedVarSub)
  """
  def __init__(self, mem):
    self.mem = mem

  def Matches(self, comp):
    to_complete = comp.to_complete
    assert to_complete.startswith('$')
    to_complete = to_complete[1:]
    for name in self.mem.VarNames():
      if name.startswith(to_complete):
        yield '$' + name


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


# TODO: This breaks completion of ~/.config, because $HOME isn't expanded.  We
# need to use real parser.

class DummyParser(object):

  def GetWords(self, buf):
    words = buf.split()
    # 'grep ' -> ['grep', ''], so we're completing the second word
    if buf.endswith(' '):
      words.append('')
    return words


def _FindLastSimpleCommand(node):
  """
  The last thing has to be a simple command.  Cases:

  echo a; echo b
  ls | wc -l
  test -f foo && hello
  """
  if node.tag == command_e.SimpleCommand:
    return node
  if node.tag == command_e.Sentence:
    return node.child
  if node.tag == command_e.TimeBlock:
    child = node.pipeline
    if child.tag == command_e.SimpleCommand:
      return child
    if child.tag == command_e.Pipeline:
      return child.children[0]
  if node.tag == command_e.Assignment:
    return None
  if node.tag == command_e.ControlFlow:
    return None

  assert hasattr(node, 'children'), node

  n = len(node.children)
  if n == 0:
    return None

  # Go as deep as we need.
  return _FindLastSimpleCommand(node.children[-1])


def _GetCompKind(w_parser, c_parser, word_ev, debug_f):
  """What kind of values should we complete?

  Args:
    w_parser, c_parser, word_ev: For inspecting parser state
    debug_f: Debug file

  Returns:
    comp_type
    prefix: the prefix to complete
    comp_words: list of words.  First word is used for dispatching.

  We try to parse the command line, then inspect the state of various parsers.
  That turns into comp_kind_e and a partial_argv.

  NOTE: partial_argv isn't necessary for comp_kind_e.{VarName,HashKey} etc.?

  We also look at the state of the LineLexer in order to determine if we're
  completing a new word.

  """
  # Return values
  kind = comp_kind_e.First
  to_complete = ''
  partial_argv = []

  try:
    node = c_parser.ParseLogicalLine()
  except util.ParseError as e:
    # e.g. 'ls | ' will not parse.  Now inspect the parser state!
    node = None

  # Inspect state after parsing.  Hm I'm getting the newline.  Can I view the
  # one before that?
  cur_token = w_parser.cur_token
  prev_token = w_parser.PrevToken()
  cur_word = w_parser.cursor

  # Find the last SimpleCommandNode.
  com_node = None
  if node:
    # These 4 should all parse
    if node.tag == command_e.SimpleCommand:
      com_node = node

    elif node.tag == command_e.CommandList:  # echo a; echo b
      com_node = _FindLastSimpleCommand(node)
    elif node.tag == command_e.AndOr:  # echo a && echo b
      com_node = _FindLastSimpleCommand(node)
    elif node.tag == command_e.Pipeline:  # echo a | wc -l
      com_node = _FindLastSimpleCommand(node)
    else:
      # Return comp_kind_e.Nothing?  Not handling it for now
      pass
  else:  # No node.
    pass

  if 0:
    log('command node = %s', com_node)
    log('prev_token = %s', prev_token)
    log('cur_token = %s', cur_token)
    log('cur_word = %s', cur_word)
    log('comp_state = %s', c_parser.parse_ctx.comp_state)
  if 1:
    from osh import ast_lib
    print('  words:')
    for w in c_parser.parse_ctx.comp_state.words:
      ast_lib.PrettyPrint(w)
    print()
    print('  parts:')
    for p in c_parser.parse_ctx.comp_state.word_parts:
      ast_lib.PrettyPrint(p)
    print()
    print('  tokens:')
    for p in c_parser.parse_ctx.comp_state.tokens:
      ast_lib.PrettyPrint(p)
    print()

  if 0:
    # Hm we need token IDs, not just line spans.
    print('--')
    arena = c_parser.parse_ctx.arena
    last_span_id = arena.LastSpanId()
    for spid in xrange(0, last_span_id):
      span = arena.GetLineSpan(spid)
      ast_lib.PrettyPrint(span)

  if com_node:
    for w in com_node.words:
      try:
        # TODO: Should we call EvalWordSequence?  But turn globbing off?  It
        # can do splitting and such.
        val = word_ev.EvalWordToString(w)
      except util.FatalRuntimeError:
        # Why would it fail?
        continue
      if val.tag == value_e.Str:
        partial_argv.append(val.s)
      else:
        pass
        # Oh I have to handle $@ on the command line?

  # TODO: Detect SimpleVarSub and BracedVarSub?
  #
  # FindLastVarSub on the word nodes?
  # Does it make sense to write a function that flattens the LST?
  # And then we look for the last thing?
  #
  # Do we care about this?
  #
  # copy --verb'o'<TAB>
  #
  # o=$o
  # copy --verb'o'<TAB>
  # We should check language completions FIRST.

  # To distinguish 'echo<TAB>' vs. 'echo <TAB>'.  Could instead we look for
  # Id.Ignored_Space somewhere?  Not sure if it's worth it.
  cur_line = c_parser.lexer.GetCurrentLine()
  #log('current line = %r', cur_line)
  # Done with CompDummy
  #if cur_line.endswith(' '):
  #  partial_argv.append('')

  n = len(partial_argv)

  if n == 0:
    kind = comp_kind_e.First
    to_complete = ''
  elif n == 1:
    kind = comp_kind_e.First
    to_complete = partial_argv[-1]
  else:
    kind = comp_kind_e.Rest
    to_complete = partial_argv[-1]

  # TODO: Need to show buf... Need a multiline display for debugging?
  if 0:
    debug_f.log('prev_token %s  cur_token %s  cur_word %s',
        prev_token, cur_token, cur_word)
    debug_f.log('comp_state %s  error %s', comp_state, c_parser.Error())
    # This one can be multiple lines
    debug_f.log('node: %s %s', repr(node) if node else '<Parse Error>',
                  node.tag if node else '')
    # This one can be multiple lines
    debug_f.log('com_node: %s', repr(com_node) if com_node else '<None>')

  return kind, to_complete, partial_argv


def _GetCompKindHeuristic(parser, buf):
  """Hacky implementation using heuristics."""
  words = parser.GetWords(buf)  # just does a dummy split for now

  n = len(words)
  # Complete variables
  # TODO: Parser should tell if we saw $, ${, but are NOT in a single quoted
  # state.  And also we didn't see $${, which would be a special var.  Oil
  # rules are almost the same.
  if n > 0 and words[-1].startswith('$'):
    comp_type = comp_kind_e.VarName
    to_complete = words[-1]

  # Otherwise complete words
  elif n == 0:
    comp_type = comp_kind_e.First
    to_complete = ''
  elif n == 1:
    comp_type = comp_kind_e.First
    to_complete = words[-1]
  else:
    comp_type = comp_kind_e.Rest
    to_complete = words[-1]

  comp_index = len(words) - 1
  return comp_type, to_complete, words


class RootCompleter(object):
  """
  Provide completion of a buffer according to the configured rules.
  """
  def __init__(self, word_ev, comp_lookup, var_comp, parse_ctx, progress_f,
               debug_f):
    self.word_ev = word_ev
    self.comp_lookup = comp_lookup
    # This can happen in any position, with any command
    self.var_comp = var_comp
    self.parse_ctx = parse_ctx
    self.progress_f = progress_f
    self.debug_f = debug_f

    # This simply splits words!
    self.parser = DummyParser()  # TODO: remove

  def Matches(self, comp):
    arena = alloc.SideArena('<completion>')

    # Two strategies:
    # 1. COMP_WORDBREAKS like bash.  set_completer_delims()
    # 2. Use the actual OSH parser.  Parse these cases:
    #   - echo 
    #   - $VA
    #   - ${VA
    #   - $(echo h)
    #     - <(echo h)
    #     - >(echo h)
    #     - ``
    #   - $(( VA    # This should be a variable name
    #   - while false; do <TAB>
    #   - if <TAB>
    #   - while <TAB> -- bash gets this wrong!
    #   - command <TAB> -- bash-completion fills this in
    #   - alias completion?
    #     - alias ll='ls -l'
    #   - also var expansion?  
    #     foo=ls
    #     $foo <TAB>    (even ZSH doesn't seem to handle this)
    #
    # the empty completer is consistently wrong.  Only works in the first
    # position.
    #
    # I think bash-completion is fighting with bash?
    #
    # completing aliases -- someone mentioned about zsh

    if 0:  # TODO: enable
      comp_type, to_complete, comp_words = _GetCompKindHeuristic(self.parser,
                                                                 comp.line)
      self.debug_f.log(
          'OLD comp_type: %s, to_complete: %s, comp_words %s', comp_type,
          to_complete, comp_words)

      w_parser, c_parser = self.parse_ctx.MakeParserForCompletion(comp.line, arena)
      # NOTE: comp_words could be argv or partial_argv?  They are stripped of
      # shell syntax.
      comp_type, to_complete, comp_words = _GetCompKind(w_parser, c_parser,
                                                        self.word_ev,
                                                        self.debug_f)
    else:
      comp_type, to_complete, comp_words = _GetCompKindHeuristic(self.parser,
                                                                 comp.line)
    self.debug_f.log(
        'NEW comp_type: %s, to_complete: %s, comp_words %s', comp_type,
        to_complete, comp_words)

    index = len(comp_words) - 1  # COMP_CWORD is -1 when it's empty

    # After parsing
    comp.Update(words=comp_words, index=index, to_complete=to_complete)

    # Non-user chains
    if comp_type == comp_kind_e.VarName:
      # TODO: 
      # - echo $F
      # - echo ${F
      # - echo $(( 2 * F ))  # var name here
      # - echo $(echo ${undef:-${F    # required completing ${F
      chain = self.var_comp
    elif comp_type == comp_kind_e.HashKey:
      chain = 'TODO: look in hash table keys'
    elif comp_type == comp_kind_e.RedirPath:
      chain = FileSystemAction()

    elif comp_type == comp_kind_e.First:
      chain = self.comp_lookup.GetFirstCompleter()
    elif comp_type == comp_kind_e.Rest:
      chain = self.comp_lookup.GetCompleterForName(comp_words[0])

    elif comp_type == comp_kind_e.Nothing:
      # Null chain?  No completion?  For example,
      # ${a:- <TAB>  -- we have no idea what to put here
      chain = 'TODO'
    else:
      raise AssertionError(comp_type)

    self.progress_f.Write('Completing %r ... (Ctrl-C to cancel)', comp.line)
    start_time = time.time()

    self.debug_f.log('Using %s', chain)

    i = 0
    for m in chain.Matches(comp):
      # TODO: dedupe these?  You can get two 'echo' in bash, which is dumb.

      if m.endswith('/'):
        yield m
      else:
        # TODO: don't append space if 'nospace' is set?
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
    done = True

    # TODO: Have to de-dupe and sort these?  Because 'echo' is a builtin as
    # well as a command, and we don't want to show it twice.  Although then
    # it's not incremental.  We can still show progress though.  Need
    # status_line.


class ReadlineCompleter(object):
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

      # Begin: the index of the first char of the 'word' in the line.  Words
      # are parsed according to readline delims (which we won't use).

      begin = self.readline_mod.get_begidx()

      # The current position of the cursor.  The thing being completed.
      end = self.readline_mod.get_endidx()

      comp = CompletionApi(line=buf, begin=begin, end=end)
      self.debug_f.log(
          'line: %r / begin - end: %d - %d, part: %r', buf, begin, end,
          buf[begin:end])

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
    # NOTE: The readline library tokenizes words.  We bypass that and use
    # get_line_buffer().  So we get 'for x in l' instead of just 'l'.

    #self.debug_f.log(0, 'word %r state %s', unused_word, state)
    try:
      return self._GetNextCompletion(state)
    except Exception as e:
      #traceback.print_exc()
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
