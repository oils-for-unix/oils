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
from core import optview
from mycpp.mylib import log
from frontend import lexer
from frontend import lexer_def
from frontend import reader
from pgen2 import parse, pgen, token


class OilTokenDef(object):

    def __init__(self, ops, more_ops, keyword_ops):
        self.ops = ops
        self.more_ops = more_ops
        self.keyword_ops = keyword_ops

    def GetTerminalNum(self, label):
        """e.g. translate Expr_Name in the grammar to 178."""
        id_ = getattr(Id, label)
        #log('Id %s = %d', id_, id_)
        assert id_ < token.NT_OFFSET, id_
        return id_

    def GetKeywordNum(self, s):
        """e.g 'xor' -> Id.Expr_Xor.

        Python doesn't have this, but Oil does.  Returns None if not
        found.
        """
        id_ = self.keyword_ops.get(s)
        if id_ is None:
            return None
        assert id_ < token.NT_OFFSET, id_
        return id_

    def GetOpNum(self, op_str):
        """
        Args:
          op_str: '>='

        Returns:
          Integer for '>=' or Id.Arith_GreatEqual
        """
        # Fail if not there
        id_ = self.ops.get(op_str) or self.more_ops[op_str]
        assert id_ < token.NT_OFFSET, id_
        return id_


def MakeOilLexer(code_str, arena):
    arena.PushSource(source.MainFile('pgen2_main'))
    line_reader = reader.StringLineReader(code_str, arena)
    line_lexer = lexer.LineLexer(arena)
    lex = lexer.Lexer(line_lexer, line_reader)
    return lex


def main(argv):
    action = argv[1]
    argv = argv[2:]

    # Used at grammar BUILD time.
    OPS = {
        '!': Id.Expr_Bang,
        '.': Id.Expr_Dot,
        '..=': Id.Expr_DDotEqual,
        '..<': Id.Expr_DDotLessThan,
        '->': Id.Expr_RArrow,
        '=>': Id.Expr_RDArrow,
        '//': Id.Expr_DSlash,
        '++': Id.Arith_DPlus,
        '!~': Id.Expr_NotTilde,
        '~~': Id.Expr_DTilde,
        '!~~': Id.Expr_NotDTilde,
        '~==': Id.Expr_TildeDEqual,
        '===': Id.Expr_TEqual,
        '!==': Id.Expr_NotDEqual,
        '@': Id.Expr_At,
        '...': Id.Expr_Ellipsis,
        '$': Id.Expr_Dollar,  # Only for legacy eggex /d+$/
        '**=': Id.Expr_DStarEqual,
        '//=': Id.Expr_DSlashEqual,
    }

    # Note: We have two lists of ops because Id.Op_Semi is used, not
    # Id.Arith_Semi.
    for _, token_str, id_ in lexer_def.EXPR_OPS:
        assert token_str not in OPS, token_str
        OPS[token_str] = id_

    # Tokens that look like / or ${ or @{
    triples = (lexer_def.ID_SPEC.LexerPairs(Kind.Arith) +
               lexer_def.YSH_LEFT_SUBS + lexer_def.YSH_LEFT_UNQUOTED +
               lexer_def.EXPR_WORDS)
    more_ops = {}
    for _, token_str, id_ in triples:
        if token_str in more_ops:
            import pprint
            raise AssertionError(
                '%r %s' % (token_str, pprint.pformat(more_ops, indent=2)))
        more_ops[token_str] = id_

    # Tokens that look like 'for'
    keyword_ops = {}
    for _, token_str, id_ in lexer_def.EXPR_WORDS:  # for, in, etc.
        assert token_str not in keyword_ops, token_str
        keyword_ops[token_str] = id_

    if 0:
        from pprint import pprint
        pprint(OPS)
        print('---')
        pprint(more_ops)
        print('---')
        pprint(keyword_ops)
        print('---')

    tok_def = OilTokenDef(OPS, more_ops, keyword_ops)

    if action == 'py':  # generate the grammar and parse it
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

        nonterm_py = os.path.join(out_dir, basename + '_nt.py')
        with open(nonterm_py, 'w') as out_f:
            gr.dump_nonterminals_py(out_f)

        log('%s -> (ysh/grammar_gen) -> %s/%s{.marshal,_nt.py}', grammar_path,
            out_dir, basename)

        #gr.report()

    elif action == 'cpp':  # generate the grammar and parse it
        grammar_path = argv[0]
        out_dir = argv[1]

        basename, _ = os.path.splitext(os.path.basename(grammar_path))

        with open(grammar_path) as f:
            gr = pgen.MakeGrammar(f, tok_def=tok_def)

        nonterm_h = os.path.join(out_dir, basename + '_nt.h')
        with open(nonterm_h, 'w') as out_f:
            gr.dump_nonterminals_cpp(out_f)

        grammar_cpp_path = os.path.join(out_dir, basename + '_tables.cc')
        with open(grammar_cpp_path, 'w') as src_f:
            gr.dump_cpp(src_f)

        if 0:
            log('%s -> (ysh/grammar_gen) -> %s/%s._nt.h', grammar_path,
                out_dir, basename)

    elif action == 'parse':  # generate the grammar and parse it
        # Remove build dependency
        from frontend import parse_lib
        from ysh import expr_parse
        from ysh import expr_to_ast

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

        parse_opts = optview.Parse([], [])
        parse_ctx = parse_lib.ParseContext(arena, parse_opts, {}, gr)
        p = expr_parse.ExprParser(parse_ctx, gr, False)
        try:
            with expr_parse.ctx_PNodeAllocator(p):
                pnode, _ = p.Parse(lex_, gr.symbol2number[start_symbol])
        except parse.ParseError as e:
            log('Parse Error: %s', e)
            return 1

        names = expr_to_ast.MakeGrammarNames(gr)
        p_printer = expr_parse.ParseTreePrinter(names)  # print raw nodes
        p_printer.Print(pnode)

        if is_expr:
            tr = expr_to_ast.Transformer(gr)
            if start_symbol == 'eval_input':
                ast_node = tr.Expr(pnode)
            elif start_symbol == 'ysh_case_pat':
                ast_node = tr.YshCasePattern(pnode)
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
