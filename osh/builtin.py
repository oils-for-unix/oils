#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
builtins.py - Implementation of builtins, along with their metadata.

- used for lookup in cmd_exec.py
  - need a hash of builtin names for quick testing?
- handle completion of builtin NAMES -- pass to completion.py
  - handle aliases : . and source, [ and test
- handle flags they take
  - handle completion of builtin FLAGS
- Add the "help" builtin itself

NOTE: bash has help -d -m -s.  Default is -s, like a man page.

Links on special builtins:
http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_14

- syntax errors in special builtins may cause the shell to abort, but NOT for
  regular builtins?
"""
from __future__ import print_function

import termios # for read -n
import signal  # for calculating numbers
import sys

from _devbuild.gen import osh_help  # generated file
from _devbuild.gen.runtime_asdl import (
  value_e, scope_e, span_e, builtin_e, arg_vector
)
from asdl import pretty
from core import ui
from core import util
from core.util import log, e_die
from frontend import args
from frontend import lex
from frontend import match
from pylib import os_path
from osh import state
from osh import string_ops
from osh import word_compile

import libc
import posix_ as posix

from typing import Dict

# Special builtins can't be redefined by functions.  On the other hand, 'cd'
# CAN be redefined.
#
# http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_14
# https://www.gnu.org/software/bash/manual/html_node/Special-Builtins.html

_SPECIAL_BUILTINS = {
    ":": builtin_e.COLON,
    ".": builtin_e.DOT,
    "eval": builtin_e.EVAL,
    "exec": builtin_e.EXEC,
    "export": builtin_e.EXPORT,

    "set": builtin_e.SET,
    "shift": builtin_e.SHIFT,
    #"times": builtin_e.TIMES,  # no implemented
    "trap": builtin_e.TRAP,
    "unset": builtin_e.UNSET,

    # May be a builtin or an assignment
    #"readonly": builtin_e.READONLY,
    #"local": builtin_e.LOCAL,
    "declare": builtin_e.DECLARE,
    "typeset": builtin_e.TYPESET,
    "builtin": builtin_e.BUILTIN,

    # Not treated as builtins by OSH.  TODO: Need to auto-complete these
    # break continue return
}

_NORMAL_BUILTINS = {
    "read": builtin_e.READ,
    "echo": builtin_e.ECHO,
    "printf": builtin_e.PRINTF,

    "cd": builtin_e.CD,
    "pushd": builtin_e.PUSHD,
    "popd": builtin_e.POPD,
    "dirs": builtin_e.DIRS,
    "pwd": builtin_e.PWD,

    "source": builtin_e.SOURCE,  # note that . alias is special

    "umask": builtin_e.UMASK,
    "wait": builtin_e.WAIT,
    "jobs": builtin_e.JOBS,
    "fg": builtin_e.FG,
    "bg": builtin_e.BG,

    "shopt": builtin_e.SHOPT,
    "complete": builtin_e.COMPLETE,
    "compgen": builtin_e.COMPGEN,
    "compopt": builtin_e.COMPOPT,
    "compadjust": builtin_e.COMPADJUST,

    "true": builtin_e.TRUE,
    "false": builtin_e.FALSE,

    "test": builtin_e.TEST,
    "[": builtin_e.BRACKET,

    "getopts": builtin_e.GETOPTS,

    "command": builtin_e.COMMAND,
    "type": builtin_e.TYPE,
    "hash": builtin_e.HASH,
    "help": builtin_e.HELP,
    "history": builtin_e.HISTORY,

    "declare": builtin_e.DECLARE,
    "typeset": builtin_e.TYPESET,

    "alias": builtin_e.ALIAS,
    "unalias": builtin_e.UNALIAS,

    # OSH only
    "repr": builtin_e.REPR,
}

# This is used by completion.
BUILTIN_NAMES = _SPECIAL_BUILTINS.keys() + _NORMAL_BUILTINS.keys()


class BuiltinDef(object):
  """
  NOTE: This isn't used anywhere!  We're registering nothing.

  We want to complete the flags to builtins.  So this is a mapping from name
  to arg spec.  There might not be any flags.
  """
  def __init__(self):
    # Is this what we want?
    names = set()
    names.update(_NORMAL_BUILTINS.keys())
    names.update(_SPECIAL_BUILTINS.keys())
    # TODO: Also complete keywords first for, while, etc.  Bash/zsh/fish/yash
    # all do this.  See osh/lex/{_KEYWORDS, _MORE_KEYWORDS}.

    self.arg_specs = {}
    self.to_complete = sorted(names)

  def Register(self, name, help_topic=None):
    # The help topics are in the quick ref.  TODO: We should match them up?
    #help_topic = help_topic or name
    arg_spec = args.BuiltinFlags()
    self.arg_specs[name] = arg_spec
    return arg_spec


# Global instance for "metaprogramming" before main().
BUILTIN_DEF = BuiltinDef()


def _Register(name, help_topic=None):
  return BUILTIN_DEF.Register(name, help_topic=help_topic)


def ResolveSpecial(argv0):
  return _SPECIAL_BUILTINS.get(argv0, builtin_e.NONE)


def Resolve(argv0):
  return _NORMAL_BUILTINS.get(argv0, builtin_e.NONE)


#
# Implementation of builtins.
#

ECHO_SPEC = _Register('echo')
ECHO_SPEC.ShortFlag('-e')  # no backslash escapes
ECHO_SPEC.ShortFlag('-n')


def Echo(arg_vec):
  """echo builtin.

  set -o sane-echo could do the following:
  - only one arg, no implicit joining.
  - no -e: should be echo c'one\ttwo\t'
  - no -n: should be write 'one'

  multiple args on a line:
  echo-lines one two three
  """
  # NOTE: both getopt and optparse are unsuitable for 'echo' because:
  # - 'echo -c' should print '-c', not fail
  # - echo '---' should print ---, not fail

  argv = arg_vec.strs[1:]
  arg, arg_index = ECHO_SPEC.ParseLikeEcho(argv)
  argv = argv[arg_index:]
  if arg.e:
    new_argv = []
    for a in argv:
      parts = []
      for id_, value in match.ECHO_LEXER.Tokens(a):
        p = word_compile.EvalCStringToken(id_, value)

        # Unusual behavior: '\c' prints what is there and aborts processing!
        if p is None:
          new_argv.append(''.join(parts))
          for i, a in enumerate(new_argv):
            if i != 0:
              sys.stdout.write(' ')  # arg separator
            sys.stdout.write(a)
          return 0  # EARLY RETURN

        parts.append(p)
      new_argv.append(''.join(parts))

    # Replace it
    argv = new_argv

  #log('echo argv %s', argv)
  for i, a in enumerate(argv):
    if i != 0:
      sys.stdout.write(' ')  # arg separator
    sys.stdout.write(a)
  if not arg.n:
    sys.stdout.write('\n')

  return 0


WAIT_SPEC = _Register('wait')
WAIT_SPEC.ShortFlag('-n')


class Wait(object):
  """
  wait: wait [-n] [id ...]
      Wait for job completion and return exit status.

      Waits for each process identified by an ID, which may be a process ID or a
      job specification, and reports its termination status.  If ID is not
      given, waits for all currently active child processes, and the return
      status is zero.  If ID is a a job specification, waits for all processes
      in that job's pipeline.

      If the -n option is supplied, waits for the next job to terminate and
      returns its exit status.

      Exit Status:
      Returns the status of the last ID; fails if ID is invalid or an invalid
      option is given.
  """
  def __init__(self, waiter, job_state, mem, errfmt):
    self.waiter = waiter
    self.job_state = job_state
    self.mem = mem
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    arg, arg_index = WAIT_SPEC.ParseVec(arg_vec)
    job_ids = arg_vec.strs[arg_index:]
    arg_count = len(arg_vec.strs)

    if arg.n:
      # wait -n returns the exit status of the JOB.
      # You don't know WHICH process, which is odd.

      # TODO: this should wait for the next JOB, which may be multiple
      # processes.
      # Bash has a wait_for_any_job() function, which loops until the jobs
      # table changes.
      #
      # target_count = self.job_state.NumRunning() - 1
      # while True:
      #   if not self.waiter.WaitForOne():
      #     break
      #
      #   if self.job_state.NumRunning == target_count:
      #     break
      #    
      #log('wait next')

      if self.waiter.WaitForOne():
        return self.waiter.last_status
      else:
        return 127  # nothing to wait for

    if arg_index == arg_count:  # no arguments
      #log('wait all')

      i = 0
      while True:
        # BUG: If there is a STOPPED process, this will hang forever, because
        # we don't get ECHILD.
        # Not sure it matters since you can now Ctrl-C it.

        if not self.waiter.WaitForOne():
          break  # nothing to wait for
        i += 1
        if self.job_state.NoneAreRunning():
          break

      log('Waited for %d processes', i)
      return 0

    # Get list of jobs.  Then we need to check if they are ALL stopped.
    # Returns the exit code of the last one on the COMMAND LINE, not the exit
    # code of last one to FINISH.
    status = 1  # error
    for i in xrange(arg_index, arg_count):
      job_id = arg_vec.strs[i]
      span_id = arg_vec.spids[i]

      # The % syntax is sort of like ! history sub syntax, with various queries.
      # https://stackoverflow.com/questions/35026395/bash-what-is-a-jobspec
      if job_id.startswith('%'):
        raise args.UsageError(
            "doesn't support bash-style jobspecs (got %r)" % job_id,
            span_id=span_id)

      # Does it look like a PID?
      try:
        pid = int(job_id)
      except ValueError:
        raise args.UsageError('expected PID or jobspec, got %r' % job_id,
                              span_id=span_id)

      job = self.job_state.JobFromPid(pid)
      if job is None:
        self.errfmt.Print("%s isn't a child of this shell", pid,
                          span_id=span_id)
        return 127

      # TODO: Wait for pipelines, and handle PIPESTATUS from Pipeline.Wait().
      status = job.Wait(self.waiter)

    return status


class Jobs(object):
  """List jobs."""
  def __init__(self, job_state):
    self.job_state = job_state

  def __call__(self, arg_vec):
    # NOTE: the + and - in the jobs list mean 'current' and 'previous', and are
    # addressed with %+ and %-.

    # [6]   Running                 sleep 5 | sleep 5 &
    # [7]-  Running                 sleep 5 | sleep 5 &
    # [8]+  Running                 sleep 5 | sleep 5 &

    self.job_state.List()
    return 0


class Fg(object):
  """Put a job in the foreground"""
  def __init__(self, job_state, waiter):
    self.job_state = job_state
    self.waiter = waiter

  def __call__(self, arg_vec):
    # Get job instead of PID, and then do
    #
    # Should we also have job.SendContinueSignal() ?
    # - posix.killpg()
    #
    # job.WaitUntilDone(self.waiter)
    # - waitpid() under the hood

    pid = self.job_state.GetLastStopped()
    if pid is None:
      log('No job to put in the foreground')
      return 1

    # TODO: Print job ID rather than the PID
    log('Continue PID %d', pid)
    posix.kill(pid, signal.SIGCONT)

    job = self.job_state.JobFromPid(pid)
    status = job.Wait(self.waiter)
    #log('status = %d', status)
    return status


class Bg(object):
  """Put a job in the background"""
  def __init__(self, job_state):
    self.job_state = job_state

  def __call__(self, arg_vec):
    # How does this differ from 'fg'?  It doesn't wait and it sets controlling
    # terminal?

    raise args.UsageError("isn't implemented")


# Summary:
# - Split with IFS, except \ can escape them!  This is different than the
# algorithm for splitting words (at least the way I've represented it.)
# - And

# Bash manual:
# - If there are more words than names, the remaining words and their
# intervening delimiters are assigned to the last name.
# - If there are fewer words read from the input stream than names, the
# remaining names are assigned empty values.
# - The characters in the value of the IFS variable are used to split the line
# into words using the same rules the shell uses for expansion (described
# above in Word Splitting).
# - The backslash character '\' may be used to remove any special meaning for
# the next character read and for line continuation.
#
# Hm but word splitting isn't affected by \<space>
#
# I think I have to make two passes.
#
# 1. Process backslashes (or don't if it's -r)
# 2. Split.

def _AppendParts(s, spans, max_results, join_next, parts):
  """
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
        parts[-1] += s[start_index:end_index]
        join_next = False
      else:
        parts.append(s[start_index:end_index])
      last_span_was_black = True

    elif span_type == span_e.Delim:
      if join_next:
        parts[-1] += s[start_index:end_index]
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
  if spans:
    #log('%s %s', s, spans)
    #log('%s', spans[-1])
    last_span_type, _ = spans[-1]
    if last_span_type == span_e.Backslash:
      done = False

  #log('PARTS %s', parts)
  return done, join_next


READ_SPEC = _Register('read')
READ_SPEC.ShortFlag('-r')
READ_SPEC.ShortFlag('-n', args.Int)
READ_SPEC.ShortFlag('-a', args.Str)  # name of array to read into


# sys.stdin.readline() in Python has buffering!  TODO: Rewrite this tight loop
# in C?  Less garbage probably.
# NOTE that dash, mksh, and zsh all read a single byte at a time.  It appears
# to be required by POSIX?  Could try libc getline and make this an option.
def ReadLineFromStdin():
  chars = []
  while True:
    c = posix.read(0, 1)
    if not c:
      break
    chars.append(c)

    if c == '\n':
      break
  return ''.join(chars)


class Read(object):
  def __init__(self, splitter, mem):
    self.splitter = splitter
    self.mem = mem

  def __call__(self, arg_vec):
    arg, i = READ_SPEC.ParseVec(arg_vec)

    names = arg_vec.strs[i:]
    if arg.n is not None:  # read a certain number of bytes
      stdin = sys.stdin.fileno()
      try:
        name = names[0]
      except IndexError:
        name = 'REPLY'  # default variable name
      s = ""
      if sys.stdin.isatty():  # set stdin to read in unbuffered mode
        orig_attrs = termios.tcgetattr(stdin)
        attrs = termios.tcgetattr(stdin)
        # disable canonical (buffered) mode
        # see `man termios` for an extended discussion
        attrs[3] &= ~termios.ICANON
        try:
          termios.tcsetattr(stdin, termios.TCSANOW, attrs)
          # posix.read always returns a single character in unbuffered mode
          while arg.n > 0:
            s += posix.read(stdin, 1)
            arg.n -= 1
        finally:
          termios.tcsetattr(stdin, termios.TCSANOW, orig_attrs)
      else:
        s_len = 0
        while arg.n > 0:
          buf = posix.read(stdin, arg.n)
          # EOF
          if buf == '':
            break
          arg.n -= len(buf)
          s += buf

      state.SetLocalString(self.mem, name, s)
      # NOTE: Even if we don't get n bytes back, there is no error?
      return 0

    if not names:
      names.append('REPLY')

    # leftover words assigned to the last name
    if arg.a:
      max_results = 0  # no max
    else:
      max_results = len(names)

    # We have to read more than one line if there is a line continuation (and
    # it's not -r).

    parts = []
    join_next = False
    while True:
      line = ReadLineFromStdin()
      #log('LINE %r', line)
      if not line:  # EOF
        status = 1
        break

      if line.endswith('\n'):  # strip trailing newline
        line = line[:-1]
        status = 0
      else:
        # odd bash behavior: fail even if we can set variables.
        status = 1

      spans = self.splitter.SplitForRead(line, not arg.r)
      done, join_next = _AppendParts(line, spans, max_results, join_next, parts)

      #log('PARTS %s continued %s', parts, continued)
      if done:
        break

    if arg.a:
      state.SetArrayDynamic(self.mem, arg.a, parts)
    else:
      for i in xrange(max_results):
        try:
          s = parts[i]
        except IndexError:
          s = ''  # if there are too many variables
        #log('read: %s = %s', names[i], s)
        state.SetStringDynamic(self.mem, names[i], s)

    return status


CD_SPEC = _Register('cd')
CD_SPEC.ShortFlag('-L')
CD_SPEC.ShortFlag('-P')

class Cd(object):
  def __init__(self, mem, dir_stack, errfmt):
    self.mem = mem
    self.dir_stack = dir_stack
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    arg, i = CD_SPEC.ParseVec(arg_vec)
    # TODO: error checking, etc.
    # TODO: ensure that if multiple flags are provided, the *last* one overrides
    # the others.

    try:
      dest_dir = arg_vec.strs[i]
    except IndexError:
      val = self.mem.GetVar('HOME')
      if val.tag == value_e.Undef:
        self.errfmt.Print("$HOME isn't defined")
        return 1
      elif val.tag == value_e.Str:
        dest_dir = val.s
      elif val.tag == value_e.StrArray:
        # User would have to unset $HOME to get rid of exported flag
        self.errfmt.Print("$HOME shouldn't be an array")
        return 1

    if dest_dir == '-':
      old = self.mem.GetVar('OLDPWD', scope_e.GlobalOnly)
      if old.tag == value_e.Undef:
        self.errfmt.Print('OLDPWD not set')
        return 1
      elif old.tag == value_e.Str:
        dest_dir = old.s
        print(dest_dir)  # Shells print the directory
      elif old.tag == value_e.StrArray:
        # TODO: Prevent the user from setting OLDPWD to array (or maybe they
        # can't even set it at all.)
        raise AssertionError('Invalid OLDPWD')

    pwd = self.mem.GetVar('PWD')
    assert pwd.tag == value_e.Str, pwd  # TODO: Need a general scheme to avoid

    # Calculate new directory, chdir() to it, then set PWD to it.  NOTE: We can't
    # call posix.getcwd() because it can raise OSError if the directory was
    # removed (ENOENT.)
    abspath = os_path.join(pwd.s, dest_dir)  # make it absolute, for cd ..
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
      self.errfmt.Print("cd %r: %s", real_dest_dir, posix.strerror(e.errno),
                        span_id=arg_vec.spids[i])
      return 1

    state.ExportGlobalString(self.mem, 'OLDPWD', pwd.s)
    state.ExportGlobalString(self.mem, 'PWD', real_dest_dir)
    self.dir_stack.Reset()  # for pushd/popd/dirs
    return 0


WITH_LINE_NUMBERS = 1
WITHOUT_LINE_NUMBERS = 2
SINGLE_LINE = 3

def _PrintDirStack(dir_stack, style, home_dir):
  """Helper for 'dirs'."""

  if style == WITH_LINE_NUMBERS:
    for i, entry in enumerate(dir_stack.Iter()):
      print('%2d  %s' % (i, ui.PrettyDir(entry, home_dir)))

  elif style == WITHOUT_LINE_NUMBERS:
    for entry in dir_stack.Iter():
      print(ui.PrettyDir(entry, home_dir))

  elif style == SINGLE_LINE:
    s = ' '.join(ui.PrettyDir(entry, home_dir) for entry in dir_stack.Iter())
    print(s)


class Pushd(object):
  def __init__(self, mem, dir_stack, errfmt):
    self.mem = mem
    self.dir_stack = dir_stack
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    num_args = len(arg_vec.strs) - 1
    if num_args == 0:
      # TODO: It's suppose to try another dir before doing this?
      self.errfmt.Print('pushd: no other directory')
      return 1
    elif num_args > 1:
      raise args.UsageError('got too many arguments')

    dest_dir = os_path.abspath(arg_vec.strs[1])
    try:
      posix.chdir(dest_dir)
    except OSError as e:
      self.errfmt.Print("pushd: %r: %s", dest_dir, posix.strerror(e.errno),
                        span_id=arg_vec.spids[1])
      return 1

    self.dir_stack.Push(dest_dir)
    _PrintDirStack(self.dir_stack, SINGLE_LINE, self.mem.GetVar('HOME'))
    state.SetGlobalString(self.mem, 'PWD', dest_dir)
    return 0


class Popd(object):
  def __init__(self, mem, dir_stack, errfmt):
    self.mem = mem
    self.dir_stack = dir_stack
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    dest_dir = self.dir_stack.Pop()
    if dest_dir is None:
      self.errfmt.Print('popd: directory stack is empty')
      return 1

    try:
      posix.chdir(dest_dir)
    except OSError as e:
      # Happens if a directory is deleted in pushing and popping
      self.errfmt.Print("popd: %r: %s", dest_dir, posix.strerror(e.errno))
      return 1

    _PrintDirStack(self.dir_stack, SINGLE_LINE, self.mem.GetVar('HOME'))
    state.SetGlobalString(self.mem, 'PWD', dest_dir)
    return 0


DIRS_SPEC = _Register('dirs')
DIRS_SPEC.ShortFlag('-c')
DIRS_SPEC.ShortFlag('-l')
DIRS_SPEC.ShortFlag('-p')
DIRS_SPEC.ShortFlag('-v')


class Dirs(object):
  def __init__(self, mem, dir_stack, errfmt):
    self.mem = mem
    self.dir_stack = dir_stack
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    home_dir = self.mem.GetVar('HOME')

    arg, i = DIRS_SPEC.ParseVec(arg_vec)
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


PWD_SPEC = _Register('pwd')
PWD_SPEC.ShortFlag('-L')
PWD_SPEC.ShortFlag('-P')


class Pwd(object):
  def __init__(self, errfmt):
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    arg, _ = PWD_SPEC.ParseVec(arg_vec)

    try:
      # This comes FIRST, even if you change $PWD.
      pwd = posix.getcwd()
    except OSError as e:
      # Happens when the directory is unlinked.
      self.errfmt.Print("Can't determine working directory: %s",
                        posix.strerror(e.errno))
      return 1

    # '-L' is the default behavior; no need to check it
    # TODO: ensure that if multiple flags are provided, the *last* one overrides
    # the others
    if arg.P:
      pwd = libc.realpath(pwd)
    print(pwd)
    return 0


def AddOptionsToArgSpec(spec):
  """Shared between 'set' builtin and the shell's own arg parser."""
  for short_flag, opt_name in state.SET_OPTIONS:
    spec.Option(short_flag, opt_name)


SET_SPEC = args.FlagsAndOptions()
AddOptionsToArgSpec(SET_SPEC)


def SetExecOpts(exec_opts, opt_changes):
  """Used by bin/oil.py too."""
  for opt_name, b in opt_changes:
    exec_opts.SetOption(opt_name, b)


class Set(object):
  def __init__(self, exec_opts, mem):
    self.exec_opts = exec_opts
    self.mem = mem

  def __call__(self, arg_vec):
    # TODO:
    # - How to integrate this with auto-completion?  Have to handle '+'.

    if len(arg_vec.strs) == 1:
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
        code_str = '%s=%s' % (name, string_ops.ShellQuoteOneLine(str_val))
        print(code_str)
      return 0

    arg_r = args.Reader(arg_vec.strs, spids=arg_vec.spids)
    arg_r.Next()  # skip 'set'
    arg = SET_SPEC.Parse(arg_r)

    # 'set -o' shows options.  This is actually used by autoconf-generated
    # scripts!
    if arg.show_options:
      self.exec_opts.ShowOptions([])
      return 0

    SetExecOpts(self.exec_opts, arg.opt_changes)
    # Hm do we need saw_double_dash?
    if arg.saw_double_dash or not arg_r.AtEnd():
      self.mem.SetArgv(arg_r.Rest())
    return 0

  # TODO:
  # - STRICT: should be a combination of errexit,nounset,pipefail, plus
  #   strict-*, plus IFS?  Caps because it's a composite.
  # - SANE: disallow constructs like $* ?  That can be done with an explicit
  #   join, like s="$@" or something?
  #   or s="$@"  # osh: join
  #
  # This should be done at the module level.
  #
  # Maybe:
  # option -o foo
  # option +o foo
  # But it can only be in a module with all functions?  I don't want the state
  # to persist.
  # It's a flag on functions?  Were they defined in a FILE with -o?
  #
  # source
  # This way they're not global variables.
  # or what about shopt?
  #
  # Ways of setting options:
  #   set -o +o
  #   shopt -o +o
  #   shopt -s / shopt -u
  #
  # shopt is also a runtime thing, not a delaration.
  #
  # PROBLEM:
  # shopt -s noglob
  # set -o pipefail
  # source 'lib.sh'  # behavior is changed.  Although not if you put everything
  # in functions!  In that case, it's really the settings in main() that matter
  # (as long as nobody later turns things off.)


SHOPT_SPEC = _Register('shopt')
SHOPT_SPEC.ShortFlag('-s')  # set
SHOPT_SPEC.ShortFlag('-u')  # unset
SHOPT_SPEC.ShortFlag('-o')  # use 'set -o' up names
SHOPT_SPEC.ShortFlag('-p')  # print
SHOPT_SPEC.ShortFlag('-q')  # query option settings


class Shopt(object):
  def __init__(self, exec_opts):
    self.exec_opts = exec_opts

  def __call__(self, arg_vec):
    arg, i = SHOPT_SPEC.ParseVec(arg_vec)
    opt_names = arg_vec.strs[i:]

    if arg.p:  # print values
      if arg.o:  # use set -o names
        self.exec_opts.ShowOptions(opt_names)
      else:
        self.exec_opts.ShowShoptOptions(opt_names)
      return 0

    if arg.q:  # query values
      for name in opt_names:
        if not hasattr(self.exec_opts, name):
          return 2  # bash gives 1 for invalid option; 2 is better
        if not getattr(self.exec_opts, name):
          return 1  # at least one option is not true
      return 0  # all options are true

    b = None
    if arg.s:
      b = True
    elif arg.u:
      b = False

    if b is None:  # Print options
      # bash prints uses a different format for 'shopt', but we use the
      # same format as 'shopt -p'.
      self.exec_opts.ShowShoptOptions(opt_names)
      return 0

    # Otherwise, set options.
    for name in opt_names:
      if arg.o:
        self.exec_opts.SetOption(name, b)
      else:
        self.exec_opts.SetShoptOption(name, b)

    return 0


def _ResolveNames(names, funcs, aliases, search_path):
  results = []
  for name in names:
    if name in funcs:
      kind = ('function', name)
    elif name in aliases:
      kind = ('alias', name)
    elif Resolve(name) != builtin_e.NONE:
      kind = ('builtin', name)
    elif ResolveSpecial(name) != builtin_e.NONE:
      kind = ('builtin', name)
    elif lex.IsOtherBuiltin(name):  # declare, continue, etc.
      kind = ('builtin', name)
    elif lex.IsKeyword(name):
      kind = ('keyword', name)
    else:
      resolved = search_path.Lookup(name)
      if resolved is None:
        kind = (None, None)
      else:
        kind = ('file', resolved) 
    results.append(kind)

  return results


COMMAND_SPEC = _Register('command')
COMMAND_SPEC.ShortFlag('-v')
#COMMAND_SPEC.ShortFlag('-V')  # Another verbose mode.


class Command(object):
  def __init__(self, ex, funcs, aliases, search_path):
    self.ex = ex
    self.funcs = funcs
    self.aliases = aliases
    self.search_path = search_path

  def __call__(self, arg_vec, fork_external):
    arg, arg_index = COMMAND_SPEC.ParseVec(arg_vec)
    if arg.v:
      status = 0
      names = arg_vec.strs[arg_index:]
      for kind, arg in _ResolveNames(names, self.funcs, self.aliases,
                                     self.search_path):
        if kind is None:
          status = 1  # nothing printed, but we fail
        else:
          # This is for -v, -V is more detailed.
          print(arg)
      return status

    arg_vec2 = arg_vector(arg_vec.strs[1:], arg_vec.spids[1:])  # shift by one
    # 'command ls' suppresses function lookup.
    return self.ex.RunSimpleCommand(arg_vec2, fork_external, funcs=False)


TYPE_SPEC = _Register('type')
TYPE_SPEC.ShortFlag('-f')
TYPE_SPEC.ShortFlag('-t')
TYPE_SPEC.ShortFlag('-p')
TYPE_SPEC.ShortFlag('-P')


class Type(object):
  def __init__(self, funcs, aliases, search_path):
    self.funcs = funcs
    self.aliases = aliases
    self.search_path = search_path

  def __call__(self, arg_vec):
    arg, i = TYPE_SPEC.ParseVec(arg_vec)

    if arg.f:
      funcs = []
    else:
      funcs = self.funcs

    status = 0
    r = _ResolveNames(arg_vec.strs[i:], funcs, self.aliases, self.search_path)
    for kind, name in r:
      if kind is None:
        status = 1  # nothing printed, but we fail
      else:
        if arg.t:
          print(kind)
        elif arg.p:
          if kind == 'file':
            print(name)
        elif arg.P:
          if kind == 'file':
            print(name)
          else:
            resolved = self.search_path.Lookup(name)
            if resolved is None:
              status = 1
            else:
              print(resolved)

        else:
          # Alpine's abuild relies on this text because busybox ash doesn't have
          # -t!
          # ash prints "is a shell function" instead of "is a function", but the
          # regex accouts for that.
          print('%s is a %s' % (name, kind))
          if kind == 'function':
            # bash prints the function body, busybox ash doesn't.
            pass

    return status


HASH_SPEC = _Register('hash')
HASH_SPEC.ShortFlag('-r')


class Hash(object):
  def __init__(self, search_path):
    self.search_path = search_path

  def __call__(self, arg_vec):
    arg_r = args.Reader(arg_vec.strs, spids=arg_vec.spids)
    arg_r.Next()  # skip 'hash'
    arg, i = HASH_SPEC.Parse(arg_r)

    rest = arg_r.Rest()
    if arg.r:
      if rest:
        raise args.UsageError('got extra arguments after -r')
      self.search_path.ClearCache()
      return 0

    status = 0
    if rest:
      for cmd in rest:  # enter in cache
        full_path = self.search_path.CachedLookup(cmd)
        if full_path is None:
          ui.Stderr('hash: %r not found', cmd)
          status = 1
    else:  # print cache
      for cmd in self.search_path.CachedCommands():
        print(cmd)

    return status


ALIAS_SPEC = _Register('alias')


class Alias(object):
  def __init__(self, aliases, errfmt):
    self.aliases = aliases
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    if len(arg_vec.strs) == 1:
      for name in sorted(self.aliases):
        alias_exp = self.aliases[name]
        # This is somewhat like bash, except we use %r for ''.
        print('alias %s=%r' % (name, alias_exp))
      return 0

    status = 0
    for i in xrange(1, len(arg_vec.strs)):
      arg = arg_vec.strs[i]
      parts = arg.split('=', 1)
      if len(parts) == 1:  # if we get a plain word without, print alias
        name = parts[0]
        alias_exp = self.aliases.get(name)
        if alias_exp is None:
          self.errfmt.Print('No alias named %r', name, span_id=arg_vec.spids[i])
          status = 1
        else:
          print('alias %s=%r' % (name, alias_exp))
      else:
        name, alias_exp = parts
        self.aliases[name] = alias_exp

    #print(argv)
    #log('AFTER ALIAS %s', aliases)
    return status


UNALIAS_SPEC = _Register('unalias')


class UnAlias(object):
  def __init__(self, aliases, errfmt):
    self.aliases = aliases
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    if len(arg_vec.strs) == 1:
      raise args.UsageError('unalias NAME...')

    status = 0
    for i in xrange(1, len(arg_vec.strs)):
      name = arg_vec.strs[i]
      try:
        del self.aliases[name]
      except KeyError:
        self.errfmt.Print('No alias named %r', name, span_id=arg_vec.spids[i])
        status = 1
    return status


class _TrapHandler(object):
  """A function that is called by Python's signal module.

  Similar to process.SubProgramThunk."""

  def __init__(self, node, nodes_to_run):
    self.node = node
    self.nodes_to_run = nodes_to_run

  def __call__(self, unused_signalnum, unused_frame):
    """For Python's signal module."""
    # TODO: set -o xtrace/verbose should enable this.
    #log('*** SETTING TRAP for %d ***', unused_signalnum)
    self.nodes_to_run.append(self.node)

  def __str__(self):
    # Used by trap -p
    # TODO: Abbreviate with fmt.PrettyPrint?
    return str(self.node)


def _MakeSignals():
  """Piggy-back on CPython to get a list of portable signals.

  When Oil is ported to C, we might want to do something like bash/dash.
  """
  names = {}
  for name in dir(signal):
    # don't want SIG_DFL or SIG_IGN
    if name.startswith('SIG') and not name.startswith('SIG_'):
      int_val = getattr(signal, name)
      abbrev = name[3:]
      names[abbrev] = int_val
  return names


def _GetSignalNumber(sig_spec):
  # POSIX lists the numbers that are required.
  # http://pubs.opengroup.org/onlinepubs/9699919799/
  #
  # Added 13 for SIGPIPE because autoconf's 'configure' uses it!
  if sig_spec.strip() in ('1', '2', '3', '6', '9', '13', '14', '15'):
    return int(sig_spec)

  # INT is an alias for SIGINT
  if sig_spec.startswith('SIG'):
    sig_spec = sig_spec[3:]
  return _SIGNAL_NAMES.get(sig_spec)


_SIGNAL_NAMES = _MakeSignals()

_HOOK_NAMES = ('EXIT', 'ERR', 'RETURN', 'DEBUG')


TRAP_SPEC = _Register('trap')
TRAP_SPEC.ShortFlag('-p')
TRAP_SPEC.ShortFlag('-l')

# TODO:
#
# bash's default -p looks like this:
# trap -- '' SIGTSTP
# trap -- '' SIGTTIN
# trap -- '' SIGTTOU
#
# CPython registers different default handlers.  The C++ rewrite should make
# OVM match sh/bash more closely.

class Trap(object):
  def __init__(self, sig_state, traps, nodes_to_run, ex, errfmt):
    self.sig_state = sig_state
    self.traps = traps
    self.nodes_to_run = nodes_to_run
    self.ex = ex  # TODO: ParseTrapCode could be inlined below
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    arg, _ = TRAP_SPEC.ParseVec(arg_vec)

    if arg.p:  # Print registered handlers
      for name, value in self.traps.iteritems():
        # The unit tests rely on this being one line.
        # bash prints a line that can be re-parsed.
        print('%s %s' % (name, value.__class__.__name__))

      return 0

    if arg.l:  # List valid signals and hooks
      ordered = _SIGNAL_NAMES.items()
      ordered.sort(key=lambda x: x[1])

      for name in _HOOK_NAMES:
        print('   %s' % name)
      for name, int_val in ordered:
        print('%2d %s' % (int_val, name))

      return 0

    arg_r = args.Reader(arg_vec.strs, spids=arg_vec.spids)
    arg_r.Next()  # skip argv[0]
    code_str = arg_r.ReadRequired('requires a code string')
    sig_spec = arg_r.ReadRequired('requires a signal or hook name')

    # sig_key is NORMALIZED sig_spec: and integer signal number or string hook
    # name.
    sig_key = None
    sig_num = None
    if sig_spec in _HOOK_NAMES:
      sig_key = sig_spec
    elif sig_spec == '0':  # Special case
      sig_key = 'EXIT'
    else:
      sig_num = _GetSignalNumber(sig_spec)
      if sig_num is not None:
        sig_key = sig_num

    if sig_key is None:
      self.errfmt.Print("Invalid signal or hook %r", sig_spec,
                        span_id=arg_vec.spids[2])
      return 1

    # NOTE: sig_spec isn't validated when removing handlers.
    if code_str == '-':
      if sig_key in _HOOK_NAMES:
        try:
          del self.traps[sig_key]
        except KeyError:
          pass
        return 0

      if sig_num is not None:
        try:
          del self.traps[sig_key]
        except KeyError:
          pass

        self.sig_state.RemoveUserTrap(sig_num)
        return 0

      raise AssertionError('Signal or trap')

    # Try parsing the code first.
    node = self.ex.ParseTrapCode(code_str)
    if node is None:
      return 1  # ParseTrapCode() prints an error for us.

    # Register a hook.
    if sig_key in _HOOK_NAMES:
      if sig_key in ('ERR', 'RETURN', 'DEBUG'):
        ui.Stderr("osh warning: The %r hook isn't yet implemented ",
                  sig_spec)
      self.traps[sig_key] = _TrapHandler(node, self.nodes_to_run)
      return 0

    # Register a signal.
    sig_num = _GetSignalNumber(sig_spec)
    if sig_num is not None:
      handler = _TrapHandler(node, self.nodes_to_run)
      # For signal handlers, the traps dictionary is used only for debugging.
      self.traps[sig_key] = handler
      self.sig_state.AddUserTrap(sig_num, handler)
      return 0

    raise AssertionError('Signal or trap')

  # Example:
  # trap -- 'echo "hi  there" | wc ' SIGINT
  #
  # Then hit Ctrl-C.


def Umask(arg_vec):
  argv = arg_vec.strs[1:]
  if len(argv) == 0:
    # umask() has a dumb API: you can't get it without modifying it first!
    # NOTE: dash disables interrupts around the two umask() calls, but that
    # shouldn't be a concern for us.  Signal handlers won't call umask().
    mask = posix.umask(0)
    posix.umask(mask)  #
    print('0%03o' % mask)  # octal format
    return 0

  if len(argv) == 1:
    a = argv[0]
    try:
      new_mask = int(a, 8)
    except ValueError:
      # NOTE: This happens if we have '8' or '9' in the input too.
      ui.Stderr("osh warning: umask with symbolic input isn't implemented")
      return 1
    else:
      posix.umask(new_mask)
      return 0

  raise args.UsageError('umask: unexpected arguments')


def _ParseOptSpec(spec_str):
  # type: (str) -> Dict[str, bool]
  spec = {}
  i = 0
  n = len(spec_str)
  while True:
    if i >= n:
      break
    c = spec_str[i]
    key = '-' + c
    spec[key] = False
    i += 1
    if i >= n:
      break
    # If the next character is :, change the value to True.
    if spec_str[i] == ':':
      spec[key] = True
      i += 1
  return spec


def _GetOpts(spec, argv, optind, errfmt):
  optarg = ''  # not set by default

  try:
    current = argv[optind-1]  # 1-based indexing
  except IndexError:
    return 1, '?', optarg, optind

  if not current.startswith('-'):  # The next arg doesn't look like a flag.
    return 1, '?', optarg, optind

  # It looks like an argument.  Stop iteration by returning 1.
  if current not in spec:  # Invalid flag
    optind += 1
    return 0, '?', optarg, optind

  optind += 1
  opt_char = current[-1]

  needs_arg = spec[current]
  if needs_arg:
    try:
      optarg = argv[optind-1]  # 1-based indexing
    except IndexError:
      errfmt.Print('getopts: option %r requires an argument.', current)
      ui.Stderr('(getopts argv: %s)', ' '.join(pretty.Str(a) for a in argv))
      # Hm doesn't cause status 1?
      return 0, '?', optarg, optind

    optind += 1

  return 0, opt_char, optarg, optind


class GetOpts(object):
  """
  Vars used:
    OPTERR: disable printing of error messages
  Vars set:
    The variable named by the second arg
    OPTIND - initialized to 1 at startup
    OPTARG - argument
  """

  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt
    self.spec_cache = {}  # type: Dict[str, Dict[str, bool]]

  def __call__(self, arg_vec):
    arg_r = args.Reader(arg_vec.strs, spids=arg_vec.spids)
    arg_r.Next()

    # NOTE: If first char is a colon, error reporting is different.  Alpine
    # might not use that?
    spec_str = arg_r.ReadRequired('requires an argspec')

    var_name, var_spid = arg_r.ReadRequired2(
        'requires the name of a variable to set')

    try:
      spec = self.spec_cache[spec_str]
    except KeyError:
      spec = _ParseOptSpec(spec_str)
      self.spec_cache[spec_str] = spec

    # These errors are fatal errors, not like the builtin exiting with code 1.
    # Because the invariants of the shell have been violated!
    v = self.mem.GetVar('OPTIND')
    if v.tag != value_e.Str:
      e_die('OPTIND should be a string, got %r', v)
    try:
      optind = int(v.s)
    except ValueError:
      e_die("OPTIND doesn't look like an integer, got %r", v.s)

    user_argv = arg_r.Rest() or self.mem.GetArgv()
    #util.log('user_argv %s', user_argv)
    status, opt_char, optarg, optind = _GetOpts(spec, user_argv, optind,
                                                self.errfmt)

    # Bug fix: bash-completion uses a *local* OPTIND !  Not global.
    state.SetStringDynamic(self.mem, 'OPTARG', optarg)
    state.SetStringDynamic(self.mem, 'OPTIND', str(optind))
    if match.IsValidVarName(var_name):
      state.SetStringDynamic(self.mem, var_name, opt_char)
    else:
      # NOTE: The builtin has PARTIALLY filed.  This happens in all shells
      # except mksh.
      raise args.UsageError('got invalid variable name %r' % var_name,
                            span_id=var_spid)
    return status


class Help(object):

  def __init__(self, loader, errfmt):
    self.loader = loader
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    # TODO: Need $VERSION inside all pages?
    try:
      topic = arg_vec.strs[1]
    except IndexError:
      topic = 'help'

    if topic == 'toc':
      # Just show the raw source.
      f = self.loader.open('doc/osh-quick-ref-toc.txt')
    else:
      try:
        section_id = osh_help.TOPIC_LOOKUP[topic]
      except KeyError:
        # NOTE: bash suggests:
        # man -k zzz
        # info zzz
        # help help
        # We should do something smarter.

        # NOTE: This is mostly an interactive command.  Is it obnoxious to
        # quote the line of code?
        self.errfmt.Print('No help topics match %r', topic,
                          span_id=arg_vec.spids[1])
        return 1
      else:
        try:
          f = self.loader.open('_devbuild/osh-quick-ref/%s' % section_id)
        except IOError as e:
          util.log(str(e))
          raise AssertionError('Should have found %r' % section_id)

    for line in f:
      sys.stdout.write(line)
    f.close()
    return 0


HISTORY_SPEC = _Register('history')


class History(object):
  """Show interactive command history."""

  def __init__(self, readline_mod):
    self.readline_mod = readline_mod

  def __call__(self, arg_vec):
    # NOTE: This builtin doesn't do anything in non-interactive mode in bash?
    # It silently exits zero.
    # zsh -c 'history' produces an error.
    readline_mod = self.readline_mod
    if not readline_mod:
      raise args.UsageError("OSH wasn't compiled with the readline module.")

    arg, arg_index = HISTORY_SPEC.ParseVec(arg_vec)

    # Returns 0 items in non-interactive mode?
    num_items = readline_mod.get_current_history_length()
    #log('len = %d', num_items)

    rest = arg_vec.strs[arg_index:]
    if len(rest) == 0:
      start_index = 1
    elif len(rest) == 1:
      arg0 = rest[0]
      try:
        num_to_show = int(arg0)
      except ValueError:
        raise args.UsageError('Invalid argument %r' % arg0)
      start_index = max(1, num_items + 1 - num_to_show)
    else:
      raise args.UsageError('Too many arguments')

    # TODO:
    # - Exclude lines that don't parse from the history!  bash and zsh don't do
    # that.
    # - Consolidate multiline commands.

    for i in xrange(start_index, num_items+1):  # 1-based index
      item = readline_mod.get_history_item(i)
      print('%5d  %s' % (i, item))
    return 0


class Repr(object):
  """Given a list of variable names, print their values.

  'repr a' is a lot easier to type than 'argv.py "${a[@]}"'.
  """
  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    status = 0
    for i in xrange(1, len(arg_vec.strs)):
      name = arg_vec.strs[i]
      if not match.IsValidVarName(name):
        raise args.UsageError('got invalid variable name %r' % name,
                              span_id=arg_vec.spids[i])

      cell = self.mem.GetCell(name)
      if cell is None:
        print('%r is not defined' % name)
        status = 1
      else:
        sys.stdout.write('%s = ' % name)
        cell.PrettyPrint()  # may be color
        sys.stdout.write('\n')
    return status
