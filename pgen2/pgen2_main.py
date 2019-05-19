#!/usr/bin/python
"""
calc.py
"""
from __future__ import print_function

import cStringIO
import sys

from opy.pgen2 import token
from opy.pgen2 import tokenize
from opy.pgen2 import driver, parse, pgen, grammar

from opy.opy_main import Symbols, ParseTreePrinter, log


def main(argv):
  action = argv[1]
  argv = argv[2:]
  if action == 'parse':
    grammar_path = argv[0]
    start_symbol = argv[1]
    expr = argv[2]

    f = cStringIO.StringIO(expr)
    gr = pgen.generate_grammar(grammar_path)

    symbols = Symbols(gr)
    #pytree.Init(symbols)  # for type_repr() pretty printing

    tokens = tokenize.generate_tokens(f.readline)

    # TODO: convert could be a big list of semantic actions.

    #print(tokens)
    #p = parse.Parser(gr, convert=skeleton.py2st)

    p = parse.Parser(gr)

    try:
      parse_tree = driver.PushTokens(p, tokens, gr.symbol2number[start_symbol])
    except parse.ParseError as e:
      # Extract location information and show it.
      unused, (lineno, offset) = e.context
      # extra line needed for '\n' ?
      lines = expr.splitlines() + ['']

      line = lines[lineno-1]
      log('  %s', line)
      log('  %s^', ' '*offset)
      log('Parse Error: %s', e)
      return 1

    #n = CountTupleTree(parse_tree)
    #log('%r => %d nodes', expr, n)

    if 1:
      # NOTE: Similar work for Python is done in transformer.Init()
      names = {}
      for k, v in token.tok_name.items():
          names[k] = v
      for k, v in gr.number2symbol.items():
          names[k] = v

      printer = ParseTreePrinter(names)  # print raw nodes
      printer.Print(parse_tree)
      print()



if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
