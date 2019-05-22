#!/usr/bin/python
"""
calc.py
"""
from __future__ import print_function

import cStringIO
import os
import sys

from opy.pgen2 import token
from opy.pgen2 import tokenize
from opy.pgen2 import driver, parse, pgen, grammar

from opy.opy_main import Symbols, ParseTreePrinter, log

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import source
from _devbuild.gen.types_asdl import lex_mode_e
from core import alloc
from frontend import lexer, match, reader


def CalcActions(gr, node):
  #log('%s', node)
  typ, value, context, children = node

  # collapse
  # hm this was so easy!  Why does it materialize so much then?
  # Does CPython do it, or only pgen2?
  # I think you already know
  if children is not None and len(children) == 1:
    return children[0]

  return node

SEMANTIC_ACTIONS = {
    'calc': CalcActions,
}


def MakeOilLexer(code_str, arena):
  arena.PushSource(source.MainFile('pgen2_main'))
  line_reader = reader.StringLineReader(code_str, arena)
  line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
  lex = lexer.Lexer(line_lexer, line_reader)
  return lex


def LexerWrapper(lex, arena):
  # reader doesn't have the line though
  while True:
    tok = lex.Read(lex_mode_e.Arith)
    print(token)
    if tok.id == Id.Eof_Real:
      raise StopIteration

    span = arena.GetLineSpan(tok.span_id)
    line_num = arena.GetLineNumber(span.line_id)

    start = (line_num, span.col)
    end = (line_num, span.col + span.length)
    line_text = arena.GetLine(span.line_id)

    yield (tok.id, tok.val, start, end, line_text)


def main(argv):
  action = argv[1]
  argv = argv[2:]

  if action == 'parse':
    grammar_path = argv[0]
    start_symbol = argv[1]
    code_str = argv[2]

    f = cStringIO.StringIO(code_str)
    gr = pgen.generate_grammar(grammar_path)

    symbols = Symbols(gr)
    #pytree.Init(symbols)  # for type_repr() pretty printing

    # next() and StopIteration is the interface
    # I guess I could change it to yield?  OK sure.

    if 0:
      tokens = tokenize.generate_tokens(f.readline)
    else:
      arena = alloc.Arena()
      lex = MakeOilLexer(code_str, arena)
      tokens = LexerWrapper(lex, arena)

      # NOTE: This lexer has Id.Arith_Plus
      # AddToken
      # translations:
      # driver.py
      #   OP type -> grammar.opmap type
      # parse.py
      #   classify takes NAME -> grammar.keywords or grammar.tokens
      #
      # OK fair enough
      # You have to interject these when parsing
      #
      # pgen.py: make_label adds to c.tokens and c.keywords

    # Semantic actions are registered in this code.
    grammar_name, _ = os.path.splitext(os.path.basename(grammar_path))
    p = parse.Parser(gr, convert=SEMANTIC_ACTIONS.get(grammar_name))

    try:
      parse_tree = driver.PushTokens(p, tokens, gr.symbol2number[start_symbol])
    except parse.ParseError as e:
      # Extract location information and show it.
      unused, (lineno, offset) = e.context
      # extra line needed for '\n' ?
      lines = code_str.splitlines() + ['']

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

  elif action == 'stdlib-test':
    # This shows how deep Python's parse tree is.  It doesn't use semantic
    # actions to prune on the fly!

    import parser
    t = parser.expr('1+2')
    print(t)
    t2 = parser.st2tuple(t)
    print(t2)

  else:
    raise RuntimeError('Invalid actio %r' % action)



if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
