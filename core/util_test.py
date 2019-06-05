#!/usr/bin/env python2
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


class UtilTest(unittest.TestCase):

  def testLog(self):
    util.log('hello %d', 42)


if __name__ == '__main__':
  unittest.main()
