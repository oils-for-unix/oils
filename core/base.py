#!/usr/bin/python3
"""
base.py - Common base classes.
"""

import io
import sys


class _Parser(object):
  """
  A recursive parser needs to keep track of error messages.

  fields:
    - format string, args
    - token number -- which can point to line and column?  Or has to be
      computed.
      - or is it a range of errors?
      - maybe an error can be associated with any kind of entity: CNode,
        ExprNode, etc. Word, WordPart.  And if there is a range of tokens, then
        those will be highlighted.

  And we also have to keep state across multiple parsers.

  Do all of them have access to a pool_ / arena_ ?  For creating new objects
  and looking them up with IDs.
  """
  def __init__(self, arena):
    # The arena is used to serialize the tree quickly?  And make sure every
    # node has a number?
    #
    # It can also be used in the interactive REPL to clear everything...
    # although honestly it will take a trivial amount of time to follow like
    # 100 pointers max and delete them.
    #
    # Well it lets you "forget" about some of them?  Although I guess every
    # word should be owned by node, and every WordPart is owned by a node.  Hm.
    # And token are passed by value, so you can forget them.  Hm.
    self.arena = arena

  def AddErrorContext(self):
    pass

  def Error(self):  # get error
    pass


class _Evaluator(object):
  """
  An recursive evaluator has to throw exceptions:

    arith:        divide by zero, overflow
    bool:         type mismatch: 1 -eq z
    cmd executor: errexit, pipefail, etc.
    word:         $hi'foo'"hi${}"
                  ${var?error}

  And should there be a unified stack trace system?
  """

  def AddErrorContext(self):
    pass

  def Error(self):  # Get error
    pass


def MakeError(msg, *args, token=None, word=None):
  """Common function to make an error."""
  if args:
    msg = msg % args

  if token and word:
    raise AssertionError('Only one error location can be specified')

  if token:
    near_token = token
  elif word:
    from core.word import ParseErrorLocation
    near_token = ParseErrorLocation(word)
    #print('NEAR TOKEN', near_token)

    # TODO: Change this to LocationPair()?  It could be a single location or
    # multiple locations?  Put it in word.py?  Or somewhere else?  I think you
    # implement runtime errors in addition to parse time errors first.
  else:
    near_token = None

  return (near_token, msg)

