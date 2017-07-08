#!/usr/bin/env python
"""
sh_spec_test.py: Tests for sh_spec.py
"""

import io
import pprint
import unittest

from sh_spec import *  # module under test

TEST = io.BytesIO("""\
### Env binding in readonly/declare disallowed
FOO=foo readonly v=$(tests/printenv.py FOO)
echo "v=$v"
# Shells allow this misleading construct, but the correct behavior is to
# disallow it at parse time.
# OK bash/dash/mksh stdout: v=None
# OK bash/dash/mksh status: 0
# status: 2
""")

TOKENS = list(LineIter(TEST))
CASE = ParseTestCase(Tokenizer(iter(TOKENS)))


class TestShTest(unittest.TestCase):

  def testLineIter(self):
    pprint.pprint(TOKENS)

    types = [type_ for line_num, type_, value in TOKENS]
    self.assertEqual(
        [ TEST_CASE_BEGIN, CODE, CODE, 
          KEY_VALUE, KEY_VALUE, KEY_VALUE,
          EOF], types)

    pprint.pprint(CASE)
    expected = {'status': '0', 'stdout': 'v=None\n', 'qualifier': 'OK'}
    self.assertEqual(expected, CASE['bash'])
    self.assertEqual(expected, CASE['dash'])
    self.assertEqual(expected, CASE['mksh'])

  def testCreateAssertions(self):
    print(CreateAssertions(CASE, 'bash'))

  def testRunCases(self):
    shells = [('bash', '/bin/bash'), ('osh', 'bin/osh')]
    env = {}
    out = AnsiOutput(sys.stdout, False)
    RunCases([CASE], lambda i, case: True, shells, env, out)


if __name__ == '__main__':
  unittest.main()
