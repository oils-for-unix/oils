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
fanos_test.py: Tests for fanos.c
"""
import errno
import socket
import sys
import unittest

from mycpp.mylib import log

import fanos  # module under test


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


class FanosTest(unittest.TestCase):

  def testSend(self):
    """Send with our fanos library; receive with Python stdlib."""

    print('\n___ fanos.send ___')
    left, right = socket.socketpair()
    print(left)
    print(right)

    print(fanos.send(left.fileno(), b'foo'))
    print(fanos.send(left.fileno(), b'https://www.oilshell.org/', 
      sys.stdin.fileno(), sys.stdout.fileno(), sys.stderr.fileno()))

    msg = netstring_recv(right)
    self.assertEqual('foo', msg)
    msg = netstring_recv(right)
    self.assertEqual('https://www.oilshell.org/', msg)

  def testRecv(self):
    """Send with Python; received our fanos library"""
    print('\n___ fanos.recv ___')
    left, right = socket.socketpair()

    left.send(netstring_encode('spam'))

    fd_out = []
    msg = fanos.recv(right.fileno(), fd_out)
    self.assertEqual('spam', msg)
    print("msg = %r" % msg)
    print('fd_out = %s' % fd_out)

    left.send(netstring_encode('eggs-eggs-eggs'))

    msg = fanos.recv(right.fileno(), fd_out)
    self.assertEqual('eggs-eggs-eggs', msg)
    print("py msg = %r" % msg)
    print('fd_out = %s' % fd_out)

    # Empty string
    left.send(netstring_encode(''))

    msg = fanos.recv(right.fileno(), fd_out)
    self.assertEqual('', msg)
    print("py msg = %r" % msg)
    print('fd_out = %s' % fd_out)

  def testIOErrors(self):
    try:
      fanos.send(99, b'foo')
    except IOError as e:
      print(e)
      print(type(e))
      self.assertEqual(errno.EBADF, e.errno)
    else:
      self.fail('Expected IOError')

    try:
      result = fanos.recv(99, [])
    except IOError as e:
      print(e)
      print(type(e))
      self.assertEqual(errno.EBADF, e.errno)
    else:
      self.fail('Expected IOError')

  def testRecvErrors(self):
    left, right = socket.socketpair()

    # TODO: test invalid netstring cases
    # Instead of RuntimeError they should be fanos.error?
    # Instead of 'OK' you return
    # 'fanos ERROR: Invalid netstring'

    # This is OK
    left.send(b'000000003:foo,')

    fd_out = []
    msg = fanos.recv(right.fileno(), fd_out)
    print("msg = %r" % msg)
    print('fd_out = %s' % fd_out)

    # This is too long
    left.send(b'0000000003:foo,')

    try:
      msg = fanos.recv(right.fileno(), fd_out)
    except ValueError:
      pass
    else:
      self.fail('Expected ValueError')

    print("msg = %r" % msg)
    print('fd_out = %s' % fd_out)

  def testSendRecv(self):
    """Send and receive with our fanos library"""
    print('\n___ testSendReceive ___')

    left, right = socket.socketpair()

    print(fanos.send(left.fileno(), b'foo'))
    print(fanos.send(left.fileno(), b'https://www.oilshell.org/', 
      sys.stdin.fileno(), sys.stdout.fileno(), sys.stderr.fileno()))

    fd_out = []
    msg = fanos.recv(right.fileno(), fd_out)
    self.assertEqual('foo', msg)
    self.assertEqual([], fd_out)
    print("py msg = %r" % msg)
    print('fd_out = %s' % fd_out)

    del fd_out[:]
    msg = fanos.recv(right.fileno(), fd_out)
    self.assertEqual('https://www.oilshell.org/', msg)
    self.assertEqual(3, len(fd_out))

    print("py msg = %r" % msg)
    print('fd_out = %s' % fd_out)

    left.close()
    msg = fanos.recv(right.fileno(), fd_out)
    self.assertEqual(None, msg)  # Valid EOF

    right.close()


class InvalidMessageTests(unittest.TestCase):
  """COPIED from py_fanos_test.py."""

  def testInvalidColon(self):
    fd_out = []
    left, right = socket.socketpair()

    left.send(b':')  # Should be 3:foo,
    try:
      msg = fanos.recv(right.fileno(), fd_out)
    except ValueError as e:
      print(type(e))
      print(e)
    else:
      self.fail('Expected failure')

    left.close()
    right.close()

  def testInvalidDigits(self):
    fd_out = []
    left, right = socket.socketpair()

    left.send(b'34')  # EOF in the middle of length
    left.close()
    try:
      msg = fanos.recv(right.fileno(), fd_out)
    except ValueError as e:
      print(type(e))
      print(e)
    else:
      self.fail('Expected failure')

    right.close()

  def testInvalidMissingColon(self):
    fd_out = []
    left, right = socket.socketpair()

    left.send(b'34foo')
    left.close()
    try:
      msg = fanos.recv(right.fileno(), fd_out)
    except ValueError as e:
      print(type(e))
      print(e)
    else:
      self.fail('Expected failure')

    right.close()

  def testInvalidMissingComma(self):
    fd_out = []
    left, right = socket.socketpair()

    # Short payload BLOCKS indefinitely?
    #left.send(b'3:fo')

    left.send(b'3:foo')  # missing comma

    left.close()
    try:
      msg = fanos.recv(right.fileno(), fd_out)
    except ValueError as e:
      print(type(e))
      print(e)
    else:
      self.fail('Expected failure')

    right.close()


if __name__ == '__main__':
  unittest.main()
