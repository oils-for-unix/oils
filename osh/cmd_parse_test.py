#!/usr/bin/env python2
"""
cmd_parse_test.py: Tests for cmd_parse.py
"""

import unittest

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import command_e
from core import error
from core import test_lib
from core import ui

from osh import word_


def _assertParseMethod(test, code_str, method, expect_success=True):
  arena = test_lib.MakeArena('<cmd_parse_test>')
  c_parser = test_lib.InitCommandParser(code_str, arena=arena)
  m = getattr(c_parser, method)
  try:
    node = m()

  except error.Parse as e:
    ui.PrettyPrintError(e, arena)
    if expect_success:
      test.fail('%r failed' % code_str)
    node = None
  else:
    node.PrettyPrint()
    if not expect_success:
      test.fail('Expected %r to fail ' % code_str)

  return node


def _assert_ParseCommandListError(test, code_str):
  arena = test_lib.MakeArena('<cmd_parse_test>')
  c_parser = test_lib.InitCommandParser(code_str, arena=arena)

  try:
    node = c_parser._ParseCommandLine()
  except error.Parse as e:
    ui.PrettyPrintError(e, arena)
  else:
    print('UNEXPECTED:')
    node.PrettyPrint()
    test.fail("Expected %r to fail" % code_str)


#
# Successes
#
# (These differences might not matter, but preserve the diversity for now)

def assertParseSimpleCommand(test, code_str):
  return _assertParseMethod(test, code_str, 'ParseSimpleCommand')

def assertParsePipeline(test, code_str):
  return _assertParseMethod(test, code_str, 'ParsePipeline')

def assertParseAndOr(test, code_str):
  return _assertParseMethod(test, code_str, 'ParseAndOr')

def assert_ParseCommandLine(test, code_str):
  return _assertParseMethod(test, code_str, '_ParseCommandLine')

def assert_ParseCommandList(test, code_str):
  node = _assertParseMethod(test, code_str, '_ParseCommandList')
  if len(node.children) == 1:
    return node.children[0]
  else:
    return node

def assertParseRedirect(test, code_str):
  return _assertParseMethod(test, code_str, 'ParseRedirect')

#
# Failures
#

#def assertFailSimpleCommand(test, code_str):
#  return _assertParseMethod(test, code_str, 'ParseSimpleCommand',
#      expect_success=False)
#
#def assertFailCommandLine(test, code_str):
#  return _assertParseMethod(test, code_str, '_ParseCommandLine',
#      expect_success=False)

def assertFailCommandList(test, code_str):
  return _assertParseMethod(test, code_str, '_ParseCommandList',
      expect_success=False)

#def assertFailRedirect(test, code_str):
#  return _assertParseMethod(test, code_str, 'ParseRedirect',
#      expect_success=False)


class SimpleCommandTest(unittest.TestCase):

  def testParseSimpleCommand1(self):
    node = assertParseSimpleCommand(self, 'ls foo')
    self.assertEqual(2, len(node.words), node.words)

    node = assertParseSimpleCommand(self, 'FOO=bar ls foo')
    self.assertEqual(2, len(node.words))
    self.assertEqual(1, len(node.more_env))

    node = assertParseSimpleCommand(self,
        'FOO=bar >output.txt SPAM=eggs ls foo')
    self.assertEqual(2, len(node.words))
    self.assertEqual(2, len(node.more_env))
    self.assertEqual(1, len(node.redirects))

    node = assertParseSimpleCommand(self,
        'FOO=bar >output.txt SPAM=eggs ls foo >output2.txt')
    self.assertEqual(2, len(node.words))
    self.assertEqual(2, len(node.more_env))
    self.assertEqual(2, len(node.redirects))

  def testMultipleGlobalShAssignments(self):
    node = assert_ParseCommandList(self, 'ONE=1 TWO=2')
    self.assertEqual(command_e.ShAssignment, node.tag)
    self.assertEqual(2, len(node.pairs))

  def testOnlyRedirect(self):
    # This just touches the file
    node = assert_ParseCommandList(self, '>out.txt')
    self.assertEqual(command_e.Simple, node.tag)
    self.assertEqual(0, len(node.words))
    self.assertEqual(1, len(node.redirects))

  def testParseRedirectInTheMiddle(self):
    node = assert_ParseCommandList(self, 'echo >out.txt 1 2 3')
    self.assertEqual(command_e.Simple, node.tag)
    self.assertEqual(4, len(node.words))
    self.assertEqual(1, len(node.redirects))

  def testParseRedirectBeforeShAssignment(self):
    # Write ENV to a file
    node = assert_ParseCommandList(self, '>out.txt PYTHONPATH=. env')
    self.assertEqual(command_e.Simple, node.tag)
    self.assertEqual(1, len(node.words))
    self.assertEqual(1, len(node.redirects))
    self.assertEqual(1, len(node.more_env))

  def testParseAdjacentDoubleQuotedWords(self):
    node = assertParseSimpleCommand(self, 'echo "one"two "three""four" five')
    self.assertEqual(4, len(node.words))


