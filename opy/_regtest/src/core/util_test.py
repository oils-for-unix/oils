#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
util_test.py: Tests for util.py
"""

import unittest

from core import util  # module under test


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


if __name__ == '__main__':
  unittest.main()
