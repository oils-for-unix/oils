#!/usr/bin/python
from __future__ import print_function
"""
main_loop.py

main_loop.Interactive()
main_loop.Batch()

They should call 

ex.ExecuteOne() -- and catch FatalRuntimeError or ControlFlow?

For interactive, you keep going on an error, but exit on 'exit'

For batch, you fail at the first error

Get rid of:

ex.Execute() -- used for ExitTrap
ex.ExecuteAndCatch()
ParseWholeFile -- needs to check the here doc.
"""

from core import ui
from core import util

log = util.log


def Interactive(opts, ex, c_parser, arena):
  status = 0
  while True:
    # Reset internal newline state.  NOTE: It would actually be correct to
    # reinitialize all objects (except Env) on every iteration.
    c_parser.Reset()
    c_parser.ResetInputObjects()

    try:
      node = c_parser.ParseOne()
    except util.ParseError as e:
      ui.PrettyPrintError(e, arena)
      # NOTE: This should set the status interactively!  Bash does this.
      status = 2
      continue

    if node is None:  # EOF
      # NOTE: We don't care if there are pending here docs in the interative case.
      break

    is_control_flow, is_fatal = ex.ExecuteAndCatch(node)
    status = ex.LastStatus()
    if is_control_flow:  # e.g. 'exit' in the middle of a script
      break
    if is_fatal:  # e.g. divide by zero 
      continue

    if opts.print_status:
      print('STATUS', repr(status))

  if ex.MaybeRunExitTrap():
    return ex.LastStatus()
  else:
    return status  # could be a parse error


def Batch(opts, ex, c_parser, arena, nodes_out=None):
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
      node = c_parser.ParseOne()  # can raise ParseError
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
