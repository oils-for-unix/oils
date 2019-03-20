#!/usr/bin/env python
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

import posix
import signal
import sys

from _devbuild.gen import osh_help  # generated file
from _devbuild.gen.runtime_asdl import (
  lvalue, value, value_e, scope_e, span_e, var_flags_e, builtin_e)
from core import ui
from core import util
from core import pyutil
from frontend import args
from frontend import lex
from frontend import match
from pylib import os_path
from pylib import path_stat
from osh import state
from osh import string_ops
from osh import word_compile

import libc

from typing import Dict

log = util.log
e_die = util.e_die

# Special builtins can't be redefined by functions.  On the other hand, 'cd'
# CAN be redefined.
#
# http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_14

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
    # Disabled for release 0.6.pre10
    #"printf": builtin_e.PRINTF,
    "cd": builtin_e.CD,
    "pushd": builtin_e.PUSHD,
    "popd": builtin_e.POPD,
    "dirs": builtin_e.DIRS,
    "pwd": builtin_e.PWD,

    "source": builtin_e.SOURCE,  # note that . alias is special

    "umask": builtin_e.UMASK,
    "wait": builtin_e.WAIT,
    "jobs": builtin_e.JOBS,

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


def Echo(argv):
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

  # I think the flush fixes a problem with command sub.  But it causes
  # IOError non-deterministically, when spec/background.test.sh is run in
  # parallel with other tests.  So just silence it.

  # File "/home/andy/git/oil/bin/../core/cmd_exec.py", line 251, in _RunBuiltin
  #   status = builtin.Echo(argv)
  # File "/home/andy/git/oil/bin/../core/builtin.py", line 431, in Echo
  #   sys.stdout.flush()
  # IOError: [Errno 32] Broken pipe
  try:
    sys.stdout.flush()
  except IOError as e:
    pass

  return 0


PRINTF_SPEC = _Register('printf')
PRINTF_SPEC.ShortFlag('-v', args.Str)


def Printf(argv, mem):
  """
  printf: printf [-v var] format [argument ...]
  """
  arg, args_consumed = PRINTF_SPEC.Parse(argv)
  if args_consumed >= len(argv):
    util.error('printf: need format string')
    return 1
  fmt = argv[args_consumed]
  vals = argv[args_consumed + 1:]

  parts = []
  f = 0
  v = 0
  # Loop invariant: vals[v:] and fmt[f:] remain, to accumulate onto `parts`.
  while True:
    f_next = fmt.find('%', f)
    if f_next < 0:
      f_next = len(fmt)

    parts.append(fmt[f:f_next])  # TODO backslash-escapes, at least \n
    f = f_next

    if f >= len(fmt):
      if v >= len(vals):
        break
      else:
        # (handy!) bash printf quirk: re-use fmt to consume remaining vals.
        f = 0
        continue

    c = fmt[f+1]
    if c == '%':
      f += 2
      parts.append('%')
      continue
    elif c == 's':
      f += 2
      parts.append(vals[v] if v < len(vals) else '')
      v += 1
      continue
    elif c == 'q':
      f += 2
      parts.append(string_ops.ShellQuote(vals[v] if v < len(vals) else ''))
      v += 1
      continue
    elif c == 'd':
      f += 2
      val = vals[v] if v < len(vals) else '0'
      v += 1
      try:
        num = int(val)
      except ValueError:
        # TODO should print message but carry on as if 0
        util.error('printf: %s: invalid number', val)
        return 1
      parts.append(str(num))
    else:
      # TODO %b, %(fmt)T, plus "the standard ones in printf(1)"
      raise NotImplementedError

  result = ''.join(parts)
  if arg.v:
    state.SetLocalString(mem, arg.v, result)
  else:
    sys.stdout.write(result)
    sys.stdout.flush()
  return 0


WAIT_SPEC = _Register('wait')
WAIT_SPEC.ShortFlag('-n')


