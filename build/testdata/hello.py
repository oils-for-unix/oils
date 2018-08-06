#!/usr/bin/env python
"""
hello.py
"""
from __future__ import print_function

import sys
print('Hello from hello.py', file=sys.stderr)

import os

print('sys.path:', sys.path, file=sys.stderr)
print('sys.argv:', sys.argv, file=sys.stderr)
print('hello _OVM_IS_BUNDLE', os.getenv('_OVM_IS_BUNDLE'), file=sys.stderr)

# Default
if not os.getenv('_OVM_DEPS'):
  import inspect
  print(inspect)

import lib

#import zipfile

import zipimport

if os.getenv('_OVM_IS_BUNDLE') == '1':
  if 0:
    print('ZIP')
    z = zipfile.ZipFile(sys.argv[0])
    print(z.infolist())
  else:
    z = zipimport.zipimporter(sys.argv[0])
    print(z)
    print(dir(z))
    # None if we have the module, but no source.
    print('SOURCE', repr(z.get_source('runpy')))
    # TODO: Add a method to get a file?  I think it just imports zlib.
    r = z.get_data('hello-data.txt')
    print('FILE', repr(r))


def Busy(n):
  s = 0
  for i in xrange(n):
    s += i
  print(s)


def main(argv):
  try:
    action = argv[0]
  except IndexError:
    action = 'busy'

  if action == 'busy':
    try:
      n = int(argv[1])
    except IndexError:
      n = 100
    Busy(n)

  elif action == 'unicode':  # For testing that we support 4-byte chars
    print(repr(unichr(0x10000)))

  elif action == 'crash':  # For testing that stack trace shows code
    lib.Crash()

  elif action == 'exit42':  # for testing exit code
    return 42

  else:
    print('Unknown action %r' % action, file=sys.stderr)
    return 1

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
