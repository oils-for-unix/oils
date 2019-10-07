#!/usr/bin/python
"""
cgi.py - Copied from Python stdlib.

We don't want the side effects of importing tempfile, which imports random,
which opens /dev/urandom!
"""
from __future__ import print_function

import os

from mylib import log


# For testing what the code generator does
BACKSLASH = '\\'
RAW_BACKSLASH = r'\d+'

def escape(s, quote=False):
    # type: (str, bool) -> str
    '''Replace special characters "&", "<" and ">" to HTML-safe sequences.
    If the optional flag quote is true, the quotation mark character (")
    is also translated.'''
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
    return s


def run_tests():
  # type: () -> None

  log("escaped: %s", escape('<html>', True))
  # TODO: Fix double escaping here
  s = 'xo--xo'
  log("%s\n", s.replace('xo', 'OX'))


def run_benchmarks():
  # type: () -> None
  i = 0
  n = 1000000
  while i < n:
    escape('<html>', True)
    i = i + 1


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
