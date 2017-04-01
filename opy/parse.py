#!/usr/bin/env python3
"""
parse.py

"""

import io
import os
import sys

from pgen2 import driver
from pgen2 import token, tokenize
import pytree
from compiler import transformer
from compiler import pycodegen


# From lib2to3/pygram.py.  This presumably takes the place of the 'symbol'
# module.  Could we hook it up elsewhere?
#
# compiler/transformer module needs this.
# tools/compile.py runs compileFile, which runs parseFile.

class Symbols(object):

    def __init__(self, grammar):
        """Initializer.

        Creates an attribute for each grammar symbol (nonterminal),
        whose value is the symbol's type (an int >= 256).
        """
        for name, symbol in grammar.symbol2number.items():
            setattr(self, name, symbol)
            #print('%s -> %d' % (name, symbol))
        # For transformer to use
        self.number2symbol = grammar.number2symbol
        #assert 0


def HostStdlibNames():
  import symbol
  import token
  names = {}
  for k, v in symbol.sym_name.items():
    names[k] = v
  for k, v in token.tok_name.items():
    names[k] = v
  return names


# Emulate the interface that Transformer expects from parsermodule.c.
class Pgen2PythonParser:
  def __init__(self, driver, start_symbol):
    self.driver = driver
    self.start_symbol = start_symbol

  def suite(self, text):
    f = io.StringIO(text)
    tokens = tokenize.generate_tokens(f.readline)
    tree = self.driver.parse_tokens(tokens, start_symbol=self.start_symbol)
    return tree


def main(argv):
  grammar_path = argv[1]
  # NOTE: This is cached as a pickle
  grammar = driver.load_grammar(grammar_path)
  FILE_INPUT = grammar.symbol2number['file_input']

  symbols = Symbols(grammar)
  pytree.Init(symbols)  # for type_repr() pretty printing
  transformer.Init(symbols)  # for _names and other dicts

  if 'PYTHON2' in os.environ:
    pass
  else:
    # lib2to3 had a flag for the print statement!  Don't use it with Python 3.
    del grammar.keywords["print"]

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

  do_glue = False
  do_glue = True

  if do_glue:  # Make it a flag
    # Emulating parser.st structures from parsermodule.c.
    # They have a totuple() method, which outputs tuples like this.
    def py2st(grammar, raw_node):
      type, value, context, children = raw_node
      # See pytree.Leaf
      if context:
        _, (lineno, column) = context
      else:
        lineno = 0  # default in Leaf
        column = 0

      if children:
        return (type,) + tuple(children)
      else:
        return (type, value, lineno, column)
    convert = py2st
  else:
    convert = pytree.convert

  d = driver.Driver(grammar, convert=convert)

  action = argv[2]

  if action == 'stdlib-parse':
    # This is what the compiler/ package was written against.
    import parser

    py_path = argv[3]
    with open(py_path) as f:
      st = parser.suite(f.read())

    tree = st.totuple()

    n = transformer.CountTupleTree(tree)
    print('COUNT', n)
    printer = transformer.TupleTreePrinter(HostStdlibNames())
    printer.Print(tree)

  elif action == 'parse':
    py_path = argv[3]
    with open(py_path) as f:
      tokens = tokenize.generate_tokens(f.readline)
      tree = d.parse_tokens(tokens, start_symbol=FILE_INPUT)

    if isinstance(tree, tuple):
      n = transformer.CountTupleTree(tree)
      print('COUNT', n)

      printer = transformer.TupleTreePrinter(transformer._names)
      printer.Print(tree)
    else:
      tree.PrettyPrint(sys.stdout)
      print('\tChildren: %d' % len(tree.children), file=sys.stderr)

  elif action == 'compile':

    DISPLAY = 0  # debugging?
    py_path = argv[3]
    out_path = argv[4]
    if do_glue:
      py_parser = Pgen2PythonParser(d, FILE_INPUT)
      printer = transformer.TupleTreePrinter(transformer._names)
      tr = transformer.Pgen2Transformer(py_parser, printer)
    else:
      tr = transformer.Transformer()

    #pycodegen.compileFile(py_path, transformer=tr)

    # Not file_input instead of single_input?  Why is this not a Module?
    # Because you 

    with open(py_path) as f:
      contents = f.read()
      co = pycodegen.compile(contents, py_path, 'exec', transformer=tr)
      file_size = os.path.getsize(py_path)
    print(co)
    with open(out_path, 'wb') as out_f:
      pycodegen.WritePyc(co, py_path, out_f)

  else: 
    raise RuntimeError('Invalid action %r' % action)

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
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
