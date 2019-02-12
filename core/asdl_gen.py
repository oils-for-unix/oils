#!/usr/bin/env python
"""
asdl_gen.py - Generate Python and C from OSH ASDL schemas.
"""
from __future__ import print_function

import os
import pickle
import sys

from asdl import front_end
from asdl import gen_cpp
from asdl import gen_python
from asdl import runtime

from core.util import log

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
    from core.meta import Id
    app_types = {'id': runtime.UserType(Id)}

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
from asdl import const  # For const.NO_INTEGER
from asdl import runtime
from pylib import unpickle

from core import util

f = util.GetResourceLoader().open('%s')
TYPE_LOOKUP = unpickle.load_v2_subset(f)
f.close()

""" % pickle_out_path)

    v = gen_python.GenClassesVisitor(f)
    v.VisitModule(schema_ast)

    if pickle_out_path:
      # Pickle version 2 is better.  (Pickle version 0 uses
      # s.decode('string-escape')! )
      # In version 2, now I have 16 opcodes + STOP.
      with open(pickle_out_path, 'w') as f:
        pickle.dump(type_lookup, f, protocol=2)
      log('Wrote %s', pickle_out_path)

  elif action == 'mypy':  # typed mypy
    with open(schema_path) as f:
      schema_ast, type_lookup = front_end.LoadSchema(f, app_types)

    try:
      abbrev_module_name = argv[3]
    except IndexError:
      abbrev_mod = None
    else:
      # Weird Python rule for importing: fromlist needs to be non-empty.
      abbrev_mod = __import__(abbrev_module_name, fromlist=['.'])

    f = sys.stdout

    f.write("""\
from asdl import const  # For const.NO_INTEGER
from asdl import typed_runtime as runtime

PrettyLeaf = runtime.PrettyLeaf
PrettyArray = runtime.PrettyArray
PrettyNode = runtime.PrettyNode

Color_TypeName = runtime.Color_TypeName
Color_StringConst = runtime.Color_StringConst
Color_OtherConst = runtime.Color_OtherConst
Color_UserType = runtime.Color_UserType

from typing import Optional, List, Tuple

""")

    if abbrev_mod:
      package, module = abbrev_module_name.split('.')
      f.write('from %s import %s\n' % (package, module))
      f.write('\n')

    v = gen_python.GenMyPyVisitor(f, type_lookup, abbrev_mod)
    v.VisitModule(schema_ast)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
