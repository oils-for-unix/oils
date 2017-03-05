#!/usr/bin/env python3
"""
base.py -- Common base classes.
"""

import io
import sys


# NOTE: These aren't really necessary in Python.  I'm keeping them for now
# because I might want to have an ErrorState class that
# {arith,bool,word,cmd}_parse.py can share.  Composition over inheritance.

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

  Do all of them have access to a arena_ / arena_ ?  For creating new objects
  and looking them up with IDs.
  """
  def __init__(self, arena):
    # The arena is used to allocate nodes and clear them all at once.  The
    # Reader needs to allocate lines; the Lexer needs to allocate tokens.
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


class ParseError:
  """A parse error that can be formatted.

  Formatting is in ui.PrintError.
  """
  def __init__(self, msg, *args, token=None, word=None):
    self.msg = msg
    self.args = args
    self.token = token
    self.word = word

  def UserErrorString(self):
    return self.msg % self.args
