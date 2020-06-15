#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
builtin_misc.py - Misc builtins.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import span_e, cmd_value__Argv
from asdl import runtime
from core import error
from core import passwd
from core.pyerror import e_usage
from core import pyutil  # strerror_OS
from core import state
from core.util import log
from core import ui
from core import vm
from frontend import flag_spec
from mycpp import mylib
from pylib import os_path

import libc
import posix_ as posix

from typing import Tuple, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import span_t
  from core.pyutil import _ResourceLoader
  from core.state import Mem, DirStack
  from core.ui import ErrorFormatter
  from osh.cmd_eval import CommandEvaluator
  from osh.split import SplitContext

_ = log

#
# Implementation of builtins.
#


class Times(vm._Builtin):
  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    passwd.PrintTimes()
    return 0


# The Read builtin splits using IFS.
#
# Summary:
# - Split with IFS, except \ can escape them!  This is different than the
#   algorithm for splitting words (at least the way I've represented it.)

# Bash manual:
# - If there are more words than names, the remaining words and their
#   intervening delimiters are assigned to the last name.
# - If there are fewer words read from the input stream than names, the
#   remaining names are assigned empty values.
# - The characters in the value of the IFS variable are used to split the line
#   into words using the same rules the shell uses for expansion (described
# above in Word Splitting).
# - The backslash character '\' may be used to remove any special meaning for
#   the next character read and for line continuation.

def _AppendParts(s, spans, max_results, join_next, parts):
  # type: (str, List[Tuple[span_t, int]], int, bool, List[mylib.BufWriter]) -> Tuple[bool, bool]
  """ Append to 'parts', for the 'read' builtin.
  
  Similar to _SpansToParts in osh/split.py

  Args:
    s: The original string
    spans: List of (span, end_index)
    max_results: the maximum number of parts we want
    join_next: Whether to join the next span to the previous part.  This
    happens in two cases:
      - when we have '\ '
      - and when we have more spans # than max_results.
  """
  start_index = 0
  # If the last span was black, and we get a backslash, set join_next to merge
  # two black spans.
  last_span_was_black = False

  for span_type, end_index in spans:
    if span_type == span_e.Black:
      if join_next and parts:
        parts[-1].write(s[start_index:end_index])
        join_next = False
      else:
        buf = mylib.BufWriter()
        buf.write(s[start_index:end_index])
        parts.append(buf)
      last_span_was_black = True

    elif span_type == span_e.Delim:
      if join_next:
        parts[-1].write(s[start_index:end_index])
        join_next = False
      last_span_was_black = False

    elif span_type == span_e.Backslash:
      if last_span_was_black:
        join_next = True
      last_span_was_black = False

    if max_results and len(parts) >= max_results:
      join_next = True

    start_index = end_index

  done = True
  if len(spans):
    #log('%s %s', s, spans)
    #log('%s', spans[-1])
    last_span_type, _ = spans[-1]
    if last_span_type == span_e.Backslash:
      done = False

  #log('PARTS %s', parts)
  return done, join_next


# sys.stdin.readline() in Python has buffering!  TODO: Rewrite this tight loop
# in C?  Less garbage probably.
# NOTE that dash, mksh, and zsh all read a single byte at a time.  It appears
# to be required by POSIX?  Could try libc getline and make this an option.

def ReadLineFromStdin(delim_char):
  # type: (Optional[str]) -> Tuple[str, bool]
  """Read a portion of stdin.
  
  If delim_char is set, read until that delimiter, but don't include it.
  If not set, read a line, and include the newline.
  """
  eof = False
  chars = []  # type: List[str]
  while True:
    c = posix.read(0, 1)
    if len(c) == 0:
      eof = True
      break

    if c == delim_char:
      break

    chars.append(c)

  return ''.join(chars), eof


