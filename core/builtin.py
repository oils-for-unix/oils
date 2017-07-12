#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
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

import os
import sys

from core import args
from core import runtime
from core import util
from core import state

from osh import lex

value_e = runtime.value_e
scope = runtime.scope
var_flags = runtime.var_flags
log = util.log

# NOTE: NONE is a special value.
# TODO:
# - Make a table of name to enum?  source, dot, etc.
# - So you can just add "complete" and have it work.

EBuiltin = util.Enum('EBuiltin', """
NONE READ ECHO SHIFT
CD PUSHD POPD DIRS
EXPORT UNSET SET
TRAP UMASK
EXIT SOURCE DOT EVAL EXEC WAIT JOBS 
COMPLETE COMPGEN DEBUG_LINE
TRUE FALSE
COLON
HELP
""".split())


# These can't be redefined by functions.
# http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_14
# On the other hand, 'cd' CAN be redefined.
#
# NOTE: OSH treats these specially:
# - break/continue/return
# - local/readonly
SPECIAL_BUILTINS = [
    'break', ':', 'continue', '.', 'eval', 'exec', 'exit', 'export',
    'readonly', 'return', 'set', 'shift', 'times', 'trap', 'unset',

    # local and declare are not POSIX, but should be here since export and
    # readonly are.
    'local', 'declare',
]

# TODO: Add a way to register.
BUILTINS = ['echo', 'read']


class Builtins(object):
  """
  NOTE: Used by completion.py.
  """
  def __init__(self):
    # Is this what we want?
    names = set()
    names.update(BUILTINS)
    names.update(SPECIAL_BUILTINS)
    # TODO: Also complete keywords first for, while, etc.  Bash/zsh/fish/yash
    # all do this.  Also do/done

    self.to_complete = sorted(names)

  def GetNamesToComplete(self):
    """For completion of builtin names."""
    return self.to_complete


# TODO: Resolve() and EBuiltin kind of useless?  We could just test for string
# equality directly.  Or do we want to cache this lookup so it isn't done on
# say every iteration of a loop?

def ResolveSpecial(argv0):
  # TODO: Add more special builtins here
  if argv0 == "export":
    return EBuiltin.EXPORT
  elif argv0 == "exit":
    return EBuiltin.EXIT
  elif argv0 == ":":
    return EBuiltin.COLON

  return EBuiltin.NONE

def Resolve(argv0):
  # TODO: ResolveSpecialBuiltin first, then ResolveFunction, then
  # ResolveOtherBuiltin.  In other words, you can't redefine special builtins
  # with functions, but you can redefine other builtins.

  # For completion, this is a flat list of names.  Although coloring them
  # would be nice.

  # TODO: Use BuiltinDef instances in BUILTINS to initialize.

  if argv0 == "read":
    return EBuiltin.READ
  elif argv0 == "echo":
    return EBuiltin.ECHO
  elif argv0 == "cd":
    return EBuiltin.CD
  elif argv0 == "shift":
    return EBuiltin.SHIFT
  elif argv0 == "pushd":
    return EBuiltin.PUSHD
  elif argv0 == "popd":
    return EBuiltin.POPD
  elif argv0 == "dirs":
    return EBuiltin.DIRS

  elif argv0 == "source":
    return EBuiltin.SOURCE
  elif argv0 == ".":
    return EBuiltin.DOT

  elif argv0 == "trap":
    return EBuiltin.TRAP
  elif argv0 == "umask":
    return EBuiltin.UMASK
  elif argv0 == "eval":
    return EBuiltin.EVAL
  elif argv0 == "exec":
    return EBuiltin.EXEC
  elif argv0 == "wait":
    return EBuiltin.WAIT
  elif argv0 == "jobs":
    return EBuiltin.JOBS

  elif argv0 == "set":
    return EBuiltin.SET
  elif argv0 == "unset":
    return EBuiltin.UNSET
  elif argv0 == "complete":
    return EBuiltin.COMPLETE
  elif argv0 == "compgen":
    return EBuiltin.COMPGEN

  elif argv0 == "true":
    return EBuiltin.TRUE
  elif argv0 == "false":
    return EBuiltin.FALSE

  elif argv0 == "help":
    return EBuiltin.HELP

  elif argv0 == "debug-line":
    return EBuiltin.DEBUG_LINE

  return EBuiltin.NONE


echo_spec = args.BuiltinFlags()
echo_spec.ShortFlag('-e')  # no backslash escapes
echo_spec.ShortFlag('-n')


