#!/usr/bin/env python
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
from core.meta import ID_SPEC


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

def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  ids = list(ID_SPEC.id_names.iteritems())
  ids.sort(key=lambda pair: pair[0])  # Sort by ID

  if action == 'c':
    for i, name in ids:
      print('#define id__%s %s' % (name, i))

  elif action == 'mypy':
    from asdl import asdl_
    from asdl import gen_python

    #
    # Create a SYNTHETIC ASDL module, and generate code from it.
    #
    id_sum = asdl_.Sum([asdl_.Constructor(name) for _, name in ids])

    variants2 = [asdl_.Constructor(name) for name in ID_SPEC.kind_name_list]
    kind_sum = asdl_.Sum(variants2)

    id_ = asdl_.Type('Id', id_sum)
    kind_ = asdl_.Type('Kind', kind_sum)

    schema_ast = asdl_.Module('id_kind', [id_, kind_])
    #print(schema_ast)

    f = sys.stdout

    f.write("""\
from asdl import runtime
""")
    # Minor style issue: we want Id and Kind, not Id_e and Kind_e
    v = gen_python.GenMyPyVisitor(f, None, e_suffix=False)
    v.VisitModule(schema_ast)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