class Read(vm._Builtin):
  def __init__(self, splitter, mem):
    # type: (SplitContext, Mem) -> None
    self.splitter = splitter
    self.mem = mem
    self.stdin = mylib.Stdin()

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('read', cmd_val)
    arg = arg_types.read(attrs.attrs)
    names = arg_r.Rest()

    if arg.n >= 0 :  # read a certain number of bytes (-1 means unset)
      if len(names):
        name = names[0]
      else:
        name = 'REPLY'  # default variable name

      status = 0
      stdin_fd = self.stdin.fileno()
      if self.stdin.isatty():  # set stdin to read in unbuffered mode
        s = passwd.ReadBytesFromTerminal(stdin_fd, arg.n)
      else:
        chunks = []  # type: List[str]
        n = arg.n
        while n > 0:
          chunk = posix.read(stdin_fd, n)  # read at up to N chars
          if len(chunk) == 0:
            break
          chunks.append(chunk)
          n -= len(chunk)
        s = ''.join(chunks)

      # DIdn't read all the bytes we wanted
      if len(s) != n:
        status = 1

      state.SetStringDynamic(self.mem, name, s)
      # NOTE: Even if we don't get n bytes back, there is no error?
      return status

    if len(names) == 0:
      names.append('REPLY')

    # leftover words assigned to the last name
    if arg.a is not None:
      max_results = 0  # no max
    else:
      max_results = len(names)

    if arg.d is not None:
      if len(arg.d):
        delim_char = arg.d[0]
      else:
        delim_char = '\0'  # -d '' delimits by NUL
    else:
      delim_char = '\n'  # read a line

    # We have to read more than one line if there is a line continuation (and
    # it's not -r).
    parts = []  # type: List[mylib.BufWriter]
    join_next = False
    status = 0
    while True:
      line, eof = ReadLineFromStdin(delim_char)

      if eof:
        # status 1 to terminate loop.  (This is true even though we set
        # variables).
        status = 1

      #log('LINE %r', line)
      if len(line) == 0:
        break

      spans = self.splitter.SplitForRead(line, not arg.r)
      done, join_next = _AppendParts(line, spans, max_results, join_next, parts)

      #log('PARTS %s continued %s', parts, continued)
      if done:
        break

    entries = [buf.getvalue() for buf in parts]
    num_parts = len(entries)
    if arg.a is not None:
      state.SetArrayDynamic(self.mem, arg.a, entries)
    else:
      for i in xrange(max_results):
        if i < num_parts:
          s = entries[i]
        else:
          s = ''  # if there are too many variables
        #log('read: %s = %s', names[i], s)
        state.SetStringDynamic(self.mem, names[i], s)

    return status


class MapFile(vm._Builtin):
  """ mapfile / readarray """

  def __init__(self, mem, errfmt):
    # type: (Mem, ErrorFormatter) -> None
    self.mem = mem
    self.errfmt = errfmt
    self.f = mylib.Stdin()

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('mapfile', cmd_val)
    # TODO: Implement flags to mapfile
    #arg = arg_types.mapfile(attrs.attrs)

    var_name, _ = arg_r.Peek2()
    if var_name is None:
      var_name = 'MAPFILE'

    lines = []  # type: List[str]
    while True:
      line = self.f.readline()
      if len(line) == 0:
        break
      lines.append(line)

    state.SetArrayDynamic(self.mem, var_name, lines)
    return 0


