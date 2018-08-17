#!/usr/bin/env python
"""
ast_gen.py
"""

import sys

from osh.meta import types, Id
from asdl import asdl_ as asdl
from asdl import front_end
from asdl import gen_cpp

lex_mode_e = types.lex_mode_e


def main(argv):
  #print lex_mode_e
  #print dir(lex_mode_e)

  app_types = {'id': asdl.UserType(Id)}
  with open('osh/types.asdl') as f:
    asdl_module, _ = front_end.LoadSchema(f, app_types)

  v = gen_cpp.CEnumVisitor(sys.stdout)
  v.VisitModule(asdl_module)

  # NOTE: MakeTypes does things in a certain order.


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