class OldStaticParsing(object):

  def testRedirectsInShAssignment(self):
    err = _assert_ParseCommandListError(self, 'x=1 >/dev/null')
    err = _assert_ParseCommandListError(self, 'echo hi; x=1 >/dev/null')
    err = _assert_ParseCommandListError(self, 'declare  x=1 >/dev/null')

  def testParseShAssignment(self):
    node = assert_ParseCommandList(self, 'local foo=bar spam eggs one=1')
    self.assertEqual(4, len(node.pairs))

    node = assert_ParseCommandList(self, 'foo=bar')
    self.assertEqual(1, len(node.pairs))

    # This is not valid since env isn't respected
    assertFailCommandList(self, 'FOO=bar local foo=$(env)')


  def testExport(self):
    # This is the old static parsing.  Probably need to revisit.
    return
    node = assert_ParseCommandList(self, 'export ONE=1 TWO=2 THREE')
    self.assertEqual(command_e.ShAssignment, node.tag)
    self.assertEqual(3, len(node.pairs))

  def testReadonly(self):
    return
    node = assert_ParseCommandList(self, 'readonly ONE=1 TWO=2 THREE')
    self.assertEqual(command_e.ShAssignment, node.tag)
    self.assertEqual(3, len(node.pairs))


def assertHereDocToken(test, expected_token_val, node):
  """A sanity check for some ad hoc tests."""
  test.assertEqual(1, len(node.redirects))
  h = node.redirects[0]
  test.assertEqual(expected_token_val, h.stdin_parts[0].val)


class HereDocTest(unittest.TestCase):
  """NOTE: These ares come from tests/09-here-doc.sh, but add assertions."""

  def testUnquotedHereDoc(self):
    # Unquoted here docs use the double quoted context.
    node = assert_ParseCommandLine(self, """\
cat <<EOF
$v
"two
EOF
""")
    self.assertEqual(1, len(node.redirects))
    h = node.redirects[0]
    # 4 literal parts: VarSub, newline, right ", "two\n"
    self.assertEqual(4, len(h.stdin_parts))

  def testQuotedHereDocs(self):
    # Quoted here doc
    node = assert_ParseCommandLine(self, """\
cat <<"EOF"
$v
"two
EOF
""")
    self.assertEqual(1, len(node.redirects))
    h = node.redirects[0]
    self.assertEqual(2, len(h.stdin_parts))  # 2 literal parts

    node = assert_ParseCommandLine(self, """\
cat <<'EOF'
single-quoted: $var
EOF
""")
    self.assertEqual(1, len(node.redirects))
    h = node.redirects[0]
    self.assertEqual(1, len(h.stdin_parts))  # 1 line, one literal part

    # \ escape
    node = assert_ParseCommandLine(self, r"""\
cat <<EO\F
single-quoted: $var
EOF
""")
    self.assertEqual(1, len(node.redirects))
    h = node.redirects[0]
    self.assertEqual(1, len(h.stdin_parts))  # 1 line, one literal part

  def testLeadingTabs(self):
    node = assert_ParseCommandLine(self, """\
\tcat <<-EOF
\tone tab then foo: $foo
\tEOF
echo hi
""")
    self.assertEqual(node.tag, command_e.Simple)
    assertHereDocToken(self, 'one tab then foo: ', node)

  def testHereDocInPipeline(self):
    # Pipe and command on SAME LINE
    node = assert_ParseCommandLine(self, """\
cat <<EOF | tac
PIPE 1
PIPE 2
EOF
""")
    self.assertEqual(2, len(node.children))
    assertHereDocToken(self, 'PIPE 1\n', node.children[0])

    # Pipe command AFTER here doc
    node = assert_ParseCommandLine(self, """\
cat <<EOF |
PIPE 1
PIPE 2
EOF
tac
""")
    self.assertEqual(2, len(node.children))
    assertHereDocToken(self, 'PIPE 1\n', node.children[0])

  def testTwoHereDocsInPipeline(self):
    # Pipeline with two here docs
    node = assert_ParseCommandList(self, """\
cat <<EOF1 | tac <<EOF2
PIPE A1
PIPE A2
EOF1
PIPE B1
PIPE B2
EOF2
""")
    self.assertEqual(2, len(node.children))
    assertHereDocToken(self, 'PIPE A1\n', node.children[0])
    assertHereDocToken(self, 'PIPE B1\n', node.children[1])

  def testHereDocInAndOrChain(self):
    # || command AFTER here doc
    node = assert_ParseCommandLine(self, """\
cat <<EOF ||
PIPE 1
PIPE 2
EOF
echo hi
""")
    self.assertEqual(2, len(node.children))
    assertHereDocToken(self, 'PIPE 1\n', node.children[0])

    # && and command on SAME LINE
    node = assert_ParseCommandLine(self, """\
cat <<EOF && echo hi
PIPE 1
PIPE 2
EOF
""")
    self.assertEqual(2, len(node.children))
    assertHereDocToken(self, 'PIPE 1\n', node.children[0])

    node = assert_ParseCommandLine(self, """\
tac <<EOF1 && tac <<EOF2
PIPE A1
PIPE A2
EOF1
PIPE B1
PIPE B2
EOF2
echo
""")
    self.assertEqual(2, len(node.children))
    assertHereDocToken(self, 'PIPE A1\n', node.children[0])
    assertHereDocToken(self, 'PIPE B1\n', node.children[1])

  def testHereDocInSequence(self):
    # PROBLEM: _ParseCommandList vs _ParseCommandLine
    # _ParseCommandLine only used interactively.  _ParseCommandList is used by
    # ParseFile.

    # command AFTER here doc
    node = assert_ParseCommandList(self, """\
cat <<EOF ;
PIPE 1
PIPE 2
EOF
echo hi
""")
    self.assertEqual(node.tag, command_e.CommandList)
    self.assertEqual(2, len(node.children), repr(node))
    assertHereDocToken(self, 'PIPE 1\n', node.children[0].child)

  def testHereDocInSequence2(self):
    # ; and command on SAME LINE
    node = assert_ParseCommandList(self, """\
cat <<EOF ; echo hi
PIPE 1
PIPE 2
EOF
""")
    self.assertEqual(node.tag, command_e.CommandList)
    self.assertEqual(2, len(node.children))
    assertHereDocToken(self, 'PIPE 1\n', node.children[0].child)

  def testCommandSubInHereDoc(self):
    node = assert_ParseCommandLine(self, """\
cat <<EOF
1 $(echo 2
echo 3) 4
EOF
""")
    self.assertEqual(1, len(node.words))
    self.assertEqual(1, len(node.redirects))


