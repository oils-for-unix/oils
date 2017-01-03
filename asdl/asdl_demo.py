#!/usr/bin/env python3
"""
asdl_demo.py
"""

import sys
from asdl import asdl_parse
from asdl import arith_parse
from asdl import py_meta
from asdl import encode
from asdl import format as fmt


def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  if action == 'py':
    schema_path = argv[2]

    module = asdl_parse.parse(schema_path)
    root = sys.modules[__name__]
    py_meta.MakeTypes(module, root)
    print(dir(root))

  elif action == 'arith-encode':
    expr = argv[2]
    out_path = argv[3]

    obj = arith_parse.ParseShell(expr)
    #print(obj)

    enc = encode.Params()
    with open(out_path, 'wb') as f:
      out = encode.BinOutput(f)
      encode.EncodeRoot(obj, enc, out)

  elif action == 'arith-format':
    expr = argv[2]

    obj = arith_parse.ParseShell(expr)
    #out = fmt.TextOutput(sys.stdout)
    tree = fmt.MakeTree(obj)
    #treee= ['hi', 'there', ['a', 'b'], 'c']
    fmt.PrintTree(tree, sys.stdout)

    # Might need to print the output?
    # out.WriteToFile?
  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
