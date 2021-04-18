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
cp5o_test.py: Tests for cp5o.py
"""
import unittest
import socket
import sys

import cp5o


def netstring_encode(s):
  return b'%d:%s,' % (len(s), s)


class cp5oTest(unittest.TestCase):

  def testSend(self):
    print('___ c5po.send ___')
    left, right = socket.socketpair()
    print(left)
    print(right)

    print(cp5o.send(left.fileno(), b'foo'))
    print(cp5o.send(left.fileno(), b'bar', 
      sys.stdin.fileno(), sys.stdout.fileno(), sys.stderr.fileno()))

    # Read what we wrote
    received = right.recv(20)
    print(received)

  def testReceive(self):
    print('___ c5po.receive ___')
    left, right = socket.socketpair()

    if 1:
      left.send(netstring_encode('spam'))

      fd_out = []
      msg = cp5o.receive(right.fileno(), fd_out)
      print("msg = %r" % msg)
      print('fd_out = %s' % fd_out)
      return

    # This is OK
    left.send(b'000001234:foo,')

    # This is too long
    # left.send(b'0000012345:foo,')

    fd_out = []
    msg = cp5o.receive(right.fileno(), fd_out)
    print("msg = %r" % msg)
    print('fd_out = %s' % fd_out)



if __name__ == '__main__':
  unittest.main()
