#!/usr/bin/env python2
"""
asdl_gen.py - Generate Python and C from OSH ASDL schemas.
"""
from __future__ import print_function

import os
import sys

from asdl import asdl_
from asdl import front_end
from asdl import gen_cpp
from asdl import gen_python

#from core.pyerror import log

# Special cases like Id
# TODO: Put this in the ASDL schema!
_SIMPLE = ['state', 'emit', 'char_kind', 'opt_group']


class UserType(object):
  """
  TODO: Delete this class after we have modules with 'use'?
  """
  def __init__(self, mod_name, type_name):
    self.mod_name = mod_name
    self.type_name = type_name

  def __repr__(self):
    return '<UserType %s %s>' % (self.mod_name, self.type_name)


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
    app_types = {'id': UserType('id_kind_asdl', 'Id_t')}
  else:
    app_types = {}

  if action == 'c':  # Generate C code for the lexer
    with open(schema_path) as f:
      schema_ast = front_end.LoadSchema(f, app_types)

    v = gen_cpp.CEnumVisitor(sys.stdout)
    v.VisitModule(schema_ast)

  elif action == 'cpp':  # Generate C++ code for ASDL schemas
    out_prefix = argv[3]
    pretty_print_methods = bool(os.getenv('PRETTY_PRINT_METHODS', 'yes'))

    with open(schema_path) as f:
      schema_ast = front_end.LoadSchema(f, app_types)

    # asdl/typed_arith.asdl -> typed_arith_asdl
    ns = os.path.basename(schema_path).replace('.', '_')

    with open(out_prefix + '.h', 'w') as f:
      guard = ns.upper()
      f.write("""\
// %s.h is generated by asdl/tool.py

#ifndef %s
#define %s

""" % (out_prefix, guard, guard))

      f.write("""\
#include <cstdint>
""")
      f.write("""
#ifdef LEAKY_BINDINGS
#include "mycpp/mylib_old.h"
using mylib::NewList;
#else
#include "mycpp/gc_types.h"
using gc_heap::Obj;
using gc_heap::Dict;
using gc_heap::List;
using gc_heap::NewList;
using gc_heap::Str;
using gc_heap::StrFromC;
#endif
""")
      if pretty_print_methods:
        f.write("""\
#include "_build/cpp/hnode_asdl.h"
using hnode_asdl::hnode_t;

""")

      if app_types:
        f.write("""\
#include "_build/cpp/id_kind_asdl.h"
using id_kind_asdl::Id_t;

""")

      for use in schema_ast.uses:
        # Forward declarations in the header, like
        # namespace syntax_asdl { class command_t; }
        # must come BEFORE namespace, so it can't be in the visitor.

        # assume sum type for now!
        cpp_names = [
            'class %s;' % asdl_.TypeNameHeuristic(n) for n in use.type_names]
        f.write('namespace %s_asdl { %s }\n' % (
            use.mod_name, ' '.join(cpp_names)))
        f.write('\n')

      f.write("""\
namespace %s {

""" % ns)

      v = gen_cpp.ForwardDeclareVisitor(f)
      v.VisitModule(schema_ast)

      debug_info = {}
      v2 = gen_cpp.ClassDefVisitor(f, pretty_print_methods=pretty_print_methods,
                                   simple_int_sums=_SIMPLE,
                                   debug_info=debug_info)
      v2.VisitModule(schema_ast)

      f.write("""
}  // namespace %s

#endif  // %s
""" % (ns, guard))

      try:
        debug_info_path = argv[4]
      except IndexError:
        pass
      else:
        with open(debug_info_path, 'w') as f:
          from pprint import pformat
          f.write('''\
cpp_namespace = %r
tags_to_types = \\
%s
''' % (ns, pformat(debug_info)))

      with open(out_prefix + '.cc', 'w') as f:
        f.write("""\
// %s.cc is generated by asdl/tool.py

#include "%s.h"
#include <assert.h>
""" % (out_prefix, ns))

        if pretty_print_methods:
          f.write("""\
#include "asdl/runtime.h"  // generated code uses wrappers here
""")

        # To call pretty-printing methods
        for use in schema_ast.uses:
          f.write('#include "%s_asdl.h"  // "use" in ASDL \n' % use.mod_name)

        if pretty_print_methods:
          f.write("""\

// Generated code uses these types
using hnode_asdl::hnode__Record;
using hnode_asdl::hnode__Array;
using hnode_asdl::hnode__External;
using hnode_asdl::hnode__Leaf;
using hnode_asdl::field;
using hnode_asdl::color_e;

""")

        if app_types:
          f.write('using id_kind_asdl::Id_str;\n')


        f.write("""
namespace %s {

""" % ns)

        v3 = gen_cpp.MethodDefVisitor(f,
                                      pretty_print_methods=pretty_print_methods,
                                      simple_int_sums=_SIMPLE)
        v3.VisitModule(schema_ast)

        f.write("""
}  // namespace %s
""" % ns)

  elif action == 'mypy':  # Generated typed MyPy code
    with open(schema_path) as f:
      schema_ast = front_end.LoadSchema(f, app_types)

    try:
      abbrev_module_name = argv[3]
    except IndexError:
      abbrev_mod = None
    else:
      # Weird Python rule for importing: fromlist needs to be non-empty.
      abbrev_mod = __import__(abbrev_module_name, fromlist=['.'])

    f = sys.stdout

    # TODO: Remove Any once we stop using it
    f.write("""\
from asdl import pybase
from pylib.collections_ import OrderedDict
from typing import Optional, List, Tuple, Dict, Any, cast, TYPE_CHECKING
""")

    if schema_ast.uses:
      f.write('\n')
      f.write('if TYPE_CHECKING:\n')
    for use in schema_ast.uses:
      py_names = [asdl_.TypeNameHeuristic(n) for n in use.type_names]
      # indented
      f.write('  from _devbuild.gen.%s_asdl import %s\n' % (
        use.mod_name, ', '.join(py_names)))
    f.write('\n')

    for typ in app_types.itervalues():
      if isinstance(typ, UserType):
        f.write('from _devbuild.gen.%s import %s\n' % (
          typ.mod_name, typ.type_name))
        # HACK
        f.write('from _devbuild.gen.%s import Id_str\n' % typ.mod_name)
        f.write('\n')

    pretty_print_methods = bool(os.getenv('PRETTY_PRINT_METHODS', 'yes'))
    optional_fields = bool(os.getenv('OPTIONAL_FIELDS', 'yes'))

    if pretty_print_methods:
      f.write("""
from asdl import runtime  # For runtime.NO_SPID
from asdl.runtime import NewRecord, NewLeaf
from _devbuild.gen.hnode_asdl import color_e, hnode, hnode_e, hnode_t, field

""")

    abbrev_mod_entries = dir(abbrev_mod) if abbrev_mod else []
    v = gen_python.GenMyPyVisitor(f, abbrev_mod_entries,
                                  pretty_print_methods=pretty_print_methods,
                                  optional_fields=optional_fields,
                                  simple_int_sums=_SIMPLE)
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
    
