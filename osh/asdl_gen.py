#!/usr/bin/env python
from __future__ import print_function
"""
ast_gen.py: Generate the Id enum in C code.

# TODO: This should be renamed to asdl_gen.py
"""

import os
import pickle
import sys

from asdl import asdl_ as asdl
from asdl import front_end
from asdl import gen_cpp
from asdl import gen_python

def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  try:
    schema_path = argv[2]
  except IndexError:
    raise RuntimeError('Schema path required')

  # To avoid circular dependencies, don't load Id for types.asdl.
  if os.path.basename(schema_path) == 'types.asdl':
    app_types = {}
  else:
    from osh.meta import Id
    app_types = {'id': asdl.UserType(Id)}

  if action == 'c':  # Generate C code for the lexer
    with open(schema_path) as f:
      schema_ast, _ = front_end.LoadSchema(f, app_types)

    v = gen_cpp.CEnumVisitor(sys.stdout)
    v.VisitModule(schema_ast)

  elif action == 'py':  # Generate Python code so we don't depend on ASDL schemas
    pickle_out_path = argv[3]

    with open(schema_path) as f:
      schema_ast, type_lookup = front_end.LoadSchema(f, app_types)

    f = sys.stdout

    f.write("""\
import pickle

from asdl import asdl_ as asdl
from asdl import const  # For const.NO_INTEGER
from asdl import py_meta

from core import util

f = util.GetResourceLoader().open('%s')
type_lookup = pickle.load(f)
TYPE_LOOKUP = asdl.TypeLookup(type_lookup)
f.close()

""" % pickle_out_path)

    v = gen_python.GenClassesVisitor(f)
    v.VisitModule(schema_ast)

    if pickle_out_path:
      # Pickle version 2 is better.  (Pickle version 0 uses
      # s.decode('string-escape')! )
      # In version 2, now I have 16 opcodes + STOP.
      with open(pickle_out_path, 'w') as f:
        pickle.dump(type_lookup.runtime_type_lookup, f, protocol=2)
      from core.util import log
      log('Wrote %s', pickle_out_path)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
