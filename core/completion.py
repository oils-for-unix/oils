#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
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

import atexit
import os
import sys
import time
import traceback

from osh.meta import ast, runtime
from core import alloc
from core import state
from core import util

import libc

command_e = ast.command_e
value_e = runtime.value_e
completion_state_e = runtime.completion_state_e

log = util.log


class _RetryCompletion(Exception):
  """For the 'exit 124' protocol."""
  pass


class NullCompleter(object):

  def Matches(self, words, index, to_complete):
    return []


_NULL_COMPLETER = NullCompleter()


class CompletionLookup(object):
  """
  names -> list of actions

  -E -> list of actions
  -D -> default list of actions, when we don't know

  Maybe call those __DEFAULT__ and '' or something, -D and -E is
  confusing.

  But I also want to register patterns.
  """
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

    key = os.path.basename(argv0)
    actions = self.lookup.get(key)
    if chain:
      return chain

    for glob_pat, chain in self.patterns:
      #log('Matching %r %r', key, glob_pat)
      if libc.fnmatch(glob_pat, key):
        return chain

    # Nothing matched
    return self.lookup['__fallback']


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

  def Matches(self, words, index, to_complete):
    pass


class WordsAction(CompletionAction):
  # NOTE: Have to split the words passed to -W.  Using IFS or something else?
  def __init__(self, words, delay=None):
    self.words = words
    self.delay = delay

  def Matches(self, words, index, to_complete):
    for w in self.words:
      if w.startswith(to_complete):
        if self.delay:
          time.sleep(self.delay)
        yield w + ' '


class FileSystemAction(CompletionAction):
  """Complete paths from the file system.

  Directories will have a / suffix.
  
  TODO: We need a variant that tests for an executable bit.
  """
  def Matches(self, words, index, to_complete):
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
      names = os.listdir(to_list)
    except OSError as e:
      return  # nothing

    for name in names:
      path = os.path.join(base, name)
      if path.startswith(to_complete):
        if os.path.isdir(path):
          yield path + '/'
        else:
          yield path


class ShellFuncAction(CompletionAction):
  def __init__(self, ex, func):
    self.ex = ex
    self.func = func

  def __repr__(self):
    # TODO: Add file and line number here!
    return '<ShellFuncAction %r>' % (self.func.name,)

  def log(self, *args):
    self.ex.debug_f.log(*args)

  def Matches(self, comp_words, index, to_complete):
    # TODO: Delete COMPREPLY here?  It doesn't seem to be defined in bash by
    # default.
    command = comp_words[0]

    if index == -1:  # called directly by compgen, not by hitting TAB
      prev = ''
      comp_words = []  # not completing anything?
    else:
      prev = '' if index == 0 else comp_words[index-1]

    argv = [command, to_complete, prev]

    state.SetGlobalArray(self.ex.mem, 'COMP_WORDS', comp_words)
    state.SetGlobalString(self.ex.mem, 'COMP_CWORD', str(index))

    self.log('Running completion function %r with arguments %s',
        self.func.name, argv)

    status = self.ex.RunFuncForCompletion(self.func, argv)
    if status == 124:
      self.log('Got status 124 from %r', self.func.name)
      raise _RetryCompletion()

    # Should be COMP_REPLY to follow naming convention!  Lame.
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

  def Matches(self, words, index, to_complete):
    for var_name in self.mem.VarNames():
      yield var_name


class VariablesActionInternal(object):
  """When we parse $VAR ourselves.

  TODO: Also need to complete ${P (BracedVarSub)
  """
  def __init__(self, mem):
    self.mem = mem

  def Matches(self, words, index, to_complete):
    assert to_complete.startswith('$')
    to_complete = to_complete[1:]
    for name in self.mem.VarNames():
      if name.startswith(to_complete):
        yield '$' + name + ' '  # full word


