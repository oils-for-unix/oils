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

  schema_filename = os.path.basename(schema_path) 
  if schema_filename in ('syntax.asdl', 'runtime.asdl'):
    app_types = {'id': meta.UserType('id_kind_asdl', 'Id_t')}
  else:
    app_types = {}

  if action == 'c':  # Generate C code for the lexer
    with open(schema_path) as f:
      schema_ast, _ = front_end.LoadSchema(f, app_types)

    v = gen_cpp.CEnumVisitor(sys.stdout)
    v.VisitModule(schema_ast)

  elif action == 'cpp':  # Generate C++ code for ASDL schemas
    out_prefix = argv[3]
    pretty_print_methods = bool(os.getenv('PRETTY_PRINT_METHODS', 'yes'))

    with open(schema_path) as f:
      schema_ast, type_lookup = front_end.LoadSchema(f, app_types)

    # asdl/typed_arith.asdl -> typed_arith_asdl
    ns = os.path.basename(schema_path).replace('.', '_')

    with open(out_prefix + '.h', 'w') as f:
      guard = ns.upper()
      f.write("""\
#ifndef %s
#define %s

""" % (guard, guard))

      f.write("""\
#include <cstdint>

#include "mylib.h"  // for Str, List, etc.
""")

      if pretty_print_methods:
        f.write("""\
#include "hnode_asdl.h"
using hnode_asdl::hnode_t;
""")

      if app_types:
        f.write("""\
using id_kind_asdl::Id_str;
""")

      f.write("""\
namespace %s {

""" % ns)

      v = gen_cpp.ForwardDeclareVisitor(f)
      v.VisitModule(schema_ast)

      v2 = gen_cpp.ClassDefVisitor(f, type_lookup,
                                   pretty_print_methods=pretty_print_methods)
      v2.VisitModule(schema_ast)

      f.write("""
}  // namespace %s

#endif  // %s
""" % (ns, guard))

      with open(out_prefix + '.cc', 'w') as f:
        # HACK until we support 'use'
        if schema_filename == 'syntax.asdl':
          f.write('#include "id_kind_asdl.h"  // hack\n')
          f.write('using id_kind_asdl::Id_t;  // hack\n')

        f.write("""
#include <assert.h>

#include "asdl_runtime.h"  // generated code uses wrappers here

// Generated code uses these types
using hnode_asdl::hnode__Record;
using hnode_asdl::hnode__Array;
using hnode_asdl::hnode__External;
using hnode_asdl::hnode__Leaf;
using hnode_asdl::field;
using hnode_asdl::color_e;
""")

        f.write("""
#include "%s.h"

namespace %s {

""" % (ns, ns))

        v3 = gen_cpp.MethodDefVisitor(f, type_lookup,
                                      pretty_print_methods=pretty_print_methods)
        v3.VisitModule(schema_ast)

        f.write("""
}  // namespace %s
""" % ns)

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
        # HACK
        f.write('from _devbuild.gen.%s import Id_str\n' % typ.mod_name)
        f.write('\n')

    # NOTE: Dict, Any are for AssocArray with 'dict' type.
    f.write("""\
from asdl import pybase
from typing import Optional, List, Tuple, Dict, Any, cast
""")

    pretty_print_methods = bool(os.getenv('PRETTY_PRINT_METHODS', 'yes'))
    optional_fields = bool(os.getenv('OPTIONAL_FIELDS', 'yes'))

    if pretty_print_methods:
      f.write("""
from asdl import runtime  # For runtime.NO_SPID
from asdl.runtime import NewRecord, NewLeaf
from _devbuild.gen.hnode_asdl import color_e, hnode, hnode_e, hnode_t, field

""")

    abbrev_mod_entries = dir(abbrev_mod) if abbrev_mod else []
    v = gen_python.GenMyPyVisitor(f, type_lookup, abbrev_mod_entries,
                                  pretty_print_methods=pretty_print_methods,
                                  optional_fields=optional_fields)
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
