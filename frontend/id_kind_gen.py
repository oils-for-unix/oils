#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
id_kind_gen.py - Code generation for id_kind.py.
"""
from __future__ import print_function

import sys

from asdl.visitor import FormatLines
from frontend import id_kind


def Emit(s, f, depth=0):
  for line in FormatLines(s, depth):
    f.write(line)


def GenCppCode(kind_names, id_names, f, id_labels=None, kind_labels=None):
  """
  Args:
    kind_names: List of kind name strings, in display order
    id_names: List of list of id name strings, in display order
    f: output file
    id_labels: optional name to integer
    kind_labels: optional name to integer
  """
  Emit('#include <cstdint>', f)
  #Emit('#include "stdio.h"', f)
  Emit('', f)
  Emit('enum class Kind : uint8_t {', f)
  if kind_labels:
    s = ', '.join(['%s=%s' % (k, kind_labels[k]) for k in kind_names]) + ','
    Emit(s, f, 1)
  else:
    Emit(', '.join(kind_names), f, 1)
  Emit('};\n', f)

  # TODO: Change this back to a uint8_t?  Right now we have a Glob_ Kind which
  # pushes it over 256, but we don't really need it in Id.  It could easily be
  # its own type GlobId.

  Emit('enum class Id : uint16_t {', f)
  for names_in_kind in id_names:
    if id_labels:
      s = ', '.join(['%s=%s' % (i, id_labels[i]) for i in names_in_kind]) + ','
      Emit(s, f, 1)
    else:
      Emit(', '.join(names_in_kind) + ',', f, 1)
    Emit('', f)

  Emit('};\n', f)

  if 0:  # Test for blog post
    f.write(r"""
  Kind LookupKind(Id id) {
    int i = static_cast<int>(id);
    int k = 175 & i & ((i ^ 173) + 11);
    return static_cast<Kind>(k);
  }

  int main() {
  """)
    for names_in_kind in id_names:
      if id_labels:
        for id_name in names_in_kind:
          kind_name = id_name.split('_')[0]
          test = (
              'if (LookupKind(Id::%s) != Kind::%s) return 1;' %
              (id_name, kind_name))
          Emit(test, f, 1)
      else:
        pass
      Emit('', f)

    f.write(r"""
    printf("PASSED\n");
    return 0;
  }
  """)


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
  ID_TO_KIND_INTEGERS = {}
  BOOL_ARG_TYPES = {}
  TEST_UNARY_LOOKUP = {}
  TEST_BINARY_LOOKUP = {}
  TEST_OTHER_LOOKUP = {}

  ID_SPEC = id_kind.IdSpec(ID_TO_KIND_INTEGERS, BOOL_ARG_TYPES)

  id_kind.AddKinds(ID_SPEC)
  id_kind.AddBoolKinds(ID_SPEC)  # must come second

  id_kind.SetupTestBuiltin(ID_SPEC, TEST_UNARY_LOOKUP, TEST_BINARY_LOOKUP,
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
      f.write("""
#ifndef ID_KIND_ASDL_H
#define ID_KIND_ASDL_H

namespace id_kind_asdl {
""")

      v = gen_cpp.ClassDefVisitor(f, {}, e_suffix=False)
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

      v = gen_cpp.MethodDefVisitor(f, {}, e_suffix=False)
      v.VisitModule(schema_ast)

      f.write('}  // namespace id_kind_asdl\n')

  elif action == 'mypy':
    from asdl import gen_python

    schema_ast = _CreateModule(ID_SPEC, ids)
    #print(schema_ast)

    f = sys.stdout

    f.write("""\
from asdl import pybase
from typing import List

""")
    # Minor style issue: we want Id and Kind, not Id_e and Kind_e
    v = gen_python.GenMyPyVisitor(f, None, e_suffix=False,
                                  simple_int_sums=['Id'])
    v.VisitModule(schema_ast)

    f.write("""
ID_INSTANCES = [
  None,  # unused index 0
""")
    for name, _ in ids:
      f.write('  Id.%s,\n' % name)
    f.write(']  # type: List[Id_t]\n')

    f.write("""

KIND_INSTANCES = [
  None,  # unused index 0
""")
    for name in ID_SPEC.kind_name_list:
      f.write('  Kind.%s,\n' % name)
    f.write(']  # type: List[Kind_t]\n')

  elif action == 'cc-tables':
    pass

  elif action == 'py-tables':
    # It's kind of weird to use the generated code to generate more code.
    # Can we do this instead with the parsed module for "id" and "types.asdl"?

    from frontend.lookup import REDIR_DEFAULT_FD, REDIR_ARG_TYPES
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
    print('ID_TO_KIND_INTEGERS = {')
    for id_ in sorted(ID_TO_KIND_INTEGERS):
      v = Kind_str(ID_TO_KIND_INTEGERS[id_])
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
