#!/usr/bin/env python
"""
asdl_gen.py - Generate Python and C from OSH ASDL schemas.
"""
from __future__ import print_function

import os
import sys

from asdl import front_end
from asdl import gen_cpp
from asdl import gen_python
from asdl import meta

#from core.util import log

def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  try:
    schema_path = argv[2]
  except IndexError:
    raise RuntimeError('Schema path required')

  if os.path.basename(schema_path) in ('syntax.asdl', 'runtime.asdl'):
    app_types = {'id': meta.UserType('id_kind_asdl', 'Id_t')}
  else:
    app_types = {}

  if action == 'c':  # Generate C code for the lexer
    with open(schema_path) as f:
      schema_ast, _ = front_end.LoadSchema(f, app_types)

    v = gen_cpp.CEnumVisitor(sys.stdout)
    v.VisitModule(schema_ast)

  elif action == 'cpp':  # Generate C++ code for ASL schemas
    with open(schema_path) as f:
      schema_ast, _ = front_end.LoadSchema(f, app_types)

    v = gen_cpp.ForwardDeclareVisitor(sys.stdout)
    v.VisitModule(schema_ast)

  elif action == 'mypy':  # Generated typed MyPy code
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

    for typ in app_types.itervalues():
      if isinstance(typ, meta.UserType):
        f.write('from _devbuild.gen.%s import %s\n' % (
          typ.mod_name, typ.type_name))
        f.write('\n')

    # NOTE: Dict, Any are for AssocArray with 'dict' type.
    f.write("""\
from asdl import const  # For const.NO_INTEGER
from asdl import runtime
from asdl.runtime import (
  PrettyLeaf, PrettyArray, PrettyNode,
  Color_TypeName, Color_StringConst, Color_OtherConst, Color_UserType,
)

from typing import Optional, List, Tuple, Dict, Any

""")

    abbrev_mod_entries = dir(abbrev_mod) if abbrev_mod else []
    v = gen_python.GenMyPyVisitor(f, type_lookup, abbrev_mod_entries)
    v.VisitModule(schema_ast)

    if abbrev_mod:
      f.write("""\
#
# CONCATENATED FILE
#

""")
      package, module = abbrev_module_name.split('.')
      path = os.path.join(package, module + '.py')
      with open(path) as in_f:
        f.write(in_f.read())

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
