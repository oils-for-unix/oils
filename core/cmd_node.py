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

from core.tokens import Id, TokenTypeToName
from core.word_node import CommandWord
from core.base import _Node

# Types of the main command node.
ENode = util.Enum('ENode', """
SIMPLE_COMMAND ASSIGN PIPELINE AND_OR LIST BRACE_GROUP SUBSHELL FORK CASE IF
FOR FOR_EXPR WHILE UNTIL FUNCTION_DEF CASE DBRACKET DPAREN ELSE_TRUE 
""".split())


class CNode(_Node):
  """Abstract base class for CompositeNode/SimpleCommandNode/AssignmentNode.

  TODO: Rename to CNode
  """
  def __init__(self, type):
    self.type = type
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


class RedirectType(object):
  FILENAME = 0
  DESCRIPTOR = 1
  HERE_DOC = 2


class RedirectNode(object):
  """
  SimpleCommandNode and CompositeNode (function body or compound command) can
  have non-NULL redirect nodes.

  This is not an CNode since it can't be executed directly.
  TODO: Does it need self.word_start and self.word_end?  Probably.
  """
  def __init__(self, type, op, fd):
    """
    Args:
      type: node type
      op: Token, the operator
    """
    self.type = type
    self.op = op
    self.fd = fd

  def DebugString(self):
    return repr(self)

  def __repr__(self):
    f = io.StringIO()
    self.Print(f)
    return f.getvalue()

  def Print(self, f):
    f.write('(%s ' % self.__class__.__name__)
    self._PrintHeader(f)
    f.write(' %s' % self.op)
    #if self.fd != -1:
    f.write(' %s' % self.fd)
    f.write(')')


class HereDocRedirectNode(RedirectNode):
  """ << and <<- causes pipe()
  
  TODO: We need a flag to tell if the here end word is quoted!
  cat <<EOF vs cat <<'EOF' or cat <<"EOF"
  """

  def __init__(self, op):
    # stdin by default
    RedirectNode.__init__(self, RedirectType.HERE_DOC, op, 0)
    self.body_word = CommandWord()  # pseudo-word to be expanded
    self.here_end = None  # CommandWord 
    self.do_expansion = False
    #self.read_lines = False  # STATE: whether we read lines for this node yet
    self.was_filled = False  # STATE: whether we read lines for this node yet

  def _PrintHeader(self, f):
    f.write('here_end=%r do_expansion=%r body_word=%r' % (
      self.here_end, self.do_expansion, self.body_word))


class HereWordRedirectNode(RedirectNode):
  """ <<< and <<- causes pipe()
  
  TODO: We need a flag to tell if the here end word is quoted!
  cat <<EOF vs cat <<'EOF' or cat <<"EOF"
  """
  def __init__(self, op):
    # Use the same executor
    RedirectNode.__init__(self, RedirectType.HERE_DOC, op, 0)
    self.body_word = None

  def _PrintHeader(self, f):
    f.write('here_word=%r' % self.body_word)


class FilenameRedirectNode(RedirectNode):
  """ < > cause os.open() and then dup2()

  Also handle >> and maybe >|
  """
  def __init__(self, op):
    if op.val[0].isdigit():
      fd = int(op.val[0])
    else:
      if op.type in (Id.Redir_Great, Id.Redir_DGreat, Id.Redir_Clobber):
        fd = 1  # stdout
      elif op.type == Id.Redir_Less:
        fd = 0  # stdin
      else:  # < would be fd 0
        raise AssertionError
    RedirectNode.__init__(self, RedirectType.FILENAME, op, fd)
    self.filename = ''  # a word

  def _PrintHeader(self, f):
    f.write('filename=%s' % self.filename)


class DescriptorRedirectNode(RedirectNode):
  """ >& just causes dup2() """

  def __init__(self, op):
    if op.val[0].isdigit():
      fd = int(op.val[0])
    else:
      if op.type == Id.Redir_GreatAnd:
        fd = 1  # stdout
      elif op.type == Id.Redir_LessAnd:
        fd = 0  # stdout
      else:  # < would be fd 0
        raise AssertionError
    RedirectNode.__init__(self, RedirectType.DESCRIPTOR, op, fd)
    self.target_fd = -1

  def _PrintHeader(self, f):
    f.write('target=%s' % self.target_fd)


def _GetHereDocsToFill(redirects):
  return [
      r for r in redirects
      if r.op.type in (Id.Redir_DLess, Id.Redir_DLessDash) and not r.was_filled
      ]

class SimpleCommandNode(CNode):
  def __init__(self):
    CNode.__init__(self, ENode.SIMPLE_COMMAND)
    self.words = []  # CommandWord instances
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
      self._PrintTreeRedirects(f, indent=indent+2)
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


class ElseTrueNode(CNode):
  """Dummy node for the empty "else" condition."""
  def __init__(self):
    CNode.__init__(self, ENode.ELSE_TRUE)

  def PrintLine(self, f):
    f.write('(ElseTrue)')


