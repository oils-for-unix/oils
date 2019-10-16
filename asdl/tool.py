#!/usr/bin/env python2
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

  elif action == 'cpp':  # Generate C++ code for ASDL schemas
    with open(schema_path) as f:
      schema_ast, type_lookup = front_end.LoadSchema(f, app_types)

    # asdl/typed_arith.asdl -> typed_arith_asdl
    ns = os.path.basename(schema_path).replace('.', '_')

    f = sys.stdout

    guard = ns.upper()
    f.write("""\
#ifndef %s
#define %s

""" % (guard, guard))
    f.write("""\
#include <cstdint>

#include "mylib.h"  // for Str, List, etc.
""")
    pretty_print_methods = bool(os.getenv('PRETTY_PRINT_METHODS', 'yes'))
    if pretty_print_methods:
      f.write('#include "hnode_asdl.h"\n')
      f.write('using hnode_asdl::hnode_t;\n')
      f.write('using hnode_asdl::hnode__External;\n')
      f.write('using hnode_asdl::hnode__Leaf;\n')
      f.write('using hnode_asdl::color_e;\n')

    f.write("""\
namespace %s {

""" % ns)

    v = gen_cpp.ForwardDeclareVisitor(f)
    v.VisitModule(schema_ast)

    v2 = gen_cpp.ClassDefVisitor(f, type_lookup,
                                 pretty_print_methods=pretty_print_methods)
    v2.VisitModule(schema_ast)

    f.write('}  // namespace %s\n' % ns)

    f.write('\n')
    f.write('#endif  // %s\n' % guard)

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
from asdl import pybase
from typing import Optional, List, Tuple, Dict, Any, cast
""")

    pretty_print_methods = bool(os.getenv('PRETTY_PRINT_METHODS', 'yes'))
    if pretty_print_methods:
      f.write("""
from asdl import runtime  # For runtime.NO_SPID
from asdl.runtime import (
  NewRecord, NewLeaf,
)
from _devbuild.gen.hnode_asdl import color_e, hnode, hnode_e, hnode_t, field

""")

    abbrev_mod_entries = dir(abbrev_mod) if abbrev_mod else []
    v = gen_python.GenMyPyVisitor(f, type_lookup, abbrev_mod_entries,
                                  pretty_print_methods=pretty_print_methods)
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