class Cd(vm._Builtin):
  def __init__(self, mem, dir_stack, cmd_ev, errfmt):
    # type: (Mem, DirStack, CommandEvaluator, ErrorFormatter) -> None
    self.mem = mem
    self.dir_stack = dir_stack
    self.cmd_ev = cmd_ev  # To run blocks
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('cd', cmd_val)
    arg = arg_types.cd(attrs.attrs)

    dest_dir, arg_spid = arg_r.Peek2()
    if dest_dir is None:
      val = self.mem.GetVar('HOME')
      try:
        dest_dir = state.GetString(self.mem, 'HOME')
      except error.Runtime as e:
        self.errfmt.Print_(e.UserErrorString())
        return 1

    if dest_dir == '-':
      try:
        dest_dir = state.GetString(self.mem, 'OLDPWD')
        print(dest_dir)  # Shells print the directory
      except error.Runtime as e:
        self.errfmt.Print_(e.UserErrorString())
        return 1

    try:
      pwd = state.GetString(self.mem, 'PWD')
    except error.Runtime as e:
      self.errfmt.Print_(e.UserErrorString())
      return 1

    # Calculate new directory, chdir() to it, then set PWD to it.  NOTE: We can't
    # call posix.getcwd() because it can raise OSError if the directory was
    # removed (ENOENT.)
    abspath = os_path.join(pwd, dest_dir)  # make it absolute, for cd ..
    if arg.P:
      # -P means resolve symbolic links, then process '..'
      real_dest_dir = libc.realpath(abspath)
    else:
      # -L means process '..' first.  This just does string manipulation.  (But
      # realpath afterward isn't correct?)
      real_dest_dir = os_path.normpath(abspath)

    try:
      posix.chdir(real_dest_dir)
    except OSError as e:
      self.errfmt.Print_("cd %r: %s" % (real_dest_dir, pyutil.strerror_OS(e)),
                         span_id=arg_spid)
      return 1

    state.ExportGlobalString(self.mem, 'PWD', real_dest_dir)

    # WEIRD: We need a copy that is NOT PWD, because the user could mutate PWD.
    # Other shells use global variables.
    self.mem.SetPwd(real_dest_dir)

    if cmd_val.block:
      self.dir_stack.Push(real_dest_dir)
      try:
        unused = self.cmd_ev.EvalBlock(cmd_val.block)
      finally:  # TODO: Change this to a context manager.
        # note: it might be more consistent to use an exception here.
        if not _PopDirStack(self.mem, self.dir_stack, self.errfmt):
          return 1

    else:  # No block
      state.ExportGlobalString(self.mem, 'OLDPWD', pwd)
      self.dir_stack.Reset()  # for pushd/popd/dirs

    return 0


WITH_LINE_NUMBERS = 1
WITHOUT_LINE_NUMBERS = 2
SINGLE_LINE = 3

def _PrintDirStack(dir_stack, style, home_dir):
  # type: (DirStack, int, Optional[str]) -> None
  """Helper for 'dirs'."""

  if style == WITH_LINE_NUMBERS:
    for i, entry in enumerate(dir_stack.Iter()):
      print('%2d  %s' % (i, ui.PrettyDir(entry, home_dir)))

  elif style == WITHOUT_LINE_NUMBERS:
    for entry in dir_stack.Iter():
      print(ui.PrettyDir(entry, home_dir))

  elif style == SINGLE_LINE:
    parts = [ui.PrettyDir(entry, home_dir) for entry in dir_stack.Iter()]
    s = ' '.join(parts)
    print(s)


class Pushd(vm._Builtin):
  def __init__(self, mem, dir_stack, errfmt):
    # type: (Mem, DirStack, ErrorFormatter) -> None
    self.mem = mem
    self.dir_stack = dir_stack
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    num_args = len(cmd_val.argv) - 1
    if num_args == 0:
      # TODO: It's suppose to try another dir before doing this?
      self.errfmt.Print_('pushd: no other directory')
      return 1
    elif num_args > 1:
      e_usage('got too many arguments')

    # TODO: 'cd' uses normpath?  Is that inconsistent?
    dest_dir = os_path.abspath(cmd_val.argv[1])
    try:
      posix.chdir(dest_dir)
    except OSError as e:
      self.errfmt.Print_("pushd: %r: %s" % (dest_dir, pyutil.strerror_OS(e)),
                         span_id=cmd_val.arg_spids[1])
      return 1

    self.dir_stack.Push(dest_dir)
    _PrintDirStack(self.dir_stack, SINGLE_LINE, state.MaybeString(self.mem, 'HOME'))
    state.ExportGlobalString(self.mem, 'PWD', dest_dir)
    self.mem.SetPwd(dest_dir)
    return 0


def _PopDirStack(mem, dir_stack, errfmt):
  # type: (Mem, DirStack, ErrorFormatter) -> bool
  """Helper for popd and cd { ... }."""
  dest_dir = dir_stack.Pop()
  if dest_dir is None:
    errfmt.Print_('popd: directory stack is empty')
    return False

  try:
    posix.chdir(dest_dir)
  except OSError as e:
    # Happens if a directory is deleted in pushing and popping
    errfmt.Print_("popd: %r: %s" % (dest_dir, pyutil.strerror_OS(e)))
    return False

  state.SetGlobalString(mem, 'PWD', dest_dir)
  mem.SetPwd(dest_dir)
  return True


