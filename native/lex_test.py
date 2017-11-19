#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
libc_test.py: Tests for libc.py
"""

import unittest

import lex # module under test


class LexTest(unittest.TestCase):

  def testFnmatch(self):
    print(dir(lex))


if __name__ == '__main__':
  unittest.main()