class ArrayTest(unittest.TestCase):

  def testArrayLiteral(self):
    # Empty array
    node = assert_ParseCommandList(self,
        'empty=()')
    self.assertEqual(['empty'], [p.lhs.name for p in node.pairs])
    self.assertEqual([], node.pairs[0].rhs.parts[0].words)  # No words
    self.assertEqual(command_e.ShAssignment, node.tag)

    # Array with 3 elements
    node = assert_ParseCommandList(self,
        'array=(a b c)')
    self.assertEqual(['array'], [p.lhs.name for p in node.pairs])
    self.assertEqual(3, len(node.pairs[0].rhs.parts[0].words))
    self.assertEqual(command_e.ShAssignment, node.tag)

    # Array literal can't come after word
    # Now caught at runtime
    #assertFailCommandList(self,
    #    'ls array=(a b c)')

    # Word can't come after array literal
    assertFailCommandList(self,
        'array=(a b c) ls')

    # Two array literals
    node = assert_ParseCommandList(self,
        'array=(a b c); array2=(d e f)')
    self.assertEqual(2, len(node.children))
    a2 = node.children[1]
    self.assertEqual(['array2'], [p.lhs.name for p in a2.pairs])


class RedirectTest(unittest.TestCase):

  def testParseRedirects1(self):
    node = assertParseSimpleCommand(self, '>out.txt cat 1>&2')
    self.assertEqual(1, len(node.words))
    self.assertEqual(2, len(node.redirects))

    node = assertParseSimpleCommand(self, ' cat <&3')
    self.assertEqual(1, len(node.redirects))

  def testParseFilenameRedirect(self):
    node = assertParseRedirect(self, '>out.txt cat')

  def testDescriptorRedirect(self):
    node = assertParseRedirect(self, '1>& 2 cat')

  def testHereDoc(self):
    node = assertParseRedirect(self, """\
<<EOF cat
hi
EOF
""")

  def testHereDocStrip(self):
    node = assertParseRedirect(self, """\
<<-EOF cat
hi
EOF
""")

  def testParseRedirectList(self):
    node = assertParseRedirect(self, """\
<<EOF >out.txt cat
hi
EOF
""")

  def testParseCommandWithLeadingRedirects(self):
    node = assertParseSimpleCommand(self, """\
<<EOF >out.txt cat
hi
EOF
""")
    self.assertEqual(1, len(node.words))
    self.assertEqual(2, len(node.redirects))

  def testClobberRedirect(self):
    node = assertParseSimpleCommand(self, 'echo hi >| clobbered.txt')


