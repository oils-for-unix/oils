#!/usr/bin/env python3
"""
util_test.py: Tests for util.py
"""

import unittest

import util  # module under test


class _Parser(object):
  """Test class for tracing."""

  def __init__(self, lexer):
    self.lexer = lexer

  def ParseTrailer(self, node):
    return 'trailer'

  def ParseCommandTerm(self, node):
    return 'term'

  def ParseCommandList(self, node):
    self.ParseCommandTerm(node)
    return self.ParseTrailer(node)


class TraceTest(unittest.TestCase):

  def testWrapMethods(self):
    state = util.TraceState()
    # TODO: Fix UnboundMethodType error
    return
    util.WrapMethods(_Parser, state)
    p = _Parser('lexer')
    print(p.ParseCommandList({}))


class EnumTest(unittest.TestCase):

  def testEnum(self):
    Color = util.Enum('Color', 'red green blue'.split())
    print(Color._values)
    print(Color._lookup)

    Color = util.Enum('Color', ['red', ('green', 3), 'blue'])
    print(Color._values)
    print(Color._lookup)

    print(Color.red)
    print(Color.green)
    try:
      print(Color.BAD)
    except AttributeError as e:
      self.assertEqual('BAD', e.args[0])
    else:
      self.fail("Expected error")

    self.assertEqual(Color.red, Color.red)
    self.assertNotEqual(Color.red, Color.green)

    self.assertEqual(Color.red, 0)
    self.assertEqual(Color.blue, 4)
    try:
      print(Color.blue == '')
    except ValueError as e:
      pass
    else:
      self.fail("Expected error")


if __name__ == '__main__':
  unittest.main()