def Wait(argv, waiter, job_state, mem):
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

  # Job spec, %1 %2, %%, %?a etc.

  http://mywiki.wooledge.org/BashGuide/JobControl#jobspec

  This is different than a PID?  But it does have a PID.
  """
  arg, i = WAIT_SPEC.Parse(argv)
  pids = argv[i:]

  if arg.n:
    # wait -n returns the exit status of the process.  But how do you know
    # WHICH process?  That doesn't seem useful.
    log('wait next')
    if waiter.Wait():
      return waiter.last_status
    else:
      return 127  # nothing to wait for

  if not pids:
    log('wait all')
    # TODO: get all background jobs from JobState?
    i = 0
    while True:
      if not waiter.Wait():
        break  # nothing to wait for
      i += 1
      if job_state.AllDone():
        break

    log('waited for %d processes', i)
    return 0

  # Get list of jobs.  Then we need to check if they are ALL stopped.
  # Returns the exit code of the last one on the COMMAND LINE, not the exit
  # code of last one to FINSIH.

  status = 1  # error
  for pid in pids:
    # NOTE: osh doesn't accept 'wait %1' yet
    try:
      jid = int(pid)
    except ValueError:
      util.error('Invalid argument %r', pid)
      return 127

    job = job_state.jobs.get(jid)
    if job is None:
      util.error('No such job: %s', jid)
      return 127

    st = job.WaitUntilDone(waiter)
    if isinstance(st, list):
      status = st[-1]
      state.SetGlobalArray(mem, 'PIPESTATUS', [str(p) for p in st])
    else:
      status = st

  return status


def Jobs(argv, job_state):
  """List jobs."""
  job_state.List()
  return 0


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


def Read(argv, splitter, mem):
  arg, i = READ_SPEC.Parse(argv)

  names = argv[i:]
  if arg.n is not None:  # read a certain number of bytes
    try:
      name = names[0]
    except IndexError:
      name = 'REPLY'  # default variable name
    s = posix.read(sys.stdin.fileno(), arg.n)
    #log('read -n: %s = %s', name, s)

    state.SetLocalString(mem, name, s)
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

    spans = splitter.SplitForRead(line, not arg.r)
    done, join_next = _AppendParts(line, spans, max_results, join_next, parts)

    #log('PARTS %s continued %s', parts, continued)
    if done:
      break

  if arg.a:
    state.SetArrayDynamic(mem, arg.a, parts)
  else:
    for i in xrange(max_results):
      try:
        s = parts[i]
      except IndexError:
        s = ''  # if there are too many variables
      #log('read: %s = %s', names[i], s)
      state.SetStringDynamic(mem, names[i], s)

  return status


def Shift(argv, mem):
  if len(argv) > 1:
    util.error('shift: too many arguments')
    return 1
  try:
    n = int(argv[0])
  except IndexError:
    n = 1
  except ValueError:
    print("Invalid shift argument %r" % argv[1], file=sys.stderr)
    return 1  # runtime error

  return mem.Shift(n)

CD_SPEC = _Register('cd')
CD_SPEC.ShortFlag('-L')
CD_SPEC.ShortFlag('-P')

def Cd(argv, mem, dir_stack):
  arg, i = CD_SPEC.Parse(argv)
  # TODO: error checking, etc.
  # TODO: ensure that if multiple flags are provided, the *last* one overrides
  # the others.

  try:
    dest_dir = argv[i]
  except IndexError:
    val = mem.GetVar('HOME')
    if val.tag == value_e.Undef:
      util.error("$HOME isn't defined")
      return 1
    elif val.tag == value_e.Str:
      dest_dir = val.s
    elif val.tag == value_e.StrArray:
      util.error("$HOME shouldn't be an array.")
      return 1

  if dest_dir == '-':
    old = mem.GetVar('OLDPWD', scope_e.GlobalOnly)
    if old.tag == value_e.Undef:
      log('OLDPWD not set')
      return 1
    elif old.tag == value_e.Str:
      dest_dir = old.s
      print(dest_dir)  # Shells print the directory
    elif old.tag == value_e.StrArray:
      # TODO: Prevent the user from setting OLDPWD to array (or maybe they
      # can't even set it at all.)
      raise AssertionError('Invalid OLDPWD')

  pwd = mem.GetVar('PWD')
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
    # TODO: Add line number, etc.
    util.error("cd %r: %s", real_dest_dir, posix.strerror(e.errno))
    return 1

  state.ExportGlobalString(mem, 'OLDPWD', pwd.s)
  state.ExportGlobalString(mem, 'PWD', real_dest_dir)
  dir_stack.Reset()  # for pushd/popd/dirs
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

  sys.stdout.flush()


def Pushd(argv, mem, dir_stack):
  num_args = len(argv)
  if num_args <= 0:
    util.error('pushd: no other directory')
    return 1
  elif num_args > 1:
    util.error('pushd: too many arguments')
    return 1

  dest_dir = os_path.abspath(argv[0])
  try:
    posix.chdir(dest_dir)
  except OSError as e:
    util.error("pushd: %r: %s", dest_dir, posix.strerror(e.errno))
    return 1

  dir_stack.Push(dest_dir)
  _PrintDirStack(dir_stack, SINGLE_LINE, mem.GetVar('HOME'))
  state.SetGlobalString(mem, 'PWD', dest_dir)
  return 0


def Popd(argv, mem, dir_stack):
  dest_dir = dir_stack.Pop()
  if dest_dir is None:
    util.error('popd: directory stack is empty')
    return 1

  try:
    posix.chdir(dest_dir)
  except OSError as e:
    util.error("popd: %r: %s", dest_dir, posix.strerror(e.errno))
    return 1

  _PrintDirStack(dir_stack, SINGLE_LINE, mem.GetVar('HOME'))
  state.SetGlobalString(mem, 'PWD', dest_dir)
  return 0


DIRS_SPEC = _Register('dirs')
DIRS_SPEC.ShortFlag('-c')
DIRS_SPEC.ShortFlag('-l')
DIRS_SPEC.ShortFlag('-p')
DIRS_SPEC.ShortFlag('-v')


def Dirs(argv, home_dir, dir_stack):
  arg, i = DIRS_SPEC.Parse(argv)
  style = SINGLE_LINE

  # Following bash order of flag priority
  if arg.l:
    home_dir = None
  if arg.c:
    dir_stack.Reset()
    return 0
  elif arg.v:
    style = WITH_LINE_NUMBERS
  elif arg.p:
    style = WITHOUT_LINE_NUMBERS

  _PrintDirStack(dir_stack, style, home_dir)
  return 0


PWD_SPEC = _Register('pwd')
PWD_SPEC.ShortFlag('-L')
PWD_SPEC.ShortFlag('-P')


def Pwd(argv, mem):
  arg, i = PWD_SPEC.Parse(argv)

  pwd = mem.GetVar('PWD').s

  # '-L' is the default behavior; no need to check it
  # TODO: ensure that if multiple flags are provided, the *last* one overrides
  # the others
  if arg.P:
    pwd = libc.realpath(pwd)
  print(pwd)
  return 0


EXPORT_SPEC = _Register('export')
EXPORT_SPEC.ShortFlag('-n')


def Export(argv, mem):
  arg, i = EXPORT_SPEC.Parse(argv)
  if arg.n:
    for name in argv[i:]:
      m = match.IsValidVarName(name)
      if not m:
        raise args.UsageError('export: Invalid variable name %r' % name)

      # NOTE: bash doesn't care if it wasn't found.
      mem.ClearFlag(name, var_flags_e.Exported, scope_e.Dynamic)
  else:
    for arg in argv[i:]:
      parts = arg.split('=', 1)
      if len(parts) == 1:
        name = parts[0]
        val = None  # Creates an empty variable
      else:
        name, s = parts
        val = value.Str(s)

      m = match.IsValidVarName(name)
      if not m:
        raise args.UsageError('export: Invalid variable name %r' % name)

      #log('%s %s', name, val)
      mem.SetVar(
          lvalue.LhsName(name), val, (var_flags_e.Exported,), scope_e.Dynamic)

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


def Set(argv, exec_opts, mem):
  # TODO:
  # - How to integrate this with auto-completion?  Have to handle '+'.

  if not argv:  # empty
    # TODO:
    # - This should be set -o, not plain 'set'.
    # - When no arguments are given, it shows functions/vars?  Why not show
    # other state?
    exec_opts.ShowOptions([])
    return 0

  arg_r = args.Reader(argv)
  arg = SET_SPEC.Parse(arg_r)

  SetExecOpts(exec_opts, arg.opt_changes)
  # Hm do we need saw_double_dash?
  if arg.saw_double_dash or not arg_r.AtEnd():
    mem.SetArgv(arg_r.Rest())
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


def Shopt(argv, exec_opts):
  arg, i = SHOPT_SPEC.Parse(argv)

  if arg.p:  # print values
    if arg.o:  # use set -o names
      exec_opts.ShowOptions(argv[i:])
    else:
      exec_opts.ShowShoptOptions(argv[i:])
    return 0

  if arg.q:  # query values
    for opt_name in argv[i:]:
      if not hasattr(exec_opts, opt_name):
        return 2  # bash gives 1 for invalid option; 2 is better
      if not getattr(exec_opts, opt_name):
        return 1  # at least one option is not true
    return 0  # all options are true

  b = None
  if arg.s:
    b = True
  elif arg.u:
    b = False

  if b is None:
    raise NotImplementedError  # Display options

  for opt_name in argv[i:]:
    if arg.o:
      exec_opts.SetOption(opt_name, b)
    else:
      exec_opts.SetShoptOption(opt_name, b)

  return 0


UNSET_SPEC = _Register('unset')
UNSET_SPEC.ShortFlag('-v')
UNSET_SPEC.ShortFlag('-f')


# TODO:
# - Parse lvalue expression: unset 'a[ i - 1 ]'.  Static or dynamic parsing?
def Unset(argv, mem, funcs):
  arg, i = UNSET_SPEC.Parse(argv)

  for name in argv[i:]:
    if arg.f:
      if name in funcs:
        del funcs[name]
    elif arg.v:
      ok, _  = mem.Unset(lvalue.LhsName(name), scope_e.Dynamic)
      if not ok:
        util.error("Can't unset readonly variable %r", name)
        return 1
    else:
      # Try to delete var first, then func.
      ok, found = mem.Unset(lvalue.LhsName(name), scope_e.Dynamic)
      if not ok:
        util.error("Can't unset readonly variable %r", name)
        return 1
      #log('%s: %s', name, found)
      if not found:
        if name in funcs:
          del funcs[name]

  return 0


def _ResolveNames(names, funcs, path_val):
  if path_val.tag == value_e.Str:
    path_list = path_val.s.split(':')
  else:
    path_list = []  # treat as empty path

  results = []
  for name in names:
    if name in funcs:
      kind = ('function', name)
    elif Resolve(name) != builtin_e.NONE:
      kind = ('builtin', name)
    elif ResolveSpecial(name) != builtin_e.NONE:
      kind = ('builtin', name)
    elif lex.IsOtherBuiltin(name):  # declare, continue, etc.
      kind = ('builtin', name)
    elif lex.IsKeyword(name):
      kind = ('keyword', name)
    else:
      # Now look for files.
      found = False
      for path_dir in path_list:
        full_path = os_path.join(path_dir, name)
        if path_stat.exists(full_path):
          kind = ('file', full_path)
          found = True
          break
      if not found:  # Nothing printed, but status is 1.
        kind = (None, None)
    results.append(kind)

  return results


COMMAND_SPEC = _Register('command')
COMMAND_SPEC.ShortFlag('-v')
#COMMAND_SPEC.ShortFlag('-V')  # Another verbose mode.


class Command(object):
  def __init__(self, ex, funcs, mem):
    self.ex = ex
    self.funcs = funcs
    self.mem = mem

  def __call__(self, argv, fork_external, span_id):
    arg, i = COMMAND_SPEC.Parse(argv)
    if arg.v:
      path_val = self.mem.GetVar('PATH')
      status = 0
      for kind, arg in _ResolveNames(argv[i:], self.funcs, path_val):
        if kind is None:
          status = 1  # nothing printed, but we fail
        else:
          # This is for -v, -V is more detailed.
          print(arg)
      return status

    # 'command ls' suppresses function lookup.
    return self.ex.RunSimpleCommand(argv, fork_external, span_id, funcs=False)


TYPE_SPEC = _Register('type')
TYPE_SPEC.ShortFlag('-t')
TYPE_SPEC.ShortFlag('-p')


def Type(argv, funcs, path_val):
  arg, i = TYPE_SPEC.Parse(argv)

  status = 0
  for kind, name in _ResolveNames(argv[i:], funcs, path_val):
    if kind is None:
      status = 1  # nothing printed, but we fail
    else:
      if arg.t:
        print(kind)
      elif arg.p:
        if kind == 'file':
          print(name)
      else:
        # Alpine's abuild relies on this text because busybox ash doesn't have
        # -t!
        # ash prints "is a shell function" instead of "is a function", but the
        # regex accouts for that.
        print('%s is a %s' % (name, kind))
        if kind == 'function':
          # bash prints the function body, busybox ash doesn't.
          pass

  # REQUIRED because of Python's buffering.  A command sub may give the wrong
  # result otherwise.
  sys.stdout.flush()
  return status


DECLARE_SPEC = _Register('declare')
DECLARE_SPEC.ShortFlag('-f')
DECLARE_SPEC.ShortFlag('-F')
DECLARE_SPEC.ShortFlag('-p')


def DeclareTypeset(argv, mem, funcs):
  arg, i = DECLARE_SPEC.Parse(argv)

  status = 0

  # NOTE: in bash, -f shows the function body, while -F shows the name.  In
  # osh, they're identical and behave like -F.

  if arg.f or arg.F:  # Lookup and print functions.
    names = argv[i:]
    if names:
      for name in names:
        if name in funcs:
          print(name)
          # TODO: Could print LST, or render LST.  Bash does this.  'trap' too.
          #print(funcs[name])
        else:
          status = 1
    elif arg.F:
      for func_name in sorted(funcs):
        print('declare -f %s' % (func_name))
    else:
      raise NotImplementedError('declare/typeset -f without args')

  elif arg.p:  # Lookup and print variables.

    names = argv[i:]
    if names:
      for name in names:
        val = mem.GetVar(name)
        if val.tag != value_e.Undef:
          # TODO: Print flags.

          print(name)
        else:
          status = 1
    else:
      raise NotImplementedError('declare/typeset -p without args')

  else:
    raise NotImplementedError

  sys.stdout.flush()
  return status


ALIAS_SPEC = _Register('alias')


def Alias(argv, aliases):
  if not argv:
    for name in sorted(aliases):
      alias_exp = aliases[name]
      # This is somewhat like bash, except we use %r for ''.
      print('alias %s=%r' % (name, alias_exp))
    return 0

  status = 0
  for arg in argv:
    parts = arg.split('=', 1)
    if len(parts) == 1:  # if we get a plain word without, print alias
      name = parts[0]
      alias_exp = aliases.get(name)
      if alias_exp is None:
        util.error('alias %r is not defined', name)  # TODO: error?
        status = 1
      else:
        print('alias %s=%r' % (name, alias_exp))
    else:
      name, alias_exp = parts
      aliases[name] = alias_exp

  #print(argv)
  #log('AFTER ALIAS %s', aliases)
  return status


UNALIAS_SPEC = _Register('unalias')


def UnAlias(argv, aliases):
  if not argv:
    raise args.UsageError('unalias NAME...')

  status = 0
  for name in argv:
    try:
      del aliases[name]
    except KeyError:
      util.error('alias %r is not defined', name)
      status = 1
  return status


def _SigIntHandler(unused, unused_frame):
  """
  Either this handler is installed, or the user's handler is installed.
  Python's default handler of raising KeyboardInterrupt should never be
  installed.
  """
  # TODO: It might be nice to write diagnostic messages when invokved with
  # 'osh --debug-pipe=/path'.
  #
  # NOTE: I think dash and POSIX somehow set the exit code to 128 + exit code?

  #print('Ctrl-C')
  pass


def RegisterSigIntHandler():
  #log('Registering')
  signal.signal(signal.SIGINT, _SigIntHandler)


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
  # POSIX lists the unmbers that are required.
  # http://pubs.opengroup.org/onlinepubs/9699919799/
  if sig_spec.strip() in ('1', '2', '3', '6', '9', '14', '15'):
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

def Trap(argv, traps, nodes_to_run, ex):
  arg, i = TRAP_SPEC.Parse(argv)

  if arg.p:  # Print registered handlers
    for name, value in traps.iteritems():
      # The unit tests rely on this being one line.
      # bash prints a line that can be re-parsed.
      print('%s %s' % (name, value.__class__.__name__))

    sys.stdout.flush()
    return 0

  if arg.l:  # List valid signals and hooks
    ordered = _SIGNAL_NAMES.items()
    ordered.sort(key=lambda x: x[1])

    for name in _HOOK_NAMES:
      print('   %s' % name)
    for name, int_val in ordered:
      print('%2d %s' % (int_val, name))

    sys.stdout.flush()
    return 0

  try:
    code_str = argv[0]
    sig_spec = argv[1]
  except IndexError:
    raise args.UsageError('trap CODE SIGNAL_SPEC')

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
    util.error("Invalid signal or hook %r" % sig_spec)
    return 1

  # NOTE: sig_spec isn't validated when removing handlers.
  if code_str == '-':
    if sig_key in _HOOK_NAMES:
      try:
        del traps[sig_key]
      except KeyError:
        pass
      return 0

    if sig_num is not None:
      try:
        del traps[sig_key]
      except KeyError:
        pass

      # Restore default
      if sig_num == signal.SIGINT:
        RegisterSigIntHandler()
      else:
        signal.signal(sig_num, signal.SIG_DFL)
      return 0

    raise AssertionError('Signal or trap')

  # Try parsing the code first.
  node = ex.ParseTrapCode(code_str)
  if node is None:
    return 1  # ParseTrapCode() prints an error for us.

  # Register a hook.
  if sig_key in _HOOK_NAMES:
    if sig_key in ('ERR', 'RETURN', 'DEBUG'):
      util.warn("*** The %r isn't yet implemented in OSH ***", sig_spec)
    traps[sig_key] = _TrapHandler(node, nodes_to_run)
    return 0

  # Register a signal.
  sig_num = _GetSignalNumber(sig_spec)
  if sig_num is not None:
    handler = _TrapHandler(node, nodes_to_run)
    # For signal handlers, the traps dictionary is used only for debugging.
    traps[sig_key] = handler

    signal.signal(sig_num, handler)
    return 0

  raise AssertionError('Signal or trap')

  # Example:
  # trap -- 'echo "hi  there" | wc ' SIGINT
  #
  # Then hit Ctrl-C.


def Umask(argv):
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

      util.warn('*** umask with symbolic input not implemented ***')
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


def _GetOpts(spec, argv, optind):
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
      util.error('getopts: option %r requires an argument', current)
      # Hm doesn't cause status 1?
      return 0, '?', optarg, optind

    optind += 1

  return 0, opt_char, optarg, optind


# spec string -> {flag, arity}
_GETOPTS_CACHE = {}  # type: Dict[str, Dict[str, bool]]

def GetOpts(argv, mem):
  """
  Vars to set:
    OPTIND - initialized to 1 at startup
    OPTARG - argument
  Vars used:
    OPTERR: disable printing of error messages
  """
  # TODO: need to handle explicit args.

  try:
    # NOTE: If first char is a colon, error reporting is different.  Alpine
    # might not use that?
    spec_str = argv[0]
    var_name = argv[1]
  except IndexError:
    raise args.UsageError('getopts optstring name [arg]')

  try:
    spec = _GETOPTS_CACHE[spec_str]
  except KeyError:
    spec = _ParseOptSpec(spec_str)
    _GETOPTS_CACHE[spec_str] = spec

  # These errors are fatal errors, not like the builtin exiting with code 1.
  # Because the invariants of the shell have been violated!
  v = mem.GetVar('OPTIND')
  if v.tag != value_e.Str:
    e_die('OPTIND should be a string, got %r', v)
  try:
    optind = int(v.s)
  except ValueError:
    e_die("OPTIND doesn't look like an integer, got %r", v.s)

  user_argv = argv[2:] or mem.GetArgv()
  status, opt_char, optarg, optind = _GetOpts(spec, user_argv, optind)

  # Bug fix: bash-completion uses a *local* OPTIND !  Not global.
  state.SetStringDynamic(mem, var_name, opt_char)
  state.SetStringDynamic(mem, 'OPTARG', optarg)
  state.SetStringDynamic(mem, 'OPTIND', str(optind))
  return status


def Help(argv, loader):
  # TODO: Need $VERSION inside all pages?
  try:
    topic = argv[0]
  except IndexError:
    topic = 'help'

  if topic == 'toc':
    # Just show the raw source.
    f = loader.open('doc/osh-quick-ref-toc.txt')
  else:
    try:
      section_id = osh_help.TOPIC_LOOKUP[topic]
    except KeyError:
      util.error('No help topics match %r', topic)
      return 1
    else:
      try:
        f = loader.open('_devbuild/osh-quick-ref/%s' % section_id)
      except IOError as e:
        util.error(str(e))
        raise AssertionError('Should have found %r' % section_id)

  for line in f:
    sys.stdout.write(line)
  f.close()
  return 0


HISTORY_SPEC = _Register('history')


class History(object):
  """Show history."""

  def __init__(self, readline_mod):
    self.readline_mod = readline_mod

  def __call__(self, argv):
    # NOTE: This builtin doesn't do anything in non-interactive mode in bash?
    # It silently exits zero.
    # zsh -c 'history' produces an error.
    readline_mod = self.readline_mod
    if not readline_mod:
      raise args.UsageError("OSH wasn't compiled with the readline module.")

    #arg_r = args.Reader(argv)
    arg, i = HISTORY_SPEC.Parse(argv)

    # Returns 0 items in non-interactive mode?
    num_items = readline_mod.get_current_history_length()
    #log('len = %d', num_items)

    rest = argv[i:]
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


def Repr(argv, mem):
  """Given a list of variable names, print their values.

  'repr a' is a lot easier to type than 'argv.py "${a[@]}"'.
  """
  status = 0
  for name in argv:
    if not match.IsValidVarName(name):
      util.error('%r is not a valid variable name', name)
      return 1

    # TODO: Should we print flags too?
    val = mem.GetVar(name)
    if val.tag == value_e.Undef:
      print('%r is not defined' % name)
      status = 1
    else:
      print('%s = %s' % (name, val))
  return status


def main(argv):
  # Localization: Optionally  use GNU gettext()?  For help only.  Might be
  # useful in parser error messages too.  Good thing both kinds of code are
  # generated?  Because I don't want to deal with a C toolchain for it.

  loader = pyutil.GetResourceLoader()
  Help([], loader)

  for name, spec in BUILTIN_DEF.arg_specs.iteritems():
    print(name)
    spec.PrintHelp(sys.stdout)
    print()


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
