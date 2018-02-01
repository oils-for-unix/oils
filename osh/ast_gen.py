#!/usr/bin/env python
"""
ast_gen.py
"""

import sys

from osh import ast_ as ast
from asdl import gen_cpp

lex_mode_e = ast.lex_mode_e


def main(argv):
  #print lex_mode_e
  #print dir(lex_mode_e)

  with open('osh/osh.asdl') as f:
    asdl_module, _ = ast.LoadSchema(f)

  # TODO: Generate C files for lex_mode_e, id_e, etc.

  # It already works for lex_mode.  Except it's C++.  Maybe write one that's C?
  #
  # C doesn't have namespaces!

  # lex_mode_e__NONE?
  # lex_mode_e__OUTER?
  # The re2c code will have a switch statement for that?
  #
  # Or maybe just lex_mode__NONE.
  #
  # And then it will output id__Lit_Chars ?
  # This is all generated so we can change it at any time.

  # Eventually you may also generate code to map Id -> Kind?  But right now you
  # just need Id for the lexer!

  #print asdl_module
  #print gen_cpp

  v = gen_cpp.CEnumVisitor(sys.stdout)
  v.VisitModule(asdl_module)

  # NOTE: MakeTypes does things in a certain order.


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
