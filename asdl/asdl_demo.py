#!/usr/bin/env python
from __future__ import print_function
"""
asdl_demo.py
"""

import sys
from asdl import asdl_ as asdl
from asdl import arith_parse
from asdl import py_meta
from asdl import encode
from asdl import format as fmt

from core.id_kind import Id
from core.util import log


def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  if action == 'py':  # Prints the module
    schema_path = argv[2]

    with open(schema_path) as f:
      module = asdl.parse(f)

    app_types = {'id': asdl.UserType(Id)}
    type_lookup = asdl.ResolveTypes(module, app_types)

    # Note this is a big tree.  But we really want a graph of pointers to
    # instances.
    # Type(name, Product(...))
    # Type(name, Sum([Constructor(...), ...]))
    #print(module)

    root = sys.modules[__name__]
    # NOTE: We shouldn't pass in app_types for arith.asdl, but this is just a
    # demo.
    py_meta.MakeTypes(module, root, type_lookup)

    print('Dynamically created a Python module with these types:')
    for name in dir(root):
      print('\t' + name)

  elif action == 'arith-encode':  # oheap encoding
    expr = argv[2]
    out_path = argv[3]

    obj = arith_parse.ParseShell(expr)
    print('Encoding %r into binary:' % expr)
    print(obj)

    enc = encode.Params()
    with open(out_path, 'wb') as f:
      out = encode.BinOutput(f)
      encode.EncodeRoot(obj, enc, out)

  elif action == 'arith-format':  # pretty printing
    expr = argv[2]

    obj = arith_parse.ParseShell(expr)
    #out = fmt.TextOutput(sys.stdout)
    tree = fmt.MakeTree(obj)
    #treee= ['hi', 'there', ['a', 'b'], 'c']
    f = fmt.DetectConsoleOutput(sys.stdout)
    fmt.PrintTree(tree, f)
    print()

    # Might need to print the output?
    # out.WriteToFile?

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %r' % e, file=sys.stderr)
    sys.exit(1)