class CommandParserTest(unittest.TestCase):

  def testParsePipeline(self):
    node = assertParsePipeline(self, 'ls foo')
    self.assertEqual(2, len(node.words))

    node = assertParsePipeline(self, 'ls foo|wc -l')
    self.assertEqual(2, len(node.children))
    self.assertEqual(command_e.Pipeline, node.tag)

    node = assertParsePipeline(self, '! echo foo | grep foo')
    self.assertEqual(2, len(node.children))
    self.assertEqual(command_e.Pipeline, node.tag)
    self.assertTrue(node.negated)

    node = assertParsePipeline(self, 'ls foo|wc -l|less')
    self.assertEqual(3, len(node.children))
    self.assertEqual(command_e.Pipeline, node.tag)

    _assertParseMethod(self, 'ls foo|', 'ParsePipeline', expect_success=False)

  def testParsePipelineBash(self):
    node = assert_ParseCommandList(self, 'ls | cat |& cat')
    self.assertEqual(command_e.Pipeline, node.tag)
    self.assertEqual([1], node.stderr_indices)

    node = assert_ParseCommandList(self, 'ls |& cat | cat')
    self.assertEqual(command_e.Pipeline, node.tag)
    self.assertEqual([0], node.stderr_indices)

    node = assert_ParseCommandList(self, 'ls |& cat |& cat')
    self.assertEqual(command_e.Pipeline, node.tag)
    self.assertEqual([0, 1], node.stderr_indices)

  def testParseAndOr(self):
    node = assertParseAndOr(self, 'ls foo')
    self.assertEqual(2, len(node.words))

    node = assertParseAndOr(self, 'ls foo|wc -l')
    self.assertEqual(2, len(node.children))
    self.assertEqual(command_e.Pipeline, node.tag)

    node = assertParseAndOr(self, 'ls foo || die')
    self.assertEqual(2, len(node.children))
    self.assertEqual(command_e.AndOr, node.tag)

    node = assertParseAndOr(self, 'ls foo|wc -l || die')
    self.assertEqual(2, len(node.children))
    self.assertEqual(command_e.AndOr, node.tag)

  def testParseCommand(self):
    c_parser = test_lib.InitCommandParser('ls foo')
    node = c_parser.ParseCommand()
    self.assertEqual(2, len(node.words))
    print(node)

    c_parser = test_lib.InitCommandParser('fun() { echo hi; }')
    node = c_parser.ParseCommand()
    print(node)
    self.assertEqual(command_e.ShFunction, node.tag)

  def test_ParseCommandLine(self):
    node = assert_ParseCommandLine(self, 'ls foo 2>/dev/null')
    self.assertEqual(2, len(node.words))

    node = assert_ParseCommandLine(self, 'ls foo|wc -l')
    self.assertEqual(command_e.Pipeline, node.tag)

    node = assert_ParseCommandLine(self, 'ls foo|wc -l || die')
    self.assertEqual(command_e.AndOr, node.tag)

    node = assert_ParseCommandLine(self, 'ls foo|wc -l || die; ls /')
    self.assertEqual(command_e.CommandList, node.tag)
    self.assertEqual(2, len(node.children))  # two top level things

  def test_ParseCommandList(self):
    node = assert_ParseCommandList(self, 'ls foo')
    self.assertEqual(2, len(node.words))

    node = assert_ParseCommandList(self, 'ls foo|wc -l || die; ls /')
    self.assertEqual(command_e.CommandList, node.tag)
    self.assertEqual(2, len(node.children))

    node = assert_ParseCommandList(self, """\
ls foo | wc -l || echo fail ;
echo bar | wc -c || echo f2
""")
    self.assertEqual(command_e.CommandList, node.tag)
    self.assertEqual(2, len(node.children))

    # TODO: Check that we get (LIST (AND_OR (PIPELINE (COMMAND ...)))) here.
    # We want all levels.

  def testParseCase(self):
    # Empty case
    node = assert_ParseCommandLine(self, """\
case foo in
esac
""")
    self.assertEqual(command_e.Case, node.tag)
    self.assertEqual(0, len(node.arms))

