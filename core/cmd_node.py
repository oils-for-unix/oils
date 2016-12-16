#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
cmd_node.py -- AST Nodes for the command language
"""

import io

from core import util

from core.id_kind import Id, IdName
from core.word_node import CompoundWord
from core.base import _Node


class CNode(_Node):
  """Abstract base class for _CompoundCNode/SimpleCommandNode/AssignmentNode."""

  def __init__(self, id):
    _Node.__init__(self, id)
    self.redirects = []  # common to almost all nodes

    # TODO: Fill these out.  BUT: We need ordering info.  If we have < and
    # <<EOF on the same line.
    self.here_docs = []

    self.word_start = -1  # 1-based index into words
    self.word_end = -1

  def GetHereDocsToFill(self):
    """For CommandParser to fill here docs"""
    # By default, there are no here docs (e.g. AssignmentNode.)
    return []

  def _PrintLineRedirects(self, f):
    if self.redirects:
      f.write('redirects=[')
      for i, r in enumerate(self.redirects):
        if i != 0:
          f.write(' ')
        f.write(repr(r))
      f.write(']')

  def _PrintTreeRedirects(self, f, indent=0):
    ind = indent * ' '
    if self.redirects:
      f.write(ind)
      f.write('<\n')
      for r in self.redirects:
        f.write(ind)
        f.write(repr(r))
        f.write(',\n')
      f.write(ind)
      f.write('>\n')


class RedirNode(_Node):
  """
  SimpleCommandNode and _CompoundCNode (function body or compound command) can
  have non-NULL redirect nodes.

  This is not an CNode since it can't be executed directly.
  TODO: Does it need self.word_start and self.word_end?  Probably.

  TODO: base class _Node
  """
  def __init__(self, id, fd):
    """
    Args:
      id: The actual ID
      fd: the fd that occurs before the operator, e.g. 1 in 1>&2.
        DescriptorRedirNode has another descriptor AFTER the operator.
    """
    _Node.__init__(self, id)
    self.fd = fd
    self.arg_word = None  # CompoundWord

  def DebugString(self):
    return repr(self)

  def __repr__(self):
    f = io.StringIO()
    self.Print(f)
    return f.getvalue()

  def _PrintHeader(self, f):
    # No extra metadata?
    pass

  def Print(self, f):
    f.write('(%s ' % self.__class__.__name__)
    self._PrintHeader(f)

    # TODO: This word can be huge
    f.write(' %s' % self.arg_word)

    #if self.fd != -1:
    f.write(' %s' % self.fd)
    f.write(')')


class HereDocNode(RedirNode):
  """ << and <<- cause pipe()
  """
  def __init__(self, id, fd):
    # stdin by default
    RedirNode.__init__(self, id, fd)
    self.do_expansion = False
    # NOTE: These two can be dropped for execution.  here_end and was_filled
    # not needed after parsing. 
    self.here_end = None  # CompoundWord
    self.was_filled = False  # STATE: whether we read lines for this node yet

  def _PrintHeader(self, f):
    f.write('here_end=%r do_expansion=%r' % (
      self.here_end, self.do_expansion))


def _GetHereDocsToFill(redirects):
  return [
      r for r in redirects
      if r.id in (Id.Redir_DLess, Id.Redir_DLessDash) and not r.was_filled
  ]


class SimpleCommandNode(CNode):
  def __init__(self):
    CNode.__init__(self, Id.Node_Command)
    self.words = []  # CompoundWord instances
    self.more_env = {}  # binding

  def GetHereDocsToFill(self):
    """For CommandParser to fill here"""
    return _GetHereDocsToFill(self.redirects)

  def PrintLine(self, f):
    f.write('(Com ')
    self._PrintLineRedirects(f)
    if self.more_env:
      # NOTE: This gives a {a:b, c:d} format.
      f.write('more_env=%s ' % self.more_env)
    for i, w in enumerate(self.words):
      if i != 0:
        f.write(' ')
      w.PrintLine(f)
    f.write(')')

  def PrintTree(self, f, indent=0):
    ind = indent * ' '
    f.write(ind)
    f.write('(Com ')
    # Print words, space-separated
    for i, w in enumerate(self.words):
      if i != 0:
        f.write(' ')
      w.PrintLine(f)  # PrintTree for ComSub and so forth?  nodes?
    if self.redirects:
      f.write('\n')
      self._PrintTreeRedirects(f, indent=indent + 2)
    if self.more_env:
      # NOTE: This gives a {a:b, c:d} format.
      f.write('\n')
      f.write(ind)
      f.write(ind)  # 2 indents
      f.write('more_env=%s\n' % self.more_env)
    multiline = bool(self.redirects) or bool(self.more_env)
    if multiline:
      f.write(ind)
    f.write(')')


class NoOpNode(CNode):
  """Dummy node for the empty "else" condition."""
  def __init__(self):
    CNode.__init__(self, Id.Node_NoOp)

  def PrintLine(self, f):
    f.write('(ElseTrue)')


class AssignmentNode(CNode):
  def __init__(self, scope, flags):
    CNode.__init__(self, Id.Node_Assign)
    self.scope = scope
    self.flags = flags
    # readonly foo bar=baz is allowed.  We separate them here.  Order
    # information is not preserved.
    self.words = []
    self.bindings = {}

  def PrintLine(self, f):
    f.write('(= ')
    f.write('scope=%s ' % self.scope)
    f.write('flags=%s ' % self.flags)
    f.write('words=%s ' % self.words)
    f.write('bindings=%s' % self.bindings)
    f.write(')')


class DBracketNode(CNode):
  """Represents a top level [[ expression."""
  def __init__(self, bnode):
    CNode.__init__(self, Id.KW_DLeftBracket)
    self.bnode = bnode  # type: _BNode

  def PrintLine(self, f):
    f.write('(DBracket ')
    f.write('%s' % self.bnode)
    f.write(')')


class DParenNode(CNode):
  """Represents a top level (( expression."""
  def __init__(self, anode):
    CNode.__init__(self, Id.Op_DLeftParen)
    self.anode = anode  # type: _ExprNode

  def PrintLine(self, f):
    f.write('(DParen ')
    f.write('%s' % self.anode)
    f.write(')')


# NOTE: This has N children, instead of a fixed 0, 1, or 2.
class _CompoundCNode(CNode):
  def __init__(self, id):
    CNode.__init__(self, id)
    # children of type CNode.
    self.children = []

  def GetHereDocsToFill(self):
    """For CommandParser to fill here docs"""
    # Has to be a POST ORDER TRAVERSAL of here docs, e.g.
    #
    # while read line; do cat <<EOF1; done <<EOF2
    # body
    # EOF1
    # while
    # EOF2
    here_docs = []
    for child in self.children:
      here_docs.extend(child.GetHereDocsToFill())
    here_docs.extend(_GetHereDocsToFill(self.redirects))
    return here_docs

  def _PrintHeader(self, f):
    """Print node name and node-specifc values."""
    raise NotImplementedError(self.__class__.__name__)

  def PrintTree(self, f, indent=0):
    f.write(indent * ' ' + '(')
    self._PrintHeader(f)
    f.write('\n')
    for c in self.children:
      c.PrintTree(f, indent=indent + 2)
      f.write('\n')
    f.write(indent * ' ' + ')')

  def PrintLine(self, f):
    # All on a single line.  No newlines, and don't respect indent.
    f.write('(')
    self._PrintHeader(f)
    f.write(' ')
    for c in self.children:
      c.PrintLine(f)
      f.write(' ')
    f.write(')')

  def __eq__(self, other):
    # TODO: Switch on the type too!  Check all the extra info for each node
    # type.
    return self.id == other.id and self.children == other.children


# TODO:
# - Where does & for async go?  # Can you make whole functions async.  Yes.  I
# guess pipelines and AND_OR can be too?
#   - you could have an entire ASYNC node, which is different than the parse
#     tree.  Hm.  Sort of like a separate BANG node?  Might be easier for
#     execution this way.
#
# Unary nodes, that operate on lists...
#   BANG
#   ASYNC -- fork interpreter for composite, and don't wait.
#   REDIRECT -- does this require forking for compound commands?
#     - or does it just require state before and after?
#     - Because ANY compound command can have redirects.  for/while/if/{}
#
# Problem: What's convenient for execution is inconvenient for shell -> oil
# translation.
# - Well I think losing "until" loops might actually be OK!
#
# - Write __repr__ and __eq__ for every node, for testing
#   - in C++, the debug string will serve as the tests!  multi-language tests.

# NOTE: The ANTLR book has all nodes of separate types, but ALSO separate token
# types.  There are two ways to switch on it.

class ListNode(_CompoundCNode):
  """
  For BraceGroup, function body, case item, etc.

  children: list of AND_OR
  """
  def __init__(self):
    _CompoundCNode.__init__(self, Id.Op_Semi)

  def _PrintHeader(self, f):
    f.write('List')
    if self.redirects:
      f.write(' redirects=')
      f.write(str(self.redirects))


class SubshellNode(_CompoundCNode):
  """
  children: either list of AND_OR, or a LIST node?

  Exec() is different I guess
  """
  def __init__(self):
    _CompoundCNode.__init__(self, Id.Node_Subshell)
    # no redirects for subshell?

  def _PrintHeader(self, f):
    f.write('Subshell')


class ForkNode(_CompoundCNode):
  """
  children: either list of AND_OR, or a LIST node?
  """
  def __init__(self):
    _CompoundCNode.__init__(self, Id.Node_Fork)

  def _PrintHeader(self, f):
    f.write('Fork')


class PipelineNode(_CompoundCNode):
  """
  children: list of SimpleCommandNode
  """
  def __init__(self, children, negated):
    _CompoundCNode.__init__(self, Id.Op_Pipe)
    self.children = children
    self.negated = negated
    # If there are 3 children, they are numbered 0, 1, and 2.  There are two
    # pipes -- 0 and 1.  This list contains the pipe numbers that are |& rather
    # than |.  We are optimizing for the common case.
    self.stderr_indices = []

  def _PrintHeader(self, f):
    f.write('Pipeline%s' % ('!' if self.negated else '',))


class AndOrNode(_CompoundCNode):
  """
  children[0]: LHS
  children[1]: RHS
  """
  def __init__(self, op):
    _CompoundCNode.__init__(self, Id.Node_AndOr)
    self.op = op  # TokenType Op_DAmp or Op_DPipe, set by parser

  def _PrintHeader(self, f):
    f.write('AndOr %s' % IdName(self.op))


class ForNode(_CompoundCNode):
  """
  children: list of AND_OR?
  """

  def __init__(self):
    _CompoundCNode.__init__(self, Id.Node_ForEach)
    self.iter_name = None  # type: str
    self.iter_words = []  # can be empty explicitly empty, which is dumb
    # whether we should iterate over args; iter_words should be empty
    self.do_arg_iter = False

  def _PrintHeader(self, f):
    f.write('For %s' % self.iter_name)
    if self.do_arg_iter:
      f.write(' do_arg_iter')
    else:
      f.write(' %s' % self.iter_words)
    f.write(')')


class ForExpressionNode(_CompoundCNode):
  """
  children: list of AND_OR?
  """
  def __init__(self, init, cond, update):
    _CompoundCNode.__init__(self, Id.Node_ForExpr)
    self.init = init  # type: ExprNode
    self.cond = cond  # type: ExprNode
    self.update = update  # type: ExprNode

  def _PrintHeader(self, f):
    # TODO: Put these on separate lines
    f.write('ForExpr %s %s %s' % (self.init, self.cond, self.update))


class WhileNode(_CompoundCNode):
  """
  children[0] = condition (LIST)
  children[1] = body (LIST)
  """
  def __init__(self, children):
    _CompoundCNode.__init__(self, Id.KW_While)
    self.children = children

  def _PrintHeader(self, f):
    f.write('While')


class UntilNode(_CompoundCNode):
  """
  children[0] = condition (LIST)
  children[1] = body (LIST)
  """
  def __init__(self, children):
    _CompoundCNode.__init__(self, Id.KW_Until)
    self.children = children

  def _PrintHeader(self, f):
    f.write('Until')


class FunctionDefNode(_CompoundCNode):
  """
  children = statement body
  """
  def __init__(self):
    _CompoundCNode.__init__(self, Id.Node_FuncDef)
    self.name = ''

  def _PrintHeader(self, f):
    f.write('FunctionDef %s %s' % (self.name, self.redirects))


class IfNode(_CompoundCNode):
  """
  children = condition, action, condition, action

  Last condition is TRUE for else!!!
  """
  def __init__(self):
    _CompoundCNode.__init__(self, Id.KW_If)

  def _PrintHeader(self, f):
    f.write('If')


class CaseNode(_CompoundCNode):
  """
  Representation:
    pat_word_list = patterns to match, a list parallel to 'children'
    children = CNodes to execute

  This representation makes it easier to write homogeneous walkers.

  Alternatively, we could represent the patterns as a boolean expression, like:

  case $v in foo|bar) echo match ;; *) echo nope ;; esac

  # Also does this force evaluation differently?
  if (v ~ Glob/foo/ or v ~ Glob/bar/) {
    echo match
  } else {
    echo nope
  }
  """
  def __init__(self):
    _CompoundCNode.__init__(self, Id.KW_Case)
    # the word to match against successive patterns
    self.to_match = None  # type: Word
    self.pat_word_list = []  # List<List<Word>> -- patterns to match

  def _PrintHeader(self, f):
    # TODO: Since pat_word_list is parallel to children, it should be printed
    # on multiple lines!
    f.write('Case to_match=%s, pat_word_list=%s' % (self.to_match,
      self.pat_word_list))
