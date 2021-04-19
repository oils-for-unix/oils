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
nuds_test.py: Tests for nuds.c
"""
import unittest
import socket
import sys

from core.pyerror import log

import nuds  # module under test


def netstring_encode(s):
  return b'%d:%s,' % (len(s), s)


def netstring_recv(sock):
  """Plain decoder that IGNORES file descriptors.

  Using pure Python libs is a useful sanity check on the protocol.
  (Python 2 doesn't have recvmsg()).
  """
  len_buf = []
  while True:
    byte = sock.recv(1)
    #log('byte = %r', byte)

    if len(byte) == 0:
      raise RuntimeError('Expected a netstring length byte')

    if byte == b':':
      break

    if b'0' <= byte and byte <= b'9':
      len_buf.append(byte)
    else:
      raise RuntimeError('Invalid netstring length byte %r' % byte)

  num_bytes = int(b''.join(len_buf))
  log('num_bytes = %d', num_bytes)

  # +1 for the comma
  n = num_bytes
  msg = b''
  #fd_list = []

  while n > 0:
    chunk = sock.recv(n)
    log("chunk %r", chunk)

    msg += chunk
    n -= len(chunk)

    if len(msg) == n:
      break

  byte = sock.recv(1)
  if byte != b',':
    raise RuntimeError('Expected ,')

  return msg


class nudsTest(unittest.TestCase):

  def testSend(self):
    """Send with our cp50 library; receive with Python stdlib."""

    print('\n___ c5po.send ___')
    left, right = socket.socketpair()
    print(left)
    print(right)

    print(nuds.send(left.fileno(), b'foo'))
    print(nuds.send(left.fileno(), b'https://www.oilshell.org/', 
      sys.stdin.fileno(), sys.stdout.fileno(), sys.stderr.fileno()))

    msg = netstring_recv(right)
    self.assertEqual('foo', msg)
    msg = netstring_recv(right)
    self.assertEqual('https://www.oilshell.org/', msg)

  def testRecv(self):
    """Send with Python; received our cp50 library"""
    print('\n___ c5po.recv ___')
    left, right = socket.socketpair()

    left.send(netstring_encode('spam'))

    fd_out = []
    msg = nuds.recv(right.fileno(), fd_out)
    self.assertEqual('spam', msg)
    print("msg = %r" % msg)
    print('fd_out = %s' % fd_out)

    left.send(netstring_encode('eggs-eggs-eggs'))

    msg = nuds.recv(right.fileno(), fd_out)
    self.assertEqual('eggs-eggs-eggs', msg)
    print("py msg = %r" % msg)
    print('fd_out = %s' % fd_out)

  def testRecvErrors(self):
    left, right = socket.socketpair()

    # TODO: test invalid netstring cases
    # Instead of RuntimeError they sould be nuds.error?
    # Instead of 'OK' you return
    # 'nuds ERROR: Invalid netstring'

    # This is OK
    left.send(b'000000003:foo,')

    fd_out = []
    msg = nuds.recv(right.fileno(), fd_out)
    print("msg = %r" % msg)
    print('fd_out = %s' % fd_out)

    # This is too long
    left.send(b'0000000003:foo,')

    try:
      msg = nuds.recv(right.fileno(), fd_out)
    except ValueError:
      pass
    else:
      self.fail('Expected ValueError')

    print("msg = %r" % msg)
    print('fd_out = %s' % fd_out)

  def testSendRecv(self):
    """Send and receive with our cp50 library"""
    print('\n___ testSendReceive ___')

    left, right = socket.socketpair()

    print(nuds.send(left.fileno(), b'foo'))
    print(nuds.send(left.fileno(), b'https://www.oilshell.org/', 
      sys.stdin.fileno(), sys.stdout.fileno(), sys.stderr.fileno()))

    fd_out = []
    msg = nuds.recv(right.fileno(), fd_out)
    self.assertEqual('foo', msg)
    self.assertEqual([], fd_out)
    print("py msg = %r" % msg)
    print('fd_out = %s' % fd_out)

    del fd_out[:]
    msg = nuds.recv(right.fileno(), fd_out)
    self.assertEqual('https://www.oilshell.org/', msg)
    self.assertEqual(3, len(fd_out))

    print("py msg = %r" % msg)
    print('fd_out = %s' % fd_out)


if __name__ == '__main__':
  unittest.main()