# TODO: Test all these.  Probably need to add newlines too.
# case foo esac  # INVALID
# case foo in esac
# case foo in foo) esac
# case foo in foo) ;; esac
# case foo in foo) echo hi ;; esac
# case foo in foo) echo hi; ;; esac

    node = assert_ParseCommandLine(self, """\
case word in
  foo|foo2|foo3) echo hi ;;
esac
""")
    self.assertEqual(command_e.Case, node.tag)
    self.assertEqual(1, len(node.arms))

    node = assert_ParseCommandLine(self, """\
case word in foo) echo one-line ;; esac
""")
    self.assertEqual(command_e.Case, node.tag)
    self.assertEqual(1, len(node.arms))

    node = assert_ParseCommandLine(self, """\
case word in
  foo) echo foo ;;
  bar) echo bar ;;
esac
""")
    self.assertEqual(command_e.Case, node.tag)
    self.assertEqual(2, len(node.arms))

    node = assert_ParseCommandLine(self, """\
case word in
  foo) echo foo ;;    # NO TRAILING ;; but trailing ;
  bar) echo bar ;
esac
""")
    self.assertEqual(command_e.Case, node.tag)
    self.assertEqual(2, len(node.arms))

    node = assert_ParseCommandLine(self, """\
case word in
  foo) echo foo ;;    # NO TRAILING ;;
  bar) echo bar
esac
""")
    self.assertEqual(command_e.Case, node.tag)
    self.assertEqual(2, len(node.arms))

  def testParseWhile(self):
    node = assert_ParseCommandList(self, """\
while true; do
  echo hi
  break
done
""")

    node = assert_ParseCommandList(self, """\
while true  # comment
do  # comment
  echo hi  # comment
  break  # comment
done  # comment
""")

  def testParseUntil(self):
    node = assert_ParseCommandList(self, """\
until false; do
  echo hi
  break
done
""")

  def testParseFor(self):
    node = assert_ParseCommandList(self, """\
for i in 1 2 3; do
  echo $i
done
""")
    self.assertEqual(3, len(node.iter_words))

    # Don't iterate over anything!
    node = assert_ParseCommandList(self, """\
for i in ; do
  echo $i
done
""")
    self.assertEqual(0, len(node.iter_words))
    self.assertEqual(False, node.do_arg_iter)

    # Iterate over the default
    node = assert_ParseCommandList(self, """\
for i; do echo $i; done
""")
    self.assertEqual(True, node.do_arg_iter)

    # Iterate over the default, over multiple lines
    node = assert_ParseCommandList(self, """\
for i
do
  echo $i
done
""")
    self.assertEqual(True, node.do_arg_iter)

  def testParseForExpression(self):
    node = assert_ParseCommandList(self, """\
for ((i=0; i<5; ++i)); do
  echo $i
done
""")
    self.assertEqual(Id.Arith_Equal, node.init.op_id)
    self.assertEqual(Id.Arith_Less, node.cond.op_id)
    self.assertEqual(Id.Arith_DPlus, node.update.op_id)
    self.assertEqual(command_e.DoGroup, node.body.tag)

    # Now without the ; OR a newline
    node = assert_ParseCommandList(self, """\
for ((i=0; i<5; ++i)) do
  echo $i
done
""")
    self.assertEqual(Id.Arith_Equal, node.init.op_id)
    self.assertEqual(Id.Arith_Less, node.cond.op_id)
    self.assertEqual(Id.Arith_DPlus, node.update.op_id)
    self.assertEqual(command_e.DoGroup, node.body.tag)

    node = assert_ParseCommandList(self, """\
for ((;;)); do
  echo $i
done
""")
    self.assertEqual(command_e.DoGroup, node.body.tag)

  def testParseCommandSub(self):
    # Two adjacent command subs
    node = assertParseSimpleCommand(self, 'echo $(echo 12)$(echo 34)')
    self.assertEqual(2, len(node.words))

    # Two adjacent command subs, quoted
    node = assertParseSimpleCommand(self, 'echo "$(echo 12)$(echo 34)"')
    self.assertEqual(2, len(node.words))

  def testParseTildeSub(self):
    node = assert_ParseCommandList(self,
        "ls ~ ~root ~/src ~/src/foo ~root/src ~weird!name/blah!blah ")

  def testParseDBracket(self):
    node = assert_ParseCommandList(self, '[[ $# -gt 1 ]]')

    # Bash allows embedded newlines in some places, but not all
    node = assert_ParseCommandList(self, """\
[[ $# -gt 1 &&

foo ]]""")

    # Newline needs to be Id.Op_Newline!
    node = assert_ParseCommandList(self, """\
if [[ $# -gt 1 ]]
then
  echo hi
fi
""")

    # Doh, technically this works!
    # [[ =~ =~ =~ ]]; echo $?
    # 0

  def testParseDParen(self):
    node = assert_ParseCommandList(self, '(( 1 + 2 ))')

  def testParseDBracketRegex(self):
    node = assert_ParseCommandList(self, '[[ foo =~ foo ]]')
    self.assertEqual(Id.BoolBinary_EqualTilde, node.expr.op_id)

    node = assert_ParseCommandList(self, '[[ foo =~ (foo|bar) ]]')
    self.assertEqual(Id.BoolBinary_EqualTilde, node.expr.op_id)
    right = node.expr.right
    self.assertEqual(5, len(right.parts))
    self.assertEqual('(', right.parts[0].val)

    # TODO: Implement BASH_REGEX_CHARS
    return
    node = assert_ParseCommandList(self, '[[ "< >" =~ (< >) ]]')
    self.assertEqual(Id.BoolBinary_EqualTilde, node.expr.op_id)

    node = assert_ParseCommandList(self, '[[ "ba ba" =~ ([a b]+) ]]')
    self.assertEqual(Id.BoolBinary_EqualTilde, node.expr.op_id)

  def testParseIf(self):
    node = assert_ParseCommandList(self, 'if true; then echo yes; fi')
    # Subshell in condition
    node = assert_ParseCommandList(self, 'if (true); then echo yes; fi')

  def testParseFunction(self):
    node = assert_ParseCommandList(self, 'foo() { echo hi; }')

    node = assert_ParseCommandList(self,
        'foo() ( echo hi )')
    node = assert_ParseCommandList(self,
        'foo() for i in x; do echo $i; done')

    # KSH FUNCTION
    node = assert_ParseCommandList(self, 'function foo { echo hi; }')
    node = assert_ParseCommandList(self, 'function foo () { echo hi; }')

    node = assert_ParseCommandList(self,
        'function foo() ( echo hi )')
    node = assert_ParseCommandList(self,
        'function foo() for i in x; do echo $i; done')

    # No () is OK here!
    node = assert_ParseCommandList(self,
        'function foo for i in x; do echo $i; done')

    # Redirects
    node = assert_ParseCommandList(self, 'foo() { echo hi; } 1>&2 2>/dev/null')
    self.assertEqual(command_e.BraceGroup, node.body.tag)
    self.assertEqual(2, len(node.body.redirects))

  def testParseKeyword(self):
    # NOTE: It chooses the longest match, which is Lit_Chars>
    node = assert_ParseCommandList(self, 'ifFOO')


