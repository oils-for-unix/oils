#!/usr/bin/python -S
"""
encode_test.py: Tests for encode.py
"""

import unittest

from asdl import encode  # module under test


class EncoderTest(unittest.TestCase):

  def testEncoder(self):
    p = encode.Params(16)

    chunk = bytearray()
    p.Int(1, chunk)
    self.assertEqual(b'\x01\x00\x00', chunk)

    chunk = p.PaddedBytes('0123456789')
    # 2 byte length -- max 64K entries
    self.assertEqual(b'\x0A\x000123456789\x00\x00\x00\x00', bytes(chunk))

    chunk = p.PaddedStr('0123456789')
    # 2 byte length -- max 64K entries
    self.assertEqual(b'0123456789\x00\x00\x00\x00\x00\x00', bytes(chunk))

    #p.Block([b'a', b'bc'])


if __name__ == '__main__':
  unittest.main()
