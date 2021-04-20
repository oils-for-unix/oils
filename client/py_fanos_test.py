#!/usr/bin/env python3
"""
py_fanos_test.py: Tests for py_fanos.py
"""
import socket
import sys
import unittest

import py_fanos  # module under test


class FanosTest(unittest.TestCase):

  def testSendReceive(self):
    left, right = socket.socketpair()

    py_fanos.send(left, b'foo')

    fd_out = []
    msg = py_fanos.recv(right, fd_out=fd_out)
    self.assertEqual(b'foo', msg)
    self.assertEqual([], fd_out)

    py_fanos.send(left, b'spam', [sys.stdin.fileno(), sys.stdout.fileno(), sys.stderr.fileno()])

    msg = py_fanos.recv(right, fd_out=fd_out)
    self.assertEqual(b'spam', msg)
    self.assertEqual(3, len(fd_out))
    print(fd_out)

    left.close()
    msg = py_fanos.recv(right)
    self.assertEqual(None, msg)  # Valid EOF

    right.close()


class InvalidMessageTests(unittest.TestCase):
  """COPIED to native/fanos_test.py."""

  def testInvalidColon(self):
    left, right = socket.socketpair()

    left.send(b':')  # Should be 3:foo,
    try:
      msg = py_fanos.recv(right)
    except ValueError as e:
      print(type(e))
      print(e)
    else:
      self.fail('Expected failure')

    left.close()
    right.close()

  def testInvalidDigits(self):
    left, right = socket.socketpair()

    left.send(b'34')  # EOF in the middle of length
    left.close()
    try:
      msg = py_fanos.recv(right)
    except ValueError as e:
      print(type(e))
      print(e)
    else:
      self.fail('Expected failure')

    right.close()

  def testInvalidMissingColon(self):
    left, right = socket.socketpair()

    left.send(b'34foo')  # missing colon

    left.close()
    try:
      msg = py_fanos.recv(right)
    except ValueError as e:
      print(type(e))
      print(e)
    else:
      self.fail('Expected failure')

    right.close()

  def testInvalidMissingComma(self):
    left, right = socket.socketpair()

    # Short payload BLOCKS indefinitely?
    #left.send(b'3:fo')

    left.send(b'3:foo')  # missing comma

    left.close()
    try:
      msg = py_fanos.recv(right)
    except ValueError as e:
      print(type(e))
      print(e)
    else:
      self.fail('Expected failure')

    right.close()


if __name__ == '__main__':
  unittest.main()
