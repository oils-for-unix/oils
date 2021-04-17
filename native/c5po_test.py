#!/usr/bin/env python2
# coding=utf8
# Copyright 2021 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
c5po_test.py: Tests for c5po.py
"""
import unittest
import socket
import sys

import c5po

class c5poTest(unittest.TestCase):

  def testSend(self):
    left, right = socket.socketpair()
    print(left)
    print(right)

    print(c5po.receive(42))
    print(c5po.send(0, b'foo'))


if __name__ == '__main__':
  unittest.main()
