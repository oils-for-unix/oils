#!/usr/bin/env python2
"""
sh_spec_test.py: Tests for sh_spec.py
"""

import cStringIO
import pprint
import unittest

from sh_spec import *  # module under test

TEST1 = """\
#### Env binding in readonly/declare disallowed
FOO=foo readonly v=$(tests/printenv.py FOO)
echo "v=$v"
# Shells allow this misleading construct, but the correct behavior is to
# disallow it at parse time.
## OK bash/dash/mksh stdout: v=None
## OK bash/dash/mksh status: 0
## status: 2
"""


TEST2 = """\
#### Multiline test case
echo one
echo two
## status: 1
## stderr-json: ""
## STDOUT:
one
two
## OK dash STDOUT:
dash1
dash2
## END
## OK mksh STDOUT:
mksh1
mksh2
## END
"""


def Slurp(s):
  t = Tokenizer(cStringIO.StringIO(s))
  tokens = []
  while True:
    tok = t.peek()
    print(tok)
    tokens.append(tok)
    if tok[1] == EOF:
      break
    t.next()
  return tokens


class ShSpecTest(unittest.TestCase):

  def setUp(self):
    self.TOKENS1 = Slurp(TEST1)
    t = Tokenizer(cStringIO.StringIO(TEST1))
    self.CASE1 = ParseTestCase(t)
    assert self.CASE1 is not None

    self.TOKENS2 = Slurp(TEST2)
    t = Tokenizer(cStringIO.StringIO(TEST2))
    self.CASE2 = ParseTestCase(t)
    assert self.CASE2 is not None

  def testTokenizer(self):
    #pprint.pprint(TOKENS1)

    types = [type_ for line_num, type_, value in self.TOKENS1]
    self.assertEqual(
        [ TEST_CASE_BEGIN, PLAIN_LINE, PLAIN_LINE,
          KEY_VALUE, KEY_VALUE, KEY_VALUE,
          EOF], types)

    #pprint.pprint(TOKENS2)
    types2 = [type_ for line_num, type_, value in self.TOKENS2]
    self.assertEqual(
        [ TEST_CASE_BEGIN, PLAIN_LINE, PLAIN_LINE,
          KEY_VALUE, KEY_VALUE,
          KEY_VALUE_MULTILINE, PLAIN_LINE, PLAIN_LINE,
          KEY_VALUE_MULTILINE, PLAIN_LINE, PLAIN_LINE, END_MULTILINE,
          KEY_VALUE_MULTILINE, PLAIN_LINE, PLAIN_LINE, END_MULTILINE,
          EOF], types2)

  def testParsed(self):
    CASE1 = self.CASE1
    CASE2 = self.CASE2

    print('CASE1')
    pprint.pprint(CASE1)
    print()

    expected = {'status': '0', 'stdout': 'v=None\n', 'qualifier': 'OK'}
    self.assertEqual(expected, CASE1['bash'])
    self.assertEqual(expected, CASE1['dash'])
    self.assertEqual(expected, CASE1['mksh'])
    self.assertEqual('2', CASE1['status'])
    self.assertEqual(
        'Env binding in readonly/declare disallowed', CASE1['desc'])

    print('CASE2')
    pprint.pprint(CASE2)
    print()
    print(CreateAssertions(CASE2, 'bash'))
    self.assertEqual('one\ntwo\n', CASE2['stdout'])
    self.assertEqual(
        {'qualifier': 'OK', 'stdout': 'dash1\ndash2\n'}, CASE2['dash'])
    self.assertEqual(
        {'qualifier': 'OK', 'stdout': 'mksh1\nmksh2\n'}, CASE2['mksh'])

  def testCreateAssertions(self):
    print(CreateAssertions(self.CASE1, 'bash'))

  def testRunCases(self):
    o = Options()
    opts, _ = o.parse_args(['--no-cd-tmp'])

    shells = [('bash', '/bin/bash'), ('osh', 'bin/osh')]
    env = {}
    if 0:
      out_f = sys.stdout
    else:
      out_f = cStringIO.StringIO()
    out = AnsiOutput(out_f, False)
    RunCases([self.CASE1], lambda i, case: True, shells, env, out, opts)
    print(repr(out.f.getvalue()))


if __name__ == '__main__':
  unittest.main()
