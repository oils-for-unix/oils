#!/usr/bin/python
"""
main_loop.py

Two variants:

main_loop.Interactive()
main_loop.Batch()

They call CommandParser.ParseLogicalLine() and Executor.ExecuteAndCatch().

Get rid of:

ex.Execute() -- only used for tests
ParseWholeFile() -- needs to check the here doc.
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import command_t, command
from _devbuild.gen.id_kind_asdl import Id
from core import ui
from core import util
from core.util import log
from osh import word

from typing import Any, Optional, List, TYPE_CHECKING
if TYPE_CHECKING:
  from core.alloc import Arena
  from osh.cmd_parse import CommandParser
  # commented out so --strict doesn't follow all
  #from osh.cmd_exec import Executor


def Interactive(opts, ex, c_parser, display, arena):
  # type: (Any, Any, CommandParser, Any, Arena) -> Any
  status = 0
  done = False
  while not done:
    # - This loop has a an odd structure because we want to do cleanup after
    # every 'break'.  (The ones without 'done = True' were 'continue')
    # - display.EraseLines() needs to be called BEFORE displaying anything, so
    # it appears in all branches.

    while True:  # ONLY EXECUTES ONCE
      try:
        w = c_parser.Peek()  # may raise HistoryError or ParseError

        c_id = word.CommandId(w)
        if c_id == Id.Op_Newline:  # print PS1 again, not PS2
          display.EraseLines()
          break  # next command
        elif c_id == Id.Eof_Real:  # InteractiveLineReader prints ^D
          display.EraseLines()
          done = True
          break  # quit shell

        node = c_parser.ParseLogicalLine()  # ditto, HistoryError or ParseError
      except util.HistoryError as e:  # e.g. expansion failed
        # Where this happens:
        # for i in 1 2 3; do
        #   !invalid
        # done
        display.EraseLines()
        print(e.UserErrorString())
        break
      except util.ParseError as e:
        display.EraseLines()
        ui.PrettyPrintError(e, arena)
        # NOTE: This should set the status interactively!  Bash does this.
        status = 2
        break
      except KeyboardInterrupt:  # thrown by InteractiveLineReader._GetLine()
        # Here we must print a newline BEFORE EraseLines()
        print('^C')
        display.EraseLines()
        # http://www.tldp.org/LDP/abs/html/exitcodes.html
        # bash gives 130, dash gives 0, zsh gives 1.
        # Unless we SET ex.last_status, scripts see it, so don't bother now.
        break

      if node is None:  # EOF
        display.EraseLines()
        # NOTE: We don't care about pending here docs in the interative case.
        done = True
        break

      display.EraseLines()  # Clear candidates right before executing

      is_control_flow, is_fatal = ex.ExecuteAndCatch(node)
      status = ex.LastStatus()
      if is_control_flow:  # e.g. 'exit' in the middle of a script
        done = True
        break
      if is_fatal:  # e.g. divide by zero 
        break

      break  # QUIT LOOP after one iteration.

    # Cleanup after every command (or failed command).

    # Reset internal newline state.
    c_parser.Reset()
    c_parser.ResetInputObjects()

    display.Reset()  # clears dupes and number of lines last displayed

    # TODO: Replace this with a shell hook?  with 'trap', or it could be just
    # like command_not_found.  The hook can be 'echo $?' or something more
    # complicated, i.e. with timetamps.
    if opts.print_status:
      print('STATUS', repr(status))

  if ex.MaybeRunExitTrap():
    return ex.LastStatus()
  else:
    return status  # could be a parse error


def Batch(ex, c_parser, arena, nodes_out=None):
  # type: (Any, CommandParser, Arena, Optional[List[command_t]]) -> Any
  """Loop for batch execution.

  Args:
    nodes_out: if set to a list, the input lines are parsed, and LST nodes are
      appended to it instead of executed.  For 'sh -n'.

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
    except util.ParseError as e:
      ui.PrettyPrintError(e, arena)
      status = 2
      break

    if nodes_out is not None:
      nodes_out.append(node)
      continue

    #log('parsed %s', node)

    is_control_flow, is_fatal = ex.ExecuteAndCatch(node)
    status = ex.LastStatus()
    # e.g. divide by zero or 'exit' in the middle of a script
    if is_control_flow or is_fatal:
      break

  if ex.MaybeRunExitTrap():
    return ex.LastStatus()
  else:
    return status  # could be a parse error


def ParseWholeFile(c_parser):
  # type: (CommandParser) -> command_t
  """Parse an entire shell script.

  This uses the same logic as Batch().
  """
  children = []
  while True:
    node = c_parser.ParseLogicalLine()  # can raise ParseError
    if node is None:  # EOF
      c_parser.CheckForPendingHereDocs()  # can raise ParseError
      break
    children.append(node)

  if len(children) == 1:
    return children[0]
  else:
    return command.CommandList(children)