class NestedParensTest(unittest.TestCase):
  """Test the hard $() and () nesting.

  Meanings of ):

  ( echo x )           # subshell (cmd_parse)
  echo $(echo x)       # command substitution (word_parse)
  (( ))                # end arith command (cmd_parse)
  $(( ))               # end arith sub (word_parse))
  a=(1 2 3)            # array literal and assoc array literal
  a[1*(2+3)]=x         # grouping in arith context
  fun() { echo x ; }   # function def

  case x in x) echo x ;; esac     # case, with balanced or unbalanced
  case x in (x) echo x ;; esac
  """

  def testParseSubshell(self):
    node = assert_ParseCommandLine(self,
        '(cd /; echo PWD 1); echo PWD 2')
    self.assertEqual(2, len(node.children))
    self.assertEqual(command_e.CommandList, node.tag)

  def testParseBraceGroup(self):
    node = assert_ParseCommandLine(self,
        '{ cd /; echo PWD; }')
    self.assertEqual(2, len(node.children))
    self.assertEqual(command_e.BraceGroup, node.tag)

    node = assert_ParseCommandLine(self,
        '{ cd /; echo PWD; }; echo PWD')
    self.assertEqual(2, len(node.children))
    self.assertEqual(command_e.CommandList, node.tag)

  def testUnquotedComSub(self):
    # CommandSub with two Literal instances surrounding it
    node = assertParseSimpleCommand(self,
        'echo ab$(echo hi)cd ef')
    self.assertEqual(3, len(node.words))

  def testNestedComSub(self):
    node = assertParseSimpleCommand(self,
        'echo $(one$(echo two)one) three')
    self.assertEqual(3, len(node.words))

  def testArithSubWithin(self):
    # Within com sub
    node = assertParseSimpleCommand(self,
        'echo $(echo $((1+2)))')
    self.assertEqual(command_e.Simple, node.tag)
    self.assertEqual(2, len(node.words))

    # Within subshell
    node = assert_ParseCommandList(self,
        '(echo $((1+2)))')
    self.assertEqual(command_e.Subshell, node.tag)
    self.assertEqual(command_e.CommandList, node.command_list.tag)

  def testArithGroupingWithin(self):
    # Within com sub
    node = assertParseSimpleCommand(self,
        'echo $(echo $((1*(2+3))) )')
    self.assertEqual(command_e.Simple, node.tag)
    self.assertEqual(2, len(node.words))

    # Within subshell
    node = assert_ParseCommandList(self,
        '(echo $((1*(2+3))) )')
    self.assertEqual(command_e.Subshell, node.tag)
    self.assertEqual(command_e.CommandList, node.command_list.tag)

  def testLhsArithGroupingWithin(self):
    # Within Arith sub
    node = assertParseSimpleCommand(self, 'echo $((a[1*(2+3)]=x))')
    self.assertEqual(2, len(node.words))

    # Within Command Sub -- NOT IMPLEMENTED
    return
    node = assertParseSimpleCommand(self, 'echo $(a[1*(2+3)]=x)')
    self.assertEqual(2, len(node.words))

  def testShFunctionWithin(self):
    node = assert_ParseCommandList(self,
        'echo $(fun() { echo hi; }; fun)')
    self.assertEqual(command_e.Simple, node.tag)
    self.assertEqual(2, len(node.words))

    node = assert_ParseCommandList(self,
        '(fun() { echo hi; }; fun)')
    self.assertEqual(command_e.Subshell, node.tag)
    self.assertEqual(command_e.CommandList, node.command_list.tag)

  def testArrayLiteralWithin(self):
    node = assert_ParseCommandList(self,
        'echo $(array=(a b c))')
    self.assertEqual(command_e.Simple, node.tag)
    self.assertEqual(2, len(node.words))

    node = assert_ParseCommandList(self,
        '(array=(a b c))')
    self.assertEqual(command_e.Subshell, node.tag)
    self.assertEqual(command_e.CommandList, node.command_list.tag)

  def testSubshellWithinComSub(self):
    node = assert_ParseCommandList(self,
        'echo one; echo $( (cd /; echo subshell_PWD); echo comsub_PWD); echo two')
    self.assertEqual(command_e.CommandList, node.tag)
    self.assertEqual(3, len(node.children))   # 3 echo statements

    # TODO: Need a way to test the literal value of a word
    #words = [w.UnquotedLiteralValue() for w in node.children[2].words]
    #print(words)

  def testCaseWithinComSub(self):
    node = assert_ParseCommandList(self,
        'echo $( case foo in one) echo comsub;; esac)')
    self.assertEqual(2, len(node.words))

    node = assert_ParseCommandList(self, """\
echo $(
case foo in one) echo comsub1;; esac
case bar in two) echo comsub2;; esac
)
""")
    self.assertEqual(2, len(node.words))

  def testComsubWithinCaseWithinComSub(self):
    # Comsub within case within comsub
    node = assert_ParseCommandList(self,
        'echo one; echo $( case one in $(echo one)) echo $(comsub);; esac ); echo two')
    self.assertEqual(command_e.CommandList, node.tag)
    # Top level should have 3 echo statements
    self.assertEqual(3, len(node.children))

  def testComSubWithinDoubleQuotes(self):
    # CommandSub with two Literal instances surrounding it
    node = assertParseSimpleCommand(self,
        'echo "double $(echo hi) quoted" two')
    self.assertEqual(3, len(node.words))

  def testEmptyCaseWithinSubshell(self):
    node = assert_ParseCommandList(self, """\
( case foo in
  esac
)
""")
    self.assertEqual(command_e.Subshell, node.tag)

  def testBalancedCaseWithin(self):
    # With leading ( in case.  This one doesn't cause problems!   We don't need
    # the MaybeUnreadOne() lexer hack.
    node = assert_ParseCommandList(self, """\
$( case foo in
  (one) echo hi ;;
  esac
)
""")
    self.assertEqual(command_e.Simple, node.tag)

    node = assert_ParseCommandList(self, """\
( case foo in
  (one) echo hi ;;
  esac
)
""")
    self.assertEqual(command_e.Subshell, node.tag)

  def testUnbalancedCaseWithin(self):
    # With leading ( in case.  This one doesn't cause problems!   We don't need
    # the MaybeUnreadOne() lexer hack.
    node = assert_ParseCommandList(self, """\
$( case foo in
  one) echo hi ;;
  esac
)
""")
    self.assertEqual(command_e.Simple, node.tag)

    node = assert_ParseCommandList(self, """\
( case foo in
  one) echo hi ;;
  esac
)
""")
    self.assertEqual(command_e.Subshell, node.tag)

  def testForExpressionWithin(self):
    # With leading ( in case.  This one doesn't cause problems!   We don't need
    # the MaybeUnreadOne() lexer hack.
    node = assert_ParseCommandList(self, """\
$( for ((i=0; i<3; ++i)); do
     echo hi
   done
)
""")
    self.assertEqual(command_e.Simple, node.tag)

    node = assert_ParseCommandList(self, """\
( for ((i=0; i<3; ++i)); do
    echo hi
  done
)
""")
    self.assertEqual(command_e.Subshell, node.tag)