class AssignmentNode(CNode):
  def __init__(self, scope, flags):
    CNode.__init__(self, ENode.ASSIGN)
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
    CNode.__init__(self, ENode.DBRACKET)
    self.bnode = bnode  # type: _BNode

  def PrintLine(self, f):
    f.write('(DBracket ')
    f.write('%s' % self.bnode)
    f.write(')')


class DParenNode(CNode):
  """Represents a top level (( expression."""
  def __init__(self, anode):
    CNode.__init__(self, ENode.DPAREN)
    self.anode = anode # type: _ANode

  def PrintLine(self, f):
    f.write('(DParen ')
    f.write('%s' % self.anode)
    f.write(')')


class CompositeNode(CNode):
  def __init__(self, type):
    CNode.__init__(self, type)
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
    return self.type == other.type and self.children == other.children


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

class ListNode(CompositeNode):
  """
  For BraceGroup, function body, case item, etc.

  children: list of AND_OR
  """
  def __init__(self):
    CompositeNode.__init__(self, ENode.LIST)
    self.redirects = []

  def _PrintHeader(self, f):
    f.write('List')
    if self.redirects:
      f.write(' redirects=')
      f.write(str(self.redirects))


class SubshellNode(CompositeNode):
  """
  children: either list of AND_OR, or a LIST node?

  Exec() is different I guess
  """
  def __init__(self):
    CompositeNode.__init__(self, ENode.SUBSHELL)
    # no redirects for subshell?

  def _PrintHeader(self, f):
    f.write('Subshell')


class ForkNode(CompositeNode):
  """
  children: either list of AND_OR, or a LIST node?
  """
  def __init__(self):
    CompositeNode.__init__(self, ENode.FORK)

  def _PrintHeader(self, f):
    f.write('Fork')


class PipelineNode(CompositeNode):
  """
  children: list of SimpleCommandNode
  """
  def __init__(self, children, negated):
    CompositeNode.__init__(self, ENode.PIPELINE)
    self.children = children
    self.negated = negated
    # If there are 3 children, they are numbered 0, 1, and 2.  There are two
    # pipes -- 0 and 1.  This list contains the pipe numbers that are |& rather
    # than |.  We are optimizing for the common case.
    self.stderr_indices = []

  def _PrintHeader(self, f):
    f.write('Pipeline%s' % ('!' if self.negated else '',))


class AndOrNode(CompositeNode):
  """
  children[0]: LHS
  children[1]: RHS
  """
  def __init__(self, op):
    CompositeNode.__init__(self, ENode.AND_OR)
    self.op = op # TokenType AND_IF or OR_IF, set by parser

  def _PrintHeader(self, f):
    f.write('AndOr %s' % TokenTypeToName(self.op))


class ForNode(CompositeNode):
  """
  children: list of AND_OR?
  """

  def __init__(self):
    CompositeNode.__init__(self, ENode.FOR)
    self.iter_name = None 
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


class ForExpressionNode(CompositeNode):
  """
  children: list of AND_OR?
  """
  def __init__(self, init, cond, update):
    CompositeNode.__init__(self, ENode.FOR_EXPR)
    self.init = init  # type: ANode
    self.cond = cond  # type: ANode
    self.update = update  # type: ANode

  def _PrintHeader(self, f):
    # TODO: Put these on separate lines
    f.write('ForExpr %s %s %s' % (self.init, self.cond, self.update))


class WhileNode(CompositeNode):
  """
  children[0] = condition (LIST)
  children[1] = body (LIST)
  """
  def __init__(self, children):
    CompositeNode.__init__(self, ENode.WHILE)
    self.children = children

  def _PrintHeader(self, f):
    f.write('While')


class UntilNode(CompositeNode):
  """
  children[0] = condition (LIST)
  children[1] = body (LIST)
  """
  def __init__(self, children):
    CompositeNode.__init__(self, ENode.UNTIL)
    self.children = children

  def _PrintHeader(self, f):
    f.write('Until')


class FunctionDefNode(CompositeNode):
  """
  children = statement body
  """
  def __init__(self):
    CompositeNode.__init__(self, ENode.FUNCTION_DEF)
    self.name = ''
    self.redirects = []

  def _PrintHeader(self, f):
    f.write('FunctionDef %s %s' % (self.name, self.redirects))


class IfNode(CompositeNode):
  """
  children = condition, action, condition, action

  Last condition is TRUE for else!!!
  """
  def __init__(self):
    CompositeNode.__init__(self, ENode.IF)

  def _PrintHeader(self, f):
    f.write('If')


class CaseNode(CompositeNode):
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
    CompositeNode.__init__(self, ENode.CASE)
    # the word to match against successive patterns
    self.to_match = None  # type: Word
    self.pat_word_list = []  # List<List<Word>> -- patterns to match

  def _PrintHeader(self, f):
    # TODO: Since pat_word_list is parallel to children, it should be printed
    # on multiple lines!
    f.write('Case to_match=%s, pat_word_list=%s' % (self.to_match,
      self.pat_word_list))

