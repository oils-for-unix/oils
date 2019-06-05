#!/usr/bin/env python2
from __future__ import print_function
"""
opcode_gen.py
"""

import sys

from lib import opcode


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def main(argv):
  opcode_nums = set(opcode.opmap.itervalues())

  # Print opcodes in numerical order.  They're not contiguous integers.
  for num in sorted(opcode_nums):
    # SLICE+1 -> SLICE_1
    name = opcode.opname[num].replace('+', '_')
    print('#define %s %d' % (name, num))

  print('')
  print('#define HAVE_ARGUMENT %d' % opcode.HAVE_ARGUMENT)

  #log('%s', opcode.opname)

  print('')
  print('const char* const kOpcodeNames[] = {')
  n = max(opcode_nums)
  for i in xrange(n+1):
    if i in opcode_nums:
      print('"%s",' % opcode.opname[i])
    else:
      print('"",')  # empty value
  print('};')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
