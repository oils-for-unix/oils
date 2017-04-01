#!/usr/bin/env python3
"""
parse.py

"""

import os
import sys

from opy.pgen2 import driver
from opy.pgen2 import token, tokenize
from opy import pytree
from opy import pygram


def main(argv):

  # NOTE: Parsing tables are cached with pickle.
  # For Python 3.

  # lib2to3 had a flag for the print statement!  Don't use it with Python 3.

  if 'PYTHON2' in os.environ:
    grammar = pygram.python_grammar
  else:
    grammar = pygram.python_grammar_no_print_statement

  # TODO: Now hook convert to generate Python.asdl?
  #
  # or opy.asdl
  #
  # then maybe -> ovm.asdl to flatten loops?  Make .append special?
  #
  # YES: modules, classes, functions (kwargs), exceptions, generators, strings,
  # int list comprehensions, generator expressions, % string formatting,
  #   dicts/list runtime (append/extend)
  # assert
  #
  # metaprogramming: setattr() for core/id_kind.py.
  #
  # sparingly:
  #   I don't think lambda
  #   yield in asdl, tdop, and completion.  Hm.
  #
  # NO: complex numbers, async/await, global/nonlocal, I don't see any use of
  # with
  # 
  # Libraries: optparse, etc.

  d = driver.Driver(grammar, convert=pytree.convert)

  py_path = argv[1]
  with open(py_path) as f:
    tokens = tokenize.generate_tokens(f.readline)
    tree = d.parse_tokens(tokens)

  tree.PrettyPrint(sys.stdout)
  print('\tChildren: %d' % len(tree.children), file=sys.stderr)
  return
  print(tree)
  print(repr(tree))
  return

  #print(type(tree))
  for c in tree.children:
    print(repr(c))
    print()



  # Examples of nodes Leaf(type, value):
  #   Leaf(1, 'def')
  #   Leaf(4, '\n')
  #   Leaf(8, ')')
  # Oh are these just tokens?
  # yes.

  # Node(prefix, children)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
