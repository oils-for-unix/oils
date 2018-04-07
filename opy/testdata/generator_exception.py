#!/usr/bin/python
from __future__ import print_function
"""
generator_exception.py
"""

import sys


def Tokenize(s):
  for item in ('1', '2', '3'):
    yield item


class Parser(object):
  """Recursive TDOP parser."""

  def __init__(self, lexer):
    self.lexer = lexer  # iterable
    self.token = None  # current token

  def Next(self):
    """Move to the next token."""
    try:
      t = self.lexer.next()
    except StopIteration:
      t = None
    self.token = t


def main(argv):
  lexer = Tokenize('1+2')
  p = Parser(lexer)
  p.Next()
  p.Next()
  print('Done')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
