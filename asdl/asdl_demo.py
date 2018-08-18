#!/usr/bin/env python
from __future__ import print_function
"""
asdl_demo.py
"""

import sys
from asdl import asdl_ as asdl
from asdl import front_end
from asdl import arith_parse
from asdl import py_meta
from asdl import encode
from asdl import format as fmt

from osh.meta import Id
from core import util

log = util.log


def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  if action == 'py':  # Prints the module
    # Called by asdl/run.sh py-cpp

    schema_path = argv[2]
    app_types = {'id': asdl.UserType(Id)}
    with open(schema_path) as f:
      schema_ast, type_lookup = front_end.LoadSchema(f, app_types)

    root = sys.modules[__name__]
    # NOTE: We shouldn't pass in app_types for arith.asdl, but this is just a
    # demo.
    py_meta.MakeTypes(schema_ast, root, type_lookup)

    log('AST for this ASDL schema:')
    schema_ast.Print(sys.stdout, 0)
    print()

    log('Dynamically created a Python module with these types:')
    for name in dir(root):
      print('\t' + name)

    if 1:
      # NOTE: It can be pickled, but not marshaled
      import marshal
      import cPickle
      print(dir(marshal))
      out_path = schema_path + '.pickle'
      with open(out_path, 'w') as f:
        #marshal.dump(type_lookup, f)
        # Version 2 is the highest protocol for Python 2.7.
        cPickle.dump(type_lookup.runtime_type_lookup, f, protocol=2)

      print('runtime_type_lookup:')
      for name, desc in type_lookup.runtime_type_lookup.items():
        print(name)
        print(desc)
      print()
      print('Wrote %s' % out_path)

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
