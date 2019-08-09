#!/usr/bin/env python2
"""
typed_demo.py
"""
from __future__ import print_function

import sys

from _devbuild.gen import typed_demo_asdl

op_id_e = typed_demo_asdl.op_id_e

cflow = typed_demo_asdl.cflow
cflow_e = typed_demo_asdl.cflow_e
cflow__Return = typed_demo_asdl.cflow__Return
source_location = typed_demo_asdl.source_location

word = typed_demo_asdl.word
bool_expr = typed_demo_asdl.bool_expr
bool_expr_e = typed_demo_asdl.bool_expr_e

from typing import cast
from typing import List


def main(argv):
  # type: (List[str]) -> None

  op = op_id_e.Plus
  print(op)
  print(repr(op))

  n1 = cflow.Break()
  n2 = cflow.Return()  # hm I would like a type error here

  #n3 = cflow.Return('hi')  # type error, yay!
  n3 = cflow.Return(42)

  print(n1)
  print(n2)
  print(n3)

  nodes =[n1, n2, n3]
  #reveal_type(nodes)

  for n in nodes:
    print(n.tag)
    if n.tag == cflow_e.Return:
      print('Return = %s' % n)

      # Hm mypy doesn't like this one, but I think it should be equivalent.
      # type aliases are only at the top level?

      # https://github.com/python/mypy/issues/3855
      # This is closed by #5926 that emits a better error message, and accepts
      # safe use cases (e.g. when one nested class is a subclass of another
      # nested class).

      #reveal_type(n)
      #n2 = cast(cflow.Return, n)

      n2 = cast(cflow__Return, n)
      #reveal_type(n2)

      print('status = %s' % n2.status)

  loc = source_location('foo', 13, 0, 2)
  print(loc)


  w1 = word('w1')
  w2 = word('e2')
  b1 = bool_expr.Binary(w1, w2)
  b2 = bool_expr.LogicalNot(b1)
  print(b1)
  print(b2)

  b3 = bool_expr.LogicalBinary(op_id_e.Star, b1, b2)
  print(b3)
  #b4 = bool_expr.LogicalBinary(op_id_e.Star, b1, 'a')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
