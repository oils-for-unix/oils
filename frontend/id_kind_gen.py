#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
id_kind_gen.py - Code generation for id_kind_def.py.
"""
from __future__ import print_function

import sys

from asdl.visitor import FormatLines
from frontend import id_kind_def


def Emit(s, f, depth=0):
  for line in FormatLines(s, depth):
    f.write(line)


def _CreateModule(id_spec, ids):
  """ 
  Create a SYNTHETIC ASDL module to generate code from.
  """
  from asdl import asdl_

  id_sum = asdl_.Sum([asdl_.Constructor(name) for name, _ in ids])

  variants2 = [asdl_.Constructor(name) for name in id_spec.kind_name_list]
  kind_sum = asdl_.Sum(variants2)

  id_ = asdl_.Type('Id', id_sum)
  kind_ = asdl_.Type('Kind', kind_sum)

  schema_ast = asdl_.Module('id_kind', [], [id_, kind_])
  return schema_ast


def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  # TODO: Remove duplication in core/meta.py
  ID_TO_KIND = {}
  BOOL_ARG_TYPES = {}
  TEST_UNARY_LOOKUP = {}
  TEST_BINARY_LOOKUP = {}
  TEST_OTHER_LOOKUP = {}

  ID_SPEC = id_kind_def.IdSpec(ID_TO_KIND, BOOL_ARG_TYPES)

  id_kind_def.AddKinds(ID_SPEC)
  id_kind_def.AddBoolKinds(ID_SPEC)  # must come second

  id_kind_def.SetupTestBuiltin(ID_SPEC, TEST_UNARY_LOOKUP, TEST_BINARY_LOOKUP,
                               TEST_OTHER_LOOKUP)

  ids = ID_SPEC.id_str2int.items()
  ids.sort(key=lambda pair: pair[1])  # Sort by ID

  if action == 'c':
    for name, id_int in ids:
      print('#define id__%s %s' % (name, id_int))

  elif action == 'cpp':
    from asdl import gen_cpp

    schema_ast = _CreateModule(ID_SPEC, ids)

    out_prefix = argv[2]

    with open(out_prefix + '.h', 'w') as f:
      f.write("""\
#ifndef ID_KIND_ASDL_H
#define ID_KIND_ASDL_H

namespace id_kind_asdl {
""")

      v = gen_cpp.ClassDefVisitor(f, {}, e_suffix=False,
                                  simple_int_sums=['Id'])
      v.VisitModule(schema_ast)

      f.write("""
}  // namespace id_kind_asdl

#endif  // ID_KIND_ASDL_H
""")

    with open(out_prefix + '.cc', 'w') as f:
      f.write("""\
#include <assert.h>
#include "id_kind_asdl.h"

