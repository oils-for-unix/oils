#!/usr/bin/env python2
"""
expr_parse_test.py: Tests for expr_parse.py
"""
from __future__ import print_function

import unittest

#from _devbuild.gen import grammar_nt  # names for integer nonterminal IDs
from _devbuild.gen.id_kind_asdl import Kind
from _devbuild.gen.syntax_asdl import source

from core.meta import ID_SPEC
from core import alloc
from core import meta
from core import pyutil
from core.util import log
from frontend import parse_lib
from frontend import reader


class ExprParseTest(unittest.TestCase):

  def setUp(self):
    """Done on every test."""
    self.arena = alloc.Arena()
    self.arena.PushSource(source.Unused(''))
    parse_opts = parse_lib.OilParseOptions()

    loader = pyutil.GetResourceLoader()
    oil_grammar = meta.LoadOilGrammar(loader)

    self.parse_ctx = parse_lib.ParseContext(self.arena, parse_opts, {},
                                            oil_grammar, one_pass_parse=True)

  def _ParseOsh(self, code_str):
    """Parse a line of OSH, which can include Oil assignments."""
    line_reader = reader.StringLineReader(code_str, self.arena)
    # the OSH parser hooks into the Oil parser
    c_parser = self.parse_ctx.MakeOshParser(line_reader)
    node = c_parser.ParseLogicalLine()
    print('')
    log('\t%s', code_str)
    node.PrettyPrint()
    print('')
    return node

  def _ParseOilExpression(self, code_str):
    """Convenient shortcut."""
    node = self._ParseOsh('var x = %s\n' % code_str)

  def testPythonLike(self):
    # This works.
    node = self._ParseOsh('var x = y + 2 * 3;')

    # The lexer isn't handling single quotes yet.
    #node = self._ParseOsh(r"var x = 'one\ntwo\n';")

    # NOTE: C-escapes aren't parsed properly.
    node = self._ParseOsh(r'var x = "one\ntwo\n";')

    # These raise NotImplementedError

    node = self._ParseOsh('var x = [1,2,3];')
    node = self._ParseOilExpression('[4+5, 6+7*8]')
    node = self._ParseOilExpression('[]')

    node = self._ParseOilExpression('[x for x in y]')
    #node = self._ParseOilExpression('{foo: bar}')

  def testShellArrays(self):
    #return
    node = self._ParseOsh('var x = @(a b);')
    node = self._ParseOsh(r"var x = @('c' $'string\n');")
    node = self._ParseOsh(r"var x = @($(echo command) $(echo sub));")

    # Test out the DisallowedLineReader
    node = self._ParseOsh(r"""var x = @($(echo command <<EOF
EOF
))""")
    return

    node = self._ParseOsh('var x = $(echo hi);')

  def testOtherExpr(self):
    """Some examples copied from pgen2/pgen2-test.sh mode-test."""

    node = self._ParseOsh('@[1 2 3];')

    CASES = [
      '@[1 2 3]',
      '$/ x /',
      '$/ "." [a-z A-Z] y /',
      '$[echo hi]',
      #'$(1 + 2)',
      '${x}',
      '"quoted ${x}"',
    ]

    # array literal
    for c in CASES:
      node = self._ParseOilExpression(c)

  def testLexer(self):
    # NOTE: Kind.Expr for Oil doesn't have LexerPairs
    pairs = ID_SPEC.LexerPairs(Kind.Arith)
    for p in pairs:
      #print(p)
      pass


if __name__ == '__main__':
  unittest.main()