class Popd(vm._Builtin):
  def __init__(self, mem, dir_stack, errfmt):
    # type: (Mem, DirStack, ErrorFormatter) -> None
    self.mem = mem
    self.dir_stack = dir_stack
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    if len(cmd_val.arg_spids) > 1:
      e_usage('got extra argument', span_id=cmd_val.arg_spids[1])

    if not _PopDirStack(self.mem, self.dir_stack, self.errfmt):
      return 1  # error

    _PrintDirStack(self.dir_stack, SINGLE_LINE, state.MaybeString(self.mem, ('HOME')))
    return 0


class Dirs(vm._Builtin):
  def __init__(self, mem, dir_stack, errfmt):
    # type: (Mem, DirStack, ErrorFormatter) -> None
    self.mem = mem
    self.dir_stack = dir_stack
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('dirs', cmd_val)
    arg = arg_types.dirs(attrs.attrs)

    home_dir = state.MaybeString(self.mem, 'HOME')
    style = SINGLE_LINE

    # Following bash order of flag priority
    if arg.l:
      home_dir = None  # disable pretty ~
    if arg.c:
      self.dir_stack.Reset()
      return 0
    elif arg.v:
      style = WITH_LINE_NUMBERS
    elif arg.p:
      style = WITHOUT_LINE_NUMBERS

    _PrintDirStack(self.dir_stack, style, home_dir)
    return 0


class Pwd(vm._Builtin):
  """
  NOTE: pwd doesn't just call getcwd(), which returns a "physical" dir (not a
  symlink).
  """
  def __init__(self, mem, errfmt):
    # type: (Mem, ErrorFormatter) -> None
    self.mem = mem
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('pwd', cmd_val)
    arg = arg_types.pwd(attrs.attrs)

    # NOTE: 'pwd' will succeed even if the directory has disappeared.  Other
    # shells behave that way too.
    pwd = self.mem.pwd

    # '-L' is the default behavior; no need to check it
    # TODO: ensure that if multiple flags are provided, the *last* one overrides
    # the others
    if arg.P:
      pwd = libc.realpath(pwd)
    print(pwd)
    return 0


# TODO: Need $VERSION inside all pages?

if mylib.PYTHON:
  # Needs a different _ResourceLoader to translate
  class Help(vm._Builtin):

    def __init__(self, loader, errfmt):
      # type: (_ResourceLoader, ErrorFormatter) -> None
      self.loader = loader
      self.errfmt = errfmt

    def _Groups(self):
      # type: () -> List[str]
      # TODO: cache this?
      f = self.loader.open('_devbuild/help/groups.txt')
      lines = f.readlines()
      f.close()
      groups = [line.rstrip() for line in lines]
      return groups

    def Run(self, cmd_val):
      # type: (cmd_value__Argv) -> int

      #attrs, arg_r = flag_spec.ParseCmdVal('help', cmd_val)
      #arg = arg_types.help(attrs.attrs)

      try:
        topic = cmd_val.argv[1]
        blame_spid = cmd_val.arg_spids[1]
      except IndexError:
        topic = 'help'
        blame_spid = runtime.NO_SPID

      # TODO: Should be -i for index?  Or -l?
      if topic == 'index':
        groups = cmd_val.argv[2:]
        if len(groups) == 0:
          # Print the whole index
          groups = self._Groups()

        for group in groups:
          try:
            f = self.loader.open('_devbuild/help/_%s' % group)
          except IOError:
            self.errfmt.Print_('Invalid help index group: %r' % group)
            return 1
          print(f.read())
          f.close()
        return 0

      try:
        f = self.loader.open('_devbuild/help/%s' % topic)
      except IOError:
        # Notes:
        # 1. bash suggests:
        # man -k zzz
        # info zzz
        # help help
        # We should do something smarter.

        # 2. This also happens on 'build/dev.sh minimal', which isn't quite
        # accurate.  We don't have an exact list of help topics!

        # 3. This is mostly an interactive command.  Is it obnoxious to
        # quote the line of code?
        self.errfmt.Print_('no help topics match %r' % topic,
                           span_id=blame_spid)
        return 1

      print(f.read())
      f.close()
      return 0


class Cat(vm._Builtin):
  """Internal implementation detail for $(< file).
  
  Maybe expose this as 'builtin cat' ?
  """
  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    while True:
      chunk = posix.read(0, 4096)
      if len(chunk) == 0:
        break
      mylib.Stdout().write(chunk)
    return 0
