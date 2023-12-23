#!/usr/bin/env python2
"""expr_parse_test.py: Tests for expr_parse.py."""
from __future__ import print_function

import unittest

from _devbuild.gen.syntax_asdl import source

from asdl import format as fmt
from core import alloc
from core import error
from core import pyutil
from core import test_lib
from mycpp.mylib import log
from frontend import reader


class ExprParseTest(unittest.TestCase):

    def setUp(self):
        """Done on every test."""
        self.arena = alloc.Arena()
        self.arena.PushSource(source.Unused(''))

        loader = pyutil.GetResourceLoader()
        ysh_grammar = pyutil.LoadYshGrammar(loader)

        self.parse_ctx = test_lib.InitParseContext(arena=self.arena,
                                                   ysh_grammar=ysh_grammar,
                                                   one_pass_parse=True)

    def _ParseOsh(self, code_str):
        """Parse a line of OSH, which can include Oil assignments."""
        line_reader = reader.StringLineReader(code_str, self.arena)
        # the OSH parser hooks into the Oil parser
        c_parser = self.parse_ctx.MakeOshParser(line_reader)
        node = c_parser.ParseLogicalLine()
        print('')
        log('\t%s', code_str)
        fmt.PrettyPrint(node)
        print('')
        return node

    def _ParseYshExpression(self, code_str):
        """Convenient shortcut."""
        node = self._ParseOsh('var x = %s\n' % code_str)

    def testPythonLike(self):
        # This works.
        node = self._ParseOsh('var x = y + 2 * 3;')

        node = self._ParseOsh(r"var x = r'one\ntwo\n';")
        node = self._ParseOsh(r"var x = $'one\ntwo\n';")

        node = self._ParseOsh(r'var x = "one\\ntwo\\n";')

        # These raise NotImplementedError()

        node = self._ParseOsh('var x = [1,2,3];')
        node = self._ParseYshExpression('[4+5, 6+7*8]')
        node = self._ParseYshExpression('[]')

        node = self._ParseYshExpression('[x for x in y]')
        #node = self._ParseYshExpression('{foo: bar}')

    def testShellArrays(self):
        node = self._ParseOsh('var x = %(a b);')
        node = self._ParseOsh(r"var x = %('c' $'string\n');")
        node = self._ParseOsh(r"var x = %($(echo command) $(echo sub));")

        # Can parse multiple arrays (this is a runtime error)
        node = self._ParseOsh(r"var x = %(a b) * %($c ${d});")

        # Can parse over multiple lines
        node = self._ParseOsh(r"""var x = %(
    a
    b
    c
    );""")

        # Test out the DisallowedLineReader
        self.assertRaises(error.Parse, self._ParseOsh,
                          r"""var x = %($(echo command <<EOF
EOF
))""")

    def testShellCommandSub(self):
        node = self._ParseOsh('var x = $(echo hi);')
        node = self._ParseOsh('var x = $(echo $(echo hi));')

        # This doesn't use the Reader, so it's allowed
        node = self._ParseOsh("""var x = $(echo
hi)
    """)

        # Here docs use the Reader, so aren't allowed
        self.assertRaises(error.Parse, self._ParseOsh, """var x = $(cat <<EOF
hi
EOF)
    """)

        node = self._ParseOsh('var x = $(echo $((1+2)));')
        node = self._ParseOsh('var x = $(for i in 1 2 3; do echo $i; done);')

        node = self._ParseOsh('var x = %(a b)')

        # TODO: Recursive 'var' shouldn't be allowed!
        return
        node = self._ParseOsh('var x = $(var x = %(a b););')
        node = self._ParseOsh('var x = $(var x = %(a b));')

    def testOtherExpr(self):
        """Some examples copied from pgen2/pgen2-test.sh mode-test."""

        CASES = [
            #'$/ x /',
            # TODO: Put this back after fixing double quoted strings in expression
            # mode.
            #'$/ "." [a-z A-Z] y /',
            #'$[echo hi]',
            '$(echo hi)',

            # TODO: Add these back
            '${x}',
            '"quoted ${x}"',
        ]

        # array literal
        for c in CASES:
            print('--- %s' % c)
            node = self._ParseYshExpression(c)

    def testLexer(self):
        CASES = [
            ("= x }", 4),
            ("= x;}", 3),
            ("= x; }", 3),
            ("echo $x;}", 8),
            ("echo $x; }", 8),
            ("= x\n}", 3),
            ("echo $x\n}", 8),
        ]

        for code_str, end_pos in CASES:
            line_reader = reader.StringLineReader(code_str, self.arena)
            cmd_parser = self.parse_ctx.MakeOshParser(line_reader)
            lexer = cmd_parser.lexer

            node = cmd_parser.ParseCommand()

            # Assert that we are at the RBrace. Ie,
            # 'x }\n'
            #    ^
            self.assertEqual(end_pos, lexer.line_lexer.line_pos)

            print("-----")
            print("%r" % lexer.line_lexer.src_line.content)
            print(" " * (lexer.line_lexer.line_pos + 1) + "^")
            print("-----")


if __name__ == '__main__':
    unittest.main()
