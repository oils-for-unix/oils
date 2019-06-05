#!/usr/bin/env python2
from __future__ import print_function
"""
generator_exception.py
"""

import sys


def Tokenize(s):
  for item in ('1', '2', '3'):
    yield item


class TokenizeClass(object):  # NOT a generator
  def __init__(self, s):
    self.s = s
    self.i = 1

  def next(self):
    if self.i == 4:
      raise StopIteration()
    ret = str(self.i)
    self.i += 1
    return ret


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
  if 1:
    lexer = Tokenize('1+2')  # does NOT work
  else:
    lexer = TokenizeClass('1+2')  # WORKS

  p = Parser(lexer)
  p.Next()
  print('Done')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