class ExternalCommandAction(object):
  """Complete commands in $PATH.

  NOTE: -A command in bash is FIVE things: aliases, builtins, functions,
  keywords, etc.
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

  def Matches(self, words, index, to_complete):
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
    #print(path_dirs)

    names = []
    for d in path_dirs:
      try:
        st = os.stat(d)
      except OSError as e:
        # There could be a directory that doesn't exist in the $PATH.
        continue
      key = (d, st.st_mtime)
      listing = self.cache.get(key)
      if listing is None:
        listing = os.listdir(d)
        self.cache[key] = listing
      names.extend(listing)

    # TODO: Shouldn't do the prefix / space thing ourselves.  readline does
    # that at the END of the line.
    for word in listing:
      if word.startswith(to_complete):
        yield word + ' '


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

  def Matches(self, words, index, to_complete, filter_func_matches=True):
    # NOTE: This has to be evaluated eagerly so we get the _RetryCompletion
    # exception.
    for a in self.actions:
      for match in a.Matches(words, index, to_complete):
        # Special case hack to match bash for compgen -F.  It doesn't filter by
        # to_complete!
        show = (
            match.startswith(to_complete) and self.predicate(match) or
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


def _GetCompletionType(w_parser, c_parser, ev, debug_f):
  """
  Parser returns completion state.
  Then we translate that into completion_state_e.

  Returns:
    comp_type
    prefix: the prefix to complete
    comp_words: list of words.  First word is used for dispatching.

    TODO: what about hash table name?
  """
  # TODO: Fill these in
  comp_type = completion_state_e.FIRST
  prefix = ''
  words = []

  try:
    node = c_parser.ParseLogicalLine()
  except util.ParseError as e:
    return comp_type, prefix, words  # EARLY RETURN

  # Inspect state after parsing.  Hm I'm getting the newline.  Can I view the
  # one before that?
  cur_token = w_parser.cur_token
  prev_token = w_parser.PrevToken()
  cur_word = w_parser.cursor
  comp_state = c_parser.GetCompletionState()

  com_node = None
  if node:
    # These 4 should all parse
    if node.tag == command_e.SimpleCommand:
      # NOTE: prev_token can be ;, then complete a new one
      #print('WORDS', node.words)
      # TODO:
      # - EvalVarSub depends on memory
      # - EvalTildeSub needs to be somewhere else
      # - EvalCommandSub needs to be
      #
      # maybe write a version of Executor._EvalWordSequence that doesn't do
      # CommandSub.  Or honestly you can just reuse it for now.  Can you pass
      # the same cmd_exec in?  What about side effects?  I guess it can't
      # really have any.  It can only have them on the file system.  Hm.
      # Defining funcitons?  Yeah if you complete partial functions that could
      # be bad.  That is, you could change the name of the function.

      argv = []
      for w in node.words:
        try:
          # TODO: Should we call EvalWordSequence?  But turn globbing off?  It
          # can do splitting and such.
          val = ev.EvalWordToString(w)
        except util.FatalRuntimeError:
          # Why would it fail?
          continue
        if val.tag == value_e.Str:
          argv.append(val.s)
        else:
          pass
          # Oh I have to handle $@ on the command line?

      #print(argv)
      com_node = node

    elif node.tag == command_e.CommandList:  # echo a; echo b
      com_node = _FindLastSimpleCommand(node)
    elif node.tag == command_e.AndOr:  # echo a && echo b
      com_node = _FindLastSimpleCommand(node)
    elif node.tag == command_e.Pipeline:  # echo a | wc -l
      com_node = _FindLastSimpleCommand(node)
    else:
      # Return NONE?  Not handling it for now
      pass
  else:  # No node.
    pass

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

  # IMPORTANT: if the last token is Id.Ignored_Space, then we want to add a
  # dummy word!  empty word

  # initial simple algorithm
  # If we got a node:
  #   1. Look at c_parser.LastCompletionState()
  #   1. don't complete unless it's SIMPLE_COMMAND?
  #   2. look at node.words -- first word or not?
  #   3. EvalStatic() of the first word

  # If we got None:
  #   1. Look at c_parser.LastCompletionState()
  #   2. If it is $ or ${, complete var names
  #
  #   Is there any case where we shoudl fall back on buf.split()?

  # Now parse it.  And then look at the AST, but don't eval?  Or actually we
  # CAN eval, but we probably don't want to.
  #
  # completion state also has to know about ${pre<TAB>  and ${foo[pre<TAB>
  # Those are invalid parses.  But the LAST TOKEN is the one we want to
  # complete?  Will it be a proper group of LIT tokens?  I don't think you
  # complete anything else besides that?
  #
  # $<TAB> will be Id.Lit_Other -- but you might want to special case
  # $na<TAB> will be VS_NAME

  # NOTE: The LineLexer adds \n to the buf?  Should we disable it and add \0?

  # I guess the shortest way to do it is to just Eval(), and even run command
  # sub.  Or maybe SafeEval() for command sub returns __DUMMY__ or None or some
  # other crap.
  # I guess in oil you could have some arbitrarily long function in $split(bar,
  # baz).  That is what you would want to run the completion in a subprocess
  # with a timeout.
  return comp_type, prefix, words


def _GetCompletionType1(parser, buf):
  words = parser.GetWords(buf)
  comp_name = None

  n = len(words)
  # Complete variables
  # TODO: Parser should tell if we saw $, ${, but are NOT in a single quoted
  # state.  And also we didn't see $${, which would be a special var.  Oil
  # rules are almost the same.
  if n > 0 and words[-1].startswith('$'):
    comp_type = completion_state_e.VAR_NAME
    prefix = words[-1]

  # Otherwise complete words
  elif n == 0:
    comp_type = completion_state_e.FIRST
    prefix = ''
  elif n == 1:
    comp_type = completion_state_e.FIRST
    prefix = words[-1]
  else:
    comp_type = completion_state_e.REST
    prefix = words[-1]

  comp_index = len(words) - 1
  return comp_type, prefix, words


class RootCompleter(object):
  """
  Provide completion of a buffer according to the configured rules.
  """
  def __init__(self, ev, comp_lookup, var_comp, parse_ctx, progress_f,
               debug_f):
    self.ev = ev
    self.comp_lookup = comp_lookup
    # This can happen in any position, with any command
    self.var_comp = var_comp
    self.parse_ctx = parse_ctx
    self.progress_f = progress_f
    self.debug_f = debug_f

    # This simply splits words!
    self.parser = DummyParser()  # TODO: remove

  def Matches(self, buf):
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

    if 0:
      w_parser, c_parser = self.parse_ctx.MakeParserForCompletion(buf, arena)
      comp_type, to_complete, comp_words = _GetCompletionType(
          w_parser, c_parser, self.ev, self.debug_f)
    else:
      comp_type, to_complete, comp_words = _GetCompletionType1(self.parser, buf)

    if comp_type == completion_state_e.VAR_NAME:
      # Non-user chain
      chain = self.var_comp
    elif comp_type == completion_state_e.HASH_KEY:
      # Non-user chain
      chain = 'TODO'
    elif comp_type == completion_state_e.REDIR_FILENAME:
      # Non-user chain
      chain = FileSystemAction()

    elif comp_type == completion_state_e.FIRST:
      chain = self.comp_lookup.GetFirstCompleter()
    elif comp_type == completion_state_e.REST:
      chain = self.comp_lookup.GetCompleterForName(comp_words[0])

    elif comp_type == completion_state_e.NONE:
      # Null chain?  No completion?  For example,
      # ${a:- <TAB>  -- we have no idea what to put here
      chain = 'TODO'
    else:
      raise AssertionError(comp_type)

    self.progress_f.Write('Completing %r ... (Ctrl-C to cancel)', buf)
    start_time = time.time()

    index = len(comp_words) - 1  # COMP_CWORD -1 when it's empty
    self.debug_f.log('Using %s', chain)

    i = 0
    for m in chain.Matches(comp_words, index, to_complete):
      # TODO: need to dedupe these
      yield m
      i += 1
      elapsed = time.time() - start_time
      plural = '' if i == 1 else 'es'
      self.progress_f.Write(
          '... %d match%s for %r in %.2f seconds (Ctrl-C to cancel)', i,
          plural, buf, elapsed)

    elapsed = time.time() - start_time
    plural = '' if i == 1 else 'es'
    self.progress_f.Write(
        'Found %d match%s for %r in %.2f seconds', i,
        plural, buf, elapsed)
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

      self.debug_f.log(
          'line: %r / begin - end: %d - %d, part: %r', buf, begin, end,
          buf[begin:end])

      self.comp_iter = self.root_comp.Matches(buf)

    assert self.comp_iter is not None, self.comp_iter

    done = False
    while not done:
      self.debug_f.log('comp_iter.next()')
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
      traceback.print_exc()
      self.debug_f.log('Unhandled exception while completing: %s', e)


def InitReadline(readline_mod, complete_cb):
  home_dir = os.environ.get('HOME')
  if home_dir is None:
    home_dir = util.GetHomeDir()
    if home_dir is None:
      print("Couldn't find home dir in $HOME or /etc/passwd", file=sys.stderr)
      return
  history_filename = os.path.join(home_dir, 'oil_history')

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

  # NOTE: This apparently matters for -a -n completion -- why?  Is space the
  # right value?
  # http://web.mit.edu/gnu/doc/html/rlman_2.html#SEC39
  # "The basic list of characters that signal a break between words for the
  # completer routine. The default value of this variable is the characters
  # which break words for completion in Bash, i.e., " \t\n\"\\'`@$><=;|&{(""
  #
  # Hm I don't get this.
  readline_mod.set_completer_delims(' ')


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
