#!/usr/bin/env python2
"""
grammar_gen.py - Use pgen2 to generate tables from Oil's grammar.
"""
from __future__ import print_function

import os
import sys

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.syntax_asdl import source

from core import alloc
from core import meta
from core.util import log
from frontend import lexer, match, reader, lex
from pgen2 import parse, pgen


# Used at grammar BUILD time.
OPS = {
    '(': Id.Op_LParen,
    ')': Id.Op_RParen,

    '[': Id.Op_LBracket,
    ']': Id.Op_RBracket,     # Problem: in OilOuter, this is OP_RBracket.
                             # OK I think the metalanguage needs to be
                             # extended to take something other than ']'
                             # It needs proper token names!
    '{': Id.Op_LBrace,
    '}': Id.Op_RBrace,
    ';': Id.Op_Semi,

    '$[': Id.Left_DollarBracket,
    '${': Id.Left_DollarBrace,
    '$(': Id.Left_DollarParen,
    '$/': Id.Left_DollarSlash,
    '@[': Id.Left_AtBracket,
    '@(': Id.Left_AtParen,

    '"': Id.Left_DoubleQuote,
    "'": Id.Left_SingleQuoteRaw,

    '.': Id.Expr_Dot,
    '->': Id.Expr_RArrow,
    '@': Id.Expr_At,

    # TODO: Add Ellipsis.
    '...': Id.Expr_Dot,

    # TODO: do we need div= and xor= ?
}

# TODO: We should be able to remove all these.
TERMINALS = {
    'NAME': Id.Expr_Name,

    # The grammar seems something like 'for' or '>='
    # These need to be looked up at "_Classify" time?
    #'STRING': Id.Expr_Name,

    'NEWLINE': Id.Op_Newline,
    'ENDMARKER': Id.Eof_Real,
}


if 0:  # unused because the grammar compile keeps track of keywords!
  KEYWORDS = {
      'div': Id.Expr_Div,
      'xor': Id.Expr_Xor,

      'and': Id.Expr_And,
      'or': Id.Expr_Or,
      'not': Id.Expr_Not,

      'for': Id.Expr_For,
      'is': Id.Expr_Is,
      'in': Id.Expr_In,
      'if': Id.Expr_If,
      'else': Id.Expr_Else,

      'match': Id.Expr_Match,
      'func': Id.Expr_Func,
  }


class OilTokenDef(object):

  def __init__(self, arith_ops):
    self.arith_ops = arith_ops

  def GetTerminalNum(self, label):
    """
    e.g. translate Expr_Name in the grammar to 178
    """
    id_ = TERMINALS.get(label) or getattr(Id, label)
    #log('Id %s = %d', id_, id_.enum_id)
    assert id_.enum_id < 256, id_
    return id_.enum_id

  def GetOpNum(self, value):
    id_ = OPS.get(value) or self.arith_ops[value]
    assert id_.enum_id < 256, id_
    return id_.enum_id


def MakeOilLexer(code_str, arena):
  arena.PushSource(source.MainFile('pgen2_main'))
  line_reader = reader.StringLineReader(code_str, arena)
  line_lexer = lexer.LineLexer(match.MATCHER, '', arena)
  lex = lexer.Lexer(line_lexer, line_reader)
  return lex


def main(argv):
  action = argv[1]
  argv = argv[2:]

  # Common initialization
  arith_ops = {}
  for _, token_str, id_ in meta.ID_SPEC.LexerPairs(Kind.Arith):
    arith_ops[token_str] = id_

  if 0:  # TODO: Enable this
    for _, token_str, id_ in lex.EXPR_WORDS:  # for, in, etc.
      arith_ops[token_str] = id_

  from pprint import pprint
  if 0:
    pprint(arith_ops)

  tok_def = OilTokenDef(arith_ops)

  if action == 'marshal':  # generate the grammar and parse it
    grammar_path = argv[0]
    out_dir = argv[1]

    basename, _ = os.path.splitext(os.path.basename(grammar_path))

    # HACK for find:
    if basename == 'find':
      from tools.find import tokenizer as find_tokenizer
      tok_def = find_tokenizer.TokenDef()

    with open(grammar_path) as f:
      gr = pgen.MakeGrammar(f, tok_def=tok_def)

    marshal_path = os.path.join(out_dir, basename + '.marshal')
    with open(marshal_path, 'wb') as out_f:
      gr.dump(out_f)

    nonterm_path = os.path.join(out_dir, basename + '_nt.py')
    with open(nonterm_path, 'w') as out_f:
      gr.dump_nonterminals(out_f)

    log('Compiled %s -> %s and %s', grammar_path, marshal_path, nonterm_path)
    #gr.report()

  elif action == 'parse':  # generate the grammar and parse it
    # Remove build dependency
    from frontend import parse_lib
    from oil_lang import expr_parse

    grammar_path = argv[0]
    start_symbol = argv[1]
    code_str = argv[2]

    # For choosing lexer and semantic actions
    grammar_name, _ = os.path.splitext(os.path.basename(grammar_path))

    with open(grammar_path) as f:
      gr = pgen.MakeGrammar(f, tok_def=tok_def)

    arena = alloc.Arena()
    lex_ = MakeOilLexer(code_str, arena)

    is_expr = grammar_name in ('calc', 'grammar')

    parse_opts = parse_lib.OilParseOptions()
    parse_ctx = parse_lib.ParseContext(arena, parse_opts, {}, gr)
    p = expr_parse.ExprParser(parse_ctx, gr)
    try:
      pnode, _ = p.Parse(lex_, gr.symbol2number[start_symbol])
    except parse.ParseError as e:
      log('Parse Error: %s', e)
      return 1

    names = parse_lib.MakeGrammarNames(gr)
    p_printer = expr_parse.ParseTreePrinter(names)  # print raw nodes
    p_printer.Print(pnode)

    if is_expr:
      from oil_lang import expr_to_ast
      tr = expr_to_ast.Transformer(gr)
      if start_symbol == 'eval_input':
        ast_node = tr.Expr(pnode)
      else:
        ast_node = tr.VarDecl(pnode)
      ast_node.PrettyPrint()
      print()

  elif action == 'stdlib-test':
    # This shows how deep Python's parse tree is.  It doesn't use semantic
    # actions to prune on the fly!

    import parser  # builtin module
    t = parser.expr('1+2')
    print(t)
    t2 = parser.st2tuple(t)
    print(t2)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