def Echo(argv):
  """
  echo builtin.  Doesn't depend on executor state.

  TODO: Where to put help?  docstring?
  """
  # NOTE: both getopt and optparse are unsuitable for 'echo' because:
  # - 'echo -c' should print '-c', not fail
  # - echo '---' should print ---, not fail

  arg, i = echo_spec.ParseLikeEcho(argv)
  if arg.e:
    util.warn('*** echo -e not implemented ***')

  #log('echo argv %s', argv)
  n = len(argv)
  for i in xrange(i, n-1):
    sys.stdout.write(argv[i])
    sys.stdout.write(' ')  # arg separator
  if argv:
    sys.stdout.write(argv[-1])
  if not arg.n:
    sys.stdout.write('\n')

  # Do I need the flush?  Had a problem here under load, but it might not have
  # been because of that.
  # File "/home/andy/git/oil/bin/../core/cmd_exec.py", line 251, in _RunBuiltin
  #   status = builtin.Echo(argv)
  # File "/home/andy/git/oil/bin/../core/builtin.py", line 431, in Echo
  #   sys.stdout.flush()
  # IOError: [Errno 32] Broken pipe

  sys.stdout.flush()
  return 0


def Exit(argv):
  if len(argv) > 1:
    util.error('exit: too many arguments')
    return 1
  try:
    code = int(argv[0])
  except IndexError:
    code = 0
  except ValueError as e:
    print("Invalid argument %r" % argv[0], file=sys.stderr)
    code = 1  # Runtime Error
  # TODO: Should this be turned into our own SystemExit exception?
  sys.exit(code)


import getopt

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
  # NOTE: echo can't use getopt because of 'echo ---'
  # But that's a special case; the rest of the builtins can use it.
  # We must respect -- everywhere, EXCEPT echo.  'wait -- -n' should work must work.

  opt_n = False

  try:
    opts, args = getopt.getopt(argv, 'n')
  except getopt.GetoptError as e:
    util.usage(str(e))
    sys.exit(2)
  for name, val in opts:
    if name == '-n':
      opt_n = True
    else:
      raise AssertionError

  if opt_n:
    # wait -n returns the exit status of the process.  But how do you know
    # WHICH process?  That doesn't seem useful.
    log('wait next')
    if waiter.Wait():
      return waiter.last_status
    else:
      return 127  # nothing to wait for

  if not args:
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
  for a in args:
    # NOTE: osh doesn't accept 'wait %1' yet
    try:
      jid = int(a)
    except ValueError:
      util.error('Invalid argument %r', a)
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


def Read(argv, mem):
  # TODO:
  # - parse flags.
  # - Use IFS instead of Python's split().

  names = argv
  line = sys.stdin.readline()
  if not line:  # EOF
    return 1

  if line.endswith('\n'):  # strip trailing newline
    line = line[:-1]
    status = 0
  else:
    # odd bash behavior: fail even if we can set variables.
    status = 1

  # leftover words assigned to the last name
  n = len(names)

  strs = line.split(None, n-1)

  for i in xrange(n):
    try:
      s = strs[i]
    except IndexError:
      s = ''  # if there are too many variables
    state.SetLocalString(mem, names[i], s)

  return status


def Shift(argv, mem):
  if len(argv) > 1:
    util.error('shift: too many arguments')
    return 1
  try:
    n = int(argv[0])
  except IndexError:
    n = 1
  except ValueError as e:
    print("Invalid shift argument %r" % argv[1], file=sys.stderr)
    return 1  # runtime error

  return mem.Shift(n)


def _Cd(argv, mem):
  # TODO: Parse flags, error checking, etc.
  dest_dir = argv[0]
  if dest_dir == '-':
    old = mem.GetVar('OLDPWD', scope.GlobalOnly)
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

  # Save OLDPWD.
  state.SetGlobalString(mem, 'OLDPWD', os.getcwd())
  os.chdir(dest_dir)
  state.SetGlobalString(mem, 'PWD', dest_dir)
  return 0


def Pushd(argv, dir_stack):
  dir_stack.append(os.getcwd())
  dest_dir = argv[0]
  os.chdir(dest_dir)  # TODO: error checking
  return 0


def Popd(argv, dir_stack):
  try:
    dest_dir = dir_stack.pop()
  except IndexError:
    log('popd: directory stack is empty')
    return 1
  os.chdir(dest_dir)  # TODO: error checking
  return 0


