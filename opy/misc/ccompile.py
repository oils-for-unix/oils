#!/usr/bin/env python2
"""
ccompile.py - Compile with builtin compile() function, which uses compile.c.
"""

import sys
import stdlib_compile


def main(argv):
  in_path = argv[1]
  out_path = argv[2]

  stdlib_compile.compileAndWrite(in_path, out_path, compile)


if __name__ == '__main__':
  main(sys.argv)
