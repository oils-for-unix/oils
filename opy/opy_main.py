#!/usr/bin/python
"""
parse.py
"""
from __future__ import print_function

import codecs
import io
import os
import sys
import marshal

from pgen2 import driver
from pgen2 import token, tokenize
import pytree
from compiler import transformer
from compiler import pycodegen
from compiler import opcode27
from util import log
import util


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
            #log('%s -> %d' % (name, symbol))
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


_READ_SOURCE_AS_UNICODE = True
# Not sure why this doesn't work?  It should be more like what the compiler
# module expected.
#_READ_SOURCE_AS_UNICODE = False

# Emulate the interface that Transformer expects from parsermodule.c.
class Pgen2PythonParser:
  def __init__(self, driver, start_symbol):
    self.driver = driver
    self.start_symbol = start_symbol

  def suite(self, text):
    #if util.PY2:
    if _READ_SOURCE_AS_UNICODE:
      f = io.StringIO(text)
    else:
      import cStringIO
      f = cStringIO.StringIO()
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

  # In Python 2 code, always use from __future__ import print_function.
  try:
    del grammar.keywords["print"]
  except KeyError:
    pass

  #do_glue = False
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
    log('COUNT %d', n)
    printer = transformer.TupleTreePrinter(HostStdlibNames())
    printer.Print(tree)

  elif action == 'parse':
    py_path = argv[3]
    with open(py_path) as f:
      tokens = tokenize.generate_tokens(f.readline)
      tree = d.parse_tokens(tokens, start_symbol=FILE_INPUT)

    if isinstance(tree, tuple):
      n = transformer.CountTupleTree(tree)
      log('COUNT %d', n)

      printer = transformer.TupleTreePrinter(transformer._names)
      printer.Print(tree)
    else:
      tree.PrettyPrint(sys.stdout)
      log('\tChildren: %d' % len(tree.children), file=sys.stderr)

  elif action == 'compile':
    py_path = argv[3]
    out_path = argv[4]

    if do_glue:
      py_parser = Pgen2PythonParser(d, FILE_INPUT)
      printer = transformer.TupleTreePrinter(transformer._names)
      tr = transformer.Pgen2Transformer(py_parser, printer)
    else:
      tr = transformer.Transformer()

    # for Python 2.7 compatibility:
    if _READ_SOURCE_AS_UNICODE:
      f = codecs.open(py_path, encoding='utf-8')
    else:
      f = open(py_path)

    contents = f.read()
    co = pycodegen.compile(contents, py_path, 'exec', transformer=tr)
    file_size = os.path.getsize(py_path)
    log("Code length: %d", len(co.co_code))

    # Write the .pyc file
    with open(out_path, 'wb') as out_f:
      h = pycodegen.getPycHeader(py_path)
      out_f.write(h)
      marshal.dump(co, out_f)

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
    log('FATAL: %s', e)
    sys.exit(1)
