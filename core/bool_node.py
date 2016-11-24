#!/usr/bin/python
"""
bool_node.py - AST Nodes for boolean expressions
"""

from core.base import _Node
from core.tokens import Id, IdName

#
# BNode
#

class _BNode(_Node):
  """Abstract base class for internal nodes of a [[ expresion.

  It is an _Node because it has tokens/words to point to?
  """
  def __init__(self, btype):
    _Node.__init__(self, 'TODO:get rid of')
    self.btype = btype

  def PrintLine(self, f):
    raise NotImplementedError  # Abstract


class NotBNode(_BNode):
  """ ! """
  def __init__(self, child):
    _BNode.__init__(self, Id.KW_Bang)
    self.child = child  # type: _BNode

  def PrintLine(self, f):
    f.write('{B! ')
    f.write(str(self.child))
    f.write('}')


class LogicalBNode(_BNode):
  """ && and || """
  def __init__(self, btype, left, right):
    _BNode.__init__(self, btype)
    self.left = left  # type: _BNode
    self.right = right  # type: _BNode

  def PrintLine(self, f):
    f.write('{B? ')
    f.write('%s %s %s' % (IdName(self.btype), self.left, self.right))
    f.write('}')


class UnaryBNode(_BNode):
  """ -z -n

  Note that the word itself is parsed as -n
  """
  def __init__(self, btype, word):
    _BNode.__init__(self, btype)
    self.word = word  # type: CompoundWord

  def PrintLine(self, f):
    f.write('{B1 ')
    f.write('%s %s' % (IdName(self.btype), self.word))
    f.write('}')


class BinaryBNode(_BNode):
  """
  ==, == as a GLOB with RHS detected at parse time, -gt for integers, -ot for
  files
  """
  def __init__(self, btype, left, right):
    _BNode.__init__(self, btype)
    self.left = left  # type: CompoundWord
    self.right = right  # type: CompoundWord

  def PrintLine(self, f):
    f.write('{B2 ')
    f.write('%s %s %s' % (IdName(self.btype), self.left, self.right))
    f.write('}')
