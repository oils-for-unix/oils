#!/usr/bin/env python2
"""
test_global.py - for Global singletons

"""
from __future__ import print_function

import os

from mycpp.mylib import log


class Token(object):
  def __init__(self, x):
    # type: (int) -> None
    self.x = x

gToken = None  # type: Token

def GetInstance():
  # type: () -> Token

  global gToken
  if gToken is None:
    gToken = Token(42)

  return gToken


_EOL_TOK = None  # type: Token


class LineLexer(object):

  def __init__(self):
    # type: () -> None

    # Initialize global singleton
    global _EOL_TOK
    if _EOL_TOK is None:
      _EOL_TOK = Token(99)

  def Read(self):
    # type: () -> Token
    return _EOL_TOK
  


def run_tests():
  # type: () -> None

  a = GetInstance()
  log("a.x = %d", a.x)


  lx = LineLexer()
  tok = lx.Read()
  log("tok.x = %d", tok.x)


def run_benchmarks():
  # type: () -> None
  raise NotImplementedError()


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