class RealBugsTest(unittest.TestCase):

  def testGitBug(self):
    # Original bug from git codebase.  Case in subshell.
    node = assert_ParseCommandList(self, """\
( cd "$PACKDIR" &&
  for e in $existing
  do
    case " $fullbases " in
      *" $e "*) ;;
      *) rm -f "$e.pack" "$e.idx" "$e.keep" ;;
    esac
  done
)
""")
    self.assertEqual(command_e.Subshell, node.tag)

  def testParseCase3(self):
    # Bug from git codebase.  NOT a comment token.
    node = assert_ParseCommandLine(self, """\
case "$fd,$command" in
  3,#*|3,)
    # copy comments
    ;;
esac
""")
    self.assertEqual(command_e.Case, node.tag)

  def testGitComment(self):
    # ;# is a comment!  Gah.
    # Conclusion: Comments are NOT LEXICAL.  They are part of word parsing.

    node = assert_ParseCommandList(self, """\
. "$TEST_DIRECTORY"/diff-lib.sh ;# test-lib chdir's into trash
""")
    self.assertEqual(command_e.Sentence, node.tag)
    self.assertEqual(2, len(node.child.words))

    # This is NOT a comment
    node = assert_ParseCommandList(self, """\
echo foo#bar
""")
    self.assertEqual(command_e.Simple, node.tag)
    self.assertEqual(2, len(node.words))
    _, s, _ = word_.StaticEval(node.words[1])
    self.assertEqual('foo#bar', s)

    # This is a comment
    node = assert_ParseCommandList(self, """\
echo foo #comment
""")
    self.assertEqual(command_e.Simple, node.tag)
    self.assertEqual(2, len(node.words))
    _, s, _ = word_.StaticEval(node.words[1])
    self.assertEqual('foo', s)

    # Empty comment
    node = assert_ParseCommandList(self, """\
echo foo #
""")
    self.assertEqual(command_e.Simple, node.tag)
    self.assertEqual(2, len(node.words))
    _, s, _ = word_.StaticEval(node.words[1])
    self.assertEqual('foo', s)

  def testChromeIfSubshell(self):
    node = assert_ParseCommandList(self, """\
if true; then (
  echo hi
)
fi
""")
    self.assertEqual(command_e.If, node.tag)

    node = assert_ParseCommandList(self, """\
while true; do {
  echo hi
  break
} done
""")
    self.assertEqual(command_e.WhileUntil, node.tag)
    self.assertEqual(Id.KW_While, node.keyword.id)

    node = assert_ParseCommandList(self, """\
if true; then (
  echo hi
) fi
""")
    self.assertEqual(command_e.If, node.tag)

    # Related: two fi's in a row, found in Chrome configure.  Compound commands
    # are special; don't need newlines.
    node = assert_ParseCommandList(self, """\
if true; then
  if true; then
    echo hi
  fi fi
echo hi
""")
    self.assertEqual(command_e.CommandList, node.tag)

  def testBackticks(self):
    # Another empty command sub
    node = assert_ParseCommandList(self, """\
echo $()
""")

    # Simplest case
    node = assert_ParseCommandList(self, """\
echo ``
""")

    # Found in the wild.
    # Just a comment trick found in sandstorm
    node = assert_ParseCommandList(self, """\
cmd \
  flag `# comment` \
  flag2
""")

    # Empty should be allowed
    node = assert_ParseCommandList(self, """\
FOO="bar"`
    `"baz"
""")

  def testQuineDb(self):
    # Need to handle the DOLLAR_SQ lex state
    node = assert_ParseCommandList(self, r"""\
case foo in
$'\'')
  ret+="\\"\'
  ;;
esac
""")
    self.assertEqual(command_e.Case, node.tag)

    node = assert_ParseCommandList(self, r"""\
$'abc\ndef'
""")
    self.assertEqual(command_e.Simple, node.tag)
    self.assertEqual(1, len(node.words))
    w = node.words[0]
    self.assertEqual(1, len(w.parts))
    p = w.parts[0]
    self.assertEqual(3, len(p.tokens))
    self.assertEqual(Id.Char_Literals, p.tokens[0].id)
    self.assertEqual(Id.Char_OneChar, p.tokens[1].id)
    self.assertEqual(Id.Char_Literals, p.tokens[2].id)

  def testArithConstants(self):
    # Found in Gherkin
    node = assert_ParseCommandList(self, r"""\
 [[ -n "${marks[${tag_marker}002${cons_ptr}]}" ]];
""")
    # Dynamic constant
    node = assert_ParseCommandList(self, r"""\
echo $(( 0x$foo ))
""")

  def testBacktickCommentHack(self):
    # Found in sandstorm.
    # The problem here is that the comment goes to the end of the line, which
    # eats up the closing backtick!  We could change the mode of the lexer
    # inside a command sub, or possibly just ignore this use case.
    return

    node = assert_ParseCommandList(self, r"""\
openssl \
    -newkey rsa:4096 `# Create a new RSA key of length 4096 bits.` \
    `# Sandcats just needs the CN= (common name) in the request.` \
    -subj "/CN=*.${SS_HOSTNAME}/"
""")

  def testArrayLiteralFromSetup(self):
    # Found in setup.shl/bin/setup -- this is the "Parsing Bash is
    # Undecidable" problem.
    err = _assert_ParseCommandListError(self, """\
errcmd=( "${SETUP_STATE[$err.cmd]}" )
""")

    # Double quotes fix it.
    node = assert_ParseCommandList(self, r"""\
errcmd=( "${SETUP_STATE["$err.cmd"]}" )
""")


