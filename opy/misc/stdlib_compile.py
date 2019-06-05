#!/usr/bin/env python2
from __future__ import print_function
"""
stdlib_compile.py
"""

import compiler as stdlib_comp
import imp
#import os
import marshal
import struct
import sys

#import hashlib


def getPycHeader(filename):
  # compile.c uses marshal to write a long directly, with
  # calling the interface that would also generate a 1-byte code
  # to indicate the type of the value.  simplest way to get the
  # same effect is to call marshal and then skip the code.
  #mtime = os.path.getmtime(filename)
  mtime = 0  # to make it deterministic for now
  mtime = struct.pack('<i', int(mtime))
  return imp.get_magic() + mtime


def compileAndWrite(in_path, out_path, compile_func):
  #print(stdlib_comp, file=sys.stderr)

  with open(in_path) as f:
    co = compile_func(f.read(), in_path, 'exec')

  #print(co, file=sys.stderr)

  h = getPycHeader(in_path)
  with open(out_path, 'w') as out_f:
    out_f.write(h)

    s = marshal.dumps(co)
    #m = hashlib.md5()
    #m.update(s)
    #print(m.hexdigest(), file=sys.stderr)

    out_f.write(s)


def main(argv):
  in_path = argv[1]
  out_path = argv[2]

  compileAndWrite(in_path, out_path, stdlib_comp.compile)


if __name__ == '__main__':
  main(sys.argv)
