#!/usr/bin/env python2
"""
u2.py
"""
from __future__ import print_function

import sys


from core import completion
from core import test_lib
from frontend import parse_lib
from osh import state


def main(argv):
  init_code = ' echo hi >&2 '

  arena = test_lib.MakeArena('<InitCompletionTest>')
  parse_ctx = parse_lib.ParseContext(arena, {})
  mem = state.Mem('', [], {}, arena)

  comp_lookup = completion.Lookup()
  ex = test_lib.EvalCode(init_code, parse_ctx, comp_lookup=comp_lookup,
                         mem=mem)

  print('hi')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)