class ErrorLocationsTest(unittest.TestCase):

  def testCommand(self):
    """Enumerating errors in cmd_parse.py."""

    err = _assert_ParseCommandListError(self, 'ls <')

    err = _assert_ParseCommandListError(self, 'ls < <')

    # Word parse error in command parser
    err = _assert_ParseCommandListError(self, r'echo foo$(ls <)bar')

    err = _assert_ParseCommandListError(self, r'BAD_ENV=(1 2 3) ls')

    # This needs more context
    err = _assert_ParseCommandListError(self,
        'for ((i=1; i<)); do echo $i; done')

    err = _assert_ParseCommandListError(self,
        'for ((i=1; i<5; ++i)) OOPS echo $i; ERR')

    # After semi
    err = _assert_ParseCommandListError(self,
        'for ((i=1; i<5; ++i)); OOPS echo $i; ERR')

    err = _assert_ParseCommandListError(self,
        'for $bad in 1 2; do echo hi; done')

    err = _assert_ParseCommandListError(self, 'for foo BAD')

    err = _assert_ParseCommandListError(self, 'if foo; then echo hi; z')

    err = _assert_ParseCommandListError(self, 'foo$(invalid) () { echo hi; }')

  def testErrorInHereDoc(self):
    return
    # Here doc body.  Hm this should be failing.  Does it just fail to get
    # filled?
    err = _assert_ParseCommandListError(self, """cat <<EOF
$(echo <)
EOF
""")
    return

  def testBool(self):
    """Enumerating errors in bool_parse.py."""
    err = _assert_ParseCommandListError(self, '[[ foo bar ]]')
    err = _assert_ParseCommandListError(self, '[[ foo -eq ]]')

    # error in word
    err = _assert_ParseCommandListError(self, '[[ foo$(echo <) -eq foo ]]')

    return
    # NOTE: This was disabled because of escaping.
    # Invalid regex
    err = _assert_ParseCommandListError(self, '[[ foo =~ \( ]]')

  def testArith(self):
    """Enumerating errors in arith_parse.py."""
    err = _assert_ParseCommandListError(self, '(( 1 + ))')

  def testArraySyntax(self):
    err = _assert_ParseCommandListError(self, 'A= (1 2)')

  def testEofInDoubleQuoted(self):
    err = _assert_ParseCommandListError(self, 'foo="" echo "bar  ')

  def testQuotesInFunctionName(self):
    err = _assert_ParseCommandListError(self, """\
    foo"bar" () {
      echo hi
    }
    """)

  def testForLoopName(self):
    err = _assert_ParseCommandListError(self, """\
    for [ i = 1; i < 10; i++ ]
    """)
    err = _assert_ParseCommandListError(self, """\
    for = in a
    """)

  def testHereDocCommandSub(self):
    # Originall from spec/09-here-doc.sh.
    err = _assert_ParseCommandListError(self, """\
for x in 1 2 $(cat <<EOF
THREE
EOF); do
  echo for word $x
done
""")

  def testForLoopEof(self):
    err = _assert_ParseCommandListError(self, "for x in 1 2 $(")


if __name__ == '__main__':
  unittest.main()