namespace id_kind_asdl {

""")

      v = gen_cpp.MethodDefVisitor(f, {}, e_suffix=False,
                                   simple_int_sums=['Id'])

      v.VisitModule(schema_ast)

      f.write('}  // namespace id_kind_asdl\n')

  elif action == 'mypy':
    from asdl import gen_python

    schema_ast = _CreateModule(ID_SPEC, ids)
    #print(schema_ast)

    f = sys.stdout

    f.write("""\
from asdl import pybase

""")
    # Minor style issue: we want Id and Kind, not Id_e and Kind_e
    v = gen_python.GenMyPyVisitor(f, None, e_suffix=False,
                                  simple_int_sums=['Id'])
    v.VisitModule(schema_ast)

  elif action == 'cpp-consts':
    from frontend.consts import REDIR_DEFAULT_FD, REDIR_ARG_TYPES
    from _devbuild.gen.id_kind_asdl import Id_str, Kind_str
    from _devbuild.gen.types_asdl import redir_arg_type_str, bool_arg_type_str

    prefix = argv[2]

    with open(prefix + '.h', 'w') as f:
      def out(fmt, *args):
        print(fmt % args, file=f)

      out("""\
#ifndef LOOKUP_H
#define LOOKUP_H

#include "id_kind_asdl.h"
#include "types_asdl.h"

namespace consts {

int RedirDefaultFd(id_kind_asdl::Id_t id);
types_asdl::redir_arg_type_t RedirArgType(id_kind_asdl::Id_t id);
types_asdl::bool_arg_type_t BoolArgType(id_kind_asdl::Id_t id);
id_kind_asdl::Kind GetKind(id_kind_asdl::Id_t id);

}  // namespace consts

#endif  // LOOKUP_H
""")

    with open(prefix + '.cc', 'w') as f:
      def out(fmt, *args):
        print(fmt % args, file=f)

      out("""\
#include "consts.h"

namespace Id = id_kind_asdl::Id;
using id_kind_asdl::Kind;
using types_asdl::redir_arg_type_e;
using types_asdl::bool_arg_type_e;

namespace consts {
""")

      out("""\
int RedirDefaultFd(id_kind_asdl::Id_t id) {
  // relies on "switch lowering"
  switch (id) {
""")
      for id_ in sorted(REDIR_DEFAULT_FD):
        a = Id_str(id_).replace('.','::')
        b = REDIR_DEFAULT_FD[id_]
        out('  case %s: return %s;' % (a, b))
      out("""\
  }
}
""")

      out("""\
types_asdl::redir_arg_type_t RedirArgType(id_kind_asdl::Id_t id) {
  // relies on "switch lowering"
  switch (id) {
""")
      for id_ in sorted(REDIR_ARG_TYPES):
        a = Id_str(id_).replace('.','::')
        # redir_arg_type_e::Path, etc.
        b = redir_arg_type_str(REDIR_ARG_TYPES[id_]).replace('.', '_e::')
        out('  case %s: return %s;' % (a, b))
      out("""\
  }
}
""")

      out("""\
types_asdl::bool_arg_type_t BoolArgType(id_kind_asdl::Id_t id) {
  // relies on "switch lowering"
  switch (id) {
""")
      for id_ in sorted(BOOL_ARG_TYPES):
        a = Id_str(id_).replace('.','::')
        # bool_arg_type_e::Str, etc.
        b = bool_arg_type_str(BOOL_ARG_TYPES[id_]).replace('.', '_e::')
        out('  case %s: return %s;' % (a, b))
      out("""\
  }
}
""")

      out("""\
Kind GetKind(id_kind_asdl::Id_t id) {
  // relies on "switch lowering"
  switch (id) {
""")
      for id_ in sorted(ID_TO_KIND):
        a = Id_str(id_).replace('.','::')
        b = Kind_str(ID_TO_KIND[id_]).replace('.', '::')
        out('  case %s: return %s;' % (a, b))
      out("""\
  }
}
""")

      out("""\
}  // namespace consts
""")


  elif action == 'py-consts':
    # It's kind of weird to use the generated code to generate more code.
    # Can we do this instead with the parsed module for "id" and "types.asdl"?

    from frontend.consts import REDIR_DEFAULT_FD, REDIR_ARG_TYPES
    from _devbuild.gen.id_kind_asdl import Id_str, Kind_str
    from _devbuild.gen.types_asdl import redir_arg_type_str, bool_arg_type_str

    print("""
from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.types_asdl import redir_arg_type_e, bool_arg_type_e
""")

    print('')
    print('REDIR_DEFAULT_FD = {')
    for id_ in sorted(REDIR_DEFAULT_FD):
      v = REDIR_DEFAULT_FD[id_]
      print('  %s: %s,' % (Id_str(id_), v))
    print('}')

    print('')
    print('REDIR_ARG_TYPES = {')
    for id_ in sorted(REDIR_ARG_TYPES):
      v = REDIR_ARG_TYPES[id_]
      # HACK
      v = redir_arg_type_str(v).replace('.', '_e.')
      print('  %s: %s,' % (Id_str(id_), v))
    print('}')

    print('')
    print('BOOL_ARG_TYPES = {')
    for id_ in sorted(BOOL_ARG_TYPES):
      v = BOOL_ARG_TYPES[id_]
      # HACK
      v = bool_arg_type_str(v).replace('.', '_e.')
      print('  %s: %s,' % (Id_str(id_), v))
    print('}')

    print('')
    print('TEST_UNARY_LOOKUP = {')
    for op_str in sorted(TEST_UNARY_LOOKUP):
      v = Id_str(TEST_UNARY_LOOKUP[op_str])
      print('  %r: %s,' % (op_str, v))
    print('}')

    print('')
    print('TEST_BINARY_LOOKUP = {')
    for op_str in sorted(TEST_BINARY_LOOKUP):
      v = Id_str(TEST_BINARY_LOOKUP[op_str])
      print('  %r: %s,' % (op_str, v))
    print('}')

    print('')
    print('TEST_OTHER_LOOKUP = {')
    for op_str in sorted(TEST_OTHER_LOOKUP):
      v = Id_str(TEST_OTHER_LOOKUP[op_str])
      print('  %r: %s,' % (op_str, v))
    print('}')

    print('')
    print('ID_TO_KIND = {')
    for id_ in sorted(ID_TO_KIND):
      v = Kind_str(ID_TO_KIND[id_])
      print('  %s: %s,' % (Id_str(id_), v))
    print('}')

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