def Dirs(argv, dir_stack):
  print(dir_stack)
  return 0


EXPORT_SPEC = args.BuiltinFlags()
EXPORT_SPEC.ShortFlag('-n')


def Export(argv, mem):
  arg, i = EXPORT_SPEC.Parse(argv)
  if arg.n:
    for name in argv[i:]:
      # TODO: Validate variable name
      m = lex.VAR_NAME_RE.match(name)
      if not m:
        raise args.UsageError('export: Invalid variable name %r' % name)

      # NOTE: bash does not care if it wasn't found
      _ = mem.ClearFlag(name, var_flags.Exported, scope.Dynamic)
  else:
    for arg in argv[i:]:
      parts = arg.split('=', 1)
      if len(parts) == 1:
        name = parts[0]
        val = None  # Creates an empty variable
      else:
        name, s = parts
        val = runtime.Str(s)

      #log('%s %s', name, val)
      mem.SetVar(
          runtime.LhsName(name), val, (var_flags.Exported,), scope.Dynamic)

  return 0


def AddOptionsToArgSpec(spec):
  """Shared between 'set' builtin and the shell's own arg parser."""
  spec.Option('e', 'errexit')
  spec.Option('n', 'noexec')
  spec.Option('u', 'nounset')
  spec.Option('x', 'xtrace')
  spec.Option(None, 'pipefail')


set_spec = args.FlagsAndOptions()
AddOptionsToArgSpec(set_spec)


def SetExecOpts(exec_opts, opt_changes):
  for name, val in opt_changes:
    if name == 'errexit':
      exec_opts.errexit.Set(val)
    else:
      setattr(exec_opts, name, val)


def Set(argv, exec_opts, mem):
  # TODO:
  # - How to integrate this with auto-completion?  Have to handle '+'.

  if not argv:  # empty
    # TODO: If no arguments are given, it shows functions/vars?  Why not show
    # other state?
    print('TODO: set without arguments')
    return 0

  arg, i = set_spec.Parse(argv)

  SetExecOpts(exec_opts, arg.opt_changes)
  if arg.saw_double_dash or i != len(argv):  # set -u shouldn't affect argv
    mem.SetArgv(argv[i:])
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

  # Oil-specific
  if name == 'strict-arith':
    exec_opts.strict_arith = True
  elif name == 'strict-array':
    exec_opts.strict_array = True
  elif name == 'strict-command':
    exec_opts.strict_command = True
  elif name == 'strict-word':
    exec_opts.strict_word = True
  elif name == 'strict-scope':
    exec_opts.strict_scope = True


UNSET_SPEC = args.BuiltinFlags()
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
      mem.Unset(runtime.LhsName(name), scope.Dynamic)
    else:
      # Try to delete var first, then func.
      found = mem.Unset(runtime.LhsName(name), scope.Dynamic)
      #log('%s: %s', name, found)
      if not found:
        if name in funcs:
          del funcs[name]

  return 0


def Trap(argv, traps):
  # TODO: register trap

  # Example:
  # trap -- 'echo "hi  there" | wc ' SIGINT
  #
  # Then hit Ctrl-C.
  #
  # Yeah you need the EvalHelper.  traps is a list of signals to parsed
  # NODES.

  util.warn('*** trap not implemented ***')
  return 0


def Umask(argv):
  if len(argv) == 0:
    # umask() has a dumb API: you can't get it without modifying it first!
    # NOTE: dash disables interrupts around the two umask() calls, but that
    # shouldn't be a concern for us.  Signal handlers won't call umask().
    mask = os.umask(0)
    os.umask(mask)  # 
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
      os.umask(new_mask)
      return 0

  raise args.UsageError('umask: unexpected arguments')


def Help(argv, loader):
  f = loader.open('doc/osh-quick-ref-toc.txt')
  for line in f:
    sys.stdout.write(line)
  return 0


def DebugLine(argv, status_lines):
  # TODO: Maybe add a position flag?  Like debug-line -n 1 'foo'
  # And enforce that you get a single arg?

  status_lines[0].Write('DEBUG: %s', ' '.join(argv))
  return 0


def main(argv):
  # Localization: Optionally  use GNU gettext()?  For help only.  Might be
  # useful in parser error messages too.  Good thing both kinds of code are
  # generated?  Because I don't want to deal with a C toolchain for it.

  loader = util.GetResourceLoader()
  Help([], loader)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
