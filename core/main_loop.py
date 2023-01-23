"""
main_loop.py

Variants:
  main_loop.Interactive()    calls ParseInteractiveLine() and ExecuteAndCatch()
  main_loop.Batch()          calls ParseLogicalLine() and ExecuteAndCatch()
  main_loop.Headless()       calls Batch() like eval and source. 
                                   We want 'echo 1\necho 2\n' to work, so we 
                                   don't bother with "the PS2 problem".
  main_loop.ParseWholeFile() calls ParseLogicalLine().  Used by osh -n.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.syntax_asdl import (
    command_t, command, parse_result__Node, parse_result_e
)
from core import error
from core import process
from core import ui
from core import util
from core.pyerror import log
from frontend import reader
from osh import cmd_eval
from mycpp import mylib
from mycpp.mylib import print_stderr, tagswitch

import fanos
import posix_ as posix

from typing import cast, Any, List, TYPE_CHECKING
if TYPE_CHECKING:
  from core.comp_ui import _IDisplay
  from core.ui import ErrorFormatter
  from frontend import parse_lib
  from osh.cmd_parse import CommandParser
  from osh.cmd_eval import CommandEvaluator
  from osh.prompt import UserPlugin

_ = log


class ctx_Descriptors(object):
  """Save and restore descriptor state for the headless EVAL command."""

  def __init__(self, fds):
    # type: (List[int]) -> None

    self.saved0 = process.SaveFd(0)
    self.saved1 = process.SaveFd(1)
    self.saved2 = process.SaveFd(2)

    #ShowDescriptorState('BEFORE')
    posix.dup2(fds[0], 0)
    posix.dup2(fds[1], 1)
    posix.dup2(fds[2], 2)

    self.fds = fds

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None

    # Restore
    posix.dup2(self.saved0, 0)
    posix.dup2(self.saved1, 1)
    posix.dup2(self.saved2, 2)

    # Restoration done, so close
    posix.close(self.saved0)
    posix.close(self.saved1)
    posix.close(self.saved2)

    # And close descriptors we were passed
    posix.close(self.fds[0])
    posix.close(self.fds[1])
    posix.close(self.fds[2])


def fanos_log(msg):
  # type: (str) -> None
  print_stderr('[FANOS] %s' % msg)


def ShowDescriptorState(label):
  # type: (str) -> None
  if mylib.PYTHON:
    import os  # Our posix fork doesn't have os.system
    import time
    time.sleep(0.01)  # prevent interleaving

    pid = posix.getpid()
    print_stderr(label + ' (PID %d)' % pid)

    os.system('ls -l /proc/%d/fd >&2' % pid)

    time.sleep(0.01)  # prevent interleaving

class Headless(object):
  """Main loop for headless mode."""

  def __init__(self, cmd_ev, parse_ctx, errfmt):
    # type: (CommandEvaluator, parse_lib.ParseContext, ErrorFormatter) -> None
    self.cmd_ev = cmd_ev
    self.parse_ctx = parse_ctx
    self.errfmt = errfmt

  def Loop(self):
    # type: () -> int
    try:
      return self._Loop()
    except ValueError as e:
      fanos.send(1, 'ERROR %s' % e)
      return 1

  def EVAL(self, arg):
    # type: (str) -> str

    # This logic is similar to the 'eval' builtin in osh/builtin_meta.

    # Note: we're not using the InteractiveLineReader, so there's no history
    # expansion.  It would be nice if there was a way for the client to use
    # that.
    line_reader = reader.StringLineReader(arg, self.parse_ctx.arena)
    c_parser = self.parse_ctx.MakeOshParser(line_reader)

    # Status is unused; $_ can be queried by the headless client
    unused_status = Batch(self.cmd_ev, c_parser, self.errfmt, 0)

    return ''  # result is always 'OK ' since there was no protocol error

  def _Loop(self):
    # type: () -> int
    fanos_log('Connect stdin and stdout to one end of socketpair() and send control messages.  osh writes debug messages (like this one) to stderr.')

    fd_out = []  # type: List[int]
    while True:
      try:
        blob = fanos.recv(0, fd_out)
      except ValueError as e:
        fanos_log('protocol error: %s' % e)
        raise  # higher level handles it

      if blob is None:
        fanos_log('EOF received')
        break

      fanos_log('received blob %r' % blob)
      if ' ' in blob:
        bs = blob.split(' ', 1)
        command = bs[0]
        arg = bs[1]
      else:
        command = blob
        arg = ''

      if command == 'GETPID':
        reply = str(posix.getpid())

      elif command == 'EVAL':
        #fanos_log('arg %r', arg)

        if len(fd_out) != 3:
          raise ValueError('Expected 3 file descriptors')

        for fd in fd_out:
          fanos_log('received descriptor %d' % fd)

        with ctx_Descriptors(fd_out):
          reply = self.EVAL(arg)

        #ShowDescriptorState('RESTORED')

      # Note: lang == 'osh' or lang == 'oil' puts this in different modes.
      # Do we also need 'complete --oil' and 'complete --osh' ?
      elif command == 'PARSE':
        # Just parse
        reply = 'TODO:PARSE'

      else:
        fanos_log('Invalid command %r' % command)
        raise ValueError('Invalid command %r' % command)

      fanos.send(1, b'OK %s' % reply)
      del fd_out[:]  # reset for next iteration

    return 0

def Interactive(flag, cmd_ev, c_parser, display, prompt_plugin, errfmt):
  # type: (arg_types.main, CommandEvaluator, CommandParser, _IDisplay, UserPlugin, ErrorFormatter) -> int

  # TODO: Any could be _Attributes from frontend/args.py

  status = 0
  done = False
  while not done:
    mylib.MaybeCollect()  # manual GC point

    # - This loop has a an odd structure because we want to do cleanup after
    # every 'break'.  (The ones without 'done = True' were 'continue')
    # - display.EraseLines() needs to be called BEFORE displaying anything, so
    # it appears in all branches.

    while True:  # ONLY EXECUTES ONCE
      prompt_plugin.Run()
      try:
        # may raise HistoryError or ParseError
        result = c_parser.ParseInteractiveLine()
        UP_result = result
        with tagswitch(result) as case:
          if case(parse_result_e.EmptyLine):
            display.EraseLines()
            break  # quit shell
          elif case(parse_result_e.Eof):
            display.EraseLines()
            done = True
            break  # quit shell
          elif case(parse_result_e.Node):
            result = cast(parse_result__Node, UP_result)
            node = result.cmd
          else:
            raise AssertionError()

      except util.HistoryError as e:  # e.g. expansion failed
        # Where this happens:
        # for i in 1 2 3; do
        #   !invalid
        # done
        display.EraseLines()
        print(e.UserErrorString())
        break
      except error.Parse as e:
        display.EraseLines()
        errfmt.PrettyPrintError(e)
        status = 2
        cmd_ev.mem.SetLastStatus(status)
        break
      except KeyboardInterrupt:  # thrown by InteractiveLineReader._GetLine()
        # Here we must print a newline BEFORE EraseLines()
        print('^C')
        display.EraseLines()
        # http://www.tldp.org/LDP/abs/html/exitcodes.html
        # bash gives 130, dash gives 0, zsh gives 1.
        # Unless we SET cmd_ev.last_status, scripts see it, so don't bother now.
        break

      display.EraseLines()  # Clear candidates right before executing

      # to debug the slightly different interactive prasing
      if cmd_ev.exec_opts.noexec():
        ui.PrintAst(node, flag)
        break

      try:
        is_return, _ = cmd_ev.ExecuteAndCatch(node)
      except KeyboardInterrupt:  # issue 467, Ctrl-C during $(sleep 1)
        is_return = False
        display.EraseLines()
        status = 130  # 128 + 2
        cmd_ev.mem.SetLastStatus(status)
        break

      status = cmd_ev.LastStatus()
      if is_return:
        done = True
        break

      break  # QUIT LOOP after one iteration.

    cmd_ev.RunPendingTraps()  # Run trap handlers even if we get just ENTER

    # Cleanup after every command (or failed command).

    # Reset internal newline state.
    c_parser.Reset()
    c_parser.ResetInputObjects()

    display.Reset()  # clears dupes and number of lines last displayed

    # TODO: Replace this with a shell hook?  with 'trap', or it could be just
    # like command_not_found.  The hook can be 'echo $?' or something more
    # complicated, i.e. with timetamps.
    if flag.print_status:
      print('STATUS\t%r' % status)

  return status



def Batch(cmd_ev, c_parser, errfmt, cmd_flags=0):
  # type: (CommandEvaluator, CommandParser, ui.ErrorFormatter, int) -> int
  """Loop for batch execution.

  Returns:
    int status, e.g. 2 on parse error

  Can this be combined with interative loop?  Differences:
  
  - Handling of parse errors.
  - Have to detect here docs at the end?

  Not a problem:
  - Get rid of --print-status and --show-ast for now
  - Get rid of EOF difference

  TODO:
  - Do source / eval need this?
    - 'source' needs to parse incrementally so that aliases are respected
    - I doubt 'eval' does!  You can test it.
  - In contrast, 'trap' should parse up front?
  - What about $() ?
  """
  status = 0
  while True:
    try:
      node = c_parser.ParseLogicalLine()  # can raise ParseError
      if node is None:  # EOF
        c_parser.CheckForPendingHereDocs()  # can raise ParseError
        break
    except error.Parse as e:
      errfmt.PrettyPrintError(e)
      status = 2
      break

    # Only optimize if we're on the last line like -c "echo hi" etc.
    if (cmd_flags & cmd_eval.IsMainProgram and
        c_parser.line_reader.LastLineHint()):
      cmd_flags |= cmd_eval.Optimize

    # can't optimize this because we haven't seen the end yet
    is_return, is_fatal = cmd_ev.ExecuteAndCatch(node, cmd_flags=cmd_flags)
    status = cmd_ev.LastStatus()
    # e.g. 'return' in middle of script, or divide by zero
    if is_return or is_fatal:
      break

    mylib.MaybeCollect()  # manual GC point

  return status


def ParseWholeFile(c_parser):
  # type: (CommandParser) -> command_t
  """Parse an entire shell script.

  This uses the same logic as Batch().  Used by:
  - osh -n
  - oshc translate
  - Used by 'trap' to store code.  But 'source' and 'eval' use Batch().
  """
  children = []  # type: List[command_t]
  while True:
    node = c_parser.ParseLogicalLine()  # can raise ParseError
    if node is None:  # EOF
      c_parser.CheckForPendingHereDocs()  # can raise ParseError
      break
    children.append(node)

    mylib.MaybeCollect()  # manual GC point

  if len(children) == 1:
    return children[0]
  else:
    return command.CommandList(children)
