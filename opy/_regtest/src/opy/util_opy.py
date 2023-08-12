#!/usr/bin/env python
"""
util.py
"""
from __future__ import print_function

import sys

PY2 = sys.version[0] == '2'

# This uses Python3 keyword-only syntax!
#def log(msg, *args, file=sys.stdout):
#
# WHY oh WHY didn't they rename print to something else, like say().  You have
# to do something like this to hide "if PY2" because it doesn't even parse.

#s = getattr(__builtins__, 'print')

#def say(msg, *args, **kwargs):
#  if msg:
#    msg = msg % args
#  if 'file' in kwargs:
#    f = kwargs.pop('file')
#  else:
#    f = sys.stdout
#  if kwargs:
#    raise ValueError('Invalid keyword arguments %s' % kwargs)
#  if PY2:
#    print >>f, msg
#  else:
#    p(msg, file=f)


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


# compiler.py always tested isinstance(s, str)
def is_unicode(s):
  if PY2:
    return isinstance(s, unicode)
    #return isinstance(s, unicode) or isinstance(s, str)
  else:
    return isinstance(s, str)


if __name__ == '__main__':
  #say('say: %d', 1)
  log('log: %d', 1)
  #log('Test: %d', 1, foo=3)
