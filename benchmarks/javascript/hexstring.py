#!/usr/bin/env python2
"""
hexstring.py
"""
from __future__ import print_function

import sys


def main(argv):
  hexdigits = '0123456789abcdef'
  for c in hexdigits:
    for d in hexdigits:
      for e in hexdigits:
        hexbyte = c + d + e #+ f

        byte = hexbyte
        byte = byte.replace('0', '0000')
        byte = byte.replace('1', '0001')
        byte = byte.replace('2', '0010')
        byte = byte.replace('3', '0011')

        byte = byte.replace('4', '0100')
        byte = byte.replace('5', '0101')
        byte = byte.replace('6', '0110')
        byte = byte.replace('7', '0111')

        byte = byte.replace('8', '1000')
        byte = byte.replace('9', '1001')
        byte = byte.replace('a', '1010')
        byte = byte.replace('b', '1011')

        byte = byte.replace('c', '1100')
        byte = byte.replace('d', '1101')
        byte = byte.replace('e', '1110')
        byte = byte.replace('f', '1111')

        #print(byte)

        ones = byte.replace('0', '')
        if len(ones) == 11:
          print(hexbyte, byte)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
